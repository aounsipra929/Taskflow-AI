"""OpenRouter Chat Completions client.

Two ways of letting the model choose an action, behind one interface:

* native  - OpenAI-style ``tools`` / ``tool_calls`` (used when the model supports it)
* json    - the model answers with one JSON object that is validated with Pydantic
            (used when the model has no tool support, or OPENROUTER_TOOL_MODE=json)

In ``auto`` mode we try native first and remember, per model, when OpenRouter says
the model cannot do tool calling, so later requests go straight to JSON mode.

The API key is read from the backend settings only and never leaves this module.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, ValidationError, model_validator

from app.core.config import settings

logger = logging.getLogger("todo.llm")


# --------------------------------------------------------------------------- types
class LLMError(Exception):
    """Anything that goes wrong while talking to the model. `message` is safe to show."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class _ToolsUnsupported(Exception):
    pass


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    parse_error: str | None = None


@dataclass
class LLMTurn:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class _JsonReply(BaseModel):
    """The protocol used when native tool calling is not available."""

    action: Literal["tool_call", "final"]
    tool: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    message: str | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.action == "tool_call" and not self.tool:
            raise ValueError("'tool' is required when action is 'tool_call'")
        if self.action == "final" and not (self.message or "").strip():
            raise ValueError("'message' is required when action is 'final'")
        return self


_JSON_PROTOCOL = """\

## Response format (STRICT)
You cannot call tools natively, so reply with EXACTLY ONE JSON object and nothing else
(no markdown, no code fences, no text before or after it).

To use a tool:
{"action": "tool_call", "tool": "<tool name>", "arguments": { ... }}

To answer the user:
{"action": "final", "message": "<your reply to the user>"}

After a tool call you will receive a message starting with TOOL_RESULT. Use it to decide
the next step. Call one tool at a time.

## Available tools (name: description, JSON-schema of arguments)
"""


# --------------------------------------------------------------------------- client
class OpenRouterClient:
    # model ids that OpenRouter told us cannot do tool calling (process-wide cache)
    _no_native_tools: set[str] = set()

    def __init__(self, transport: httpx.BaseTransport | None = None):
        self._transport = transport  # tests inject httpx.MockTransport

    # ---- public ---------------------------------------------------------------
    def complete(self, messages: list[dict], tools: list[dict]) -> LLMTurn:
        if not settings.chatbot_enabled:
            raise LLMError("The Chatbot Assistant is not configured yet (missing OpenRouter settings).", 503)

        model = settings.OPENROUTER_MODEL.strip()
        mode = settings.OPENROUTER_TOOL_MODE.strip().lower()

        if mode == "native" or (mode == "auto" and model not in self._no_native_tools):
            try:
                return self._complete_native(messages, tools)
            except _ToolsUnsupported:
                if mode == "native":
                    raise LLMError("The selected model does not support tool calling. Set OPENROUTER_TOOL_MODE=auto or json.", 503)
                logger.info("Model %s has no native tool calling; switching to JSON mode", model)
                self._no_native_tools.add(model)
        return self._complete_json(messages, tools)

    # ---- native tool calling --------------------------------------------------
    def _complete_native(self, messages: list[dict], tools: list[dict]) -> LLMTurn:
        data = self._post(
            {
                "model": settings.OPENROUTER_MODEL.strip(),
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "temperature": 0.2,
            },
            detect_tool_support=True,
        )
        msg = self._first_message(data)
        calls: list[ToolCall] = []
        for i, tc in enumerate(msg.get("tool_calls") or []):
            fn = tc.get("function") or {}
            raw = fn.get("arguments") or "{}"
            args: dict[str, Any] = {}
            err: str | None = None
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(parsed, dict):
                    args = parsed
                else:
                    err = "arguments must be a JSON object"
            except json.JSONDecodeError:
                err = "arguments were not valid JSON"
            calls.append(ToolCall(id=tc.get("id") or f"call_{i}", name=fn.get("name") or "", arguments=args, parse_error=err))
        return LLMTurn(content=(msg.get("content") or "").strip(), tool_calls=calls)

    # ---- JSON protocol --------------------------------------------------------
    def _complete_json(self, messages: list[dict], tools: list[dict]) -> LLMTurn:
        convo = self._to_json_mode_messages(messages, tools)
        last_error = ""
        for attempt in range(2):
            data = self._post(
                {"model": settings.OPENROUTER_MODEL.strip(), "messages": convo, "temperature": 0.2},
                detect_tool_support=False,
            )
            text = (self._first_message(data).get("content") or "").strip()
            try:
                reply = _JsonReply.model_validate(self._extract_json(text))
            except (ValueError, ValidationError) as exc:
                last_error = str(exc)
                logger.warning("Model returned invalid JSON-mode reply (attempt %s): %s", attempt + 1, last_error[:200])
                convo = convo + [
                    {"role": "assistant", "content": text},
                    {
                        "role": "user",
                        "content": "Your last reply was not valid. Reply with ONE JSON object exactly as specified "
                        '(either {"action":"tool_call",...} or {"action":"final","message":"..."}).',
                    },
                ]
                continue
            if reply.action == "final":
                return LLMTurn(content=(reply.message or "").strip())
            return LLMTurn(tool_calls=[ToolCall(id="json_call", name=reply.tool or "", arguments=reply.arguments)])

        # The model keeps answering in prose. Plain text is harmless (it cannot change data),
        # so show it rather than failing the whole request.
        logger.warning("JSON mode failed twice (%s); returning raw text", last_error[:200])
        return LLMTurn(content=text or "Sorry, I could not understand that. Could you rephrase?")

    @staticmethod
    def _to_json_mode_messages(messages: list[dict], tools: list[dict]) -> list[dict]:
        catalogue = "\n".join(
            f"- {t['function']['name']}: {t['function']['description']}\n  arguments: "
            f"{json.dumps(t['function']['parameters'], separators=(',', ':'))}"
            for t in tools
        )
        out: list[dict] = []
        for m in messages:
            role = m["role"]
            if role == "system":
                out.append({"role": "system", "content": m["content"] + _JSON_PROTOCOL + catalogue})
            elif role == "assistant" and m.get("tool_calls"):
                tc = m["tool_calls"][0]["function"]
                try:
                    args = json.loads(tc.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                out.append({"role": "assistant", "content": json.dumps({"action": "tool_call", "tool": tc["name"], "arguments": args})})
            elif role == "tool":
                out.append({"role": "user", "content": f"TOOL_RESULT for {m.get('name', 'tool')}:\n{m['content']}"})
            elif role == "assistant":
                out.append({"role": "assistant", "content": json.dumps({"action": "final", "message": m.get("content") or ""})})
            else:
                out.append({"role": role, "content": m["content"]})
        return out

    @staticmethod
    def _extract_json(text: str) -> dict:
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("no JSON object found")
        obj = json.loads(text[start : end + 1])
        if not isinstance(obj, dict):
            raise ValueError("JSON reply must be an object")
        return obj

    # ---- HTTP -----------------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {settings.OPENROUTER_API_KEY.strip()}", "Content-Type": "application/json"}
        if settings.OPENROUTER_SITE_URL:
            headers["HTTP-Referer"] = settings.OPENROUTER_SITE_URL
        if settings.OPENROUTER_APP_NAME:
            headers["X-Title"] = settings.OPENROUTER_APP_NAME
        return headers

    def _post(self, payload: dict, detect_tool_support: bool) -> dict:
        url = settings.OPENROUTER_BASE_URL.rstrip("/") + "/chat/completions"
        try:
            with httpx.Client(timeout=settings.OPENROUTER_TIMEOUT_SECONDS, transport=self._transport) as http:
                resp = http.post(url, headers=self._headers(), json=payload)
        except httpx.TimeoutException:
            raise LLMError("The AI model took too long to respond. Please try again.", 504)
        except httpx.HTTPError:
            logger.exception("OpenRouter network error")
            raise LLMError("Could not reach the AI service. Please try again later.", 503)

        if resp.status_code >= 400:
            self._raise_for_status(resp.status_code, resp.text, detect_tool_support)

        try:
            data = resp.json()
        except ValueError:
            raise LLMError("The AI service returned an unreadable response.", 502)

        # OpenRouter sometimes answers HTTP 200 with an {"error": {...}} body.
        if isinstance(data, dict) and data.get("error") and not data.get("choices"):
            err = data["error"] if isinstance(data["error"], dict) else {"message": str(data["error"])}
            code = err.get("code")
            self._raise_for_status(int(code) if isinstance(code, int) else 502, json.dumps(err), detect_tool_support)
        return data

    @staticmethod
    def _raise_for_status(status: int, body: str, detect_tool_support: bool) -> None:
        logger.warning("OpenRouter HTTP %s: %s", status, body[:300])
        low = body.lower()
        if detect_tool_support and status in (400, 404) and ("tool" in low or "function" in low):
            raise _ToolsUnsupported()
        if status in (401, 403):
            raise LLMError("The AI service rejected the API key. Please contact the administrator.", 503)
        if status == 402:
            raise LLMError("The AI service has no credits left for this model.", 503)
        if status == 404:
            raise LLMError("The configured AI model was not found. Please contact the administrator.", 503)
        if status == 429:
            raise LLMError("The AI model is busy or rate-limited right now. Please wait a moment and try again.", 429)
        if status == 408:
            raise LLMError("The AI model took too long to respond. Please try again.", 504)
        if status >= 500:
            raise LLMError("The AI service is temporarily unavailable. Please try again later.", 503)
        raise LLMError("The AI service could not process the request.", 502)

    @staticmethod
    def _first_message(data: dict) -> dict:
        try:
            msg = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            raise LLMError("The AI service returned an empty response. Please try again.", 502)
        if not isinstance(msg, dict):
            raise LLMError("The AI service returned an unexpected response.", 502)
        return msg


def get_llm_client() -> OpenRouterClient:
    """FastAPI dependency (tests override it with a fake)."""
    return OpenRouterClient()

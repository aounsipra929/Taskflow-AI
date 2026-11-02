import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { chatApi } from "../api/services";
import { getErrorMessage } from "../utils/errors";
import { useAuth } from "./AuthContext";

/**
 * Chat state lives above the routes so the conversation survives navigation between pages.
 * Nothing is written to browser storage; the conversation is cleared on login / logout.
 * The OpenRouter key is never here - the browser only talks to our own FastAPI backend.
 */
const ChatContext = createContext(null);

let counter = 0;
const uid = () => `m${Date.now()}-${counter++}`;
const MAX_HISTORY = 10;

// The browser's local date (YYYY-MM-DD) so "tomorrow" is right for the person asking.
const localDate = () => {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
};

// Tells task lists / dashboards to reload after the assistant changed data.
const announceChange = () => window.dispatchEvent(new Event("tasks:changed"));

export function ChatProvider({ children }) {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const [enabled, setEnabled] = useState(null); // null = not checked yet

  const messagesRef = useRef(messages);
  messagesRef.current = messages;
  const sendingRef = useRef(false);
  const userId = user?.id ?? null;

  // New session whenever a different person signs in (or out).
  useEffect(() => {
    setMessages([]);
    setOpen(false);
    setEnabled(null);
    setSending(false);
    sendingRef.current = false;
  }, [userId]);

  // Ask the backend (once per session) whether the assistant is configured.
  useEffect(() => {
    if (!open || !userId || enabled !== null) return;
    chatApi
      .status()
      .then((res) => setEnabled(!!res.data.enabled))
      .catch(() => setEnabled(true)); // unknown: let the first message report the real problem
  }, [open, userId, enabled]);

  const patchMessage = useCallback((id, patch) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch(m) } : m)));
  }, []);

  const send = useCallback(async (text) => {
    const content = text.trim();
    if (!content || sendingRef.current) return;

    const history = messagesRef.current
      .filter((m) => !m.error && m.content)
      .slice(-MAX_HISTORY)
      .map((m) => ({ role: m.role, content: m.content }));

    sendingRef.current = true;
    setSending(true);
    setMessages((prev) => [...prev, { id: uid(), role: "user", content }]);
    try {
      const { data } = await chatApi.send({ message: content, history, client_date: localDate() });
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: "assistant",
          content: data.reply,
          tasks: data.tasks || [],
          stats: data.stats || null,
          pending: data.pending_action ? { ...data.pending_action, state: "idle", error: null } : null,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: "assistant",
          error: true,
          content: getErrorMessage(err, "The assistant could not answer right now."),
          retryText: content,
        },
      ]);
    } finally {
      sendingRef.current = false;
      setSending(false);
    }
  }, []);

  // Remove the failed exchange and ask again.
  const retry = useCallback(
    (id) => {
      const list = messagesRef.current;
      const idx = list.findIndex((m) => m.id === id);
      if (idx < 1) return;
      const text = list[idx].retryText;
      setMessages(list.filter((_, i) => i !== idx && i !== idx - 1));
      send(text);
    },
    [send]
  );

  const confirm = useCallback(
    async (messageId, action) => {
      patchMessage(messageId, (m) => ({ pending: { ...m.pending, state: "busy", error: null } }));
      try {
        const { data } = await chatApi.confirm(action.id);
        patchMessage(messageId, (m) => ({ pending: { ...m.pending, state: "done" } }));
        setMessages((prev) => [
          ...prev,
          { id: uid(), role: "assistant", content: `✅ ${data.message}`, tasks: data.task ? [data.task] : [] },
        ]);
        announceChange();
      } catch (err) {
        const status = err.response?.status;
        const message = getErrorMessage(err, "Could not apply the change.");
        // 404/409/410/422 are final (expired, already handled, changed...). Anything else may be retried.
        const final = [404, 409, 410, 422].includes(status);
        patchMessage(messageId, (m) => ({ pending: { ...m.pending, state: final ? "failed" : "idle", error: message } }));
      }
    },
    [patchMessage]
  );

  const cancel = useCallback(
    async (messageId, action) => {
      patchMessage(messageId, (m) => ({ pending: { ...m.pending, state: "busy", error: null } }));
      try {
        await chatApi.cancel(action.id);
      } catch {
        /* the action expires on its own; treat it as cancelled in the UI */
      }
      patchMessage(messageId, (m) => ({ pending: { ...m.pending, state: "cancelled" } }));
      setMessages((prev) => [...prev, { id: uid(), role: "assistant", content: "Okay, cancelled. Nothing was changed." }]);
    },
    [patchMessage]
  );

  const reset = useCallback(() => setMessages([]), []);

  const value = useMemo(
    () => ({ open, setOpen, messages, sending, enabled, send, retry, confirm, cancel, reset }),
    [open, messages, sending, enabled, send, retry, confirm, cancel, reset]
  );
  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export const useChat = () => useContext(ChatContext);

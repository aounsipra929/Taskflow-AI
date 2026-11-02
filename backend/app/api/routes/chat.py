"""Chatbot Assistant endpoints (any authenticated user; admins get extra, server-checked abilities)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import ActionResult, ChatRequest, ChatResponse, ChatStatus
from app.services import chat_service
from app.services.llm_client import LLMError, OpenRouterClient, get_llm_client

router = APIRouter(prefix="/chat", tags=["Chatbot"])


@router.get("/status", response_model=ChatStatus)
def chat_status(_: User = Depends(get_current_user)):
    """Lets the UI explain that the assistant is not configured (the API key is never exposed)."""
    return ChatStatus(enabled=settings.chatbot_enabled)


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    llm: OpenRouterClient = Depends(get_llm_client),
):
    """One chat turn. The LLM may read tasks; changes are returned as a pending action to confirm."""
    try:
        return chat_service.handle_chat(db, user, payload, llm)
    except LLMError as exc:
        raise HTTPException(exc.status_code, exc.message)


@router.post("/actions/{action_id}/confirm", response_model=ActionResult)
def confirm(action_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Execute a change the assistant proposed. Works once, only for its owner, only before it expires."""
    return chat_service.confirm_action(db, user, action_id)


@router.post("/actions/{action_id}/cancel", response_model=ActionResult)
def cancel(action_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return chat_service.cancel_action(db, user, action_id)

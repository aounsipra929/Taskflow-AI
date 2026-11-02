"""Request / response models for the chatbot endpoints."""
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatHistoryItem] = Field(default_factory=list, max_length=40)
    # The browser's local date, so "tomorrow" means tomorrow for the person asking.
    client_date: date | None = None


class ChatTaskCard(BaseModel):
    id: int
    title: str
    description: str | None = None
    priority: str
    status: str
    due_date: date | None = None
    overdue: bool = False
    owner_id: int | None = None
    owner_name: str | None = None
    reason: str | None = None  # why it was suggested (computed by the backend)


class PendingActionRead(BaseModel):
    id: str
    action_type: Literal["create_task", "update_task", "delete_task"]
    summary: str
    destructive: bool = False
    expires_at: datetime
    task: ChatTaskCard | None = None  # the current task for update / delete


class ChatResponse(BaseModel):
    reply: str
    tasks: list[ChatTaskCard] = Field(default_factory=list)
    stats: dict[str, Any] | None = None
    pending_action: PendingActionRead | None = None


class ChatStatus(BaseModel):
    enabled: bool


class ActionResult(BaseModel):
    ok: bool
    message: str
    action_type: str
    task: ChatTaskCard | None = None

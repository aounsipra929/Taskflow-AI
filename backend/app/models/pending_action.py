"""A task change proposed by the chatbot that is waiting for the user's confirmation.

The LLM can only *propose* create/update/delete actions. They are stored here and
executed by the confirm endpoint, so a change always needs an explicit click from
the person who owns the action, and it can be executed at most once.
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PendingAction(Base):
    __tablename__ = "pending_actions"
    __table_args__ = (Index("ix_pending_actions_user_status", "user_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # uuid4
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    action_type: Mapped[str] = mapped_column(String(20))  # create_task | update_task | delete_task
    payload: Mapped[dict] = mapped_column(JSON)  # validated arguments (+ snapshot of the target task)
    summary: Mapped[str] = mapped_column(Text)  # human readable, built by the backend, not the LLM
    # pending -> confirmed | cancelled | expired | failed
    status: Mapped[str] = mapped_column(String(12), default="pending", server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

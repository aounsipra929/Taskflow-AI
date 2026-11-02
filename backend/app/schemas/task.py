from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import Priority, TaskStatus
from app.schemas.user import UserBrief


class TaskBase(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    priority: Priority = Priority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title must not be blank")
        return v


class TaskCreate(TaskBase):
    pass


class AdminTaskCreate(TaskBase):
    """Admin may create a task on behalf of any user."""

    user_id: int


class TaskUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    priority: Priority | None = None
    status: TaskStatus | None = None
    due_date: date | None = None


class TaskStatusUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    status: TaskStatus


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    priority: Priority
    status: TaskStatus
    due_date: date | None
    created_at: datetime
    updated_at: datetime
    user_id: int
    owner: UserBrief | None = None


class DashboardStats(BaseModel):
    total_users: int
    active_users: int
    total_tasks: int
    completed_tasks: int
    pending_tasks: int

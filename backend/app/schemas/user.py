import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import Role


def _validate_password(value: str) -> str:
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must contain at least one letter and one number")
    return value


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.lower()

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()

    _check_password = field_validator("password")(_validate_password)


class UserUpdate(BaseModel):
    """Profile update. Every field is optional."""

    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    password: str | None = Field(default=None, min_length=8, max_length=72)
    current_password: str | None = None

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str | None) -> str | None:
        return _validate_password(v) if v is not None else v


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str


class UserRead(UserBrief):
    role: Role
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AdminUserRead(UserRead):
    task_count: int = 0


class UserStatusUpdate(BaseModel):
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead

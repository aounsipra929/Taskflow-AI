"""Reusable FastAPI dependencies: auth, authorization, query parameters."""
from datetime import date
from typing import Literal

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import Priority, TaskStatus
from app.models.user import User
from app.services.task_service import TaskFilters

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise credentials_error
    user = db.get(User, user_id)
    if user is None:
        raise credentials_error
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin privileges required")
    return user


def task_filters(
    q: str | None = Query(None, max_length=100, description="Search in title and description"),
    status: TaskStatus | None = Query(None, description="pending | completed"),
    priority: Priority | None = Query(None, description="low | medium | high"),
    due_from: date | None = Query(None, description="Due date on/after (YYYY-MM-DD)"),
    due_to: date | None = Query(None, description="Due date on/before (YYYY-MM-DD)"),
    sort_by: Literal["due_date", "created_at", "priority"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> TaskFilters:
    return TaskFilters(
        q=q,
        status=status.value if status else None,
        priority=priority.value if priority else None,
        due_from=due_from,
        due_to=due_to,
        sort_by=sort_by,
        order=order,
        page=page,
        page_size=page_size,
    )

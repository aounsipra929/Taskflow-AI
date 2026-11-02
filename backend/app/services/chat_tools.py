"""The only things the chatbot's LLM is allowed to do.

* Read tools run immediately (list / search / details / suggestions / statistics).
* Write tools (create / update / delete) are only *staged*: they are validated here,
  stored as a PendingAction and executed after the user clicks "Confirm"
  (see chat_service.confirm_action).

The model never sees SQL and never writes SQL. Every argument is validated with Pydantic,
and permissions come from the authenticated user loaded from the database - never from
anything the model or the browser claims.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import TaskStatus
from app.models.task import Task
from app.models.user import User
from app.schemas.chat import ChatTaskCard
from app.schemas.task import TaskCreate, TaskUpdate
from app.services import task_service
from app.services.task_service import TaskFilters

READ_TOOLS = {"list_tasks", "get_task", "suggest_next_tasks", "get_task_stats", "find_users"}
WRITE_TOOLS = {"create_task", "update_task", "delete_task"}

_PRIORITY_WEIGHT = {"low": 1, "medium": 2, "high": 3}
_STOPWORDS = {"the", "and", "for", "task", "tasks", "my", "our", "that", "this", "with", "from", "old", "all"}


class ToolError(Exception):
    """A problem the model should hear about (bad id, not allowed, invalid value...)."""


@dataclass
class ToolContext:
    db: Session
    user: User
    today: date
    cards: list[ChatTaskCard] = field(default_factory=list)  # tasks to show as cards
    stats: dict[str, Any] | None = None


@dataclass
class StagedAction:
    action_type: str
    payload: dict[str, Any]
    summary: str
    destructive: bool
    card: ChatTaskCard | None


# --------------------------------------------------------------------------- argument models
class _Args(BaseModel):
    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _drop_empty(cls, data):
        # Models often send null / "" for "not provided".
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if v is not None and v != ""}
        return data


class ListTasksArgs(_Args):
    query: str | None = Field(None, max_length=100)
    status: Literal["pending", "completed"] | None = None
    priority: Literal["low", "medium", "high"] | None = None
    due_from: date | None = None
    due_to: date | None = None
    overdue_only: bool = False
    sort_by: Literal["due_date", "created_at", "priority"] = "due_date"
    order: Literal["asc", "desc"] = "asc"
    limit: int = 10
    scope: Literal["mine", "all"] | None = None
    owner_user_id: int | None = None

    @field_validator("limit", mode="before")
    @classmethod
    def _clamp(cls, v):
        try:
            return max(1, min(int(v), 20))
        except (TypeError, ValueError):
            return 10


class GetTaskArgs(_Args):
    task_id: int


class SuggestArgs(_Args):
    limit: int = 3
    scope: Literal["mine", "all"] | None = None

    @field_validator("limit", mode="before")
    @classmethod
    def _clamp(cls, v):
        try:
            return max(1, min(int(v), 5))
        except (TypeError, ValueError):
            return 3


class StatsArgs(_Args):
    scope: Literal["mine", "all"] | None = None
    owner_user_id: int | None = None


class FindUsersArgs(_Args):
    query: str | None = Field(None, max_length=100)
    limit: int = 10

    @field_validator("limit", mode="before")
    @classmethod
    def _clamp(cls, v):
        try:
            return max(1, min(int(v), 10))
        except (TypeError, ValueError):
            return 10


class CreateTaskArgs(_Args):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(None, max_length=5000)
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: date | None = None
    owner_user_id: int | None = None

    @field_validator("title")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be blank")
        return v


class UpdateTaskArgs(_Args):
    task_id: int
    title: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=5000)
    priority: Literal["low", "medium", "high"] | None = None
    status: Literal["pending", "completed"] | None = None
    due_date: date | None = None
    clear_due_date: bool = False


class DeleteTaskArgs(_Args):
    task_id: int


# --------------------------------------------------------------------------- tool schemas
def _fn(name: str, description: str, properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required or []},
        },
    }


_PRIORITY = {"type": "string", "enum": ["low", "medium", "high"]}
_STATUS = {"type": "string", "enum": ["pending", "completed"]}
_DATE = {"type": "string", "description": "Date as YYYY-MM-DD"}


def tool_definitions(user: User) -> list[dict]:
    """Tools offered to the model. Admin-only parameters/tools are only offered to admins
    (and are re-checked on the server regardless)."""
    admin = user.is_admin
    scope = {"type": "string", "enum": ["mine", "all"], "description": "mine = the admin's own tasks, all = every user's tasks"}
    owner = {"type": "integer", "description": "Restrict to / assign to this user id (use find_users to look it up)"}

    list_props: dict[str, Any] = {
        "query": {"type": "string", "description": "ONE or two keywords to search in title/description, e.g. 'presentation'"},
        "status": _STATUS,
        "priority": _PRIORITY,
        "due_from": _DATE,
        "due_to": _DATE,
        "overdue_only": {"type": "boolean", "description": "Only pending tasks whose due date has passed"},
        "sort_by": {"type": "string", "enum": ["due_date", "created_at", "priority"]},
        "order": {"type": "string", "enum": ["asc", "desc"]},
        "limit": {"type": "integer", "description": "Max tasks to return (1-20, default 10)"},
    }
    create_props: dict[str, Any] = {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "priority": _PRIORITY,
        "due_date": _DATE,
    }
    stats_props: dict[str, Any] = {}
    suggest_props: dict[str, Any] = {"limit": {"type": "integer", "description": "How many tasks to suggest (1-5, default 3)"}}
    if admin:
        list_props.update(scope=scope, owner_user_id=owner)
        create_props["owner_user_id"] = {"type": "integer", "description": "Create the task for this user id instead of the admin"}
        stats_props.update(scope=scope, owner_user_id=owner)
        suggest_props["scope"] = scope

    tools = [
        _fn(
            "list_tasks",
            "Search and list tasks from the database. ALWAYS use this before talking about existing tasks, "
            "and to find a task's id before updating or deleting it.",
            list_props,
        ),
        _fn("get_task", "Get the full details of one task by its id.", {"task_id": {"type": "integer"}}, ["task_id"]),
        _fn(
            "suggest_next_tasks",
            "Rank pending tasks by urgency (overdue, due date, priority) and return the best ones to work on next, "
            "each with a reason computed by the system.",
            suggest_props,
        ),
        _fn(
            "get_task_stats",
            "Get task statistics (totals, pending, completed, overdue, high-priority, due today / next 7 days).",
            stats_props,
        ),
        _fn(
            "create_task",
            "Propose creating a new task. Nothing is saved until the user confirms.",
            create_props,
            ["title"],
        ),
        _fn(
            "update_task",
            "Propose changing a task (title, description, priority, status, due date). Needs the task id. "
            "Use status=completed to mark it done. Nothing changes until the user confirms.",
            {
                "task_id": {"type": "integer"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "priority": _PRIORITY,
                "status": _STATUS,
                "due_date": _DATE,
                "clear_due_date": {"type": "boolean", "description": "Remove the due date"},
            },
            ["task_id"],
        ),
        _fn(
            "delete_task",
            "Propose deleting a task. Needs the task id. Nothing is deleted until the user confirms.",
            {"task_id": {"type": "integer"}},
            ["task_id"],
        ),
    ]
    if admin:
        tools.append(
            _fn(
                "find_users",
                "Admin only: look up users by name or e-mail to get their ids.",
                {"query": {"type": "string"}, "limit": {"type": "integer"}},
            )
        )
    return tools


# --------------------------------------------------------------------------- helpers
def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def stamp(task: Task) -> str:
    """Version marker of a task row, used to detect edits between proposal and confirmation."""
    return _aware(task.updated_at).astimezone(timezone.utc).isoformat() if task.updated_at else ""


def _is_overdue(task: Task, today: date) -> bool:
    return task.status == TaskStatus.PENDING.value and task.due_date is not None and task.due_date < today


def to_card(ctx_or_user: ToolContext | User, task: Task, today: date, reason: str | None = None) -> ChatTaskCard:
    user = ctx_or_user.user if isinstance(ctx_or_user, ToolContext) else ctx_or_user
    show_owner = user.is_admin and task.owner is not None
    return ChatTaskCard(
        id=task.id,
        title=task.title,
        description=task.description,
        priority=task.priority,
        status=task.status,
        due_date=task.due_date,
        overdue=_is_overdue(task, today),
        owner_id=task.user_id if show_owner else None,
        owner_name=task.owner.full_name if show_owner else None,
        reason=reason,
    )


def _task_for_llm(card: ChatTaskCard) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": card.id,
        "title": card.title,
        "description": (card.description or "")[:300] or None,
        "priority": card.priority,
        "status": card.status,
        "due_date": card.due_date.isoformat() if card.due_date else None,
        "overdue": card.overdue,
    }
    if card.owner_name:
        d["owner"] = {"id": card.owner_id, "name": card.owner_name}
    if card.reason:
        d["reason"] = card.reason
    return d


def _get_task(ctx: ToolContext, task_id: int) -> Task:
    """Always re-reads the row. Users get 404 for other people's tasks; admins can see all."""
    try:
        return task_service.get_task_for_user(ctx.db, task_id, ctx.user)
    except HTTPException:
        raise ToolError(f"Task #{task_id} was not found (or you do not have access to it).")


def _resolve_owner(ctx: ToolContext, scope: str | None, owner_user_id: int | None, default_all_for_admin: bool) -> int | None:
    """Which user's tasks to read. None = every user (admins only)."""
    user = ctx.user
    if not user.is_admin:
        if scope == "all" or (owner_user_id is not None and owner_user_id != user.id):
            raise ToolError("You are only allowed to access your own tasks.")
        return user.id
    if owner_user_id is not None:
        if ctx.db.get(User, owner_user_id) is None:
            raise ToolError(f"User #{owner_user_id} does not exist.")
        return owner_user_id
    if scope == "mine":
        return user.id
    if scope == "all":
        return None
    return None if default_all_for_admin else user.id


def _validate(model: type[BaseModel], arguments: dict[str, Any]):
    try:
        return model.model_validate(arguments)
    except ValidationError as exc:
        msgs = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())
        raise ToolError(f"Invalid arguments - {msgs}")


# --------------------------------------------------------------------------- read tools
def run_read_tool(ctx: ToolContext, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute a read-only tool. Returns JSON-serialisable data for the model."""
    try:
        if name == "list_tasks":
            return _list_tasks(ctx, _validate(ListTasksArgs, arguments))
        if name == "get_task":
            return _get_task_tool(ctx, _validate(GetTaskArgs, arguments))
        if name == "suggest_next_tasks":
            return _suggest(ctx, _validate(SuggestArgs, arguments))
        if name == "get_task_stats":
            return _stats(ctx, _validate(StatsArgs, arguments))
        if name == "find_users":
            return _find_users(ctx, _validate(FindUsersArgs, arguments))
    except ToolError as exc:
        return {"error": str(exc)}
    return {"error": f"Unknown tool '{name}'."}


def _list_tasks(ctx: ToolContext, a: ListTasksArgs) -> dict[str, Any]:
    owner_id = _resolve_owner(ctx, a.scope, a.owner_user_id, default_all_for_admin=True)
    f = TaskFilters(
        q=a.query,
        status=a.status,
        priority=a.priority,
        due_from=a.due_from,
        due_to=a.due_to,
        sort_by=a.sort_by,
        order=a.order,
        page=1,
        page_size=a.limit,
    )
    if a.overdue_only:
        f.status = TaskStatus.PENDING.value
        yesterday = ctx.today - timedelta(days=1)
        f.due_to = min(f.due_to, yesterday) if f.due_to else yesterday

    items, total = task_service.list_tasks(ctx.db, f, owner_id=owner_id)

    # "finish my assignment" finds nothing as a phrase -> try the individual keywords.
    if not items and a.query:
        words = [w for w in re.findall(r"\w+", a.query.lower()) if len(w) > 2 and w not in _STOPWORDS]
        if len(words) > 1:
            hits: dict[int, tuple[int, Task]] = {}
            for w in words[:5]:
                sub = TaskFilters(**{**f.__dict__, "q": w})
                found, _ = task_service.list_tasks(ctx.db, sub, owner_id=owner_id)
                for t in found:
                    n, _t = hits.get(t.id, (0, t))
                    hits[t.id] = (n + 1, t)
            ranked = sorted(hits.values(), key=lambda x: -x[0])
            items = [t for _, t in ranked][: a.limit]
            total = len(hits)

    cards = [to_card(ctx, t, ctx.today) for t in items]
    ctx.cards = cards
    return {
        "today": ctx.today.isoformat(),
        "total_matching": total,
        "returned": len(cards),
        "tasks": [_task_for_llm(c) for c in cards],
    }


def _get_task_tool(ctx: ToolContext, a: GetTaskArgs) -> dict[str, Any]:
    task = _get_task(ctx, a.task_id)
    card = to_card(ctx, task, ctx.today)
    ctx.cards = [card]
    full = _task_for_llm(card)
    full["description"] = card.description
    full["created_at"] = _aware(task.created_at).isoformat() if task.created_at else None
    full["updated_at"] = _aware(task.updated_at).isoformat() if task.updated_at else None
    return {"today": ctx.today.isoformat(), "task": full}


def _rank(task: Task, today: date) -> tuple[int, str]:
    """Deterministic urgency score + a human reason. Higher score = work on it sooner."""
    prio = _PRIORITY_WEIGHT.get(task.priority, 2)
    if task.due_date is None:
        urgency, when = 0, "no due date"
    else:
        days = (task.due_date - today).days
        if days < 0:
            urgency = 100 + min(-days, 30)
            when = f"overdue by {-days} day{'s' if days != -1 else ''}"
        elif days == 0:
            urgency, when = 90, "due today"
        elif days == 1:
            urgency, when = 75, "due tomorrow"
        else:
            urgency, when = max(0, 80 - days * 5), f"due in {days} days"
    return urgency + prio * 10, f"{task.priority.capitalize()} priority, {when}"


def _suggest(ctx: ToolContext, a: SuggestArgs) -> dict[str, Any]:
    owner_id = _resolve_owner(ctx, a.scope, None, default_all_for_admin=False)
    f = TaskFilters(status=TaskStatus.PENDING.value, sort_by="due_date", order="asc", page=1, page_size=500)
    items, total = task_service.list_tasks(ctx.db, f, owner_id=owner_id)
    scored = sorted(
        ((*_rank(t, ctx.today), t) for t in items),
        key=lambda x: (-x[0], x[2].due_date or date.max, x[2].id),
    )[: a.limit]
    cards = [to_card(ctx, t, ctx.today, reason=reason) for _, reason, t in scored]
    ctx.cards = cards
    if not cards:
        return {"today": ctx.today.isoformat(), "pending_total": 0, "tasks": [], "note": "There are no pending tasks."}
    return {
        "today": ctx.today.isoformat(),
        "pending_total": total,
        "tasks": [_task_for_llm(c) for c in cards],
        "ranking": "overdue first, then nearest due date, then priority",
    }


def _count(db: Session, *conditions) -> int:
    return db.scalar(select(func.count(Task.id)).where(*conditions)) or 0


def _stats(ctx: ToolContext, a: StatsArgs) -> dict[str, Any]:
    owner_id = _resolve_owner(ctx, a.scope, a.owner_user_id, default_all_for_admin=True)
    base = [Task.user_id == owner_id] if owner_id is not None else []
    pending = Task.status == TaskStatus.PENDING.value
    today = ctx.today
    stats: dict[str, Any] = {
        "scope": "all users" if owner_id is None else ("your tasks" if owner_id == ctx.user.id else f"user #{owner_id}"),
        "total_tasks": _count(ctx.db, *base),
        "pending_tasks": _count(ctx.db, *base, pending),
        "completed_tasks": _count(ctx.db, *base, Task.status == TaskStatus.COMPLETED.value),
        "overdue_tasks": _count(ctx.db, *base, pending, Task.due_date < today),
        "high_priority_pending": _count(ctx.db, *base, pending, Task.priority == "high"),
        "due_today": _count(ctx.db, *base, pending, Task.due_date == today),
        "due_next_7_days": _count(ctx.db, *base, pending, Task.due_date >= today, Task.due_date <= today + timedelta(days=7)),
    }
    if owner_id is None:  # only reachable by admins (see _resolve_owner)
        stats["total_users"] = ctx.db.scalar(select(func.count(User.id))) or 0
        stats["active_users"] = ctx.db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0
    ctx.stats = stats
    return {"today": today.isoformat(), "stats": stats}


def _find_users(ctx: ToolContext, a: FindUsersArgs) -> dict[str, Any]:
    if not ctx.user.is_admin:
        raise ToolError("Only administrators can look up other users.")
    stmt = select(User).order_by(User.id).limit(a.limit)
    if a.query:
        like = f"%{a.query.strip()}%"
        stmt = stmt.where(User.full_name.ilike(like) | User.email.ilike(like))
    users = ctx.db.scalars(stmt).all()
    return {
        "users": [
            {"id": u.id, "name": u.full_name, "email": u.email, "role": u.role, "active": u.is_active} for u in users
        ]
    }


# --------------------------------------------------------------------------- write tools (staging only)
def stage_write_tool(ctx: ToolContext, name: str, arguments: dict[str, Any]) -> StagedAction:
    """Validate a create/update/delete request and describe it. Does NOT touch the database.
    Raises ToolError if the request is invalid or not permitted."""
    if name == "create_task":
        return _stage_create(ctx, _validate(CreateTaskArgs, arguments))
    if name == "update_task":
        return _stage_update(ctx, _validate(UpdateTaskArgs, arguments))
    if name == "delete_task":
        return _stage_delete(ctx, _validate(DeleteTaskArgs, arguments))
    raise ToolError(f"Unknown tool '{name}'.")


def _check_future(ctx: ToolContext, due: date | None) -> None:
    if due is not None and due < ctx.today:
        raise ToolError(
            f"Due date {due.isoformat()} is in the past (today is {ctx.today.isoformat()}). "
            "Ask the user which date they mean."
        )


def _owner_for_create(ctx: ToolContext, owner_user_id: int | None) -> User:
    if owner_user_id is None or owner_user_id == ctx.user.id:
        return ctx.user
    if not ctx.user.is_admin:
        raise ToolError("You are only allowed to create tasks for yourself.")
    owner = ctx.db.get(User, owner_user_id)
    if owner is None:
        raise ToolError(f"User #{owner_user_id} does not exist.")
    return owner


def _stage_create(ctx: ToolContext, a: CreateTaskArgs) -> StagedAction:
    _check_future(ctx, a.due_date)
    owner = _owner_for_create(ctx, a.owner_user_id)
    fields = {
        "title": a.title,
        "description": a.description,
        "priority": a.priority,
        "due_date": a.due_date.isoformat() if a.due_date else None,
    }
    try:
        TaskCreate(**fields)  # the same validation the normal API applies
    except ValidationError as exc:
        raise ToolError(f"Invalid task - {exc.errors()[0]['msg']}")
    due = a.due_date.isoformat() if a.due_date else "no due date"
    summary = f'Create task "{a.title}" (priority {a.priority}, due {due})'
    if owner.id != ctx.user.id:
        summary += f" for {owner.full_name}"
    card = ChatTaskCard(
        id=0, title=a.title, description=a.description, priority=a.priority, status="pending",
        due_date=a.due_date, owner_id=owner.id if ctx.user.is_admin else None,
        owner_name=owner.full_name if ctx.user.is_admin else None,
    )
    return StagedAction("create_task", {"fields": fields, "owner_user_id": owner.id}, summary, False, card)


def _stage_update(ctx: ToolContext, a: UpdateTaskArgs) -> StagedAction:
    task = _get_task(ctx, a.task_id)  # fresh read + permission check
    if a.due_date is not None and a.clear_due_date:
        raise ToolError("Provide either due_date or clear_due_date, not both.")
    _check_future(ctx, a.due_date)

    wanted: dict[str, Any] = {}
    if a.title is not None:
        wanted["title"] = a.title.strip()
    if a.description is not None:
        wanted["description"] = a.description
    if a.priority is not None:
        wanted["priority"] = a.priority
    if a.status is not None:
        wanted["status"] = a.status
    if a.due_date is not None:
        wanted["due_date"] = a.due_date
    elif a.clear_due_date:
        wanted["due_date"] = None
    if not wanted:
        raise ToolError("No changes were specified.")

    changes: dict[str, Any] = {}
    parts: list[str] = []
    for key, new in wanted.items():
        old = getattr(task, key)
        if old == new:
            continue
        changes[key] = new.isoformat() if isinstance(new, date) else new
        show = lambda v: "none" if v in (None, "") else (v.isoformat() if isinstance(v, date) else str(v))  # noqa: E731
        if key == "description":
            parts.append("description updated")
        else:
            parts.append(f"{key.replace('_', ' ')}: {show(old)} → {show(new)}")
    if not changes:
        raise ToolError(f'Task #{task.id} "{task.title}" already has those values. Tell the user nothing needs to change.')
    try:
        TaskUpdate(**changes)
    except ValidationError as exc:
        raise ToolError(f"Invalid change - {exc.errors()[0]['msg']}")

    summary = f'Update task #{task.id} "{task.title}": ' + "; ".join(parts)
    if ctx.user.is_admin and task.user_id != ctx.user.id and task.owner:
        summary += f" (owner: {task.owner.full_name})"
    payload = {"task_id": task.id, "changes": changes, "stamp": stamp(task)}
    return StagedAction("update_task", payload, summary, False, to_card(ctx, task, ctx.today))


def _stage_delete(ctx: ToolContext, a: DeleteTaskArgs) -> StagedAction:
    task = _get_task(ctx, a.task_id)
    summary = f'Delete task #{task.id} "{task.title}" permanently'
    if ctx.user.is_admin and task.user_id != ctx.user.id and task.owner:
        summary += f" (owner: {task.owner.full_name})"
    payload = {"task_id": task.id, "stamp": stamp(task)}
    return StagedAction("delete_task", payload, summary, True, to_card(ctx, task, ctx.today))

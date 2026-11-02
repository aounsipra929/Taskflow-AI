"""Business logic for tasks: filtering, sorting, pagination and CRUD."""
from dataclasses import dataclass
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.task import Task
from app.models.user import User

# Semantic ordering for priority (alphabetical order would be wrong).
PRIORITY_RANK = case({"low": 1, "medium": 2, "high": 3}, value=Task.priority)


@dataclass
class TaskFilters:
    q: str | None = None
    status: str | None = None
    priority: str | None = None
    due_from: date | None = None
    due_to: date | None = None
    sort_by: str = "created_at"
    order: str = "desc"
    page: int = 1
    page_size: int = 10


def list_tasks(db: Session, f: TaskFilters, owner_id: int | None = None):
    """Return (tasks, total). owner_id=None means tasks of every user (admin)."""
    conditions = []
    if owner_id is not None:
        conditions.append(Task.user_id == owner_id)
    if f.q:
        like = f"%{f.q.strip()}%"
        conditions.append(or_(Task.title.ilike(like), Task.description.ilike(like)))
    if f.status:
        conditions.append(Task.status == f.status)
    if f.priority:
        conditions.append(Task.priority == f.priority)
    if f.due_from:
        conditions.append(Task.due_date >= f.due_from)
    if f.due_to:
        conditions.append(Task.due_date <= f.due_to)

    total = db.scalar(select(func.count(Task.id)).where(*conditions)) or 0

    sort_column = {
        "due_date": Task.due_date,
        "created_at": Task.created_at,
        "priority": PRIORITY_RANK,
    }[f.sort_by]
    ordered = sort_column.asc() if f.order == "asc" else sort_column.desc()
    if f.sort_by == "due_date":
        ordered = ordered.nulls_last()

    stmt = (
        select(Task)
        .options(joinedload(Task.owner))
        .where(*conditions)
        .order_by(ordered, Task.id.desc())  # id as a stable tie-breaker
        .offset((f.page - 1) * f.page_size)
        .limit(f.page_size)
    )
    return list(db.scalars(stmt).unique()), total


def get_task_for_user(db: Session, task_id: int, user: User) -> Task:
    """Admins can access any task; users only their own (404 hides existence)."""
    task = db.scalar(select(Task).options(joinedload(Task.owner)).where(Task.id == task_id))
    if task is None or (not user.is_admin and task.user_id != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task


def create_task(db: Session, data: dict, owner_id: int) -> Task:
    task = Task(**data, user_id=owner_id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task(db: Session, task: Task, data: dict) -> Task:
    for key, value in data.items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task: Task) -> None:
    db.delete(task)
    db.commit()

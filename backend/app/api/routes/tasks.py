from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, task_filters
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.task import TaskCreate, TaskRead, TaskStatusUpdate, TaskUpdate
from app.services import task_service
from app.services.task_service import TaskFilters

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=Page[TaskRead])
def list_my_tasks(
    filters: TaskFilters = Depends(task_filters),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List the caller's own tasks with search, filters, sorting and pagination."""
    items, total = task_service.list_tasks(db, filters, owner_id=user.id)
    return Page.create(items, total, filters.page, filters.page_size)


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return task_service.create_task(db, payload.model_dump(), owner_id=user.id)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return task_service.get_task_for_user(db, task_id, user)


@router.put("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = task_service.get_task_for_user(db, task_id, user)
    return task_service.update_task(db, task, payload.model_dump(exclude_unset=True))


@router.patch("/{task_id}/status", response_model=TaskRead)
def set_task_status(
    task_id: int,
    payload: TaskStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark a task completed or pending."""
    task = task_service.get_task_for_user(db, task_id, user)
    return task_service.update_task(db, task, {"status": payload.status})


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = task_service.get_task_for_user(db, task_id, user)
    task_service.delete_task(db, task)

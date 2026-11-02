"""Admin-only endpoints. The router-level dependency enforces the admin role."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin, task_filters
from app.db.session import get_db
from app.models.enums import Role, TaskStatus
from app.models.task import Task
from app.models.user import User
from app.schemas.common import Page
from app.schemas.task import AdminTaskCreate, DashboardStats, TaskRead
from app.schemas.user import AdminUserRead, UserStatusUpdate
from app.services import task_service
from app.services.task_service import TaskFilters

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db)):
    count = lambda *cond: db.scalar(select(func.count(Task.id)).where(*cond)) or 0  # noqa: E731
    return DashboardStats(
        total_users=db.scalar(select(func.count(User.id))) or 0,
        active_users=db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0,
        total_tasks=count(),
        completed_tasks=count(Task.status == TaskStatus.COMPLETED.value),
        pending_tasks=count(Task.status == TaskStatus.PENDING.value),
    )


@router.get("/users", response_model=Page[AdminUserRead])
def list_users(
    q: str | None = Query(None, max_length=100),
    role: Role | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    conditions = []
    if q:
        like = f"%{q.strip()}%"
        conditions.append(or_(User.email.ilike(like), User.full_name.ilike(like)))
    if role:
        conditions.append(User.role == role.value)
    if is_active is not None:
        conditions.append(User.is_active.is_(is_active))

    total = db.scalar(select(func.count(User.id)).where(*conditions)) or 0
    rows = db.execute(
        select(User, func.count(Task.id))
        .outerjoin(Task, Task.user_id == User.id)
        .where(*conditions)
        .group_by(User.id)
        .order_by(User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [AdminUserRead.model_validate(u).model_copy(update={"task_count": n}) for u, n in rows]
    return Page.create(items, total, page, page_size)


@router.get("/users/{user_id}", response_model=AdminUserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    n = db.scalar(select(func.count(Task.id)).where(Task.user_id == user_id)) or 0
    return AdminUserRead.model_validate(user).model_copy(update={"task_count": n})


@router.patch("/users/{user_id}/status", response_model=AdminUserRead)
def set_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Activate / deactivate an account. Admins cannot deactivate themselves."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id and not payload.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate your own account")
    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    n = db.scalar(select(func.count(Task.id)).where(Task.user_id == user_id)) or 0
    return AdminUserRead.model_validate(user).model_copy(update={"task_count": n})


@router.get("/tasks", response_model=Page[TaskRead])
def list_all_tasks(
    user_id: int | None = Query(None, description="Restrict to one user's tasks"),
    filters: TaskFilters = Depends(task_filters),
    db: Session = Depends(get_db),
):
    """Every user's tasks, with the same filters as /tasks."""
    items, total = task_service.list_tasks(db, filters, owner_id=user_id)
    return Page.create(items, total, filters.page, filters.page_size)


@router.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task_for_user(payload: AdminTaskCreate, db: Session = Depends(get_db)):
    if db.get(User, payload.user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    data = payload.model_dump(exclude={"user_id"})
    return task_service.create_task(db, data, owner_id=payload.user_id)

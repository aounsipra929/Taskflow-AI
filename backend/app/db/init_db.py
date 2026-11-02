"""Optional bootstrap: create the first admin account from environment variables."""
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import Role
from app.models.user import User


def create_first_admin() -> None:
    if not (settings.FIRST_ADMIN_EMAIL and settings.FIRST_ADMIN_PASSWORD):
        return
    with SessionLocal() as db:
        email = settings.FIRST_ADMIN_EMAIL.lower()
        if db.scalar(select(User).where(User.email == email)):
            return
        db.add(
            User(
                email=email,
                full_name=settings.FIRST_ADMIN_NAME,
                hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
                role=Role.ADMIN.value,
            )
        )
        db.commit()

# Import models so Alembic / metadata can discover them.
from app.models.task import Task  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.pending_action import PendingAction  # noqa: F401

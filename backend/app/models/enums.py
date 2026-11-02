from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"


class TaskStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

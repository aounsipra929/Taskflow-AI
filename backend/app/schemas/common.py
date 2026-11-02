from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def create(cls, items: list, total: int, page: int, page_size: int) -> "Page":
        return cls(items=items, total=total, page=page, page_size=page_size, pages=ceil(total / page_size) if total else 1)


class Message(BaseModel):
    detail: str

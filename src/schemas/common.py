from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    """DTO chung cho mọi response phân trang."""

    page: int = 1
    limit: int = 20
    total: int = 0
    total_pages: int = 0
    items: list[T] = Field(default_factory=list)
    has_prev: bool = False
    has_next: bool = False

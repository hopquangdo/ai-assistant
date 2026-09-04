"""Offset/limit pagination: the query params in, a page of results out."""
from __future__ import annotations

from typing import Generic, Sequence, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class Page(BaseModel, Generic[T]):
    """One page of ``items`` plus enough metadata for the client to page on."""

    items: list[T]
    page: int
    page_size: int
    total: int

    @property
    def pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size if self.page_size else 0

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @classmethod
    def of(cls, items: Sequence[T], *, total: int, params: PaginationParams) -> "Page[T]":
        return cls(items=list(items), page=params.page, page_size=params.page_size, total=total)


__all__ = ["PaginationParams", "Page"]

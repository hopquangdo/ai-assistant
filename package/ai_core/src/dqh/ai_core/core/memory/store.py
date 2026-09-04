"""``MemoryStore`` — hợp đồng lưu ghi nhớ dài hạn theo ``namespace`` (vd ``"user:123"``).

ABC. ``search`` nhận sẵn ``embedding`` của query (đã tính ngoài) để store làm ngữ nghĩa;
không có thì store tự so khớp từ khoá. Backend (pgvector/Qdrant/…) là INFRA — app viết impl
kế thừa rồi tiêm vào :class:`~dqh.ai_core.core.memory.facade.Memory`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from dqh.ai_core.core.memory.models import MemoryItem

__all__ = ["MemoryStore"]


class MemoryStore(ABC):
    @abstractmethod
    async def put(self, namespace: str, item: MemoryItem, *, embedding: list[float] | None = None) -> None:
        """Ghi (ghi đè theo ``item.key``)."""

    @abstractmethod
    async def get(self, namespace: str, key: str) -> MemoryItem | None: ...

    @abstractmethod
    async def delete(self, namespace: str, key: str) -> None: ...

    @abstractmethod
    async def list(self, namespace: str, *, limit: int = 100) -> list[MemoryItem]:
        """Tất cả item trong namespace, mới nhất trước."""

    @abstractmethod
    async def search(
        self,
        namespace: str,
        query: str,
        *,
        limit: int = 5,
        embedding: list[float] | None = None,
    ) -> list[MemoryItem]:
        """Top-``limit`` item liên quan nhất tới ``query``."""

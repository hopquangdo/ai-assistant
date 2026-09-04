"""``InMemoryMemoryStore`` — impl tham chiếu của :class:`MemoryStore`, lưu RAM.

Search: có ``embedding`` (query) + item đã lưu kèm vector -> cosine top-k. Không thì chấm điểm
theo số từ khoá trùng. Đủ cho dev/test/single-process; prod dùng vector DB (app tự viết impl).
"""
from __future__ import annotations

import asyncio
import math
import re
from typing import Any

from dqh.ai_core.core.memory.models import MemoryItem
from dqh.ai_core.core.memory.store import MemoryStore

__all__ = ["InMemoryMemoryStore"]

_WORD = re.compile(r"\w+", re.UNICODE)


def _tokens(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(text)}


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class InMemoryMemoryStore(MemoryStore):
    def __init__(self) -> None:
        # namespace -> key -> (item, embedding | None)
        self._data: dict[str, dict[str, tuple[MemoryItem, list[float] | None]]] = {}
        self._lock = asyncio.Lock()

    async def put(self, namespace: str, item: MemoryItem, *, embedding: list[float] | None = None) -> None:
        async with self._lock:
            self._data.setdefault(namespace, {})[item.key] = (item, embedding)

    async def get(self, namespace: str, key: str) -> MemoryItem | None:
        async with self._lock:
            entry = self._data.get(namespace, {}).get(key)
            return entry[0] if entry else None

    async def delete(self, namespace: str, key: str) -> None:
        async with self._lock:
            self._data.get(namespace, {}).pop(key, None)

    async def list(self, namespace: str, *, limit: int = 100) -> list[MemoryItem]:
        async with self._lock:
            items = [it for it, _ in self._data.get(namespace, {}).values()]
        items.sort(key=lambda it: it.created_at, reverse=True)
        return items[:limit]

    async def search(
        self,
        namespace: str,
        query: str,
        *,
        limit: int = 5,
        embedding: list[float] | None = None,
    ) -> list[MemoryItem]:
        async with self._lock:
            entries = list(self._data.get(namespace, {}).values())
        if not entries:
            return []

        scored: list[tuple[float, MemoryItem]] = []
        q_tokens = _tokens(query)
        for item, emb in entries:
            if embedding and emb:
                score = _cosine(embedding, emb)
            else:
                overlap = q_tokens & _tokens(item.text)
                score = len(overlap) / max(len(q_tokens), 1)
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda s: s[0], reverse=True)
        return [it for _, it in scored[:limit]]

"""``InMemoryConversationStore`` — ``ConversationStore`` lưu trong RAM tiến trình.

Cho dev/test/single-process. Không bền qua restart, không chia sẻ giữa nhiều worker.
"""
from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from typing import Any, Sequence

from langchain_core.messages import BaseMessage

from dqh.ai_core.core.conversation.store import ConversationStore

__all__ = ["InMemoryConversationStore"]


class _Thread:
    __slots__ = ("messages", "meta", "touched_at")

    def __init__(self) -> None:
        self.messages: list[BaseMessage] = []
        self.meta: dict[str, Any] = {}
        self.touched_at: float = time.time()


class InMemoryConversationStore(ConversationStore):
    """``max_turns``: mỗi lần ghi chỉ giữ N ``HumanMessage`` cuối (kèm message sau chúng).
    ``max_threads``: giới hạn số thread, evict thread cũ nhất (LRU).
    """

    def __init__(self, *, max_turns: int | None = None, max_threads: int | None = None) -> None:
        self._threads: "OrderedDict[str, _Thread]" = OrderedDict()
        self._max_turns = max_turns
        self._max_threads = max_threads
        self._lock = asyncio.Lock()

    async def load(self, thread_id: str) -> list[BaseMessage]:
        async with self._lock:
            t = self._threads.get(thread_id)
            return list(t.messages) if t else []

    async def replace(self, thread_id: str, messages: Sequence[BaseMessage]) -> None:
        async with self._lock:
            self._get(thread_id).messages = self._cap(list(messages))
            self._touch(thread_id)

    async def append(self, thread_id: str, messages: Sequence[BaseMessage]) -> None:
        async with self._lock:
            t = self._get(thread_id)
            t.messages = self._cap([*t.messages, *messages])
            self._touch(thread_id)

    async def get_meta(self, thread_id: str, key: str, default: Any = None) -> Any:
        async with self._lock:
            t = self._threads.get(thread_id)
            return t.meta.get(key, default) if t else default

    async def set_meta(self, thread_id: str, key: str, value: Any) -> None:
        async with self._lock:
            self._get(thread_id).meta[key] = value
            self._touch(thread_id)

    async def clear(self, thread_id: str) -> None:
        async with self._lock:
            self._threads.pop(thread_id, None)

    async def list_threads(self, *, limit: int = 100) -> list[str]:
        async with self._lock:
            return list(reversed(self._threads))[:limit]

    # -- nội bộ -------------------------------------------------------------

    def _get(self, thread_id: str) -> _Thread:
        t = self._threads.get(thread_id)
        if t is None:
            t = self._threads[thread_id] = _Thread()
            if self._max_threads and len(self._threads) > self._max_threads:
                self._threads.popitem(last=False)
        return t

    def _touch(self, thread_id: str) -> None:
        self._threads.move_to_end(thread_id)
        self._threads[thread_id].touched_at = time.time()

    def _cap(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        if not self._max_turns:
            return messages
        human = [i for i, m in enumerate(messages) if m.__class__.__name__ == "HumanMessage"]
        return messages[human[-self._max_turns]:] if len(human) > self._max_turns else messages

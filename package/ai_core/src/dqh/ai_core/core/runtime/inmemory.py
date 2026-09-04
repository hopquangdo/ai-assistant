"""Impl tham chiếu của ``TaskSource`` / ``OutcomeSink`` dùng ``asyncio.Queue`` — cho test & demo."""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

from dqh.ai_core.core.runtime.sink import OutcomeSink
from dqh.ai_core.core.runtime.source import TaskSource
from dqh.ai_core.core.runtime.task import AgentOutcome, AgentTask

__all__ = ["InMemoryTaskSource", "InMemoryOutcomeSink"]

_CLOSED = object()


class InMemoryTaskSource(TaskSource):
    """Đẩy task vào bằng ``put``/``extend``; gọi ``close`` để iterator kết thúc."""

    def __init__(self) -> None:
        self._q: asyncio.Queue = asyncio.Queue()
        self.acked: list[str] = []
        self.nacked: list[tuple[str, bool]] = []

    async def put(self, task: AgentTask) -> None:
        await self._q.put(task)

    async def extend(self, tasks) -> None:
        for t in tasks:
            await self._q.put(t)

    def __aiter__(self) -> AsyncIterator[AgentTask]:
        return self._iter()

    async def _iter(self) -> AsyncIterator[AgentTask]:
        while True:
            item = await self._q.get()
            if item is _CLOSED:
                return
            yield item

    async def ack(self, task: AgentTask) -> None:
        self.acked.append(task.id)

    async def nack(self, task: AgentTask, *, requeue: bool = True) -> None:
        self.nacked.append((task.id, requeue))
        if requeue:
            await self._q.put(task)

    async def close(self) -> None:
        await self._q.put(_CLOSED)


class InMemoryOutcomeSink(OutcomeSink):
    def __init__(self) -> None:
        self.published: list[AgentOutcome] = []

    async def publish(self, outcome: AgentOutcome) -> None:
        self.published.append(outcome)

"""``TaskSource`` — nguồn cấp ``AgentTask`` (Kafka / queue / stream …).

ABC + async-iterator. App viết impl bọc client thật (aiokafka, redis stream, SQS…) rồi tiêm
vào ``AgentWorker``. ``ack``/``nack`` để báo backend đã xử lý xong / cần thử lại.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from dqh.ai_core.core.runtime.task import AgentTask

__all__ = ["TaskSource"]


class TaskSource(ABC):
    @abstractmethod
    def __aiter__(self) -> AsyncIterator[AgentTask]:
        """Lặp bất tận (hoặc tới khi đóng) và ``yield`` từng ``AgentTask``."""

    @abstractmethod
    async def ack(self, task: AgentTask) -> None:
        """Báo backend: task đã xử lý xong, commit offset / xoá khỏi queue."""

    @abstractmethod
    async def nack(self, task: AgentTask, *, requeue: bool = True) -> None:
        """Báo backend: task lỗi. ``requeue=False`` -> bỏ / đẩy sang DLQ (tuỳ backend)."""

    async def close(self) -> None:
        """Đóng nguồn (đóng consumer…). Mặc định no-op."""

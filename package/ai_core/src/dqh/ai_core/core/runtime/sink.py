"""``OutcomeSink`` — nơi đẩy ``AgentOutcome`` sau khi agent xử lý xong.

ABC. App viết impl bọc producer thật (Kafka topic, webhook, DB…). ``outcome.reply_to`` cho
biết đích cụ thể của từng task nếu cần.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from dqh.ai_core.core.runtime.task import AgentOutcome

__all__ = ["OutcomeSink"]


class OutcomeSink(ABC):
    @abstractmethod
    async def publish(self, outcome: AgentOutcome) -> None:
        """Gửi kết quả đi. Ném exception nếu gửi thất bại (worker sẽ nack task tương ứng)."""

    async def close(self) -> None:
        """Đóng sink (flush + đóng producer…). Mặc định no-op."""

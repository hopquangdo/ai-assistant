"""``Embedder`` — hợp đồng nhúng text thành vector, để long-term store search ngữ nghĩa.

App tiêm impl (OpenAI/Cohere/local…). Không có embedder thì store fallback sang so khớp từ khoá.
"""
from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

__all__ = ["Embedder"]


@runtime_checkable
class Embedder(Protocol):
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Trả về 1 vector cho mỗi text, cùng thứ tự."""
        ...

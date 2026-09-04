"""``MemoryItem`` — 1 mẩu ghi nhớ dài hạn (fact, sở thích, ghi chú…)."""
from __future__ import annotations

import time

from pydantic import BaseModel, Field

__all__ = ["MemoryItem"]


class MemoryItem(BaseModel):
    key: str = Field(description="Định danh ổn định (slug) — ghi cùng key sẽ ghi đè")
    text: str = Field(description="Nội dung ghi nhớ, 1 câu ngắn gọn")
    kind: str = Field(default="fact", description="fact | preference | todo | context | …")
    metadata: dict = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)

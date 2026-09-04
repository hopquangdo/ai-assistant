"""``extract_memories`` — dùng LLM rút các mẩu ghi nhớ ĐÁNG LƯU DÀI HẠN từ 1 đoạn hội thoại.

Prompt mặc định trung tính (không gắn ngôn ngữ/nghiệp vụ); truyền ``instruction`` để tuỳ biến.
"""
from __future__ import annotations

import re
from typing import Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, Field

from dqh.ai_core.core.structured import extract
from dqh.ai_core.core.memory.models import MemoryItem

__all__ = ["extract_memories"]

_DEFAULT_INSTRUCTION = (
    "Extract only durable, reusable facts about the user or their ongoing goals/preferences "
    "from the conversation below. Ignore small talk, one-off questions, and anything already "
    "obvious. If nothing is worth remembering, return an empty list. Keep each item to one "
    "short sentence, in the same language as the conversation."
)


class _Extracted(BaseModel):
    text: str = Field(description="One short sentence worth remembering long-term")
    kind: str = Field(default="fact", description="fact | preference | goal | context")


def _slug(text: str, maxlen: int = 48) -> str:
    s = re.sub(r"[^\w]+", "-", text.lower(), flags=re.UNICODE).strip("-")
    return s[:maxlen] or "memory"


def _transcript(messages: Sequence[BaseMessage]) -> str:
    lines = []
    for m in messages:
        who = "User" if isinstance(m, HumanMessage) else "Assistant" if isinstance(m, AIMessage) else m.__class__.__name__
        content = getattr(m, "content", "")
        if content:
            lines.append(f"{who}: {content}")
    return "\n".join(lines)


async def extract_memories(
    llm: BaseChatModel,
    messages: Sequence[BaseMessage],
    *,
    instruction: str = _DEFAULT_INSTRUCTION,
    existing: Sequence[str] = (),
) -> list[MemoryItem]:
    """Trả về ``list[MemoryItem]`` (có thể rỗng). Lỗi LLM -> rỗng."""
    transcript = _transcript(messages)
    if not transcript.strip():
        return []

    known = ("\n\nAlready remembered (do not repeat):\n" + "\n".join(f"- {e}" for e in existing)) if existing else ""
    rows = await extract(
        llm,
        prompt=f"Conversation:\n{transcript}{known}",
        schema=list[_Extracted],
        system=instruction,
        retries=1,
        default=[],
    )
    return [
        MemoryItem(key=_slug(r.text), text=r.text.strip(), kind=r.kind or "fact")
        for r in rows
        if r.text and r.text.strip()
    ]

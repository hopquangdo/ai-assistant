"""``ContextBuilder`` — lắp ráp context cho 1 lượt LLM trong 1 ngân sách token.

Phần cố định (system + ghi nhớ dài hạn + tin nhắn user) được ưu tiên; phần còn lại của
ngân sách dành cho lịch sử hội thoại, cắt từ lượt cũ nhất cho vừa.

    msgs = (
        ContextBuilder(budget=6000)
        .system(system_prompt)
        .memory(recall_snippets)          # từ long-term memory
        .history(prev_messages)
        .user("Câu hỏi mới…")
        .build()
    )
"""
from __future__ import annotations

from typing import Callable, Iterable, Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.messages.utils import count_tokens_approximately

from dqh.ai_core.core.conversation.history import History

__all__ = ["ContextBuilder"]

TokenCounter = Callable[[list[BaseMessage]], int] | BaseChatModel
UserContent = str | list[dict | str]


class ContextBuilder:
    def __init__(self, *, budget: int = 8000, token_counter: TokenCounter | None = None) -> None:
        self._budget = budget
        self._counter = token_counter or count_tokens_approximately
        self._system: str | None = None
        self._memory: list[str] = []
        self._memory_header = "Thông tin đã ghi nhớ, dùng nếu liên quan:"
        self._history: list[BaseMessage] = []
        self._user: UserContent | None = None

    def system(self, text: str | None) -> "ContextBuilder":
        self._system = text or None
        return self

    def memory(self, snippets: Iterable[str], *, header: str | None = None) -> "ContextBuilder":
        self._memory = [s.strip() for s in snippets if s and s.strip()]
        if header is not None:
            self._memory_header = header
        return self

    def history(self, messages: Sequence[BaseMessage]) -> "ContextBuilder":
        self._history = list(messages)
        return self

    def user(self, content: UserContent | None) -> "ContextBuilder":
        self._user = content
        return self

    def build(self) -> list[BaseMessage]:
        head = self._build_system()
        tail: list[BaseMessage] = [HumanMessage(content=self._user)] if self._user is not None else []

        fixed = ([head] if head else []) + tail
        remaining = max(self._budget - self._count(fixed), 0)

        history = self._history
        if history and remaining > 0:
            history = History(history).trim_to_tokens(remaining, token_counter=self._counter).messages
        elif remaining == 0:
            history = []

        return ([head] if head else []) + history + tail

    # -- nội bộ -----------------------------------------------------------

    def _build_system(self) -> SystemMessage | None:
        parts = [p for p in [self._system, self._memory_block()] if p]
        return SystemMessage(content="\n\n".join(parts)) if parts else None

    def _memory_block(self) -> str:
        if not self._memory:
            return ""
        return self._memory_header + "\n" + "\n".join(f"- {s}" for s in self._memory)

    def _count(self, messages: list[BaseMessage]) -> int:
        c = self._counter
        if isinstance(c, BaseChatModel):
            return c.get_num_tokens_from_messages(messages)
        return c(messages)

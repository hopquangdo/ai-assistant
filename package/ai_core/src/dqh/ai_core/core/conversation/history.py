"""``History`` — chuỗi làm sạch ``list[BaseMessage]`` cho hội thoại, fluent.

Các phép biến đổi ĐỒNG BỘ, mỗi method trả về ``self`` để nối chuỗi. Phép cần gọi LLM
(tóm tắt lượt cũ) tách riêng ở ``condense_history`` vì nó bất đồng bộ.

    from dqh.ai_core.core.memory import History

    msgs = (
        History(raw)
        .prune_orphan_tool_calls()
        .keep_recent_turns(12)
        .trim_to_tokens(4000)
        .messages
    )
"""
from __future__ import annotations

from typing import Callable, Iterable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately

__all__ = ["History"]

TokenCounter = Callable[[list[BaseMessage]], int] | BaseChatModel


class History:
    """Bọc 1 danh sách message + các phép làm sạch nối chuỗi. Không đụng list gốc."""

    def __init__(self, messages: Iterable[BaseMessage]) -> None:
        self._msgs: list[BaseMessage] = list(messages)

    # -- kết quả ---------------------------------------------------------------

    @property
    def messages(self) -> list[BaseMessage]:
        """Danh sách sau khi biến đổi (bản sao)."""
        return list(self._msgs)

    def __iter__(self):
        return iter(self._msgs)

    def __len__(self) -> int:
        return len(self._msgs)

    # -- phép biến đổi -------------------------------------------------------

    def prune_orphan_tool_calls(self) -> "History":
        """Bỏ mọi ``AIMessage`` có ``tool_calls`` mà KHÔNG đủ ``ToolMessage`` phản hồi ngay sau.

        Lịch sử hỏng (lượt trước lỗi giữa chừng: timeout, exception, gom SSE thiếu) khiến
        OpenAI/Anthropic trả 400 "tool_calls must be followed by tool messages". Chạy trước
        mỗi lần gọi model để tự dọn, khỏi phải tạo session mới.
        """
        result: list[BaseMessage] = []
        i, n = 0, len(self._msgs)
        while i < n:
            msg = self._msgs[i]
            tool_calls = getattr(msg, "tool_calls", None)
            if isinstance(msg, AIMessage) and tool_calls:
                expected = {c.get("id") for c in tool_calls if c.get("id")}
                collected: list[BaseMessage] = []
                found: set = set()
                j = i + 1
                while j < n and isinstance(self._msgs[j], ToolMessage):
                    collected.append(self._msgs[j])
                    found.add(self._msgs[j].tool_call_id)
                    j += 1
                if expected and expected.issubset(found):
                    result.append(msg)
                    result.extend(collected)
                # thiếu phản hồi -> bỏ cả AIMessage này + ToolMessage lẻ
                i = j
                continue
            result.append(msg)
            i += 1
        self._msgs = result
        return self

    def keep_recent_turns(self, n: int, *, keep_system: bool = True) -> "History":
        """Giữ ``n`` lượt gần nhất (1 lượt = 1 ``HumanMessage`` + mọi message tới trước Human kế tiếp).

        Message hệ thống ở đầu được giữ lại khi ``keep_system=True``.
        """
        if n <= 0:
            self._msgs = []
            return self

        head: list[BaseMessage] = []
        rest = self._msgs
        if keep_system:
            k = 0
            while k < len(rest) and isinstance(rest[k], SystemMessage):
                k += 1
            head, rest = rest[:k], rest[k:]

        human_idx = [i for i, m in enumerate(rest) if m.__class__.__name__ == "HumanMessage"]
        if len(human_idx) > n:
            rest = rest[human_idx[-n]:]
        self._msgs = head + rest
        return self

    def trim_to_tokens(self, max_tokens: int, *, token_counter: TokenCounter | None = None) -> "History":
        """Cắt bớt từ ĐẦU hội thoại cho tới khi tổng token <= ``max_tokens`` (giữ lượt cuối).

        ``token_counter``: hàm đếm, hoặc 1 ``BaseChatModel`` (dùng bộ đếm chính xác của model đó);
        mặc định ``count_tokens_approximately`` của langchain.
        """
        self._msgs = trim_messages(
            self._msgs,
            max_tokens=max_tokens,
            token_counter=token_counter or count_tokens_approximately,
            strategy="last",
            start_on="human",
            include_system=True,
            allow_partial=False,
        )
        return self

"""``Conversation`` — gắn 1 ``Agent`` với 1 ``ConversationStore`` theo ``thread_id``.

Lo phần load lịch sử -> làm sạch (hygiene) -> chạy agent -> lưu lại. Không ép cách streaming:
- ``send()``       : 1 lượt trọn vẹn, không stream.
- ``prepare()``/``commit()`` : cho app tự stream (vd SSE token) rồi lưu.
"""
from __future__ import annotations

from typing import Any, Callable, Sequence

from langchain_core.messages import BaseMessage, HumanMessage

from dqh.ai_core.core.agents.base import Agent
from dqh.ai_core.core.conversation.store import ConversationStore

__all__ = ["Conversation"]

Hygiene = Callable[[list[BaseMessage]], list[BaseMessage]]


class Conversation:
    def __init__(
        self,
        agent: Agent,
        store: ConversationStore,
        thread_id: str,
        *,
        hygiene: Hygiene = lambda messages: messages,
        prelude: Sequence[BaseMessage] | Callable[[], Sequence[BaseMessage]] = (),
    ) -> None:
        """``hygiene``: hàm làm sạch lịch sử trước mỗi lượt (vd ``lambda m: History(m).prune_orphan_tool_calls().messages``).
        ``prelude``: message chèn TRƯỚC lịch sử mỗi lần chạy nhưng KHÔNG lưu (vd tiêm ngày hiện tại)."""
        self.agent = agent
        self.store = store
        self.thread_id = thread_id
        self._hygiene = hygiene
        self._prelude = prelude

    # -- đọc/ghi thô ---------------------------------------------------------

    async def history(self) -> list[BaseMessage]:
        return await self.store.load(self.thread_id)

    async def reset(self) -> None:
        await self.store.clear(self.thread_id)

    async def get_meta(self, key: str, default: Any = None) -> Any:
        return await self.store.get_meta(self.thread_id, key, default)

    async def set_meta(self, key: str, value: Any) -> None:
        await self.store.set_meta(self.thread_id, key, value)

    # -- cho app tự stream -------------------------------------------------

    async def prepare(self, text: str) -> tuple[list[BaseMessage], list[BaseMessage]]:
        """Trả về ``(persisted, graph_input)``:

        - ``persisted``   : lịch sử đã làm sạch + ``HumanMessage(text)`` — cái sẽ được lưu.
        - ``graph_input`` : ``prelude`` + ``persisted`` — cái đưa vào ``agent.graph``.
        """
        history = self._hygiene(await self.store.load(self.thread_id))
        persisted = [*history, HumanMessage(content=text)]
        return persisted, [*self._resolve_prelude(), *persisted]

    async def commit(self, persisted_before: list[BaseMessage], new_messages: Sequence[BaseMessage]) -> None:
        """Lưu ``persisted_before + new_messages`` làm lịch sử mới của thread."""
        await self.store.replace(self.thread_id, [*persisted_before, *new_messages])

    # -- 1 lượt trọn vẹn -------------------------------------------------

    async def send(self, text: str, *, config: dict | None = None) -> list[BaseMessage]:
        """Chạy 1 lượt ReAct, lưu lịch sử, trả về CÁC MESSAGE MỚI (tool call, tool result, câu trả lời)."""
        persisted, graph_input = await self.prepare(text)
        out = await self.agent.graph.ainvoke({"messages": graph_input}, config=config)
        new_messages = out["messages"][len(graph_input):]
        await self.commit(persisted, new_messages)
        return new_messages

    # -- nội bộ ---------------------------------------------------------------

    def _resolve_prelude(self) -> list[BaseMessage]:
        p = self._prelude
        return list(p() if callable(p) else p)

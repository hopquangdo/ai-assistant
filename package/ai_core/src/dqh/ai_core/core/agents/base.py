from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent

from dqh.ai_core.adapters.llm_factory import get_chat_model
from dqh.ai_core.core.agents.stream import stream_agent
from dqh.ai_core.core.observability import Usage, UsageTracker, model_name_of

UserContent = str | list[dict | str]


@dataclass
class Agent:
    """A thin, reusable wrapper around a LangGraph ReAct agent.

    `Agent.create(tools=..., model=..., system=...)` gives you a runnable that
    loops: model -> tool calls -> tool results -> model, until the model stops
    calling tools. Any LangChain `BaseTool` works; nothing here knows about a
    specific task.
    """

    model: BaseChatModel
    tools: list[BaseTool]
    system: str = ""
    graph: Any = field(default=None, repr=False)
    usage: Usage | None = field(default=None, repr=False)

    @classmethod
    def create(
        cls,
        tools: Iterable[BaseTool],
        *,
        model: str | BaseChatModel | None = None,
        system: str = "",
        checkpointer: Any | None = None,
        **model_kwargs: Any,
    ) -> "Agent":
        chat = model if isinstance(model, BaseChatModel) else get_chat_model(model, **model_kwargs)
        tool_list = list(tools)
        graph = create_react_agent(
            chat,
            tool_list,
            prompt=system or None,
            checkpointer=checkpointer,
        )
        return cls(model=chat, tools=tool_list, system=system, graph=graph)

    def _input(self, user_content: UserContent, history: Sequence[AnyMessage] | None) -> dict:
        msgs: list[AnyMessage] = list(history or [])
        msgs.append(HumanMessage(content=user_content))
        return {"messages": msgs}

    def _with_tracking(self, config: dict | None, track: bool) -> dict | None:
        if not track:
            return config
        self.usage = Usage(model=model_name_of(self.model))
        cfg = dict(config or {})
        cfg["callbacks"] = [*cfg.get("callbacks", []), UsageTracker(self.usage)]
        return cfg

    async def run(
        self,
        user_content: UserContent,
        *,
        history: Sequence[AnyMessage] | None = None,
        config: dict | None = None,
        track: bool = False,
    ) -> list[BaseMessage]:
        """Chạy 1 lượt ReAct đầy đủ (không stream). ``track=True`` -> ``self.usage`` (token + cost).

        Muốn stream event token/tool thì dùng :meth:`astream`.
        """
        cfg = self._with_tracking(config, track)
        out = await self.graph.ainvoke(self._input(user_content, history), config=cfg)
        return out["messages"]

    async def stream_values(
        self,
        user_content: UserContent,
        *,
        history: Sequence[AnyMessage] | None = None,
        config: dict | None = None,
    ):
        """Async iterator: danh sách message sau mỗi bước graph (``stream_mode='values'``)."""
        async for chunk in self.graph.astream(
            self._input(user_content, history), config=config, stream_mode="values"
        ):
            yield chunk

    def astream(
        self,
        user_content: UserContent,
        *,
        history: Sequence[AnyMessage] | None = None,
        config: dict | None = None,
        track: bool = False,
        recursion_fallback: str = "",
    ):
        """Async iterator các ``AgentEvent`` đã chuẩn hoá (token / tool / message / done / error).

        Xem :mod:`dqh.ai_core.core.agents.stream`. ``track=True`` gắn ``UsageTracker`` -> ``self.usage``.
        """
        cfg = self._with_tracking(config, track)
        return stream_agent(
            self.graph, self._input(user_content, history), config=cfg,
            recursion_fallback=recursion_fallback,
        )

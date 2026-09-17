import asyncio
import logging
from typing import List

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.errors import GraphRecursionError

from src.agents.nodes.node_base import Node
from src.agents.nodes.react.prompt import SELECT_PROMPT
from src.agents.nodes.react.schema import ToolCall
from src.agents.nodes.react.state import ReActState
from src.core.constants import AGENT_RECURSION_LIMIT, RECURSION_LIMIT_FALLBACK_TEXT
from src.infrastructure.llm_client import llm_client_factory
from src.schemas.stream import StreamEvent, StreamEventName
from src.utils import dispatch_custom_event

logger = logging.getLogger("chatbot.agent.react")


class ReActNode(Node):
    """Loop model -> tool_calls -> tool result, without writing the final answer."""

    def __init__(self, tools: list[BaseTool]):
        self._tools = tools
        self._tools_by_name = {tool.name: tool for tool in tools}
        self._models: dict[str | None, Runnable] = {}
        self.__tool_semaphore = asyncio.Semaphore(8)

    name = "react"
    default_model = "gpt-5.6-luna"

    def _model_for(self, model: str | None) -> Runnable:
        resolved_model = llm_client_factory.resolve_node_model(model, self.default_model)
        if resolved_model not in self._models:
            self._models[resolved_model] = llm_client_factory.get_chat_model(resolved_model).bind_tools(self._tools)
        return self._models[resolved_model]

    async def _execute_tool(self, call: ToolCall, config: RunnableConfig) -> ToolMessage:
        tool = self._tools_by_name[call["name"]]
        try:
            async with self.__tool_semaphore:
                result = await tool.ainvoke(
                    call["args"],
                    config=config,
                )
        except Exception as exc:  # noqa: BLE001
            result = f"Tool error: {exc}"
        return ToolMessage(
            content=str(result),
            tool_call_id=call["id"],
            name=call["name"]
        )

    """
                 ┌── tool A ── 2s ──┐
    LLM ──────────┼── tool B ── 3s ──┼── LLM
                 └── tool C ── 1s ──┘
                        ↓
                      ~3s
    """

    async def __call_tools(
            self, calls: List[ToolCall], config: RunnableConfig
    ):
        return list(
            await asyncio.gather(
                *(self._execute_tool(call, config) for call in calls),
            )
        )

    async def __call__(self, state: ReActState, config: RunnableConfig) -> dict:
        model = (config.get("configurable") or {}).get("model")
        messages = [SystemMessage(content=SELECT_PROMPT), *state["messages"]]
        new_messages: list[AIMessage | ToolMessage] = []
        new_tool_calls: list[dict] = []
        iterations = 0

        try:
            for _ in range(AGENT_RECURSION_LIMIT):
                iterations += 1
                ai_message = await self._model_for(model).ainvoke(messages, config=config)
                logger.info(
                    "react model result tool_calls=%s content=%r",
                    [call["name"] for call in ai_message.tool_calls],
                    ai_message.content,
                )
                if not ai_message.tool_calls:
                    break
                new_messages.append(ai_message)
                messages.append(ai_message)
                new_tool_calls.extend(
                    {"name": call["name"], "args": call["args"]} for call in ai_message.tool_calls
                )

                await dispatch_custom_event(
                    StreamEvent(
                        name=StreamEventName.TOOL_START,
                        payload={
                            "node": self.name,
                            "tools": [
                                {"name": call["name"], "args": call["args"]}
                                for call in ai_message.tool_calls
                            ],
                        },
                    ),
                    config,
                )

                tool_messages = await self.__call_tools(
                    ai_message.tool_calls,
                    config,
                )

                new_messages.extend(tool_messages)
                messages.extend(tool_messages)
            else:
                return {
                    "messages": [AIMessage(content=RECURSION_LIMIT_FALLBACK_TEXT)],
                    "recursion_hit": True,
                    "react_iterations": state.get("react_iterations", 0) + iterations,
                }
        except GraphRecursionError:
            return {
                "messages": [AIMessage(content=RECURSION_LIMIT_FALLBACK_TEXT)],
                "recursion_hit": True,
                "react_iterations": state.get("react_iterations", 0) + iterations,
            }

        return {
            "messages": new_messages,
            "recursion_hit": False,
            "react_iterations": state.get("react_iterations", 0) + iterations,
            "tool_calls_history": [*state.get("tool_calls_history", []), *new_tool_calls],
        }

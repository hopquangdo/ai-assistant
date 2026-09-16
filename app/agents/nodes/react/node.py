from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.errors import GraphRecursionError

from app.agents.nodes.node_base import Node
from app.agents.nodes.react.prompt import SELECT_PROMPT
from app.agents.nodes.react.schema import ToolCall
from app.core.constants import AGENT_RECURSION_LIMIT, RECURSION_LIMIT_FALLBACK_TEXT
from app.llm.client import get_chat_model, resolve_node_model


class ReActNode(Node):
    """Loop model -> tool_calls -> tool result, without writing the final answer."""

    def __init__(self, tools: list[BaseTool]):
        self._tools = tools
        self._tools_by_name = {tool.name: tool for tool in tools}
        self._models: dict[str | None, Runnable] = {}
    name = "react"
    default_model = "gpt-5.6-luna"

    def _model_for(self, model: str | None) -> Runnable:
        resolved_model = resolve_node_model(model, self.default_model)
        if resolved_model not in self._models:
            self._models[resolved_model] = get_chat_model(resolved_model).bind_tools(self._tools)
        return self._models[resolved_model]

    async def _call_tool(self, call: ToolCall, config: RunnableConfig) -> ToolMessage:
        tool = self._tools_by_name[call["name"]]
        try:
            result = await tool.ainvoke(call["args"], config=config)
        except Exception as exc:  # noqa: BLE001
            result = f"Tool error: {exc}"
        return ToolMessage(content=str(result), tool_call_id=call["id"], name=call["name"])

    async def __call__(self, state: dict, config: RunnableConfig) -> dict:
        model = (config.get("configurable") or {}).get("model")
        messages = [SystemMessage(content=SELECT_PROMPT), *state["messages"]]
        new_messages: list[AIMessage | ToolMessage] = []

        try:
            for _ in range(AGENT_RECURSION_LIMIT):
                ai_message = await self._model_for(model).ainvoke(messages, config=config)
                if not ai_message.tool_calls:
                    break
                new_messages.append(ai_message)
                messages.append(ai_message)
                for call in ai_message.tool_calls:
                    tool_message = await self._call_tool(call, config)
                    new_messages.append(tool_message)
                    messages.append(tool_message)
            else:
                return {"messages": [AIMessage(content=RECURSION_LIMIT_FALLBACK_TEXT)], "recursion_hit": True}
        except GraphRecursionError:
            return {"messages": [AIMessage(content=RECURSION_LIMIT_FALLBACK_TEXT)], "recursion_hit": True}

        return {"messages": new_messages, "recursion_hit": False}

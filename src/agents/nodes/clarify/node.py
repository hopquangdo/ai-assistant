from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.utils.function_calling import convert_to_openai_tool

from src.agents.nodes.clarify.prompt import CLARIFY_PROMPT
from src.agents.nodes.clarify.schema import ClarifyDecision
from src.agents.nodes.node_base import Node
from src.infrastructure.llm_client import llm_client_factory
from src.schemas.stream import StreamEvent, StreamEventName
from src.utils import dispatch_custom_event

_CLARIFY_SCHEMA = convert_to_openai_tool(ClarifyDecision)["function"]


class ClarifyNode(Node):
    """Kiá»ƒm tra tham sá»‘ báº¯t buá»™c trÆ°á»›c khi ReAct gá»i tool."""

    name = "clarify"
    default_model = "gpt-5.4-nano"

    def __init__(self, tools: list):
        self._tool_catalog = "\n\n".join(
            f"- {tool.name}: {tool.description}" for tool in tools
        )
        self._default_model_name = llm_client_factory.resolve_node_model("auto", self.default_model)
        self._models: dict[str | None, Runnable] = {
            self._default_model_name: self._build_model(self._default_model_name),
        }

    @staticmethod
    def _build_model(model_name: str | None) -> Runnable:
        return llm_client_factory.get_chat_model(model_name).with_structured_output(_CLARIFY_SCHEMA)

    def _model_for(self, requested_model: str | None) -> Runnable:
        resolved_model = llm_client_factory.resolve_node_model(requested_model, self.default_model)
        if resolved_model not in self._models:
            self._models[resolved_model] = self._build_model(resolved_model)
        return self._models[resolved_model]

    async def __call__(self, state: dict, config: RunnableConfig) -> dict:
        requested_model = (config.get("configurable") or {}).get("model")
        model = self._model_for(requested_model)
        messages = [
            SystemMessage(content=CLARIFY_PROMPT),
            SystemMessage(content=f"Danh má»¥c tool hiá»‡n cÃ³:\n{self._tool_catalog}"),
            *state["messages"],
        ]
        partial: dict = {}
        streamed_reply = ""
        response_started = False
        async for chunk in model.astream(messages, config=config):
            chunk_data = chunk.model_dump() if isinstance(chunk, ClarifyDecision) else chunk
            if not isinstance(chunk_data, dict):
                continue
            partial.update({key: value for key, value in chunk_data.items() if value is not None})
            reply_so_far = str(partial.get("reply") or "")
            if len(reply_so_far) > len(streamed_reply):
                if not response_started:
                    await dispatch_custom_event(
                        StreamEvent(name=StreamEventName.NODE_START, payload={"node": self.name}),
                        config,
                    )
                    response_started = True
                delta = reply_so_far[len(streamed_reply):]
                streamed_reply = reply_so_far
                await dispatch_custom_event(
                    StreamEvent(name=StreamEventName.NODE_DELTA, payload={"node": self.name, "content": delta}),
                    config,
                )

        raw_decision = partial
        decision = (
            ClarifyDecision.model_validate(raw_decision)
            if isinstance(raw_decision, dict)
            else raw_decision
        )
        if decision.needs_clarification:
            reply = decision.reply.strip() or "Anh/chá»‹ vui lÃ²ng bá»• sung thÃ´ng tin cáº§n thiáº¿t Ä‘á»ƒ tÃ´i tra cá»©u chÃ­nh xÃ¡c."
            await self._complete_stream(reply, response_started, config)
            return {
                "messages": [AIMessage(content=reply)],
                "clarification_needed": True,
                "needs_react": False,
            }

        if not decision.needs_react:
            reply = decision.reply.strip() or "ChÃ o anh/chá»‹! TÃ´i cÃ³ thá»ƒ há»— trá»£ tra cá»©u thÃ´ng tin nghiá»‡p vá»¥."
            await self._complete_stream(reply, response_started, config)
            return {
                "messages": [AIMessage(content=reply)],
                "clarification_needed": False,
                "needs_react": False,
            }

        return {
            "clarification_needed": False,
            "needs_react": True,
        }

    async def _complete_stream(self, text: str, response_started: bool, config: RunnableConfig) -> None:
        if not response_started:
            await dispatch_custom_event(
                StreamEvent(name=StreamEventName.NODE_START, payload={"node": self.name}),
                config,
            )
        await dispatch_custom_event(
            StreamEvent(
                name=StreamEventName.NODE_COMPLETED,
                payload={"node": self.name, "answer": text, "should_generate_chart": False},
            ),
            config,
        )


import logging

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from src.agents.nodes.genchart.prompt import CHART_PROMPT
from src.agents.nodes.genchart.schema import ChartDecision, ChartPayload
from src.agents.nodes.node_base import Node
from src.infrastructure.llm_client import llm_client_factory

logger = logging.getLogger("chatbot.agent.genchart")


class GenChartNode(Node):
    def __init__(self):
        self._models = {}
    name = "genchart"
    default_model = "gpt-5.4-nano"

    def _model_for(self, model: str | None):
        resolved_model = llm_client_factory.resolve_node_model(model, self.default_model)
        if resolved_model not in self._models:
            self._models[resolved_model] = llm_client_factory.get_chat_model(resolved_model).with_structured_output(ChartDecision)
        return self._models[resolved_model]

    async def __call__(self, state: dict, config: RunnableConfig) -> dict:
        try:
            model = (config.get("configurable") or {}).get("model")
            tool_messages = [
                SystemMessage(content=f"TOOL RESULT:\n{message.content}")
                for message in state["messages"]
                if isinstance(message, ToolMessage)
            ]
            decision: ChartDecision = await self._model_for(model).ainvoke(
                [SystemMessage(content=CHART_PROMPT), *tool_messages], config=config
            )
            if not decision.has_chart:
                return {"charts": []}
            return {
                "charts": [ChartPayload(spec=chart).model_dump() for chart in decision.charts]
            }
        except Exception:
            logger.warning("genchart failed; continuing without chart", exc_info=True)
            return {"charts": []}


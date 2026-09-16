import logging

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from app.agents.nodes.genchart.prompt import CHART_PROMPT
from app.agents.nodes.genchart.schema import ChartDecision, ChartPayload
from app.agents.nodes.node_base import Node
from app.core.constants import AGENT_MODEL
from app.llm.client import get_chat_model

logger = logging.getLogger("chatbot.agent.genchart")


class GenChartNode(Node):
    def __init__(self):
        self._models = {}

    def _model_for(self, model: str | None):
        if model not in self._models:
            self._models[model] = get_chat_model(model or AGENT_MODEL).with_structured_output(ChartDecision)
        return self._models[model]

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

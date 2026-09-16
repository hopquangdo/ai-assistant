import logging

from langchain_core.messages import SystemMessage
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
            decision: ChartDecision = await self._model_for(model).ainvoke(
                [SystemMessage(content=CHART_PROMPT), *state["messages"]], config=config
            )
            if not decision.has_chart or decision.chart is None:
                return {"chart": None}
            return {"chart": ChartPayload(spec=decision.chart).model_dump()}
        except Exception:
            logger.warning("genchart failed; continuing without chart", exc_info=True)
            return {"chart": None}

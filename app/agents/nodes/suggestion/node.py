import logging
import inspect

from dqh.ai_core import extract
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from app.agents.nodes.node_base import Node
from app.agents.nodes.suggestion.prompt import SUGGESTION_PROMPT
from app.agents.nodes.suggestion.schema import Suggestion
from app.core.config import get_settings
from app.core.constants import AGENT_MODEL
from app.llm.client import get_chat_model

logger = logging.getLogger("chatbot.agent.suggestion")


class SuggestionNode(Node):
    def _context(self, history: list) -> list:
        out: list = []
        for message in history:
            role = message.get("role") if isinstance(message, dict) else getattr(message, "type", None)
            content = message.get("content") if isinstance(message, dict) else getattr(message, "content", "")
            if not content or role not in ("user", "assistant", "human", "ai"):
                continue
            message_type = HumanMessage if role in ("user", "human") else AIMessage
            out.append(message_type(content=str(content)[:2000]))
        return out[-6:]

    async def __call__(self, state: dict, config: RunnableConfig) -> dict:
        messages = state.get("messages", [])
        reply = str(getattr(messages[-1], "content", "") or "") if messages else ""
        if not get_settings().enable_followups or not reply.strip():
            return {"suggestions": []}
        model_name = (config.get("configurable") or {}).get("model") or AGENT_MODEL
        try:
            extract_kwargs = {
                "prompt": f"Câu trả lời vừa rồi:\n{reply[:3000]}\n\nGợi ý 3 câu hỏi tiếp theo.",
                "schema": list[Suggestion],
                "system": SUGGESTION_PROMPT.format(n=3),
                "context": self._context(messages),
                "retries": 1,
                "default": [],
            }
            if "config" in inspect.signature(extract).parameters:
                extract_kwargs["config"] = config
            model = get_chat_model(model_name).bind(max_tokens=250)
            try:
                items = await extract(model, **extract_kwargs)
            except TypeError as exc:
                if "unexpected keyword argument 'config'" not in str(exc):
                    raise
                extract_kwargs.pop("config", None)
                items = await extract(model, **extract_kwargs)
        except Exception:
            logger.warning("suggestion generation failed", exc_info=True)
            items = []
        suggestions: list[str] = []
        for item in items:
            question = item.question.strip()
            if len(question) >= 6 and question not in suggestions:
                suggestions.append(question)
        return {"suggestions": suggestions}

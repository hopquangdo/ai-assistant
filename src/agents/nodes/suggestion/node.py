import logging
import inspect

from dqh.ai_core import extract
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from src.agents.nodes.node_base import Node
from src.agents.nodes.suggestion.prompt import SUGGESTION_PROMPT
from src.agents.nodes.suggestion.schema import Suggestion
from src.core.config import get_settings
from src.infrastructure.llm_client import llm_client_factory

logger = logging.getLogger("chatbot.agent.suggestion")


class SuggestionNode(Node):
    name = "suggestion"
    default_model = "gpt-5-nano"

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
        if not get_settings().enable_followups or not reply.strip() or not state.get("needs_react", True):
            return {"suggestions": []}
        requested_model = (config.get("configurable") or {}).get("model")
        model_name = llm_client_factory.resolve_node_model(requested_model, self.default_model)
        try:
            extract_kwargs = {
                "prompt": f"CÃ¢u tráº£ lá»i vá»«a rá»“i:\n{reply[:3000]}\n\nGá»£i Ã½ 3 cÃ¢u há»i tiáº¿p theo.",
                "schema": list[Suggestion],
                "system": SUGGESTION_PROMPT.format(n=3),
                "context": self._context(messages),
                "retries": 1,
                "default": [],
            }
            if "config" in inspect.signature(extract).parameters:
                extract_kwargs["config"] = config
            model_options = {"max_tokens": 250}
            if model_name.lower().startswith("gpt-5") and "chat" not in model_name.lower():
                model_options = {"max_completion_tokens": 250}
            model = llm_client_factory.get_chat_model(model_name).bind(**model_options)
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


from langchain_core.language_models import BaseChatModel

from dqh.ai_core import get_chat_model as _ai_core_get_chat_model
from src.core.config import get_settings
from src.core.constants import AGENT_MODEL, AUTO_MODEL


class LLMClientFactory:
    """Dung chat model tu dqh.ai_core, cache theo model_override trong tien trinh."""

    def __init__(self) -> None:
        self._models: dict[str | None, BaseChatModel] = {}

    @staticmethod
    def resolve_node_model(model_override: str | None, node_default: str | None) -> str | None:
        """Chon model override chung hoac model mac dinh rieng cua node khi o che do auto."""
        if model_override and model_override != AUTO_MODEL:
            return model_override
        return node_default or AGENT_MODEL

    def get_chat_model(self, model_override: str | None = None) -> BaseChatModel:
        """Chat model dung chung, dung qua dqh.ai_core.get_chat_model.

        - Co LLM_BASE_URL (endpoint OpenAI-compatible, vd OpenRouter): de dqh.ai_core dung client
          tu Settings (base_url + api_key + model + temperature).
        - Khong co LLM_BASE_URL (goi thang OpenAI): truyen model dang chuoi ``openai:<name>`` de
          langchain init_chat_model tu lay OPENAI_API_KEY tu moi truong va dung endpoint mac dinh.
        """
        if model_override in self._models:
            return self._models[model_override]

        settings = get_settings()
        name = model_override or settings.llm_model_name

        if settings.llm_base_url.strip():
            # model_override chuoi se bi dqh.ai_core bo qua base_url/key -- nen chi dung nhanh nay
            # khi khong override (doi model qua .env).
            model = _ai_core_get_chat_model(model_override, settings=settings)
            self._models[model_override] = model
            return model

        spec = name if ":" in name else f"openai:{name}"
        kwargs: dict = {"temperature": settings.llm_temperature}
        if settings.llm_api_key.strip():
            kwargs["api_key"] = settings.llm_api_key
        if settings.llm_max_tokens is not None:
            kwargs["max_tokens"] = settings.llm_max_tokens

        # Model dong gpt-5 (tru gpt-5-chat) la reasoning model: neu de reasoning_effort mac dinh
        # (khac "none"), OpenAI tra 400 khi request co kem function tools qua /v1/chat/completions
        # (agent luon goi kem tool). Ep "none" de tuong thich function calling.
        lname = name.lower()
        if lname.startswith("gpt-5") and "chat" not in lname:
            kwargs.setdefault("reasoning_effort", "none")

        model = _ai_core_get_chat_model(spec, **kwargs)
        self._models[model_override] = model
        return model


llm_client_factory = LLMClientFactory()

__all__ = ["LLMClientFactory", "llm_client_factory"]

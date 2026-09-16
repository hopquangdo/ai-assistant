from functools import lru_cache

from langchain_core.language_models import BaseChatModel

from dqh.ai_core import get_chat_model as _ai_core_get_chat_model
from app.core.config import get_settings
from app.core.constants import AGENT_MODEL, AUTO_MODEL


def resolve_node_model(model_override: str | None, node_default: str | None) -> str | None:
    """Chọn model override chung hoặc model mặc định riêng của node khi ở chế độ auto."""
    if model_override and model_override != AUTO_MODEL:
        return model_override
    return node_default or AGENT_MODEL


@lru_cache
def get_chat_model(model_override: str | None = None) -> BaseChatModel:
    """Chat model dùng chung, dựng qua dqh.ai_core.get_chat_model.

    - Có LLM_BASE_URL (endpoint OpenAI-compatible, vd OpenRouter): để dqh.ai_core dựng client
      từ Settings (base_url + api_key + model + temperature).
    - Không có LLM_BASE_URL (gọi thẳng OpenAI): truyền model dạng chuỗi ``openai:<name>`` để
      langchain init_chat_model tự lấy OPENAI_API_KEY từ môi trường và dùng endpoint mặc định.
    """
    settings = get_settings()
    name = model_override or settings.llm_model_name

    if settings.llm_base_url.strip():
        # model_override chuỗi sẽ bị dqh.ai_core bỏ qua base_url/key — nên chỉ dùng nhánh này
        # khi không override (đổi model qua .env).
        return _ai_core_get_chat_model(model_override, settings=settings)

    spec = name if ":" in name else f"openai:{name}"
    kwargs: dict = {"temperature": settings.llm_temperature}
    if settings.llm_api_key.strip():
        kwargs["api_key"] = settings.llm_api_key
    if settings.llm_max_tokens is not None:
        kwargs["max_tokens"] = settings.llm_max_tokens

    # Model dòng gpt-5 (trừ gpt-5-chat) là reasoning model: nếu để reasoning_effort mặc định
    # (khác "none"), OpenAI trả 400 khi request có kèm function tools qua /v1/chat/completions
    # (agent luôn gọi kèm tool). Ép "none" để tương thích function calling.
    lname = name.lower()
    if lname.startswith("gpt-5") and "chat" not in lname:
        kwargs.setdefault("reasoning_effort", "none")

    return _ai_core_get_chat_model(spec, **kwargs)

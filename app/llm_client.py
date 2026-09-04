from functools import lru_cache

from langchain_core.language_models import BaseChatModel

from dqh.ai_core import get_chat_model as _ai_core_get_chat_model
from app.settings import get_settings


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
    return _ai_core_get_chat_model(spec, **kwargs)

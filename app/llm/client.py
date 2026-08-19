from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config.settings import get_settings


@lru_cache
def get_chat_model(model_override: str | None = None) -> ChatOpenAI:
    """Trả về chat model dùng chung, hoặc model riêng nếu agent gọi có truyền model_override
    (vd để mỗi agent — orchestrator/responder/module — dùng 1 model khác nhau, xem app/config/settings.py)."""
    settings = get_settings()
    return ChatOpenAI(
        model=model_override or settings.llm_model,
        api_key=settings.llm_api_key or None,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )

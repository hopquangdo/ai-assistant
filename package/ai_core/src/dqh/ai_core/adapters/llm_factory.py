"""Chat-model factory — the one place dqh.ai_core produces a ``BaseChatModel``.

Returns a stock LangChain ``BaseChatModel`` so callers keep the full LCEL surface
(``|``, ``.stream``, ``.with_structured_output`` ...).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.language_models import BaseChatModel

from dqh.ai_core.adapters.settings import DEFAULT_MODEL, get_settings

if TYPE_CHECKING:
    from ..config.settings import Settings

__all__ = ["DEFAULT_MODEL", "get_chat_model"]


def get_chat_model(
    model: str | BaseChatModel | None = None,
    *,
    settings: "Settings | None" = None,
    **kwargs: Any,
) -> BaseChatModel:
    """Resolve a chat model.

    - ``BaseChatModel`` → returned as-is.
    - ``str`` → a provider-prefixed name for langchain's ``init_chat_model``
      (e.g. ``"anthropic:claude-sonnet-5"``, ``"openai:gpt-4o"``).
    - ``None`` → built from ``settings`` (or the cached :func:`get_settings`).
      This project always talks to an OpenAI-compatible endpoint, so
      ``LLM_BASE_URL`` / ``LLM_API_KEY`` / ``LLM_MODEL_NAME`` are **required** —
      a missing one raises ``RuntimeError``. A bare model name is sent as
      ``openai:<name>``.

    ``kwargs`` are passed through to the model and win over settings-derived
    values (e.g. ``timeout=``, ``max_retries=``).
    """
    if isinstance(model, BaseChatModel):
        return model

    if model is None:
        s = settings or get_settings()
        required = (
            ("LLM_BASE_URL", s.llm_base_url),
            ("LLM_API_KEY", s.llm_api_key),
            ("LLM_MODEL_NAME", s.llm_model_name),
        )
        missing = [n for n, v in required if not v.strip()]
        if missing:
            raise RuntimeError(f"Thiếu {' và '.join(missing)} — bắt buộc để dựng chat model.")

        name = s.llm_model_name.strip()
        model = name if ":" in name else f"openai:{name}"
        kwargs = {
            "api_key": s.llm_api_key,
            "base_url": s.llm_base_url,
            "temperature": s.llm_temperature,
            **({"max_tokens": s.llm_max_tokens} if s.llm_max_tokens is not None else {}),
            **kwargs,
        }

    from langchain.chat_models import init_chat_model

    kwargs.setdefault("temperature", 0)
    return init_chat_model(model, **kwargs)

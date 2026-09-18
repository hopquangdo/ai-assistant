"""Shared dependencies for chatbot API routes."""

from fastapi import HTTPException

from src.core.constants import AVAILABLE_MODELS

TOOL_PREVIEW_LIMIT = 8000


def validate_model(model: str | None) -> str | None:
    """Reject models that are not explicitly available to clients."""
    if model is not None and model not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail=f"Model không hợp lệ: {model}")
    return model


def tool_preview(value: object, limit: int = TOOL_PREVIEW_LIMIT) -> str:
    """Flatten and truncate tool input/output for frontend debug events."""
    text = getattr(value, "content", value)
    if not isinstance(text, str):
        text = str(text)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + f"… (+{len(text) - limit} ký tự)"


__all__ = ["TOOL_PREVIEW_LIMIT", "tool_preview", "validate_model"]

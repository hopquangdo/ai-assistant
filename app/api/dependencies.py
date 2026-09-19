"""Shared dependencies for chatbot API routes."""

from fastapi import Header, HTTPException

from src.core.constants import AVAILABLE_MODELS

TOOL_PREVIEW_LIMIT = 8000


def get_user_id(x_user_id: str | None = Header(default=None)) -> str:
    """Nguoi dung do Backend (BFF) xac thuc va gui qua header X-User-Id. Chatbot khong tu xac thuc,
    chi dung id nay lam owner cua conversation/stream. Chatbot chi duoc mo trong mang noi bo."""
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(status_code=400, detail="Thiếu header X-User-Id")
    return x_user_id.strip()


def get_mcp_token(x_mcp_token: str | None = Header(default=None)) -> str | None:
    """Token MCP do Backend cap cho luot chat nay (dai dien nguoi dung). Chatbot chi chuyen tiep
    cho MCP, khong doc/sua noi dung. Thieu token thi chat van chay nhung tool MCP se bi tu choi."""
    return x_mcp_token.strip() if x_mcp_token and x_mcp_token.strip() else None


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


__all__ = ["TOOL_PREVIEW_LIMIT", "get_mcp_token", "get_user_id", "tool_preview", "validate_model"]

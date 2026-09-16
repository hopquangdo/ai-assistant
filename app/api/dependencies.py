"""Helper dùng chung cho các route API."""

from fastapi import HTTPException

from app.core.constants import AVAILABLE_MODELS

# Giới hạn ký tự cho phần args/result của tool phát qua SSE để debug — đủ đọc, không làm phình payload.
TOOL_PREVIEW_LIMIT = 8000


def validate_model(model: str | None) -> str | None:
    """Chặn model lạ (không có trong AVAILABLE_MODELS) — tránh client tự ý truyền chuỗi bất kỳ
    xuống init_chat_model (có thể trỏ sang provider khác nếu chứa dấu ":")."""
    if model is not None and model not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail=f"Model không hợp lệ: {model}")
    return model


def tool_preview(value: object, limit: int = TOOL_PREVIEW_LIMIT) -> str:
    """Rút gọn input/output của tool về 1 chuỗi để log ra frontend (debug)."""
    text = getattr(value, "content", value)
    if not isinstance(text, str):
        text = str(text)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + f"… (+{len(text) - limit} ký tự)"

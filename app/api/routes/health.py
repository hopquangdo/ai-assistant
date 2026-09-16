"""Route health-check và danh sách model."""

from fastapi import APIRouter

from app.core.constants import AVAILABLE_MODELS

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Check health của dịch vụ chatbot."""
    return {"status": "ok"}


@router.get("/models")
def list_models() -> dict[str, object]:
    """Danh sách model client được chọn (dropdown ở frontend)."""
    return {"models": AVAILABLE_MODELS, "default": AVAILABLE_MODELS[0]}

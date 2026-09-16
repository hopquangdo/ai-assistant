"""Route danh sách model. Health-check dùng chung của svc_core (mount ở root /health)."""

from fastapi import APIRouter

from app.core.constants import AVAILABLE_MODELS

router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
def list_models() -> dict[str, object]:
    """Danh sách model client được chọn (dropdown ở frontend)."""
    return {"models": AVAILABLE_MODELS, "default": AVAILABLE_MODELS[0]}

"""Model listing route."""

from fastapi import APIRouter

from src.core.constants import AVAILABLE_MODELS, AUTO_MODEL

router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
def list_models() -> dict[str, object]:
    """Return models available for client selection."""
    return {"models": AVAILABLE_MODELS, "default": AUTO_MODEL}

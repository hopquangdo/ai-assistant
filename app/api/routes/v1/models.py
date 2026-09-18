"""Model listing route."""

from fastapi import APIRouter, Depends

from src.security.auth import Principal, get_current_principal
from src.core.constants import AVAILABLE_MODELS, AUTO_MODEL

router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
def list_models(principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    """Return models available for client selection."""
    return {"models": AVAILABLE_MODELS, "default": AUTO_MODEL}

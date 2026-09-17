"""Version 1 API routes."""

from fastapi import APIRouter

from src.api.routes.v1.chat_stream import router as chat_stream_router
from src.api.routes.v1.conversation import router as conversation_router
from src.api.routes.v1.models import router as models_router

router = APIRouter(prefix="/v1")
router.include_router(chat_stream_router)
router.include_router(conversation_router)
router.include_router(models_router)

__all__ = ["router"]

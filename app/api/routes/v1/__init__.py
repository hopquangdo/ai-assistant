"""Package version 1 của API — tự mang tiền tố /v1 (tiền tố /api do app/main.py cộng thêm).

Mỗi router con (chat, models, ...) tự khai báo prefix riêng của resource."""

from fastapi import APIRouter

from app.api.routes.v1.chat import router as chat_router
from app.api.routes.v1.models import router as models_router

router = APIRouter(prefix="/v1")
router.include_router(chat_router)
router.include_router(models_router)

__all__ = ["router"]

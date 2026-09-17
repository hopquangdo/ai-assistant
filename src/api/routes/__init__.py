"""Top-level API router registration."""

from fastapi import APIRouter

from src.api.routes.v1 import router as v1_router

router = APIRouter()
router.include_router(v1_router)

__all__ = ["router"]

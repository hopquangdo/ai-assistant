"""Gộp tất cả version API thành 1 router duy nhất cho app/main.py.

Thêm version mới (v2, ...) bằng cách tạo package con app/api/routes/v2/ rồi
include_router thêm ở đây — không đụng tới các version cũ."""

from fastapi import APIRouter

from app.api.routes.v1 import router as v1_router

router = APIRouter()
router.include_router(v1_router)

__all__ = ["router"]


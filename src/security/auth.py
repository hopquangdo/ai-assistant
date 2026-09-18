"""Xac thuc nguoi dung cho cac API chatbot.

Chatbot khong tu verify JWT (khong giu JWT_SECRET) -- moi request phai co
`Authorization: Bearer <token>` cua nguoi dung. Viec xac thuc tap trung tai
AuthMiddleware (src/middleware.py): middleware forward token sang
backend Spring (GET /api/v1/xac-thuc/toi), backend la nguon xac thuc duy nhat.
Route/service khong tu goi backend -- chi doc Principal da duoc middleware
gan san vao request.state qua dependency get_current_principal() o day.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from fastapi import Request

from dqh.svc_core.contracts.errors import UnauthorizedError, UnavailableError
from dqh.svc_core.transports.http.client import HttpClient

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger("security.auth")

_cache: dict[str, tuple[float, "Principal"]] = {}


@dataclass(frozen=True)
class Principal:
    """Danh tinh nguoi dung da duoc backend xac thuc cho request hien tai."""

    user_id: str
    ten_dang_nhap: str
    quyen_ma: str | None
    khu_vuc_id: str | None


def get_current_principal(request: Request) -> Principal:
    """Dependency dung trong route: doc Principal ma AuthMiddleware da xac thuc va
    gan san vao request.state. Khong tu goi backend o day -- middleware da chan
    request thieu/sai token truoc khi toi duoc router."""
    principal = getattr(request.state, "principal", None)
    if principal is None:
        # Khong nen xay ra neu AuthMiddleware duoc dang ky dung -- fail-safe.
        raise UnauthorizedError("Thiếu Authorization: Bearer <token>")
    return principal


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Thiếu Authorization: Bearer <token>")
    token = authorization[len("bearer "):].strip()
    if not token:
        raise UnauthorizedError("Thiếu Authorization: Bearer <token>")
    return token


async def authenticate(token: str) -> Principal:
    """Xac thuc 1 access token qua backend, dung cache ngan han theo token de tranh
    goi lai backend tren moi frame SSE / request lien tuc cua cung 1 token."""
    cached = _cache.get(token)
    if cached is not None:
        expires_at, principal = cached
        if expires_at > time.monotonic():
            return principal
        del _cache[token]

    principal = await _introspect(token)
    ttl = get_settings().auth_cache_ttl_seconds
    _cache[token] = (time.monotonic() + ttl, principal)
    return principal


async def _introspect(token: str) -> Principal:
    settings = get_settings()
    if not settings.backend_base_url:
        logger.error("backend_base_url chưa được cấu hình — không thể xác thực")
        raise UnavailableError("Chatbot chưa được cấu hình backend xác thực")

    async with HttpClient(settings.backend_base_url, token=token, timeout=5.0, retries=1) as http:
        response = await http.get("/api/v1/xac-thuc/toi")

    payload = response.json().get("data") or {}
    user_id = payload.get("id")
    if not user_id:
        raise UnauthorizedError("Token không hợp lệ")

    return Principal(
        user_id=str(user_id),
        ten_dang_nhap=str(payload.get("tenDangNhap") or ""),
        quyen_ma=payload.get("quyenMa"),
        khu_vuc_id=str(payload["khuVucId"]) if payload.get("khuVucId") else None,
    )


__all__ = ["Principal", "authenticate", "extract_bearer_token", "get_current_principal"]

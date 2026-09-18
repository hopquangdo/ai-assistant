from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from dqh.svc_core.contracts.errors import AppError
from dqh.svc_core.transports.http.errors import to_api_error
from dqh.svc_core.transports.http.models import err

from src.security.auth import authenticate, extract_bearer_token
from src.core.logging import get_logger

logger = get_logger("security.auth_middleware")


_PUBLIC_PATH_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico")


class AuthMiddleware:
    """ASGI middleware — cung style voi RequestIdMiddleware/TimingMiddleware cua
    dqh.svc_core (pure ASGI, khong dung BaseHTTPMiddleware)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] == "OPTIONS" or self._is_public(scope["path"]):
            # OPTIONS bo qua: preflight CORS cua trinh duyet khong gui Authorization,
            # phai toi duoc CORSMiddleware (o trong AuthMiddleware trong stack) thi moi tra
            # duoc Access-Control-Allow-* header -- chan o day se lam request that bai CORS.
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        try:
            token = extract_bearer_token(request.headers.get("authorization"))
            principal = await authenticate(token)
        except AppError as exc:
            if exc.status >= 500:
                logger.exception("auth backend error: %s", exc.message, exc_info=exc)
            else:
                logger.warning(
                    "request từ chối: %s %s -> %s", scope.get("method"), scope["path"], exc.message
                )
            response = self._error_response(exc)
            await response(scope, receive, send)
            return

        scope.setdefault("state", {})["principal"] = principal
        await self.app(scope, receive, send)

    @staticmethod
    def _is_public(path: str) -> bool:
        return any(path == prefix or path.startswith(prefix + "/") for prefix in _PUBLIC_PATH_PREFIXES)

    @staticmethod
    def _error_response(exc: AppError) -> JSONResponse:
        api_err = to_api_error(exc)
        body = err(api_err.code, api_err.message, details=api_err.details)
        return JSONResponse(status_code=exc.status, content=jsonable_encoder(body))


__all__ = ["AuthMiddleware"]

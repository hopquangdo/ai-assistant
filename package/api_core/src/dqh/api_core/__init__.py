"""dqh.api_core — a thin, reusable FastAPI layer (sibling of ``dqh.ai_core``).

Layout:
    app/            ``create_app`` — a FastAPI wired with the defaults below
    dto/            response envelope (``ApiResponse`` / ``ok`` / ``err``) + pagination
    errors/         ``ApiException`` hierarchy + ``install_exception_handlers``
    middleware/     pure-ASGI request-id / timing / access-log + ``install_middleware``
    streaming/      SSE helpers (``sse``, ``SSEResponse``)
    health/         ``health_router`` with optional dependency checks
    dependencies/   FastAPI ``Depends`` callables (pagination, request id)
    types/          request-id ContextVar

Everything returns stock Starlette/FastAPI/Pydantic types, so callers keep the
full framework surface.
"""
from .app import create_app
from .dependencies import Pagination, RequestId
from .dto import ApiError, ApiResponse, Page, PaginationParams, err, ok
from .errors import (
    ApiException,
    BadRequestError,
    ConflictError,
    ErrorCode,
    ForbiddenError,
    InternalError,
    NotFoundError,
    RateLimitedError,
    UnauthorizedError,
    UpstreamError,
    ValidationError,
    install_exception_handlers,
)
from .health import health_router
from .logging import (
    DEFAULT_FORMAT,
    RequestIdLogFilter,
    install_request_id_log_filter,
)
from .middleware import install_middleware
from .streaming import SSEResponse, sse
from .types import current_request_id, request_id_ctx

__all__ = [
    "create_app",
    "ApiResponse",
    "ApiError",
    "ok",
    "err",
    "Page",
    "PaginationParams",
    "Pagination",
    "RequestId",
    "ErrorCode",
    "ApiException",
    "BadRequestError",
    "ValidationError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ConflictError",
    "RateLimitedError",
    "UpstreamError",
    "InternalError",
    "install_exception_handlers",
    "install_middleware",
    "health_router",
    "sse",
    "SSEResponse",
    "current_request_id",
    "request_id_ctx",
    "install_request_id_log_filter",
    "RequestIdLogFilter",
    "DEFAULT_FORMAT",
]

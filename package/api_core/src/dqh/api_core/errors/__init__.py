"""Error codes, exceptions, and the handlers that render them.

    from dqh.api_core.errors import install_exception_handlers
    install_exception_handlers(app)

After that, raising any :class:`ApiException` (or a bare ``HTTPException``, or an
unhandled ``Exception``) yields a consistent ``ApiResponse`` failure body.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from dqh.api_core.dto.response import err
from dqh.api_core.errors.codes import ErrorCode
from dqh.api_core.errors.exceptions import (
    ApiException,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    InternalError,
    NotFoundError,
    RateLimitedError,
    UnauthorizedError,
    UpstreamError,
    ValidationError,
)

logger = logging.getLogger("dqh.api_core")

_STATUS_TO_CODE = {
    400: ErrorCode.BAD_REQUEST,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    409: ErrorCode.CONFLICT,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMITED,
    502: ErrorCode.UPSTREAM_ERROR,
}


def _json(status: int, body) -> JSONResponse:
    return JSONResponse(status_code=status, content=jsonable_encoder(body))


def install_exception_handlers(app: FastAPI) -> None:
    """Register handlers turning exceptions into ``ApiResponse`` failures."""

    @app.exception_handler(ApiException)
    async def _api_exc(_: Request, exc: ApiException) -> JSONResponse:
        if exc.status >= 500:
            logger.exception("api exception: %s", exc.message, exc_info=exc)
        return _json(exc.status, err(exc.code, exc.message, details=exc.details))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _json(
            422,
            err(ErrorCode.VALIDATION_ERROR, "Request validation failed", details={"errors": exc.errors()}),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_TO_CODE.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        return _json(exc.status_code, err(code, str(exc.detail)))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled exception", exc_info=exc)
        return _json(500, err(ErrorCode.INTERNAL_ERROR, "Internal server error"))


__all__ = [
    "install_exception_handlers",
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
    "HTTPException",
]

"""Exception hierarchy that maps cleanly onto :class:`~dqh.api_core.dto.ApiResponse`.

Raise these anywhere in a request; the handlers installed by
:func:`dqh.api_core.errors.install_exception_handlers` turn them into a
``{"success": false, "error": {...}}`` body with the right HTTP status.
"""
from __future__ import annotations

from typing import Any

from dqh.api_core.errors.codes import ErrorCode


class ApiException(Exception):
    """Base for expected, client-facing failures.

    ``status`` is the HTTP status to send; ``code`` is the stable string the
    client branches on; ``details`` is optional structured context (never a
    stack trace or anything sensitive).
    """

    status: int = 500
    code: str = ErrorCode.INTERNAL_ERROR

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.__class__.__doc__ or self.__class__.__name__
        if code is not None:
            self.code = code
        if status is not None:
            self.status = status
        self.details = details
        super().__init__(self.message)


class BadRequestError(ApiException):
    """The request was malformed or semantically invalid."""

    status = 400
    code = ErrorCode.BAD_REQUEST


class ValidationError(ApiException):
    """Request data failed validation."""

    status = 422
    code = ErrorCode.VALIDATION_ERROR


class UnauthorizedError(ApiException):
    """Authentication is missing or invalid."""

    status = 401
    code = ErrorCode.UNAUTHORIZED


class ForbiddenError(ApiException):
    """Authenticated but not allowed to do this."""

    status = 403
    code = ErrorCode.FORBIDDEN


class NotFoundError(ApiException):
    """The requested resource does not exist."""

    status = 404
    code = ErrorCode.NOT_FOUND


class ConflictError(ApiException):
    """The request conflicts with the current state of the resource."""

    status = 409
    code = ErrorCode.CONFLICT


class RateLimitedError(ApiException):
    """Too many requests."""

    status = 429
    code = ErrorCode.RATE_LIMITED


class UpstreamError(ApiException):
    """A dependency (DB, model provider, MCP server, ...) failed."""

    status = 502
    code = ErrorCode.UPSTREAM_ERROR


class InternalError(ApiException):
    """Unexpected server-side failure."""

    status = 500
    code = ErrorCode.INTERNAL_ERROR


__all__ = [
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
]

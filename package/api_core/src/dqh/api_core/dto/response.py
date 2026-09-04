"""The single response envelope every endpoint returns.

    { "success": true,  "data": <payload>, "error": null, "request_id": "..." }
    { "success": false, "data": null,      "error": {code, message, details}, "request_id": "..." }

Use :func:`ok` / :func:`err` to build one; the ``request_id`` is filled in from
the request context automatically when omitted.
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from dqh.api_core.types import current_request_id

T = TypeVar("T")


class ApiError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: ApiError | None = None
    request_id: str | None = None


def ok(data: T | None = None, *, request_id: str | None = None) -> ApiResponse[T]:
    """A success envelope wrapping ``data``."""
    return ApiResponse[T](
        success=True,
        data=data,
        request_id=request_id or current_request_id() or None,
    )


def err(
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> ApiResponse[Any]:
    """A failure envelope. Handlers in :mod:`dqh.api_core.errors` use this."""
    return ApiResponse[Any](
        success=False,
        error=ApiError(code=str(code), message=message, details=details),
        request_id=request_id or current_request_id() or None,
    )


__all__ = ["ApiError", "ApiResponse", "ok", "err"]

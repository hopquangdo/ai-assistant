"""Machine-readable error codes carried in :class:`~dqh.api_core.dto.ApiError`.

Kept deliberately small and HTTP-shaped. Apps that need domain-specific codes can
pass any string to :class:`~dqh.api_core.errors.ApiException`; this enum is just
the common set the built-in exceptions use.
"""
from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    BAD_REQUEST = "BAD_REQUEST"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    def __str__(self) -> str:  # so f-strings / json give the bare value
        return self.value


__all__ = ["ErrorCode"]

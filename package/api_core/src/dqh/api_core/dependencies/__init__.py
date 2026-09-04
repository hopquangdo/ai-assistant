"""FastAPI dependency callables.

    from dqh.api_core.dependencies import pagination, RequestId

    @app.get("/items")
    async def list_items(page: PaginationParams = Depends(pagination)): ...

    @app.get("/whoami")
    async def whoami(rid: RequestId): ...
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query

from dqh.api_core.dto.pagination import PaginationParams
from dqh.api_core.types import current_request_id


def pagination(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


def request_id() -> str:
    return current_request_id()


Pagination = Annotated[PaginationParams, Depends(pagination)]
RequestId = Annotated[str, Depends(request_id)]

__all__ = ["pagination", "request_id", "Pagination", "RequestId"]

"""Thực thi tool tất định (cho plan / bước workflow không qua LLM) — BẤT ĐỒNG BỘ.

``arun(parallel=True)`` chạy song song các call độc lập. Tool chỉ có ``_run`` (sync):
LangChain tự chạy trong thread pool khi gọi ``ainvoke`` — không sao.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from langchain_core.tools import BaseTool

__all__ = [
    "ToolExecutor",
    "ToolCall",
    "ToolResult",
    "ToolExecutorError",
    "UnknownToolError",
]


class ToolExecutorError(RuntimeError):
    """Base error for deterministic tool execution."""


class UnknownToolError(ToolExecutorError):
    """Raised when a plan refers to a tool that was not registered."""


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    call: ToolCall
    output: Any = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class ToolExecutor:
    """Chạy các LangChain tool đã đăng ký theo thứ tự dự đoán được, có kiểm toán."""

    def __init__(self, tools: Iterable[BaseTool]) -> None:
        self._tools: dict[str, BaseTool] = {}
        for tool in tools:
            if tool.name in self._tools:
                raise ValueError(f"duplicate tool name: {tool.name!r}")
            self._tools[tool.name] = tool

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(self._tools)

    def _resolve(self, call: ToolCall) -> BaseTool:
        tool = self._tools.get(call.name)
        if tool is None:
            raise UnknownToolError(f"unknown tool: {call.name!r}")
        return tool

    async def invoke(self, call: ToolCall) -> ToolResult:
        """Chạy 1 call. Lỗi tool -> gói trong ``ToolResult.error`` (không raise).
        Tool không tồn tại -> raise ``UnknownToolError``."""
        tool = self._resolve(call)
        try:
            return ToolResult(call=call, output=await tool.ainvoke(call.arguments))
        except Exception as exc:
            return ToolResult(call=call, error=f"{type(exc).__name__}: {exc}")

    async def run(
        self,
        calls: Sequence[ToolCall],
        *,
        stop_on_error: bool = True,
        parallel: bool = False,
        max_concurrency: int | None = None,
    ) -> list[ToolResult]:
        """Chạy nhiều call.

        - ``parallel=False`` (mặc định): tuần tự, giữ đúng thứ tự, dừng khi lỗi nếu ``stop_on_error``.
        - ``parallel=True``: chạy đồng thời (``max_concurrency`` giới hạn nếu cần), CHẠY HẾT mọi
          call (bỏ qua ``stop_on_error``), lỗi gói trong từng ``ToolResult``. Kết quả vẫn theo
          thứ tự đầu vào.
        """
        calls = list(calls)
        if not parallel:
            results: list[ToolResult] = []
            for call in calls:
                result = await self.invoke(call)
                results.append(result)
                if stop_on_error and not result.ok:
                    break
            return results

        sem = asyncio.Semaphore(max_concurrency) if max_concurrency else None

        async def _one(call: ToolCall) -> ToolResult:
            if sem is None:
                return await self.invoke(call)
            async with sem:
                return await self.invoke(call)

        return list(await asyncio.gather(*(_one(c) for c in calls)))

import asyncio

import pytest
from langchain_core.tools import StructuredTool

from dqh.ai_core import ToolCall, ToolExecutor, UnknownToolError


def add(left: int, right: int) -> int:
    """Add two integers."""
    return left + right


def fail() -> None:
    """Raise a predictable test error."""
    raise ValueError("boom")


def test_executor_runs_registered_tools_in_order() -> None:
    executor = ToolExecutor([StructuredTool.from_function(add, name="add")])

    results = asyncio.run(executor.run([ToolCall("add", {"left": 2, "right": 3})]))

    assert executor.tool_names == ("add",)
    assert results[0].ok
    assert results[0].output == 5


def test_executor_captures_errors_and_can_stop() -> None:
    executor = ToolExecutor([StructuredTool.from_function(fail, name="fail")])

    results = asyncio.run(executor.run([ToolCall("fail", {}), ToolCall("fail", {})]))

    assert len(results) == 1
    assert results[0].error == "ValueError: boom"
    assert not results[0].ok


def test_executor_parallel_runs_all_and_captures_each_error() -> None:
    executor = ToolExecutor([
        StructuredTool.from_function(add, name="add"),
        StructuredTool.from_function(fail, name="fail"),
    ])

    results = asyncio.run(
        executor.run(
            [ToolCall("add", {"left": 1, "right": 1}), ToolCall("fail", {}), ToolCall("add", {"left": 2, "right": 2})],
            parallel=True,
        )
    )

    assert [r.output for r in results] == [2, None, 4]
    assert results[1].error == "ValueError: boom"


def test_executor_rejects_unknown_tool() -> None:
    executor = ToolExecutor([])

    with pytest.raises(UnknownToolError, match="unknown tool"):
        asyncio.run(executor.invoke(ToolCall("missing", {})))

"""``extract`` — bắt LLM trả về output đúng schema, tự retry khi parse hỏng.

    class Followup(BaseModel):
        question: str

    items = await extract(model, "Gợi ý 3 câu hỏi tiếp theo…", list[Followup], default=[])

Hỗ trợ schema: 1 ``pydantic.BaseModel``, ``list[Model]`` (tự bọc), hoặc ``TypedDict``.
"""
from __future__ import annotations

import typing
from typing import Any, Sequence, TypeVar, get_args, get_origin

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, create_model

__all__ = ["extract", "StructuredOutputError"]

T = TypeVar("T")
_SENTINEL = object()


class StructuredOutputError(RuntimeError):
    """LLM không trả về output hợp lệ sau khi đã retry."""


def _wrap_list_schema(schema: Any) -> tuple[Any, bool]:
    """``list[X]`` -> (model bọc có field ``items: list[X]``, True). Còn lại giữ nguyên -> (schema, False)."""
    if get_origin(schema) in (list, typing.List):
        (inner,) = get_args(schema)
        wrapper = create_model("_ExtractList", items=(list[inner], ...))
        return wrapper, True
    return schema, False


async def extract(
    model: BaseChatModel,
    prompt: str,
    schema: type[T] | Any,
    *,
    system: str | None = None,
    context: Sequence[BaseMessage] = (),
    retries: int = 2,
    retry_hint: str = "The previous result was invalid ({error}). Reply again in EXACTLY the required format, nothing else.",
    default: Any = _SENTINEL,
) -> T | Any:
    """Gọi ``model.with_structured_output(schema)`` và trả về object đã parse.

    - ``system`` / ``context``: chèn trước ``prompt``.
    - Parse/validate hỏng -> nhắc lại model kèm lỗi, tối đa ``retries`` lần.
    - Hết retry: raise ``StructuredOutputError``, HOẶC trả ``default`` nếu có truyền.
    """
    target, wrapped = _wrap_list_schema(schema)
    structured = model.with_structured_output(target)

    messages: list[BaseMessage] = []
    if system:
        messages.append(SystemMessage(content=system))
    messages.extend(context)
    messages.append(HumanMessage(content=prompt))

    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            result = await structured.ainvoke(messages)
            if wrapped:
                return result.items if isinstance(result, BaseModel) else result["items"]
            return result
        except Exception as exc:  # parse / validation / API
            last_err = exc
            if attempt < retries:
                messages.append(HumanMessage(content=retry_hint.format(error=exc)))

    if default is not _SENTINEL:
        return default
    raise StructuredOutputError(f"extract thất bại sau {retries + 1} lần: {last_err}") from last_err

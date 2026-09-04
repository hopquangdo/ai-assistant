"""``compact_tool_output`` — thu nhỏ kết quả tool trước khi trả lại model (giảm token + nhiễu).

Nếu là JSON: cắt bớt phần tử mảng dài + chuỗi dài NHƯNG GIỮ cấu trúc (khoá vẫn còn để model
đọc được). Nếu không: cắt ký tự có ellipsis. Thuần hàm, không gọi LLM.

    from dqh.ai_core.core.tools import compact_tool_output
    short = compact_tool_output(tool_message, max_array=5, max_str=300)
"""
from __future__ import annotations

import json
from typing import Any

__all__ = ["compact_tool_output"]


def _unwrap(value: Any) -> str:
    """ToolMessage / obj -> chuỗi."""
    text = getattr(value, "content", value)
    return text if isinstance(text, str) else str(text)


def _shrink(node: Any, *, max_array: int, max_str: int, max_keys: int) -> Any:
    if isinstance(node, str):
        return node if len(node) <= max_str else node[:max_str] + f"…(+{len(node) - max_str})"
    if isinstance(node, list):
        head = [_shrink(x, max_array=max_array, max_str=max_str, max_keys=max_keys) for x in node[:max_array]]
        if len(node) > max_array:
            head.append(f"…(+{len(node) - max_array} phần tử)")
        return head
    if isinstance(node, dict):
        items = list(node.items())
        out = {k: _shrink(v, max_array=max_array, max_str=max_str, max_keys=max_keys) for k, v in items[:max_keys]}
        if len(items) > max_keys:
            out["…"] = f"+{len(items) - max_keys} khoá"
        return out
    return node


def compact_tool_output(
    value: Any,
    *,
    max_array: int = 8,
    max_str: int = 400,
    max_keys: int = 40,
    max_chars: int = 6000,
) -> str:
    """Chuỗi rút gọn của ``value``. JSON -> giữ cấu trúc; còn lại -> cắt ký tự."""
    raw = _unwrap(value)
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        flat = " ".join(raw.split())
        return flat if len(flat) <= max_chars else flat[:max_chars] + f"…(+{len(flat) - max_chars} ký tự)"

    shrunk = _shrink(data, max_array=max_array, max_str=max_str, max_keys=max_keys)
    out = json.dumps(shrunk, ensure_ascii=False)
    return out if len(out) <= max_chars else out[:max_chars] + "…"

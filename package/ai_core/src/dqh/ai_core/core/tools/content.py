"""Helpers for authoring tools that plug into dqh.ai_core.

Tools are plain LangChain tools (`BaseTool` / `StructuredTool` / `@tool`).
The only extra thing here is a couple of content-block builders so a tool can
return images (or mixed text+image) back to a multimodal model.
"""
from __future__ import annotations

from langchain_core.tools import BaseTool, StructuredTool, tool

__all__ = ["BaseTool", "StructuredTool", "tool", "text_block", "image_block"]


def text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def image_block(data_b64: str, mime_type: str = "image/jpeg") -> dict:
    """A LangChain standard image content block (base64).

    Use with a tool declared ``response_format="content_and_artifact"``:
    return ``([image_block(...)], artifact)``.
    """
    return {
        "type": "image",
        "source_type": "base64",
        "mime_type": mime_type,
        "data": data_b64,
    }

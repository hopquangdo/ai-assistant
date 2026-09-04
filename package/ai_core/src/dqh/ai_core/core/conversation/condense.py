"""``condense_history`` — nén các lượt cũ của hội thoại thành 1 ``SystemMessage`` tóm tắt.

Tách khỏi ``History`` (đồng bộ, fluent) vì hàm này gọi LLM -> bất đồng bộ.
"""
from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

__all__ = ["condense_history"]

_DEFAULT_PROMPT = (
    "Summarize the conversation below into short bullet points. Keep: the user's request and "
    "context, important facts/numbers, and any conclusions reached. Drop greetings and small "
    "talk. Write in the same language as the conversation, under 200 words."
)


def _split(messages: list[BaseMessage], keep_last: int) -> tuple[list[BaseMessage], list[BaseMessage], list[BaseMessage]]:
    """(system ở đầu, phần cũ cần nén, keep_last lượt cuối giữ nguyên)."""
    k = 0
    while k < len(messages) and isinstance(messages[k], SystemMessage):
        k += 1
    system, body = messages[:k], messages[k:]

    human_idx = [i for i, m in enumerate(body) if isinstance(m, HumanMessage)]
    if len(human_idx) <= keep_last:
        return system, [], body
    cut = human_idx[-keep_last]
    return system, body[:cut], body[cut:]


async def condense_history(
    messages: list[BaseMessage],
    llm: BaseChatModel,
    *,
    keep_last: int = 6,
    prompt: str = _DEFAULT_PROMPT,
    marker: str = "[conversation summary]",
) -> list[BaseMessage]:
    """Trả về: ``[*system, SystemMessage(tóm tắt phần cũ), *keep_last lượt cuối]``.

    Không có gì để nén (hội thoại ngắn hơn ``keep_last`` lượt, hoặc đã nén rồi) -> trả nguyên.
    Lỗi gọi LLM -> trả nguyên (không làm hỏng luồng chính).
    """
    system, old, recent = _split(messages, keep_last)
    if not old or any(isinstance(m, SystemMessage) and marker in (m.content or "") for m in system):
        return messages

    transcript = "\n".join(
        f"{'User' if isinstance(m, HumanMessage) else 'Assistant' if isinstance(m, AIMessage) else m.__class__.__name__}: {m.content}"
        for m in old
        if getattr(m, "content", "")
    )
    try:
        resp = await llm.ainvoke([SystemMessage(content=prompt), HumanMessage(content=transcript)])
        summary = str(resp.content).strip()
    except Exception:
        return messages
    if not summary:
        return messages

    return [*system, SystemMessage(content=f"{marker}\n{summary}"), *recent]

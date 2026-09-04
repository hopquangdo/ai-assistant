"""Sinh gợi ý câu hỏi tiếp theo cho người dùng sau mỗi câu trả lời của AI.

1 lần gọi LLM nhẹ (không tool), tách khỏi luồng agent chính. Lỗi ở đây KHÔNG được làm hỏng
câu trả lời — trả list rỗng là an toàn.
"""
import logging

from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from dqh.ai_core import extract

from app.llm_client import get_chat_model
from app.settings import get_settings

logger = logging.getLogger("chatbot.followups")

_SYSTEM = (
    "Bạn là trợ lý gợi ý câu hỏi. Dựa trên đoạn hội thoại và câu trả lời vừa rồi, đề xuất "
    "{n} câu hỏi TIẾP THEO ngắn gọn (dưới 15 từ) mà người dùng có thể muốn hỏi để đào sâu "
    "hoặc mở rộng, bám sát dữ liệu nghiệp vụ hợp đồng/sản lượng/trạm/vướng mắc/phân công. "
    "Tiếng Việt."
)


class _Followup(BaseModel):
    question: str = Field(description="Một câu hỏi gợi ý, tiếng Việt, dưới 15 từ")


def _context(history: list) -> list:
    """history dict {role, content} -> message LangChain (bỏ tool call/tool result), 6 message cuối."""
    out: list = []
    for m in history:
        role = m.get("role") if isinstance(m, dict) else getattr(m, "type", None)
        content = m.get("content") if isinstance(m, dict) else getattr(m, "content", "")
        if not content or role not in ("user", "assistant", "human", "ai"):
            continue
        cls = HumanMessage if role in ("user", "human") else AIMessage
        out.append(cls(content=str(content)[:2000]))
    return out[-6:]


async def suggest_followups(history: list, reply: str, n: int = 3) -> list[str]:
    """Trả về tối đa `n` câu hỏi gợi ý. Rỗng nếu tắt tính năng hoặc gặp lỗi."""
    if not get_settings().enable_followups or not reply.strip():
        return []
    items = await extract(
        get_chat_model().bind(max_tokens=250),
        prompt=f"Câu trả lời vừa rồi:\n{reply[:3000]}\n\nGợi ý {n} câu hỏi tiếp theo.",
        schema=list[_Followup],
        system=_SYSTEM.format(n=n),
        context=_context(history),
        retries=1,
        default=[],
    )
    seen: list[str] = []
    for it in items:
        q = it.question.strip()
        if len(q) >= 6 and q not in seen:
            seen.append(q)
    return seen[:n]

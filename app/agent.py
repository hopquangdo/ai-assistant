from functools import lru_cache
import logging
import time

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.errors import GraphRecursionError

from dqh.ai_core import Agent, Usage, UsageTracker

from app.llm_client import get_chat_model
from app.prompts import AGENT_PROMPT
from app.settings import get_settings
from app.tools import ALL_TOOLS
from app.utils.time_context import current_date_system_message

# Model mặc định khi client không chọn — None nghĩa là dùng settings.llm_model_name.
AGENT_MODEL: str | None = None

# Model cho phép chọn ở frontend (dropdown) — giới hạn model OpenAI đã có giá trong
# model_prices.json (xem package/ai_core/data/model_prices.json) vì backend hiện gọi thẳng
# OpenAI (LLM_BASE_URL rỗng, xem app/llm_client.py). Thêm model khác vào đây CHỈ SAU KHI đã có
# base_url/API key phù hợp cho model đó.
AVAILABLE_MODELS: list[str] = ["gpt-4o-mini", "gpt-4o", "gpt-5-nano", "gpt-5-mini", "gpt-5"]

# Chặn cứng vòng lặp ReAct (mỗi vòng "agent quyết định -> gọi tool" tốn 2 bước graph, KHÔNG tính
# theo số tool call nếu gọi song song nhiều tool trong 1 vòng). 10 bước ~ đủ cho câu hỏi cần đối
# chiếu 2-3 lĩnh vực cùng lúc; vượt ngưỡng này gần như chắc chắn là agent đang "mò" tool sai vì
# không có tool nào khớp đúng câu hỏi (xem GraphRecursionError bên dưới) chứ không phải câu hỏi
# hợp lệ cần nhiều vòng hơn.
AGENT_RECURSION_LIMIT = 10

# Câu trả lời an toàn khi agent chạm AGENT_RECURSION_LIMIT — dùng chung cho /chat và /chat/stream
# (xem app/routes.py) để 2 endpoint trả lời nhất quán khi rơi vào cùng 1 tình huống.
RECURSION_LIMIT_FALLBACK_TEXT = (
    "Hệ thống hiện chưa có dữ liệu/tool phù hợp để trả lời chính xác câu hỏi này "
    "(có thể câu hỏi cần một khái niệm nghiệp vụ mà hệ thống chưa theo dõi). "
    "Anh/chị có thể mô tả lại theo hướng cụ thể hơn, hoặc hỏi từng phần riêng lẻ."
)

logger = logging.getLogger("chatbot.agent")


@lru_cache
def get_agent(model: str | None = None) -> Agent:
    """Agent ReAct (dqh.ai_core.Agent bọc create_react_agent), nạp toàn bộ tool nghiệp vụ
    discover từ MCP server.

    ``model`` là tên model client chọn (xem AVAILABLE_MODELS) — None dùng AGENT_MODEL mặc định.
    lru_cache trả cùng 1 instance cho mỗi model (1 instance/model là đủ vì ALL_TOOLS được nạp 1
    lần lúc app khởi động, xem app/main.py). Dùng .graph để invoke/stream bất đồng bộ.
    """
    return Agent.create(tools=ALL_TOOLS, model=get_chat_model(model or AGENT_MODEL), system=AGENT_PROMPT)


async def warmup_agent() -> None:
    """Đẩy toàn bộ chi phí "cold start" vào lúc app khởi động thay vì bắt request đầu chịu.

    Gọi lúc lifespan (sau khi đã set_tools): dựng + compile graph, và bắn 1 request LLM
    cực nhỏ để mở sẵn connection pool / handshake TLS tới nhà cung cấp và cache prompt phía
    họ. Lỗi ở đây không được làm chết app — chỉ log cảnh báo.
    """
    t0 = time.perf_counter()
    try:
        agent = get_agent()
        await agent.model.ainvoke([HumanMessage(content="ping")])
        logger.info("agent warmup done in %.0fms (tools=%d)",
                    (time.perf_counter() - t0) * 1000, len(ALL_TOOLS))
    except Exception:
        logger.warning("agent warmup failed (bỏ qua, request đầu sẽ chịu cold start)", exc_info=True)


def new_usage_tracker(model: str | None = None) -> tuple[Usage, UsageTracker]:
    """Cặp (Usage, UsageTracker) mới cho 1 lượt chat — gắn tracker vào config callbacks.

    Việc log token/chi phí do chính UsageTracker của dqh.ai_core đảm nhiệm (logger
    ``dqh.ai_core``, mỗi lần gọi LLM log tokens + cache + cộng dồn + cost). Tầng chatbot
    KHÔNG log lại usage nữa để tránh trùng lặp."""
    usage = Usage(model=model or get_settings().llm_model_name)
    return usage, UsageTracker(usage)


def build_input_messages(messages: list) -> list:
    """Tiêm ngày hiện tại thật (tính lại mỗi lần gọi) trước hội thoại — đảm bảo agent tự tính đúng
    ngày tháng năm khi câu hỏi nhắc thời gian tương đối, không phụ thuộc LLM tự gọi tool."""
    return [current_date_system_message(), *messages]


async def run_agent(messages: list, model: str | None = None) -> list:
    """Chạy 1 lượt ReAct đầy đủ (không streaming), trả về CÁC MESSAGE MỚI sinh ra (tool call, tool
    result, câu trả lời cuối) — không gồm message đầu vào.
    """
    logger.info("agent execution start", extra={"messages_count": len(messages)})
    graph = get_agent(model).graph
    input_messages = build_input_messages(messages)
    _usage, tracker = new_usage_tracker(model)
    try:
        result = await graph.ainvoke(
            {"messages": input_messages},
            config={"recursion_limit": AGENT_RECURSION_LIMIT, "callbacks": [tracker]},
        )
        new_messages = result["messages"][len(input_messages):]
    except GraphRecursionError:
        # Agent đã thử vượt AGENT_RECURSION_LIMIT bước mà chưa dừng — gần như luôn do câu hỏi cần
        # 1 khái niệm/dữ liệu mà KHÔNG tool nào có, khiến agent cứ đổi entity/operation để "mò".
        # Trả lời an toàn thay vì để lỗi 500 hoặc im lặng loop tới khi client timeout.
        logger.warning("agent hit recursion limit (%s) — likely no matching tool for this query", AGENT_RECURSION_LIMIT)
        new_messages = [AIMessage(content=RECURSION_LIMIT_FALLBACK_TEXT)]
    finally:
        # dqh.ai_core tự log dòng "usage ..." khi graph chạy xong; gọi thêm ở đây để
        # nhánh GraphRecursionError (graph bị abort, không có on_chain_end) vẫn log tổng.
        tracker.log_summary()
    logger.info("agent execution finish", extra={"reply": str(new_messages[-1:])})
    return new_messages

from functools import lru_cache
import logging

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from app.config.settings import get_settings
from app.graph.state import GraphState
from app.llm.client import get_chat_model
from app.prompts import AGENT_PROMPT
from app.tools import ALL_TOOLS
from app.utils.time_context import current_date_system_message

# Model cho agent duy nhất — để None để dùng model mặc định (settings.llm_model).
AGENT_MODEL: str | None = None

logger = logging.getLogger("chatbot.agent")

# Đơn giá USD/1M token theo model id trên OpenRouter (input, cached input, output) — dùng để log ra
# tiền ước tính mỗi lượt chat, theo dõi chi phí. Cập nhật thủ công theo https://openrouter.ai/models
# khi đổi model hoặc giá thay đổi — không có API tra giá realtime nên chấp nhận có thể lệch nhẹ.
_PRICING_PER_MILLION_USD: dict[str, tuple[float, float, float]] = {
    "openai/gpt-4o-mini": (0.15, 0.075, 0.60),
    "openai/gpt-4o": (2.50, 1.25, 10.00),
    "openai/gpt-4.1-mini": (0.40, 0.10, 1.60),
    "openai/gpt-4.1": (2.00, 0.50, 8.00),
    "anthropic/claude-haiku-4.5": (1.00, 0.10, 5.00),
    "anthropic/claude-sonnet-5": (3.00, 0.30, 15.00),
    "google/gemini-2.5-flash": (0.30, 0.075, 2.50),
    "google/gemini-2.5-pro": (1.25, 0.31, 10.00),
}


def _estimate_cost_usd(input_tokens: int, cached_tokens: int, output_tokens: int) -> float | None:
    """Trả về None nếu model hiện tại chưa có trong bảng giá — không đoán mò giá của model lạ."""
    model = get_settings().llm_model
    pricing = _PRICING_PER_MILLION_USD.get(model)
    if pricing is None:
        return None
    input_price, cached_price, output_price = pricing
    uncached_input = max(input_tokens - cached_tokens, 0)
    return (
        uncached_input * input_price + cached_tokens * cached_price + output_tokens * output_price
    ) / 1_000_000


def _log_tool_calls(messages: list) -> None:
    """Log rõ tool nào được gọi với tham số gì, và tool trả về gì — để debug agent có gọi đúng
    tool/tham số hay không (vd có gọi thoigian_hientai trước khi tính ngày tương đối không)."""
    for message in messages:
        if isinstance(message, AIMessage) and getattr(message, "tool_calls", None):
            for call in message.tool_calls:
                logger.info(f"tool call: {call.get('name')} args={call.get('args')}")
        elif isinstance(message, ToolMessage):
            content = str(message.content)
            truncated = content[:2000] + ("..." if len(content) > 2000 else "")
            logger.info(f"tool result: {message.name} -> {truncated}")


def _log_token_usage(messages: list) -> None:
    """Log input/output/cached token của MỖI lần gọi LLM trong lượt này (1 agent turn có thể gọi
    LLM nhiều lần: 1 lần/vòng ReAct) — dùng theo dõi chi phí, so sánh giữa các nhà cung cấp qua
    OpenRouter. usage_metadata chỉ có khi provider trả kèm usage (hầu hết model OpenAI-compatible
    đều có, một số model free trên OpenRouter có thể thiếu — bỏ qua nếu không có, không lỗi)."""
    total_input = total_output = total_cached = 0
    calls = 0
    for message in messages:
        if not isinstance(message, AIMessage):
            continue
        usage = getattr(message, "usage_metadata", None)
        if not usage:
            continue
        calls += 1
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        total_tokens = usage.get("total_tokens", input_tokens + output_tokens)
        cached_tokens = (usage.get("input_token_details") or {}).get("cache_read", 0)
        total_input += input_tokens
        total_output += output_tokens
        total_cached += cached_tokens
        cost = _estimate_cost_usd(input_tokens, cached_tokens, output_tokens)
        cost_str = f"${cost:.6f}" if cost is not None else "n/a"
        logger.info(
            "token usage: input=%s (cached=%s) output=%s total=%s cost=%s",
            input_tokens, cached_tokens, output_tokens, total_tokens, cost_str,
        )
    if calls > 1:
        total_cost = _estimate_cost_usd(total_input, total_cached, total_output)
        total_cost_str = f"${total_cost:.6f}" if total_cost is not None else "n/a"
        logger.info(
            "token usage (tổng %s lần gọi LLM): input=%s (cached=%s) output=%s total=%s cost=%s",
            calls, total_input, total_cached, total_output, total_input + total_output, total_cost_str,
        )


@lru_cache
def _build_agent():
    """Xây agent ReAct duy nhất, nạp toàn bộ tool nghiệp vụ discover từ MCP server.

    lru_cache trả cùng 1 instance mỗi lần gọi — an toàn vì ALL_TOOLS được nạp 1 lần lúc app khởi
    động (xem app/main.py) trước khi node đầu tiên chạy.
    """
    return create_react_agent(
        get_chat_model(AGENT_MODEL),
        tools=ALL_TOOLS,
        prompt=AGENT_PROMPT,
    )


async def agent_node(state: GraphState) -> dict:
    """Thực thi agent duy nhất với toàn bộ hội thoại, trả về mọi message mới sinh ra.

    Async vì tool nạp từ MCP server (langchain-mcp-adapters) chỉ hỗ trợ gọi bất đồng bộ.
    """
    logger.info("agent execution start", extra={"messages_count": len(state.get("messages", []))})
    agent = _build_agent()
    # Tiêm ngày hiện tại thật (tính lại mỗi lần gọi) trước hội thoại — đảm bảo agent tự tính đúng
    # ngày tháng năm khi câu hỏi nhắc thời gian tương đối, không phụ thuộc LLM tự gọi tool.
    input_messages = [current_date_system_message(), *state["messages"]]
    result = await agent.ainvoke({"messages": input_messages})
    new_messages = result["messages"][len(input_messages):]
    _log_tool_calls(new_messages)
    _log_token_usage(new_messages)
    logger.info("agent execution finish", extra={"reply": str(new_messages[-1:])})
    return {"messages": new_messages}

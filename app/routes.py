"""Định nghĩa các tuyến API cho chatbot."""

import logging
import uuid

from fastapi import APIRouter, HTTPException

from dqh.ai_core import (
    DoneEvent,
    ErrorEvent,
    MessageEvent,
    TokenEvent,
    ToolEndEvent,
    ToolStartEvent,
    stream_agent,
)
from dqh.svc_core.transports.sse import SSEResponse, sse as _sse

from app.agent import (
    AGENT_RECURSION_LIMIT,
    AVAILABLE_MODELS,
    RECURSION_LIMIT_FALLBACK_TEXT,
    build_input_messages,
    get_agent,
    new_usage_tracker,
    run_agent,
)
from app.followups import suggest_followups
from app.logging import get_logger
from app.memory import memory_manager, sanitize_tool_call_history
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()
logger = get_logger("api.routes")

# Giới hạn ký tự cho phần args/result của tool phát qua SSE để debug — đủ đọc, không làm phình payload.
_TOOL_PREVIEW_LIMIT = 8000


def _tool_preview(value: object, limit: int = _TOOL_PREVIEW_LIMIT) -> str:
    """Rút gọn input/output của tool về 1 chuỗi để log ra frontend (debug)."""
    text = getattr(value, "content", value)
    if not isinstance(text, str):
        text = str(text)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + f"… (+{len(text) - limit} ký tự)"

@router.get("/health")
def health() -> dict[str, str]:
    """Check health của dịch vụ chatbot."""
    return {"status": "ok"}


@router.get("/models")
def list_models() -> dict[str, object]:
    """Danh sách model client được chọn (dropdown ở frontend)."""
    return {"models": AVAILABLE_MODELS, "default": AVAILABLE_MODELS[0]}


def _validate_model(model: str | None) -> str | None:
    """Chặn model lạ (không có trong AVAILABLE_MODELS) — tránh client tự ý truyền chuỗi bất kỳ
    xuống init_chat_model (có thể trỏ sang provider khác nếu chứa dấu ":")."""
    if model is not None and model not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail=f"Model không hợp lệ: {model}")
    return model


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Nhận tin nhắn từ client, giữ memory phiên và trả về câu trả lời."""
    session_id = request.session_id or str(uuid.uuid4())
    session_memory = memory_manager.get(session_id)
    history = sanitize_tool_call_history(session_memory.get("messages", []))
    messages = history + [{"role": "user", "content": request.message}]

    logger.info("chat request", extra={"session_id": session_id, "user_message": request.message})

    model = _validate_model(request.model)
    try:
        new_messages = await run_agent(messages, model=model)
    except Exception:
        logger.exception("chat failed", extra={"session_id": session_id})
        raise HTTPException(status_code=500, detail="Đã có lỗi xảy ra, vui lòng thử lại.")

    last_message = new_messages[-1]
    content = last_message.content if hasattr(last_message, "content") else last_message["content"]

    # Lưu toàn bộ trace (bao gồm tool call/tool result) để lượt sau còn số liệu gốc làm căn cứ.
    memory_manager.update(session_id, {"messages": messages + new_messages})
    logger.info("chat response", extra={"session_id": session_id, "reply": content})

    suggestions = await suggest_followups(messages, str(content))
    return ChatResponse(reply=content, session_id=session_id, suggestions=suggestions)


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> SSEResponse:
    """Stream trạng thái xử lý + token trả lời qua Server-Sent Events.

    Stream thẳng từ agent ReAct (không qua StateGraph bọc ngoài) — chunk có nội dung text (không
    phải tool-call) chỉ xuất hiện ở lượt trả lời cuối cùng của node "agent", nên stream thẳng mọi
    on_chat_model_stream của node đó là an toàn (xem app/agents/base.py).
    """
    model = _validate_model(request.model)
    session_id = request.session_id or str(uuid.uuid4())
    session_memory = memory_manager.get(session_id)
    history = sanitize_tool_call_history(session_memory.get("messages", []))
    messages = history + [{"role": "user", "content": request.message}]

    logger.info("chat stream request", extra={"session_id": session_id, "user_message": request.message})

    async def event_generator():
        graph = get_agent(model).graph
        input_messages = build_input_messages(messages)
        _usage, tracker = new_usage_tracker(model)
        # DoneEvent.messages là nguồn chính; MessageEvent tích luỹ dự phòng nếu stream đứt sớm.
        new_messages: list = []
        final_content = ""

        try:
            async for ev in stream_agent(
                graph,
                {"messages": input_messages},
                config={"recursion_limit": AGENT_RECURSION_LIMIT, "callbacks": [tracker]},
                recursion_fallback=RECURSION_LIMIT_FALLBACK_TEXT,
            ):
                match ev:
                    # Mỗi tool -> 1 bước riêng để người dùng thấy đang tra cứu cái gì.
                    case ToolStartEvent(name=name, args=args):
                        yield _sse("status", {
                            "node": name, "type": "SEARCHING", "module": name,
                            "args": _tool_preview(args, 1000),
                        })
                    case ToolEndEvent(name=name, output=output):
                        preview = _tool_preview(output)
                        logger.info("tool result", extra={"session_id": session_id, "tool": name, "result": preview})
                        yield _sse("tool_result", {"tool": name, "output": preview})
                    case TokenEvent(text=text):
                        yield _sse("token", {"content": text})
                    case MessageEvent(message=message):
                        new_messages.append(message)
                    case ErrorEvent(message=msg, recoverable=recoverable):
                        logger.warning("agent stream error: %s (recoverable=%s)", msg, recoverable)
                    case DoneEvent(messages=msgs, text=text):
                        new_messages = msgs or new_messages
                        final_content = text
        except Exception:
            logger.exception("chat stream failed", extra={"session_id": session_id})
            tracker.log_summary(error="chat stream failed")
            yield _sse("error", {"message": "Đã có lỗi xảy ra, vui lòng thử lại."})
            return
        finally:
            tracker.log_summary()

        final_content = final_content or "Xin lỗi, tôi chưa có câu trả lời."
        if new_messages:
            memory_manager.update(session_id, {"messages": messages + new_messages})

        logger.info("chat stream response", extra={"session_id": session_id, "reply": final_content})
        yield _sse("usage", _usage.to_dict())
        yield _sse("done", {"reply": final_content, "session_id": session_id})

        # Gợi ý câu hỏi tiếp theo — tính SAU khi đã phát "done" để không trì hoãn câu trả lời.
        suggestions = await suggest_followups(messages, final_content)
        if suggestions:
            yield _sse("suggestions", {"suggestions": suggestions})

    # SSEResponse (dqh.svc_core) đã set sẵn header chặn buffer ở reverse proxy
    # (Cache-Control: no-cache, X-Accel-Buffering: no, Connection: keep-alive).
    return SSEResponse(event_generator())

"""Định nghĩa các tuyến API cho chatbot."""

import json
import logging
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.graph.graph import get_graph
from app.logging import get_logger
from app.memory import memory_manager, sanitize_tool_call_history
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()
logger = get_logger("api.routes")

NODE_EVENT_TYPES = {
    "agent": "SEARCHING",
}


@router.get("/health")
def health() -> dict[str, str]:
    """Check health của dịch vụ chatbot."""
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Nhận tin nhắn từ client, giữ memory phiên và trả về câu trả lời."""
    session_id = request.session_id or str(uuid.uuid4())
    session_memory = memory_manager.get(session_id)
    history = sanitize_tool_call_history(session_memory.get("messages", []))
    messages = history + [{"role": "user", "content": request.message}]

    logger.info("chat request", extra={"session_id": session_id, "user_message": request.message})
    graph = get_graph()

    try:
        result = await graph.ainvoke({"messages": messages})
    except Exception:
        logger.exception("chat failed", extra={"session_id": session_id})
        raise HTTPException(status_code=500, detail="Đã có lỗi xảy ra, vui lòng thử lại.")

    last_message = result["messages"][-1]
    content = last_message.content if hasattr(last_message, "content") else last_message["content"]

    # Lưu toàn bộ trace (bao gồm tool call/tool result) để lượt sau còn số liệu gốc làm căn cứ.
    memory_manager.update(session_id, {"messages": result["messages"]})
    logger.info("chat response", extra={"session_id": session_id, "reply": content})

    return ChatResponse(reply=content, session_id=session_id)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Stream trạng thái xử lý + token trả lời qua Server-Sent Events.

    Chỉ có 1 node "agent" — nó vừa gọi tool vừa sinh câu trả lời cuối trong cùng 1 vòng ReAct.
    Chunk có nội dung text (không phải tool-call) chỉ xuất hiện ở lượt trả lời cuối cùng, nên stream
    thẳng mọi on_chat_model_stream của node này là an toàn (xem app/agents/base.py).
    """
    session_id = request.session_id or str(uuid.uuid4())
    session_memory = memory_manager.get(session_id)
    history = sanitize_tool_call_history(session_memory.get("messages", []))
    messages = history + [{"role": "user", "content": request.message}]

    logger.info("chat stream request", extra={"session_id": session_id, "user_message": request.message})

    async def event_generator():
        graph = get_graph()
        reply_text = ""
        last_node_message = None
        # Gom toàn bộ message mới sinh ra (tool call, tool result, câu trả lời cuối) để lưu đủ trace
        # vào memory, thay vì chỉ câu trả lời cuối — xem app/agents/base.py.
        new_messages: list = []

        try:
            async for event in graph.astream_events({"messages": messages}, version="v2"):
                kind = event.get("event")
                metadata = event.get("metadata") or {}
                node = metadata.get("langgraph_node")
                # create_react_agent (bên trong agent_node) là 1 sub-graph LangGraph có node cũng
                # tên "agent"/"tools" — checkpoint_ns của event phát sinh từ sub-graph đó chứa "|"
                # (nối namespace cha|con). Phải loại các event này, chỉ giữ event của graph ngoài
                # cùng — nếu không, on_chain_end sẽ khớp CẢ lần node "agent" bên trong kết thúc
                # (chỉ có AIMessage tool_calls, CHƯA có ToolMessage vì node "tools" bên trong chưa
                # chạy xong) khiến new_messages bị lưu 1 AIMessage(tool_calls) mồ côi — lượt chat
                # sau gửi lại messages này, OpenAI trả lỗi 400 "tool_calls must be followed by
                # tool messages".
                is_top_level = "|" not in metadata.get("checkpoint_ns", "")

                # Mỗi lần agent gọi 1 tool cụ thể -> phát 1 bước riêng (thay vì gộp chung 1 bước
                # "Đang tra cứu dữ liệu" cho toàn bộ vòng ReAct) để người dùng thấy rõ đang tra cứu
                # cái gì. Event tool nằm trong sub-graph (checkpoint_ns có "|") nên KHÔNG lọc theo
                # is_top_level như on_chain_start/end ở trên.
                if kind == "on_tool_start":
                    tool_name = event.get("name") or "tool"
                    yield _sse("status", {"node": tool_name, "type": "SEARCHING", "module": tool_name})

                elif kind == "on_chat_model_stream" and node == "agent":
                    chunk = event["data"]["chunk"]
                    piece = getattr(chunk, "content", "") or ""
                    if isinstance(piece, str) and piece:
                        reply_text += piece
                        yield _sse("token", {"content": piece})

                elif kind == "on_chain_end" and node in NODE_EVENT_TYPES and is_top_level:
                    output = event["data"].get("output") or {}
                    node_messages = output.get("messages") if isinstance(output, dict) else None
                    if node_messages:
                        new_messages.extend(node_messages)
                        last_node_message = node_messages[-1]

        except Exception:
            logger.exception("chat stream failed", extra={"session_id": session_id})
            yield _sse("error", {"message": "Đã có lỗi xảy ra, vui lòng thử lại."})
            return

        if last_node_message is not None:
            final_content = (
                last_node_message.content if hasattr(last_node_message, "content") else last_node_message["content"]
            )
            memory_manager.update(session_id, {"messages": messages + new_messages})
        else:
            final_content = reply_text or "Xin lỗi, tôi chưa có câu trả lời."

        logger.info("chat stream response", extra={"session_id": session_id, "reply": final_content})
        yield _sse("done", {"reply": final_content, "session_id": session_id})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            # Chặn buffer ở reverse proxy (nginx/Next.js dev tunnel...) để event tới browser ngay khi có,
            # không đợi gộp hết response mới gửi.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

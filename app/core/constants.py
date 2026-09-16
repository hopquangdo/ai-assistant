"""Hằng số cấu hình agent — tách khỏi core/config.py (Settings từ .env) vì đây là giá trị cố định
trong code, không phải config runtime."""

# Model mặc định khi client không chọn — None nghĩa là dùng settings.llm_model_name.
AGENT_MODEL: str | None = None

# Giá trị đặc biệt: mỗi node tự dùng model mặc định riêng.
AUTO_MODEL = "auto"

# Model cho phép chọn ở frontend (dropdown) — giới hạn model OpenAI đã có giá trong
# model_prices.json (xem package/ai_core/data/model_prices.json) vì backend hiện gọi thẳng
# OpenAI (LLM_BASE_URL rỗng, xem app/llm/client.py). Thêm model khác vào đây CHỈ SAU KHI đã có
# base_url/API key phù hợp cho model đó.
AVAILABLE_MODELS: list[str] = [
    AUTO_MODEL,
    "gpt-5.6-luna",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-4o-mini",
]

# Chặn cứng vòng lặp ReAct của planner (mỗi vòng "agent quyết định -> gọi tool" tốn 2 bước graph,
# KHÔNG tính theo số tool call nếu gọi song song nhiều tool trong 1 vòng). 10 bước ~ đủ cho câu
# hỏi cần đối chiếu 2-3 lĩnh vực cùng lúc; vượt ngưỡng này gần như chắc chắn là agent đang "mò"
# tool sai vì không có tool nào khớp đúng câu hỏi, chứ không phải câu hỏi hợp lệ cần nhiều vòng
# hơn.
AGENT_RECURSION_LIMIT = 10

# Câu trả lời an toàn khi planner chạm AGENT_RECURSION_LIMIT — dùng chung cho /chat và
# /chat/stream (xem app/api/routes/chat.py) để 2 endpoint trả lời nhất quán khi rơi vào cùng 1
# tình huống.
RECURSION_LIMIT_FALLBACK_TEXT = (
    "Hệ thống hiện chưa có dữ liệu/tool phù hợp để trả lời chính xác câu hỏi này "
    "(có thể câu hỏi cần một khái niệm nghiệp vụ mà hệ thống chưa theo dõi). "
    "Anh/chị có thể mô tả lại theo hướng cụ thể hơn, hoặc hỏi từng phần riêng lẻ."
)

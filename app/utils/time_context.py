"""Cung cấp ngày hiện tại của hệ thống dưới dạng SystemMessage, tiêm động mỗi lần gọi LLM.

Không dùng tool để LLM tự quyết định gọi — đã thử và LLM bỏ qua hướng dẫn "bắt buộc gọi tool trước"
dù prompt ghi rõ, dẫn tới suy đoán sai năm hiện tại. Tiêm thẳng ngày thật vào system message là cách
duy nhất đảm bảo chắc chắn đúng.
"""

from datetime import date

from langchain_core.messages import SystemMessage

_WEEKDAY_VI = {
    0: "Thứ Hai",
    1: "Thứ Ba",
    2: "Thứ Tư",
    3: "Thứ Năm",
    4: "Thứ Sáu",
    5: "Thứ Bảy",
    6: "Chủ Nhật",
}


def current_date_system_message() -> SystemMessage:
    """Tạo SystemMessage nêu rõ ngày hiện tại của hệ thống, tính lại mỗi lần gọi (không cache)."""
    today = date.today()
    weekday = _WEEKDAY_VI[today.weekday()]
    return SystemMessage(
        content=(
            f"NGÀY HIỆN TẠI CỦA HỆ THỐNG: {today.isoformat()} ({weekday}). "
            "Dùng ngày này làm mốc DUY NHẤT để quy đổi mọi thời gian tương đối trong câu hỏi "
            "(vd \"tháng này\", \"tháng trước\", \"tuần này\", \"hôm nay\", \"gần đây\") sang ngày "
            "tháng năm cụ thể. TUYỆT ĐỐI không tự đoán năm hiện tại từ kiến thức khác."
        )
    )

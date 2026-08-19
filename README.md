# Chatbot VTK

Chatbot nghiệp vụ nội bộ Viettel — FastAPI + LangGraph, trả lời câu hỏi dựa trên dữ liệu thật lấy qua
MCP từ backend Java (Spring AI).

## Yêu cầu trước khi chạy

- Backend Java (`../backend`) đang chạy, cổng mặc định `8080`, endpoint MCP: `http://localhost:8080/mcp`.
- Python 3.12+ (venv đã có sẵn tại `.venv`, không cần tạo lại).
- File `.env` ở thư mục gốc `chatbot/` với 2 biến bắt buộc:
  ```
  OPENAI_API_KEY=sk-...
  MCP_SERVER_URL=http://localhost:8080/mcp
  ```

## Chạy chatbot

```powershell
cd D:\Workspace\Work\Rdsic\Viettel\chatbot
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Chatbot chạy ở `http://localhost:8000`. Log khởi động sẽ in số tool + tên tool đã nạp được từ MCP theo
từng module — nếu backend Java chưa chạy hoặc sai `MCP_SERVER_URL`, sẽ thấy log lỗi kết nối ngay lúc
startup nhưng app vẫn khởi động được (tool rỗng, agent sẽ không trả lời được câu hỏi cần dữ liệu).

**Lưu ý về `--reload`:** chỉ tự nạp lại khi sửa file `.py`. Sửa file trong `app/prompts/*.txt` (system
prompt của orchestrator/module/responder) **không** tự reload — phải dừng (Ctrl+C) và chạy lại lệnh
trên để prompt mới có hiệu lực.

## Test nhanh

```powershell
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{\"message\": \"tong quan hop dong hien tai the nao\"}'
```

Với câu hỏi có dấu tiếng Việt, tránh gõ trực tiếp trong `curl` trên PowerShell (dễ lỗi encoding) — nên
dùng Postman, hoặc tạo file JSON UTF-8 rồi gọi `curl --data-binary @file.json`.

Endpoint stream (SSE, dùng cho frontend hiển thị theo token):

```
POST /chat/stream
```

Bộ câu hỏi mẫu để test thủ công: `tests/sample_questions.csv` (danh sách câu hỏi) và
`tests/bo_cau_hoi_mau_va_tool.xlsx` (đầy đủ câu hỏi + tool tương ứng + trạng thái đã làm/chưa làm).

## Cấu trúc chính

```
app/
  main.py              # FastAPI app, nạp tool MCP lúc khởi động
  api/routes.py         # /chat, /chat/stream
  graph/                # LangGraph: orchestrator -> module (song song) -> responder
  agents/
    orchestrator/        # Quyết định CONTINUE/COMPLETE/ASK_USER + chọn module cần chạy
    tiendo|nhansu|vanhanh/ # 3 module nghiệp vụ (ReAct agent, tự gọi tool MCP)
    responder/            # Tổng hợp câu trả lời cuối cùng
    base.py               # Logic dùng chung để build/chạy 1 module agent
  prompts/              # System prompt dạng .txt cho từng agent (sửa xong phải restart, xem trên)
  tools/__init__.py     # Phân nhóm tool MCP theo prefix tên -> module (vd hopdong_* -> tiendo)
  mcp/client.py          # Kết nối MCP tới backend Java
  memory.py              # Lưu lịch sử hội thoại theo session_id (in-memory, mất khi restart)
  utils/time_context.py  # Tiêm ngày hiện tại thật vào system message mỗi lần gọi LLM
```

## Đổi model cho từng agent

Model được khai trực tiếp trong code (không qua `.env`), để `None` = dùng model mặc định
(`settings.llm_model` trong `app/config/settings.py`):

- `app/agents/orchestrator/agent.py` → hằng số `ORCHESTRATOR_MODEL`
- `app/agents/responder/agent.py` → hằng số `RESPONDER_MODEL`
- `app/agents/base.py` → dict `MODULE_MODELS` (`tiendo`/`nhansu`/`vanhanh`)

Sửa xong nhớ restart (đây là file `.py` nên `--reload` tự nạp lại, không cần Ctrl+C).

## Routing tool theo module

`app/tools/__init__.py` gom tool MCP vào 3 module theo **prefix tên tool**:

| Prefix | Module |
|---|---|
| `hopdong_`, `sanluong_` | `tiendo` |
| `phancong_`, `nguonluc_` | `nhansu` |
| `tramton_`, `vuongmac_` | `vanhanh` |

Thêm tool mới ở backend Java thì phải đặt tên đúng 1 trong các prefix trên để chatbot tự route đúng
module — nếu không, cần sửa `_MODULE_PREFIXES` trong file này.

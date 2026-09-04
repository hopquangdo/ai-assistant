# Chatbot VTK

Chatbot nghiệp vụ nội bộ Viettel — FastAPI + LangGraph, trả lời câu hỏi dựa trên dữ liệu thật lấy qua
MCP từ backend Java (Spring AI).

## Yêu cầu trước khi chạy

- Backend Java (`../backend`) đang chạy, cổng mặc định `8080`, endpoint MCP: `http://localhost:8080/mcp`.
- Python 3.12+ (venv đã có sẵn tại `.venv`, không cần tạo lại).
- File `.env` ở thư mục gốc `chatbot/` với các biến:
  ```
  OPENAI_API_KEY=sk-...
  MCP_SERVER_URL=http://localhost:8080/mcp
  MCP_API_KEY=...        # phải khớp APP_MCP_API_KEY ở backend/.env (backend fail-closed: thiếu key -> 503)
  ```
  Backend Java gửi khóa qua header `X-API-Key` (không prefix) — header/scheme đã set sẵn trong
  `app/settings.py`. Client MCP là `dqh.ai_core.MCPClient` / `load_mcp_tools` (gói `package/ai_core`),
  `app/mcp_client.py` chỉ gọi lại kèm `Settings` của app.

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

Kiến trúc: **1 agent ReAct duy nhất** (`langgraph.prebuilt.create_react_agent`), không
orchestrator/router/responder riêng — agent tự chọn tool MCP, tự gọi, tự viết câu trả lời cuối
trong cùng 1 vòng lặp. Các gói con trước đây chỉ có đúng 1 file `.py` đã được gộp phẳng vào thẳng
`app/` cho gọn (không còn `agents/`, `api/`, `config/`, `llm/`, `mcp/`, `tools/` dạng package).

```
app/
  main.py              # FastAPI app, nạp tool MCP lúc khởi động
  routes.py            # /health, /chat, /chat/stream (stream trực tiếp từ agent, không qua graph bọc ngoài)
  agent.py             # Agent ReAct duy nhất: get_agent()/run_agent(), guard recursion_limit, log tool call + token/cost
  settings.py          # Cấu hình đọc từ .env (pydantic-settings)
  llm_client.py         # Factory ChatOpenAI dùng chung
  mcp_client.py          # Kết nối MCP tới backend Java, discover tool lúc khởi động
  tools.py              # ALL_TOOLS — danh sách tool discover được từ MCP (loại trừ thoigian_*)
  prompts/              # AGENT_PROMPT (agent.txt) — sửa xong phải restart, xem trên
  memory.py             # Lưu lịch sử hội thoại theo session_id (in-memory, mất khi restart)
  schemas/              # Pydantic schema request/response + GraphState
  utils/time_context.py # Tiêm ngày hiện tại thật vào system message mỗi lần gọi LLM
```

## Đổi model cho agent

Model khai trực tiếp trong code (không qua `.env`), để `None` = dùng model mặc định
(`settings.llm_model` trong `app/settings.py`):

- `app/agent.py` → hằng số `AGENT_MODEL`

Sửa xong nhớ restart (đây là file `.py` nên `--reload` tự nạp lại, không cần Ctrl+C).

## Tool MCP

`app/tools.py` nạp TOÀN BỘ tool discover được từ MCP server vào 1 danh sách phẳng `ALL_TOOLS`
(loại trừ tool có prefix `thoigian_` — ngày hiện tại được tiêm thẳng vào system message thay vì để
agent tự gọi tool, xem `app/utils/time_context.py`). Không phân nhóm/route theo prefix tên nữa —
thêm tool mới ở backend Java không cần sửa gì ở đây, agent tự đọc description của tool để quyết
định dùng khi nào (xem `app/prompts/agent.txt` mục PHẠM VI NGHIỆP VỤ).

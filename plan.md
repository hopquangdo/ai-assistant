# Plan: sinh JSON biểu đồ cho frontend

## 0. Trả lời nhanh: có nên dùng LLM để sinh chart không?

**Có, nhưng là 1 LLM call riêng ở NODE CUỐI (sau executor), dùng structured output — không phải
tool cho planner gọi giữa vòng ReAct.**

- Nếu để planner gọi `generate_chart` như 1 tool giữa vòng ReAct, planner có thể gọi SỚM (ngay sau
  tool nghiệp vụ đầu tiên) trước khi biết toàn cảnh câu hỏi cần so sánh gì — dễ ra chart lệch với
  nội dung executor viết sau đó, vì 2 agent quyết định độc lập trên 2 lượt suy luận khác nhau.
- Đặt ở **node cuối cùng** (ngay sau khi executor đã có text trả lời hoàn chỉnh) đảm bảo chart và
  text luôn nhất quán: chart-agent nhìn thấy CẢ tool results LẪN câu trả lời cuối cùng đã chốt, chỉ
  việc "đóng gói lại" phần số liệu đã được xác nhận đúng thành spec trực quan — không suy luận
  nghiệp vụ mới, không có nguy cơ lệch pha với text.
- Vẫn dùng LLM (không phải rule cứng) vì "chọn chart_type nào, nhóm theo category nào" là quyết
  định ngữ nghĩa phụ thuộc câu hỏi — nhưng ép qua **structured output** (schema cứng), không qua
  tool-calling tự do, và **không tự bịa số**: prompt yêu cầu chỉ dùng số đã xuất hiện trong tool
  results/text, nếu không đủ căn cứ để vẽ thì trả `chart: null`.
- Validate lại bằng Pydantic ở tầng code trước khi bắn ra FE — không tin LLM tự đảm bảo đúng cấu
  trúc dù đã dùng structured output.
- Vẽ chart thật sự (canvas/SVG) **không dùng LLM** — việc của frontend, nhận JSON spec map sang
  1 trong các component chart ĐÃ ĐỊNH NGHĨA SẴN. Backend không quyết cách vẽ, chỉ quyết "loại chart
  nào trong danh sách FE hỗ trợ + số liệu gì".

## 1. Kiến trúc luồng dữ liệu — 3 node

```
START -> react (planner, LLM, ReAct loop gọi tool nghiệp vụ MCP)      -- không đổi
      -> response (executor, LLM, viết text trả lời cuối)              -- không đổi
      -> genchart (chart-agent, LLM, structured output, KHÔNG stream)  -- NODE MỚI
      -> END
```

- **react**: giữ nguyên. Chọn & gọi tool nghiệp vụ tới khi đủ dữ liệu, dừng.
- **response**: giữ nguyên. Đọc tool results, viết text trả lời (stream token ra SSE như hiện tại).
- **genchart** (mới): đọc `tool results + text vừa chốt`, gọi LLM với
  `model.with_structured_output(ChartDecision)`, trả `{chart: ChartSpec | None}`. Nếu có chart,
  Pydantic double-check invariant liên-field (structured output của một số provider không tự
  enforce validator, vd `len(series.data) == len(categories)`). Chạy sau khi text đã stream xong,
  không chặn tốc độ hiển thị câu trả lời đầu tiên.

Orchestrator (SSE):
```
... stream "token" như hiện tại (không đổi) ...
-> "done" (reply text, như hiện tại)
-> nếu genchart trả chart hợp lệ -> "chart" (JSON)
-> "suggestions" (như hiện tại, sau "done")
```

Nguyên tắc giữ nguyên: planner vẫn KHÔNG viết câu trả lời, executor vẫn KHÔNG gọi tool,
response.txt vẫn cấm JSON trong text — chart-agent là 1 bước hoàn toàn tách biệt.

## 2. Schema — `app/schemas/chart.py` (file mới)

Đây là **hợp đồng dùng chung giữa BE và FE** — FE định nghĩa sẵn tập component chart nào thì
`ChartType` ở đây phải khớp chính xác tập đó (xem mục Frontend). Thêm/bớt 1 loại chart luôn cần
sửa đồng thời cả 2 phía.

```python
"""Schema cho biểu đồ trực quan hoá — output của node genchart, tiêu thụ bởi frontend. Đây là
HỢP ĐỒNG (contract) với FE: ChartType phải khớp đúng tập component FE đã định nghĩa sẵn (xem
frontend/src/charts/registry.ts). Thay đổi field phải bump CHART_SCHEMA_VERSION."""

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

CHART_SCHEMA_VERSION = 1

# Phải khớp 1-1 với key trong CHART_REGISTRY phía frontend.
ChartType = Literal["bar", "line", "pie", "donut", "stacked_bar", "area"]

MAX_CATEGORIES = 12
MAX_SERIES = 6


class ChartSeries(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    data: list[float] = Field(..., min_length=1)


class ChartSpec(BaseModel):
    chart_type: ChartType
    title: str = Field(..., min_length=1, max_length=200)
    categories: list[str] = Field(..., min_length=1, max_length=MAX_CATEGORIES)
    series: list[ChartSeries] = Field(..., min_length=1, max_length=MAX_SERIES)
    unit: Optional[str] = Field(default=None, max_length=50)
    note: Optional[str] = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _check_shape(self) -> "ChartSpec":
        n = len(self.categories)
        for s in self.series:
            if len(s.data) != n:
                raise ValueError(
                    f"series '{s.name}' có {len(s.data)} điểm dữ liệu nhưng có {n} categories."
                )
        if self.chart_type in ("pie", "donut") and len(self.series) != 1:
            raise ValueError("pie/donut chỉ nhận đúng 1 series.")
        return self


class ChartDecision(BaseModel):
    """Schema structured-output của node genchart — LLM điền đúng field này."""

    has_chart: bool = Field(
        description="False nếu dữ liệu không đủ/không phù hợp để vẽ chart."
    )
    chart: Optional[ChartSpec] = Field(
        default=None, description="Bắt buộc có khi has_chart=True, bỏ trống khi False."
    )


class ChartPayload(BaseModel):
    """Payload thật sự bắn ra SSE/API cho FE."""

    schema_version: int = CHART_SCHEMA_VERSION
    spec: ChartSpec
```

Giới hạn `MAX_CATEGORIES=12`, `MAX_SERIES=6`: tránh chart quá nhiều cột/nhóm không đọc được — ép
LLM chọn top-N/nhóm lại, đúng tinh thần "so sánh có sẵn trong dữ liệu" đã có trong `response.txt`.

`has_chart` tách riêng khỏi `chart` (thay vì chỉ dùng `chart: Optional[...]`) vì một số provider
structured-output xử lý `Optional[Model]` không ổn định (dễ tự ý điền field rỗng thay vì null) —
cờ boolean tường minh giúp parse chắc chắn hơn.

## 3. Refactor cấu trúc thư mục — package theo node, mỗi file 1 nhiệm vụ, ưu tiên class

Yêu cầu: `app/agents/` tổ chức lại theo đúng khái niệm graph — mỗi node là 1 class trong 1 file
riêng, không gộp nhiều trách nhiệm vào 1 file như `planner.py`/`executor.py` hiện tại.

```
app/agents/
  __init__.py
  state.py                 # OrchestratorState (TypedDict) — CHỈ định nghĩa state, không logic
  graph.py                 # ChatGraph — lắp 3 node thành StateGraph, compile 1 lần (lru_cache)
  orchestrator.py          # AgentOrchestrator — chạy graph, dịch LangGraph event -> AgentEvent
                            #   (TokenEvent/ToolStartEvent/ToolEndEvent/DoneEvent/ChartEvent) cho
                            #   tầng route dùng, KHÔNG chứa logic nghiệp vụ của từng node
  nodes/
    __init__.py             # export ReactNode, ResponseNode, GenChartNode
    base.py                 # Node — base class tối thiểu (contract __call__)
    node_react.py           # ReactNode — chọn & gọi tool nghiệp vụ (thay planner.py)
    node_response.py        # ResponseNode — viết text trả lời cuối (thay executor.py)
    node_genchart.py        # GenChartNode — structured output quyết định chart
  prompts/                  # giữ nguyên (select.txt, response.txt, + chart.txt mới)
  chart_agent.py            # XOÁ — logic dời vào nodes/node_genchart.py
  planner.py                # XOÁ — logic dời vào nodes/node_react.py
  executor.py                # XOÁ — logic dời vào nodes/node_response.py
```

### `nodes/base.py`

```python
"""Contract chung cho 1 node trong graph chatbot — mỗi node là 1 class thuần, nhận state +
config, trả dict patch cho state (đúng convention của StateGraph)."""

from typing import Protocol


class Node(Protocol):
    async def __call__(self, state: dict, config: dict) -> dict: ...
```

### `nodes/node_react.py`

```python
"""ReactNode — node CHỌN TOOL (ReAct). Nhiệm vụ DUY NHẤT: lặp gọi tool nghiệp vụ (MCP) tới khi đủ
dữ liệu rồi dừng. KHÔNG viết câu trả lời cuối — xem nodes/node_response.py."""

from functools import lru_cache

from langgraph.errors import GraphRecursionError

from dqh.ai_core import Agent

from src.agents.prompts import SELECT_PROMPT
from src.core.constants import AGENT_MODEL, AGENT_RECURSION_LIMIT, RECURSION_LIMIT_FALLBACK_TEXT
from src.llm.client import get_chat_model
from langchain_core.messages import AIMessage


class ReactNode:
    def __init__(self, tools: list, model: str | None = None):
        self._tools = tools
        self._model = model or AGENT_MODEL

    @property
    @lru_cache
    def agent(self) -> Agent:
        return Agent.create(tools=self._tools, model=get_chat_model(self._model), system=SELECT_PROMPT)

    async def __call__(self, state: dict, config: dict) -> dict:
        try:
            result = await self.agent.graph.ainvoke(
                {"messages": state["messages"]},
                config={**config, "recursion_limit": AGENT_RECURSION_LIMIT},
            )
            new_messages = result["messages"][len(state["messages"]):]
            return {"messages": new_messages, "recursion_hit": False}
        except GraphRecursionError:
            return {"messages": [AIMessage(content=RECURSION_LIMIT_FALLBACK_TEXT)], "recursion_hit": True}
```

(`@property @lru_cache` trên method instance chỉ minh hoạ ý — thực tế Python không cache theo
instance kiểu này gọn gàng; lúc code thật dùng `functools.cached_property` thay thế.)

### `nodes/node_response.py`

```python
"""ResponseNode — node TỔNG HỢP CÂU TRẢ LỜI, không có tool. Đọc lại hội thoại (đã có kết quả tool
từ ReactNode) và viết câu trả lời cuối cho người dùng."""

from functools import cached_property

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage

from src.agents.prompts import RESPONSE_PROMPT
from src.core.constants import AGENT_MODEL
from src.llm.client import get_chat_model


def strip_trailing_placeholder(messages: list) -> list:
    if messages and isinstance(messages[-1], AIMessage) and not messages[-1].tool_calls:
        return messages[:-1]
    return messages


class ResponseNode:
    def __init__(self, model: str | None = None):
        self._model = model or AGENT_MODEL

    @cached_property
    def llm(self) -> BaseChatModel:
        return get_chat_model(self._model)

    async def __call__(self, state: dict, config: dict) -> dict:
        kept = strip_trailing_placeholder(state["messages"])
        reply = await self.llm.ainvoke([SystemMessage(content=RESPONSE_PROMPT), *kept], config=config)
        return {"messages": [AIMessage(content=reply.content)]}
```

### `nodes/node_genchart.py`

```python
"""GenChartNode — node CUỐI CÙNG, chạy sau ResponseNode. Đọc tool results + text đã chốt, quyết
định có nên sinh 1 biểu đồ trực quan hoá hay không, sinh đúng schema ChartSpec qua structured
output. KHÔNG suy luận nghiệp vụ mới — chỉ "đóng gói lại" số liệu đã có."""

import logging
from functools import cached_property

from langchain_core.messages import SystemMessage

from src.agents.prompts import CHART_PROMPT
from src.core.constants import AGENT_MODEL
from src.llm.client import get_chat_model
from src.schemas.chart import ChartDecision, ChartPayload

logger = logging.getLogger("chatbot.agent.genchart")


class GenChartNode:
    def __init__(self, model: str | None = None):
        self._model = model or AGENT_MODEL

    @cached_property
    def structured_llm(self):
        return get_chat_model(self._model).with_structured_output(ChartDecision)

    async def __call__(self, state: dict, config: dict) -> dict:
        try:
            decision: ChartDecision = await self.structured_llm.ainvoke(
                [SystemMessage(content=CHART_PROMPT), *state["messages"]], config=config,
            )
        except Exception:
            logger.warning("genchart failed (bỏ qua chart)", exc_info=True)
            return {"chart": None}
        if not decision.has_chart or decision.chart is None:
            return {"chart": None}
        return {"chart": ChartPayload(spec=decision.chart).model_dump()}
```

### `state.py`

```python
"""State của graph chatbot — CHỈ định nghĩa, không logic."""

from typing import Annotated, Optional, TypedDict

from langgraph.graph.message import add_messages


class OrchestratorState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    recursion_hit: bool
    chart: Optional[dict]
```

### `graph.py`

```python
"""ChatGraph — lắp 3 node (react -> response -> genchart) thành 1 StateGraph, compile 1 lần dùng
chung cho mọi request (model chọn qua config["configurable"]["model"] mỗi lần invoke)."""

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from src.agents.nodes.node_genchart import GenChartNode
from src.agents.nodes.node_react import ReactNode
from src.agents.nodes.node_response import ResponseNode
from src.agents.state import OrchestratorState
from src.tools.registry import ALL_TOOLS


def _route_after_react(state: OrchestratorState) -> str:
    return END if state.get("recursion_hit") else "response"


class ChatGraph:
    def __init__(self):
        self.react = ReactNode(ALL_TOOLS)
        self.response = ResponseNode()
        self.genchart = GenChartNode()

    def build(self):
        builder = StateGraph(OrchestratorState)
        builder.add_node("react", self.react)
        builder.add_node("response", self.response)
        builder.add_node("genchart", self.genchart)
        builder.add_edge(START, "react")
        builder.add_conditional_edges("react", _route_after_react, {"response": "response", END: END})
        builder.add_edge("response", "genchart")
        builder.add_edge("genchart", END)
        return builder.compile()


@lru_cache
def get_chat_graph():
    return ChatGraph().build()
```

Lưu ý: `react`/`response` hiện nhận `model` cố định lúc khởi tạo Node — vì API cho phép chọn model
mỗi request (`config["configurable"]["model"]`), cách đơn giản nhất giữ tương thích: Node đọc
model từ `config` bên trong `__call__` thay vì constructor (giống code cũ trong `graph.py` hiện
tại dùng `_model_of(config)`), tránh phải tạo lại `ChatGraph` theo từng model. Sửa từng Node để
lazy-resolve LLM theo `config.get("configurable", {}).get("model")` tại thời điểm gọi, cache theo
`model` bằng dict nội bộ thay vì 1 giá trị cố định — chi tiết này cần làm đúng lúc code thật, nêu
ra đây để không quên khi implement (khác với bản rút gọn ở trên chỉ minh hoạ ý tưởng).

### `orchestrator.py` (rút gọn còn lại — chỉ dịch event, không chứa logic node)

```python
"""AgentOrchestrator — chạy ChatGraph, dịch LangGraph stream event sang AgentEvent
(TokenEvent/ToolStartEvent/ToolEndEvent/DoneEvent/ChartEvent/ErrorEvent) cho tầng route dùng.
Đây là nguồn xử lý DUY NHẤT cho việc "chạy 1 lượt chat" — không chứa logic nghiệp vụ của node nào.
"""

class AgentOrchestrator:
    def __init__(self, graph):
        self._graph = graph

    async def run_stream(self, messages: list, model: str | None = None):
        # astream_events(..., version="v2"): lọc on_chat_model_stream theo
        # metadata["langgraph_node"] == "response" -> TokenEvent; on_tool_start/on_tool_end ở node
        # "react" -> ToolStartEvent/ToolEndEvent; state cuối có "chart" -> ChartEvent.
        ...

    async def run(self, messages: list, model: str | None = None) -> tuple[list, dict | None]:
        ...
```

Đây là thay đổi lớn nhất trong cả plan: **gộp 2 nguồn logic hiện có** (`orchestrator.py` tự stream
tay theo 2 phase, và `graph.py` là bản `StateGraph` song song chưa dùng thật) thành 1 nguồn duy
nhất — trực tiếp trả lời "quyết định cần chốt" ở mục 20 bản trước: có, hợp nhất, làm luôn trong đợt
refactor chart này vì đằng nào cũng phải sửa cấu trúc node.

**Rủi ro cần lường trước khi code**: `astream_events` của LangGraph có cấu trúc event khác hẳn
`dqh.ai_core.stream_agent` đang dùng — cần kiểm tra kỹ `dqh.ai_core` có hỗ trợ chạy trên 1 graph
tuỳ ý (không riêng ReAct) hay không, hoặc phải tự viết lớp dịch event mới thay cho `stream_agent`.
Đây là phần cần spike/thử nghiệm nhỏ trước khi cam kết toàn bộ refactor, không chỉ chép nguyên code
minh hoạ ở trên.

## 4. Prompt mới — `app/agents/prompts/chart.txt`

```
ROLE
Bạn là agent PHỤ TRÁCH QUYẾT ĐỊNH BIỂU ĐỒ. Bạn nhận toàn bộ hội thoại (kết quả tool nghiệp vụ +
câu trả lời cuối cùng đã được chốt cho người dùng). Nhiệm vụ DUY NHẤT: quyết định có nên vẽ 1
biểu đồ trực quan hoá minh hoạ cho câu trả lời đó không, và nếu có thì điền đúng số liệu.

QUY TẮC
- CHỈ dùng số liệu đã xuất hiện trong tool results hoặc câu trả lời text — không tự tính thêm số
  mới ngoài phép cộng/tỷ lệ đơn giản đã có sẵn trong dữ liệu.
- has_chart = false khi: câu hỏi chỉ hỏi 1 giá trị/1 đối tượng đơn lẻ, dữ liệu chỉ có 1 con số,
  hoặc không đủ ít nhất 2 nhóm/kỳ để so sánh.
- has_chart = true khi dữ liệu có từ 2 nhóm/danh mục/kỳ trở lên đáng so sánh (xếp hạng, tỷ trọng,
  xu hướng theo thời gian).
- Chọn chart_type:
  - "bar": so sánh nhiều đối tượng tại 1 thời điểm.
  - "line" hoặc "area": biến động theo thời gian (nhiều kỳ).
  - "pie" hoặc "donut": tỷ trọng cấu thành của 1 tổng thể (chỉ 1 series).
  - "stacked_bar": so sánh nhiều đối tượng, mỗi đối tượng gồm nhiều thành phần cộng lại.
- Tối đa 12 category, 6 series — nếu dữ liệu nhiều hơn, chọn nhóm nổi bật nhất (top-N) hoặc gộp
  phần còn lại vào "Khác", không cắt bỏ âm thầm.
- Không lặp lại nguyên văn toàn bộ câu trả lời vào "note" — note chỉ ghi ngắn gọn kỳ/nguồn dữ liệu.
```

`CHART_PROMPT` export từ `app/agents/prompts/__init__.py` giống `SELECT_PROMPT`/`RESPONSE_PROMPT`
hiện có.

## 5. Wiring graph — đã chốt ở mục 3

Kiến trúc `ChatGraph` (3 node) + `AgentOrchestrator` (dịch event) ở mục 3 THAY THẾ hoàn toàn cách
làm cũ (`planner.py`/`executor.py` + stream tay trong `orchestrator.py`). `ChartEvent` (dataclass
cạnh `UsageEvent`) do `AgentOrchestrator.run_stream` phát ra sau khi state graph có `chart` khác
`None`; `chat.py` (route SSE) thêm case xử lý (đặt trước `case UsageEvent`):

```python
case ChartEvent(payload=payload):
    yield _sse("chart", payload)
```

Thứ tự SSE thực tế: `token...` -> `done` -> `usage` -> `chart` (nếu có) -> `suggestions` (thứ tự
chính xác phụ thuộc cách `run_stream` duyệt `astream_events`, không quan trọng bằng việc `chart`
luôn tới sau `token` cuối cùng).

## 6. API không streaming — `POST /chat`

`ChatResponse` (`app/schemas/chat.py`) thêm field:

```python
charts: list[dict] = []
```

`AgentOrchestrator.run(...)` (thay cho hàm `run_agent` cũ) gom cả `messages` lẫn `chart` từ state
graph cuối cùng, trả `tuple[list, dict | None]` — `chat.py` route không-stream gọi trực tiếp
phương thức này thay vì import hàm rời như trước.

Đây là thay đổi **breaking signature** so với `run_agent` cũ — chỉ có 1 nơi gọi hiện tại (`chat.py`
route không-stream), cập nhật luôn nơi gọi đó.

## 7. Persist / lịch sử hội thoại — `app/services/chat_service.py`

Chart KHÔNG nằm trong `messages` (không giống bản nháp trước dùng tool) — nó là artefact riêng,
sinh ra ngoài luồng `messages` LangChain. Nếu cần replay lại lịch sử cho FE (mở lại phiên chat cũ),
phải **lưu `charts` kèm theo turn** khi `persist_turn` (thêm cột/field `charts: list[dict]` vào bản
ghi lịch sử), không thể suy ra lại từ `messages` như cách cũ.

## 8. Kiểm soát rủi ro / production hardening

- **Validation là lớp phòng thủ chính**: mọi `ChartSpec` qua Pydantic trước khi ra khỏi backend.
- **Giới hạn kích thước**: `MAX_CATEGORIES`, `MAX_SERIES`.
- **Không tự bịa số**: ràng buộc ở `chart.txt` — Pydantic không kiểm được "số có khớp tool nghiệp
  vụ hay không", chấp nhận giới hạn này (tương tự rủi ro executor tính sai phép chia, đã note
  trong `response.txt`).
- **Lỗi node genchart không vỡ luồng chat**: bọc `try/except` quanh `decide_chart`, log warning,
  coi như không có chart — KHÔNG raise lên làm hỏng response đã trả cho user.
- **Thêm 1 LLM call/lượt chat**: tăng latency tổng thể (dù không chặn text đầu tiên) và chi phí —
  cân nhắc dùng model rẻ/nhanh hơn `AGENT_MODEL` cho riêng bước này nếu cost là vấn đề (structured
  output JSON nhỏ không cần model mạnh nhất).
- **Logging**: log input/output của `decide_chart` giống style `tracker.log_summary()` hiện có, để
  audit khi FE báo chart sai số.

## 9. Test

- Unit test `ChartSpec`/`ChartDecision`: mismatch length, pie có >1 series, vượt MAX_CATEGORIES,
  `has_chart=False` bỏ qua `chart`, case hợp lệ.
- Unit test `decide_chart`: mock LLM trả structured output hợp lệ/không hợp lệ, kiểm return
  `ChartPayload | None` đúng.
- Integration test stream: giả lập executor trả text xong, `decide_chart` trả 1 chart hợp lệ ->
  kiểm SSE có đúng 1 event `chart` sau `done`.
- Integration test route `/chat` (non-stream): `ChatResponse.charts` đúng khi genchart quyết định
  có chart, rỗng khi không.

## 10. Thứ tự triển khai

1. `app/schemas/chart.py` (`ChartSpec`, `ChartDecision`, `ChartPayload`)
2. `app/agents/prompts/chart.txt` + export `CHART_PROMPT`
3. **Spike nhỏ trước**: xác nhận `dqh.ai_core` có hỗ trợ `astream_events`/chạy trên `StateGraph`
   tuỳ ý hay không (rủi ro nêu ở cuối mục 3) — quyết định cách viết `AgentOrchestrator` trước khi
   dời code, tránh làm rồi phát hiện không tương thích.
4. `app/agents/state.py`, `nodes/base.py`, `nodes/node_react.py`, `nodes/node_response.py`,
   `nodes/node_genchart.py` (dời logic từ `planner.py`/`executor.py`, viết mới `genchart`)
5. `app/agents/graph.py` — `ChatGraph`
6. `app/agents/orchestrator.py` — viết lại `AgentOrchestrator` theo kết quả spike ở bước 3
7. Xoá `planner.py`, `executor.py`, `chart_agent.py` (logic đã dời hết vào `nodes/`)
8. `app/api/routes/chat.py` — case SSE `chart`, field `charts` trong `ChatResponse`, gọi
   `AgentOrchestrator` thay vì hàm `run_agent`/`run_agent_stream` cũ
9. `app/services/chat_service.py` — `persist_turn` lưu kèm `charts`
10. Test (mục 9)
11. Test thủ công qua `/chat/stream` với câu hỏi so sánh nhiều hợp đồng/kỳ, xác nhận cả tool
    streaming lẫn token streaming vẫn hoạt động đúng như trước refactor (không có regression từ
    việc đổi cách stream)

---

# Phần Frontend

## 11. Nguyên tắc

FE **định nghĩa trước** một tập cố định các component chart (registry), backend chỉ được chọn
`chart_type` nằm trong tập đó — không có chart "tuỳ biến tự do". Điều này giữ UI nhất quán (màu
sắc, font, spacing theo 1 hệ thống — xem skill `dataviz`) và tránh LLM/BE quyết định layout.

```
Backend quyết: chart_type (trong danh sách cố định) + dữ liệu (categories/series/unit)
Frontend quyết: mọi thứ về hiển thị (màu, kích thước, animation, responsive, tooltip, legend)
```

## 12. Chart registry (TypeScript)

`frontend/src/charts/registry.ts`:

```ts
export type ChartType = "bar" | "line" | "pie" | "donut" | "stacked_bar" | "area";

export interface ChartSeries {
  name: string;
  data: number[];
}

export interface ChartSpec {
  chart_type: ChartType;
  title: string;
  categories: string[];
  series: ChartSeries[];
  unit?: string | null;
  note?: string | null;
}

export interface ChartPayload {
  schema_version: number;
  spec: ChartSpec;
}

export const CHART_REGISTRY: Record<ChartType, React.ComponentType<{ spec: ChartSpec }>> = {
  bar: BarChartView,
  line: LineChartView,
  area: AreaChartView,
  pie: PieChartView,
  donut: DonutChartView,
  stacked_bar: StackedBarChartView,
};
```

`ChartType` ở đây **phải khớp 1-1** với `ChartType` (Literal) phía `app/schemas/chart.py`. Đây là
điểm dễ lệch nhất giữa 2 team — xem mục 15 (đồng bộ contract) để giảm rủi ro.

## 13. Component `ChartRenderer` — điểm vào duy nhất

`frontend/src/charts/ChartRenderer.tsx`:

```tsx
import { CHART_REGISTRY, ChartPayload } from "./registry";

const SUPPORTED_SCHEMA_VERSION = 1;

export function ChartRenderer({ payload }: { payload: ChartPayload }) {
  if (payload.schema_version > SUPPORTED_SCHEMA_VERSION) {
    // Version FE chưa hỗ trợ (BE deploy trước FE) — ẩn thay vì crash.
    return null;
  }
  const View = CHART_REGISTRY[payload.spec.chart_type];
  if (!View) {
    console.warn(`Chart type không được hỗ trợ: ${payload.spec.chart_type}`);
    return null;
  }
  return (
    <div className="chart-card">
      <ChartCardHeader title={payload.spec.title} unit={payload.spec.unit} />
      <View spec={payload.spec} />
      {payload.spec.note && <p className="chart-note">{payload.spec.note}</p>}
    </div>
  );
}
```

Nguyên tắc: **fail-soft, không bao giờ crash** khung chat vì 1 chart lỗi/không hỗ trợ — trả `null`,
log console, phần text trả lời vẫn hiển thị bình thường.

## 14. Từng component chart (dùng Recharts làm ví dụ, đổi lib tuỳ FE đã chọn)

- `BarChartView`, `StackedBarChartView`: X = `categories`, mỗi phần tử `series` là 1 `<Bar>`
  (stack chung `stackId` cho bản stacked).
- `LineChartView`, `AreaChartView`: X = `categories` (coi như trục thời gian nếu categories là
  kỳ/tháng), mỗi `series` là 1 `<Line>`/`<Area>`.
- `PieChartView`, `DonutChartView`: dữ liệu = `categories[i] -> series[0].data[i]` (luôn đúng 1
  series, đã ràng buộc ở BE); donut chỉ khác bar ở `innerRadius`.

Toàn bộ dùng chung 1 bảng màu categorical + format số/đơn vị theo skill `dataviz` (không tự chọn
màu tuỳ tiện mỗi component).

## 15. Nhận payload từ backend

**Luồng streaming** (SSE, dùng nhiều hơn — xem `useChatStream` hook hiện có phía FE):

```ts
case "chart":
  appendChartToLastMessage(sessionId, event.data as ChartPayload);
  break;
```

Chart gắn vào **message cuối cùng** (message assistant vừa nhận `done`) dưới dạng
`message.charts: ChartPayload[]`, render bằng `<ChartRenderer payload={c} />` cho mỗi phần tử,
đặt dưới bong bóng text.

**Luồng non-stream** (`POST /chat`): `response.charts` map thẳng vào `message.charts` khi tạo
message assistant, không cần xử lý gì thêm.

**Load lại lịch sử hội thoại** (nếu có API riêng): mỗi message trả về từ BE phải kèm `charts` (đã
lưu ở mục 7) để render giống hệt lúc live.

## 16. Đồng bộ contract BE-FE (tránh lệch enum/field)

Vì `ChartType` tồn tại độc lập ở 2 codebase (Pydantic Literal vs TS union), rủi ro lệch khi thêm
loại chart mới. Chọn 1 trong 2 cách, khuyến nghị cách 1 nếu FE/BE khác repo như hiện tại:

1. **Quy ước thủ công + checklist PR**: thêm 1 dòng trong `plan.md`/README: "thêm chart_type mới
   luôn sửa đồng thời `app/schemas/chart.py` (BE) và `frontend/src/charts/registry.ts` (FE) trong
   cùng 1 PR/đợt release, review chéo 2 phía." Đơn giản, đủ dùng ở quy mô hiện tại.
2. **Generate type từ OpenAPI**: nếu BE đã expose OpenAPI schema (FastAPI tự có `/openapi.json`),
   FE dùng `openapi-typescript` generate `ChartType`/`ChartSpec` tự động, loại bỏ hoàn toàn khả
   năng lệch tay. Tốn công sức setup pipeline hơn — cân nhắc khi số loại chart tăng lên hoặc lệch
   contract từng gây lỗi thật.

## 17. Trạng thái rỗng / loading / lỗi phía FE

- Không có chart (`has_chart=false` ở BE, hoặc BE cũ chưa có field) → không render gì thêm, không
  hiện khung rỗng/skeleton chờ chart (vì chart tới SAU `done`, tránh UI "giật" chờ vô thời hạn nếu
  BE lỗi ở bước genchart).
- Chart tới trễ hơn text vài trăm ms (do node genchart chạy sau) là **hành vi bình thường**, không
  phải bug — FE không cần loading spinner riêng cho chart, chỉ cần "xuất hiện thêm" mượt (fade-in
  nhẹ) khi event `chart` tới.
- `chart_type` lạ (BE deploy field mới FE chưa kịp thêm component) → `ChartRenderer` trả `null` +
  log console, không crash, không hiện lỗi cho user.

## 18. Test phía Frontend

- Unit test từng `*ChartView` với fixture JSON mẫu cho mỗi `chart_type` (đặt ở
  `frontend/src/charts/__fixtures__/`), snapshot test.
- Test `ChartRenderer`: `schema_version` cao hơn hỗ trợ -> `null`; `chart_type` không có trong
  registry -> `null` + không throw.
- Test tích hợp luồng chat: mock SSE có event `chart` sau `done`, kiểm chart xuất hiện đúng dưới
  message tương ứng, không đè lên message khác nếu user gửi tiếp câu hỏi mới trong lúc chart đang
  tới (race condition — chart phải gắn đúng theo `session_id`/message id, không gắn vào "message
  cuối cùng hiện tại" một cách ngây thơ nếu có thể có 2 request chồng nhau).

## 19. Thứ tự triển khai Frontend

1. `frontend/src/charts/registry.ts` — type + `CHART_REGISTRY` (khung, component rỗng trước)
2. Từng `*ChartView` component (bar -> line/area -> pie/donut -> stacked_bar), theo skill
   `dataviz` cho màu/style
3. `ChartRenderer.tsx`
4. Wiring nhận SSE event `chart` -> `appendChartToLastMessage`
5. Wiring `POST /chat` response `charts` -> message
6. Test (mục 18)
7. Test thủ công: hỏi 1 câu so sánh nhiều hợp đồng, xác nhận chart đúng loại, đúng số, đúng vị trí
   (dưới text, đúng message)

---

## 20. Quyết định cần chốt trước khi code

- ~~Hợp nhất `graph.py` và luồng tay trong `orchestrator.py`~~ — **đã chốt: có**, refactor theo
  `ChatGraph` + package `nodes/` (mục 3), làm cùng đợt với chart. Rủi ro kỹ thuật còn lại (tương
  thích `dqh.ai_core` với `astream_events`) cần spike trước khi cam kết toàn bộ (xem bước 3, mục
  10).
- **Model riêng cho genchart hay dùng chung `AGENT_MODEL`** — ảnh hưởng cost/latency (mục 8).
- **Thứ tự SSE `chart` trước hay sau `done`** — ảnh hưởng UX nhẹ, không ảnh hưởng schema, có thể
  quyết lúc code.
- **Cách đồng bộ contract BE-FE** (mục 16) — quy ước thủ công hay generate từ OpenAPI.
</content>

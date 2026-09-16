from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.utils.function_calling import convert_to_openai_tool

from app.agents.nodes.node_base import Node
from app.agents.nodes.response.prompt import RESPONSE_PROMPT
from app.agents.nodes.response.schema import ResponseOutput
from app.core.constants import AGENT_MODEL
from app.core.messages import strip_trailing_placeholder
from app.llm.client import get_chat_model
from app.schemas.stream import StreamEvent, StreamEventName
from app.shared import dispatch_custom_event

# Dict/JSON-schema (khong phai Pydantic class) de with_structured_output tra ve
# dict tich luy dan trong luc stream. Voi Pydantic class, chunk chi xuat hien 1
# lan khi model sinh xong toan bo (vi instance can validate du field), nen mat
# hoan toan kha nang stream token.
_RESPONSE_SCHEMA = convert_to_openai_tool(ResponseOutput)["function"]


class ResponseNode(Node):
    """Sinh answer + should_generate_chart trong 1 lan goi model, dung Structured
    Outputs (response_format=json_schema) thay vi tool-calling: model chi co 1
    kenh content de sinh noi dung, nen answer luon duoc stream ngay, khong bi
    "nuot" boi nhanh tool_call nhu khi dung bind_tools.
    """

    def __init__(self):
        self._models = {}

    def _model_for(self, model: str | None):
        if model not in self._models:
            self._models[model] = get_chat_model(model or AGENT_MODEL).with_structured_output(
                _RESPONSE_SCHEMA
            )
        return self._models[model]

    async def __call__(self, state: dict, config: RunnableConfig) -> dict:
        model = (config.get("configurable") or {}).get("model")
        kept = strip_trailing_placeholder(state["messages"])

        await dispatch_custom_event(
            StreamEvent(name=StreamEventName.RESPONSE_START, payload={}),
            config,
        )

        sent = 0
        partial: dict = {}
        async for partial in self._model_for(model).astream(
            [SystemMessage(content=RESPONSE_PROMPT), *kept], config=config
        ):
            answer_so_far = partial.get("answer") or ""
            if len(answer_so_far) > sent:
                delta = answer_so_far[sent:]
                sent = len(answer_so_far)
                await dispatch_custom_event(
                    StreamEvent(name=StreamEventName.RESPONSE_DELTA, payload={"content": delta}),
                    config,
                )

        answer = (partial.get("answer") or "").strip()
        if not answer:
            answer = "Tôi đã lấy được dữ liệu, nhưng chưa tạo được phần diễn giải."
        output = ResponseOutput(
            answer=answer,
            should_generate_chart=bool(partial.get("should_generate_chart", False)),
        )

        await dispatch_custom_event(
            StreamEvent(name=StreamEventName.RESPONSE_COMPLETED, payload=output.model_dump()),
            config,
        )
        return {
            "messages": [AIMessage(content=output.answer)],
            "should_generate_chart": output.should_generate_chart,
        }

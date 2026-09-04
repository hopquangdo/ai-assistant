"""dqh.ai_core — lớp mỏng, tái dùng trên LangChain / LangGraph.

Tổ chức 2 tầng:
    core/      contract (ports) + value object + logic thuần + orchestrator + impl in-memory
      ├ agents/        Agent, stream_agent, ToolExecutor
      ├ conversation/  lịch sử 1 phiên: ConversationStore, History, Conversation
      ├ memory/        ghi nhớ dài hạn: MemoryStore, Memory, extract_memories
      ├ runtime/       chạy theo hàng đợi: AgentTask/Outcome, TaskSource/Sink, AgentWorker
      └ observability/ context.py  prompts/  tools/  structured.py
    adapters/  chạm hệ ngoài / dep tuỳ chọn: Settings (env), get_chat_model (provider),
               install_cache (global), MCP client (network), RedisConversationStore

Public API dưới đây ổn định — ``from dqh.ai_core import X``. Mọi thứ trả về kiểu LangChain gốc.
"""
from .adapters.llm_cache import (
    BaseCache,
    InMemoryCache,
    cache_disabled,
    clear_cache,
    install_cache,
)
from .adapters.llm_factory import DEFAULT_MODEL, get_chat_model
from .adapters.mcp import MCPClient, MCPServerConfig, load_mcp_tools
from .adapters.redis_conversation_store import RedisConversationStore
from .adapters.settings import Settings, get_settings
from .core.agents import (
    Agent,
    AgentEvent,
    DoneEvent,
    ErrorEvent,
    MessageEvent,
    TokenEvent,
    ToolCall,
    ToolEndEvent,
    ToolExecutor,
    ToolExecutorError,
    ToolResult,
    ToolStartEvent,
    UnknownToolError,
    stream_agent,
)
from .core.context import ContextBuilder
from .core.conversation import (
    Conversation,
    ConversationStore,
    History,
    InMemoryConversationStore,
    condense_history,
    deserialize_messages,
    serialize_messages,
    thread_config,
)
from .core.memory import (
    Embedder,
    InMemoryMemoryStore,
    Memory,
    MemoryItem,
    MemoryStore,
    extract_memories,
)
from .core.observability import (
    PRICE_TABLE,
    PRICES,
    USD_TO_VND,
    Usage,
    UsageTracker,
    cached_price_for,
    price_for,
    usd_to_vnd,
)
from .core.prompts import PromptNotFound, PromptRegistry
from .core.runtime import (
    AgentOutcome,
    AgentTask,
    AgentWorker,
    InMemoryOutcomeSink,
    InMemoryTaskSource,
    OutcomeSink,
    TaskSource,
)
from .core.structured import StructuredOutputError, extract
from .core.tools import BaseTool, StructuredTool, compact_tool_output, image_block, text_block, tool

__all__ = [
    "Agent",
    "ToolCall",
    "ToolExecutor",
    "ToolExecutorError",
    "ToolResult",
    "UnknownToolError",
    "get_chat_model",
    "load_mcp_tools",
    "MCPClient",
    "MCPServerConfig",
    "Settings",
    "get_settings",
    "DEFAULT_MODEL",
    "BaseTool",
    "StructuredTool",
    "tool",
    "text_block",
    "image_block",
    "Usage",
    "UsageTracker",
    "PRICES",
    "PRICE_TABLE",
    "price_for",
    "cached_price_for",
    "USD_TO_VND",
    "usd_to_vnd",
    "Conversation",
    "ConversationStore",
    "RedisConversationStore",
    "History",
    "InMemoryConversationStore",
    "condense_history",
    "thread_config",
    "serialize_messages",
    "deserialize_messages",
    "AgentEvent",
    "TokenEvent",
    "ToolStartEvent",
    "ToolEndEvent",
    "MessageEvent",
    "DoneEvent",
    "ErrorEvent",
    "stream_agent",
    "extract",
    "StructuredOutputError",
    "install_cache",
    "clear_cache",
    "cache_disabled",
    "BaseCache",
    "InMemoryCache",
    "ContextBuilder",
    "PromptRegistry",
    "PromptNotFound",
    "compact_tool_output",
    "Memory",
    "MemoryItem",
    "MemoryStore",
    "InMemoryMemoryStore",
    "Embedder",
    "extract_memories",
    "AgentTask",
    "AgentOutcome",
    "TaskSource",
    "OutcomeSink",
    "AgentWorker",
    "InMemoryTaskSource",
    "InMemoryOutcomeSink",
]

"""dqh.ai_core.core — contract (ports) + value object + logic thuần + orchestrator + impl in-memory.

Không chạm hệ ngoài, không phụ thuộc tuỳ chọn (trừ 1 cầu tiện lợi: ``Agent.create`` gọi
``adapters.llm_factory`` khi bạn truyền model dạng chuỗi). Sub-package:

    agents/        Agent, stream_agent, AgentEvent*, ToolExecutor
    conversation/  ConversationStore, History, Conversation, condense_history, thread_config
    memory/        MemoryStore, Memory, MemoryItem, extract_memories, Embedder
    runtime/       AgentTask/AgentOutcome, TaskSource/OutcomeSink, AgentWorker
    observability/ Usage, UsageTracker, price_for …
    prompts/       PromptRegistry
    tools/         compact_tool_output, text_block, image_block
    context.py     ContextBuilder
    structured.py  extract (structured output)

Public API ổn định ở ``dqh.ai_core`` — import từ đó cho tiện.
"""

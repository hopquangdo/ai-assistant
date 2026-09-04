"""dqh.ai_core.core.conversation — lịch sử / state của MỘT phiên hội thoại.

    store              ConversationStore (ABC) + serialize_messages / deserialize_messages
    inmemory_store     InMemoryConversationStore — RAM, không dep
    history            History — chuỗi làm sạch list[BaseMessage] đồng bộ, fluent
    condense           condense_history() — nén lượt cũ thành 1 SystemMessage (async, nhận llm)
    conversation       Conversation — gắn Agent + store, lo load/hygiene/run/save
    thread_config      dựng RunnableConfig {"configurable": {"thread_id": ...}}

Backend ngoài RAM: adapters (RedisConversationStore) hoặc langgraph checkpointer.
Ghi nhớ DÀI HẠN xuyên phiên -> xem ``dqh.ai_core.core.memory``.
"""
from dqh.ai_core.core.conversation.condense import condense_history
from dqh.ai_core.core.conversation.conversation import Conversation
from dqh.ai_core.core.conversation.history import History
from dqh.ai_core.core.conversation.inmemory_store import InMemoryConversationStore
from dqh.ai_core.core.conversation.store import (
    ConversationStore,
    deserialize_messages,
    serialize_messages,
)
from dqh.ai_core.core.conversation.thread_config import thread_config

__all__ = [
    "Conversation",
    "ConversationStore",
    "History",
    "InMemoryConversationStore",
    "condense_history",
    "thread_config",
    "serialize_messages",
    "deserialize_messages",
]

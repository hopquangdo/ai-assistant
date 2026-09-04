"""dqh.ai_core.adapters — tầng chạm hệ ngoài / phụ thuộc tuỳ chọn.

Import trực tiếp module con để rõ phụ thuộc:
    from dqh.ai_core.adapters.settings import get_settings
    from dqh.ai_core.adapters.llm_factory import get_chat_model      # provider
    from dqh.ai_core.adapters.llm_cache import install_cache          # global cache
    from dqh.ai_core.adapters.mcp import load_mcp_tools               # [mcp] extra
    from dqh.ai_core.adapters.redis_conversation_store import RedisConversationStore  # [redis] extra

(Các tên trên cũng có ở ``dqh.ai_core`` — public API ổn định.)
"""

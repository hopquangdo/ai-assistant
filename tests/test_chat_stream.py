import asyncio

import fakeredis.aioredis

from src.infrastructure.memory.store import memory_store
from src.infrastructure.message_queue.queue import RedisStreamQueue
from src.services.chat_stream_service import ChatStreamService
from src.services.conversation_service import ConversationService


def test_get_conversation_and_messages_from_memory():
    session_id = "session-read-1"
    memory_store.clear(session_id)
    memory_store.update(
        session_id,
        {
            "messages": [
                {"type": "human", "content": "Xin chào"},
                {"type": "ai", "content": "Chào bạn"},
            ],
            "charts": [{"title": "Biểu đồ demo"}],
        },
    )

    service = ConversationService()
    conversation = service.get_conversation(session_id)
    messages = service.get_messages(session_id)

    assert conversation["session_id"] == session_id
    assert conversation["charts"] == [{"title": "Biểu đồ demo"}]
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_get_paginated_messages_from_memory():
    session_id = "session-page-1"
    memory_store.clear(session_id)
    memory_store.update(
        session_id,
        {
            "messages": [
                {"type": "human", "content": f"msg-{idx}"}
                for idx in range(1, 25)
            ]
        },
    )

    service = ConversationService()
    payload = service.get_message_page(session_id, page=2, limit=10)

    assert payload["session_id"] == session_id
    assert payload["page"] == 2
    assert payload["limit"] == 10
    assert payload["total"] == 24
    assert payload["items"][0]["content"] == "msg-11"
    assert payload["items"][-1]["content"] == "msg-20"


def test_stream_queue_survives_consumer_before_producer(monkeypatch):
    async def fake_run(*args):
        return None

    async def scenario():
        service = ChatStreamService()
        monkeypatch.setattr(service, "_run", fake_run)

        fake_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
        stream_id = "stream-1"
        queue = RedisStreamQueue(fake_client, stream_id)
        await queue.open()
        assert await queue.exists()

        await service._produce(queue, stream_id, "session-1", [], None)

        assert await queue.get() is None
        assert not await queue.exists()

    asyncio.run(scenario())

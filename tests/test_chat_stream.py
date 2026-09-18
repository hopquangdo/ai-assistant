import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import fakeredis.aioredis

from src.infrastructure.message_queue.queue import RedisStreamQueue
from src.services.chat_stream_service import ChatStreamService
from src.services.conversation_service import ConversationService


def test_get_conversation_and_messages_from_db(monkeypatch):
    session_id = "session-read-1"
    stored_messages = [
        {"role": "user", "content": "Xin chào"},
        {"role": "assistant", "content": "Chào bạn"},
    ]

    async def fake_check_owner(self, sid, user_id):
        return None

    async def fake_get_messages(self, sid):
        assert sid == session_id
        return stored_messages

    async def fake_get_meta(sid):
        return {"updated_at": datetime.now(timezone.utc)}

    async def fake_get_charts(sid):
        return [{"title": "Biểu đồ demo"}]

    monkeypatch.setattr(ConversationService, "_check_owner", fake_check_owner)
    monkeypatch.setattr(ConversationService, "get_messages", fake_get_messages)
    from src.repository.chat_repository import chat_repository

    monkeypatch.setattr(chat_repository, "get_conversation_meta", fake_get_meta)
    monkeypatch.setattr(chat_repository, "get_charts", fake_get_charts)

    async def scenario():
        service = ConversationService()
        conversation = await service.get_conversation(session_id, "user-1")
        return conversation

    conversation = asyncio.run(scenario())

    assert conversation["session_id"] == session_id
    assert conversation["charts"] == [{"title": "Biểu đồ demo"}]
    assert conversation["messages"][0]["role"] == "user"
    assert conversation["messages"][1]["role"] == "assistant"


def test_get_paginated_messages_from_db(monkeypatch):
    session_id = "session-page-1"
    stored_messages = [{"role": "user", "content": f"msg-{idx}"} for idx in range(1, 25)]

    async def fake_check_owner(self, sid, user_id):
        return None

    async def fake_get_messages(self, sid):
        return stored_messages

    monkeypatch.setattr(ConversationService, "_check_owner", fake_check_owner)
    monkeypatch.setattr(ConversationService, "get_messages", fake_get_messages)

    async def scenario():
        service = ConversationService()
        return await service.get_message_page(session_id, "user-1", page=2, limit=10)

    payload = asyncio.run(scenario())

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

        await service._produce(queue, stream_id, "session-1", str(uuid4()), "hello", None)

        assert await queue.get() is None
        assert not await queue.exists()

    asyncio.run(scenario())

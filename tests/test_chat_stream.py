import asyncio

import fakeredis.aioredis

from src.infrastructure.message_queue.queue import RedisStreamQueue
from src.services.chat_stream_service import ChatStreamService


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

        await service._produce(queue, stream_id, "session-1", "hello", None)

        assert await queue.get() is None
        assert not await queue.exists()

    asyncio.run(scenario())

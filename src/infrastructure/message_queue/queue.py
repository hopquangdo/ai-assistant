"""Hang doi FIFO tren Redis List, thay the asyncio.Queue in-memory cua ChatStreamService --
producer (POST /chat/stream) va consumer (GET /chat/stream/{id}) co the nam o 2 process/worker
khac nhau sau load balancer, nen khong the dua vao dict trong tien trinh nua."""

from redis.asyncio import Redis

_DONE_SENTINEL = "__STREAM_DONE__"
_OPEN_MARKER = "__STREAM_OPEN__"
_TTL_SECONDS = 600


class RedisStreamQueue:
    def __init__(self, client: Redis, stream_id: str) -> None:
        self._client = client
        self._key = f"chat:stream:{stream_id}"
        self._owner_key = f"chat:stream:owner:{stream_id}"

    async def exists(self) -> bool:
        return bool(await self._client.exists(self._key))

    async def open(self) -> None:
        """Danh dau stream ton tai truoc khi co frame dau tien, de subscribe_chat_stream
        goi ngay sau create_chat_stream khong bi 404 do race condition."""
        await self._client.rpush(self._key, _OPEN_MARKER)
        await self._client.expire(self._key, _TTL_SECONDS)

    async def set_owner(self, user_id: str) -> None:
        """Ghi nho nguoi tao stream -- subscribe_chat_stream dung de tu choi user khac
        doc stream nay (ownership check, xem plan_auth_chatbot.md muc 6)."""
        await self._client.set(self._owner_key, user_id, ex=_TTL_SECONDS)

    async def owner(self) -> str | None:
        return await self._client.get(self._owner_key)

    async def put(self, frame: str) -> None:
        await self._client.rpush(self._key, frame)
        await self._client.expire(self._key, _TTL_SECONDS)

    async def close(self) -> None:
        await self._client.rpush(self._key, _DONE_SENTINEL)
        await self._client.expire(self._key, _TTL_SECONDS)

    async def get(self) -> str | None:
        """Cho (blocking) toi khi co frame moi; tra None khi stream da ket thuc."""
        while True:
            result = await self._client.blpop([self._key], timeout=0)
            if result is None:
                return None
            _, value = result
            if value == _OPEN_MARKER:
                continue
            if value == _DONE_SENTINEL:
                await self._client.delete(self._key)
                return None
            return value


__all__ = ["RedisStreamQueue"]

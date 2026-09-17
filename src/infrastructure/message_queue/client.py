"""Client Redis dung chung trong tien trinh -- 1 connection pool, lazy-init lan dau dung."""

from redis.asyncio import Redis, from_url

from src.core.config import get_settings


class RedisClientFactory:
    def __init__(self) -> None:
        self._client: Redis | None = None

    def get(self) -> Redis:
        if self._client is None:
            # redis-py mac dinh socket_timeout=5s -- neu giu nguyen, BLPOP(timeout=0) cua
            # RedisStreamQueue (cho vo han cho token/tool-result moi) se bi client tu ngat sau
            # dung 5s khong co du lieu va nem TimeoutError, du Redis server van dang cho dung.
            # Phai tat socket_timeout de BLPOP thuc su block vo han nhu y do.
            self._client = from_url(
                get_settings().redis_url,
                decode_responses=True,
                socket_timeout=None,
                socket_connect_timeout=5,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
        self._client = None


redis_client_factory = RedisClientFactory()

__all__ = ["RedisClientFactory", "redis_client_factory"]

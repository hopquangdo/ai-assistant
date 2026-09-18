"""Client Postgres cho du lieu app-level (chat_conversation, chat_messages, chat_charts trong
db/schema.sql) -- tach voi checkpointer LangGraph (src/infrastructure/memory/client.py, bang
checkpoints/checkpoint_writes) du 2 ben dung chung database_url.
"""

import logging

from psycopg_pool import AsyncConnectionPool

from src.core.config import get_settings

logger = logging.getLogger("chatbot.infrastructure.db")


class DbPoolFactory:
    def __init__(self) -> None:
        self._pool: AsyncConnectionPool | None = None

    async def get(self) -> AsyncConnectionPool:
        """Tra ve pool da mo (lazy-init lan goi dau). Raise neu database_url chua cau hinh --
        khac voi checkpointer (co the chay khong co), du lieu conversation/message la bat buoc."""
        if self._pool is not None:
            return self._pool

        database_url = get_settings().database_url
        if not database_url:
            raise RuntimeError("database_url chua duoc cau hinh -- khong the luu conversation/message")

        pool = AsyncConnectionPool(
            conninfo=database_url,
            max_size=10,
            kwargs={"autocommit": True, "prepare_threshold": 0},
            open=False,
        )
        await pool.open()
        self._pool = pool
        logger.info("app db pool ready")
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
        self._pool = None


db_pool_factory = DbPoolFactory()

__all__ = ["DbPoolFactory", "db_pool_factory"]

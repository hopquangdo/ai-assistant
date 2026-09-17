"""Client Postgres cho memory ben vung cua graph (checkpoint LangGraph) -- luu state runtime
(charts, suggestions, clarification_needed, recursion_hit...) theo thread_id, thay vi tu quan
ly thu cong.

langgraph tu tao/migrate bang rieng (checkpoints, checkpoint_writes, checkpoint_blobs...)
trong DB database_url khi setup() chay lan dau.
"""

import logging

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from src.core.config import get_settings

logger = logging.getLogger("chatbot.infrastructure.memory")


class PostgresCheckpointerFactory:
    def __init__(self) -> None:
        self._pool: AsyncConnectionPool | None = None
        self._saver: AsyncPostgresSaver | None = None

    async def get(self) -> AsyncPostgresSaver | None:
        """Tra ve checkpointer da setup, hoac None neu chua cau hinh database_url
        (graph van chay duoc khong checkpoint, chi mat kha nang resume theo thread_id)."""
        if self._saver is not None:
            return self._saver

        database_url = get_settings().database_url
        if not database_url:
            logger.warning("database_url chua cau hinh -- graph chay khong co checkpointer")
            return None

        self._pool = AsyncConnectionPool(
            conninfo=database_url,
            max_size=10,
            kwargs={"autocommit": True, "prepare_threshold": 0},
            open=False,
        )
        await self._pool.open()
        saver = AsyncPostgresSaver(self._pool)
        await saver.setup()
        self._saver = saver
        logger.info("checkpointer postgres ready")
        return self._saver

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
        self._pool = None
        self._saver = None


checkpointer_factory = PostgresCheckpointerFactory()

__all__ = ["PostgresCheckpointerFactory", "checkpointer_factory"]

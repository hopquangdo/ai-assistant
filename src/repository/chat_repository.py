"""Repository luu tru conversation/message/chart xuong Postgres (bang chat_conversation,
chat_messages, chat_charts trong db/schema.sql) -- thay the memory_store in-process cu."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from src.infrastructure.db.client import db_pool_factory


class ChatRepository:
    async def get_conversation_owner(self, session_id: str) -> str | None:
        pool = await db_pool_factory.get()
        async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT user_id FROM chat_conversation WHERE id = %s", (session_id,))
            row = await cur.fetchone()
            return row["user_id"] if row else None

    async def ensure_conversation(self, session_id: str, user_id: str) -> None:
        """Tao conversation neu chua ton tai (no-op neu da co, khong doi owner)."""
        pool = await db_pool_factory.get()
        async with pool.connection() as conn:
            await conn.execute(
                "INSERT INTO chat_conversation (id, user_id) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                (session_id, user_id),
            )

    async def touch_conversation(self, session_id: str) -> None:
        pool = await db_pool_factory.get()
        async with pool.connection() as conn:
            await conn.execute("UPDATE chat_conversation SET updated_at = now() WHERE id = %s", (session_id,))

    async def get_conversation_meta(self, session_id: str) -> dict[str, Any] | None:
        pool = await db_pool_factory.get()
        async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT id, user_id, created_at, updated_at FROM chat_conversation WHERE id = %s",
                (session_id,),
            )
            return await cur.fetchone()

    async def insert_message(self, session_id: str, run_id: str, thread_id: str, role: str, content: str) -> UUID:
        """Chen 1 message va tra ve id (dung de gan chart cho dung cau tra loi da sinh ra no)."""
        pool = await db_pool_factory.get()
        async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                INSERT INTO chat_messages (conversation_id, run_id, thread_id, role, content)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (session_id, run_id, thread_id, role, content),
            )
            row = await cur.fetchone()
            return row["id"]

    async def insert_charts(self, message_id: UUID, charts: list[dict]) -> None:
        if not charts:
            return
        pool = await db_pool_factory.get()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.executemany(
                "INSERT INTO chat_charts (message_id, payload) VALUES (%s, %s)",
                [(message_id, Jsonb(chart)) for chart in charts],
            )

    async def get_messages(self, session_id: str) -> list[dict[str, str]]:
        pool = await db_pool_factory.get()
        async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT role, content FROM chat_messages
                WHERE conversation_id = %s AND role IN ('user', 'assistant')
                ORDER BY created_at ASC
                """,
                (session_id,),
            )
            rows = await cur.fetchall()
            return [{"role": row["role"], "content": row["content"]} for row in rows]

    async def get_charts(self, session_id: str) -> list[dict]:
        pool = await db_pool_factory.get()
        async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT c.payload FROM chat_charts c
                JOIN chat_messages m ON m.id = c.message_id
                WHERE m.conversation_id = %s
                ORDER BY c.created_at ASC
                """,
                (session_id,),
            )
            rows = await cur.fetchall()
            return [row["payload"] for row in rows]

    async def list_conversations(self, user_id: str) -> list[dict[str, Any]]:
        """Conversation cua user kem title (tin nhan user dau tien) va message_count, chi
        nhung conversation da co it nhat 1 message, moi nhat truoc."""
        pool = await db_pool_factory.get()
        async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT
                    c.id AS session_id,
                    c.updated_at,
                    COALESCE(cnt.message_count, 0) AS message_count,
                    first_msg.content AS title
                FROM chat_conversation c
                LEFT JOIN LATERAL (
                    SELECT COUNT(*) AS message_count
                    FROM chat_messages m
                    WHERE m.conversation_id = c.id AND m.role IN ('user', 'assistant')
                ) cnt ON true
                LEFT JOIN LATERAL (
                    SELECT content FROM chat_messages m
                    WHERE m.conversation_id = c.id AND m.role = 'user'
                    ORDER BY m.created_at ASC
                    LIMIT 1
                ) first_msg ON true
                WHERE c.user_id = %s AND COALESCE(cnt.message_count, 0) > 0
                ORDER BY c.updated_at DESC
                """,
                (user_id,),
            )
            rows = await cur.fetchall()
            return [
                {
                    "session_id": row["session_id"],
                    "title": row["title"] or "",
                    "message_count": row["message_count"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]

    async def clear_messages(self, session_id: str) -> None:
        pool = await db_pool_factory.get()
        async with pool.connection() as conn:
            await conn.execute("DELETE FROM chat_messages WHERE conversation_id = %s", (session_id,))

    async def delete_conversation(self, session_id: str) -> None:
        pool = await db_pool_factory.get()
        async with pool.connection() as conn:
            await conn.execute("DELETE FROM chat_conversation WHERE id = %s", (session_id,))


chat_repository = ChatRepository()

__all__ = ["ChatRepository", "chat_repository"]

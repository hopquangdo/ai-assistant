"""Quan ly conversation (session) + lich su message -- persist xuong Postgres qua chat_repository
(bang chat_conversation/chat_messages/chat_charts), khong biet gi ve streaming/agent.

Duoc ChatStreamService goi de: (1) claim + luu tin nhan user NGAY khi nhan request, truoc khi
agent chay, de GET conversation/messages thay tin nhan nay du stream chua chay xong; (2) luu
cau tra loi cua bot (kem chart) sau khi 1 luot chay xong."""

from typing import Any
from uuid import uuid4

from dqh.svc_core.contracts.errors import ForbiddenError, NotFoundError

from src.repository.chat_repository import chat_repository


class ConversationService:
    """CRUD conversation/session + message history (luu tru: Postgres qua chat_repository)."""

    async def create_new_conversation(self, user_id: str) -> dict[str, Any]:
        """Sinh 1 session_id moi, claim owner ngay (POST /chat/conversations) -- dung cho
        flow FE: tao conversation truoc, dieu huong sang /chat/{session_id}, roi moi gui
        tin nhan dau tien qua /chat/stream nhu binh thuong."""
        session_id = str(uuid4())
        await chat_repository.ensure_conversation(session_id, user_id)
        meta = await chat_repository.get_conversation_meta(session_id)
        return {"session_id": session_id, "created_at": meta["created_at"]}

    async def claim_session(self, session_id: str, user_id: str) -> None:
        """Tao conversation neu chua ton tai; tu choi neu session da thuoc user khac.

        Goi khi tao stream (POST /chat/stream) -- diem duy nhat 1 session_id moi duoc
        sinh ra hoac tiep tuc, nen la noi hop ly nhat de khoa owner."""
        owner = await chat_repository.get_conversation_owner(session_id)
        if owner is None:
            await chat_repository.ensure_conversation(session_id, user_id)
        elif owner != user_id:
            raise ForbiddenError("Hội thoại này không thuộc về bạn")

    async def _check_owner(self, session_id: str, user_id: str) -> None:
        """Chan doc conversation/messages cua user khac. Session chua co owner (vd data cu)
        duoc coi la khong ai so huu, khong chan."""
        owner = await chat_repository.get_conversation_owner(session_id)
        if owner is not None and owner != user_id:
            raise NotFoundError("Không tìm thấy hội thoại")

    async def delete_conversation(self, session_id: str) -> None:
        await chat_repository.delete_conversation(session_id)

    async def clear_messages(self, session_id: str) -> None:
        await chat_repository.clear_messages(session_id)

    async def save_user_message(self, session_id: str, run_id: str, content: str) -> None:
        """Luu tin nhan cua user ngay khi nhan duoc request (truoc khi agent chay), de
        GET conversation/messages thay ngay tin nhan nay du bot chua tra loi xong."""
        await chat_repository.insert_message(session_id, run_id, session_id, "user", content)
        await chat_repository.touch_conversation(session_id)

    async def save_assistant_turn(
        self, session_id: str, run_id: str, content: str, charts: list[dict] | None = None
    ) -> None:
        """Luu cau tra loi cua bot (kem chart neu co) sau khi 1 luot chay xong."""
        message_id = await chat_repository.insert_message(session_id, run_id, session_id, "assistant", content)
        await chat_repository.insert_charts(message_id, charts or [])
        await chat_repository.touch_conversation(session_id)

    async def get_messages(self, session_id: str) -> list[dict[str, str]]:
        """Lay lich su tin nhan da luu cua mot session (chi user/assistant, dung de hien thi cho nguoi dung)."""
        return await chat_repository.get_messages(session_id)

    async def get_message_page(
        self, session_id: str, user_id: str, page: int = 1, limit: int = 20, order: str = "asc"
    ) -> dict[str, Any]:
        """Lay danh sach message da luu theo trang.

        order="asc" (mac dinh, tuong thich nguoc): trang 1 la cac tin nhan CU NHAT.
        order="desc": trang 1 la cac tin nhan MOI NHAT (dung cho UI chat -- mo hoi
        thoai chi can tai batch gan nhat, cuon len moi tai tiep trang cu hon). Du
        ca 2 chieu, "items" luon tra ve theo thu tu thoi gian tang dan de render
        tren-xuong-duoi tu nhien.
        """
        await self._check_owner(session_id, user_id)
        if page < 1:
            page = 1
        if limit < 1:
            limit = 20

        messages = await self.get_messages(session_id)
        total = len(messages)
        total_pages = (total + limit - 1) // limit if total else 0
        safe_page = min(page, total_pages if total_pages else 1)

        if order == "desc":
            end = max(total - (safe_page - 1) * limit, 0)
            start = max(end - limit, 0)
            has_more_older = start > 0
        else:
            start = (safe_page - 1) * limit
            end = start + limit
            has_more_older = end < total
        page_items = messages[start:end]

        return {
            "session_id": session_id,
            "page": safe_page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "items": page_items,
            "has_prev": safe_page > 1,
            "has_next": has_more_older,
        }

    async def get_conversation(self, session_id: str, user_id: str) -> dict[str, Any]:
        """Lay du lieu conversation cung toan bo tin nhan va chart."""
        await self._check_owner(session_id, user_id)
        meta = await chat_repository.get_conversation_meta(session_id)
        return {
            "session_id": session_id,
            "messages": await self.get_messages(session_id),
            "charts": await chat_repository.get_charts(session_id),
            "updated_at": meta["updated_at"] if meta else None,
        }

    async def list_conversations(self, user_id: str, page: int = 1, limit: int = 50) -> dict[str, Any]:
        """Liet ke cac conversation cua user hien tai (theo owner da claim_session) trong
        trang, moi cai kem tieu de goi y (tu tin nhan user dau tien) va thoi diem cap nhat
        gan nhat, moi nhat truoc."""
        if page < 1:
            page = 1
        if limit < 1:
            limit = 50

        summaries = await chat_repository.list_conversations(user_id)

        total = len(summaries)
        total_pages = (total + limit - 1) // limit if total else 0
        safe_page = min(page, total_pages if total_pages else 1)
        start = (safe_page - 1) * limit
        end = start + limit

        return {
            "page": safe_page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "items": summaries[start:end],
            "has_prev": safe_page > 1,
            "has_next": end < total,
        }


conversation_service = ConversationService()

__all__ = ["ConversationService", "conversation_service"]

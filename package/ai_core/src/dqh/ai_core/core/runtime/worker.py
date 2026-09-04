"""``AgentWorker`` — vòng lặp: lấy ``AgentTask`` từ ``TaskSource`` -> chạy agent -> đẩy
``AgentOutcome`` vào ``OutcomeSink`` -> ack. Xử lý song song, retry, và shutdown mềm.

    worker = AgentWorker(agent, source, sink, store=InMemoryConversationStore(), concurrency=4)
    task = asyncio.create_task(worker.run())
    ...
    await worker.stop()          # ngừng nhận task mới, chờ task đang chạy xong
    await source.close()         # để worker.run() thoát khỏi vòng lặp
"""
from __future__ import annotations

import asyncio
import logging
from typing import Callable, Literal, Sequence

from langchain_core.messages import BaseMessage

from dqh.ai_core.core.agents.base import Agent
from dqh.ai_core.core.conversation.conversation import Conversation
from dqh.ai_core.core.conversation.store import ConversationStore, serialize_messages
from dqh.ai_core.core.observability.model import Usage
from dqh.ai_core.core.observability.tracker import UsageTracker
from dqh.ai_core.core.observability.utils import model_name_of
from dqh.ai_core.core.runtime.sink import OutcomeSink
from dqh.ai_core.core.runtime.source import TaskSource
from dqh.ai_core.core.runtime.task import AgentOutcome, AgentTask

__all__ = ["AgentWorker", "OnError"]

OnError = Literal["nack", "nack_drop", "ack", "publish_error"]
Hygiene = Callable[[list[BaseMessage]], list[BaseMessage]]


def _last_text(messages: Sequence[BaseMessage]) -> str:
    for m in reversed(messages):
        content = getattr(m, "content", "")
        if isinstance(content, str) and content.strip():
            return content
    return ""


class AgentWorker:
    def __init__(
        self,
        agent: Agent,
        source: TaskSource,
        sink: OutcomeSink,
        *,
        store: ConversationStore | None = None,
        concurrency: int = 1,
        on_error: OnError = "nack",
        retries: int = 0,
        retry_backoff: float = 2.0,
        hygiene: Hygiene = lambda m: m,
        prelude: Sequence[BaseMessage] | Callable[[], Sequence[BaseMessage]] = (),
        logger: logging.Logger | None = None,
    ) -> None:
        """``store``: có -> mỗi task là 1 :class:`Conversation` theo ``thread_id`` (nhớ lịch sử).
        ``on_error``: nack (thử lại) | nack_drop (bỏ/DLQ) | ack (nuốt) | publish_error (gửi lỗi + ack)."""
        self._agent = agent
        self._source = source
        self._sink = sink
        self._store = store
        self._concurrency = max(concurrency, 1)
        self._on_error = on_error
        self._retries = max(retries, 0)
        self._backoff = retry_backoff
        self._hygiene = hygiene
        self._prelude = prelude
        self._log = logger or logging.getLogger("dqh.ai_core.runtime")
        self._stopping = False
        self._inflight: set[asyncio.Task] = set()

    async def run(self) -> None:
        """Chạy tới khi ``TaskSource`` cạn (iterator kết thúc) hoặc bị cancel."""
        sem = asyncio.Semaphore(self._concurrency)
        try:
            async for task in self._source:
                if self._stopping:
                    await self._source.nack(task, requeue=True)
                    break
                await sem.acquire()
                job = asyncio.create_task(self._guarded(task, sem))
                self._inflight.add(job)
                job.add_done_callback(self._inflight.discard)
        except asyncio.CancelledError:
            await self._drain()
            raise
        await self._drain()

    async def stop(self) -> None:
        """Ngừng nhận task mới, chờ các task đang chạy hoàn tất. Gọi ``source.close()`` để
        ``run()`` thoát hẳn."""
        self._stopping = True
        await self._drain()

    # -- nội bộ -----------------------------------------------------------

    async def _drain(self) -> None:
        if self._inflight:
            await asyncio.gather(*self._inflight, return_exceptions=True)

    async def _guarded(self, task: AgentTask, sem: asyncio.Semaphore) -> None:
        try:
            await self._handle(task)
        finally:
            sem.release()

    async def _handle(self, task: AgentTask) -> None:
        usage = Usage(model=model_name_of(self._agent.model))
        config = {"callbacks": [UsageTracker(usage)]}

        attempt = 0
        while True:
            try:
                new_messages = await self._run_agent(task, config)
                outcome = self._outcome(task, new_messages, usage)
                await self._sink.publish(outcome)
                await self._source.ack(task)
                return
            except Exception as exc:
                attempt += 1
                self._log.warning("task %s failed (attempt %d/%d): %s",
                                  task.id, attempt, self._retries + 1, exc)
                if attempt <= self._retries:
                    await asyncio.sleep(min(self._backoff ** attempt, 30))
                    continue
                await self._fail(task, exc)
                return

    async def _run_agent(self, task: AgentTask, config: dict) -> list[BaseMessage]:
        if self._store is not None:
            conv = Conversation(
                self._agent, self._store, task.thread_id or task.id,
                hygiene=self._hygiene, prelude=self._prelude,
            )
            return await conv.send(task.input, config=config)
        return await self._agent.run(task.input, config=config)

    def _outcome(
        self,
        task: AgentTask,
        new_messages: list[BaseMessage],
        usage: Usage | None,
        *,
        error: str | None = None,
    ) -> AgentOutcome:
        return AgentOutcome(
            task_id=task.id,
            thread_id=task.thread_id,
            reply_to=task.reply_to,
            reply=_last_text(new_messages),
            new_messages=serialize_messages(new_messages),
            usage=usage.to_dict() if usage else None,
            error=error,
        )

    async def _fail(self, task: AgentTask, exc: Exception) -> None:
        if self._on_error == "publish_error":
            try:
                await self._sink.publish(self._outcome(task, [], None, error=f"{type(exc).__name__}: {exc}"))
            finally:
                await self._source.ack(task)
        elif self._on_error == "ack":
            await self._source.ack(task)
        elif self._on_error == "nack_drop":
            await self._source.nack(task, requeue=False)
        else:  # "nack"
            await self._source.nack(task, requeue=True)

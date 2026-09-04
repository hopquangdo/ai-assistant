import asyncio

from langchain_core.messages import AIMessage, HumanMessage

from dqh.ai_core.core.runtime import AgentTask, AgentWorker, InMemoryOutcomeSink, InMemoryTaskSource


class _FakeGraph:
    def __init__(self, *, boom: set[str] | None = None) -> None:
        self._boom = boom or set()

    async def ainvoke(self, state, config=None):
        user = state["messages"][-1].content
        if user in self._boom:
            raise RuntimeError("kaboom")
        return {"messages": state["messages"] + [AIMessage(content=f"reply to {user}")]}


class _FakeAgent:
    def __init__(self, **kw) -> None:
        self.graph = _FakeGraph(**kw)
        self.model = object()

    async def run(self, user_content, *, history=None, config=None, track=False):
        out = await self.graph.ainvoke({"messages": [HumanMessage(content=user_content)]}, config=config)
        return out["messages"]


async def _run_worker(worker: AgentWorker, source: InMemoryTaskSource) -> None:
    runner = asyncio.create_task(worker.run())
    await asyncio.sleep(0.05)
    await source.close()
    await runner


def test_worker_processes_tasks_and_publishes_outcomes() -> None:
    src, sink = InMemoryTaskSource(), InMemoryOutcomeSink()
    worker = AgentWorker(_FakeAgent(), src, sink, concurrency=3)

    async def scenario() -> None:
        await src.extend([AgentTask(input="a"), AgentTask(input="b"), AgentTask(input="c")])
        await _run_worker(worker, src)

    asyncio.run(scenario())

    assert sorted(o.reply for o in sink.published) == ["reply to a", "reply to b", "reply to c"]
    assert len(src.acked) == 3
    assert all(o.ok for o in sink.published)


def test_worker_on_error_publish_error() -> None:
    src, sink = InMemoryTaskSource(), InMemoryOutcomeSink()
    worker = AgentWorker(_FakeAgent(boom={"bad"}), src, sink, on_error="publish_error")

    async def scenario() -> None:
        await src.extend([AgentTask(id="t-ok", input="ok"), AgentTask(id="t-bad", input="bad")])
        await _run_worker(worker, src)

    asyncio.run(scenario())

    by_id = {o.task_id: o for o in sink.published}
    assert by_id["t-ok"].ok
    assert not by_id["t-bad"].ok and "kaboom" in by_id["t-bad"].error
    assert set(src.acked) == {"t-ok", "t-bad"}


def test_worker_on_error_nack_requeues() -> None:
    src, sink = InMemoryTaskSource(), InMemoryOutcomeSink()
    worker = AgentWorker(_FakeAgent(boom={"bad"}), src, sink, on_error="nack_drop")

    async def scenario() -> None:
        await src.put(AgentTask(id="t-bad", input="bad"))
        await _run_worker(worker, src)

    asyncio.run(scenario())

    assert sink.published == []
    assert src.nacked == [("t-bad", False)]

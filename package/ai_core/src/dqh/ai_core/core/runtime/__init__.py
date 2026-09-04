"""dqh.ai_core.core.runtime — chạy agent theo hàng đợi / stream (Kafka, queue, …).

    task     AgentTask (đầu vào) + AgentOutcome (đầu ra)
    source   TaskSource (ABC) — async iterator + ack/nack
    sink     OutcomeSink (ABC) — publish(outcome)
    worker   AgentWorker — vòng lặp consume -> run agent -> publish -> ack (song song, retry, stop mềm)
    inmemory InMemoryTaskSource / InMemoryOutcomeSink — cho test & demo

Client Kafka/queue là INFRA: app viết impl ``TaskSource``/``OutcomeSink`` bọc client thật
rồi tiêm vào ``AgentWorker``.
"""
from dqh.ai_core.core.runtime.inmemory import InMemoryOutcomeSink, InMemoryTaskSource
from dqh.ai_core.core.runtime.sink import OutcomeSink
from dqh.ai_core.core.runtime.source import TaskSource
from dqh.ai_core.core.runtime.task import AgentOutcome, AgentTask
from dqh.ai_core.core.runtime.worker import AgentWorker, OnError

__all__ = [
    "AgentTask",
    "AgentOutcome",
    "TaskSource",
    "OutcomeSink",
    "AgentWorker",
    "OnError",
    "InMemoryTaskSource",
    "InMemoryOutcomeSink",
]

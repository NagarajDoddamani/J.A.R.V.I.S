from __future__ import annotations

import asyncio
import json

from nats.js import JetStreamContext

from backend.agent.adapters.outbound.mapper import (
    AgentOutboxDomainEvent,
)
from backend.agent.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyAgentOutboxAdapter,
)
from backend.agent.application.ports.outbox import AgentOutboxPort
from backend.agent.domain.model import (
    AgentActivated,
    AgentCreated,
    AgentDisabled,
    AgentExecutionCompleted,
    AgentExecutionFailed,
    AgentExecutionStarted,
    AgentPaused,
    AgentTaskCancelled,
    AgentTaskCompleted,
    AgentTaskCreated,
    AgentTaskFailed,
    AgentTaskStarted,
)
from backend.core.database import create_session
from backend.core.logging import logger

_EVENT_TYPE_MAP: dict[type, str] = {
    AgentCreated: "agent_created",
    AgentActivated: "agent_activated",
    AgentPaused: "agent_paused",
    AgentDisabled: "agent_disabled",
    AgentTaskCreated: "agent_task_created",
    AgentTaskStarted: "agent_task_started",
    AgentTaskCompleted: "agent_task_completed",
    AgentTaskFailed: "agent_task_failed",
    AgentTaskCancelled: "agent_task_cancelled",
    AgentExecutionStarted: "agent_execution_started",
    AgentExecutionCompleted: "agent_execution_completed",
    AgentExecutionFailed: "agent_execution_failed",
}

_NATS_SUBJECT_MAP: dict[type, str] = {
    AgentCreated: "jarvis.event.agent.agent_created.v1",
    AgentActivated: "jarvis.event.agent.agent_activated.v1",
    AgentPaused: "jarvis.event.agent.agent_paused.v1",
    AgentDisabled: "jarvis.event.agent.agent_disabled.v1",
    AgentTaskCreated: "jarvis.event.agent.agent_task_created.v1",
    AgentTaskStarted: "jarvis.event.agent.agent_task_started.v1",
    AgentTaskCompleted: "jarvis.event.agent.agent_task_completed.v1",
    AgentTaskFailed: "jarvis.event.agent.agent_task_failed.v1",
    AgentTaskCancelled: "jarvis.event.agent.agent_task_cancelled.v1",
    AgentExecutionStarted: "jarvis.event.agent.agent_execution_started.v1",
    AgentExecutionCompleted: "jarvis.event.agent.agent_execution_completed.v1",
    AgentExecutionFailed: "jarvis.event.agent.agent_execution_failed.v1",
}


def _get_aggregate_id(event: AgentOutboxDomainEvent) -> str:
    if isinstance(
        event,
        (
            AgentCreated,
            AgentActivated,
            AgentPaused,
            AgentDisabled,
        ),
    ):
        return str(event.agent_id)
    if isinstance(
        event,
        (
            AgentTaskCreated,
            AgentTaskStarted,
            AgentTaskCompleted,
            AgentTaskFailed,
            AgentTaskCancelled,
        ),
    ):
        return str(event.agent_id)
    if isinstance(
        event,
        (
            AgentExecutionStarted,
            AgentExecutionCompleted,
            AgentExecutionFailed,
        ),
    ):
        return str(event.agent_id)
    return ""


def _build_envelope(event: AgentOutboxDomainEvent) -> dict[str, object]:
    event_type = _EVENT_TYPE_MAP.get(type(event), "UNKNOWN")
    aggregate_id = _get_aggregate_id(event)
    envelope: dict[str, object] = {
        "event_id": aggregate_id,
        "event_type": event_type,
        "kind": "event",
        "producer": "agent",
        "aggregate_id": aggregate_id,
        "occurred_at": event.occurred_at.isoformat(),
    }
    if isinstance(event, AgentCreated):
        envelope["agent_type"] = event.agent_type
        envelope["name"] = event.name
    elif isinstance(event, AgentTaskCreated):
        envelope["task_id"] = str(event.task_id)
        envelope["goal"] = event.goal
        envelope["instruction"] = event.instruction
    elif isinstance(event, AgentTaskStarted):
        envelope["task_id"] = str(event.task_id)
    elif isinstance(event, AgentTaskCompleted):
        envelope["task_id"] = str(event.task_id)
        envelope["result"] = event.result
    elif isinstance(event, AgentTaskFailed):
        envelope["task_id"] = str(event.task_id)
        envelope["failure_reason"] = event.failure_reason
    elif isinstance(event, AgentTaskCancelled):
        envelope["task_id"] = str(event.task_id)
    elif isinstance(event, AgentExecutionStarted):
        envelope["execution_id"] = str(event.execution_id)
        envelope["task_id"] = str(event.task_id)
    elif isinstance(event, AgentExecutionCompleted):
        envelope["execution_id"] = str(event.execution_id)
        envelope["task_id"] = str(event.task_id)
        envelope["result"] = event.result
    elif isinstance(event, AgentExecutionFailed):
        envelope["execution_id"] = str(event.execution_id)
        envelope["task_id"] = str(event.task_id)
        envelope["failure_reason"] = event.failure_reason
    return envelope


async def publish_agent_outbox_events(
    js: JetStreamContext,
    *,
    outbox: AgentOutboxPort | None = None,
    batch: int = 10,
    interval_seconds: float = 5.0,
    max_iterations: int = 0,
) -> None:
    _iterations = 0
    while True:
        _iterations += 1
        db = create_session() if outbox is None else None
        try:
            repo = outbox or SqlAlchemyAgentOutboxAdapter(db)
            events = repo.fetch_unpublished(limit=batch)
            for event in events:
                subject = _NATS_SUBJECT_MAP.get(
                    type(event), "jarvis.event.agent.unknown.v1"
                )
                envelope = _build_envelope(event)
                serialized = json.dumps(
                    envelope, separators=(",", ":")
                ).encode("utf-8")
                await js.publish(subject, serialized)
                repo.mark_published(str(event.event_id))
                logger.info(
                    "Agent outbox event published",
                    subject=subject,
                    event_id=str(event.event_id),
                )
            if db is not None:
                db.commit()
        except Exception as exc:
            if db is not None:
                db.rollback()
            logger.error(
                "Agent outbox iteration failed",
                error=str(exc),
            )
        finally:
            if db is not None:
                db.close()
        if 0 < max_iterations <= _iterations:
            break
        await asyncio.sleep(interval_seconds)

from __future__ import annotations

import asyncio
import json

from nats.js import JetStreamContext

from backend.core.database import create_session
from backend.core.logging import logger
from backend.planner.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyPlannerOutboxAdapter,
)
from backend.planner.application.ports.outbox import PlannerOutboxPort
from backend.planner.domain.model import (
    PlanApproved,
    PlanCancelled,
    PlanCompleted,
    PlanCreated,
    PlanExecutionStarted,
    PlanFailed,
    PlanReady,
    TaskAssigned,
    TaskCompleted,
    TaskCreated,
    TaskFailed,
)

PlannerOutboxEvent = (
    PlanCreated
    | PlanApproved
    | PlanReady
    | PlanExecutionStarted
    | PlanCompleted
    | PlanFailed
    | PlanCancelled
    | TaskCreated
    | TaskAssigned
    | TaskCompleted
    | TaskFailed
)

_EVENT_TYPE_MAP: dict[type, str] = {
    PlanCreated: "PLAN_CREATED",
    PlanApproved: "PLAN_APPROVED",
    PlanReady: "PLAN_READY",
    PlanExecutionStarted: "PLAN_EXECUTION_STARTED",
    PlanCompleted: "PLAN_COMPLETED",
    PlanFailed: "PLAN_FAILED",
    PlanCancelled: "PLAN_CANCELLED",
    TaskCreated: "TASK_CREATED",
    TaskAssigned: "TASK_ASSIGNED",
    TaskCompleted: "TASK_COMPLETED",
    TaskFailed: "TASK_FAILED",
}

_NATS_SUBJECT_MAP: dict[type, str] = {
    PlanCreated: "jarvis.planner.event.created.v1",
    PlanApproved: "jarvis.planner.event.approved.v1",
    PlanReady: "jarvis.planner.event.ready.v1",
    PlanExecutionStarted: "jarvis.planner.event.execution_started.v1",
    PlanCompleted: "jarvis.planner.event.completed.v1",
    PlanFailed: "jarvis.planner.event.failed.v1",
    PlanCancelled: "jarvis.planner.event.cancelled.v1",
    TaskCreated: "jarvis.planner.event.task_created.v1",
    TaskAssigned: "jarvis.planner.event.task_assigned.v1",
    TaskCompleted: "jarvis.planner.event.task_completed.v1",
    TaskFailed: "jarvis.planner.event.task_failed.v1",
}


def _get_aggregate_id(event: PlannerOutboxEvent) -> str:
    if isinstance(
        event,
        (PlanCreated, PlanApproved, PlanReady, PlanExecutionStarted,
         PlanCompleted, PlanFailed, PlanCancelled),
    ):
        return str(event.plan_id)
    return str(event.task_id)


def _build_envelope(event: PlannerOutboxEvent) -> dict[str, object]:
    event_type = _EVENT_TYPE_MAP.get(type(event), "UNKNOWN")
    aggregate_id = _get_aggregate_id(event)
    envelope: dict[str, object] = {
        "event_id": aggregate_id,
        "event_type": event_type,
        "kind": "event",
        "producer": "planner",
        "aggregate_id": aggregate_id,
        "occurred_at": event.occurred_at.isoformat(),
    }
    if isinstance(event, PlanCreated):
        envelope["user_request"] = event.user_request
        envelope["goal"] = event.goal
        envelope["priority"] = event.priority
        envelope["strategy"] = event.strategy
    elif isinstance(event, PlanFailed):
        envelope["failure_reason"] = event.failure_reason
    elif isinstance(event, TaskCreated):
        envelope["description"] = event.description
    elif isinstance(event, TaskAssigned):
        envelope["assigned_agent"] = event.assigned_agent.value
    elif isinstance(event, TaskFailed):
        envelope["failure_reason"] = event.failure_reason
    return envelope


async def publish_planner_outbox_events(
    js: JetStreamContext,
    *,
    outbox: PlannerOutboxPort | None = None,
    batch: int = 10,
    interval_seconds: float = 5.0,
    max_iterations: int = 0,
) -> None:
    _iterations = 0
    while True:
        _iterations += 1
        db = create_session() if outbox is None else None
        try:
            repo = outbox or SqlAlchemyPlannerOutboxAdapter(db)  # type: ignore[arg-type]
            events = repo.fetch_unpublished(limit=batch)
            for event in events:
                subject = _NATS_SUBJECT_MAP.get(
                    type(event), "jarvis.planner.event.unknown.v1"
                )
                envelope = _build_envelope(event)
                serialized = json.dumps(
                    envelope, separators=(",", ":")
                ).encode("utf-8")
                await js.publish(subject, serialized)
                repo.mark_published(str(event.event_id))
                logger.info(
                    "Planner outbox event published",
                    subject=subject,
                    event_id=str(event.event_id),
                )
            if db is not None:
                db.commit()
        except Exception as exc:
            if db is not None:
                db.rollback()
            logger.error(
                "Planner outbox iteration failed",
                error=str(exc),
            )
        finally:
            if db is not None:
                db.close()
        if 0 < max_iterations <= _iterations:
            break
        await asyncio.sleep(interval_seconds)

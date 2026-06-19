from __future__ import annotations

import asyncio
import json

from nats.js import JetStreamContext

from backend.core.database import create_session
from backend.core.logging import logger
from backend.orchestrator.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyOrchestratorOutboxAdapter,
)
from backend.orchestrator.application.ports.outbox import OrchestratorOutboxPort
from backend.orchestrator.domain.model import (
    OrchestrationCancelled,
    OrchestrationCompleted,
    OrchestrationCreated,
    OrchestrationExecutionStarted,
    OrchestrationFailed,
    OrchestrationPlanningStarted,
    OrchestrationResearchStarted,
    WorkflowCompleted,
    WorkflowCreated,
    WorkflowFailed,
    WorkflowStepCompleted,
    WorkflowStepFailed,
    WorkflowStepStarted,
)

OrchestratorOutboxEvent = (
    OrchestrationCreated
    | OrchestrationPlanningStarted
    | OrchestrationResearchStarted
    | OrchestrationExecutionStarted
    | OrchestrationCompleted
    | OrchestrationFailed
    | OrchestrationCancelled
    | WorkflowCreated
    | WorkflowCompleted
    | WorkflowFailed
    | WorkflowStepStarted
    | WorkflowStepCompleted
    | WorkflowStepFailed
)

_NATS_SUBJECT_MAP: dict[type, str] = {
    OrchestrationCreated: "jarvis.orchestrator.event.created.v1",
    OrchestrationPlanningStarted: "jarvis.orchestrator.event.planning_started.v1",
    OrchestrationResearchStarted: "jarvis.orchestrator.event.research_started.v1",
    OrchestrationExecutionStarted: "jarvis.orchestrator.event.execution_started.v1",
    OrchestrationCompleted: "jarvis.orchestrator.event.completed.v1",
    OrchestrationFailed: "jarvis.orchestrator.event.failed.v1",
    OrchestrationCancelled: "jarvis.orchestrator.event.cancelled.v1",
    WorkflowCreated: "jarvis.orchestrator.event.workflow_created.v1",
    WorkflowCompleted: "jarvis.orchestrator.event.workflow_completed.v1",
    WorkflowFailed: "jarvis.orchestrator.event.workflow_failed.v1",
    WorkflowStepStarted: "jarvis.orchestrator.event.step_started.v1",
    WorkflowStepCompleted: "jarvis.orchestrator.event.step_completed.v1",
    WorkflowStepFailed: "jarvis.orchestrator.event.step_failed.v1",
}


def _get_aggregate_id(event: OrchestratorOutboxEvent) -> str:
    if isinstance(event, (OrchestrationCreated, OrchestrationPlanningStarted,
                          OrchestrationResearchStarted, OrchestrationExecutionStarted,
                          OrchestrationCompleted, OrchestrationFailed, OrchestrationCancelled)):
        return str(event.orchestration_id)
    if isinstance(event, (WorkflowCreated, WorkflowCompleted, WorkflowFailed)):
        return str(event.workflow_id)
    if isinstance(event, (WorkflowStepStarted, WorkflowStepCompleted, WorkflowStepFailed)):
        return str(event.step_id)
    return ""


def _build_envelope(event: OrchestratorOutboxEvent) -> dict[str, object]:
    aggregate_id = _get_aggregate_id(event)
    envelope: dict[str, object] = {
        "event_id": str(event.event_id),
        "event_type": type(event).__name__,
        "kind": "event",
        "producer": "orchestrator",
        "aggregate_id": aggregate_id,
        "occurred_at": event.occurred_at.isoformat(),
    }
    if isinstance(event, OrchestrationCreated):
        envelope["intent"] = event.intent
        envelope["goal"] = event.goal
    elif isinstance(event, OrchestrationFailed):
        envelope["failure_reason"] = event.failure_reason
    elif isinstance(event, WorkflowCreated):
        envelope["orchestration_id"] = str(event.orchestration_id)
        envelope["goal"] = event.goal
        envelope["mode"] = event.mode
    elif isinstance(event, WorkflowFailed):
        envelope["failure_reason"] = event.failure_reason
    elif isinstance(event, WorkflowStepCompleted):
        envelope["result"] = event.result
    elif isinstance(event, WorkflowStepFailed):
        envelope["failure_reason"] = event.failure_reason
    return envelope


async def publish_orchestrator_outbox_events(
    js: JetStreamContext,
    *,
    outbox: OrchestratorOutboxPort | None = None,
    batch: int = 10,
    interval_seconds: float = 5.0,
    max_iterations: int = 0,
) -> None:
    _iterations = 0
    while True:
        _iterations += 1
        db = create_session() if outbox is None else None
        try:
            repo = outbox or SqlAlchemyOrchestratorOutboxAdapter(db)  # type: ignore[arg-type]
            events = repo.fetch_unpublished(limit=batch)
            for event in events:
                subject = _NATS_SUBJECT_MAP.get(
                    type(event), "jarvis.orchestrator.event.unknown.v1"
                )
                envelope = _build_envelope(event)
                serialized = json.dumps(
                    envelope, separators=(",", ":")
                ).encode("utf-8")
                await js.publish(subject, serialized)
                repo.mark_published(str(event.event_id))
                logger.info(
                    "Orchestrator outbox event published",
                    subject=subject,
                    event_id=str(event.event_id),
                )
            if db is not None:
                db.commit()
        except Exception as exc:
            if db is not None:
                db.rollback()
            logger.error(
                "Orchestrator outbox iteration failed",
                error=str(exc),
            )
        finally:
            if db is not None:
                db.close()
        if 0 < max_iterations <= _iterations:
            break
        await asyncio.sleep(interval_seconds)

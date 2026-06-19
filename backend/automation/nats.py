from __future__ import annotations

import asyncio
import json

from nats.js import JetStreamContext

from backend.core.database import create_session
from backend.core.logging import logger
from backend.automation.adapters.outbound.mapper import (
    AutomationOutboxDomainEvent,
)
from backend.automation.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyAutomationOutboxAdapter,
)
from backend.automation.application.ports.outbox import AutomationOutboxPort
from backend.automation.domain.model import (
    ActionAdded,
    AutomationActivated,
    AutomationCreated,
    AutomationDisabled,
    AutomationExecutionCompleted,
    AutomationExecutionFailed,
    AutomationExecutionStarted,
    AutomationPaused,
    TriggerAdded,
    TriggerDisabled,
    TriggerEnabled,
)

_EVENT_TYPE_MAP: dict[type, str] = {
    AutomationCreated: "automation_created",
    AutomationActivated: "automation_activated",
    AutomationPaused: "automation_paused",
    AutomationDisabled: "automation_disabled",
    AutomationExecutionStarted: "automation_execution_started",
    AutomationExecutionCompleted: "automation_execution_completed",
    AutomationExecutionFailed: "automation_execution_failed",
    TriggerAdded: "trigger_added",
    TriggerEnabled: "trigger_enabled",
    TriggerDisabled: "trigger_disabled",
    ActionAdded: "action_added",
}

_NATS_SUBJECT_MAP: dict[type, str] = {
    AutomationCreated: "jarvis.automation.event.automation_created.v1",
    AutomationActivated: "jarvis.automation.event.automation_activated.v1",
    AutomationPaused: "jarvis.automation.event.automation_paused.v1",
    AutomationDisabled: "jarvis.automation.event.automation_disabled.v1",
    AutomationExecutionStarted: "jarvis.automation.event.automation_execution_started.v1",
    AutomationExecutionCompleted: "jarvis.automation.event.automation_execution_completed.v1",
    AutomationExecutionFailed: "jarvis.automation.event.automation_execution_failed.v1",
    TriggerAdded: "jarvis.automation.event.trigger_added.v1",
    TriggerEnabled: "jarvis.automation.event.trigger_enabled.v1",
    TriggerDisabled: "jarvis.automation.event.trigger_disabled.v1",
    ActionAdded: "jarvis.automation.event.action_added.v1",
}


def _get_aggregate_id(event: AutomationOutboxDomainEvent) -> str:
    if isinstance(
        event,
        (
            AutomationCreated,
            AutomationActivated,
            AutomationPaused,
            AutomationDisabled,
        ),
    ):
        return str(event.automation_id)
    if isinstance(
        event,
        (
            AutomationExecutionStarted,
            AutomationExecutionCompleted,
            AutomationExecutionFailed,
        ),
    ):
        return str(event.automation_id)
    if isinstance(event, (TriggerAdded, TriggerEnabled, TriggerDisabled)):
        return str(event.automation_id)
    if isinstance(event, ActionAdded):
        return str(event.automation_id)
    return ""


def _build_envelope(event: AutomationOutboxDomainEvent) -> dict[str, object]:
    event_type = _EVENT_TYPE_MAP.get(type(event), "UNKNOWN")
    aggregate_id = _get_aggregate_id(event)
    envelope: dict[str, object] = {
        "event_id": aggregate_id,
        "event_type": event_type,
        "kind": "event",
        "producer": "automation",
        "aggregate_id": aggregate_id,
        "occurred_at": event.occurred_at.isoformat(),
    }
    if isinstance(event, AutomationCreated):
        envelope["name"] = event.name
        envelope["description"] = event.description
        envelope["execution_mode"] = event.execution_mode
    elif isinstance(event, AutomationExecutionFailed):
        envelope["failure_reason"] = event.failure_reason
    elif isinstance(event, AutomationExecutionCompleted):
        envelope["result"] = event.result
    elif isinstance(event, TriggerAdded):
        envelope["trigger_type"] = event.trigger_type
    elif isinstance(event, ActionAdded):
        envelope["action_type"] = event.action_type
    return envelope


async def publish_automation_outbox_events(
    js: JetStreamContext,
    *,
    outbox: AutomationOutboxPort | None = None,
    batch: int = 10,
    interval_seconds: float = 5.0,
    max_iterations: int = 0,
) -> None:
    _iterations = 0
    while True:
        _iterations += 1
        db = create_session() if outbox is None else None
        try:
            repo = outbox or SqlAlchemyAutomationOutboxAdapter(db)
            events = repo.fetch_unpublished(limit=batch)
            for event in events:
                subject = _NATS_SUBJECT_MAP.get(
                    type(event), "jarvis.automation.event.unknown.v1"
                )
                envelope = _build_envelope(event)
                serialized = json.dumps(
                    envelope, separators=(",", ":")
                ).encode("utf-8")
                await js.publish(subject, serialized)
                repo.mark_published(str(event.event_id))
                logger.info(
                    "Automation outbox event published",
                    subject=subject,
                    event_id=str(event.event_id),
                )
            if db is not None:
                db.commit()
        except Exception as exc:
            if db is not None:
                db.rollback()
            logger.error(
                "Automation outbox iteration failed",
                error=str(exc),
            )
        finally:
            if db is not None:
                db.close()
        if 0 < max_iterations <= _iterations:
            break
        await asyncio.sleep(interval_seconds)

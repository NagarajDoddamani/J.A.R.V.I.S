from __future__ import annotations

import asyncio
import json

from nats.js import JetStreamContext

from backend.core.database import create_session
from backend.core.logging import logger
from backend.policy.adapters.outbound.mapper import (
    PolicyOutboxDomainEvent,
)
from backend.policy.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyPolicyOutboxAdapter,
)
from backend.policy.application.ports.outbox import PolicyOutboxPort
from backend.policy.domain.model import (
    PolicyActivated,
    PolicyArchived,
    PolicyCreated,
    PolicyDisabled,
    PolicyEvaluationCompleted,
    PolicyEvaluationFailed,
    PolicyEvaluationStarted,
    PolicyRuleAdded,
    PolicyRuleDisabled,
    PolicyRuleEnabled,
    PolicyRuleRemoved,
)

_EVENT_TYPE_MAP: dict[type, str] = {
    PolicyCreated: "policy_created",
    PolicyActivated: "policy_activated",
    PolicyDisabled: "policy_disabled",
    PolicyArchived: "policy_archived",
    PolicyRuleAdded: "rule_added",
    PolicyRuleRemoved: "rule_removed",
    PolicyRuleEnabled: "rule_enabled",
    PolicyRuleDisabled: "rule_disabled",
    PolicyEvaluationStarted: "evaluation_started",
    PolicyEvaluationCompleted: "evaluation_completed",
    PolicyEvaluationFailed: "evaluation_failed",
}

_NATS_SUBJECT_MAP: dict[type, str] = {
    PolicyCreated: "jarvis.event.policy.policy_created.v1",
    PolicyActivated: "jarvis.event.policy.policy_activated.v1",
    PolicyDisabled: "jarvis.event.policy.policy_disabled.v1",
    PolicyArchived: "jarvis.event.policy.policy_archived.v1",
    PolicyRuleAdded: "jarvis.event.policy.rule_added.v1",
    PolicyRuleRemoved: "jarvis.event.policy.rule_removed.v1",
    PolicyRuleEnabled: "jarvis.event.policy.rule_enabled.v1",
    PolicyRuleDisabled: "jarvis.event.policy.rule_disabled.v1",
    PolicyEvaluationStarted: "jarvis.event.policy.evaluation_started.v1",
    PolicyEvaluationCompleted: "jarvis.event.policy.evaluation_completed.v1",
    PolicyEvaluationFailed: "jarvis.event.policy.evaluation_failed.v1",
}


def _get_aggregate_id(event: PolicyOutboxDomainEvent) -> str:
    if isinstance(
        event,
        (
            PolicyCreated,
            PolicyActivated,
            PolicyDisabled,
            PolicyArchived,
        ),
    ):
        return str(event.policy_id)
    if isinstance(
        event,
        (
            PolicyRuleAdded,
            PolicyRuleRemoved,
            PolicyRuleEnabled,
            PolicyRuleDisabled,
        ),
    ):
        return str(event.policy_id)
    if isinstance(
        event,
        (
            PolicyEvaluationStarted,
            PolicyEvaluationCompleted,
            PolicyEvaluationFailed,
        ),
    ):
        return str(event.policy_id)
    return ""


def _build_envelope(event: PolicyOutboxDomainEvent) -> dict[str, object]:
    event_type = _EVENT_TYPE_MAP.get(type(event), "UNKNOWN")
    aggregate_id = _get_aggregate_id(event)
    envelope: dict[str, object] = {
        "event_id": aggregate_id,
        "event_type": event_type,
        "kind": "event",
        "producer": "policy",
        "aggregate_id": aggregate_id,
        "occurred_at": event.occurred_at.isoformat(),
    }
    if isinstance(event, PolicyCreated):
        envelope["name"] = event.name
        envelope["description"] = event.description
        envelope["priority"] = event.priority
        envelope["scope"] = event.scope
        envelope["version"] = event.version
    elif isinstance(event, PolicyRuleAdded):
        envelope["rule_id"] = str(event.rule_id)
        envelope["condition"] = event.condition
        envelope["action"] = event.action
    elif isinstance(event, PolicyEvaluationStarted):
        envelope["evaluation_id"] = str(event.evaluation_id)
    elif isinstance(event, PolicyEvaluationCompleted):
        envelope["evaluation_id"] = str(event.evaluation_id)
        envelope["decision"] = event.decision
        envelope["result"] = event.result
    elif isinstance(event, PolicyEvaluationFailed):
        envelope["evaluation_id"] = str(event.evaluation_id)
        envelope["failure_reason"] = event.failure_reason
    return envelope


async def publish_policy_outbox_events(
    js: JetStreamContext,
    *,
    outbox: PolicyOutboxPort | None = None,
    batch: int = 10,
    interval_seconds: float = 5.0,
    max_iterations: int = 0,
) -> None:
    _iterations = 0
    while True:
        _iterations += 1
        db = create_session() if outbox is None else None
        try:
            repo = outbox or SqlAlchemyPolicyOutboxAdapter(db)
            events = repo.fetch_unpublished(limit=batch)
            for event in events:
                subject = _NATS_SUBJECT_MAP.get(
                    type(event), "jarvis.event.policy.unknown.v1"
                )
                envelope = _build_envelope(event)
                serialized = json.dumps(
                    envelope, separators=(",", ":")
                ).encode("utf-8")
                await js.publish(subject, serialized)
                repo.mark_published(str(event.event_id))
                logger.info(
                    "Policy outbox event published",
                    subject=subject,
                    event_id=str(event.event_id),
                )
            if db is not None:
                db.commit()
        except Exception as exc:
            if db is not None:
                db.rollback()
            logger.error(
                "Policy outbox iteration failed",
                error=str(exc),
            )
        finally:
            if db is not None:
                db.close()
        if 0 < max_iterations <= _iterations:
            break
        await asyncio.sleep(interval_seconds)

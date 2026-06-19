from __future__ import annotations

import asyncio
import json

from nats.js import JetStreamContext

from backend.core.database import create_session
from backend.core.logging import logger
from backend.memory.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyMemoryOutboxAdapter,
)
from backend.memory.application.ports.outbox import MemoryOutboxPort
from backend.memory.domain.model import (
    ConsentGranted,
    ConsentRevoked,
    MemoryCreated,
    MemoryDeleted,
    MemoryPurgeScheduled,
    MemoryPurged,
    MemoryRetentionExpired,
    MemoryUpdated,
)

MemoryOutboxEvent = (
    MemoryCreated
    | MemoryUpdated
    | MemoryDeleted
    | MemoryRetentionExpired
    | MemoryPurgeScheduled
    | MemoryPurged
    | ConsentGranted
    | ConsentRevoked
)

_EVENT_TYPE_MAP: dict[type, str] = {
    MemoryCreated: "MEMORY_CREATED",
    MemoryUpdated: "MEMORY_UPDATED",
    MemoryDeleted: "MEMORY_DELETED",
    MemoryRetentionExpired: "MEMORY_RETENTION_EXPIRED",
    MemoryPurgeScheduled: "MEMORY_PURGE_SCHEDULED",
    MemoryPurged: "MEMORY_PURGED",
    ConsentGranted: "CONSENT_GRANTED",
    ConsentRevoked: "CONSENT_REVOKED",
}

_NATS_SUBJECT_MAP: dict[type, str] = {
    MemoryCreated: "jarvis.event.memory.memory_created.v1",
    MemoryUpdated: "jarvis.event.memory.memory_updated.v1",
    MemoryDeleted: "jarvis.event.memory.memory_deleted.v1",
    MemoryRetentionExpired: "jarvis.event.memory.memory_retention_expired.v1",
    MemoryPurgeScheduled: "jarvis.event.memory.memory_purge_scheduled.v1",
    MemoryPurged: "jarvis.event.memory.memory_purged.v1",
    ConsentGranted: "jarvis.event.memory.consent_granted.v1",
    ConsentRevoked: "jarvis.event.memory.consent_revoked.v1",
}


def _get_aggregate_id(event: MemoryOutboxEvent) -> str:
    if isinstance(
        event,
        (MemoryCreated, MemoryUpdated, MemoryDeleted,
         MemoryRetentionExpired, MemoryPurgeScheduled, MemoryPurged),
    ):
        return str(event.memory_id)
    return str(event.consent_id)


def _build_envelope(event: MemoryOutboxEvent) -> dict[str, object]:
    event_type = _EVENT_TYPE_MAP.get(type(event), "UNKNOWN")
    aggregate_id = _get_aggregate_id(event)
    envelope: dict[str, object] = {
        "event_id": aggregate_id,
        "event_type": event_type,
        "kind": "event",
        "producer": "memory",
        "aggregate_id": aggregate_id,
        "occurred_at": event.occurred_at.isoformat(),
    }
    if isinstance(event, MemoryCreated):
        envelope["consent_id"] = str(event.consent_id)
        envelope["category"] = event.category.value
        envelope["source_type"] = event.source_type
        envelope["source_id"] = event.source_id
        envelope["sensitivity"] = event.sensitivity
    elif isinstance(event, (MemoryUpdated, MemoryDeleted,
                            MemoryRetentionExpired, MemoryPurgeScheduled, MemoryPurged)):
        envelope["revision"] = event.revision
    return envelope


async def publish_memory_outbox_events(
    js: JetStreamContext,
    *,
    outbox: MemoryOutboxPort | None = None,
    batch: int = 10,
    interval_seconds: float = 5.0,
    max_iterations: int = 0,
) -> None:
    """Background task that polls the memory outbox and publishes to NATS.

    Runs in the application lifespan. Creates its own database session
    per iteration. Polls unpublished events, publishes each on a NATS
    subject derived from the event type, then marks them published.

    When *max_iterations* is > 0 the loop exits after that many
    iterations (useful for testing).
    """
    _iterations = 0
    while True:
        _iterations += 1
        db = create_session() if outbox is None else None
        try:
            repo = outbox or SqlAlchemyMemoryOutboxAdapter(db)  # type: ignore[arg-type]
            events = repo.fetch_unpublished(limit=batch)
            for event in events:
                subject = _NATS_SUBJECT_MAP.get(type(event), "jarvis.event.memory.unknown.v1")
                envelope = _build_envelope(event)
                serialized = json.dumps(
                    envelope, separators=(",", ":")
                ).encode("utf-8")
                await js.publish(subject, serialized)
                repo.mark_published(str(event.event_id))
                logger.info(
                    "Memory outbox event published",
                    subject=subject,
                    event_id=str(event.event_id),
                )
            if db is not None:
                db.commit()
        except Exception as exc:
            if db is not None:
                db.rollback()
            logger.error(
                "Memory outbox iteration failed",
                error=str(exc),
            )
        finally:
            if db is not None:
                db.close()
        if 0 < max_iterations <= _iterations:
            break
        await asyncio.sleep(interval_seconds)

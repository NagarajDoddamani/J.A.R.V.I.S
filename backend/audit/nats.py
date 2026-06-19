from __future__ import annotations

import asyncio
import json

from nats.js import JetStreamContext

from backend.audit.adapters.outbound.repositories import (
    SqlAlchemyAuditOutboxRepository,
)
from backend.audit.application.ports.outbox import AuditOutboxPort
from backend.core.database import create_session
from backend.core.logging import logger
from backend.core.nats import nats_manager
from backend.core.nats_governance import GovernanceError


async def publish_outbox_events(
    js: JetStreamContext,
    *,
    outbox: AuditOutboxPort | None = None,
    batch: int = 10,
    interval_seconds: float = 5.0,
    max_iterations: int = 0,
) -> None:
    """Background task that polls the audit outbox and publishes to NATS.

    Runs in the application lifespan. Creates its own database session
    per iteration. Polls unpublished events, publishes each as a NATS
    envelope on ``jarvis.audit.signal.<chain_name>.v1``, then marks
    them published.

    When *max_iterations* is > 0 the loop exits after that many
    iterations (useful for testing).
    """
    _iterations = 0
    while True:
        _iterations += 1
        try:
            db = create_session() if outbox is None else None
            try:
                repo = outbox or SqlAlchemyAuditOutboxRepository(db)  # type: ignore[arg-type]
                events = repo.fetch_unpublished(limit=batch)
                for event in events:
                    subject = f"jarvis.audit.signal.{event.chain_name}.v1"
                    envelope = {
                        "event_id": str(event.entry_id),
                        "event_type": "AUDIT_ENTRY_RECORDED",
                        "kind": "event",
                        "subject": subject,
                        "producer": "audit",
                        "chain_name": event.chain_name,
                        "action": event.action,
                        "actor_type": event.actor_type,
                        "correlation_id": event.correlation_id,
                        "entry_index": event.entry_index,
                        "occurred_at": event.occurred_at.isoformat(),
                    }
                    serialized = json.dumps(
                        envelope, separators=(",", ":")
                    ).encode("utf-8")
                    await js.publish(subject, serialized)
                    repo.mark_published(str(event.event_id))
                    logger.info(
                        "Outbox event published",
                        subject=subject,
                        event_id=str(event.event_id),
                    )
                if db is not None:
                    db.commit()
            except Exception as exc:
                if db is not None:
                    db.rollback()
                logger.error(
                    "Outbox iteration failed",
                    error=str(exc),
                )
            finally:
                if db is not None:
                    db.close()
        except GovernanceError as exc:
            logger.warning(
                "NATS not available, outbox publisher will retry",
                error=str(exc),
            )
        if 0 < max_iterations <= _iterations:
            break
        await asyncio.sleep(interval_seconds)

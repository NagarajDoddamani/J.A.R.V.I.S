from __future__ import annotations

import asyncio
import json

from nats.js import JetStreamContext

from backend.core.database import create_session
from backend.core.logging import logger
from backend.notification.adapters.outbound.mapper import (
    NotificationOutboxDomainEvent,
    NotificationOutboxMapperImpl,
)
from backend.notification.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyNotificationOutboxAdapter,
)
from backend.notification.application.ports.outbox import NotificationOutboxPort
from backend.notification.domain.model import (
    NotificationAcknowledged,
    NotificationActionInvoked,
    NotificationCreated,
    NotificationDismissed,
    NotificationExpired,
    NotificationShown,
)

_NATS_SUBJECT_MAP: dict[type, str] = {
    NotificationCreated: "jarvis.event.notification.created.v1",
    NotificationShown: "jarvis.event.notification.shown.v1",
    NotificationAcknowledged: "jarvis.event.notification.acknowledged.v1",
    NotificationDismissed: "jarvis.event.notification.dismissed.v1",
    NotificationExpired: "jarvis.event.notification.expired.v1",
    NotificationActionInvoked: "jarvis.event.notification.action_invoked.v1",
}

_EVENT_TYPE_MAP: dict[type, str] = {
    NotificationCreated: "NOTIFICATION_CREATED",
    NotificationShown: "NOTIFICATION_SHOWN",
    NotificationAcknowledged: "NOTIFICATION_ACKNOWLEDGED",
    NotificationDismissed: "NOTIFICATION_DISMISSED",
    NotificationExpired: "NOTIFICATION_EXPIRED",
    NotificationActionInvoked: "NOTIFICATION_ACTION_INVOKED",
}


def _get_aggregate_id(event: NotificationOutboxDomainEvent) -> str:
    if isinstance(event, NotificationActionInvoked):
        return str(event.action_id)
    return str(event.notification_id)


def _build_envelope(event: NotificationOutboxDomainEvent) -> dict[str, object]:
    event_type = _EVENT_TYPE_MAP.get(type(event), "UNKNOWN")
    aggregate_id = _get_aggregate_id(event)
    envelope: dict[str, object] = {
        "event_id": aggregate_id,
        "event_type": event_type,
        "kind": "event",
        "producer": "notification",
        "aggregate_id": aggregate_id,
        "occurred_at": event.occurred_at.isoformat(),
    }
    if isinstance(event, NotificationCreated):
        envelope["title"] = event.title
        envelope["message"] = event.message
        envelope["priority"] = event.priority
        envelope["channel"] = event.channel
        envelope["target_type"] = event.target_type
        envelope["target_id"] = event.target_id
    elif isinstance(event, NotificationActionInvoked):
        envelope["notification_id"] = str(event.notification_id)
        envelope["callback_name"] = event.callback_name
    return envelope


async def publish_notification_outbox_events(
    js: JetStreamContext,
    *,
    outbox: NotificationOutboxPort | None = None,
    batch: int = 10,
    interval_seconds: float = 5.0,
    max_iterations: int = 0,
) -> None:
    _iterations = 0
    while True:
        _iterations += 1
        db = create_session() if outbox is None else None
        try:
            repo = outbox or SqlAlchemyNotificationOutboxAdapter(db)  # type: ignore[arg-type]
            events = repo.fetch_unpublished(limit=batch)
            for event in events:
                subject = _NATS_SUBJECT_MAP.get(type(event), "jarvis.event.notification.unknown.v1")
                envelope = _build_envelope(event)
                serialized = json.dumps(
                    envelope, separators=(",", ":")
                ).encode("utf-8")
                await js.publish(subject, serialized)
                repo.mark_published(str(event.event_id))
                logger.info(
                    "Notification outbox event published",
                    subject=subject,
                    event_id=str(event.event_id),
                )
            if db is not None:
                db.commit()
        except Exception as exc:
            if db is not None:
                db.rollback()
            logger.error(
                "Notification outbox iteration failed",
                error=str(exc),
            )
        finally:
            if db is not None:
                db.close()
        if 0 < max_iterations <= _iterations:
            break
        await asyncio.sleep(interval_seconds)

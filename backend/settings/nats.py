from __future__ import annotations

import asyncio
import json

from nats.js import JetStreamContext

from backend.core.database import create_session
from backend.core.logging import logger
from backend.settings.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemySettingsOutboxAdapter,
)
from backend.settings.application.ports.outbox import SettingsOutboxPort


async def publish_settings_outbox_events(
    js: JetStreamContext,
    *,
    outbox: SettingsOutboxPort | None = None,
    batch: int = 10,
    interval_seconds: float = 5.0,
    max_iterations: int = 0,
) -> None:
    """Background task that polls the settings outbox and publishes to NATS.

    Runs in the application lifespan. Creates its own database session
    per iteration. Polls unpublished events, publishes each as a NATS
    envelope on ``jarvis.event.settings.<event_type>.v1``, then marks
    them published.

    When *max_iterations* is > 0 the loop exits after that many
    iterations (useful for testing).
    """
    _iterations = 0
    while True:
        _iterations += 1
        db = create_session() if outbox is None else None
        try:
            repo = outbox or SqlAlchemySettingsOutboxAdapter(db)  # type: ignore[arg-type]
            events = repo.fetch_unpublished(limit=batch)
            for event in events:
                event_type = (
                    "setting_updated"
                    if hasattr(event, "key")
                    else "settings_reset"
                )
                subject = f"jarvis.event.settings.{event_type}.v1"
                profile_id = str(event.profile_id)
                envelope: dict[str, object] = {
                    "event_id": profile_id,
                    "event_type": event_type.upper(),
                    "kind": "event",
                    "subject": subject,
                    "producer": "settings",
                    "profile_id": profile_id,
                    "occurred_at": (
                        event.occurred_at.isoformat()
                        if hasattr(event, "occurred_at")
                        else ""
                    ),
                }
                if event_type == "setting_updated":
                    envelope["key"] = event.key  # type: ignore[attr-defined]
                    envelope["old_value"] = str(event.old_value) if event.old_value is not None else None  # type: ignore[attr-defined]
                    envelope["new_value"] = str(event.new_value) if event.new_value is not None else None  # type: ignore[attr-defined]
                    envelope["category"] = event.category.value if hasattr(event.category, "value") else str(event.category)  # type: ignore[attr-defined]
                else:
                    envelope["previous_count"] = event.previous_count  # type: ignore[attr-defined]

                serialized = json.dumps(
                    envelope, separators=(",", ":")
                ).encode("utf-8")
                await js.publish(subject, serialized)
                repo.mark_published(str(event.event_id))
                logger.info(
                    "Settings outbox event published",
                    subject=subject,
                    event_id=str(event.event_id),
                )
            if db is not None:
                db.commit()
        except Exception as exc:
            if db is not None:
                db.rollback()
            logger.error(
                "Settings outbox iteration failed",
                error=str(exc),
            )
        finally:
            if db is not None:
                db.close()
        if 0 < max_iterations <= _iterations:
            break
        await asyncio.sleep(interval_seconds)

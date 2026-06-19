from __future__ import annotations

import asyncio
import json

from nats.js import JetStreamContext

from backend.core.database import create_session
from backend.core.logging import logger
from backend.research.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyResearchOutboxAdapter,
)
from backend.research.application.ports.outbox import ResearchOutboxPort
from backend.research.domain.model import (
    ResearchCancelled,
    ResearchCompleted,
    ResearchFailed,
    ResearchRequested,
    ResearchStarted,
    ResearchSummaryGenerated,
    SourceAdded,
)

ResearchOutboxEvent = (
    ResearchRequested
    | ResearchStarted
    | ResearchCompleted
    | ResearchFailed
    | ResearchCancelled
    | SourceAdded
    | ResearchSummaryGenerated
)

_NATS_SUBJECT_MAP: dict[type, str] = {
    ResearchRequested: "jarvis.event.research.requested.v1",
    ResearchStarted: "jarvis.event.research.started.v1",
    ResearchCompleted: "jarvis.event.research.completed.v1",
    ResearchFailed: "jarvis.event.research.failed.v1",
    ResearchCancelled: "jarvis.event.research.cancelled.v1",
    SourceAdded: "jarvis.event.research.source_added.v1",
    ResearchSummaryGenerated: "jarvis.event.research.summary_generated.v1",
}


def _get_aggregate_id(event: ResearchOutboxEvent) -> str:
    return str(event.request_id)


def _build_envelope(event: ResearchOutboxEvent) -> dict[str, object]:
    aggregate_id = _get_aggregate_id(event)
    envelope: dict[str, object] = {
        "event_id": str(event.event_id),
        "event_type": type(event).__name__,
        "kind": "event",
        "producer": "research",
        "aggregate_id": aggregate_id,
        "occurred_at": event.occurred_at.isoformat(),
    }
    if isinstance(event, ResearchRequested):
        envelope["query"] = event.query
        envelope["goal"] = event.goal
        envelope["priority"] = event.priority
    elif isinstance(event, ResearchFailed):
        envelope["failure_reason"] = event.failure_reason
    elif isinstance(event, SourceAdded):
        envelope["job_id"] = str(event.job_id)
        envelope["source_id"] = str(event.source_id)
        envelope["source_type"] = event.source_type
        envelope["reference"] = event.reference
    elif isinstance(event, ResearchSummaryGenerated):
        envelope["job_id"] = str(event.job_id)
        envelope["summary"] = event.summary
    return envelope


async def publish_research_outbox_events(
    js: JetStreamContext,
    *,
    outbox: ResearchOutboxPort | None = None,
    batch: int = 10,
    interval_seconds: float = 5.0,
    max_iterations: int = 0,
) -> None:
    _iterations = 0
    while True:
        _iterations += 1
        db = create_session() if outbox is None else None
        try:
            repo = outbox or SqlAlchemyResearchOutboxAdapter(db)  # type: ignore[arg-type]
            events = repo.fetch_unpublished(limit=batch)
            for event in events:
                subject = _NATS_SUBJECT_MAP.get(
                    type(event), "jarvis.event.research.unknown.v1"
                )
                envelope = _build_envelope(event)
                serialized = json.dumps(
                    envelope, separators=(",", ":")
                ).encode("utf-8")
                await js.publish(subject, serialized)
                repo.mark_published(str(event.event_id))
                logger.info(
                    "Research outbox event published",
                    subject=subject,
                    event_id=str(event.event_id),
                )
            if db is not None:
                db.commit()
        except Exception as exc:
            if db is not None:
                db.rollback()
            logger.error(
                "Research outbox iteration failed",
                error=str(exc),
            )
        finally:
            if db is not None:
                db.close()
        if 0 < max_iterations <= _iterations:
            break
        await asyncio.sleep(interval_seconds)

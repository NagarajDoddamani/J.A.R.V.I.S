from __future__ import annotations

import asyncio
import json

from nats.js import JetStreamContext

from backend.core.database import create_session
from backend.core.logging import logger
from backend.knowledge.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyKnowledgeOutboxAdapter,
)
from backend.knowledge.application.ports.outbox import KnowledgeOutboxPort
from backend.knowledge.domain.model import (
    ChunkCreated,
    DocumentDeleted,
    DocumentIndexed,
    DocumentIngested,
    IngestionCompleted,
    IngestionFailed,
    IngestionStarted,
    KnowledgeSourceDeleted,
    KnowledgeSourceRegistered,
    ReindexRequested,
)

KnowledgeOutboxEvent = (
    KnowledgeSourceRegistered
    | KnowledgeSourceDeleted
    | DocumentIngested
    | DocumentIndexed
    | DocumentDeleted
    | ChunkCreated
    | ReindexRequested
    | IngestionStarted
    | IngestionCompleted
    | IngestionFailed
)

_EVENT_TYPE_MAP: dict[type, str] = {
    KnowledgeSourceRegistered: "KNOWLEDGE_SOURCE_REGISTERED",
    KnowledgeSourceDeleted: "KNOWLEDGE_SOURCE_DELETED",
    DocumentIngested: "DOCUMENT_INGESTED",
    DocumentIndexed: "DOCUMENT_INDEXED",
    DocumentDeleted: "DOCUMENT_DELETED",
    ChunkCreated: "CHUNK_CREATED",
    ReindexRequested: "REINDEX_REQUESTED",
    IngestionStarted: "INGESTION_STARTED",
    IngestionCompleted: "INGESTION_COMPLETED",
    IngestionFailed: "INGESTION_FAILED",
}

_NATS_SUBJECT_MAP: dict[type, str] = {
    KnowledgeSourceRegistered: "jarvis.knowledge.event.source_registered.v1",
    KnowledgeSourceDeleted: "jarvis.knowledge.event.source_deleted.v1",
    DocumentIngested: "jarvis.knowledge.event.document_ingested.v1",
    DocumentIndexed: "jarvis.knowledge.event.document_indexed.v1",
    DocumentDeleted: "jarvis.knowledge.event.document_deleted.v1",
    ChunkCreated: "jarvis.knowledge.event.chunk_created.v1",
    ReindexRequested: "jarvis.knowledge.event.reindex_requested.v1",
    IngestionStarted: "jarvis.knowledge.event.ingestion_started.v1",
    IngestionCompleted: "jarvis.knowledge.event.ingestion_completed.v1",
    IngestionFailed: "jarvis.knowledge.event.ingestion_failed.v1",
}


def _get_aggregate_id(event: KnowledgeOutboxEvent) -> str:
    if isinstance(event, (KnowledgeSourceRegistered, KnowledgeSourceDeleted)):
        return str(event.source_id)
    if isinstance(event, (DocumentIngested, DocumentIndexed, DocumentDeleted)):
        return str(event.document_id)
    if isinstance(event, ChunkCreated):
        return str(event.chunk_id)
    if isinstance(event, ReindexRequested):
        return str(event.source_id)
    if isinstance(
        event, (IngestionStarted, IngestionCompleted, IngestionFailed)
    ):
        return str(event.job_id)
    return ""


def _build_envelope(event: KnowledgeOutboxEvent) -> dict[str, object]:
    event_type = _EVENT_TYPE_MAP.get(type(event), "UNKNOWN")
    aggregate_id = _get_aggregate_id(event)
    envelope: dict[str, object] = {
        "event_id": aggregate_id,
        "event_type": event_type,
        "kind": "event",
        "producer": "knowledge",
        "aggregate_id": aggregate_id,
        "occurred_at": event.occurred_at.isoformat(),
    }
    if isinstance(event, KnowledgeSourceRegistered):
        envelope["name"] = event.name
        envelope["source_type"] = event.source_type.value
        envelope["location"] = str(event.location)
        envelope["classification"] = event.classification
    elif isinstance(event, DocumentIngested):
        envelope["source_id"] = str(event.source_id)
        envelope["title"] = event.title
        envelope["checksum"] = str(event.checksum)
        envelope["classification"] = event.classification
    elif isinstance(event, ChunkCreated):
        envelope["document_id"] = str(event.document_id)
        envelope["chunk_index"] = event.chunk_index.value
    elif isinstance(event, IngestionFailed):
        envelope["error_message"] = event.error_message
    return envelope


async def publish_knowledge_outbox_events(
    js: JetStreamContext,
    *,
    outbox: KnowledgeOutboxPort | None = None,
    batch: int = 10,
    interval_seconds: float = 5.0,
    max_iterations: int = 0,
) -> None:
    _iterations = 0
    while True:
        _iterations += 1
        db = create_session() if outbox is None else None
        try:
            repo = outbox or SqlAlchemyKnowledgeOutboxAdapter(db)  # type: ignore[arg-type]
            events = repo.fetch_unpublished(limit=batch)
            for event in events:
                subject = _NATS_SUBJECT_MAP.get(
                    type(event), "jarvis.knowledge.event.unknown.v1"
                )
                envelope = _build_envelope(event)
                serialized = json.dumps(
                    envelope, separators=(",", ":")
                ).encode("utf-8")
                await js.publish(subject, serialized)
                repo.mark_published(str(event.event_id))
                logger.info(
                    "Knowledge outbox event published",
                    subject=subject,
                    event_id=str(event.event_id),
                )
            if db is not None:
                db.commit()
        except Exception as exc:
            if db is not None:
                db.rollback()
            logger.error(
                "Knowledge outbox iteration failed",
                error=str(exc),
            )
        finally:
            if db is not None:
                db.close()
        if 0 < max_iterations <= _iterations:
            break
        await asyncio.sleep(interval_seconds)

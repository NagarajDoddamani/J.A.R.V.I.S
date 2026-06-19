from __future__ import annotations

import json
from uuid import UUID, uuid4

from backend.knowledge.application.persistence.dto import (
    IngestionJobStorageDTO,
    KnowledgeChunkStorageDTO,
    KnowledgeDocumentStorageDTO,
    KnowledgeOutboxStorageDTO,
    KnowledgeSourceStorageDTO,
)
from backend.knowledge.domain.model import (
    ChunkContent,
    ChunkCreated,
    ChunkId,
    ChunkIndex,
    DocumentChecksum,
    DocumentDeleted,
    DocumentId,
    DocumentIndexed,
    DocumentIngested,
    DocumentStatus,
    IngestionCompleted,
    IngestionFailed,
    IngestionJob,
    IngestionJobId,
    IngestionStarted,
    IngestionStatus,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeSource,
    KnowledgeSourceDeleted,
    KnowledgeSourceId,
    KnowledgeSourceRegistered,
    ReindexRequested,
    SourceLocation,
    SourceStatus,
    SourceType,
)

KnowledgeOutboxDomainEvent = (
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
    KnowledgeSourceRegistered: "knowledge.source.registered",
    KnowledgeSourceDeleted: "knowledge.source.deleted",
    DocumentIngested: "knowledge.document.ingested",
    DocumentIndexed: "knowledge.document.indexed",
    DocumentDeleted: "knowledge.document.deleted",
    ChunkCreated: "knowledge.chunk.created",
    ReindexRequested: "knowledge.reindex.requested",
    IngestionStarted: "knowledge.ingestion.started",
    IngestionCompleted: "knowledge.ingestion.completed",
    IngestionFailed: "knowledge.ingestion.failed",
}

_EVENT_TYPE_REVERSE: dict[str, type] = {v: k for k, v in _EVENT_TYPE_MAP.items()}


class KnowledgeSourceMapperImpl:
    def domain_to_dto(self, source: KnowledgeSource) -> KnowledgeSourceStorageDTO:
        return KnowledgeSourceStorageDTO(
            source_id=str(source.source_id),
            name=source.name,
            source_type=source.source_type.value,
            location=str(source.location) if source.location else None,
            classification=source.classification,
            status=source.status.value,
            created_at=source.created_at,
            updated_at=source.updated_at,
            deleted_at=source.deleted_at,
        )

    def dto_to_domain(self, dto: KnowledgeSourceStorageDTO) -> KnowledgeSource:
        location = SourceLocation(value=dto.location) if dto.location else None
        return KnowledgeSource(
            source_id=KnowledgeSourceId(value=UUID(dto.source_id)),
            name=dto.name,
            source_type=SourceType(dto.source_type),
            location=location,
            classification=dto.classification,
            status=SourceStatus(dto.status),
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            deleted_at=dto.deleted_at,
        )


class KnowledgeDocumentMapperImpl:
    def domain_to_dto(self, document: KnowledgeDocument) -> KnowledgeDocumentStorageDTO:
        return KnowledgeDocumentStorageDTO(
            document_id=str(document.document_id),
            source_id=str(document.source_id) if document.source_id else None,
            title=document.title,
            checksum=str(document.checksum) if document.checksum else None,
            classification=document.classification,
            status=document.status.value,
            revision=document.revision,
            created_at=document.created_at,
            updated_at=document.updated_at,
            deleted_at=document.deleted_at,
        )

    def dto_to_domain(self, dto: KnowledgeDocumentStorageDTO) -> KnowledgeDocument:
        source_id = KnowledgeSourceId(value=UUID(dto.source_id)) if dto.source_id else None
        checksum = DocumentChecksum(value=dto.checksum) if dto.checksum else None
        return KnowledgeDocument(
            document_id=DocumentId(value=UUID(dto.document_id)),
            source_id=source_id,
            title=dto.title,
            checksum=checksum,
            classification=dto.classification,
            status=DocumentStatus(dto.status),
            revision=dto.revision,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            deleted_at=dto.deleted_at,
        )


class KnowledgeChunkMapperImpl:
    def domain_to_dto(self, chunk: KnowledgeChunk) -> KnowledgeChunkStorageDTO:
        return KnowledgeChunkStorageDTO(
            chunk_id=str(chunk.chunk_id),
            document_id=str(chunk.document_id) if chunk.document_id else None,
            chunk_index=int(chunk.chunk_index) if chunk.chunk_index is not None else None,
            content=chunk.content.value if chunk.content else None,
            classification=chunk.classification,
            created_at=chunk.created_at,
        )

    def dto_to_domain(self, dto: KnowledgeChunkStorageDTO) -> KnowledgeChunk:
        document_id = DocumentId(value=UUID(dto.document_id)) if dto.document_id else None
        chunk_index = ChunkIndex(value=dto.chunk_index) if dto.chunk_index is not None else None
        content = ChunkContent(value=dto.content) if dto.content else None
        return KnowledgeChunk(
            chunk_id=ChunkId(value=UUID(dto.chunk_id)),
            document_id=document_id,
            chunk_index=chunk_index,
            content=content,
            classification=dto.classification,
            created_at=dto.created_at,
        )


class IngestionJobMapperImpl:
    def domain_to_dto(self, job: IngestionJob) -> IngestionJobStorageDTO:
        return IngestionJobStorageDTO(
            job_id=str(job.job_id),
            source_id=str(job.source_id) if job.source_id else None,
            status=job.status.value,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )

    def dto_to_domain(self, dto: IngestionJobStorageDTO) -> IngestionJob:
        source_id = KnowledgeSourceId(value=UUID(dto.source_id)) if dto.source_id else None
        return IngestionJob(
            job_id=IngestionJobId(value=UUID(dto.job_id)),
            source_id=source_id,
            status=IngestionStatus(dto.status),
            started_at=dto.started_at,
            completed_at=dto.completed_at,
            error_message=dto.error_message,
        )


class KnowledgeOutboxMapperImpl:
    def event_to_dto(self, event: KnowledgeOutboxDomainEvent) -> KnowledgeOutboxStorageDTO:
        event_type = _EVENT_TYPE_MAP.get(type(event), "unknown")
        aggregate_id = self._get_aggregate_id(event)
        payload = self._build_payload(event)
        return KnowledgeOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type=event_type,
            aggregate_id=aggregate_id,
            occurred_at=event.occurred_at,
            payload=json.dumps(payload) if payload else None,
            published=False,
        )

    def dto_to_event(self, dto: KnowledgeOutboxStorageDTO) -> KnowledgeOutboxDomainEvent:
        event_cls = _EVENT_TYPE_REVERSE.get(dto.event_type)
        if event_cls is None:
            raise ValueError(f"Unknown event_type: {dto.event_type}")
        payload = json.loads(dto.payload) if dto.payload else {}
        aggregate_uuid = UUID(dto.aggregate_id)
        event_uuid = UUID(dto.event_id)

        if event_cls is KnowledgeSourceRegistered:
            return KnowledgeSourceRegistered(
                event_id=event_uuid,
                source_id=KnowledgeSourceId(value=aggregate_uuid),
                name=payload.get("name", ""),
                source_type=SourceType(payload.get("source_type", "file")),
                location=SourceLocation(value=payload.get("location", "")),
                classification=payload.get("classification", "public"),
                occurred_at=dto.occurred_at,
            )
        if event_cls is KnowledgeSourceDeleted:
            return KnowledgeSourceDeleted(
                event_id=event_uuid,
                source_id=KnowledgeSourceId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is DocumentIngested:
            return DocumentIngested(
                event_id=event_uuid,
                document_id=DocumentId(value=aggregate_uuid),
                source_id=KnowledgeSourceId(value=UUID(payload["source_id"])),
                title=payload.get("title", ""),
                checksum=DocumentChecksum(value=payload.get("checksum", "")),
                classification=payload.get("classification", "public"),
                occurred_at=dto.occurred_at,
            )
        if event_cls is DocumentIndexed:
            return DocumentIndexed(
                event_id=event_uuid,
                document_id=DocumentId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is DocumentDeleted:
            return DocumentDeleted(
                event_id=event_uuid,
                document_id=DocumentId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is ChunkCreated:
            return ChunkCreated(
                event_id=event_uuid,
                chunk_id=ChunkId(value=aggregate_uuid),
                document_id=DocumentId(value=UUID(payload["document_id"])),
                chunk_index=ChunkIndex(value=payload.get("chunk_index", 0)),
                occurred_at=dto.occurred_at,
            )
        if event_cls is ReindexRequested:
            return ReindexRequested(
                event_id=event_uuid,
                source_id=KnowledgeSourceId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is IngestionStarted:
            return IngestionStarted(
                event_id=event_uuid,
                job_id=IngestionJobId(value=aggregate_uuid),
                source_id=KnowledgeSourceId(value=UUID(payload["source_id"])),
                occurred_at=dto.occurred_at,
            )
        if event_cls is IngestionCompleted:
            return IngestionCompleted(
                event_id=event_uuid,
                job_id=IngestionJobId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is IngestionFailed:
            return IngestionFailed(
                event_id=event_uuid,
                job_id=IngestionJobId(value=aggregate_uuid),
                error_message=payload.get("error_message", ""),
                occurred_at=dto.occurred_at,
            )
        raise ValueError(f"Unsupported event type: {event_cls}")

    @staticmethod
    def _get_aggregate_id(event: KnowledgeOutboxDomainEvent) -> str:
        if isinstance(event, (KnowledgeSourceRegistered, KnowledgeSourceDeleted, ReindexRequested)):
            return str(event.source_id)
        if isinstance(event, (DocumentIngested, DocumentIndexed, DocumentDeleted)):
            return str(event.document_id)
        if isinstance(event, ChunkCreated):
            return str(event.chunk_id)
        return str(event.job_id)

    @staticmethod
    def _build_payload(event: KnowledgeOutboxDomainEvent) -> dict | None:
        if isinstance(event, KnowledgeSourceRegistered):
            return {
                "name": event.name,
                "source_type": event.source_type.value,
                "location": str(event.location),
                "classification": event.classification,
            }
        if isinstance(event, DocumentIngested):
            return {
                "source_id": str(event.source_id),
                "title": event.title,
                "checksum": str(event.checksum),
                "classification": event.classification,
            }
        if isinstance(event, ChunkCreated):
            return {
                "document_id": str(event.document_id),
                "chunk_index": int(event.chunk_index),
            }
        if isinstance(event, IngestionStarted):
            return {
                "source_id": str(event.source_id),
            }
        if isinstance(event, IngestionFailed):
            return {
                "error_message": event.error_message,
            }
        return None

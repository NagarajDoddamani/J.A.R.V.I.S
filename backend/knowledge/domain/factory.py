from __future__ import annotations

from datetime import datetime, timezone

from backend.knowledge.domain.exceptions import InvalidSourceTypeError
from backend.knowledge.domain.model import (
    ChunkContent,
    ChunkCreated,
    ChunkId,
    ChunkIndex,
    DocumentChecksum,
    DocumentId,
    DocumentIngested,
    DocumentStatus,
    IngestionJob,
    IngestionJobId,
    IngestionStarted,
    IngestionStatus,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeSource,
    KnowledgeSourceId,
    KnowledgeSourceRegistered,
    ReindexRequested,
    SourceLocation,
    SourceStatus,
    SourceType,
)
from backend.knowledge.domain.rules import (
    assert_chunk_index_monotonic,
    assert_classification_valid,
    assert_reindex_allowed,
    assert_source_active,
    assert_source_name_not_empty,
    validate_chunk_creation,
    validate_document_ingestion,
    validate_source_registration,
)


class KnowledgeFactory:
    """Factory for creating validated knowledge domain aggregates."""

    @staticmethod
    def register_source(
        *,
        name: str,
        source_type: str | SourceType,
        location: str | SourceLocation,
        classification: str,
    ) -> tuple[KnowledgeSource, KnowledgeSourceRegistered]:
        if isinstance(source_type, str):
            try:
                source_type = SourceType(source_type)
            except ValueError:
                raise InvalidSourceTypeError(source_type)
        if isinstance(location, str):
            location = SourceLocation(value=location)

        validate_source_registration(
            name=name,
            source_type=source_type,
            location=location,
            classification=classification,
        )

        now = datetime.now(tz=timezone.utc)
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name=name,
            source_type=source_type,
            location=location,
            classification=classification,
            status=SourceStatus.REGISTERED,
            created_at=now,
        )

        event = KnowledgeSourceRegistered(
            source_id=source.source_id,
            name=name,
            source_type=source_type,
            location=location,
            classification=classification,
            occurred_at=now,
        )

        return source, event

    @staticmethod
    def ingest_document(
        *,
        source: KnowledgeSource,
        title: str,
        checksum: str | DocumentChecksum,
        classification: str,
    ) -> tuple[KnowledgeDocument, DocumentIngested]:
        if isinstance(checksum, str):
            checksum = DocumentChecksum(value=checksum)

        validate_document_ingestion(
            source=source,
            title=title,
            checksum=checksum,
            classification=classification,
        )

        now = datetime.now(tz=timezone.utc)
        document = KnowledgeDocument(
            document_id=DocumentId(),
            source_id=source.source_id,
            title=title,
            checksum=checksum,
            classification=classification,
            status=DocumentStatus.PENDING,
            revision=1,
            created_at=now,
        )

        event = DocumentIngested(
            document_id=document.document_id,
            source_id=source.source_id,
            title=title,
            checksum=checksum,
            classification=classification,
            occurred_at=now,
        )

        return document, event

    @staticmethod
    def create_chunk(
        *,
        document: KnowledgeDocument,
        chunk_index: int | ChunkIndex,
        content: str | ChunkContent,
        classification: str,
        existing_indices: list[ChunkIndex] | None = None,
    ) -> tuple[KnowledgeChunk, ChunkCreated]:
        if isinstance(chunk_index, int):
            chunk_index = ChunkIndex(value=chunk_index)
        if isinstance(content, str):
            content = ChunkContent(value=content)

        existing = existing_indices or []
        validate_chunk_creation(
            document=document,
            content=content,
            existing_indices=existing,
        )
        assert_classification_valid(classification)
        assert_chunk_index_monotonic(chunk_index, existing)

        now = datetime.now(tz=timezone.utc)

        chunk = KnowledgeChunk(
            chunk_id=ChunkId(),
            document_id=document.document_id,
            chunk_index=chunk_index,
            content=content,
            classification=classification,
            created_at=now,
        )

        event = ChunkCreated(
            chunk_id=chunk.chunk_id,
            document_id=document.document_id,
            chunk_index=chunk_index,
            occurred_at=now,
        )

        return chunk, event

    @staticmethod
    def request_reindex(
        source: KnowledgeSource,
    ) -> ReindexRequested:
        assert_reindex_allowed(source)

        event = ReindexRequested(
            source_id=source.source_id,
            occurred_at=datetime.now(tz=timezone.utc),
        )

        return event

    @staticmethod
    def start_ingestion(
        source: KnowledgeSource,
    ) -> tuple[IngestionJob, IngestionStarted]:
        assert_source_active(source)
        assert_source_name_not_empty(source.name)

        now = datetime.now(tz=timezone.utc)
        job = IngestionJob(
            job_id=IngestionJobId(),
            source_id=source.source_id,
            status=IngestionStatus.RUNNING,
            started_at=now,
        )

        event = IngestionStarted(
            job_id=job.job_id,
            source_id=source.source_id,
            occurred_at=now,
        )

        return job, event

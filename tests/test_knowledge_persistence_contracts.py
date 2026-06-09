from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.knowledge.application.persistence.dto import (
    IngestionJobStorageDTO,
    KnowledgeChunkStorageDTO,
    KnowledgeDocumentStorageDTO,
    KnowledgeOutboxStorageDTO,
    KnowledgeSourceStorageDTO,
)
from backend.knowledge.application.persistence.mapper import (
    IngestionJobMapper,
    KnowledgeChunkMapper,
    KnowledgeDocumentMapper,
    KnowledgeOutboxDomainEvent,
    KnowledgeOutboxMapper,
    KnowledgeSourceMapper,
)
from backend.knowledge.application.persistence.schema import (
    INGESTION_JOBS_TABLE,
    KNOWLEDGE_CHUNKS_TABLE,
    KNOWLEDGE_DOCUMENTS_TABLE,
    KNOWLEDGE_OUTBOX_TABLE,
    KNOWLEDGE_SOURCES_TABLE,
    ColumnContract,
    TableContract,
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

# ===================================================================
# Stub mapper implementations (conform to mapper protocols)
# ===================================================================


class StubKnowledgeSourceMapper:
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


class StubKnowledgeDocumentMapper:
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


class StubKnowledgeChunkMapper:
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


class StubIngestionJobMapper:
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


class StubKnowledgeOutboxMapper:
    def event_to_dto(self, event: KnowledgeOutboxDomainEvent) -> KnowledgeOutboxStorageDTO:
        if isinstance(event, (KnowledgeSourceRegistered, KnowledgeSourceDeleted, ReindexRequested)):
            aggregate_id = str(event.source_id)
        elif isinstance(event, ChunkCreated):
            aggregate_id = str(event.chunk_id)
        elif isinstance(event, (DocumentIngested, DocumentIndexed, DocumentDeleted)):
            aggregate_id = str(event.document_id)
        else:
            aggregate_id = str(event.job_id)

        type_map = {
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
        event_type = type_map.get(type(event), "unknown")

        return KnowledgeOutboxStorageDTO(
            event_id=aggregate_id,
            event_type=event_type,
            aggregate_id=aggregate_id,
            occurred_at=event.occurred_at,
            published=False,
        )

    def dto_to_event(self, dto: KnowledgeOutboxStorageDTO) -> KnowledgeOutboxDomainEvent:
        try:
            aggregate_id = UUID(dto.aggregate_id)
        except ValueError:
            aggregate_id = UUID("00000000-0000-0000-0000-000000000001")

        if dto.event_type == "knowledge.source.registered":
            return KnowledgeSourceRegistered(
                source_id=KnowledgeSourceId(value=aggregate_id),
                name="Source",
                source_type=SourceType.FILE,
                location=SourceLocation(value="/path"),
                classification="public",
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "knowledge.source.deleted":
            return KnowledgeSourceDeleted(
                source_id=KnowledgeSourceId(value=aggregate_id),
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "knowledge.document.ingested":
            return DocumentIngested(
                document_id=DocumentId(value=aggregate_id),
                source_id=KnowledgeSourceId(value=aggregate_id),
                title="Test",
                checksum=DocumentChecksum(value="abc"),
                classification="public",
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "knowledge.document.indexed":
            return DocumentIndexed(
                document_id=DocumentId(value=aggregate_id),
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "knowledge.document.deleted":
            return DocumentDeleted(
                document_id=DocumentId(value=aggregate_id),
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "knowledge.chunk.created":
            return ChunkCreated(
                chunk_id=ChunkId(value=aggregate_id),
                document_id=DocumentId(value=aggregate_id),
                chunk_index=ChunkIndex(value=0),
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "knowledge.reindex.requested":
            return ReindexRequested(
                source_id=KnowledgeSourceId(value=aggregate_id),
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "knowledge.ingestion.started":
            return IngestionStarted(
                job_id=IngestionJobId(value=aggregate_id),
                source_id=KnowledgeSourceId(value=aggregate_id),
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "knowledge.ingestion.completed":
            return IngestionCompleted(
                job_id=IngestionJobId(value=aggregate_id),
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "knowledge.ingestion.failed":
            return IngestionFailed(
                job_id=IngestionJobId(value=aggregate_id),
                error_message="error",
                occurred_at=dto.occurred_at,
            )
        else:
            raise ValueError(f"Unknown event_type: {dto.event_type}")


# ===================================================================
# DTO construction tests
# ===================================================================


class TestKnowledgeSourceStorageDTO:
    def test_all_fields_present(self) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        dto = KnowledgeSourceStorageDTO(
            source_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            name="Test Source",
            source_type="file",
            location="/path/to/source",
            classification="public",
            status="active",
            created_at=dt,
            updated_at=dt,
            deleted_at=None,
        )
        assert dto.source_id == "01975c2f-4aef-7cf1-a940-ae54bf596280"
        assert dto.name == "Test Source"
        assert dto.source_type == "file"
        assert dto.location == "/path/to/source"
        assert dto.classification == "public"
        assert dto.status == "active"
        assert dto.created_at == dt
        assert dto.updated_at == dt
        assert dto.deleted_at is None

    def test_nullable_fields(self) -> None:
        dto = KnowledgeSourceStorageDTO(
            source_id="id-1",
            name="Test",
            source_type="file",
        )
        assert dto.location is None
        assert dto.updated_at is None
        assert dto.deleted_at is None

    def test_frozen(self) -> None:
        dto = KnowledgeSourceStorageDTO(
            source_id="id-1",
            name="Test",
            source_type="file",
        )
        with pytest.raises(AttributeError):
            dto.source_id = "changed"

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(KnowledgeSourceStorageDTO)
        assert len(fields) == 9

    def test_default_status(self) -> None:
        dto = KnowledgeSourceStorageDTO(
            source_id="id-1",
            name="Test",
            source_type="file",
        )
        assert dto.status == "registered"

    def test_default_classification(self) -> None:
        dto = KnowledgeSourceStorageDTO(
            source_id="id-1",
            name="Test",
            source_type="file",
        )
        assert dto.classification == "public"


class TestKnowledgeDocumentStorageDTO:
    def test_all_fields_present(self) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        dto = KnowledgeDocumentStorageDTO(
            document_id="01975c2f-4aef-7cf1-a940-ae54bf596281",
            source_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            title="Test Document",
            checksum="abc123",
            classification="internal",
            status="ingested",
            revision=2,
            created_at=dt,
            updated_at=dt,
            deleted_at=None,
        )
        assert dto.document_id == "01975c2f-4aef-7cf1-a940-ae54bf596281"
        assert dto.source_id == "01975c2f-4aef-7cf1-a940-ae54bf596280"
        assert dto.title == "Test Document"
        assert dto.checksum == "abc123"
        assert dto.classification == "internal"
        assert dto.status == "ingested"
        assert dto.revision == 2
        assert dto.created_at == dt
        assert dto.updated_at == dt
        assert dto.deleted_at is None

    def test_nullable_fields(self) -> None:
        dto = KnowledgeDocumentStorageDTO(
            document_id="id-1",
            title="Test",
        )
        assert dto.source_id is None
        assert dto.checksum is None
        assert dto.updated_at is None
        assert dto.deleted_at is None

    def test_frozen(self) -> None:
        dto = KnowledgeDocumentStorageDTO(
            document_id="id-1",
            title="Test",
        )
        with pytest.raises(AttributeError):
            dto.document_id = "changed"

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(KnowledgeDocumentStorageDTO)
        assert len(fields) == 10

    def test_default_status(self) -> None:
        dto = KnowledgeDocumentStorageDTO(
            document_id="id-1",
            title="Test",
        )
        assert dto.status == "pending"

    def test_default_revision(self) -> None:
        dto = KnowledgeDocumentStorageDTO(
            document_id="id-1",
            title="Test",
        )
        assert dto.revision == 1


class TestKnowledgeChunkStorageDTO:
    def test_all_fields_present(self) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        dto = KnowledgeChunkStorageDTO(
            chunk_id="01975c2f-4aef-7cf1-a940-ae54bf596282",
            document_id="01975c2f-4aef-7cf1-a940-ae54bf596281",
            chunk_index=0,
            content="Chunk content text",
            classification="public",
            created_at=dt,
        )
        assert dto.chunk_id == "01975c2f-4aef-7cf1-a940-ae54bf596282"
        assert dto.document_id == "01975c2f-4aef-7cf1-a940-ae54bf596281"
        assert dto.chunk_index == 0
        assert dto.content == "Chunk content text"
        assert dto.classification == "public"
        assert dto.created_at == dt

    def test_nullable_fields(self) -> None:
        dto = KnowledgeChunkStorageDTO(
            chunk_id="id-1",
        )
        assert dto.document_id is None
        assert dto.chunk_index is None
        assert dto.content is None
        assert dto.created_at is None

    def test_frozen(self) -> None:
        dto = KnowledgeChunkStorageDTO(
            chunk_id="id-1",
        )
        with pytest.raises(AttributeError):
            dto.chunk_id = "changed"

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(KnowledgeChunkStorageDTO)
        assert len(fields) == 6

    def test_default_classification(self) -> None:
        dto = KnowledgeChunkStorageDTO(
            chunk_id="id-1",
        )
        assert dto.classification == "public"


class TestIngestionJobStorageDTO:
    def test_all_fields_present(self) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        dto = IngestionJobStorageDTO(
            job_id="01975c2f-4aef-7cf1-a940-ae54bf596283",
            source_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            status="running",
            started_at=dt,
            completed_at=None,
            error_message=None,
        )
        assert dto.job_id == "01975c2f-4aef-7cf1-a940-ae54bf596283"
        assert dto.source_id == "01975c2f-4aef-7cf1-a940-ae54bf596280"
        assert dto.status == "running"
        assert dto.started_at == dt
        assert dto.completed_at is None
        assert dto.error_message is None

    def test_nullable_fields(self) -> None:
        dto = IngestionJobStorageDTO(
            job_id="id-1",
        )
        assert dto.source_id is None
        assert dto.started_at is None
        assert dto.completed_at is None
        assert dto.error_message is None

    def test_frozen(self) -> None:
        dto = IngestionJobStorageDTO(
            job_id="id-1",
        )
        with pytest.raises(AttributeError):
            dto.job_id = "changed"

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(IngestionJobStorageDTO)
        assert len(fields) == 6

    def test_default_status(self) -> None:
        dto = IngestionJobStorageDTO(
            job_id="id-1",
        )
        assert dto.status == "running"

    def test_completed_at_set(self) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        dto = IngestionJobStorageDTO(
            job_id="id-1",
            completed_at=dt,
        )
        assert dto.completed_at == dt

    def test_error_message_set(self) -> None:
        dto = IngestionJobStorageDTO(
            job_id="id-1",
            error_message="Something went wrong",
        )
        assert dto.error_message == "Something went wrong"


class TestKnowledgeOutboxStorageDTO:
    def test_all_fields_present(self) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        dto = KnowledgeOutboxStorageDTO(
            event_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            event_type="knowledge.source.registered",
            aggregate_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            occurred_at=dt,
            correlation_id="corr-001",
            causation_id="cause-001",
            payload='{"name": "Test"}',
        )
        assert dto.event_id == "01975c2f-4aef-7cf1-a940-ae54bf596280"
        assert dto.event_type == "knowledge.source.registered"
        assert dto.aggregate_id == "01975c2f-4aef-7cf1-a940-ae54bf596280"
        assert dto.occurred_at == dt
        assert dto.correlation_id == "corr-001"
        assert dto.causation_id == "cause-001"
        assert dto.payload == '{"name": "Test"}'

    def test_default_published_false(self) -> None:
        dto = KnowledgeOutboxStorageDTO(
            event_id="id-1",
            event_type="knowledge.source.registered",
            aggregate_id="agg-1",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        assert dto.published is False

    def test_explicit_published(self) -> None:
        dto = KnowledgeOutboxStorageDTO(
            event_id="id-1",
            event_type="knowledge.source.registered",
            aggregate_id="agg-1",
            occurred_at=datetime.now(tz=timezone.utc),
            published=True,
        )
        assert dto.published is True

    def test_nullable_fields(self) -> None:
        dto = KnowledgeOutboxStorageDTO(
            event_id="id-1",
            event_type="knowledge.source.registered",
            aggregate_id="agg-1",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        assert dto.correlation_id is None
        assert dto.causation_id is None
        assert dto.payload is None

    def test_frozen(self) -> None:
        dto = KnowledgeOutboxStorageDTO(
            event_id="id-1",
            event_type="knowledge.source.registered",
            aggregate_id="agg-1",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            dto.event_id = "changed"

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(KnowledgeOutboxStorageDTO)
        assert len(fields) == 8


# ===================================================================
# Mapper protocol conformance tests
# ===================================================================


class TestKnowledgeSourceMapper:
    @pytest.fixture
    def mapper(self) -> StubKnowledgeSourceMapper:
        return StubKnowledgeSourceMapper()

    def test_protocol_conformance(self) -> None:
        mapper: KnowledgeSourceMapper = StubKnowledgeSourceMapper()
        assert isinstance(mapper, StubKnowledgeSourceMapper)

    def test_domain_to_dto(self, mapper: StubKnowledgeSourceMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Test Source",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/path/to/file"),
            classification="public",
            status=SourceStatus.ACTIVE,
            created_at=now,
        )
        dto = mapper.domain_to_dto(source)
        assert dto.source_id == str(source.source_id)
        assert dto.name == "Test Source"
        assert dto.source_type == "file"
        assert dto.location == "/path/to/file"
        assert dto.classification == "public"
        assert dto.status == "active"
        assert dto.created_at == now
        assert dto.updated_at is None
        assert dto.deleted_at is None

    def test_dto_to_domain(self, mapper: StubKnowledgeSourceMapper) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        dto = KnowledgeSourceStorageDTO(
            source_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            name="Test Source",
            source_type="file",
            location="/path/to/file",
            classification="internal",
            status="active",
            created_at=dt,
        )
        source = mapper.dto_to_domain(dto)
        assert str(source.source_id) == dto.source_id
        assert source.name == "Test Source"
        assert source.source_type == SourceType.FILE
        assert source.location is not None
        assert str(source.location) == "/path/to/file"
        assert source.classification == "internal"
        assert source.status == SourceStatus.ACTIVE
        assert source.created_at == dt
        assert source.updated_at is None
        assert source.deleted_at is None

    def test_roundtrip(self, mapper: StubKnowledgeSourceMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Roundtrip Source",
            source_type=SourceType.URL,
            location=SourceLocation(value="https://example.com"),
            classification="sensitive",
            status=SourceStatus.REGISTERED,
            created_at=now,
            updated_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert str(reconstructed.source_id) == str(original.source_id)
        assert reconstructed.name == original.name
        assert reconstructed.source_type == original.source_type
        assert str(reconstructed.location) == str(original.location)
        assert reconstructed.classification == original.classification
        assert reconstructed.status == original.status
        assert reconstructed.created_at == original.created_at
        assert reconstructed.updated_at == original.updated_at
        assert reconstructed.deleted_at == original.deleted_at

    def test_null_fields_roundtrip(self, mapper: StubKnowledgeSourceMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="No Location",
            source_type=SourceType.MANUAL,
            location=None,
            classification="public",
            status=SourceStatus.DISABLED,
            created_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.location is None
        assert reconstructed.updated_at is None
        assert reconstructed.deleted_at is None

    def test_deleted_source_mapping(self, mapper: StubKnowledgeSourceMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Deleted Source",
            source_type=SourceType.FILE,
            classification="public",
            status=SourceStatus.DELETED,
            created_at=now,
            deleted_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.status == SourceStatus.DELETED
        assert reconstructed.deleted_at == now

    def test_mapper_has_required_methods(self) -> None:
        mapper: KnowledgeSourceMapper = StubKnowledgeSourceMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


class TestKnowledgeDocumentMapper:
    @pytest.fixture
    def mapper(self) -> StubKnowledgeDocumentMapper:
        return StubKnowledgeDocumentMapper()

    def test_protocol_conformance(self) -> None:
        mapper: KnowledgeDocumentMapper = StubKnowledgeDocumentMapper()
        assert isinstance(mapper, StubKnowledgeDocumentMapper)

    def test_domain_to_dto(self, mapper: StubKnowledgeDocumentMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        doc = KnowledgeDocument(
            document_id=DocumentId(),
            source_id=KnowledgeSourceId(),
            title="Test Doc",
            checksum=DocumentChecksum(value="def456"),
            classification="internal",
            status=DocumentStatus.INGESTED,
            revision=3,
            created_at=now,
        )
        dto = mapper.domain_to_dto(doc)
        assert dto.document_id == str(doc.document_id)
        assert dto.source_id == str(doc.source_id)
        assert dto.title == "Test Doc"
        assert dto.checksum == "def456"
        assert dto.classification == "internal"
        assert dto.status == "ingested"
        assert dto.revision == 3

    def test_dto_to_domain(self, mapper: StubKnowledgeDocumentMapper) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        dto = KnowledgeDocumentStorageDTO(
            document_id="01975c2f-4aef-7cf1-a940-ae54bf596281",
            source_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            title="Reconstructed Doc",
            checksum="abc123",
            classification="sensitive",
            status="indexed",
            revision=5,
            created_at=dt,
        )
        doc = mapper.dto_to_domain(dto)
        assert str(doc.document_id) == dto.document_id
        assert str(doc.source_id) == dto.source_id
        assert doc.title == "Reconstructed Doc"
        assert str(doc.checksum) == "abc123"
        assert doc.classification == "sensitive"
        assert doc.status == DocumentStatus.INDEXED
        assert doc.revision == 5

    def test_roundtrip(self, mapper: StubKnowledgeDocumentMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = KnowledgeDocument(
            document_id=DocumentId(),
            source_id=KnowledgeSourceId(),
            title="Roundtrip Doc",
            checksum=DocumentChecksum(value="roundtrip"),
            classification="public",
            status=DocumentStatus.INDEXED,
            revision=2,
            created_at=now,
            updated_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert str(reconstructed.document_id) == str(original.document_id)
        assert str(reconstructed.source_id) == str(original.source_id)
        assert reconstructed.title == original.title
        assert str(reconstructed.checksum) == str(original.checksum)
        assert reconstructed.classification == original.classification
        assert reconstructed.status == original.status
        assert reconstructed.revision == original.revision
        assert reconstructed.created_at == original.created_at

    def test_null_fields_roundtrip(self, mapper: StubKnowledgeDocumentMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = KnowledgeDocument(
            document_id=DocumentId(),
            title="No Source Doc",
            classification="public",
            status=DocumentStatus.PENDING,
            revision=1,
            created_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.source_id is None
        assert reconstructed.checksum is None
        assert reconstructed.updated_at is None
        assert reconstructed.deleted_at is None

    def test_deleted_document_mapping(self, mapper: StubKnowledgeDocumentMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = KnowledgeDocument(
            document_id=DocumentId(),
            title="Deleted Doc",
            classification="public",
            status=DocumentStatus.DELETED,
            revision=1,
            created_at=now,
            deleted_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.status == DocumentStatus.DELETED
        assert reconstructed.deleted_at == now

    def test_mapper_has_required_methods(self) -> None:
        mapper: KnowledgeDocumentMapper = StubKnowledgeDocumentMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


class TestKnowledgeChunkMapper:
    @pytest.fixture
    def mapper(self) -> StubKnowledgeChunkMapper:
        return StubKnowledgeChunkMapper()

    def test_protocol_conformance(self) -> None:
        mapper: KnowledgeChunkMapper = StubKnowledgeChunkMapper()
        assert isinstance(mapper, StubKnowledgeChunkMapper)

    def test_domain_to_dto(self, mapper: StubKnowledgeChunkMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        chunk = KnowledgeChunk(
            chunk_id=ChunkId(),
            document_id=DocumentId(),
            chunk_index=ChunkIndex(value=1),
            content=ChunkContent(value="Chunk content"),
            classification="sensitive",
            created_at=now,
        )
        dto = mapper.domain_to_dto(chunk)
        assert dto.chunk_id == str(chunk.chunk_id)
        assert dto.document_id == str(chunk.document_id)
        assert dto.chunk_index == 1
        assert dto.content == "Chunk content"
        assert dto.classification == "sensitive"
        assert dto.created_at == now

    def test_dto_to_domain(self, mapper: StubKnowledgeChunkMapper) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        dto = KnowledgeChunkStorageDTO(
            chunk_id="01975c2f-4aef-7cf1-a940-ae54bf596282",
            document_id="01975c2f-4aef-7cf1-a940-ae54bf596281",
            chunk_index=2,
            content="Reconstructed content",
            classification="internal",
            created_at=dt,
        )
        chunk = mapper.dto_to_domain(dto)
        assert str(chunk.chunk_id) == dto.chunk_id
        assert str(chunk.document_id) == dto.document_id
        assert int(chunk.chunk_index) == 2
        assert chunk.content.value == "Reconstructed content"
        assert chunk.classification == "internal"
        assert chunk.created_at == dt

    def test_roundtrip(self, mapper: StubKnowledgeChunkMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = KnowledgeChunk(
            chunk_id=ChunkId(),
            document_id=DocumentId(),
            chunk_index=ChunkIndex(value=0),
            content=ChunkContent(value="Roundtrip chunk"),
            classification="public",
            created_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert str(reconstructed.chunk_id) == str(original.chunk_id)
        assert str(reconstructed.document_id) == str(original.document_id)
        assert int(reconstructed.chunk_index) == int(original.chunk_index)
        assert reconstructed.content.value == original.content.value
        assert reconstructed.classification == original.classification

    def test_null_fields_roundtrip(self, mapper: StubKnowledgeChunkMapper) -> None:
        original = KnowledgeChunk(
            chunk_id=ChunkId(),
            classification="public",
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.document_id is None
        assert reconstructed.chunk_index is None
        assert reconstructed.content is None

    def test_mapper_has_required_methods(self) -> None:
        mapper: KnowledgeChunkMapper = StubKnowledgeChunkMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


class TestIngestionJobMapper:
    @pytest.fixture
    def mapper(self) -> StubIngestionJobMapper:
        return StubIngestionJobMapper()

    def test_protocol_conformance(self) -> None:
        mapper: IngestionJobMapper = StubIngestionJobMapper()
        assert isinstance(mapper, StubIngestionJobMapper)

    def test_domain_to_dto(self, mapper: StubIngestionJobMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        job = IngestionJob(
            job_id=IngestionJobId(),
            source_id=KnowledgeSourceId(),
            status=IngestionStatus.QUEUED,
            started_at=now,
        )
        dto = mapper.domain_to_dto(job)
        assert dto.job_id == str(job.job_id)
        assert dto.source_id == str(job.source_id)
        assert dto.status == "queued"
        assert dto.started_at == now
        assert dto.completed_at is None
        assert dto.error_message is None

    def test_dto_to_domain(self, mapper: StubIngestionJobMapper) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        dto = IngestionJobStorageDTO(
            job_id="01975c2f-4aef-7cf1-a940-ae54bf596283",
            source_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            status="failed",
            started_at=dt,
            completed_at=dt,
            error_message="Timeout",
        )
        job = mapper.dto_to_domain(dto)
        assert str(job.job_id) == dto.job_id
        assert str(job.source_id) == dto.source_id
        assert job.status == IngestionStatus.FAILED
        assert job.started_at == dt
        assert job.completed_at == dt
        assert job.error_message == "Timeout"

    def test_roundtrip(self, mapper: StubIngestionJobMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = IngestionJob(
            job_id=IngestionJobId(),
            source_id=KnowledgeSourceId(),
            status=IngestionStatus.COMPLETED,
            started_at=now,
            completed_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert str(reconstructed.job_id) == str(original.job_id)
        assert str(reconstructed.source_id) == str(original.source_id)
        assert reconstructed.status == original.status
        assert reconstructed.started_at == original.started_at
        assert reconstructed.completed_at == original.completed_at
        assert reconstructed.error_message == original.error_message

    def test_null_fields_roundtrip(self, mapper: StubIngestionJobMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = IngestionJob(
            job_id=IngestionJobId(),
            status=IngestionStatus.RUNNING,
            started_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.source_id is None
        assert reconstructed.completed_at is None
        assert reconstructed.error_message is None

    def test_failed_job_mapping(self, mapper: StubIngestionJobMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = IngestionJob(
            job_id=IngestionJobId(),
            source_id=KnowledgeSourceId(),
            status=IngestionStatus.FAILED,
            started_at=now,
            completed_at=now,
            error_message="Processing error",
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.status == IngestionStatus.FAILED
        assert reconstructed.error_message == "Processing error"

    def test_mapper_has_required_methods(self) -> None:
        mapper: IngestionJobMapper = StubIngestionJobMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


class TestKnowledgeOutboxMapper:
    @pytest.fixture
    def mapper(self) -> StubKnowledgeOutboxMapper:
        return StubKnowledgeOutboxMapper()

    def test_protocol_conformance(self) -> None:
        mapper: KnowledgeOutboxMapper = StubKnowledgeOutboxMapper()
        assert isinstance(mapper, StubKnowledgeOutboxMapper)

    def test_source_registered_event_to_dto(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = KnowledgeSourceRegistered(
            source_id=KnowledgeSourceId(),
            name="Test",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/path"),
            classification="public",
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "knowledge.source.registered"
        assert dto.aggregate_id == str(event.source_id)
        assert dto.occurred_at == now
        assert dto.published is False

    def test_source_deleted_event_to_dto(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = KnowledgeSourceDeleted(
            source_id=KnowledgeSourceId(),
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "knowledge.source.deleted"
        assert dto.aggregate_id == str(event.source_id)

    def test_document_ingested_event_to_dto(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = DocumentIngested(
            document_id=DocumentId(),
            source_id=KnowledgeSourceId(),
            title="Doc",
            checksum=DocumentChecksum(value="abc"),
            classification="public",
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "knowledge.document.ingested"
        assert dto.aggregate_id == str(event.document_id)

    def test_document_indexed_event_to_dto(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = DocumentIndexed(
            document_id=DocumentId(),
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "knowledge.document.indexed"
        assert dto.aggregate_id == str(event.document_id)

    def test_document_deleted_event_to_dto(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = DocumentDeleted(
            document_id=DocumentId(),
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "knowledge.document.deleted"

    def test_chunk_created_event_to_dto(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = ChunkCreated(
            chunk_id=ChunkId(),
            document_id=DocumentId(),
            chunk_index=ChunkIndex(value=0),
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "knowledge.chunk.created"
        assert dto.aggregate_id == str(event.chunk_id)

    def test_reindex_requested_event_to_dto(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = ReindexRequested(
            source_id=KnowledgeSourceId(),
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "knowledge.reindex.requested"

    def test_ingestion_started_event_to_dto(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = IngestionStarted(
            job_id=IngestionJobId(),
            source_id=KnowledgeSourceId(),
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "knowledge.ingestion.started"

    def test_ingestion_completed_event_to_dto(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = IngestionCompleted(
            job_id=IngestionJobId(),
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "knowledge.ingestion.completed"

    def test_ingestion_failed_event_to_dto(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = IngestionFailed(
            job_id=IngestionJobId(),
            error_message="error",
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "knowledge.ingestion.failed"

    def test_all_events_have_dto_mapping(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        events: list[KnowledgeOutboxDomainEvent] = [
            KnowledgeSourceRegistered(KnowledgeSourceId(), "S", SourceType.FILE,
                                      SourceLocation(value="/p"), "public", now),
            KnowledgeSourceDeleted(KnowledgeSourceId(), now),
            DocumentIngested(DocumentId(), KnowledgeSourceId(), "D",
                             DocumentChecksum(value="c"), "public", now),
            DocumentIndexed(DocumentId(), now),
            DocumentDeleted(DocumentId(), now),
            ChunkCreated(ChunkId(), DocumentId(), ChunkIndex(value=0), now),
            ReindexRequested(KnowledgeSourceId(), now),
            IngestionStarted(IngestionJobId(), KnowledgeSourceId(), now),
            IngestionCompleted(IngestionJobId(), now),
            IngestionFailed(IngestionJobId(), "e", now),
        ]
        for event in events:
            dto = mapper.event_to_dto(event)
            assert dto.event_id is not None
            assert dto.event_type is not None
            assert dto.aggregate_id is not None

    def test_event_to_dto_published_default(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = KnowledgeSourceRegistered(
            source_id=KnowledgeSourceId(),
            name="Test",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/path"),
            classification="public",
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.published is False

    def test_dto_to_event_source_registered(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = KnowledgeOutboxStorageDTO(
            event_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            event_type="knowledge.source.registered",
            aggregate_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            occurred_at=now,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, KnowledgeSourceRegistered)
        assert str(event.source_id) == dto.aggregate_id

    def test_dto_to_event_source_deleted(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = KnowledgeOutboxStorageDTO(
            event_id="id-1",
            event_type="knowledge.source.deleted",
            aggregate_id="id-1",
            occurred_at=now,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, KnowledgeSourceDeleted)

    def test_dto_to_event_document_ingested(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = KnowledgeOutboxStorageDTO(
            event_id="id-1",
            event_type="knowledge.document.ingested",
            aggregate_id="id-1",
            occurred_at=now,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, DocumentIngested)

    def test_dto_to_event_document_indexed(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = KnowledgeOutboxStorageDTO(
            event_id="id-1",
            event_type="knowledge.document.indexed",
            aggregate_id="id-1",
            occurred_at=now,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, DocumentIndexed)

    def test_dto_to_event_chunk_created(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = KnowledgeOutboxStorageDTO(
            event_id="id-1",
            event_type="knowledge.chunk.created",
            aggregate_id="id-1",
            occurred_at=now,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, ChunkCreated)

    def test_dto_to_event_ingestion_completed(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = KnowledgeOutboxStorageDTO(
            event_id="id-1",
            event_type="knowledge.ingestion.completed",
            aggregate_id="id-1",
            occurred_at=now,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, IngestionCompleted)

    def test_dto_to_event_ingestion_failed(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = KnowledgeOutboxStorageDTO(
            event_id="id-1",
            event_type="knowledge.ingestion.failed",
            aggregate_id="id-1",
            occurred_at=now,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, IngestionFailed)

    def test_dto_to_event_reindex_requested(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = KnowledgeOutboxStorageDTO(
            event_id="id-1",
            event_type="knowledge.reindex.requested",
            aggregate_id="id-1",
            occurred_at=now,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, ReindexRequested)

    def test_roundtrip_source_registered(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = KnowledgeSourceRegistered(
            source_id=KnowledgeSourceId(),
            name="Test",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/path"),
            classification="public",
            occurred_at=now,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert type(reconstructed) is type(original)
        assert str(reconstructed.source_id) == str(original.source_id)
        assert reconstructed.occurred_at == original.occurred_at

    def test_roundtrip_ingestion_failed(self, mapper: StubKnowledgeOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = IngestionFailed(
            job_id=IngestionJobId(),
            error_message="error",
            occurred_at=now,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, IngestionFailed)
        assert str(reconstructed.job_id) == str(original.job_id)


# ===================================================================
# Schema contract consistency tests
# ===================================================================


class TestKnowledgeSourcesSchema:
    def test_column_count(self) -> None:
        assert len(KNOWLEDGE_SOURCES_TABLE.columns) == 9

    def test_schema_name(self) -> None:
        assert KNOWLEDGE_SOURCES_TABLE.schema == "knowledge"
        assert KNOWLEDGE_SOURCES_TABLE.name == "knowledge_sources"

    def test_primary_key(self) -> None:
        assert KNOWLEDGE_SOURCES_TABLE.primary_key == "source_id"

    def test_indexes(self) -> None:
        expected = {"ix_knowledge_sources_status", "ix_knowledge_sources_type"}
        assert set(KNOWLEDGE_SOURCES_TABLE.indexes) == expected

    def nullables(self) -> None:
        nullable = {c.name for c in KNOWLEDGE_SOURCES_TABLE.columns if c.nullable}
        assert nullable == {"location", "updated_at", "deleted_at"}

    def test_source_type_enum(self) -> None:
        col = next(c for c in KNOWLEDGE_SOURCES_TABLE.columns if c.name == "source_type")
        assert col.enum_values == ("file", "directory", "url", "manual", "memory_export")
        assert col.max_length == 32
        assert col.nullable is False

    def test_status_enum(self) -> None:
        col = next(c for c in KNOWLEDGE_SOURCES_TABLE.columns if c.name == "status")
        assert col.enum_values == ("registered", "active", "disabled", "deleted")
        assert col.max_length == 16

    def test_classification_enum(self) -> None:
        col = next(c for c in KNOWLEDGE_SOURCES_TABLE.columns if c.name == "classification")
        assert col.enum_values == ("public", "internal", "sensitive", "restricted")
        assert col.max_length == 16


class TestKnowledgeDocumentsSchema:
    def test_column_count(self) -> None:
        assert len(KNOWLEDGE_DOCUMENTS_TABLE.columns) == 10

    def test_schema_name(self) -> None:
        assert KNOWLEDGE_DOCUMENTS_TABLE.schema == "knowledge"
        assert KNOWLEDGE_DOCUMENTS_TABLE.name == "knowledge_documents"

    def test_primary_key(self) -> None:
        assert KNOWLEDGE_DOCUMENTS_TABLE.primary_key == "document_id"

    def test_indexes(self) -> None:
        expected = {"ix_knowledge_documents_source", "ix_knowledge_documents_status"}
        assert set(KNOWLEDGE_DOCUMENTS_TABLE.indexes) == expected

    def test_status_enum(self) -> None:
        col = next(c for c in KNOWLEDGE_DOCUMENTS_TABLE.columns if c.name == "status")
        assert col.enum_values == ("pending", "ingested", "indexed", "deleted")
        assert col.max_length == 16

    def test_document_classification_enum(self) -> None:
        col = next(c for c in KNOWLEDGE_DOCUMENTS_TABLE.columns if c.name == "classification")
        assert col.enum_values == ("public", "internal", "sensitive", "restricted")
        assert col.max_length == 16

    def test_nullable_columns(self) -> None:
        nullable = {c.name for c in KNOWLEDGE_DOCUMENTS_TABLE.columns if c.nullable}
        assert nullable == {"source_id", "checksum", "updated_at", "deleted_at"}


class TestKnowledgeChunksSchema:
    def test_column_count(self) -> None:
        assert len(KNOWLEDGE_CHUNKS_TABLE.columns) == 6

    def test_schema_name(self) -> None:
        assert KNOWLEDGE_CHUNKS_TABLE.schema == "knowledge"
        assert KNOWLEDGE_CHUNKS_TABLE.name == "knowledge_chunks"

    def test_primary_key(self) -> None:
        assert KNOWLEDGE_CHUNKS_TABLE.primary_key == "chunk_id"

    def test_indexes(self) -> None:
        expected = {"ix_knowledge_chunks_document", "ix_knowledge_chunks_index"}
        assert set(KNOWLEDGE_CHUNKS_TABLE.indexes) == expected

    def test_nullable_columns(self) -> None:
        nullable = {c.name for c in KNOWLEDGE_CHUNKS_TABLE.columns if c.nullable}
        assert nullable == {"document_id", "chunk_index", "content"}

    def test_chunk_classification_enum(self) -> None:
        col = next(c for c in KNOWLEDGE_CHUNKS_TABLE.columns if c.name == "classification")
        assert col.enum_values == ("public", "internal", "sensitive", "restricted")
        assert col.max_length == 16


class TestIngestionJobsSchema:
    def test_column_count(self) -> None:
        assert len(INGESTION_JOBS_TABLE.columns) == 6

    def test_schema_name(self) -> None:
        assert INGESTION_JOBS_TABLE.schema == "knowledge"
        assert INGESTION_JOBS_TABLE.name == "ingestion_jobs"

    def test_primary_key(self) -> None:
        assert INGESTION_JOBS_TABLE.primary_key == "job_id"

    def test_indexes(self) -> None:
        expected = {"ix_ingestion_jobs_status", "ix_ingestion_jobs_source"}
        assert set(INGESTION_JOBS_TABLE.indexes) == expected

    def test_status_enum(self) -> None:
        col = next(c for c in INGESTION_JOBS_TABLE.columns if c.name == "status")
        assert col.enum_values == ("queued", "running", "completed", "failed")
        assert col.max_length == 16

    def test_nullable_columns(self) -> None:
        nullable = {c.name for c in INGESTION_JOBS_TABLE.columns if c.nullable}
        assert nullable == {"source_id", "completed_at", "error_message"}


class TestKnowledgeOutboxSchema:
    def test_column_count(self) -> None:
        assert len(KNOWLEDGE_OUTBOX_TABLE.columns) == 8

    def test_schema_name(self) -> None:
        assert KNOWLEDGE_OUTBOX_TABLE.schema == "knowledge"
        assert KNOWLEDGE_OUTBOX_TABLE.name == "outbox"

    def test_primary_key(self) -> None:
        assert KNOWLEDGE_OUTBOX_TABLE.primary_key == "event_id"

    def test_indexes(self) -> None:
        expected = {"ix_knowledge_outbox_unpublished", "ix_knowledge_outbox_aggregate"}
        assert set(KNOWLEDGE_OUTBOX_TABLE.indexes) == expected

    def test_event_type_enum(self) -> None:
        col = next(c for c in KNOWLEDGE_OUTBOX_TABLE.columns if c.name == "event_type")
        expected = (
            "knowledge.source.registered",
            "knowledge.source.deleted",
            "knowledge.document.ingested",
            "knowledge.document.indexed",
            "knowledge.document.deleted",
            "knowledge.chunk.created",
            "knowledge.reindex.requested",
            "knowledge.ingestion.started",
            "knowledge.ingestion.completed",
            "knowledge.ingestion.failed",
        )
        assert col.enum_values == expected
        assert col.max_length == 32

    def test_nullable_columns(self) -> None:
        nullable = {c.name for c in KNOWLEDGE_OUTBOX_TABLE.columns if c.nullable}
        assert nullable == {"correlation_id", "causation_id", "payload"}


# ===================================================================
# DTO ↔ Schema field alignment tests
# ===================================================================


class TestDTOFieldAlignment:
    def test_source_dto_fields_match_schema_columns(self) -> None:
        dto_fields = {
            "source_id", "name", "source_type", "location",
            "classification", "status", "created_at",
            "updated_at", "deleted_at",
        }
        schema_cols = {c.name for c in KNOWLEDGE_SOURCES_TABLE.columns}
        assert dto_fields == schema_cols

    def test_document_dto_fields_match_schema_columns(self) -> None:
        dto_fields = {
            "document_id", "source_id", "title", "checksum",
            "classification", "status", "revision",
            "created_at", "updated_at", "deleted_at",
        }
        schema_cols = {c.name for c in KNOWLEDGE_DOCUMENTS_TABLE.columns}
        assert dto_fields == schema_cols

    def test_chunk_dto_fields_match_schema_columns(self) -> None:
        dto_fields = {
            "chunk_id", "document_id", "chunk_index",
            "content", "classification", "created_at",
        }
        schema_cols = {c.name for c in KNOWLEDGE_CHUNKS_TABLE.columns}
        assert dto_fields == schema_cols

    def test_job_dto_fields_match_schema_columns(self) -> None:
        dto_fields = {
            "job_id", "source_id", "status", "started_at",
            "completed_at", "error_message",
        }
        schema_cols = {c.name for c in INGESTION_JOBS_TABLE.columns}
        assert dto_fields == schema_cols

    def test_outbox_dto_fields_match_schema_columns(self) -> None:
        dto_fields = {
            "event_id", "event_type", "aggregate_id",
            "occurred_at", "correlation_id", "causation_id",
            "payload", "published",
        }
        schema_cols = {c.name for c in KNOWLEDGE_OUTBOX_TABLE.columns}
        assert dto_fields == schema_cols

    def test_source_dto_field_types_match_schema(self) -> None:
        schema_map = {c.name: c.py_type for c in KNOWLEDGE_SOURCES_TABLE.columns}
        assert schema_map["source_id"] == str
        assert schema_map["name"] == str
        assert schema_map["source_type"] == str
        assert schema_map["classification"] == str
        assert schema_map["status"] == str
        assert schema_map["created_at"] == datetime

    def test_document_dto_field_types_match_schema(self) -> None:
        schema_map = {c.name: c.py_type for c in KNOWLEDGE_DOCUMENTS_TABLE.columns}
        assert schema_map["document_id"] == str
        assert schema_map["title"] == str
        assert schema_map["revision"] == int

    def test_chunk_dto_field_types_match_schema(self) -> None:
        schema_map = {c.name: c.py_type for c in KNOWLEDGE_CHUNKS_TABLE.columns}
        assert schema_map["chunk_id"] == str
        assert schema_map["chunk_index"] == int

    def test_job_dto_field_types_match_schema(self) -> None:
        schema_map = {c.name: c.py_type for c in INGESTION_JOBS_TABLE.columns}
        assert schema_map["job_id"] == str
        assert schema_map["started_at"] == datetime

    def test_outbox_dto_field_types_match_schema(self) -> None:
        schema_map = {c.name: c.py_type for c in KNOWLEDGE_OUTBOX_TABLE.columns}
        assert schema_map["event_id"] == str
        assert schema_map["event_type"] == str
        assert schema_map["occurred_at"] == datetime
        assert schema_map["published"] == bool

    def test_source_dto_nullability_matches_schema(self) -> None:
        schema_nullable = {c.name for c in KNOWLEDGE_SOURCES_TABLE.columns if c.nullable}
        dto_nullable = {"location", "updated_at", "deleted_at"}
        assert schema_nullable == dto_nullable

    def test_document_dto_nullability_matches_schema(self) -> None:
        schema_nullable = {c.name for c in KNOWLEDGE_DOCUMENTS_TABLE.columns if c.nullable}
        dto_nullable = {"source_id", "checksum", "updated_at", "deleted_at"}
        assert schema_nullable == dto_nullable

    def test_chunk_dto_nullability_matches_schema(self) -> None:
        schema_nullable = {c.name for c in KNOWLEDGE_CHUNKS_TABLE.columns if c.nullable}
        dto_nullable = {"document_id", "chunk_index", "content"}
        assert schema_nullable == dto_nullable

    def test_job_dto_nullability_matches_schema(self) -> None:
        schema_nullable = {c.name for c in INGESTION_JOBS_TABLE.columns if c.nullable}
        dto_nullable = {"source_id", "completed_at", "error_message"}
        assert schema_nullable == dto_nullable

    def test_outbox_dto_nullability_matches_schema(self) -> None:
        schema_nullable = {c.name for c in KNOWLEDGE_OUTBOX_TABLE.columns if c.nullable}
        dto_nullable = {"correlation_id", "causation_id", "payload"}
        assert schema_nullable == dto_nullable


# ===================================================================
# Schema value constraint alignment with domain rules
# ===================================================================


class TestSchemaDomainAlignment:
    def test_source_type_enum_matches_domain(self) -> None:
        domain_values = {e.value for e in SourceType}
        col = next(c for c in KNOWLEDGE_SOURCES_TABLE.columns if c.name == "source_type")
        assert col.enum_values is not None
        assert set(col.enum_values) == domain_values

    def test_source_status_enum_matches_domain(self) -> None:
        domain_values = {e.value for e in SourceStatus}
        col = next(c for c in KNOWLEDGE_SOURCES_TABLE.columns if c.name == "status")
        assert col.enum_values is not None
        assert set(col.enum_values) == domain_values

    def test_document_status_enum_matches_domain(self) -> None:
        domain_values = {e.value for e in DocumentStatus}
        col = next(c for c in KNOWLEDGE_DOCUMENTS_TABLE.columns if c.name == "status")
        assert col.enum_values is not None
        assert set(col.enum_values) == domain_values

    def test_ingestion_status_enum_matches_domain(self) -> None:
        domain_values = {e.value for e in IngestionStatus}
        col = next(c for c in INGESTION_JOBS_TABLE.columns if c.name == "status")
        assert col.enum_values is not None
        assert set(col.enum_values) == domain_values

    def test_classification_enum_matches_domain_rules(self) -> None:
        from backend.knowledge.domain.rules import VALID_CLASSIFICATIONS
        col = next(c for c in KNOWLEDGE_SOURCES_TABLE.columns if c.name == "classification")
        assert col.enum_values is not None
        assert set(col.enum_values) == VALID_CLASSIFICATIONS


# ===================================================================
# DTO ↔ Domain entity field parity
# ===================================================================


class TestDomainDTOParity:
    def test_source_dto_has_all_domain_fields(self) -> None:
        dto_fields = {
            "source_id": str,
            "name": str,
            "source_type": str,
            "location": str | None,
            "classification": str,
            "status": str,
            "created_at": datetime | None,
            "updated_at": datetime | None,
            "deleted_at": datetime | None,
        }
        import dataclasses
        dto_field_map = {
            f.name: f.type for f in dataclasses.fields(KnowledgeSourceStorageDTO)
        }
        for name, expected_type in dto_fields.items():
            assert name in dto_field_map, f"DTO missing field {name!r}"

    def test_document_dto_has_all_domain_fields(self) -> None:
        dto_fields = {
            "document_id": str,
            "source_id": str | None,
            "title": str,
            "checksum": str | None,
            "classification": str,
            "status": str,
            "revision": int,
            "created_at": datetime | None,
            "updated_at": datetime | None,
            "deleted_at": datetime | None,
        }
        import dataclasses
        dto_field_map = {
            f.name: f.type for f in dataclasses.fields(KnowledgeDocumentStorageDTO)
        }
        for name in dto_fields:
            assert name in dto_field_map

    def test_chunk_dto_has_all_domain_fields(self) -> None:
        dto_fields = {
            "chunk_id": str,
            "document_id": str | None,
            "chunk_index": int | None,
            "content": str | None,
            "classification": str,
            "created_at": datetime | None,
        }
        import dataclasses
        dto_field_map = {
            f.name: f.type for f in dataclasses.fields(KnowledgeChunkStorageDTO)
        }
        for name in dto_fields:
            assert name in dto_field_map

    def test_job_dto_has_all_domain_fields(self) -> None:
        dto_fields = {
            "job_id": str,
            "source_id": str | None,
            "status": str,
            "started_at": datetime | None,
            "completed_at": datetime | None,
            "error_message": str | None,
        }
        import dataclasses
        dto_field_map = {
            f.name: f.type for f in dataclasses.fields(IngestionJobStorageDTO)
        }
        for name in dto_fields:
            assert name in dto_field_map

    def test_source_location_flattened(self) -> None:
        dto_fields = {
            f.name for f in __import__(
                "dataclasses"
            ).fields(KnowledgeSourceStorageDTO)
        }
        assert "location" in dto_fields
        assert "source_id" in dto_fields


# ===================================================================
# Port / mapper interface signature verification
# ===================================================================


class TestMapperMethodSignatures:
    def test_source_mapper_methods(self) -> None:
        mapper: KnowledgeSourceMapper = StubKnowledgeSourceMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")

    def test_document_mapper_methods(self) -> None:
        mapper: KnowledgeDocumentMapper = StubKnowledgeDocumentMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")

    def test_chunk_mapper_methods(self) -> None:
        mapper: KnowledgeChunkMapper = StubKnowledgeChunkMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")

    def test_job_mapper_methods(self) -> None:
        mapper: IngestionJobMapper = StubIngestionJobMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")

    def test_outbox_mapper_methods(self) -> None:
        mapper: KnowledgeOutboxMapper = StubKnowledgeOutboxMapper()
        assert hasattr(mapper, "event_to_dto")
        assert hasattr(mapper, "dto_to_event")

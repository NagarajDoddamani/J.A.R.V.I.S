from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.knowledge.adapters.outbound.clock import SystemClockAdapter
from backend.knowledge.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.knowledge.adapters.outbound.mapper import (
    IngestionJobMapperImpl,
    KnowledgeChunkMapperImpl,
    KnowledgeDocumentMapperImpl,
    KnowledgeOutboxMapperImpl,
    KnowledgeSourceMapperImpl,
)
from backend.knowledge.application.persistence.mapper import (
    IngestionJobMapper,
    KnowledgeChunkMapper,
    KnowledgeDocumentMapper,
    KnowledgeOutboxMapper,
    KnowledgeSourceMapper,
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

NOW = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)


# ===================================================================
# Clock adapter tests
# ===================================================================


class TestSystemClockAdapter:
    def test_now_returns_utc(self) -> None:
        clock = SystemClockAdapter()
        result = clock.now()
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result).total_seconds() == 0.0

    def test_now_returns_datetime(self) -> None:
        clock = SystemClockAdapter()
        assert isinstance(clock.now(), datetime)


# ===================================================================
# ID generator adapter tests
# ===================================================================


class TestUuidGeneratorAdapter:
    def test_generate_source_id(self) -> None:
        gen = UuidGeneratorAdapter()
        sid = gen.generate_source_id()
        assert isinstance(sid, KnowledgeSourceId)

    def test_generate_document_id(self) -> None:
        gen = UuidGeneratorAdapter()
        did = gen.generate_document_id()
        assert isinstance(did, DocumentId)

    def test_generate_chunk_id(self) -> None:
        gen = UuidGeneratorAdapter()
        cid = gen.generate_chunk_id()
        assert isinstance(cid, ChunkId)

    def test_generate_job_id(self) -> None:
        gen = UuidGeneratorAdapter()
        jid = gen.generate_job_id()
        assert isinstance(jid, IngestionJobId)

    def test_unique_ids(self) -> None:
        gen = UuidGeneratorAdapter()
        source_ids = {gen.generate_source_id() for _ in range(50)}
        doc_ids = {gen.generate_document_id() for _ in range(50)}
        assert len(source_ids) == 50
        assert len(doc_ids) == 50


# ===================================================================
# KnowledgeSourceMapperImpl tests
# ===================================================================


class TestKnowledgeSourceMapperImpl:
    @pytest.fixture
    def mapper(self) -> KnowledgeSourceMapperImpl:
        return KnowledgeSourceMapperImpl()

    def test_protocol_conformance(self) -> None:
        mapper: KnowledgeSourceMapper = KnowledgeSourceMapperImpl()
        assert isinstance(mapper, KnowledgeSourceMapperImpl)

    def test_domain_to_dto(self, mapper: KnowledgeSourceMapperImpl) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Test Source",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/path"),
            classification="public",
            status=SourceStatus.ACTIVE,
            created_at=NOW,
        )
        dto = mapper.domain_to_dto(source)
        assert dto.source_id == str(source.source_id)
        assert dto.name == "Test Source"
        assert dto.source_type == "file"
        assert dto.location == "/path"
        assert dto.classification == "public"
        assert dto.status == "active"

    def test_dto_to_domain(self, mapper: KnowledgeSourceMapperImpl) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="DTO Source",
            source_type=SourceType.URL,
            location=SourceLocation(value="https://ex.com"),
            classification="internal",
            status=SourceStatus.REGISTERED,
            created_at=NOW,
        )
        dto = mapper.domain_to_dto(source)
        result = mapper.dto_to_domain(dto)
        assert str(result.source_id) == str(source.source_id)
        assert result.name == "DTO Source"
        assert result.source_type == SourceType.URL
        assert str(result.location) == "https://ex.com"

    def test_roundtrip(self, mapper: KnowledgeSourceMapperImpl) -> None:
        original = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Roundtrip",
            source_type=SourceType.DIRECTORY,
            location=SourceLocation(value="/dir"),
            classification="sensitive",
            status=SourceStatus.DISABLED,
            created_at=NOW,
            updated_at=NOW,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.name == original.name
        assert reconstructed.source_type == original.source_type
        assert reconstructed.status == original.status

    def test_null_fields(self, mapper: KnowledgeSourceMapperImpl) -> None:
        original = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Null Source",
            source_type=SourceType.MANUAL,
            location=None,
            classification="public",
            status=SourceStatus.REGISTERED,
            created_at=NOW,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.location is None
        assert reconstructed.updated_at is None

    def test_deleted_state(self, mapper: KnowledgeSourceMapperImpl) -> None:
        original = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Deleted",
            source_type=SourceType.FILE,
            classification="public",
            status=SourceStatus.DELETED,
            created_at=NOW,
            deleted_at=NOW,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.status == SourceStatus.DELETED
        assert reconstructed.deleted_at == NOW


# ===================================================================
# KnowledgeDocumentMapperImpl tests
# ===================================================================


class TestKnowledgeDocumentMapperImpl:
    @pytest.fixture
    def mapper(self) -> KnowledgeDocumentMapperImpl:
        return KnowledgeDocumentMapperImpl()

    def test_protocol_conformance(self) -> None:
        mapper: KnowledgeDocumentMapper = KnowledgeDocumentMapperImpl()
        assert isinstance(mapper, KnowledgeDocumentMapperImpl)

    def test_domain_to_dto(self, mapper: KnowledgeDocumentMapperImpl) -> None:
        doc = KnowledgeDocument(
            document_id=DocumentId(),
            source_id=KnowledgeSourceId(),
            title="Doc",
            checksum=DocumentChecksum(value="abc"),
            classification="public",
            status=DocumentStatus.INGESTED,
            revision=2,
            created_at=NOW,
        )
        dto = mapper.domain_to_dto(doc)
        assert dto.title == "Doc"
        assert dto.checksum == "abc"
        assert dto.status == "ingested"
        assert dto.revision == 2

    def test_dto_to_domain(self, mapper: KnowledgeDocumentMapperImpl) -> None:
        doc = KnowledgeDocument(
            document_id=DocumentId(),
            source_id=KnowledgeSourceId(),
            title="Back",
            checksum=DocumentChecksum(value="def"),
            classification="internal",
            status=DocumentStatus.INDEXED,
            revision=3,
            created_at=NOW,
        )
        dto = mapper.domain_to_dto(doc)
        result = mapper.dto_to_domain(dto)
        assert result.title == "Back"
        assert str(result.checksum) == "def"
        assert result.status == DocumentStatus.INDEXED

    def test_roundtrip(self, mapper: KnowledgeDocumentMapperImpl) -> None:
        original = KnowledgeDocument(
            document_id=DocumentId(),
            source_id=KnowledgeSourceId(),
            title="RT",
            checksum=DocumentChecksum(value="xyz"),
            classification="sensitive",
            status=DocumentStatus.DELETED,
            revision=5,
            created_at=NOW,
            deleted_at=NOW,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.title == original.title
        assert reconstructed.status == original.status
        assert reconstructed.revision == original.revision

    def test_null_fields(self, mapper: KnowledgeDocumentMapperImpl) -> None:
        original = KnowledgeDocument(
            document_id=DocumentId(),
            title="No Source",
            classification="public",
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.source_id is None
        assert reconstructed.checksum is None


# ===================================================================
# KnowledgeChunkMapperImpl tests
# ===================================================================


class TestKnowledgeChunkMapperImpl:
    @pytest.fixture
    def mapper(self) -> KnowledgeChunkMapperImpl:
        return KnowledgeChunkMapperImpl()

    def test_protocol_conformance(self) -> None:
        mapper: KnowledgeChunkMapper = KnowledgeChunkMapperImpl()
        assert isinstance(mapper, KnowledgeChunkMapperImpl)

    def test_domain_to_dto(self, mapper: KnowledgeChunkMapperImpl) -> None:
        chunk = KnowledgeChunk(
            chunk_id=ChunkId(),
            document_id=DocumentId(),
            chunk_index=ChunkIndex(value=0),
            content=ChunkContent(value="Content"),
            classification="public",
            created_at=NOW,
        )
        dto = mapper.domain_to_dto(chunk)
        assert dto.chunk_index == 0
        assert dto.content == "Content"

    def test_dto_to_domain(self, mapper: KnowledgeChunkMapperImpl) -> None:
        chunk = KnowledgeChunk(
            chunk_id=ChunkId(),
            document_id=DocumentId(),
            chunk_index=ChunkIndex(value=1),
            content=ChunkContent(value="Back"),
            classification="internal",
            created_at=NOW,
        )
        dto = mapper.domain_to_dto(chunk)
        result = mapper.dto_to_domain(dto)
        assert int(result.chunk_index) == 1
        assert result.content.value == "Back"

    def test_roundtrip(self, mapper: KnowledgeChunkMapperImpl) -> None:
        original = KnowledgeChunk(
            chunk_id=ChunkId(),
            document_id=DocumentId(),
            chunk_index=ChunkIndex(value=2),
            content=ChunkContent(value="Roundtrip"),
            classification="sensitive",
            created_at=NOW,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert int(reconstructed.chunk_index) == 2
        assert reconstructed.content.value == "Roundtrip"

    def test_null_fields(self, mapper: KnowledgeChunkMapperImpl) -> None:
        original = KnowledgeChunk(
            chunk_id=ChunkId(),
            classification="public",
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.document_id is None
        assert reconstructed.chunk_index is None
        assert reconstructed.content is None


# ===================================================================
# IngestionJobMapperImpl tests
# ===================================================================


class TestIngestionJobMapperImpl:
    @pytest.fixture
    def mapper(self) -> IngestionJobMapperImpl:
        return IngestionJobMapperImpl()

    def test_protocol_conformance(self) -> None:
        mapper: IngestionJobMapper = IngestionJobMapperImpl()
        assert isinstance(mapper, IngestionJobMapperImpl)

    def test_domain_to_dto(self, mapper: IngestionJobMapperImpl) -> None:
        job = IngestionJob(
            job_id=IngestionJobId(),
            source_id=KnowledgeSourceId(),
            status=IngestionStatus.RUNNING,
            started_at=NOW,
        )
        dto = mapper.domain_to_dto(job)
        assert dto.status == "running"
        assert dto.started_at == NOW

    def test_dto_to_domain(self, mapper: IngestionJobMapperImpl) -> None:
        job = IngestionJob(
            job_id=IngestionJobId(),
            source_id=KnowledgeSourceId(),
            status=IngestionStatus.FAILED,
            started_at=NOW,
            completed_at=NOW,
            error_message="Error",
        )
        dto = mapper.domain_to_dto(job)
        result = mapper.dto_to_domain(dto)
        assert result.status == IngestionStatus.FAILED
        assert result.error_message == "Error"

    def test_roundtrip(self, mapper: IngestionJobMapperImpl) -> None:
        original = IngestionJob(
            job_id=IngestionJobId(),
            source_id=KnowledgeSourceId(),
            status=IngestionStatus.COMPLETED,
            started_at=NOW,
            completed_at=NOW,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.status == original.status
        assert reconstructed.completed_at == original.completed_at

    def test_null_fields(self, mapper: IngestionJobMapperImpl) -> None:
        original = IngestionJob(
            job_id=IngestionJobId(),
            status=IngestionStatus.RUNNING,
            started_at=NOW,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.source_id is None
        assert reconstructed.completed_at is None
        assert reconstructed.error_message is None


# ===================================================================
# KnowledgeOutboxMapperImpl tests
# ===================================================================


class TestKnowledgeOutboxMapperImpl:
    @pytest.fixture
    def mapper(self) -> KnowledgeOutboxMapperImpl:
        return KnowledgeOutboxMapperImpl()

    def test_protocol_conformance(self) -> None:
        mapper: KnowledgeOutboxMapper = KnowledgeOutboxMapperImpl()
        assert isinstance(mapper, KnowledgeOutboxMapperImpl)

    def test_source_registered_event(self, mapper: KnowledgeOutboxMapperImpl) -> None:
        event = KnowledgeSourceRegistered(
            source_id=KnowledgeSourceId(),
            name="Test",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/p"),
            classification="public",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "knowledge.source.registered"
        assert dto.aggregate_id == str(event.source_id)
        assert dto.payload is not None

    def test_source_deleted_event(self, mapper: KnowledgeOutboxMapperImpl) -> None:
        event = KnowledgeSourceDeleted(
            source_id=KnowledgeSourceId(),
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "knowledge.source.deleted"
        assert dto.payload is None

    def test_document_ingested_event(self, mapper: KnowledgeOutboxMapperImpl) -> None:
        event = DocumentIngested(
            document_id=DocumentId(),
            source_id=KnowledgeSourceId(),
            title="Doc",
            checksum=DocumentChecksum(value="abc"),
            classification="public",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "knowledge.document.ingested"
        assert dto.payload is not None

    def test_chunk_created_event(self, mapper: KnowledgeOutboxMapperImpl) -> None:
        event = ChunkCreated(
            chunk_id=ChunkId(),
            document_id=DocumentId(),
            chunk_index=ChunkIndex(value=0),
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "knowledge.chunk.created"
        assert dto.payload is not None

    def test_all_events_have_mapping(self, mapper: KnowledgeOutboxMapperImpl) -> None:
        events = [
            KnowledgeSourceRegistered(KnowledgeSourceId(), "S", SourceType.FILE,
                                      SourceLocation(value="/p"), "public", NOW),
            KnowledgeSourceDeleted(KnowledgeSourceId(), NOW),
            DocumentIngested(DocumentId(), KnowledgeSourceId(), "D",
                             DocumentChecksum(value="c"), "public", NOW),
            DocumentIndexed(DocumentId(), NOW),
            DocumentDeleted(DocumentId(), NOW),
            ChunkCreated(ChunkId(), DocumentId(), ChunkIndex(value=0), NOW),
            ReindexRequested(KnowledgeSourceId(), NOW),
            IngestionStarted(IngestionJobId(), KnowledgeSourceId(), NOW),
            IngestionCompleted(IngestionJobId(), NOW),
            IngestionFailed(IngestionJobId(), "e", NOW),
        ]
        for event in events:
            dto = mapper.event_to_dto(event)
            reconstructed = mapper.dto_to_event(dto)
            assert type(reconstructed) is type(event)

    def test_roundtrip_source_registered(self, mapper: KnowledgeOutboxMapperImpl) -> None:
        original = KnowledgeSourceRegistered(
            source_id=KnowledgeSourceId(),
            name="RT",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/rt"),
            classification="internal",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, KnowledgeSourceRegistered)
        assert str(reconstructed.source_id) == str(original.source_id)

    def test_roundtrip_ingestion_failed(self, mapper: KnowledgeOutboxMapperImpl) -> None:
        original = IngestionFailed(
            job_id=IngestionJobId(),
            error_message="Timeout",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, IngestionFailed)
        assert reconstructed.error_message == "Timeout"

    def test_dto_to_event_unknown_type(self, mapper: KnowledgeOutboxMapperImpl) -> None:
        from backend.knowledge.application.persistence.dto import (
            KnowledgeOutboxStorageDTO,
        )
        dto = KnowledgeOutboxStorageDTO(
            event_id="id-1",
            event_type="unknown.type",
            aggregate_id="id-1",
            occurred_at=NOW,
        )
        with pytest.raises(ValueError, match="unknown.type"):
            mapper.dto_to_event(dto)

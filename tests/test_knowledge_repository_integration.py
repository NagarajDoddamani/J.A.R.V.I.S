from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator
from uuid import UUID

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.knowledge.adapters.outbound.clock import SystemClockAdapter
from backend.knowledge.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.knowledge.adapters.outbound.mapper import (
    IngestionJobMapperImpl,
    KnowledgeChunkMapperImpl,
    KnowledgeDocumentMapperImpl,
    KnowledgeOutboxMapperImpl,
    KnowledgeSourceMapperImpl,
)
from backend.knowledge.adapters.outbound.models import Base
from backend.knowledge.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyIngestionJobRepository,
    SqlAlchemyKnowledgeChunkRepository,
    SqlAlchemyKnowledgeDocumentRepository,
    SqlAlchemyKnowledgeOutboxAdapter,
    SqlAlchemyKnowledgeSourceRepository,
)
from backend.knowledge.domain.model import (
    ChunkContent,
    ChunkId,
    ChunkIndex,
    DocumentChecksum,
    DocumentId,
    DocumentStatus,
    IngestionJob,
    IngestionJobId,
    IngestionStatus,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeSource,
    KnowledgeSourceId,
    SourceLocation,
    SourceStatus,
    SourceType,
)

NOW = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def engine() -> Iterator[Engine]:
    e = create_engine("sqlite://", echo=False)
    for t in Base.metadata.tables.values():
        t.schema = None
    Base.metadata.create_all(bind=e)
    yield e
    e.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    S = sessionmaker(bind=engine)
    s = S()
    yield s
    s.close()


@pytest.fixture
def source_mapper() -> KnowledgeSourceMapperImpl:
    return KnowledgeSourceMapperImpl()


@pytest.fixture
def document_mapper() -> KnowledgeDocumentMapperImpl:
    return KnowledgeDocumentMapperImpl()


@pytest.fixture
def chunk_mapper() -> KnowledgeChunkMapperImpl:
    return KnowledgeChunkMapperImpl()


@pytest.fixture
def job_mapper() -> IngestionJobMapperImpl:
    return IngestionJobMapperImpl()


@pytest.fixture
def outbox_mapper() -> KnowledgeOutboxMapperImpl:
    return KnowledgeOutboxMapperImpl()


@pytest.fixture
def clock() -> SystemClockAdapter:
    return SystemClockAdapter()


@pytest.fixture
def id_gen() -> UuidGeneratorAdapter:
    return UuidGeneratorAdapter()


@pytest.fixture
def source_repo(
    session: Session, source_mapper: KnowledgeSourceMapperImpl
) -> SqlAlchemyKnowledgeSourceRepository:
    return SqlAlchemyKnowledgeSourceRepository(session=session, mapper=source_mapper)


@pytest.fixture
def document_repo(
    session: Session, document_mapper: KnowledgeDocumentMapperImpl
) -> SqlAlchemyKnowledgeDocumentRepository:
    return SqlAlchemyKnowledgeDocumentRepository(
        session=session, mapper=document_mapper
    )


@pytest.fixture
def chunk_repo(
    session: Session, chunk_mapper: KnowledgeChunkMapperImpl
) -> SqlAlchemyKnowledgeChunkRepository:
    return SqlAlchemyKnowledgeChunkRepository(session=session, mapper=chunk_mapper)


@pytest.fixture
def job_repo(
    session: Session, job_mapper: IngestionJobMapperImpl
) -> SqlAlchemyIngestionJobRepository:
    return SqlAlchemyIngestionJobRepository(session=session, mapper=job_mapper)


@pytest.fixture
def outbox_adapter(
    session: Session, outbox_mapper: KnowledgeOutboxMapperImpl
) -> SqlAlchemyKnowledgeOutboxAdapter:
    return SqlAlchemyKnowledgeOutboxAdapter(session=session, mapper=outbox_mapper)


@pytest.fixture
def a_source(clock: SystemClockAdapter) -> KnowledgeSource:
    return KnowledgeSource(
        source_id=KnowledgeSourceId(),
        name="Integration Source",
        source_type=SourceType.FILE,
        location=SourceLocation(value="/data"),
        classification="public",
        status=SourceStatus.ACTIVE,
        created_at=clock.now(),
    )


@pytest.fixture
def a_document(
    a_source: KnowledgeSource, clock: SystemClockAdapter
) -> KnowledgeDocument:
    return KnowledgeDocument(
        document_id=DocumentId(),
        source_id=a_source.source_id,
        title="Integration Doc",
        checksum=DocumentChecksum(value="abc123"),
        classification="public",
        status=DocumentStatus.PENDING,
        revision=1,
        created_at=clock.now(),
    )


@pytest.fixture
def a_job(a_source: KnowledgeSource, clock: SystemClockAdapter) -> IngestionJob:
    return IngestionJob(
        job_id=IngestionJobId(),
        source_id=a_source.source_id,
        status=IngestionStatus.RUNNING,
        started_at=clock.now(),
    )


# ===================================================================
# KnowledgeSource repository integration tests
# ===================================================================


class TestKnowledgeSourceRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        a_source: KnowledgeSource,
    ) -> None:
        source_repo.save(a_source)
        found = source_repo.find_by_id(a_source.source_id)
        assert found is not None
        assert str(found.source_id) == str(a_source.source_id)

    def test_save_updates_existing(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        a_source: KnowledgeSource,
    ) -> None:
        source_repo.save(a_source)
        found = source_repo.find_by_id(a_source.source_id)
        assert found is not None
        assert found.name == "Integration Source"

    def test_find_by_id_missing(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
    ) -> None:
        found = source_repo.find_by_id(KnowledgeSourceId())
        assert found is None

    def test_find_by_status(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        a_source: KnowledgeSource,
    ) -> None:
        source_repo.save(a_source)
        results = source_repo.find_by_status(SourceStatus.ACTIVE)
        assert len(results) >= 1
        assert results[0].source_id == a_source.source_id

    def test_find_by_status_empty(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
    ) -> None:
        results = source_repo.find_by_status(SourceStatus.DELETED)
        assert len(results) == 0

    def test_find_by_type(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        a_source: KnowledgeSource,
    ) -> None:
        source_repo.save(a_source)
        results = source_repo.find_by_type(SourceType.FILE)
        assert len(results) >= 1

    def test_find_by_type_empty(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
    ) -> None:
        results = source_repo.find_by_type(SourceType.URL)
        assert len(results) == 0

    def test_count(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
    ) -> None:
        assert source_repo.count() == 0
        source_repo.save(KnowledgeSource(
            source_id=KnowledgeSourceId(), name="S1", source_type=SourceType.FILE,
            classification="public", status=SourceStatus.REGISTERED, created_at=NOW,
        ))
        assert source_repo.count() == 1

    def test_soft_delete_preserved(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        a_source: KnowledgeSource,
    ) -> None:
        source_repo.save(a_source)
        a_source.delete()
        source_repo.save(a_source)
        found = source_repo.find_by_id(a_source.source_id)
        assert found is not None
        assert found.status == SourceStatus.DELETED
        assert found.deleted_at is not None

    def test_upsert_updates_fields(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        a_source: KnowledgeSource,
    ) -> None:
        source_repo.save(a_source)
        a_source._name = "Updated Name"
        source_repo.save(a_source)
        found = source_repo.find_by_id(a_source.source_id)
        assert found is not None
        assert found.name == "Updated Name"


# ===================================================================
# KnowledgeDocument repository integration tests
# ===================================================================


class TestKnowledgeDocumentRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
        a_document: KnowledgeDocument,
    ) -> None:
        document_repo.save(a_document)
        found = document_repo.find_by_id(a_document.document_id)
        assert found is not None
        assert str(found.document_id) == str(a_document.document_id)

    def test_find_by_id_missing(
        self,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
    ) -> None:
        found = document_repo.find_by_id(DocumentId())
        assert found is None

    def test_find_by_source_id(
        self,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
        a_document: KnowledgeDocument,
    ) -> None:
        document_repo.save(a_document)
        results = document_repo.find_by_source_id(a_document.source_id)
        assert len(results) == 1

    def test_find_by_checksum(
        self,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
        a_document: KnowledgeDocument,
    ) -> None:
        document_repo.save(a_document)
        results = document_repo.find_by_checksum(
            DocumentChecksum(value="abc123")
        )
        assert len(results) == 1

    def test_find_by_checksum_missing(
        self,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
    ) -> None:
        results = document_repo.find_by_checksum(
            DocumentChecksum(value="nonexistent")
        )
        assert len(results) == 0

    def test_find_deleted(
        self,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
        a_document: KnowledgeDocument,
    ) -> None:
        document_repo.save(a_document)
        a_document.delete()
        document_repo.save(a_document)
        deleted = document_repo.find_deleted()
        assert len(deleted) == 1
        assert deleted[0].is_deleted

    def test_find_deleted_empty(
        self,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
    ) -> None:
        assert len(document_repo.find_deleted()) == 0

    def test_count(
        self,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
        a_document: KnowledgeDocument,
    ) -> None:
        assert document_repo.count() == 0
        document_repo.save(a_document)
        assert document_repo.count() == 1

    def test_revision_preserved(
        self,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
        a_document: KnowledgeDocument,
    ) -> None:
        document_repo.save(a_document)
        found = document_repo.find_by_id(a_document.document_id)
        assert found is not None
        assert found.revision == 1

    def test_upsert_updates(
        self,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
        a_document: KnowledgeDocument,
    ) -> None:
        document_repo.save(a_document)
        a_document._title = "Updated Title"
        document_repo.save(a_document)
        found = document_repo.find_by_id(a_document.document_id)
        assert found is not None
        assert found.title == "Updated Title"


# ===================================================================
# KnowledgeChunk repository integration tests
# ===================================================================


class TestKnowledgeChunkRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        chunk_repo: SqlAlchemyKnowledgeChunkRepository,
    ) -> None:
        chunk = KnowledgeChunk(
            chunk_id=ChunkId(),
            document_id=DocumentId(),
            chunk_index=ChunkIndex(value=0),
            content=ChunkContent(value="Chunk"),
            classification="public",
            created_at=NOW,
        )
        chunk_repo.save(chunk)
        found = chunk_repo.find_by_id(chunk.chunk_id)
        assert found is not None
        assert str(found.chunk_id) == str(chunk.chunk_id)

    def test_find_by_id_missing(
        self,
        chunk_repo: SqlAlchemyKnowledgeChunkRepository,
    ) -> None:
        found = chunk_repo.find_by_id(ChunkId())
        assert found is None

    def test_find_by_document_id_ordered(
        self,
        chunk_repo: SqlAlchemyKnowledgeChunkRepository,
    ) -> None:
        doc_id = DocumentId()
        indices = [0, 2, 1]
        for i in indices:
            chunk_repo.save(KnowledgeChunk(
                chunk_id=ChunkId(),
                document_id=doc_id,
                chunk_index=ChunkIndex(value=i),
                content=ChunkContent(value=f"Chunk {i}"),
                classification="public",
                created_at=NOW,
            ))
        results = chunk_repo.find_by_document_id(doc_id)
        assert len(results) == 3
        indices_result = [int(c.chunk_index) for c in results]
        assert indices_result == [0, 1, 2]

    def test_find_by_index_range(
        self,
        chunk_repo: SqlAlchemyKnowledgeChunkRepository,
    ) -> None:
        doc_id = DocumentId()
        for i in range(5):
            chunk_repo.save(KnowledgeChunk(
                chunk_id=ChunkId(),
                document_id=doc_id,
                chunk_index=ChunkIndex(value=i),
                content=ChunkContent(value=f"C{i}"),
                classification="public",
                created_at=NOW,
            ))
        results = chunk_repo.find_by_index_range(doc_id, 1, 3)
        assert len(results) == 3
        indices_result = [int(c.chunk_index) for c in results]
        assert indices_result == [1, 2, 3]

    def test_count(
        self,
        chunk_repo: SqlAlchemyKnowledgeChunkRepository,
    ) -> None:
        assert chunk_repo.count() == 0
        chunk_repo.save(KnowledgeChunk(
            chunk_id=ChunkId(), classification="public", created_at=NOW,
        ))
        assert chunk_repo.count() == 1

    def test_find_by_document_id_empty(
        self,
        chunk_repo: SqlAlchemyKnowledgeChunkRepository,
    ) -> None:
        results = chunk_repo.find_by_document_id(DocumentId())
        assert len(results) == 0


# ===================================================================
# IngestionJob repository integration tests
# ===================================================================


class TestIngestionJobRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        job_repo: SqlAlchemyIngestionJobRepository,
        a_job: IngestionJob,
    ) -> None:
        job_repo.save(a_job)
        found = job_repo.find_by_id(a_job.job_id)
        assert found is not None
        assert str(found.job_id) == str(a_job.job_id)

    def test_find_by_id_missing(
        self,
        job_repo: SqlAlchemyIngestionJobRepository,
    ) -> None:
        found = job_repo.find_by_id(IngestionJobId())
        assert found is None

    def test_find_by_source_id(
        self,
        job_repo: SqlAlchemyIngestionJobRepository,
        a_job: IngestionJob,
    ) -> None:
        job_repo.save(a_job)
        results = job_repo.find_by_source_id(a_job.source_id)
        assert len(results) == 1

    def test_find_by_status(
        self,
        job_repo: SqlAlchemyIngestionJobRepository,
        a_job: IngestionJob,
    ) -> None:
        job_repo.save(a_job)
        results = job_repo.find_by_status(IngestionStatus.RUNNING)
        assert len(results) == 1

    def test_find_by_status_empty(
        self,
        job_repo: SqlAlchemyIngestionJobRepository,
    ) -> None:
        results = job_repo.find_by_status(IngestionStatus.COMPLETED)
        assert len(results) == 0

    def test_count(
        self,
        job_repo: SqlAlchemyIngestionJobRepository,
        a_job: IngestionJob,
    ) -> None:
        assert job_repo.count() == 0
        job_repo.save(a_job)
        assert job_repo.count() == 1

    def test_lifecycle_transition(
        self,
        job_repo: SqlAlchemyIngestionJobRepository,
        a_job: IngestionJob,
    ) -> None:
        job_repo.save(a_job)
        a_job.complete()
        job_repo.save(a_job)
        found = job_repo.find_by_id(a_job.job_id)
        assert found is not None
        assert found.status == IngestionStatus.COMPLETED
        assert found.completed_at is not None


# ===================================================================
# Outbox adapter integration tests
# ===================================================================


class TestKnowledgeOutboxAdapterIntegration:
    def test_append_and_fetch(
        self,
        outbox_adapter: SqlAlchemyKnowledgeOutboxAdapter,
    ) -> None:
        from backend.knowledge.domain.model import KnowledgeSourceRegistered, SourceType, SourceLocation, KnowledgeSourceId
        event = KnowledgeSourceRegistered(
            source_id=KnowledgeSourceId(),
            name="Test",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/p"),
            classification="public",
            occurred_at=NOW,
        )
        outbox_adapter.append(event)
        events = outbox_adapter.fetch_unpublished()
        assert len(events) == 1

    def test_fifo_ordering(
        self,
        outbox_adapter: SqlAlchemyKnowledgeOutboxAdapter,
    ) -> None:
        from backend.knowledge.domain.model import KnowledgeSourceRegistered, SourceType, SourceLocation, KnowledgeSourceId
        e1 = KnowledgeSourceRegistered(KnowledgeSourceId(), "A", SourceType.FILE,
                                       SourceLocation(value="/a"), "public", NOW)
        e2 = KnowledgeSourceRegistered(KnowledgeSourceId(), "B", SourceType.FILE,
                                       SourceLocation(value="/b"), "public", NOW)
        outbox_adapter.append(e1)
        outbox_adapter.append(e2)
        events = outbox_adapter.fetch_unpublished()
        assert len(events) == 2

    def test_limit_enforcement(
        self,
        outbox_adapter: SqlAlchemyKnowledgeOutboxAdapter,
    ) -> None:
        from backend.knowledge.domain.model import KnowledgeSourceRegistered, SourceType, SourceLocation, KnowledgeSourceId
        for i in range(5):
            outbox_adapter.append(
                KnowledgeSourceRegistered(KnowledgeSourceId(), str(i), SourceType.FILE,
                                          SourceLocation(value="/p"), "public", NOW)
            )
        events = outbox_adapter.fetch_unpublished(limit=3)
        assert len(events) == 3

    def test_mark_published(
        self,
        outbox_adapter: SqlAlchemyKnowledgeOutboxAdapter,
    ) -> None:
        from backend.knowledge.domain.model import KnowledgeSourceRegistered, SourceType, SourceLocation, KnowledgeSourceId
        event = KnowledgeSourceRegistered(
            source_id=KnowledgeSourceId(),
            name="Pub",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/p"),
            classification="public",
            occurred_at=NOW,
        )
        outbox_adapter.append(event)
        fetched = outbox_adapter.fetch_unpublished()
        outbox_adapter.mark_published(str(fetched[0].event_id))
        remaining = outbox_adapter.fetch_unpublished()
        assert len(remaining) == 0

    def test_mark_published_by_aggregate_id(
        self,
        outbox_adapter: SqlAlchemyKnowledgeOutboxAdapter,
    ) -> None:
        from backend.knowledge.domain.model import KnowledgeSourceRegistered, SourceType, SourceLocation, KnowledgeSourceId
        sid = str(KnowledgeSourceId())
        event = KnowledgeSourceRegistered(
            source_id=KnowledgeSourceId(value=UUID(sid)),
            name="Agg",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/p"),
            classification="public",
            occurred_at=NOW,
        )
        outbox_adapter.append(event)
        fetched = outbox_adapter.fetch_unpublished()
        outbox_adapter.mark_published(str(fetched[0].event_id))
        remaining = outbox_adapter.fetch_unpublished()
        assert len(remaining) == 0

    def test_mark_published_idempotent(
        self,
        outbox_adapter: SqlAlchemyKnowledgeOutboxAdapter,
    ) -> None:
        from backend.knowledge.domain.model import KnowledgeSourceRegistered, SourceType, SourceLocation, KnowledgeSourceId
        sid = str(KnowledgeSourceId())
        event = KnowledgeSourceRegistered(
            source_id=KnowledgeSourceId(value=UUID(sid)),
            name="Idem",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/p"),
            classification="public",
            occurred_at=NOW,
        )
        outbox_adapter.append(event)
        fetched = outbox_adapter.fetch_unpublished()
        outbox_adapter.mark_published(str(fetched[0].event_id))
        outbox_adapter.mark_published(str(fetched[0].event_id))
        remaining = outbox_adapter.fetch_unpublished()
        assert len(remaining) == 0


# ===================================================================
# Full roundtrip integration tests
# ===================================================================


class TestFullRoundtrip:
    def test_domain_to_dto_to_orm_to_db_to_dto_to_domain_source(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        a_source: KnowledgeSource,
    ) -> None:
        source_repo.save(a_source)
        found = source_repo.find_by_id(a_source.source_id)
        assert found is not None
        assert str(found.source_id) == str(a_source.source_id)
        assert found.name == a_source.name
        assert found.source_type == a_source.source_type
        assert str(found.location) == str(a_source.location)
        assert found.classification == a_source.classification
        assert found.status == a_source.status

    def test_domain_to_dto_to_orm_to_db_to_dto_to_domain_document(
        self,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
        a_document: KnowledgeDocument,
    ) -> None:
        document_repo.save(a_document)
        found = document_repo.find_by_id(a_document.document_id)
        assert found is not None
        assert str(found.document_id) == str(a_document.document_id)
        assert found.title == a_document.title
        assert str(found.checksum) == str(a_document.checksum)

    def test_source_lifecycle_persistence(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        a_source: KnowledgeSource,
    ) -> None:
        a_source._status = SourceStatus.REGISTERED
        source_repo.save(a_source)
        a_source.activate()
        source_repo.save(a_source)
        found = source_repo.find_by_id(a_source.source_id)
        assert found is not None
        assert found.status == SourceStatus.ACTIVE

    def test_document_lifecycle_persistence(
        self,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
        a_document: KnowledgeDocument,
    ) -> None:
        document_repo.save(a_document)
        a_document.mark_indexed()
        document_repo.save(a_document)
        found = document_repo.find_by_id(a_document.document_id)
        assert found is not None
        assert found.status == DocumentStatus.INDEXED

    def test_chunk_persistence_and_ordering(
        self,
        chunk_repo: SqlAlchemyKnowledgeChunkRepository,
    ) -> None:
        doc_id = DocumentId()
        chunks = []
        for i in range(3):
            chunk = KnowledgeChunk(
                chunk_id=ChunkId(),
                document_id=doc_id,
                chunk_index=ChunkIndex(value=i),
                content=ChunkContent(value=f"C{i}"),
                classification="public",
                created_at=NOW,
            )
            chunk_repo.save(chunk)
            chunks.append(chunk)
        results = chunk_repo.find_by_document_id(doc_id)
        assert len(results) == 3
        for i, c in enumerate(results):
            assert int(c.chunk_index) == i

    def test_ingestion_lifecycle_persistence(
        self,
        job_repo: SqlAlchemyIngestionJobRepository,
        a_job: IngestionJob,
    ) -> None:
        job_repo.save(a_job)
        a_job.complete()
        job_repo.save(a_job)
        found = job_repo.find_by_id(a_job.job_id)
        assert found is not None
        assert found.status == IngestionStatus.COMPLETED
        assert found.completed_at is not None

    def test_outbox_event_persistence(
        self,
        outbox_adapter: SqlAlchemyKnowledgeOutboxAdapter,
    ) -> None:
        from backend.knowledge.domain.model import (
            KnowledgeSourceRegistered,
            SourceType,
            SourceLocation,
            KnowledgeSourceId,
        )
        event = KnowledgeSourceRegistered(
            source_id=KnowledgeSourceId(),
            name="Persist",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/p"),
            classification="public",
            occurred_at=NOW,
        )
        outbox_adapter.append(event)
        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], KnowledgeSourceRegistered)
        assert unpublished[0].name == "Persist"

    def test_cross_repo_source_to_document(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
        a_source: KnowledgeSource,
        a_document: KnowledgeDocument,
    ) -> None:
        source_repo.save(a_source)
        document_repo.save(a_document)
        docs = document_repo.find_by_source_id(a_source.source_id)
        assert len(docs) == 1
        assert docs[0].document_id == a_document.document_id

    def test_cross_repo_source_to_job(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        job_repo: SqlAlchemyIngestionJobRepository,
        a_source: KnowledgeSource,
        a_job: IngestionJob,
    ) -> None:
        source_repo.save(a_source)
        job_repo.save(a_job)
        jobs = job_repo.find_by_source_id(a_source.source_id)
        assert len(jobs) == 1

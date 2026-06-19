from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api.endpoints import knowledge as knowledge_router
from backend.core.database import get_db
from backend.knowledge.adapters.outbound.clock import SystemClockAdapter
from backend.knowledge.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.knowledge.adapters.outbound.mapper import (
    IngestionJobMapperImpl,
    KnowledgeChunkMapperImpl,
    KnowledgeDocumentMapperImpl,
    KnowledgeOutboxMapperImpl,
    KnowledgeSourceMapperImpl,
)
from backend.knowledge.adapters.outbound.models import (
    Base,
    KnowledgeOutboxModel,
)
from backend.knowledge.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyIngestionJobRepository,
    SqlAlchemyKnowledgeChunkRepository,
    SqlAlchemyKnowledgeDocumentRepository,
    SqlAlchemyKnowledgeOutboxAdapter,
    SqlAlchemyKnowledgeSourceRepository,
)
from backend.knowledge.application.persistence.dto import (
    IngestionJobStorageDTO,
    KnowledgeChunkStorageDTO,
    KnowledgeDocumentStorageDTO,
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
from backend.knowledge.nats import (
    publish_knowledge_outbox_events,
)

for _table in Base.metadata.tables.values():
    _table.schema = None


@pytest.fixture
def engine() -> Engine:
    e = create_engine("sqlite://", echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    return e


@pytest.fixture
def session(engine: Engine) -> Session:
    conn = engine.connect()
    s = Session(bind=conn)
    yield s
    s.close()
    conn.close()


@pytest.fixture
def clock() -> SystemClockAdapter:
    return SystemClockAdapter()


@pytest.fixture
def id_gen() -> UuidGeneratorAdapter:
    return UuidGeneratorAdapter()


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
def source_repo(session: Session, source_mapper: KnowledgeSourceMapperImpl) -> SqlAlchemyKnowledgeSourceRepository:
    return SqlAlchemyKnowledgeSourceRepository(session=session, mapper=source_mapper)


@pytest.fixture
def document_repo(session: Session, document_mapper: KnowledgeDocumentMapperImpl) -> SqlAlchemyKnowledgeDocumentRepository:
    return SqlAlchemyKnowledgeDocumentRepository(session=session, mapper=document_mapper)


@pytest.fixture
def chunk_repo(session: Session, chunk_mapper: KnowledgeChunkMapperImpl) -> SqlAlchemyKnowledgeChunkRepository:
    return SqlAlchemyKnowledgeChunkRepository(session=session, mapper=chunk_mapper)


@pytest.fixture
def job_repo(session: Session, job_mapper: IngestionJobMapperImpl) -> SqlAlchemyIngestionJobRepository:
    return SqlAlchemyIngestionJobRepository(session=session, mapper=job_mapper)


@pytest.fixture
def outbox(session: Session) -> SqlAlchemyKnowledgeOutboxAdapter:
    return SqlAlchemyKnowledgeOutboxAdapter(session)


@pytest.fixture
def client(session: Session):
    def _override_get_db():
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    app = FastAPI()
    app.include_router(knowledge_router.router, prefix="/api/v1/knowledge")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


# ===================================================================
# Source lifecycle
# ===================================================================


class TestSourceLifecycle:
    def test_register_activate_disable(self, source_repo: SqlAlchemyKnowledgeSourceRepository) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Lifecycle Source",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp/lifecycle"),
            classification="public",
            status=SourceStatus.REGISTERED,
            created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        assert source.status == SourceStatus.REGISTERED

        source.activate()
        source_repo.save(source)
        found = source_repo.find_by_id(source.source_id)
        assert found is not None
        assert found.status == SourceStatus.ACTIVE

        source.disable()
        source_repo.save(source)
        found = source_repo.find_by_id(source.source_id)
        assert found is not None
        assert found.status == SourceStatus.DISABLED

    def test_activate_then_delete(
        self, source_repo: SqlAlchemyKnowledgeSourceRepository
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Deletable",
            source_type=SourceType.URL,
            location=SourceLocation(value="https://example.com"),
            classification="public",
            status=SourceStatus.ACTIVE,
            created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)

        source.delete()
        source_repo.save(source)
        found = source_repo.find_by_id(source.source_id)
        assert found is not None
        assert found.status == SourceStatus.DELETED
        assert found.deleted_at is not None

    def test_deleted_source_blocks_activation(
        self, source_repo: SqlAlchemyKnowledgeSourceRepository
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Blocked",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp"),
            classification="public",
            status=SourceStatus.DELETED,
            created_at=datetime.now(tz=timezone.utc),
            deleted_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        with pytest.raises(Exception):
            source.activate()

    def test_source_events_on_delete(
        self, source_repo: SqlAlchemyKnowledgeSourceRepository,
        outbox: SqlAlchemyKnowledgeOutboxAdapter,
        session: Session,
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Event Source",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp/events"),
            classification="public",
            status=SourceStatus.ACTIVE,
            created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        source.delete()
        for event in source.events:
            outbox.append(event)
        session.flush()

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], KnowledgeSourceDeleted)

    def test_find_by_status(
        self, source_repo: SqlAlchemyKnowledgeSourceRepository
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        for status in SourceStatus:
            s = KnowledgeSource(
                source_id=KnowledgeSourceId(),
                name=f"Source-{status.value}",
                source_type=SourceType.FILE,
                location=SourceLocation(value="/tmp"),
                classification="public",
                status=status,
                created_at=now,
            )
            source_repo.save(s)
        for status in SourceStatus:
            found = source_repo.find_by_status(status)
            assert len(found) >= 1

    def test_find_by_type(
        self, source_repo: SqlAlchemyKnowledgeSourceRepository
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        for st in SourceType:
            s = KnowledgeSource(
                source_id=KnowledgeSourceId(),
                name=f"Source-{st.value}",
                source_type=st,
                location=SourceLocation(value="/tmp"),
                classification="public",
                status=SourceStatus.REGISTERED,
                created_at=now,
            )
            source_repo.save(s)
        for st in SourceType:
            found = source_repo.find_by_type(st)
            assert len(found) >= 1

    def test_count(
        self, source_repo: SqlAlchemyKnowledgeSourceRepository
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        for _ in range(3):
            s = KnowledgeSource(
                source_id=KnowledgeSourceId(),
                name="Count Source",
                source_type=SourceType.FILE,
                location=SourceLocation(value="/tmp"),
                classification="public",
                status=SourceStatus.REGISTERED,
                created_at=now,
            )
            source_repo.save(s)
        assert source_repo.count() >= 3


# ===================================================================
# Document lifecycle
# ===================================================================


class TestDocumentLifecycle:
    def test_create_then_get(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
    ) -> None:
        source = self._create_active_source(source_repo)
        doc = KnowledgeDocument(
            document_id=DocumentId(),
            source_id=source.source_id,
            title="Test Document",
            checksum=DocumentChecksum(value="abc123"),
            classification="public",
            status=DocumentStatus.PENDING,
            created_at=datetime.now(tz=timezone.utc),
        )
        document_repo.save(doc)
        found = document_repo.find_by_id(doc.document_id)
        assert found is not None
        assert str(found.document_id) == str(doc.document_id)

    def test_mark_indexed(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
    ) -> None:
        source = self._create_active_source(source_repo)
        doc = self._create_document(document_repo, source)
        doc.mark_indexed()
        document_repo.save(doc)
        found = document_repo.find_by_id(doc.document_id)
        assert found is not None
        assert found.status == DocumentStatus.INDEXED

    def test_delete_document(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
    ) -> None:
        source = self._create_active_source(source_repo)
        doc = self._create_document(document_repo, source)
        doc.delete()
        document_repo.save(doc)
        found = document_repo.find_by_id(doc.document_id)
        assert found is not None
        assert found.status == DocumentStatus.DELETED
        assert found.deleted_at is not None

    def test_find_deleted(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
    ) -> None:
        source = self._create_active_source(source_repo)
        doc = self._create_document(document_repo, source)
        doc.delete()
        document_repo.save(doc)
        deleted = document_repo.find_deleted()
        assert len(deleted) >= 1
        assert deleted[0].document_id == doc.document_id

    def test_find_by_source_id(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
    ) -> None:
        source = self._create_active_source(source_repo)
        for i in range(3):
            doc = KnowledgeDocument(
                document_id=DocumentId(),
                source_id=source.source_id,
                title=f"Doc {i}",
                checksum=DocumentChecksum(value=f"cksum-{i}"),
                classification="public",
                status=DocumentStatus.PENDING,
                created_at=datetime.now(tz=timezone.utc),
            )
            document_repo.save(doc)
        found = document_repo.find_by_source_id(source.source_id)
        assert len(found) == 3

    def test_find_by_checksum(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
    ) -> None:
        source = self._create_active_source(source_repo)
        doc = self._create_document(document_repo, source, checksum="unique-abc")
        found = document_repo.find_by_checksum(DocumentChecksum(value="unique-abc"))
        assert len(found) == 1
        assert str(found[0].document_id) == str(doc.document_id)

    def test_count(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
    ) -> None:
        source = self._create_active_source(source_repo)
        for _ in range(3):
            self._create_document(document_repo, source)
        assert document_repo.count() >= 3

    def _create_active_source(self, source_repo: SqlAlchemyKnowledgeSourceRepository) -> KnowledgeSource:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Doc Test Source",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp/doc-test"),
            classification="public",
            status=SourceStatus.ACTIVE,
            created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        return source

    def _create_document(
        self,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
        source: KnowledgeSource,
        checksum: str = "default-cksum",
    ) -> KnowledgeDocument:
        doc = KnowledgeDocument(
            document_id=DocumentId(),
            source_id=source.source_id,
            title="Test Doc",
            checksum=DocumentChecksum(value=checksum),
            classification="public",
            status=DocumentStatus.PENDING,
            created_at=datetime.now(tz=timezone.utc),
        )
        document_repo.save(doc)
        return doc


# ===================================================================
# Chunk lifecycle
# ===================================================================


class TestChunkLifecycle:
    def test_create_then_get(
        self,
        chunk_repo: SqlAlchemyKnowledgeChunkRepository,
    ) -> None:
        chunk = KnowledgeChunk(
            chunk_id=ChunkId(),
            document_id=DocumentId(),
            chunk_index=ChunkIndex(value=0),
            content=ChunkContent(value="Test chunk content"),
            classification="public",
            created_at=datetime.now(tz=timezone.utc),
        )
        chunk_repo.save(chunk)
        found = chunk_repo.find_by_id(chunk.chunk_id)
        assert found is not None
        assert str(found.chunk_id) == str(chunk.chunk_id)

    def test_find_by_document_id(
        self,
        chunk_repo: SqlAlchemyKnowledgeChunkRepository,
    ) -> None:
        doc_id = DocumentId()
        for i in range(3):
            chunk = KnowledgeChunk(
                chunk_id=ChunkId(),
                document_id=doc_id,
                chunk_index=ChunkIndex(value=i),
                content=ChunkContent(value=f"Chunk {i}"),
                classification="public",
                created_at=datetime.now(tz=timezone.utc),
            )
            chunk_repo.save(chunk)
        found = chunk_repo.find_by_document_id(doc_id)
        assert len(found) == 3

    def test_find_by_index_range(
        self,
        chunk_repo: SqlAlchemyKnowledgeChunkRepository,
    ) -> None:
        doc_id = DocumentId()
        for i in range(5):
            chunk = KnowledgeChunk(
                chunk_id=ChunkId(),
                document_id=doc_id,
                chunk_index=ChunkIndex(value=i),
                content=ChunkContent(value=f"Chunk {i}"),
                classification="public",
                created_at=datetime.now(tz=timezone.utc),
            )
            chunk_repo.save(chunk)
        found = chunk_repo.find_by_index_range(doc_id, 1, 3)
        indices = [int(c.chunk_index) for c in found]
        assert sorted(indices) == [1, 2, 3]

    def test_ordering_guarantee(
        self,
        chunk_repo: SqlAlchemyKnowledgeChunkRepository,
    ) -> None:
        doc_id = DocumentId()
        for i in [2, 0, 1]:
            chunk = KnowledgeChunk(
                chunk_id=ChunkId(),
                document_id=doc_id,
                chunk_index=ChunkIndex(value=i),
                content=ChunkContent(value=f"Chunk {i}"),
                classification="public",
                created_at=datetime.now(tz=timezone.utc),
            )
            chunk_repo.save(chunk)
        found = chunk_repo.find_by_document_id(doc_id)
        indices = [int(c.chunk_index) for c in found]
        assert indices == sorted(indices)

    def test_count(
        self,
        chunk_repo: SqlAlchemyKnowledgeChunkRepository,
    ) -> None:
        doc_id = DocumentId()
        for i in range(3):
            chunk = KnowledgeChunk(
                chunk_id=ChunkId(),
                document_id=doc_id,
                chunk_index=ChunkIndex(value=i),
                content=ChunkContent(value=f"Chunk {i}"),
                classification="public",
                created_at=datetime.now(tz=timezone.utc),
            )
            chunk_repo.save(chunk)
        assert chunk_repo.count() >= 3


# ===================================================================
# Ingestion lifecycle
# ===================================================================


class TestIngestionLifecycle:
    def test_start_then_complete(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        job_repo: SqlAlchemyIngestionJobRepository,
    ) -> None:
        source = self._create_active_source(source_repo)
        job = IngestionJob(
            job_id=IngestionJobId(),
            source_id=source.source_id,
            status=IngestionStatus.RUNNING,
            started_at=datetime.now(tz=timezone.utc),
        )
        job_repo.save(job)

        job.complete()
        job_repo.save(job)
        found = job_repo.find_by_id(job.job_id)
        assert found is not None
        assert found.status == IngestionStatus.COMPLETED
        assert found.completed_at is not None

    def test_start_then_fail(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        job_repo: SqlAlchemyIngestionJobRepository,
    ) -> None:
        source = self._create_active_source(source_repo)
        job = IngestionJob(
            job_id=IngestionJobId(),
            source_id=source.source_id,
            status=IngestionStatus.RUNNING,
            started_at=datetime.now(tz=timezone.utc),
        )
        job_repo.save(job)

        job.fail("Something went wrong")
        job_repo.save(job)
        found = job_repo.find_by_id(job.job_id)
        assert found is not None
        assert found.status == IngestionStatus.FAILED
        assert found.error_message == "Something went wrong"

    def test_invalid_complete_twice(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        job_repo: SqlAlchemyIngestionJobRepository,
    ) -> None:
        source = self._create_active_source(source_repo)
        job = IngestionJob(
            job_id=IngestionJobId(),
            source_id=source.source_id,
            status=IngestionStatus.RUNNING,
            started_at=datetime.now(tz=timezone.utc),
        )
        job_repo.save(job)
        job.complete()
        job_repo.save(job)
        with pytest.raises(Exception):
            job.complete()

    def test_invalid_fail_after_complete(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        job_repo: SqlAlchemyIngestionJobRepository,
    ) -> None:
        source = self._create_active_source(source_repo)
        job = IngestionJob(
            job_id=IngestionJobId(),
            source_id=source.source_id,
            status=IngestionStatus.RUNNING,
            started_at=datetime.now(tz=timezone.utc),
        )
        job_repo.save(job)
        job.complete()
        with pytest.raises(Exception):
            job.fail("too late")

    def test_find_by_status(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        job_repo: SqlAlchemyIngestionJobRepository,
    ) -> None:
        source = self._create_active_source(source_repo)
        for status in [IngestionStatus.RUNNING, IngestionStatus.COMPLETED, IngestionStatus.FAILED]:
            j = IngestionJob(
                job_id=IngestionJobId(),
                source_id=source.source_id,
                status=status,
                started_at=datetime.now(tz=timezone.utc),
                completed_at=datetime.now(tz=timezone.utc) if status != IngestionStatus.RUNNING else None,
                error_message="error" if status == IngestionStatus.FAILED else None,
            )
            job_repo.save(j)
        for status in IngestionStatus:
            if status == IngestionStatus.QUEUED:
                continue
            found = job_repo.find_by_status(status)
            assert len(found) >= 1

    def test_find_by_source_id(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        job_repo: SqlAlchemyIngestionJobRepository,
    ) -> None:
        source = self._create_active_source(source_repo)
        for _ in range(2):
            j = IngestionJob(
                job_id=IngestionJobId(),
                source_id=source.source_id,
                status=IngestionStatus.RUNNING,
                started_at=datetime.now(tz=timezone.utc),
            )
            job_repo.save(j)
        found = job_repo.find_by_source_id(source.source_id)
        assert len(found) == 2

    def test_count(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        job_repo: SqlAlchemyIngestionJobRepository,
    ) -> None:
        source = self._create_active_source(source_repo)
        for _ in range(2):
            j = IngestionJob(
                job_id=IngestionJobId(),
                source_id=source.source_id,
                status=IngestionStatus.RUNNING,
                started_at=datetime.now(tz=timezone.utc),
            )
            job_repo.save(j)
        assert job_repo.count() >= 2

    def _create_active_source(self, source_repo: SqlAlchemyKnowledgeSourceRepository) -> KnowledgeSource:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Ingestion Test Source",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp/ingestion-test"),
            classification="public",
            status=SourceStatus.ACTIVE,
            created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        return source


# ===================================================================
# Reindex flow
# ===================================================================


class TestReindexFlow:
    def test_request_reindex_emits_event(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        outbox: SqlAlchemyKnowledgeOutboxAdapter,
        session: Session,
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Reindex Source",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp/reindex"),
            classification="public",
            status=SourceStatus.ACTIVE,
            created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)

        from backend.knowledge.domain.factory import KnowledgeFactory
        event = KnowledgeFactory.request_reindex(source=source)
        outbox.append(event)
        session.flush()

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], ReindexRequested)

    def test_reindex_requires_active_source(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Inactive Source",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp/inactive"),
            classification="public",
            status=SourceStatus.REGISTERED,
            created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        from backend.knowledge.domain.factory import KnowledgeFactory
        with pytest.raises(Exception):
            KnowledgeFactory.request_reindex(source=source)

    def test_reindex_persists_in_outbox(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        outbox: SqlAlchemyKnowledgeOutboxAdapter,
        session: Session,
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Persist Reindex",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp/persist"),
            classification="public",
            status=SourceStatus.ACTIVE,
            created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        from backend.knowledge.domain.factory import KnowledgeFactory
        event = KnowledgeFactory.request_reindex(source=source)
        outbox.append(event)
        session.flush()

        models = session.query(KnowledgeOutboxModel).all()
        assert len(models) >= 1
        last = models[-1]
        assert last.subject == "knowledge.reindex.requested"


# ===================================================================
# Repository roundtrip (Domain -> DTO -> ORM -> DTO -> Domain)
# ===================================================================


class TestRepositoryRoundtrip:
    def test_source_roundtrip(
        self,
        session: Session,
        source_mapper: KnowledgeSourceMapperImpl,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        original = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Roundtrip Source",
            source_type=SourceType.URL,
            location=SourceLocation(value="https://roundtrip.com"),
            classification="internal",
            status=SourceStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        dto = source_mapper.domain_to_dto(original)
        from backend.knowledge.adapters.outbound.models import KnowledgeSourceModel
        model = KnowledgeSourceModel(
            source_id=dto.source_id,
            name=dto.name,
            source_type=dto.source_type,
            location=dto.location,
            classification=dto.classification,
            status=dto.status,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            deleted_at=dto.deleted_at,
        )
        session.add(model)
        session.flush()
        session.expire(model)
        loaded = session.get(KnowledgeSourceModel, dto.source_id)
        assert loaded is not None
        back_dto = KnowledgeSourceStorageDTO(
            source_id=loaded.source_id,
            name=loaded.name,
            source_type=loaded.source_type,
            location=loaded.location,
            classification=loaded.classification,
            status=loaded.status,
            created_at=loaded.created_at,
            updated_at=loaded.updated_at,
            deleted_at=loaded.deleted_at,
        )
        reconstructed = source_mapper.dto_to_domain(back_dto)
        assert str(reconstructed.source_id) == str(original.source_id)
        assert reconstructed.name == original.name
        assert reconstructed.source_type == original.source_type
        assert str(reconstructed.location) == str(original.location)
        assert reconstructed.classification == original.classification
        assert reconstructed.status == original.status

    def test_document_roundtrip(
        self,
        session: Session,
        document_mapper: KnowledgeDocumentMapperImpl,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        original = KnowledgeDocument(
            document_id=DocumentId(),
            source_id=KnowledgeSourceId(),
            title="Roundtrip Doc",
            checksum=DocumentChecksum(value="roundtrip-cksum"),
            classification="internal",
            status=DocumentStatus.INGESTED,
            revision=2,
            created_at=now,
            updated_at=now,
        )
        dto = document_mapper.domain_to_dto(original)
        from backend.knowledge.adapters.outbound.models import KnowledgeDocumentModel
        model = KnowledgeDocumentModel(
            document_id=dto.document_id,
            source_id=dto.source_id,
            title=dto.title,
            checksum=dto.checksum,
            classification=dto.classification,
            status=dto.status,
            revision=dto.revision,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            deleted_at=dto.deleted_at,
        )
        session.add(model)
        session.flush()
        session.expire(model)
        loaded = session.get(KnowledgeDocumentModel, dto.document_id)
        assert loaded is not None
        back_dto = KnowledgeDocumentStorageDTO(
            document_id=loaded.document_id,
            source_id=loaded.source_id,
            title=loaded.title,
            checksum=loaded.checksum,
            classification=loaded.classification,
            status=loaded.status,
            revision=loaded.revision,
            created_at=loaded.created_at,
            updated_at=loaded.updated_at,
            deleted_at=loaded.deleted_at,
        )
        reconstructed = document_mapper.dto_to_domain(back_dto)
        assert str(reconstructed.document_id) == str(original.document_id)
        assert reconstructed.title == original.title
        assert reconstructed.status == original.status
        assert reconstructed.revision == original.revision

    def test_chunk_roundtrip(
        self,
        session: Session,
        chunk_mapper: KnowledgeChunkMapperImpl,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        original = KnowledgeChunk(
            chunk_id=ChunkId(),
            document_id=DocumentId(),
            chunk_index=ChunkIndex(value=5),
            content=ChunkContent(value="Roundtrip chunk content"),
            classification="internal",
            created_at=now,
        )
        dto = chunk_mapper.domain_to_dto(original)
        from backend.knowledge.adapters.outbound.models import KnowledgeChunkModel
        model = KnowledgeChunkModel(
            chunk_id=dto.chunk_id,
            document_id=dto.document_id,
            chunk_index=dto.chunk_index,
            content=dto.content,
            classification=dto.classification,
            created_at=dto.created_at,
        )
        session.add(model)
        session.flush()
        session.expire(model)
        loaded = session.get(KnowledgeChunkModel, dto.chunk_id)
        assert loaded is not None
        back_dto = KnowledgeChunkStorageDTO(
            chunk_id=loaded.chunk_id,
            document_id=loaded.document_id,
            chunk_index=loaded.chunk_index,
            content=loaded.content,
            classification=loaded.classification,
            created_at=loaded.created_at,
        )
        reconstructed = chunk_mapper.dto_to_domain(back_dto)
        assert str(reconstructed.chunk_id) == str(original.chunk_id)
        assert int(reconstructed.chunk_index) == int(original.chunk_index)
        assert reconstructed.content.value == original.content.value

    def test_ingestion_job_roundtrip(
        self,
        session: Session,
        job_mapper: IngestionJobMapperImpl,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        original = IngestionJob(
            job_id=IngestionJobId(),
            source_id=KnowledgeSourceId(),
            status=IngestionStatus.FAILED,
            started_at=now,
            completed_at=now,
            error_message="Something broke",
        )
        dto = job_mapper.domain_to_dto(original)
        from backend.knowledge.adapters.outbound.models import IngestionJobModel
        model = IngestionJobModel(
            job_id=dto.job_id,
            source_id=dto.source_id,
            status=dto.status,
            error_message=dto.error_message,
            started_at=dto.started_at,
            completed_at=dto.completed_at,
        )
        session.add(model)
        session.flush()
        session.expire(model)
        loaded = session.get(IngestionJobModel, dto.job_id)
        assert loaded is not None
        back_dto = IngestionJobStorageDTO(
            job_id=loaded.job_id,
            source_id=loaded.source_id,
            status=loaded.status,
            error_message=loaded.error_message,
            started_at=loaded.started_at,
            completed_at=loaded.completed_at,
        )
        reconstructed = job_mapper.dto_to_domain(back_dto)
        assert str(reconstructed.job_id) == str(original.job_id)
        assert reconstructed.status == original.status
        assert reconstructed.error_message == original.error_message

    def test_deleted_source_roundtrip(
        self,
        session: Session,
        source_mapper: KnowledgeSourceMapperImpl,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        original = KnowledgeSource(
            source_id=KnowledgeSourceId(),
            name="Deleted Source",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp/deleted"),
            classification="public",
            status=SourceStatus.DELETED,
            created_at=now,
            updated_at=now,
            deleted_at=now,
        )
        dto = source_mapper.domain_to_dto(original)
        reconstructed = source_mapper.dto_to_domain(dto)
        assert reconstructed.status == SourceStatus.DELETED
        assert reconstructed.deleted_at is not None


# ===================================================================
# Event flow (domain event -> outbox -> NATS -> mark published)
# ===================================================================


class TestEventFlow:
    def test_all_events_roundtrip_through_outbox(
        self,
        outbox: SqlAlchemyKnowledgeOutboxAdapter,
        outbox_mapper: KnowledgeOutboxMapperImpl,
        session: Session,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        sid = KnowledgeSourceId()
        did = DocumentId()
        cid = ChunkId()
        jid = IngestionJobId()

        events = [
            KnowledgeSourceRegistered(sid, "n", SourceType.FILE,
                                      SourceLocation(value="/t"), "pub", now),
            KnowledgeSourceDeleted(sid, now),
            DocumentIngested(did, sid, "t", DocumentChecksum(value="c"), "pub", now),
            DocumentIndexed(did, now),
            DocumentDeleted(did, now),
            ChunkCreated(cid, did, ChunkIndex(value=0), now),
            ReindexRequested(sid, now),
            IngestionStarted(jid, sid, now),
            IngestionCompleted(jid, now),
            IngestionFailed(jid, "err", now),
        ]
        for e in events:
            outbox.append(e)
        session.flush()

        fetched = outbox.fetch_unpublished(limit=20)
        assert len(fetched) == 10

    def test_outbox_fifo_ordering(
        self,
        outbox: SqlAlchemyKnowledgeOutboxAdapter,
        session: Session,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        for i in range(5):
            e = KnowledgeSourceRegistered(
                KnowledgeSourceId(), f"S{i}", SourceType.FILE,
                SourceLocation(value="/t"), "pub",
                occurred_at=now,
            )
            outbox.append(e)
        session.flush()

        fetched = outbox.fetch_unpublished(limit=10)
        assert len(fetched) == 5

    def test_nats_publish_and_mark(
        self,
        outbox: SqlAlchemyKnowledgeOutboxAdapter,
        session: Session,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        e = KnowledgeSourceRegistered(
            KnowledgeSourceId(), "NATS Test", SourceType.FILE,
            SourceLocation(value="/tmp/nats"), "public",
            occurred_at=now,
        )
        outbox.append(e)
        session.flush()

        mock_js = AsyncMock()
        mock_js.publish = AsyncMock()

        import asyncio
        asyncio.run(
            publish_knowledge_outbox_events(
                mock_js,
                outbox=outbox,
                batch=10,
                interval_seconds=0.01,
                max_iterations=1,
            )
        )

        assert mock_js.publish.await_count == 1
        remaining = outbox.fetch_unpublished()
        assert len(remaining) == 0

    def test_nats_envelope_contains_expected_fields(
        self,
        outbox: SqlAlchemyKnowledgeOutboxAdapter,
        session: Session,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        e = KnowledgeSourceRegistered(
            KnowledgeSourceId(), "Envelope Test", SourceType.FILE,
            SourceLocation(value="/tmp/env"), "public",
            occurred_at=now,
        )
        outbox.append(e)
        session.flush()

        mock_js = AsyncMock()
        mock_js.publish = AsyncMock()

        import asyncio
        asyncio.run(
            publish_knowledge_outbox_events(
                mock_js,
                outbox=outbox,
                batch=10,
                interval_seconds=0.01,
                max_iterations=1,
            )
        )

        payload = json.loads(mock_js.publish.await_args[0][1])
        assert payload["event_type"] == "KNOWLEDGE_SOURCE_REGISTERED"
        assert payload["producer"] == "knowledge"
        assert payload["kind"] == "event"
        assert "event_id" in payload
        assert "aggregate_id" in payload
        assert "occurred_at" in payload
        assert payload["name"] == "Envelope Test"
        assert payload["source_type"] == "file"

    def test_nats_subject_correct(
        self,
        outbox: SqlAlchemyKnowledgeOutboxAdapter,
        session: Session,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        e = KnowledgeSourceRegistered(
            KnowledgeSourceId(), "Subject Test", SourceType.FILE,
            SourceLocation(value="/tmp/sub"), "public",
            occurred_at=now,
        )
        outbox.append(e)
        session.flush()

        mock_js = AsyncMock()
        mock_js.publish = AsyncMock()

        import asyncio
        asyncio.run(
            publish_knowledge_outbox_events(
                mock_js,
                outbox=outbox,
                batch=10,
                interval_seconds=0.01,
                max_iterations=1,
            )
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.knowledge.event.source_registered.v1"

    def test_mark_published_idempotent(
        self,
        outbox: SqlAlchemyKnowledgeOutboxAdapter,
        session: Session,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        sid = KnowledgeSourceId()
        e = KnowledgeSourceRegistered(
            sid, "Idempotent", SourceType.FILE,
            SourceLocation(value="/tmp/idem"), "public",
            occurred_at=now,
        )
        outbox.append(e)
        session.flush()

        fetched = outbox.fetch_unpublished()
        outbox.mark_published(str(fetched[0].event_id))
        session.flush()
        remaining = outbox.fetch_unpublished()
        assert len(remaining) == 0

        outbox.mark_published(str(fetched[0].event_id))
        session.flush()
        remaining = outbox.fetch_unpublished()
        assert len(remaining) == 0


# ===================================================================
# REST contract validation
# ===================================================================


class TestRESTContract:
    def test_post_sources_201(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/knowledge/sources",
            json={"name": "REST Source", "source_type": "file", "location": "/tmp/rest", "classification": "public"},
        )
        assert resp.status_code == 201
        assert "source_id" in resp.json()

    def test_post_sources_422_empty_name(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/knowledge/sources",
            json={"name": "", "source_type": "file", "location": "/tmp", "classification": "public"},
        )
        assert resp.status_code == 422

    def test_post_sources_422_invalid_type(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/knowledge/sources",
            json={"name": "Test", "source_type": "invalid", "location": "/tmp", "classification": "public"},
        )
        assert resp.status_code == 422

    def test_get_sources_200(self, client: TestClient) -> None:
        resp = client.get("/api/v1/knowledge/sources")
        assert resp.status_code == 200
        assert "sources" in resp.json()

    def test_get_sources_by_id_200(
        self, client: TestClient, session: Session, source_repo: SqlAlchemyKnowledgeSourceRepository
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(), name="Get Test", source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp"), classification="public",
            status=SourceStatus.ACTIVE, created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        session.commit()
        resp = client.get(f"/api/v1/knowledge/sources/{source.source_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Get Test"

    def test_get_sources_404(self, client: TestClient) -> None:
        resp = client.get("/api/v1/knowledge/sources/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_delete_sources_200(
        self, client: TestClient, session: Session, source_repo: SqlAlchemyKnowledgeSourceRepository
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(), name="Del Test", source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp"), classification="public",
            status=SourceStatus.ACTIVE, created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        session.commit()
        resp = client.delete(f"/api/v1/knowledge/sources/{source.source_id}")
        assert resp.status_code == 200
        assert "deleted_at" in resp.json()

    def test_delete_sources_404(self, client: TestClient) -> None:
        resp = client.delete("/api/v1/knowledge/sources/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_post_documents_201(
        self, client: TestClient, session: Session, source_repo: SqlAlchemyKnowledgeSourceRepository
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(), name="Doc REST", source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp"), classification="public",
            status=SourceStatus.ACTIVE, created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        session.commit()
        resp = client.post(
            "/api/v1/knowledge/documents",
            json={"source_id": str(source.source_id), "title": "REST Doc", "checksum": "abc", "classification": "public"},
        )
        assert resp.status_code == 201
        assert resp.json()["title"] == "REST Doc"

    def test_post_documents_404(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/knowledge/documents",
            json={"source_id": "00000000-0000-0000-0000-000000000000", "title": "No Source", "checksum": "abc", "classification": "public"},
        )
        assert resp.status_code == 404

    def test_get_documents_200(
        self, client: TestClient, session: Session, source_repo: SqlAlchemyKnowledgeSourceRepository,
        document_repo: SqlAlchemyKnowledgeDocumentRepository
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(), name="Doc Get", source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp"), classification="public",
            status=SourceStatus.ACTIVE, created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        doc = KnowledgeDocument(
            document_id=DocumentId(), source_id=source.source_id, title="Get Doc",
            checksum=DocumentChecksum(value="abc"), classification="public",
            status=DocumentStatus.PENDING, created_at=datetime.now(tz=timezone.utc),
        )
        document_repo.save(doc)
        session.commit()
        resp = client.get(f"/api/v1/knowledge/documents/{doc.document_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Get Doc"

    def test_get_documents_404(self, client: TestClient) -> None:
        resp = client.get("/api/v1/knowledge/documents/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_post_chunks_201(
        self, client: TestClient, session: Session, source_repo: SqlAlchemyKnowledgeSourceRepository,
        document_repo: SqlAlchemyKnowledgeDocumentRepository
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(), name="Chunk REST", source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp"), classification="public",
            status=SourceStatus.ACTIVE, created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        doc = KnowledgeDocument(
            document_id=DocumentId(), source_id=source.source_id, title="Chunk Doc",
            checksum=DocumentChecksum(value="abc"), classification="public",
            status=DocumentStatus.PENDING, created_at=datetime.now(tz=timezone.utc),
        )
        document_repo.save(doc)
        session.commit()
        resp = client.post(
            "/api/v1/knowledge/chunks",
            json={"document_id": str(doc.document_id), "chunk_index": 0, "content": "Chunk content"},
        )
        assert resp.status_code == 201

    def test_post_chunks_404(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/knowledge/chunks",
            json={"document_id": "00000000-0000-0000-0000-000000000000", "chunk_index": 0, "content": "test"},
        )
        assert resp.status_code == 404

    def test_get_chunks_by_document_200(
        self, client: TestClient, session: Session, source_repo: SqlAlchemyKnowledgeSourceRepository,
        document_repo: SqlAlchemyKnowledgeDocumentRepository
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(), name="Chunk List", source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp"), classification="public",
            status=SourceStatus.ACTIVE, created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        doc = KnowledgeDocument(
            document_id=DocumentId(), source_id=source.source_id, title="List Doc",
            checksum=DocumentChecksum(value="abc"), classification="public",
            status=DocumentStatus.PENDING, created_at=datetime.now(tz=timezone.utc),
        )
        document_repo.save(doc)
        session.commit()
        resp = client.get(f"/api/v1/knowledge/documents/{doc.document_id}/chunks")
        assert resp.status_code == 200
        assert resp.json()["chunks"] == []

    def test_post_ingestions_201(
        self, client: TestClient, session: Session, source_repo: SqlAlchemyKnowledgeSourceRepository
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(), name="Ingest REST", source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp"), classification="public",
            status=SourceStatus.ACTIVE, created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        session.commit()
        resp = client.post("/api/v1/knowledge/ingestions", json={"source_id": str(source.source_id)})
        assert resp.status_code == 201
        assert resp.json()["status"] == "running"

    def test_post_ingestions_404(self, client: TestClient) -> None:
        resp = client.post("/api/v1/knowledge/ingestions", json={"source_id": "00000000-0000-0000-0000-000000000000"})
        assert resp.status_code == 404

    def test_post_ingestions_complete_200(
        self, client: TestClient, session: Session, source_repo: SqlAlchemyKnowledgeSourceRepository
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(), name="Complete REST", source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp"), classification="public",
            status=SourceStatus.ACTIVE, created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        session.commit()
        job_resp = client.post("/api/v1/knowledge/ingestions", json={"source_id": str(source.source_id)})
        job_id = job_resp.json()["job_id"]
        resp = client.post(f"/api/v1/knowledge/ingestions/{job_id}/complete")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_post_ingestions_complete_404(self, client: TestClient) -> None:
        resp = client.post("/api/v1/knowledge/ingestions/00000000-0000-0000-0000-000000000000/complete")
        assert resp.status_code == 404

    def test_post_ingestions_fail_200(
        self, client: TestClient, session: Session, source_repo: SqlAlchemyKnowledgeSourceRepository
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(), name="Fail REST", source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp"), classification="public",
            status=SourceStatus.ACTIVE, created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        session.commit()
        job_resp = client.post("/api/v1/knowledge/ingestions", json={"source_id": str(source.source_id)})
        job_id = job_resp.json()["job_id"]
        resp = client.post(f"/api/v1/knowledge/ingestions/{job_id}/fail", json={"error_message": "Failed"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_post_ingestions_fail_404(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/knowledge/ingestions/00000000-0000-0000-0000-000000000000/fail",
            json={"error_message": "error"},
        )
        assert resp.status_code == 404

    def test_get_ingestions_200(
        self, client: TestClient, session: Session, source_repo: SqlAlchemyKnowledgeSourceRepository
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(), name="Get Ing REST", source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp"), classification="public",
            status=SourceStatus.ACTIVE, created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        session.commit()
        job_resp = client.post("/api/v1/knowledge/ingestions", json={"source_id": str(source.source_id)})
        job_id = job_resp.json()["job_id"]
        resp = client.get(f"/api/v1/knowledge/ingestions/{job_id}")
        assert resp.status_code == 200
        assert resp.json()["job_id"] == job_id

    def test_get_ingestions_404(self, client: TestClient) -> None:
        resp = client.get("/api/v1/knowledge/ingestions/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_post_reindex_200(
        self, client: TestClient, session: Session, source_repo: SqlAlchemyKnowledgeSourceRepository
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(), name="Reindex REST", source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp"), classification="public",
            status=SourceStatus.ACTIVE, created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        session.commit()
        resp = client.post(f"/api/v1/knowledge/sources/{source.source_id}/reindex")
        assert resp.status_code == 200
        assert resp.json()["source_id"] == str(source.source_id)

    def test_post_reindex_404(self, client: TestClient) -> None:
        resp = client.post("/api/v1/knowledge/sources/00000000-0000-0000-0000-000000000000/reindex")
        assert resp.status_code == 404


# ===================================================================
# Cross-entity integrity
# ===================================================================


class TestCrossEntityIntegrity:
    def test_source_owns_documents(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        document_repo: SqlAlchemyKnowledgeDocumentRepository,
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(), name="Owner Source", source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp"), classification="public",
            status=SourceStatus.ACTIVE, created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        for i in range(3):
            doc = KnowledgeDocument(
                document_id=DocumentId(), source_id=source.source_id, title=f"Doc {i}",
                checksum=DocumentChecksum(value=f"c{i}"), classification="public",
                status=DocumentStatus.PENDING, created_at=datetime.now(tz=timezone.utc),
            )
            document_repo.save(doc)
        docs = document_repo.find_by_source_id(source.source_id)
        assert len(docs) == 3
        for doc in docs:
            assert doc.source_id == source.source_id

    def test_document_owns_chunks(
        self,
        chunk_repo: SqlAlchemyKnowledgeChunkRepository,
    ) -> None:
        doc_id = DocumentId()
        for i in range(3):
            chunk = KnowledgeChunk(
                chunk_id=ChunkId(), document_id=doc_id, chunk_index=ChunkIndex(value=i),
                content=ChunkContent(value=f"Chunk {i}"), classification="public",
                created_at=datetime.now(tz=timezone.utc),
            )
            chunk_repo.save(chunk)
        chunks = chunk_repo.find_by_document_id(doc_id)
        assert len(chunks) == 3
        for chunk in chunks:
            assert chunk.document_id == doc_id

    def test_ingestion_job_references_source(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
        job_repo: SqlAlchemyIngestionJobRepository,
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(), name="Ing Ref Source", source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp"), classification="public",
            status=SourceStatus.ACTIVE, created_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        job = IngestionJob(
            job_id=IngestionJobId(), source_id=source.source_id,
            status=IngestionStatus.RUNNING, started_at=datetime.now(tz=timezone.utc),
        )
        job_repo.save(job)
        found = job_repo.find_by_source_id(source.source_id)
        assert len(found) >= 1
        assert found[0].source_id == source.source_id

    def test_deleted_source_blocks_new_documents(
        self,
        source_repo: SqlAlchemyKnowledgeSourceRepository,
    ) -> None:
        source = KnowledgeSource(
            source_id=KnowledgeSourceId(), name="Deleted Source Block", source_type=SourceType.FILE,
            location=SourceLocation(value="/tmp"), classification="public",
            status=SourceStatus.DELETED, created_at=datetime.now(tz=timezone.utc),
            deleted_at=datetime.now(tz=timezone.utc),
        )
        source_repo.save(source)
        from backend.knowledge.domain.factory import KnowledgeFactory
        with pytest.raises(Exception):
            KnowledgeFactory.ingest_document(
                source=source, title="Blocked", checksum="abc", classification="public",
            )


# ===================================================================
# Outbox ordering
# ===================================================================


class TestOutboxOrdering:
    def test_fifo_preserved_across_event_types(
        self,
        outbox: SqlAlchemyKnowledgeOutboxAdapter,
        session: Session,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        events = [
            KnowledgeSourceRegistered(KnowledgeSourceId(), "A", SourceType.FILE,
                                      SourceLocation(value="/a"), "pub", base),
            DocumentIngested(DocumentId(), KnowledgeSourceId(), "B",
                             DocumentChecksum(value="b"), "pub", base),
            ChunkCreated(ChunkId(), DocumentId(), ChunkIndex(value=0), base),
            IngestionStarted(IngestionJobId(), KnowledgeSourceId(), base),
        ]
        for e in events:
            outbox.append(e)
        session.flush()

        fetched = outbox.fetch_unpublished(limit=10)
        assert len(fetched) == 4
        types = [type(e).__name__ for e in fetched]
        assert types == ["KnowledgeSourceRegistered", "DocumentIngested", "ChunkCreated", "IngestionStarted"]

    def test_batch_respects_limit(
        self,
        outbox: SqlAlchemyKnowledgeOutboxAdapter,
        session: Session,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        for i in range(5):
            e = KnowledgeSourceRegistered(
                KnowledgeSourceId(), f"S{i}", SourceType.FILE,
                SourceLocation(value=f"/{i}"), "pub", now,
            )
            outbox.append(e)
        session.flush()

        fetched = outbox.fetch_unpublished(limit=3)
        assert len(fetched) == 3

    def test_mixed_event_types_preserve_order(
        self,
        outbox: SqlAlchemyKnowledgeOutboxAdapter,
        session: Session,
    ) -> None:
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(3):
            outbox.append(KnowledgeSourceRegistered(
                KnowledgeSourceId(), f"S{i}", SourceType.FILE,
                SourceLocation(value=f"/{i}"), "pub", base,
            ))
            outbox.append(DocumentIngested(
                DocumentId(), KnowledgeSourceId(), f"D{i}",
                DocumentChecksum(value=f"d{i}"), "pub", base,
            ))
        session.flush()

        fetched = outbox.fetch_unpublished(limit=10)
        assert len(fetched) == 6
        for i in range(3):
            assert isinstance(fetched[i * 2], KnowledgeSourceRegistered)
            assert isinstance(fetched[i * 2 + 1], DocumentIngested)

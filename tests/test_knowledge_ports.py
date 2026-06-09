from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

import pytest

from backend.knowledge.application.ports.clock import KnowledgeClockPort
from backend.knowledge.application.ports.id_generator import KnowledgeIdGeneratorPort
from backend.knowledge.application.ports.outbox import KnowledgeOutboxEvent, KnowledgeOutboxPort
from backend.knowledge.application.ports.repository import (
    IngestionJobRepositoryPort,
    KnowledgeChunkRepositoryPort,
    KnowledgeDocumentRepositoryPort,
    KnowledgeSourceRepositoryPort,
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


# =============================================================================
# Helpers
# =============================================================================


def _make_source(
    *,
    source_id: KnowledgeSourceId | None = None,
    name: str = "test-source",
    source_type: SourceType = SourceType.FILE,
    status: SourceStatus = SourceStatus.REGISTERED,
) -> KnowledgeSource:
    loc = SourceLocation(value="/tmp/test")
    return KnowledgeSource(
        source_id=source_id or KnowledgeSourceId(),
        name=name,
        source_type=source_type,
        location=loc,
        classification="public",
        status=status,
    )


def _make_active_source() -> KnowledgeSource:
    s = _make_source()
    s.activate()
    return s


def _make_document(
    *,
    document_id: DocumentId | None = None,
    source_id: KnowledgeSourceId | None = None,
    title: str = "test-doc",
    status: DocumentStatus = DocumentStatus.PENDING,
    checksum: str = "abc123",
) -> KnowledgeDocument:
    return KnowledgeDocument(
        document_id=document_id or DocumentId(),
        source_id=source_id or KnowledgeSourceId(),
        title=title,
        checksum=DocumentChecksum(value=checksum),
        classification="public",
        status=status,
    )


def _make_chunk(
    *,
    chunk_id: ChunkId | None = None,
    document_id: DocumentId | None = None,
    chunk_index: int = 0,
) -> KnowledgeChunk:
    return KnowledgeChunk(
        chunk_id=chunk_id or ChunkId(),
        document_id=document_id or DocumentId(),
        chunk_index=ChunkIndex(value=chunk_index),
        content=ChunkContent(value="test chunk content"),
        classification="public",
    )


def _make_job(
    *,
    job_id: IngestionJobId | None = None,
    source_id: KnowledgeSourceId | None = None,
    status: IngestionStatus = IngestionStatus.RUNNING,
) -> IngestionJob:
    return IngestionJob(
        job_id=job_id or IngestionJobId(),
        source_id=source_id or KnowledgeSourceId(),
        status=status,
    )


_now = datetime.now(tz=timezone.utc)


def _make_source_registered_event() -> KnowledgeSourceRegistered:
    return KnowledgeSourceRegistered(
        source_id=KnowledgeSourceId(),
        name="src",
        source_type=SourceType.FILE,
        location=SourceLocation(value="/p"),
        classification="public",
        occurred_at=_now,
    )


def _make_document_ingested_event() -> DocumentIngested:
    return DocumentIngested(
        document_id=DocumentId(),
        source_id=KnowledgeSourceId(),
        title="doc",
        checksum=DocumentChecksum(value="abc"),
        classification="public",
        occurred_at=_now,
    )


# =============================================================================
# KnowledgeSourceRepositoryPort Stub
# =============================================================================


class StubKnowledgeSourceRepository:
    """Minimal stub conforming to KnowledgeSourceRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, KnowledgeSource] = {}

    def save(self, source: KnowledgeSource) -> None:
        key = str(source.source_id)
        self._store[key] = source

    def find_by_id(self, source_id: KnowledgeSourceId) -> KnowledgeSource | None:
        return self._store.get(str(source_id))

    def find_by_status(self, status: SourceStatus) -> list[KnowledgeSource]:
        return [s for s in self._store.values() if s.status == status]

    def find_by_type(self, source_type: SourceType) -> list[KnowledgeSource]:
        return [s for s in self._store.values() if s.source_type == source_type]

    def count(self) -> int:
        return len(self._store)


class TestKnowledgeSourceRepositoryPort:
    """Contract tests for KnowledgeSourceRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubKnowledgeSourceRepository:
        return StubKnowledgeSourceRepository()

    def test_save_and_find_by_id(self, repo: StubKnowledgeSourceRepository) -> None:
        source = _make_source(name="my-source")
        repo.save(source)
        found = repo.find_by_id(source.source_id)
        assert found is not None
        assert found.name == "my-source"
        assert found.source_id == source.source_id

    def test_find_by_id_returns_none(self, repo: StubKnowledgeSourceRepository) -> None:
        missing_id = KnowledgeSourceId()
        assert repo.find_by_id(missing_id) is None

    def test_find_by_status(self, repo: StubKnowledgeSourceRepository) -> None:
        s1 = _make_source(status=SourceStatus.ACTIVE)
        s2 = _make_source(status=SourceStatus.ACTIVE)
        s3 = _make_source(status=SourceStatus.REGISTERED)
        repo.save(s1)
        repo.save(s2)
        repo.save(s3)

        results = repo.find_by_status(SourceStatus.ACTIVE)
        assert len(results) == 2
        assert all(r.status == SourceStatus.ACTIVE for r in results)

    def test_find_by_status_empty(self, repo: StubKnowledgeSourceRepository) -> None:
        results = repo.find_by_status(SourceStatus.DELETED)
        assert results == []

    def test_find_by_type(self, repo: StubKnowledgeSourceRepository) -> None:
        s1 = _make_source(source_type=SourceType.FILE)
        s2 = _make_source(source_type=SourceType.FILE)
        s3 = _make_source(source_type=SourceType.URL)
        repo.save(s1)
        repo.save(s2)
        repo.save(s3)

        results = repo.find_by_type(SourceType.FILE)
        assert len(results) == 2
        assert all(r.source_type == SourceType.FILE for r in results)

    def test_find_by_type_empty(self, repo: StubKnowledgeSourceRepository) -> None:
        results = repo.find_by_type(SourceType.DIRECTORY)
        assert results == []

    def test_count(self, repo: StubKnowledgeSourceRepository) -> None:
        assert repo.count() == 0
        repo.save(_make_source())
        assert repo.count() == 1
        repo.save(_make_source())
        assert repo.count() == 2

    def test_save_upsert_semantics(self, repo: StubKnowledgeSourceRepository) -> None:
        sid = KnowledgeSourceId()
        s1 = _make_source(source_id=sid, name="original")
        repo.save(s1)
        assert repo.count() == 1

        s2 = _make_source(source_id=sid, name="updated")
        repo.save(s2)
        assert repo.count() == 1

        found = repo.find_by_id(sid)
        assert found is not None
        assert found.name == "updated"


# =============================================================================
# KnowledgeDocumentRepositoryPort Stub
# =============================================================================


class StubKnowledgeDocumentRepository:
    """Minimal stub conforming to KnowledgeDocumentRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, KnowledgeDocument] = {}

    def save(self, document: KnowledgeDocument) -> None:
        key = str(document.document_id)
        self._store[key] = document

    def find_by_id(self, document_id: DocumentId) -> KnowledgeDocument | None:
        return self._store.get(str(document_id))

    def find_by_source_id(
        self, source_id: KnowledgeSourceId
    ) -> list[KnowledgeDocument]:
        return [
            d for d in self._store.values() if d.source_id == source_id
        ]

    def find_by_checksum(
        self, checksum: DocumentChecksum
    ) -> list[KnowledgeDocument]:
        return [
            d for d in self._store.values() if d.checksum == checksum
        ]

    def find_deleted(self) -> list[KnowledgeDocument]:
        return [d for d in self._store.values() if d.is_deleted]

    def count(self) -> int:
        return len(self._store)


class TestKnowledgeDocumentRepositoryPort:
    """Contract tests for KnowledgeDocumentRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubKnowledgeDocumentRepository:
        return StubKnowledgeDocumentRepository()

    def test_save_and_find_by_id(self, repo: StubKnowledgeDocumentRepository) -> None:
        doc = _make_document(title="my-doc")
        repo.save(doc)
        found = repo.find_by_id(doc.document_id)
        assert found is not None
        assert found.title == "my-doc"
        assert found.document_id == doc.document_id

    def test_find_by_id_returns_none(self, repo: StubKnowledgeDocumentRepository) -> None:
        assert repo.find_by_id(DocumentId()) is None

    def test_find_by_source_id(self, repo: StubKnowledgeDocumentRepository) -> None:
        sid = KnowledgeSourceId()
        d1 = _make_document(source_id=sid, title="doc1")
        d2 = _make_document(source_id=sid, title="doc2")
        d3 = _make_document(title="other")
        repo.save(d1)
        repo.save(d2)
        repo.save(d3)

        results = repo.find_by_source_id(sid)
        assert len(results) == 2
        assert all(r.source_id == sid for r in results)

    def test_find_by_source_id_empty(self, repo: StubKnowledgeDocumentRepository) -> None:
        results = repo.find_by_source_id(KnowledgeSourceId())
        assert results == []

    def test_find_by_checksum(self, repo: StubKnowledgeDocumentRepository) -> None:
        cs = DocumentChecksum(value="xyz789")
        d1 = _make_document(checksum="xyz789")
        d2 = _make_document(checksum="xyz789")
        d3 = _make_document(checksum="other")
        repo.save(d1)
        repo.save(d2)
        repo.save(d3)

        results = repo.find_by_checksum(cs)
        assert len(results) == 2
        assert all(r.checksum == cs for r in results)

    def test_find_by_checksum_empty(self, repo: StubKnowledgeDocumentRepository) -> None:
        cs = DocumentChecksum(value="nonexistent")
        results = repo.find_by_checksum(cs)
        assert results == []

    def test_find_deleted(self, repo: StubKnowledgeDocumentRepository) -> None:
        d1 = _make_document()
        d1.delete()
        d2 = _make_document()
        d3 = _make_document()
        d3.delete()
        repo.save(d1)
        repo.save(d2)
        repo.save(d3)

        results = repo.find_deleted()
        assert len(results) == 2
        assert all(r.is_deleted for r in results)

    def test_find_deleted_empty(self, repo: StubKnowledgeDocumentRepository) -> None:
        repo.save(_make_document())
        results = repo.find_deleted()
        assert results == []

    def test_count(self, repo: StubKnowledgeDocumentRepository) -> None:
        assert repo.count() == 0
        repo.save(_make_document())
        assert repo.count() == 1
        repo.save(_make_document())
        assert repo.count() == 2

    def test_save_upsert_semantics(self, repo: StubKnowledgeDocumentRepository) -> None:
        did = DocumentId()
        d1 = _make_document(document_id=did, title="original")
        repo.save(d1)
        assert repo.count() == 1

        d2 = _make_document(document_id=did, title="updated")
        repo.save(d2)
        assert repo.count() == 1

        found = repo.find_by_id(did)
        assert found is not None
        assert found.title == "updated"


# =============================================================================
# KnowledgeChunkRepositoryPort Stub
# =============================================================================


class StubKnowledgeChunkRepository:
    """Minimal stub conforming to KnowledgeChunkRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, KnowledgeChunk] = {}

    def save(self, chunk: KnowledgeChunk) -> None:
        key = str(chunk.chunk_id)
        self._store[key] = chunk

    def find_by_id(self, chunk_id: ChunkId) -> KnowledgeChunk | None:
        return self._store.get(str(chunk_id))

    def find_by_document_id(
        self, document_id: DocumentId
    ) -> list[KnowledgeChunk]:
        results = [
            c for c in self._store.values() if c.document_id == document_id
        ]
        results.sort(key=lambda c: int(c.chunk_index) if c.chunk_index else 0)
        return results

    def find_by_index_range(
        self, document_id: DocumentId, start_index: int, end_index: int
    ) -> list[KnowledgeChunk]:
        results = [
            c
            for c in self._store.values()
            if c.document_id == document_id
            and c.chunk_index is not None
            and start_index <= int(c.chunk_index) <= end_index
        ]
        results.sort(key=lambda c: int(c.chunk_index) if c.chunk_index else 0)
        return results

    def count(self) -> int:
        return len(self._store)


class TestKnowledgeChunkRepositoryPort:
    """Contract tests for KnowledgeChunkRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubKnowledgeChunkRepository:
        return StubKnowledgeChunkRepository()

    def test_save_and_find_by_id(self, repo: StubKnowledgeChunkRepository) -> None:
        chunk = _make_chunk()
        repo.save(chunk)
        found = repo.find_by_id(chunk.chunk_id)
        assert found is not None
        assert found.chunk_id == chunk.chunk_id

    def test_find_by_id_returns_none(self, repo: StubKnowledgeChunkRepository) -> None:
        assert repo.find_by_id(ChunkId()) is None

    def test_find_by_document_id(self, repo: StubKnowledgeChunkRepository) -> None:
        did = DocumentId()
        c1 = _make_chunk(document_id=did, chunk_index=0)
        c2 = _make_chunk(document_id=did, chunk_index=1)
        c3 = _make_chunk()
        repo.save(c1)
        repo.save(c2)
        repo.save(c3)

        results = repo.find_by_document_id(did)
        assert len(results) == 2
        assert all(r.document_id == did for r in results)

    def test_find_by_document_id_preserves_order(
        self, repo: StubKnowledgeChunkRepository
    ) -> None:
        did = DocumentId()
        c1 = _make_chunk(document_id=did, chunk_index=2)
        c2 = _make_chunk(document_id=did, chunk_index=0)
        c3 = _make_chunk(document_id=did, chunk_index=1)
        repo.save(c1)
        repo.save(c2)
        repo.save(c3)

        results = repo.find_by_document_id(did)
        indices = [
            int(c.chunk_index) for c in results if c.chunk_index is not None
        ]
        assert indices == [0, 1, 2]

    def test_find_by_document_id_empty(self, repo: StubKnowledgeChunkRepository) -> None:
        results = repo.find_by_document_id(DocumentId())
        assert results == []

    def test_find_by_index_range(self, repo: StubKnowledgeChunkRepository) -> None:
        did = DocumentId()
        c0 = _make_chunk(document_id=did, chunk_index=0)
        c1 = _make_chunk(document_id=did, chunk_index=1)
        c2 = _make_chunk(document_id=did, chunk_index=2)
        c3 = _make_chunk(document_id=did, chunk_index=3)
        repo.save(c0)
        repo.save(c1)
        repo.save(c2)
        repo.save(c3)

        results = repo.find_by_index_range(did, 1, 2)
        assert len(results) == 2
        assert int(results[0].chunk_index) == 1
        assert int(results[1].chunk_index) == 2

    def test_find_by_index_range_empty(self, repo: StubKnowledgeChunkRepository) -> None:
        did = DocumentId()
        results = repo.find_by_index_range(did, 0, 10)
        assert results == []

    def test_count(self, repo: StubKnowledgeChunkRepository) -> None:
        assert repo.count() == 0
        repo.save(_make_chunk())
        assert repo.count() == 1
        repo.save(_make_chunk())
        assert repo.count() == 2

    def test_save_upsert_semantics(self, repo: StubKnowledgeChunkRepository) -> None:
        cid = ChunkId()
        c1 = _make_chunk(chunk_id=cid, chunk_index=0)
        repo.save(c1)
        assert repo.count() == 1

        c2 = _make_chunk(chunk_id=cid, chunk_index=1)
        repo.save(c2)
        assert repo.count() == 1


# =============================================================================
# IngestionJobRepositoryPort Stub
# =============================================================================


class StubIngestionJobRepository:
    """Minimal stub conforming to IngestionJobRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, IngestionJob] = {}

    def save(self, job: IngestionJob) -> None:
        key = str(job.job_id)
        self._store[key] = job

    def find_by_id(self, job_id: IngestionJobId) -> IngestionJob | None:
        return self._store.get(str(job_id))

    def find_by_source_id(
        self, source_id: KnowledgeSourceId
    ) -> list[IngestionJob]:
        return [
            j for j in self._store.values() if j.source_id == source_id
        ]

    def find_by_status(
        self, status: IngestionStatus
    ) -> list[IngestionJob]:
        return [j for j in self._store.values() if j.status == status]

    def count(self) -> int:
        return len(self._store)


class TestIngestionJobRepositoryPort:
    """Contract tests for IngestionJobRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubIngestionJobRepository:
        return StubIngestionJobRepository()

    def test_save_and_find_by_id(self, repo: StubIngestionJobRepository) -> None:
        job = _make_job()
        repo.save(job)
        found = repo.find_by_id(job.job_id)
        assert found is not None
        assert found.job_id == job.job_id

    def test_find_by_id_returns_none(self, repo: StubIngestionJobRepository) -> None:
        assert repo.find_by_id(IngestionJobId()) is None

    def test_find_by_source_id(self, repo: StubIngestionJobRepository) -> None:
        sid = KnowledgeSourceId()
        j1 = _make_job(source_id=sid)
        j2 = _make_job(source_id=sid)
        j3 = _make_job()
        repo.save(j1)
        repo.save(j2)
        repo.save(j3)

        results = repo.find_by_source_id(sid)
        assert len(results) == 2
        assert all(r.source_id == sid for r in results)

    def test_find_by_source_id_empty(self, repo: StubIngestionJobRepository) -> None:
        results = repo.find_by_source_id(KnowledgeSourceId())
        assert results == []

    def test_find_by_status(self, repo: StubIngestionJobRepository) -> None:
        j1 = _make_job(status=IngestionStatus.RUNNING)
        j2 = _make_job(status=IngestionStatus.RUNNING)
        j3 = _make_job(status=IngestionStatus.COMPLETED)
        repo.save(j1)
        repo.save(j2)
        repo.save(j3)

        results = repo.find_by_status(IngestionStatus.RUNNING)
        assert len(results) == 2
        assert all(r.status == IngestionStatus.RUNNING for r in results)

    def test_find_by_status_empty(self, repo: StubIngestionJobRepository) -> None:
        results = repo.find_by_status(IngestionStatus.FAILED)
        assert results == []

    def test_count(self, repo: StubIngestionJobRepository) -> None:
        assert repo.count() == 0
        repo.save(_make_job())
        assert repo.count() == 1
        repo.save(_make_job())
        assert repo.count() == 2

    def test_save_upsert_semantics(self, repo: StubIngestionJobRepository) -> None:
        jid = IngestionJobId()
        j1 = _make_job(job_id=jid)
        repo.save(j1)
        assert repo.count() == 1

        j2 = _make_job(job_id=jid)
        repo.save(j2)
        assert repo.count() == 1


# =============================================================================
# KnowledgeOutboxPort Stub
# =============================================================================


class StubKnowledgeOutbox:
    """Minimal stub conforming to KnowledgeOutboxPort."""

    def __init__(self) -> None:
        self._events: list[KnowledgeOutboxEvent] = []
        self._published: set[str] = set()

    def append(self, event: KnowledgeOutboxEvent) -> None:
        self._events.append(event)

    def fetch_unpublished(
        self, limit: int = 100
    ) -> list[KnowledgeOutboxEvent]:
        results = [
            e
            for i, e in enumerate(self._events)
            if self._event_key(e, i) not in self._published
        ]
        return results[:limit]

    def mark_published(self, aggregate_id: str) -> None:
        self._published.add(aggregate_id)

    @staticmethod
    def _event_key(event: KnowledgeOutboxEvent, index: int) -> str:
        if isinstance(event, KnowledgeSourceRegistered) or isinstance(event, KnowledgeSourceDeleted):
            return f"source:{event.source_id}"
        if isinstance(event, DocumentIngested) or isinstance(event, DocumentIndexed) or isinstance(event, DocumentDeleted):
            return f"document:{event.document_id}"
        if isinstance(event, ChunkCreated):
            return f"chunk:{event.chunk_id}"
        if isinstance(event, IngestionStarted) or isinstance(event, IngestionCompleted) or isinstance(event, IngestionFailed):
            return f"job:{event.job_id}"
        if isinstance(event, ReindexRequested):
            return f"source:{event.source_id}"
        return f"index:{index}"


class TestKnowledgeOutboxPort:
    """Contract tests for KnowledgeOutboxPort."""

    @pytest.fixture
    def outbox(self) -> StubKnowledgeOutbox:
        return StubKnowledgeOutbox()

    def test_append_and_fetch(self, outbox: StubKnowledgeOutbox) -> None:
        event = _make_source_registered_event()
        outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert unpublished[0].source_id == event.source_id

    def test_mark_published_excludes(self, outbox: StubKnowledgeOutbox) -> None:
        event = _make_source_registered_event()
        outbox.append(event)
        outbox.mark_published(f"source:{event.source_id}")
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 0

    def test_fetch_respects_limit(self, outbox: StubKnowledgeOutbox) -> None:
        for _ in range(10):
            outbox.append(_make_source_registered_event())
        fetched = outbox.fetch_unpublished(limit=3)
        assert len(fetched) == 3

    def test_fetch_default_limit(self, outbox: StubKnowledgeOutbox) -> None:
        for _ in range(200):
            outbox.append(_make_source_registered_event())
        fetched = outbox.fetch_unpublished()
        assert len(fetched) == 100

    def test_fifo_ordering(self, outbox: StubKnowledgeOutbox) -> None:
        ids = [KnowledgeSourceId() for _ in range(5)]
        for sid in ids:
            outbox.append(
                KnowledgeSourceRegistered(
                    source_id=sid,
                    name="src",
                    source_type=SourceType.FILE,
                    location=SourceLocation(value="/p"),
                    classification="public",
                    occurred_at=_now,
                )
            )
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 5
        for i, e in enumerate(unpublished):
            assert e.source_id == ids[i]

    def test_idempotent_mark_published(self, outbox: StubKnowledgeOutbox) -> None:
        event = _make_source_registered_event()
        outbox.append(event)
        key = f"source:{event.source_id}"
        outbox.mark_published(key)
        outbox.mark_published(key)
        outbox.mark_published(key)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 0

    def test_multiple_publish_then_fetch(self, outbox: StubKnowledgeOutbox) -> None:
        events = [_make_source_registered_event() for _ in range(3)]
        for e in events:
            outbox.append(e)

        outbox.mark_published(f"source:{events[0].source_id}")
        outbox.mark_published(f"source:{events[1].source_id}")

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert unpublished[0].source_id == events[2].source_id

    def test_document_event_outbox(self, outbox: StubKnowledgeOutbox) -> None:
        event = _make_document_ingested_event()
        outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], DocumentIngested)
        assert unpublished[0].document_id == event.document_id

    def test_mark_published_document_event(self, outbox: StubKnowledgeOutbox) -> None:
        event = _make_document_ingested_event()
        outbox.append(event)
        outbox.mark_published(f"document:{event.document_id}")
        assert outbox.fetch_unpublished() == []

    def test_mixed_event_types(self, outbox: StubKnowledgeOutbox) -> None:
        outbox.append(_make_source_registered_event())
        outbox.append(_make_document_ingested_event())
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 2
        assert isinstance(unpublished[0], KnowledgeSourceRegistered)
        assert isinstance(unpublished[1], DocumentIngested)

    def test_fetch_unpublished_empty(self, outbox: StubKnowledgeOutbox) -> None:
        assert outbox.fetch_unpublished() == []


# =============================================================================
# KnowledgeClockPort Stubs + Tests
# =============================================================================


class SystemClockStub:
    """Returns real system time — conforms to KnowledgeClockPort."""

    def now(self) -> datetime:
        return datetime.now(tz=timezone.utc)


class FixedClock:
    """Returns a fixed time — conforms to KnowledgeClockPort."""

    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        return self._fixed


class TestKnowledgeClockPort:
    """Contract tests for KnowledgeClockPort."""

    def test_system_clock_returns_utc(self) -> None:
        clock: KnowledgeClockPort = SystemClockStub()
        result = clock.now()
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result).total_seconds() == 0.0

    def test_fixed_clock_returns_configured_time(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        clock: KnowledgeClockPort = FixedClock(dt)
        assert clock.now() == dt

    def test_fixed_clock_is_deterministic(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        clock: KnowledgeClockPort = FixedClock(dt)
        assert clock.now() == clock.now() == dt

    def test_clock_protocol_conformance(self) -> None:
        def use_clock(c: KnowledgeClockPort) -> datetime:
            return c.now()

        assert use_clock(SystemClockStub()) is not None
        assert use_clock(
            FixedClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
        ) is not None


# =============================================================================
# KnowledgeIdGeneratorPort Stubs + Tests
# =============================================================================


class UuidKnowledgeIdGeneratorStub:
    """Generates UUID-based IDs — conforms to KnowledgeIdGeneratorPort."""

    def generate_source_id(self) -> KnowledgeSourceId:
        return KnowledgeSourceId()

    def generate_document_id(self) -> DocumentId:
        return DocumentId()

    def generate_chunk_id(self) -> ChunkId:
        return ChunkId()

    def generate_job_id(self) -> IngestionJobId:
        return IngestionJobId()


class FixedKnowledgeIdGenerator:
    """Tracks calls — conforms to KnowledgeIdGeneratorPort."""

    def __init__(self) -> None:
        self._calls: list[str] = []

    def generate_source_id(self) -> KnowledgeSourceId:
        self._calls.append("source")
        return KnowledgeSourceId()

    def generate_document_id(self) -> DocumentId:
        self._calls.append("document")
        return DocumentId()

    def generate_chunk_id(self) -> ChunkId:
        self._calls.append("chunk")
        return ChunkId()

    def generate_job_id(self) -> IngestionJobId:
        self._calls.append("job")
        return IngestionJobId()

    @property
    def call_count(self) -> int:
        return len(self._calls)

    @property
    def last_call(self) -> str | None:
        return self._calls[-1] if self._calls else None


class TestKnowledgeIdGeneratorPort:
    """Contract tests for KnowledgeIdGeneratorPort."""

    def test_generate_source_id_returns_source_id(self) -> None:
        gen: KnowledgeIdGeneratorPort = UuidKnowledgeIdGeneratorStub()
        result = gen.generate_source_id()
        assert isinstance(result, KnowledgeSourceId)

    def test_generate_document_id_returns_document_id(self) -> None:
        gen: KnowledgeIdGeneratorPort = UuidKnowledgeIdGeneratorStub()
        result = gen.generate_document_id()
        assert isinstance(result, DocumentId)

    def test_generate_chunk_id_returns_chunk_id(self) -> None:
        gen: KnowledgeIdGeneratorPort = UuidKnowledgeIdGeneratorStub()
        result = gen.generate_chunk_id()
        assert isinstance(result, ChunkId)

    def test_generate_job_id_returns_job_id(self) -> None:
        gen: KnowledgeIdGeneratorPort = UuidKnowledgeIdGeneratorStub()
        result = gen.generate_job_id()
        assert isinstance(result, IngestionJobId)

    def test_uuid_generator_unique_source_ids(self) -> None:
        gen: KnowledgeIdGeneratorPort = UuidKnowledgeIdGeneratorStub()
        ids = {gen.generate_source_id() for _ in range(100)}
        assert len(ids) == 100

    def test_fixed_generator_tracks_calls(self) -> None:
        gen: KnowledgeIdGeneratorPort = FixedKnowledgeIdGenerator()
        assert gen.call_count == 0

        gen.generate_source_id()
        assert gen.call_count == 1
        assert gen.last_call == "source"

        gen.generate_document_id()
        assert gen.call_count == 2
        assert gen.last_call == "document"

    def test_generator_protocol_conformance(self) -> None:
        def use_generator(
            g: KnowledgeIdGeneratorPort,
        ) -> tuple[
            KnowledgeSourceId, DocumentId, ChunkId, IngestionJobId
        ]:
            return (
                g.generate_source_id(),
                g.generate_document_id(),
                g.generate_chunk_id(),
                g.generate_job_id(),
            )

        result = use_generator(UuidKnowledgeIdGeneratorStub())
        assert isinstance(result[0], KnowledgeSourceId)
        assert isinstance(result[1], DocumentId)
        assert isinstance(result[2], ChunkId)
        assert isinstance(result[3], IngestionJobId)


# =============================================================================
# Port method signature cross-verification
# =============================================================================


class TestMethodSignatures:
    """Verify that each port method signature matches expectations."""

    def test_source_repo_signatures(self) -> None:
        import inspect

        expected = {
            "save": {"source": KnowledgeSource},
            "find_by_id": {
                "source_id": KnowledgeSourceId,
                "return": KnowledgeSource | None,
            },
            "find_by_status": {"status": SourceStatus, "return": list},
            "find_by_type": {"source_type": SourceType, "return": list},
            "count": {"return": int},
        }
        stub = StubKnowledgeSourceRepository()
        for method_name, expected_params in expected.items():
            method = getattr(stub, method_name)
            sig = inspect.signature(method)
            for param_name in expected_params:
                if param_name == "return":
                    continue
                assert param_name in sig.parameters, (
                    f"{method_name} missing parameter {param_name!r}"
                )

    def test_document_repo_signatures(self) -> None:
        methods = [
            "save",
            "find_by_id",
            "find_by_source_id",
            "find_by_checksum",
            "find_deleted",
            "count",
        ]
        for m in methods:
            assert hasattr(StubKnowledgeDocumentRepository(), m)

    def test_chunk_repo_signatures(self) -> None:
        methods = [
            "save",
            "find_by_id",
            "find_by_document_id",
            "find_by_index_range",
            "count",
        ]
        for m in methods:
            assert hasattr(StubKnowledgeChunkRepository(), m)

    def test_job_repo_signatures(self) -> None:
        methods = [
            "save",
            "find_by_id",
            "find_by_source_id",
            "find_by_status",
            "count",
        ]
        for m in methods:
            assert hasattr(StubIngestionJobRepository(), m)

    def test_outbox_signatures(self) -> None:
        methods = ["append", "fetch_unpublished", "mark_published"]
        for m in methods:
            assert hasattr(StubKnowledgeOutbox(), m)

    def test_clock_signature(self) -> None:
        assert hasattr(SystemClockStub(), "now")
        assert hasattr(FixedClock(datetime.now(tz=timezone.utc)), "now")

    def test_id_generator_signatures(self) -> None:
        gen = UuidKnowledgeIdGeneratorStub()
        assert hasattr(gen, "generate_source_id")
        assert hasattr(gen, "generate_document_id")
        assert hasattr(gen, "generate_chunk_id")
        assert hasattr(gen, "generate_job_id")

    def test_source_repo_method_count(self) -> None:
        port_methods = {
            m
            for m in dir(KnowledgeSourceRepositoryPort)
            if not m.startswith("_")
        }
        assert port_methods == {
            "save",
            "find_by_id",
            "find_by_status",
            "find_by_type",
            "count",
        }

    def test_document_repo_method_count(self) -> None:
        port_methods = {
            m
            for m in dir(KnowledgeDocumentRepositoryPort)
            if not m.startswith("_")
        }
        assert port_methods == {
            "save",
            "find_by_id",
            "find_by_source_id",
            "find_by_checksum",
            "find_deleted",
            "count",
        }

    def test_chunk_repo_method_count(self) -> None:
        port_methods = {
            m
            for m in dir(KnowledgeChunkRepositoryPort)
            if not m.startswith("_")
        }
        assert port_methods == {
            "save",
            "find_by_id",
            "find_by_document_id",
            "find_by_index_range",
            "count",
        }

    def test_job_repo_method_count(self) -> None:
        port_methods = {
            m
            for m in dir(IngestionJobRepositoryPort)
            if not m.startswith("_")
        }
        assert port_methods == {
            "save",
            "find_by_id",
            "find_by_source_id",
            "find_by_status",
            "count",
        }

    def test_outbox_method_count(self) -> None:
        port_methods = {
            m for m in dir(KnowledgeOutboxPort) if not m.startswith("_")
        }
        assert port_methods == {
            "append",
            "fetch_unpublished",
            "mark_published",
        }

    def test_clock_method_count(self) -> None:
        port_methods = {
            m for m in dir(KnowledgeClockPort) if not m.startswith("_")
        }
        assert port_methods == {"now"}

    def test_id_generator_method_count(self) -> None:
        port_methods = {
            m
            for m in dir(KnowledgeIdGeneratorPort)
            if not m.startswith("_")
        }
        assert port_methods == {
            "generate_source_id",
            "generate_document_id",
            "generate_chunk_id",
            "generate_job_id",
        }

    def test_source_repo_nullable_return(self) -> None:
        stub = StubKnowledgeSourceRepository()
        result = stub.find_by_id(KnowledgeSourceId())
        assert result is None

    def test_document_repo_nullable_return(self) -> None:
        stub = StubKnowledgeDocumentRepository()
        result = stub.find_by_id(DocumentId())
        assert result is None

    def test_chunk_repo_nullable_return(self) -> None:
        stub = StubKnowledgeChunkRepository()
        result = stub.find_by_id(ChunkId())
        assert result is None

    def test_job_repo_nullable_return(self) -> None:
        stub = StubIngestionJobRepository()
        result = stub.find_by_id(IngestionJobId())
        assert result is None

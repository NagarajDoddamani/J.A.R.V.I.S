from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from backend.knowledge.domain.exceptions import (
    ChunkContentTooLongError,
    CompletedIngestionRollbackError,
    DeletedDocumentBlocksChunkError,
    DeletedDocumentModificationError,
    DeletedSourceBlocksIngestionError,
    DeletedSourceReactivationError,
    DocumentRequiredForChunkError,
    EmptyChecksumError,
    EmptyChunkContentError,
    EmptyDocumentTitleError,
    EmptyLocationError,
    EmptySourceNameError,
    FailedIngestionCompletionError,
    IngestionErrorMessageRequiredError,
    InvalidClassificationError,
    InvalidDocumentTransitionError,
    InvalidIngestionTransitionError,
    InvalidSourceTransitionError,
    InvalidSourceTypeError,
    NegativeChunkIndexError,
    NonMonotonicChunkIndexError,
    ReindexRequiresActiveSourceError,
    RevisionMonotonicityError,
    SourceNotActiveError,
    SourceRequiredForDocumentError,
)
from backend.knowledge.domain.factory import KnowledgeFactory
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
from backend.knowledge.domain.rules import (
    MAX_CHUNK_CONTENT_LENGTH,
    VALID_CLASSIFICATIONS,
    assert_chunk_content_max_length,
    assert_chunk_content_not_empty,
    assert_chunk_index_monotonic,
    assert_classification_valid,
    assert_document_allows_chunk_creation,
    assert_document_not_deleted,
    assert_document_title_not_empty,
    assert_failure_has_message,
    assert_ingestion_can_transition,
    assert_location_provided,
    assert_reindex_allowed,
    assert_revision_monotonic,
    assert_source_active,
    assert_source_allows_ingestion,
    assert_source_can_transition,
    assert_source_name_not_empty,
    assert_source_not_deleted,
    assert_source_type_valid,
    validate_chunk_creation,
    validate_document_ingestion,
    validate_source_registration,
)

# =============================================================================
# Helpers
# =============================================================================


def make_source(
    status: SourceStatus = SourceStatus.REGISTERED,
    classification: str = "public",
) -> KnowledgeSource:
    loc = SourceLocation(value="/tmp/test")
    return KnowledgeSource(
        source_id=KnowledgeSourceId(),
        name="test-source",
        source_type=SourceType.FILE,
        location=loc,
        classification=classification,
        status=status,
    )


def make_active_source() -> KnowledgeSource:
    s = make_source()
    s.activate()
    return s


def make_document(
    source: KnowledgeSource | None = None,
    status: DocumentStatus = DocumentStatus.PENDING,
) -> KnowledgeDocument:
    src = source or make_active_source()
    return KnowledgeDocument(
        document_id=DocumentId(),
        source_id=src.source_id,
        title="test-doc",
        checksum=DocumentChecksum(value="abc123"),
        classification="public",
        status=status,
    )


def make_job(status: IngestionStatus = IngestionStatus.RUNNING) -> IngestionJob:
    return IngestionJob(
        job_id=IngestionJobId(),
        source_id=KnowledgeSourceId(),
        status=status,
    )


# =============================================================================
# 1. Value Object Tests
# =============================================================================


class TestKnowledgeSourceId:
    def test_creation(self) -> None:
        sid = KnowledgeSourceId()
        assert isinstance(sid.value, UUID)

    def test_str_representation(self) -> None:
        sid = KnowledgeSourceId()
        assert str(sid) == str(sid.value)

    def test_equality(self) -> None:
        val = UUID(int=0)
        a = KnowledgeSourceId(value=val)
        b = KnowledgeSourceId(value=val)
        assert a == b

    def test_inequality(self) -> None:
        assert KnowledgeSourceId() != KnowledgeSourceId()

    def test_immutability(self) -> None:
        sid = KnowledgeSourceId()
        with pytest.raises(AttributeError):
            sid.value = UUID(int=0)


class TestDocumentId:
    def test_creation(self) -> None:
        did = DocumentId()
        assert isinstance(did.value, UUID)

    def test_str(self) -> None:
        did = DocumentId()
        assert str(did) == str(did.value)

    def test_equality(self) -> None:
        val = UUID(int=0)
        assert DocumentId(value=val) == DocumentId(value=val)

    def test_immutability(self) -> None:
        did = DocumentId()
        with pytest.raises(AttributeError):
            did.value = UUID(int=0)


class TestChunkId:
    def test_creation(self) -> None:
        cid = ChunkId()
        assert isinstance(cid.value, UUID)

    def test_str(self) -> None:
        cid = ChunkId()
        assert str(cid) == str(cid.value)

    def test_equality(self) -> None:
        val = UUID(int=0)
        assert ChunkId(value=val) == ChunkId(value=val)

    def test_immutability(self) -> None:
        cid = ChunkId()
        with pytest.raises(AttributeError):
            cid.value = UUID(int=0)


class TestIngestionJobId:
    def test_creation(self) -> None:
        jid = IngestionJobId()
        assert isinstance(jid.value, UUID)

    def test_str(self) -> None:
        jid = IngestionJobId()
        assert str(jid) == str(jid.value)

    def test_equality(self) -> None:
        val = UUID(int=0)
        assert IngestionJobId(value=val) == IngestionJobId(value=val)

    def test_immutability(self) -> None:
        jid = IngestionJobId()
        with pytest.raises(AttributeError):
            jid.value = UUID(int=0)


class TestSourceLocation:
    def test_creation(self) -> None:
        loc = SourceLocation(value="/path/to/source")
        assert loc.value == "/path/to/source"

    def test_empty_raises(self) -> None:
        with pytest.raises(EmptyLocationError):
            SourceLocation(value="")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(EmptyLocationError):
            SourceLocation(value="   ")

    def test_type_error(self) -> None:
        with pytest.raises(TypeError):
            SourceLocation(value=123)  # type: ignore[arg-type]

    def test_equality(self) -> None:
        assert SourceLocation(value="/a") == SourceLocation(value="/a")

    def test_inequality(self) -> None:
        assert SourceLocation(value="/a") != SourceLocation(value="/b")

    def test_str(self) -> None:
        assert str(SourceLocation(value="/path")) == "/path"


class TestDocumentChecksum:
    def test_creation(self) -> None:
        cs = DocumentChecksum(value="abc123")
        assert cs.value == "abc123"

    def test_empty_raises(self) -> None:
        with pytest.raises(EmptyChecksumError):
            DocumentChecksum(value="")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(EmptyChecksumError):
            DocumentChecksum(value="   ")

    def test_type_error(self) -> None:
        with pytest.raises(TypeError):
            DocumentChecksum(value=123)  # type: ignore[arg-type]

    def test_equality(self) -> None:
        assert DocumentChecksum(value="x") == DocumentChecksum(value="x")

    def test_inequality(self) -> None:
        assert DocumentChecksum(value="x") != DocumentChecksum(value="y")

    def test_str(self) -> None:
        assert str(DocumentChecksum(value="hash")) == "hash"


class TestChunkIndex:
    def test_creation(self) -> None:
        ci = ChunkIndex(value=0)
        assert ci.value == 0

    def test_zero_valid(self) -> None:
        ci = ChunkIndex(value=0)
        assert int(ci) == 0

    def test_positive_valid(self) -> None:
        ci = ChunkIndex(value=5)
        assert ci.value == 5

    def test_negative_raises(self) -> None:
        with pytest.raises(NegativeChunkIndexError, match="non-negative"):
            ChunkIndex(value=-1)

    def test_type_error(self) -> None:
        with pytest.raises(TypeError):
            ChunkIndex(value="0")  # type: ignore[arg-type]

    def test_equality(self) -> None:
        assert ChunkIndex(value=1) == ChunkIndex(value=1)

    def test_inequality(self) -> None:
        assert ChunkIndex(value=1) != ChunkIndex(value=2)

    def test_int_conversion(self) -> None:
        assert int(ChunkIndex(value=42)) == 42


class TestChunkContent:
    def test_creation(self) -> None:
        cc = ChunkContent(value="hello")
        assert cc.value == "hello"

    def test_empty_raises(self) -> None:
        with pytest.raises(EmptyChunkContentError):
            ChunkContent(value="")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(EmptyChunkContentError):
            ChunkContent(value="   ")

    def test_type_error(self) -> None:
        with pytest.raises(TypeError):
            ChunkContent(value=123)  # type: ignore[arg-type]

    def test_equality(self) -> None:
        assert ChunkContent(value="a") == ChunkContent(value="a")

    def test_inequality(self) -> None:
        assert ChunkContent(value="a") != ChunkContent(value="b")

    def test_len(self) -> None:
        assert len(ChunkContent(value="abc")) == 3

    def test_max_length(self) -> None:
        long = "x" * (MAX_CHUNK_CONTENT_LENGTH + 1)
        cc = ChunkContent(value=long)
        with pytest.raises(ChunkContentTooLongError):
            assert_chunk_content_max_length(cc)


# =============================================================================
# 2. Enum Tests
# =============================================================================


class TestSourceType:
    def test_file(self) -> None:
        assert SourceType.FILE.value == "file"

    def test_directory(self) -> None:
        assert SourceType.DIRECTORY.value == "directory"

    def test_url(self) -> None:
        assert SourceType.URL.value == "url"

    def test_manual(self) -> None:
        assert SourceType.MANUAL.value == "manual"

    def test_memory_export(self) -> None:
        assert SourceType.MEMORY_EXPORT.value == "memory_export"


class TestSourceStatus:
    def test_registered(self) -> None:
        assert SourceStatus.REGISTERED.value == "registered"

    def test_active(self) -> None:
        assert SourceStatus.ACTIVE.value == "active"

    def test_disabled(self) -> None:
        assert SourceStatus.DISABLED.value == "disabled"

    def test_deleted(self) -> None:
        assert SourceStatus.DELETED.value == "deleted"


class TestDocumentStatus:
    def test_pending(self) -> None:
        assert DocumentStatus.PENDING.value == "pending"

    def test_ingested(self) -> None:
        assert DocumentStatus.INGESTED.value == "ingested"

    def test_indexed(self) -> None:
        assert DocumentStatus.INDEXED.value == "indexed"

    def test_deleted(self) -> None:
        assert DocumentStatus.DELETED.value == "deleted"


class TestIngestionStatus:
    def test_queued(self) -> None:
        assert IngestionStatus.QUEUED.value == "queued"

    def test_running(self) -> None:
        assert IngestionStatus.RUNNING.value == "running"

    def test_completed(self) -> None:
        assert IngestionStatus.COMPLETED.value == "completed"

    def test_failed(self) -> None:
        assert IngestionStatus.FAILED.value == "failed"


# =============================================================================
# 3. Entity: KnowledgeSource Tests
# =============================================================================


class TestKnowledgeSource:
    def test_creation_defaults(self) -> None:
        s = KnowledgeSource()
        assert isinstance(s.source_id, KnowledgeSourceId)
        assert s.name == ""
        assert s.source_type == SourceType.FILE
        assert s.location is None
        assert s.classification == "public"
        assert s.status == SourceStatus.REGISTERED
        assert isinstance(s.created_at, datetime)
        assert s.updated_at is None
        assert s.deleted_at is None
        assert s.events == []

    def test_custom_creation(self) -> None:
        sid = KnowledgeSourceId()
        loc = SourceLocation(value="/custom")
        dt = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        s = KnowledgeSource(
            source_id=sid,
            name="custom-src",
            source_type=SourceType.URL,
            location=loc,
            classification="sensitive",
            status=SourceStatus.ACTIVE,
            created_at=dt,
            updated_at=dt,
            deleted_at=None,
        )
        assert s.source_id == sid
        assert s.name == "custom-src"
        assert s.source_type == SourceType.URL
        assert s.location == loc
        assert s.classification == "sensitive"
        assert s.status == SourceStatus.ACTIVE
        assert s.created_at == dt
        assert s.updated_at == dt

    def test_activate_transition(self) -> None:
        s = make_source(SourceStatus.REGISTERED)
        s.activate()
        assert s.status == SourceStatus.ACTIVE
        assert s.updated_at is not None

    def test_disable_transition(self) -> None:
        s = make_source(SourceStatus.ACTIVE)
        s.disable()
        assert s.status == SourceStatus.DISABLED

    def test_delete_from_active(self) -> None:
        s = make_source(SourceStatus.ACTIVE)
        s.delete()
        assert s.status == SourceStatus.DELETED
        assert s.deleted_at is not None
        assert s.updated_at is not None

    def test_delete_from_disabled(self) -> None:
        s = make_source(SourceStatus.DISABLED)
        s.delete()
        assert s.status == SourceStatus.DELETED

    def test_is_active_true(self) -> None:
        s = make_source(SourceStatus.ACTIVE)
        assert s.is_active is True

    def test_is_active_false(self) -> None:
        s = make_source(SourceStatus.REGISTERED)
        assert s.is_active is False

    def test_is_deleted_true(self) -> None:
        s = make_source(SourceStatus.ACTIVE)
        s.delete()
        assert s.is_deleted is True

    def test_is_deleted_false(self) -> None:
        s = make_source()
        assert s.is_deleted is False

    def test_delete_emits_event(self) -> None:
        s = make_source(SourceStatus.ACTIVE)
        s.delete()
        assert len(s.events) == 1
        event = s.events[0]
        assert isinstance(event, KnowledgeSourceDeleted)
        assert event.source_id == s.source_id

    def test_activate_already_active(self) -> None:
        s = make_source(SourceStatus.ACTIVE)
        with pytest.raises(InvalidSourceTransitionError):
            s.activate()

    def test_disable_from_registered(self) -> None:
        s = make_source(SourceStatus.REGISTERED)
        with pytest.raises(InvalidSourceTransitionError):
            s.disable()

    def test_delete_deleted_source(self) -> None:
        s = make_source(SourceStatus.ACTIVE)
        s.delete()
        with pytest.raises(InvalidSourceTransitionError):
            s.delete()

    def test_activate_deleted_source(self) -> None:
        s = make_source(SourceStatus.ACTIVE)
        s.delete()
        with pytest.raises(DeletedSourceReactivationError):
            s.activate()

    def test_repr(self) -> None:
        s = make_source()
        r = repr(s)
        assert "KnowledgeSource" in r
        assert s.name in r


# =============================================================================
# 4. Entity: KnowledgeDocument Tests
# =============================================================================


class TestKnowledgeDocument:
    def test_creation_defaults(self) -> None:
        doc = KnowledgeDocument()
        assert isinstance(doc.document_id, DocumentId)
        assert doc.source_id is None
        assert doc.title == ""
        assert doc.checksum is None
        assert doc.classification == "public"
        assert doc.status == DocumentStatus.PENDING
        assert doc.revision == 1
        assert isinstance(doc.created_at, datetime)
        assert doc.updated_at is None
        assert doc.deleted_at is None
        assert doc.events == []

    def test_custom_creation(self) -> None:
        did = DocumentId()
        sid = KnowledgeSourceId()
        cs = DocumentChecksum(value="xyz")
        doc = KnowledgeDocument(
            document_id=did,
            source_id=sid,
            title="my-doc",
            checksum=cs,
            classification="sensitive",
            status=DocumentStatus.INGESTED,
            revision=3,
        )
        assert doc.document_id == did
        assert doc.source_id == sid
        assert doc.title == "my-doc"
        assert doc.checksum == cs
        assert doc.classification == "sensitive"
        assert doc.status == DocumentStatus.INGESTED
        assert doc.revision == 3

    def test_mark_indexed(self) -> None:
        doc = make_document()
        doc.mark_indexed()
        assert doc.status == DocumentStatus.INDEXED
        assert doc.updated_at is not None

    def test_delete(self) -> None:
        doc = make_document()
        doc.delete()
        assert doc.status == DocumentStatus.DELETED
        assert doc.deleted_at is not None

    def test_is_deleted_true(self) -> None:
        doc = make_document()
        doc.delete()
        assert doc.is_deleted is True

    def test_is_deleted_false(self) -> None:
        doc = make_document()
        assert doc.is_deleted is False

    def test_mark_indexed_emits_event(self) -> None:
        doc = make_document()
        doc.mark_indexed()
        assert len(doc.events) == 1
        assert isinstance(doc.events[0], DocumentIndexed)
        assert doc.events[0].document_id == doc.document_id

    def test_delete_emits_event(self) -> None:
        doc = make_document()
        doc.delete()
        assert len(doc.events) == 1
        assert isinstance(doc.events[0], DocumentDeleted)
        assert doc.events[0].document_id == doc.document_id

    def test_mark_indexed_twice_raises(self) -> None:
        doc = make_document()
        doc.mark_indexed()
        with pytest.raises(InvalidDocumentTransitionError):
            doc.mark_indexed()

    def test_delete_twice_raises(self) -> None:
        doc = make_document()
        doc.delete()
        with pytest.raises(InvalidDocumentTransitionError):
            doc.delete()

    def test_delete_from_ingested(self) -> None:
        doc = make_document(status=DocumentStatus.INGESTED)
        doc.delete()
        assert doc.status == DocumentStatus.DELETED

    def test_repr(self) -> None:
        doc = make_document()
        r = repr(doc)
        assert "KnowledgeDocument" in r


# =============================================================================
# 5. Entity: KnowledgeChunk Tests
# =============================================================================


class TestKnowledgeChunk:
    def test_creation_defaults(self) -> None:
        chunk = KnowledgeChunk()
        assert isinstance(chunk.chunk_id, ChunkId)
        assert chunk.document_id is None
        assert chunk.chunk_index is None
        assert chunk.content is None
        assert chunk.classification == "public"
        assert isinstance(chunk.created_at, datetime)

    def test_custom_creation(self) -> None:
        cid = ChunkId()
        did = DocumentId()
        ci = ChunkIndex(value=0)
        cc = ChunkContent(value="test content")
        chunk = KnowledgeChunk(
            chunk_id=cid,
            document_id=did,
            chunk_index=ci,
            content=cc,
            classification="sensitive",
        )
        assert chunk.chunk_id == cid
        assert chunk.document_id == did
        assert chunk.chunk_index == ci
        assert chunk.content == cc
        assert chunk.classification == "sensitive"

    def test_repr(self) -> None:
        chunk = KnowledgeChunk()
        r = repr(chunk)
        assert "KnowledgeChunk" in r


# =============================================================================
# 6. Entity: IngestionJob Tests
# =============================================================================


class TestIngestionJob:
    def test_creation_defaults(self) -> None:
        job = IngestionJob()
        assert isinstance(job.job_id, IngestionJobId)
        assert job.source_id is None
        assert job.status == IngestionStatus.RUNNING
        assert isinstance(job.started_at, datetime)
        assert job.completed_at is None
        assert job.error_message is None
        assert job.events == []

    def test_custom_creation(self) -> None:
        jid = IngestionJobId()
        sid = KnowledgeSourceId()
        job = IngestionJob(
            job_id=jid,
            source_id=sid,
            status=IngestionStatus.QUEUED,
        )
        assert job.job_id == jid
        assert job.source_id == sid
        assert job.status == IngestionStatus.QUEUED

    def test_complete(self) -> None:
        job = make_job(IngestionStatus.RUNNING)
        job.complete()
        assert job.status == IngestionStatus.COMPLETED
        assert job.completed_at is not None

    def test_complete_emits_event(self) -> None:
        job = make_job(IngestionStatus.RUNNING)
        job.complete()
        assert len(job.events) == 1
        assert isinstance(job.events[0], IngestionCompleted)
        assert job.events[0].job_id == job.job_id

    def test_fail(self) -> None:
        job = make_job(IngestionStatus.RUNNING)
        job.fail("corrupt file")
        assert job.status == IngestionStatus.FAILED
        assert job.error_message == "corrupt file"
        assert job.completed_at is not None

    def test_fail_emits_event(self) -> None:
        job = make_job(IngestionStatus.RUNNING)
        job.fail("timeout")
        assert len(job.events) == 1
        assert isinstance(job.events[0], IngestionFailed)
        assert job.events[0].job_id == job.job_id
        assert job.events[0].error_message == "timeout"

    def test_fail_empty_message_raises(self) -> None:
        job = make_job(IngestionStatus.RUNNING)
        with pytest.raises(IngestionErrorMessageRequiredError):
            job.fail("")

    def test_fail_whitespace_message_raises(self) -> None:
        job = make_job(IngestionStatus.RUNNING)
        with pytest.raises(IngestionErrorMessageRequiredError):
            job.fail("   ")

    def test_complete_already_completed_raises(self) -> None:
        job = make_job(IngestionStatus.RUNNING)
        job.complete()
        with pytest.raises(InvalidIngestionTransitionError):
            job.complete()

    def test_fail_already_completed_raises(self) -> None:
        job = make_job(IngestionStatus.RUNNING)
        job.complete()
        with pytest.raises(InvalidIngestionTransitionError):
            job.fail("error")

    def test_complete_failed_job_raises(self) -> None:
        job = make_job(IngestionStatus.RUNNING)
        job.fail("error")
        with pytest.raises(FailedIngestionCompletionError):
            job.complete()

    def test_complete_queued_job_raises(self) -> None:
        job = IngestionJob(status=IngestionStatus.QUEUED)
        with pytest.raises(InvalidIngestionTransitionError):
            job.complete()

    def test_repr(self) -> None:
        job = make_job()
        r = repr(job)
        assert "IngestionJob" in r


# =============================================================================
# 7. Event Tests
# =============================================================================


class TestEvents:
    def test_knowledge_source_registered_payload(self) -> None:
        sid = KnowledgeSourceId()
        loc = SourceLocation(value="/path")
        now = datetime.now(tz=timezone.utc)
        e = KnowledgeSourceRegistered(
            source_id=sid,
            name="src",
            source_type=SourceType.FILE,
            location=loc,
            classification="public",
            occurred_at=now,
        )
        assert e.source_id == sid
        assert e.name == "src"
        assert e.source_type == SourceType.FILE
        assert e.location == loc
        assert e.classification == "public"
        assert e.occurred_at == now

    def test_knowledge_source_deleted_payload(self) -> None:
        sid = KnowledgeSourceId()
        now = datetime.now(tz=timezone.utc)
        e = KnowledgeSourceDeleted(source_id=sid, occurred_at=now)
        assert e.source_id == sid
        assert e.occurred_at == now

    def test_document_ingested_payload(self) -> None:
        did = DocumentId()
        sid = KnowledgeSourceId()
        cs = DocumentChecksum(value="abc")
        now = datetime.now(tz=timezone.utc)
        e = DocumentIngested(
            document_id=did,
            source_id=sid,
            title="doc",
            checksum=cs,
            classification="public",
            occurred_at=now,
        )
        assert e.document_id == did
        assert e.source_id == sid
        assert e.title == "doc"
        assert e.checksum == cs
        assert e.occurred_at == now

    def test_document_indexed_payload(self) -> None:
        did = DocumentId()
        now = datetime.now(tz=timezone.utc)
        e = DocumentIndexed(document_id=did, occurred_at=now)
        assert e.document_id == did
        assert e.occurred_at == now

    def test_document_deleted_payload(self) -> None:
        did = DocumentId()
        now = datetime.now(tz=timezone.utc)
        e = DocumentDeleted(document_id=did, occurred_at=now)
        assert e.document_id == did
        assert e.occurred_at == now

    def test_chunk_created_payload(self) -> None:
        cid = ChunkId()
        did = DocumentId()
        ci = ChunkIndex(value=0)
        now = datetime.now(tz=timezone.utc)
        e = ChunkCreated(
            chunk_id=cid,
            document_id=did,
            chunk_index=ci,
            occurred_at=now,
        )
        assert e.chunk_id == cid
        assert e.document_id == did
        assert e.chunk_index == ci
        assert e.occurred_at == now

    def test_reindex_requested_payload(self) -> None:
        sid = KnowledgeSourceId()
        now = datetime.now(tz=timezone.utc)
        e = ReindexRequested(source_id=sid, occurred_at=now)
        assert e.source_id == sid
        assert e.occurred_at == now

    def test_ingestion_started_payload(self) -> None:
        jid = IngestionJobId()
        sid = KnowledgeSourceId()
        now = datetime.now(tz=timezone.utc)
        e = IngestionStarted(
            job_id=jid,
            source_id=sid,
            occurred_at=now,
        )
        assert e.job_id == jid
        assert e.source_id == sid
        assert e.occurred_at == now

    def test_ingestion_completed_payload(self) -> None:
        jid = IngestionJobId()
        now = datetime.now(tz=timezone.utc)
        e = IngestionCompleted(job_id=jid, occurred_at=now)
        assert e.job_id == jid
        assert e.occurred_at == now

    def test_ingestion_failed_payload(self) -> None:
        jid = IngestionJobId()
        now = datetime.now(tz=timezone.utc)
        e = IngestionFailed(
            job_id=jid,
            error_message="disk full",
            occurred_at=now,
        )
        assert e.job_id == jid
        assert e.error_message == "disk full"
        assert e.occurred_at == now

    def test_events_are_immutable(self) -> None:
        sid = KnowledgeSourceId()
        now = datetime.now(tz=timezone.utc)
        e = KnowledgeSourceRegistered(
            source_id=sid,
            name="src",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/p"),
            classification="public",
            occurred_at=now,
        )
        with pytest.raises(AttributeError):
            e.name = "changed"  # type: ignore[misc]


# =============================================================================
# 8. Rule Tests
# =============================================================================


class TestSourceNameRule:
    def test_non_empty_valid(self) -> None:
        assert_source_name_not_empty("my-source")

    def test_empty_raises(self) -> None:
        with pytest.raises(EmptySourceNameError):
            assert_source_name_not_empty("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(EmptySourceNameError):
            assert_source_name_not_empty("   ")


class TestLocationRule:
    def test_location_provided_valid(self) -> None:
        assert_location_provided(SourceLocation(value="/path"))

    def test_location_none_raises(self) -> None:
        with pytest.raises(EmptyLocationError):
            assert_location_provided(None)


class TestSourceTypeRule:
    def test_valid_string(self) -> None:
        assert_source_type_valid("file")

    def test_valid_enum(self) -> None:
        assert_source_type_valid(SourceType.FILE)

    def test_invalid_string_raises(self) -> None:
        with pytest.raises(InvalidSourceTypeError):
            assert_source_type_valid("INVALID_TYPE")


class TestClassificationRule:
    def test_valid_classification(self) -> None:
        for c in VALID_CLASSIFICATIONS:
            assert_classification_valid(c)

    def test_invalid_classification_raises(self) -> None:
        with pytest.raises(InvalidClassificationError):
            assert_classification_valid("invalid")


class TestDeletedSourceRules:
    def test_not_deleted_passes(self) -> None:
        s = make_source(SourceStatus.ACTIVE)
        assert_source_not_deleted(s)

    def test_deleted_raises(self) -> None:
        s = make_source(SourceStatus.ACTIVE)
        s.delete()
        with pytest.raises(DeletedSourceReactivationError):
            assert_source_not_deleted(s)


class TestSourceActiveRule:
    def test_active_source_passes(self) -> None:
        s = make_source(SourceStatus.ACTIVE)
        assert_source_active(s)

    def test_non_active_raises(self) -> None:
        s = make_source(SourceStatus.REGISTERED)
        with pytest.raises(SourceNotActiveError):
            assert_source_active(s)


class TestDocumentTitleRule:
    def test_non_empty_valid(self) -> None:
        assert_document_title_not_empty("my-doc")

    def test_empty_raises(self) -> None:
        with pytest.raises(EmptyDocumentTitleError):
            assert_document_title_not_empty("")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(EmptyDocumentTitleError):
            assert_document_title_not_empty("   ")


class TestChecksumRule:
    def test_checksum_passes(self) -> None:
        assert_revision_monotonic(1, 1)

    def test_revision_mismatch_raises(self) -> None:
        with pytest.raises(RevisionMonotonicityError):
            assert_revision_monotonic(2, 1)


class TestDocumentNotDeletedRule:
    def test_not_deleted_passes(self) -> None:
        doc = make_document()
        assert_document_not_deleted(doc)

    def test_deleted_raises(self) -> None:
        doc = make_document()
        doc.delete()
        with pytest.raises(DeletedDocumentModificationError):
            assert_document_not_deleted(doc)


class TestChunkContentRule:
    def test_non_empty_valid(self) -> None:
        cc = ChunkContent(value="valid content")
        assert_chunk_content_not_empty(cc)

    def test_empty_raises(self) -> None:
        with pytest.raises(EmptyChunkContentError):
            ChunkContent(value="")

    def test_max_length_exceeded(self) -> None:
        long = "x" * (MAX_CHUNK_CONTENT_LENGTH + 1)
        cc = ChunkContent(value=long)
        with pytest.raises(ChunkContentTooLongError):
            assert_chunk_content_max_length(cc)

    def test_max_length_boundary(self) -> None:
        exact = "x" * MAX_CHUNK_CONTENT_LENGTH
        cc = ChunkContent(value=exact)
        assert_chunk_content_max_length(cc)


class TestChunkIndexMonotonicRule:
    def test_first_index_valid(self) -> None:
        ci = ChunkIndex(value=0)
        assert_chunk_index_monotonic(ci, [])  # no existing

    def test_increasing_valid(self) -> None:
        ci = ChunkIndex(value=2)
        assert_chunk_index_monotonic(ci, [ChunkIndex(value=0), ChunkIndex(value=1)])

    def test_equal_index_raises(self) -> None:
        ci = ChunkIndex(value=1)
        with pytest.raises(NonMonotonicChunkIndexError):
            assert_chunk_index_monotonic(ci, [ChunkIndex(value=0), ChunkIndex(value=1)])

    def test_decreasing_index_raises(self) -> None:
        ci = ChunkIndex(value=0)
        with pytest.raises(NonMonotonicChunkIndexError):
            assert_chunk_index_monotonic(ci, [ChunkIndex(value=1)])


class TestIngestionTransitionRules:
    def test_queued_to_running_valid(self) -> None:
        assert_ingestion_can_transition(IngestionStatus.QUEUED, IngestionStatus.RUNNING)

    def test_running_to_completed_valid(self) -> None:
        assert_ingestion_can_transition(IngestionStatus.RUNNING, IngestionStatus.COMPLETED)

    def test_running_to_failed_valid(self) -> None:
        assert_ingestion_can_transition(IngestionStatus.RUNNING, IngestionStatus.FAILED)

    def test_completed_to_running_raises(self) -> None:
        with pytest.raises(CompletedIngestionRollbackError):
            assert_ingestion_can_transition(IngestionStatus.COMPLETED, IngestionStatus.RUNNING)

    def test_failed_to_completed_raises(self) -> None:
        with pytest.raises(FailedIngestionCompletionError):
            assert_ingestion_can_transition(IngestionStatus.FAILED, IngestionStatus.COMPLETED)

    def test_queued_to_completed_raises(self) -> None:
        with pytest.raises(InvalidIngestionTransitionError):
            assert_ingestion_can_transition(IngestionStatus.QUEUED, IngestionStatus.COMPLETED)


class TestFailureMessageRule:
    def test_non_empty_message_valid(self) -> None:
        assert_failure_has_message("error occurred")

    def test_empty_message_raises(self) -> None:
        with pytest.raises(IngestionErrorMessageRequiredError):
            assert_failure_has_message("")

    def test_whitespace_message_raises(self) -> None:
        with pytest.raises(IngestionErrorMessageRequiredError):
            assert_failure_has_message("   ")


class TestSourceAllowsIngestionRule:
    def test_active_allows(self) -> None:
        s = make_source(SourceStatus.ACTIVE)
        assert_source_allows_ingestion(s)

    def test_deleted_blocks(self) -> None:
        s = make_source(SourceStatus.ACTIVE)
        s.delete()
        with pytest.raises(DeletedSourceBlocksIngestionError):
            assert_source_allows_ingestion(s)


class TestDocumentAllowsChunkCreationRule:
    def test_not_deleted_allows(self) -> None:
        doc = make_document()
        assert_document_allows_chunk_creation(doc)

    def test_deleted_blocks(self) -> None:
        doc = make_document()
        doc.delete()
        with pytest.raises(DeletedDocumentBlocksChunkError):
            assert_document_allows_chunk_creation(doc)


class TestReindexAllowedRule:
    def test_active_allows(self) -> None:
        s = make_source(SourceStatus.ACTIVE)
        assert_reindex_allowed(s)

    def test_inactive_raises(self) -> None:
        s = make_source(SourceStatus.REGISTERED)
        with pytest.raises(ReindexRequiresActiveSourceError):
            assert_reindex_allowed(s)


class TestCompositeValidators:
    def test_validate_source_registration_happy(self) -> None:
        validate_source_registration(
            name="test",
            source_type=SourceType.FILE,
            location=SourceLocation(value="/p"),
            classification="public",
        )

    def test_validate_source_registration_empty_name(self) -> None:
        with pytest.raises(EmptySourceNameError):
            validate_source_registration(
                name="",
                source_type=SourceType.FILE,
                location=SourceLocation(value="/p"),
                classification="public",
            )

    def test_validate_document_ingestion_happy(self) -> None:
        s = make_active_source()
        validate_document_ingestion(
            source=s,
            title="doc",
            checksum=DocumentChecksum(value="abc"),
            classification="public",
        )

    def test_validate_document_ingestion_deleted_source(self) -> None:
        s = make_active_source()
        s.delete()
        with pytest.raises(SourceNotActiveError):
            validate_document_ingestion(
                source=s,
                title="doc",
                checksum=DocumentChecksum(value="abc"),
                classification="public",
            )

    def test_validate_chunk_creation_happy(self) -> None:
        doc = make_document()
        cc = ChunkContent(value="content")
        validate_chunk_creation(document=doc, content=cc, existing_indices=[])

    def test_validate_chunk_creation_deleted_document(self) -> None:
        doc = make_document()
        doc.delete()
        cc = ChunkContent(value="content")
        with pytest.raises(DeletedDocumentModificationError):
            validate_chunk_creation(document=doc, content=cc, existing_indices=[])


# =============================================================================
# 9. Factory Tests
# =============================================================================


class TestRegisterSource:
    def test_happy_path(self) -> None:
        source, event = KnowledgeFactory.register_source(
            name="my-source",
            source_type=SourceType.FILE,
            location="/data/files",
            classification="public",
        )
        assert isinstance(source, KnowledgeSource)
        assert source.name == "my-source"
        assert source.source_type == SourceType.FILE
        assert source.location == SourceLocation(value="/data/files")
        assert source.classification == "public"
        assert source.status == SourceStatus.REGISTERED

    def test_string_source_type(self) -> None:
        source, event = KnowledgeFactory.register_source(
            name="s",
            source_type="file",
            location="/p",
            classification="public",
        )
        assert source.source_type == SourceType.FILE

    def test_string_location(self) -> None:
        source, event = KnowledgeFactory.register_source(
            name="s",
            source_type=SourceType.FILE,
            location="/path",
            classification="public",
        )
        assert source.location == SourceLocation(value="/path")

    def test_emits_event(self) -> None:
        source, event = KnowledgeFactory.register_source(
            name="my-source",
            source_type=SourceType.FILE,
            location="/data",
            classification="public",
        )
        assert isinstance(event, KnowledgeSourceRegistered)
        assert event.source_id == source.source_id
        assert event.name == "my-source"
        assert event.source_type == SourceType.FILE
        assert event.location == SourceLocation(value="/data")
        assert event.classification == "public"

    def test_empty_name_raises(self) -> None:
        with pytest.raises(EmptySourceNameError):
            KnowledgeFactory.register_source(
                name="",
                source_type=SourceType.FILE,
                location="/p",
                classification="public",
            )

    def test_invalid_source_type_raises(self) -> None:
        with pytest.raises(InvalidSourceTypeError):
            KnowledgeFactory.register_source(
                name="s",
                source_type="INVALID",
                location="/p",
                classification="public",
            )

    def test_invalid_classification_raises(self) -> None:
        with pytest.raises(InvalidClassificationError):
            KnowledgeFactory.register_source(
                name="s",
                source_type=SourceType.FILE,
                location="/p",
                classification="invalid",
            )

    def test_empty_location_raises(self) -> None:
        with pytest.raises(EmptyLocationError):
            KnowledgeFactory.register_source(
                name="s",
                source_type=SourceType.FILE,
                location="",
                classification="public",
            )


class TestIngestDocument:
    def test_happy_path(self) -> None:
        src = make_active_source()
        doc, event = KnowledgeFactory.ingest_document(
            source=src,
            title="my-doc",
            checksum="abc123",
            classification="public",
        )
        assert isinstance(doc, KnowledgeDocument)
        assert doc.title == "my-doc"
        assert doc.checksum == DocumentChecksum(value="abc123")
        assert doc.classification == "public"
        assert doc.status == DocumentStatus.PENDING
        assert doc.revision == 1
        assert doc.source_id == src.source_id

    def test_checksum_object(self) -> None:
        src = make_active_source()
        cs = DocumentChecksum(value="xyz")
        doc, event = KnowledgeFactory.ingest_document(
            source=src,
            title="doc",
            checksum=cs,
            classification="public",
        )
        assert doc.checksum == cs

    def test_emits_event(self) -> None:
        src = make_active_source()
        doc, event = KnowledgeFactory.ingest_document(
            source=src,
            title="my-doc",
            checksum="abc",
            classification="public",
        )
        assert isinstance(event, DocumentIngested)
        assert event.document_id == doc.document_id
        assert event.source_id == src.source_id
        assert event.title == "my-doc"
        assert event.checksum == doc.checksum
        assert event.classification == "public"

    def test_deleted_source_raises(self) -> None:
        src = make_active_source()
        src.delete()
        with pytest.raises(SourceNotActiveError):
            KnowledgeFactory.ingest_document(
                source=src,
                title="doc",
                checksum="abc",
                classification="public",
            )

    def test_inactive_source_raises(self) -> None:
        src = make_source(SourceStatus.REGISTERED)
        with pytest.raises(SourceNotActiveError):
            KnowledgeFactory.ingest_document(
                source=src,
                title="doc",
                checksum="abc",
                classification="public",
            )

    def test_empty_title_raises(self) -> None:
        src = make_active_source()
        with pytest.raises(EmptyDocumentTitleError):
            KnowledgeFactory.ingest_document(
                source=src,
                title="",
                checksum="abc",
                classification="public",
            )

    def test_empty_checksum_raises(self) -> None:
        src = make_active_source()
        with pytest.raises(EmptyChecksumError):
            KnowledgeFactory.ingest_document(
                source=src,
                title="doc",
                checksum="",
                classification="public",
            )

    def test_invalid_classification_raises(self) -> None:
        src = make_active_source()
        with pytest.raises(InvalidClassificationError):
            KnowledgeFactory.ingest_document(
                source=src,
                title="doc",
                checksum="abc",
                classification="invalid",
            )


class TestCreateChunk:
    def test_happy_path(self) -> None:
        doc = make_document()
        chunk, event = KnowledgeFactory.create_chunk(
            document=doc,
            chunk_index=0,
            content="test content",
            classification="public",
        )
        assert isinstance(chunk, KnowledgeChunk)
        assert chunk.document_id == doc.document_id
        assert chunk.chunk_index == ChunkIndex(value=0)
        assert chunk.content == ChunkContent(value="test content")
        assert chunk.classification == "public"

    def test_int_chunk_index(self) -> None:
        doc = make_document()
        chunk, event = KnowledgeFactory.create_chunk(
            document=doc,
            chunk_index=5,
            content="content",
            classification="public",
        )
        assert chunk.chunk_index == ChunkIndex(value=5)

    def test_string_content(self) -> None:
        doc = make_document()
        chunk, event = KnowledgeFactory.create_chunk(
            document=doc,
            chunk_index=0,
            content="hello",
            classification="public",
        )
        assert chunk.content == ChunkContent(value="hello")

    def test_chunk_index_object(self) -> None:
        doc = make_document()
        ci = ChunkIndex(value=1)
        chunk, event = KnowledgeFactory.create_chunk(
            document=doc,
            chunk_index=ci,
            content="content",
            classification="public",
        )
        assert chunk.chunk_index == ci

    def test_emits_event(self) -> None:
        doc = make_document()
        chunk, event = KnowledgeFactory.create_chunk(
            document=doc,
            chunk_index=0,
            content="content",
            classification="public",
        )
        assert isinstance(event, ChunkCreated)
        assert event.chunk_id == chunk.chunk_id
        assert event.document_id == doc.document_id
        assert event.chunk_index == chunk.chunk_index

    def test_empty_content_raises(self) -> None:
        doc = make_document()
        with pytest.raises(EmptyChunkContentError):
            KnowledgeFactory.create_chunk(
                document=doc,
                chunk_index=0,
                content="",
                classification="public",
            )

    def test_negative_index_raises(self) -> None:
        doc = make_document()
        with pytest.raises(NegativeChunkIndexError):
            KnowledgeFactory.create_chunk(
                document=doc,
                chunk_index=-1,
                content="content",
                classification="public",
            )

    def test_non_monotonic_index_raises(self) -> None:
        doc = make_document()
        existing = [ChunkIndex(value=0)]
        with pytest.raises(NonMonotonicChunkIndexError):
            KnowledgeFactory.create_chunk(
                document=doc,
                chunk_index=0,
                content="content",
                classification="public",
                existing_indices=existing,
            )

    def test_deleted_document_raises(self) -> None:
        doc = make_document()
        doc.delete()
        with pytest.raises(DeletedDocumentModificationError):
            KnowledgeFactory.create_chunk(
                document=doc,
                chunk_index=0,
                content="content",
                classification="public",
            )

    def test_invalid_classification_raises(self) -> None:
        doc = make_document()
        with pytest.raises(InvalidClassificationError):
            KnowledgeFactory.create_chunk(
                document=doc,
                chunk_index=0,
                content="content",
                classification="invalid",
            )


class TestRequestReindex:
    def test_happy_path(self) -> None:
        src = make_active_source()
        event = KnowledgeFactory.request_reindex(source=src)
        assert isinstance(event, ReindexRequested)
        assert event.source_id == src.source_id

    def test_inactive_source_raises(self) -> None:
        src = make_source(SourceStatus.REGISTERED)
        with pytest.raises(ReindexRequiresActiveSourceError):
            KnowledgeFactory.request_reindex(source=src)


class TestStartIngestion:
    def test_happy_path(self) -> None:
        src = make_active_source()
        job, event = KnowledgeFactory.start_ingestion(source=src)
        assert isinstance(job, IngestionJob)
        assert job.source_id == src.source_id
        assert job.status == IngestionStatus.RUNNING

    def test_emits_event(self) -> None:
        src = make_active_source()
        job, event = KnowledgeFactory.start_ingestion(source=src)
        assert isinstance(event, IngestionStarted)
        assert event.job_id == job.job_id
        assert event.source_id == src.source_id

    def test_inactive_source_raises(self) -> None:
        src = make_source(SourceStatus.REGISTERED)
        with pytest.raises(SourceNotActiveError):
            KnowledgeFactory.start_ingestion(source=src)


# =============================================================================
# 10. Cross-Entity Validations
# =============================================================================


class TestCrossEntityValidations:
    def test_document_requires_source(self) -> None:
        with pytest.raises(SourceRequiredForDocumentError):
            validate_document_ingestion(
                source=None,  # type: ignore[arg-type]
                title="doc",
                checksum=DocumentChecksum(value="abc"),
                classification="public",
            )

    def test_chunk_requires_document(self) -> None:
        cc = ChunkContent(value="content")
        with pytest.raises(DocumentRequiredForChunkError):
            validate_chunk_creation(
                document=None,  # type: ignore[arg-type]
                content=cc,
                existing_indices=[],
            )

    def test_source_deleted_blocks_document_ingestion(self) -> None:
        src = make_active_source()
        src.delete()
        with pytest.raises(SourceNotActiveError):
            validate_document_ingestion(
                source=src,
                title="doc",
                checksum=DocumentChecksum(value="abc"),
                classification="public",
            )

    def test_document_deleted_blocks_chunk_creation(self) -> None:
        doc = make_document()
        doc.delete()
        cc = ChunkContent(value="content")
        with pytest.raises(DeletedDocumentModificationError):
            validate_chunk_creation(
                document=doc,
                content=cc,
                existing_indices=[],
            )

    def test_register_source_then_ingest_document(self) -> None:
        src, _ = KnowledgeFactory.register_source(
            name="full-cycle",
            source_type=SourceType.FILE,
            location="/data",
            classification="public",
        )
        src.activate()
        doc, _ = KnowledgeFactory.ingest_document(
            source=src,
            title="full-doc",
            checksum="abc123",
            classification="public",
        )
        assert doc.source_id == src.source_id

    def test_register_source_then_start_ingestion(self) -> None:
        src, _ = KnowledgeFactory.register_source(
            name="ingestion-test",
            source_type=SourceType.FILE,
            location="/data",
            classification="public",
        )
        src.activate()
        job, event = KnowledgeFactory.start_ingestion(source=src)
        assert job.source_id == src.source_id
        assert isinstance(event, IngestionStarted)

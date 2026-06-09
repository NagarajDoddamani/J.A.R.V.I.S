from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import pytest

from backend.knowledge.application.ports.outbox import KnowledgeOutboxEvent
from backend.knowledge.application.use_cases.complete_ingestion import (
    CompleteIngestionUseCase,
)
from backend.knowledge.application.use_cases.create_chunk import CreateChunkUseCase
from backend.knowledge.application.use_cases.delete_source import DeleteSourceUseCase
from backend.knowledge.application.use_cases.dto import (
    ChunkResponse,
    CompleteIngestionRequest,
    CompleteIngestionResponse,
    CreateChunkRequest,
    CreateChunkResponse,
    DeleteSourceRequest,
    DeleteSourceResponse,
    DocumentResponse,
    FailIngestionRequest,
    FailIngestionResponse,
    GetChunksByDocumentRequest,
    GetChunksByDocumentResponse,
    GetDocumentRequest,
    GetIngestionJobRequest,
    GetSourceRequest,
    IngestDocumentRequest,
    IngestDocumentResponse,
    IngestionJobResponse,
    ListSourcesRequest,
    ListSourcesResponse,
    RegisterSourceRequest,
    RegisterSourceResponse,
    ReindexResponse,
    RequestReindexRequest,
    SourceResponse,
    StartIngestionRequest,
    StartIngestionResponse,
)
from backend.knowledge.application.use_cases.exceptions import (
    ChunkNotFoundError,
    DocumentDeletedError,
    DocumentNotFoundError,
    IngestionJobNotFoundError,
    InvalidIngestionTransitionError,
    SourceInactiveError,
    SourceNotFoundError,
    UseCaseError,
)
from backend.knowledge.application.use_cases.fail_ingestion import (
    FailIngestionUseCase,
)
from backend.knowledge.application.use_cases.get_chunks_by_document import (
    GetChunksByDocumentUseCase,
)
from backend.knowledge.application.use_cases.get_document import GetDocumentUseCase
from backend.knowledge.application.use_cases.get_ingestion_job import (
    GetIngestionJobUseCase,
)
from backend.knowledge.application.use_cases.get_source import GetSourceUseCase
from backend.knowledge.application.use_cases.ingest_document import (
    IngestDocumentUseCase,
)
from backend.knowledge.application.use_cases.list_sources import ListSourcesUseCase
from backend.knowledge.application.use_cases.register_source import (
    RegisterSourceUseCase,
)
from backend.knowledge.application.use_cases.request_reindex import (
    RequestReindexUseCase,
)
from backend.knowledge.application.use_cases.start_ingestion import (
    StartIngestionUseCase,
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

UUID_STR = "01975c2f-4aef-7cf1-a940-ae54bf596280"
UUID_STR_2 = "01975c2f-4aef-7cf1-a940-ae54bf596281"
UUID_STR_3 = "01975c2f-4aef-7cf1-a940-ae54bf596282"


# ===================================================================
# Fake port implementations
# ===================================================================


class FakeKnowledgeSourceRepository:
    def __init__(self) -> None:
        self._sources: dict[str, KnowledgeSource] = {}

    def save(self, source: KnowledgeSource) -> None:
        self._sources[str(source.source_id)] = source

    def find_by_id(self, source_id: KnowledgeSourceId) -> KnowledgeSource | None:
        return self._sources.get(str(source_id))

    def find_by_status(self, status: SourceStatus) -> list[KnowledgeSource]:
        return [s for s in self._sources.values() if s.status == status]

    def find_by_type(self, source_type: SourceType) -> list[KnowledgeSource]:
        return [s for s in self._sources.values() if s.source_type == source_type]

    def count(self) -> int:
        return len(self._sources)


class FakeKnowledgeDocumentRepository:
    def __init__(self) -> None:
        self._documents: dict[str, KnowledgeDocument] = {}

    def save(self, document: KnowledgeDocument) -> None:
        self._documents[str(document.document_id)] = document

    def find_by_id(self, document_id: DocumentId) -> KnowledgeDocument | None:
        return self._documents.get(str(document_id))

    def find_by_source_id(
        self, source_id: KnowledgeSourceId
    ) -> list[KnowledgeDocument]:
        return [
            d
            for d in self._documents.values()
            if d.source_id and str(d.source_id) == str(source_id)
        ]

    def find_by_checksum(
        self, checksum: DocumentChecksum
    ) -> list[KnowledgeDocument]:
        return [
            d
            for d in self._documents.values()
            if d.checksum and str(d.checksum) == str(checksum)
        ]

    def find_deleted(self) -> list[KnowledgeDocument]:
        return [d for d in self._documents.values() if d.is_deleted]

    def count(self) -> int:
        return len(self._documents)


class FakeKnowledgeChunkRepository:
    def __init__(self) -> None:
        self._chunks: dict[str, KnowledgeChunk] = {}

    def save(self, chunk: KnowledgeChunk) -> None:
        self._chunks[str(chunk.chunk_id)] = chunk

    def find_by_id(self, chunk_id: ChunkId) -> KnowledgeChunk | None:
        return self._chunks.get(str(chunk_id))

    def find_by_document_id(
        self, document_id: DocumentId
    ) -> list[KnowledgeChunk]:
        return sorted(
            [
                c
                for c in self._chunks.values()
                if c.document_id and str(c.document_id) == str(document_id)
            ],
            key=lambda c: int(c.chunk_index) if c.chunk_index is not None else -1,
        )

    def find_by_index_range(
        self, document_id: DocumentId, start_index: int, end_index: int
    ) -> list[KnowledgeChunk]:
        return [
            c
            for c in self._chunks.values()
            if c.document_id
            and str(c.document_id) == str(document_id)
            and c.chunk_index is not None
            and start_index <= int(c.chunk_index) <= end_index
        ]

    def count(self) -> int:
        return len(self._chunks)


class FakeIngestionJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[str, IngestionJob] = {}

    def save(self, job: IngestionJob) -> None:
        self._jobs[str(job.job_id)] = job

    def find_by_id(self, job_id: IngestionJobId) -> IngestionJob | None:
        return self._jobs.get(str(job_id))

    def find_by_source_id(
        self, source_id: KnowledgeSourceId
    ) -> list[IngestionJob]:
        return [
            j
            for j in self._jobs.values()
            if j.source_id and str(j.source_id) == str(source_id)
        ]

    def find_by_status(self, status: IngestionStatus) -> list[IngestionJob]:
        return [j for j in self._jobs.values() if j.status == status]

    def count(self) -> int:
        return len(self._jobs)


class FakeKnowledgeOutbox:
    def __init__(self) -> None:
        self.events: list[KnowledgeOutboxEvent] = []

    def append(self, event: KnowledgeOutboxEvent) -> None:
        self.events.append(event)

    def fetch_unpublished(self, limit: int = 100) -> list[KnowledgeOutboxEvent]:
        return self.events[:limit]

    def mark_published(self, aggregate_id: str) -> None:
        pass


class FakeClock:
    def __init__(self, now: datetime | None = None) -> None:
        self._now = now

    def now(self) -> datetime:
        if self._now is not None:
            return self._now
        return datetime.now(tz=timezone.utc)


class FakeKnowledgeIdGenerator:
    def __init__(self) -> None:
        self.call_count = 0

    def generate_source_id(self) -> KnowledgeSourceId:
        self.call_count += 1
        return KnowledgeSourceId()

    def generate_document_id(self) -> DocumentId:
        self.call_count += 1
        return DocumentId()

    def generate_chunk_id(self) -> ChunkId:
        self.call_count += 1
        return ChunkId()

    def generate_job_id(self) -> IngestionJobId:
        self.call_count += 1
        return IngestionJobId()


# ===================================================================
# Helpers
# ===================================================================


NOW = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)


def create_persisted_source(
    repo: FakeKnowledgeSourceRepository,
    source_id: str = UUID_STR,
    name: str = "Test Source",
    source_type: SourceType = SourceType.FILE,
    location: str = "/path",
    classification: str = "public",
    status: SourceStatus = SourceStatus.ACTIVE,
) -> KnowledgeSource:
    source = KnowledgeSource(
        source_id=KnowledgeSourceId(value=UUID(source_id)),
        name=name,
        source_type=source_type,
        location=SourceLocation(value=location),
        classification=classification,
        status=status,
        created_at=NOW,
    )
    repo.save(source)
    return source


def create_persisted_document(
    repo: FakeKnowledgeDocumentRepository,
    document_id: str = UUID_STR_2,
    source_id: str = UUID_STR,
    title: str = "Test Doc",
    status: DocumentStatus = DocumentStatus.PENDING,
) -> KnowledgeDocument:
    doc = KnowledgeDocument(
        document_id=DocumentId(value=UUID(document_id)),
        source_id=KnowledgeSourceId(value=UUID(source_id)),
        title=title,
        checksum=DocumentChecksum(value="abc123"),
        classification="public",
        status=status,
        revision=1,
        created_at=NOW,
    )
    repo.save(doc)
    return doc


# ===================================================================
# DTO tests
# ===================================================================


class TestRegisterSourceRequest:
    def test_default_classification(self) -> None:
        req = RegisterSourceRequest(name="Test", source_type="file", location="/p")
        assert req.classification == "public"

    def test_fields(self) -> None:
        req = RegisterSourceRequest(
            name="Src", source_type="url", location="https://ex.com", classification="internal"
        )
        assert req.name == "Src"
        assert req.source_type == "url"
        assert req.location == "https://ex.com"
        assert req.classification == "internal"


class TestRegisterSourceResponse:
    def test_fields(self) -> None:
        resp = RegisterSourceResponse(
            source_id=UUID_STR,
            name="Src",
            source_type="file",
            location="/p",
            classification="public",
            status="registered",
            created_at=NOW,
        )
        assert resp.source_id == UUID_STR
        assert resp.status == "registered"


class TestSourceResponse:
    def test_nullable_fields(self) -> None:
        resp = SourceResponse(
            source_id=UUID_STR,
            name="Src",
            source_type="file",
            location=None,
            classification="public",
            status="active",
            created_at=NOW,
            updated_at=None,
            deleted_at=None,
        )
        assert resp.location is None
        assert resp.updated_at is None
        assert resp.deleted_at is None


class TestDocumentResponse:
    def test_fields(self) -> None:
        resp = DocumentResponse(
            document_id=UUID_STR_2,
            source_id=UUID_STR,
            title="Doc",
            checksum="abc",
            classification="public",
            status="ingested",
            revision=2,
            created_at=NOW,
            updated_at=None,
            deleted_at=None,
        )
        assert resp.document_id == UUID_STR_2
        assert resp.revision == 2


class TestIngestionJobResponse:
    def test_fields(self) -> None:
        resp = IngestionJobResponse(
            job_id=UUID_STR_3,
            source_id=UUID_STR,
            status="failed",
            started_at=NOW,
            completed_at=NOW,
            error_message="err",
        )
        assert resp.job_id == UUID_STR_3
        assert resp.error_message == "err"


class TestChunkResponse:
    def test_fields(self) -> None:
        resp = ChunkResponse(
            chunk_id=UUID_STR_3,
            document_id=UUID_STR_2,
            chunk_index=0,
            content="text",
            classification="public",
            created_at=NOW,
        )
        assert resp.chunk_index == 0


# ===================================================================
# RegisterSourceUseCase
# ===================================================================


class TestRegisterSourceUseCase:
    @pytest.fixture
    def use_case(self) -> RegisterSourceUseCase:
        return RegisterSourceUseCase(
            source_repo=FakeKnowledgeSourceRepository(),
            outbox=FakeKnowledgeOutbox(),
            clock=FakeClock(now=NOW),
            id_generator=FakeKnowledgeIdGenerator(),
        )

    def test_happy_path(self, use_case: RegisterSourceUseCase) -> None:
        resp = use_case.execute(
            RegisterSourceRequest(
                name="My Source",
                source_type="file",
                location="/data/docs",
                classification="internal",
            )
        )
        assert resp.name == "My Source"
        assert resp.status == "registered"
        assert resp.created_at is not None

    def test_persistence(self, use_case: RegisterSourceUseCase) -> None:
        resp = use_case.execute(
            RegisterSourceRequest(name="Persist", source_type="url",
                                  location="https://ex.com")
        )
        found = use_case._source_repo.find_by_id(
            KnowledgeSourceId(value=UUID(resp.source_id))
        )
        assert found is not None
        assert found.name == "Persist"

    def test_outbox_event(self, use_case: RegisterSourceUseCase) -> None:
        resp = use_case.execute(
            RegisterSourceRequest(name="Event", source_type="file",
                                  location="/data")
        )
        assert len(use_case._outbox.events) == 1
        event = use_case._outbox.events[0]
        from backend.knowledge.domain.model import KnowledgeSourceRegistered
        assert isinstance(event, KnowledgeSourceRegistered)
        assert str(event.source_id) == resp.source_id

    def test_source_type_enum_conversion(self, use_case: RegisterSourceUseCase) -> None:
        resp = use_case.execute(
            RegisterSourceRequest(name="Dir", source_type="directory",
                                  location="/dir")
        )
        assert resp.source_type == "directory"

    def test_response_has_all_fields(self, use_case: RegisterSourceUseCase) -> None:
        resp = use_case.execute(
            RegisterSourceRequest(name="Full", source_type="manual",
                                  location="/manual", classification="sensitive")
        )
        assert resp.source_type == "manual"
        assert resp.classification == "sensitive"
        assert resp.location == "/manual"


# ===================================================================
# DeleteSourceUseCase
# ===================================================================


class TestDeleteSourceUseCase:
    @pytest.fixture
    def use_case(self) -> DeleteSourceUseCase:
        source_repo = FakeKnowledgeSourceRepository()
        create_persisted_source(source_repo)
        return DeleteSourceUseCase(
            source_repo=source_repo,
            outbox=FakeKnowledgeOutbox(),
        )

    def test_delete_lifecycle(self, use_case: DeleteSourceUseCase) -> None:
        resp = use_case.execute(DeleteSourceRequest(source_id=UUID_STR))
        assert resp.source_id == UUID_STR
        assert resp.deleted_at is not None
        source = use_case._source_repo.find_by_id(
            KnowledgeSourceId(value=UUID(UUID_STR))
        )
        assert source is not None
        assert source.status == SourceStatus.DELETED

    def test_missing_source(self, use_case: DeleteSourceUseCase) -> None:
        with pytest.raises(SourceNotFoundError) as exc:
            use_case.execute(
                DeleteSourceRequest(source_id="00000000-0000-0000-0000-000000000000")
            )
        assert "00000000-0000-0000-0000-000000000000" in str(exc.value)

    def test_outbox_event(self, use_case: DeleteSourceUseCase) -> None:
        use_case.execute(DeleteSourceRequest(source_id=UUID_STR))
        assert len(use_case._outbox.events) >= 1
        from backend.knowledge.domain.model import KnowledgeSourceDeleted
        assert isinstance(use_case._outbox.events[-1], KnowledgeSourceDeleted)


# ===================================================================
# GetSourceUseCase
# ===================================================================


class TestGetSourceUseCase:
    @pytest.fixture
    def use_case(self) -> GetSourceUseCase:
        source_repo = FakeKnowledgeSourceRepository()
        create_persisted_source(source_repo)
        return GetSourceUseCase(source_repo=source_repo)

    def test_existing(self, use_case: GetSourceUseCase) -> None:
        resp = use_case.execute(GetSourceRequest(source_id=UUID_STR))
        assert resp.source_id == UUID_STR
        assert resp.name == "Test Source"

    def test_missing(self, use_case: GetSourceUseCase) -> None:
        with pytest.raises(SourceNotFoundError):
            use_case.execute(
                GetSourceRequest(source_id="00000000-0000-0000-0000-000000000000")
            )

    def test_response_location(self, use_case: GetSourceUseCase) -> None:
        resp = use_case.execute(GetSourceRequest(source_id=UUID_STR))
        assert resp.location == "/path"


# ===================================================================
# ListSourcesUseCase
# ===================================================================


class TestListSourcesUseCase:
    @pytest.fixture
    def use_case(self) -> ListSourcesUseCase:
        source_repo = FakeKnowledgeSourceRepository()
        create_persisted_source(source_repo, source_id=UUID_STR,
                                name="Active 1", status=SourceStatus.ACTIVE)
        create_persisted_source(source_repo, source_id=UUID_STR_2,
                                name="Disabled", status=SourceStatus.DISABLED)
        create_persisted_source(source_repo, source_id=UUID_STR_3,
                                name="Registered", status=SourceStatus.REGISTERED)
        return ListSourcesUseCase(source_repo=source_repo)

    def test_no_filter(self, use_case: ListSourcesUseCase) -> None:
        resp = use_case.execute(ListSourcesRequest())
        assert len(resp.sources) >= 3

    def test_status_filter(self, use_case: ListSourcesUseCase) -> None:
        resp = use_case.execute(ListSourcesRequest(status="disabled"))
        assert len(resp.sources) == 1
        assert resp.sources[0].name == "Disabled"

    def test_type_filter(self, use_case: ListSourcesUseCase) -> None:
        resp = use_case.execute(ListSourcesRequest(source_type="file"))
        assert all(s.source_type == "file" for s in resp.sources)

    def test_combined_filter_not_supported(self, use_case: ListSourcesUseCase) -> None:
        resp = use_case.execute(
            ListSourcesRequest(status="active", source_type="file")
        )
        assert len(resp.sources) >= 1

    def test_empty_result(self, use_case: ListSourcesUseCase) -> None:
        empty_repo = FakeKnowledgeSourceRepository()
        uc = ListSourcesUseCase(source_repo=empty_repo)
        resp = uc.execute(ListSourcesRequest())
        assert len(resp.sources) == 0


# ===================================================================
# IngestDocumentUseCase
# ===================================================================


class TestIngestDocumentUseCase:
    @pytest.fixture
    def use_case(self) -> IngestDocumentUseCase:
        source_repo = FakeKnowledgeSourceRepository()
        create_persisted_source(source_repo)
        return IngestDocumentUseCase(
            source_repo=source_repo,
            document_repo=FakeKnowledgeDocumentRepository(),
            outbox=FakeKnowledgeOutbox(),
            clock=FakeClock(now=NOW),
            id_generator=FakeKnowledgeIdGenerator(),
        )

    def test_active_source(self, use_case: IngestDocumentUseCase) -> None:
        resp = use_case.execute(
            IngestDocumentRequest(source_id=UUID_STR, title="Doc",
                                  checksum="abc", classification="public")
        )
        assert resp.title == "Doc"
        assert resp.status == "pending"

    def test_inactive_source(self, use_case: IngestDocumentUseCase) -> None:
        use_case._source_repo.save(
            KnowledgeSource(
                source_id=KnowledgeSourceId(value=UUID(UUID_STR_2)),
                name="Disabled",
                source_type=SourceType.FILE,
                status=SourceStatus.DISABLED,
                created_at=NOW,
            )
        )
        with pytest.raises(SourceInactiveError):
            use_case.execute(
                IngestDocumentRequest(source_id=UUID_STR_2, title="Doc",
                                      checksum="abc")
            )

    def test_missing_source(self, use_case: IngestDocumentUseCase) -> None:
        with pytest.raises(SourceNotFoundError):
            use_case.execute(
                IngestDocumentRequest(
                    source_id="00000000-0000-0000-0000-000000000000",
                    title="Doc", checksum="abc"
                )
            )

    def test_event_emission(self, use_case: IngestDocumentUseCase) -> None:
        use_case.execute(
            IngestDocumentRequest(source_id=UUID_STR, title="Doc",
                                  checksum="abc")
        )
        assert len(use_case._outbox.events) == 1
        from backend.knowledge.domain.model import DocumentIngested
        assert isinstance(use_case._outbox.events[0], DocumentIngested)

    def test_response_fields(self, use_case: IngestDocumentUseCase) -> None:
        resp = use_case.execute(
            IngestDocumentRequest(source_id=UUID_STR, title="My Document",
                                  checksum="def456", classification="sensitive")
        )
        assert resp.source_id == UUID_STR
        assert resp.checksum == "def456"
        assert resp.classification == "sensitive"

    def test_deleted_source_blocks_ingestion(self, use_case: IngestDocumentUseCase) -> None:
        deleted_id = "11975c2f-4aef-7cf1-a940-ae54bf596280"
        use_case._source_repo.save(
            KnowledgeSource(
                source_id=KnowledgeSourceId(value=UUID(deleted_id)),
                name="Deleted",
                source_type=SourceType.FILE,
                status=SourceStatus.DELETED,
                created_at=NOW,
                deleted_at=NOW,
            )
        )
        with pytest.raises(SourceInactiveError):
            use_case.execute(
                IngestDocumentRequest(source_id=deleted_id, title="Doc",
                                      checksum="abc")
            )


# ===================================================================
# GetDocumentUseCase
# ===================================================================


class TestGetDocumentUseCase:
    @pytest.fixture
    def use_case(self) -> GetDocumentUseCase:
        doc_repo = FakeKnowledgeDocumentRepository()
        create_persisted_document(doc_repo)
        return GetDocumentUseCase(document_repo=doc_repo)

    def test_existing(self, use_case: GetDocumentUseCase) -> None:
        resp = use_case.execute(GetDocumentRequest(document_id=UUID_STR_2))
        assert resp.document_id == UUID_STR_2
        assert resp.title == "Test Doc"

    def test_missing(self, use_case: GetDocumentUseCase) -> None:
        with pytest.raises(DocumentNotFoundError):
            use_case.execute(
                GetDocumentRequest(
                    document_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_checksum(self, use_case: GetDocumentUseCase) -> None:
        resp = use_case.execute(GetDocumentRequest(document_id=UUID_STR_2))
        assert resp.checksum == "abc123"


# ===================================================================
# CreateChunkUseCase
# ===================================================================


class TestCreateChunkUseCase:
    @pytest.fixture
    def use_case(self) -> CreateChunkUseCase:
        doc_repo = FakeKnowledgeDocumentRepository()
        create_persisted_document(doc_repo)
        return CreateChunkUseCase(
            document_repo=doc_repo,
            chunk_repo=FakeKnowledgeChunkRepository(),
            outbox=FakeKnowledgeOutbox(),
            clock=FakeClock(now=NOW),
            id_generator=FakeKnowledgeIdGenerator(),
        )

    def test_document_exists(self, use_case: CreateChunkUseCase) -> None:
        resp = use_case.execute(
            CreateChunkRequest(document_id=UUID_STR_2, chunk_index=0,
                               content="Chunk content")
        )
        assert resp.chunk_index == 0
        assert resp.content == "Chunk content"

    def test_missing_document(self, use_case: CreateChunkUseCase) -> None:
        with pytest.raises(DocumentNotFoundError):
            use_case.execute(
                CreateChunkRequest(
                    document_id="00000000-0000-0000-0000-000000000000",
                    chunk_index=0, content="test"
                )
            )

    def test_deleted_document(self, use_case: CreateChunkUseCase) -> None:
        deleted_id = "22975c2f-4aef-7cf1-a940-ae54bf596280"
        doc = KnowledgeDocument(
            document_id=DocumentId(value=UUID(deleted_id)),
            title="Deleted Doc",
            status=DocumentStatus.DELETED,
            created_at=NOW,
            deleted_at=NOW,
        )
        use_case._document_repo.save(doc)
        with pytest.raises(DocumentDeletedError):
            use_case.execute(
                CreateChunkRequest(document_id=deleted_id, chunk_index=0,
                                   content="test")
            )

    def test_event_emission(self, use_case: CreateChunkUseCase) -> None:
        use_case.execute(
            CreateChunkRequest(document_id=UUID_STR_2, chunk_index=0,
                               content="Emit test")
        )
        assert len(use_case._outbox.events) == 1
        from backend.knowledge.domain.model import ChunkCreated
        assert isinstance(use_case._outbox.events[0], ChunkCreated)

    def test_chunk_ordering(self, use_case: CreateChunkUseCase) -> None:
        resp0 = use_case.execute(
            CreateChunkRequest(document_id=UUID_STR_2, chunk_index=0,
                               content="First")
        )
        resp1 = use_case.execute(
            CreateChunkRequest(document_id=UUID_STR_2, chunk_index=1,
                               content="Second")
        )
        assert resp0.chunk_index == 0
        assert resp1.chunk_index == 1


# ===================================================================
# GetChunksByDocumentUseCase
# ===================================================================


class TestGetChunksByDocumentUseCase:
    @pytest.fixture
    def use_case(self) -> GetChunksByDocumentUseCase:
        chunk_repo = FakeKnowledgeChunkRepository()
        doc_id = DocumentId(value=UUID(UUID_STR_2))
        chunk_repo.save(
            KnowledgeChunk(
                chunk_id=ChunkId(),
                document_id=doc_id,
                chunk_index=ChunkIndex(value=0),
                content=ChunkContent(value="Chunk 0"),
                classification="public",
                created_at=NOW,
            )
        )
        chunk_repo.save(
            KnowledgeChunk(
                chunk_id=ChunkId(),
                document_id=doc_id,
                chunk_index=ChunkIndex(value=1),
                content=ChunkContent(value="Chunk 1"),
                classification="public",
                created_at=NOW,
            )
        )
        return GetChunksByDocumentUseCase(chunk_repo=chunk_repo)

    def test_has_chunks(self, use_case: GetChunksByDocumentUseCase) -> None:
        resp = use_case.execute(
            GetChunksByDocumentRequest(document_id=UUID_STR_2)
        )
        assert len(resp.chunks) == 2

    def test_ordering(self, use_case: GetChunksByDocumentUseCase) -> None:
        resp = use_case.execute(
            GetChunksByDocumentRequest(document_id=UUID_STR_2)
        )
        assert resp.chunks[0].chunk_index == 0
        assert resp.chunks[1].chunk_index == 1

    def test_empty(self, use_case: GetChunksByDocumentUseCase) -> None:
        resp = use_case.execute(
            GetChunksByDocumentRequest(
                document_id="00000000-0000-0000-0000-000000000000"
            )
        )
        assert len(resp.chunks) == 0


# ===================================================================
# StartIngestionUseCase
# ===================================================================


class TestStartIngestionUseCase:
    @pytest.fixture
    def use_case(self) -> StartIngestionUseCase:
        source_repo = FakeKnowledgeSourceRepository()
        create_persisted_source(source_repo)
        return StartIngestionUseCase(
            source_repo=source_repo,
            job_repo=FakeIngestionJobRepository(),
            outbox=FakeKnowledgeOutbox(),
            clock=FakeClock(now=NOW),
            id_generator=FakeKnowledgeIdGenerator(),
        )

    def test_active_source(self, use_case: StartIngestionUseCase) -> None:
        resp = use_case.execute(StartIngestionRequest(source_id=UUID_STR))
        assert resp.status == "running"
        assert resp.started_at is not None

    def test_inactive_source(self, use_case: StartIngestionUseCase) -> None:
        disabled_id = "33975c2f-4aef-7cf1-a940-ae54bf596280"
        use_case._source_repo.save(
            KnowledgeSource(
                source_id=KnowledgeSourceId(value=UUID(disabled_id)),
                name="Disabled",
                source_type=SourceType.FILE,
                status=SourceStatus.DISABLED,
                created_at=NOW,
            )
        )
        with pytest.raises(SourceInactiveError):
            use_case.execute(StartIngestionRequest(source_id=disabled_id))

    def test_missing_source(self, use_case: StartIngestionUseCase) -> None:
        with pytest.raises(SourceNotFoundError):
            use_case.execute(
                StartIngestionRequest(
                    source_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_outbox_event(self, use_case: StartIngestionUseCase) -> None:
        use_case.execute(StartIngestionRequest(source_id=UUID_STR))
        assert len(use_case._outbox.events) == 1
        from backend.knowledge.domain.model import IngestionStarted
        assert isinstance(use_case._outbox.events[0], IngestionStarted)

    def test_job_persisted(self, use_case: StartIngestionUseCase) -> None:
        resp = use_case.execute(StartIngestionRequest(source_id=UUID_STR))
        job = use_case._job_repo.find_by_id(
            IngestionJobId(value=UUID(resp.job_id))
        )
        assert job is not None
        assert job.status == IngestionStatus.RUNNING


# ===================================================================
# CompleteIngestionUseCase
# ===================================================================


class TestCompleteIngestionUseCase:
    @pytest.fixture
    def use_case(self) -> CompleteIngestionUseCase:
        job_repo = FakeIngestionJobRepository()
        job = IngestionJob(
            job_id=IngestionJobId(value=UUID(UUID_STR_3)),
            source_id=KnowledgeSourceId(value=UUID(UUID_STR)),
            status=IngestionStatus.RUNNING,
            started_at=NOW,
        )
        job_repo.save(job)
        return CompleteIngestionUseCase(
            job_repo=job_repo,
            outbox=FakeKnowledgeOutbox(),
        )

    def test_happy_path(self, use_case: CompleteIngestionUseCase) -> None:
        resp = use_case.execute(CompleteIngestionRequest(job_id=UUID_STR_3))
        assert resp.status == "completed"
        assert resp.completed_at is not None

    def test_missing_job(self, use_case: CompleteIngestionUseCase) -> None:
        with pytest.raises(IngestionJobNotFoundError):
            use_case.execute(
                CompleteIngestionRequest(
                    job_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_invalid_transition(self, use_case: CompleteIngestionUseCase) -> None:
        use_case.execute(CompleteIngestionRequest(job_id=UUID_STR_3))
        with pytest.raises(InvalidIngestionTransitionError):
            use_case.execute(CompleteIngestionRequest(job_id=UUID_STR_3))

    def test_outbox_event(self, use_case: CompleteIngestionUseCase) -> None:
        use_case.execute(CompleteIngestionRequest(job_id=UUID_STR_3))
        assert len(use_case._outbox.events) == 1
        from backend.knowledge.domain.model import IngestionCompleted
        assert isinstance(use_case._outbox.events[0], IngestionCompleted)

    def test_job_state_updated(self, use_case: CompleteIngestionUseCase) -> None:
        use_case.execute(CompleteIngestionRequest(job_id=UUID_STR_3))
        job = use_case._job_repo.find_by_id(
            IngestionJobId(value=UUID(UUID_STR_3))
        )
        assert job is not None
        assert job.status == IngestionStatus.COMPLETED


# ===================================================================
# FailIngestionUseCase
# ===================================================================


class TestFailIngestionUseCase:
    @pytest.fixture
    def use_case(self) -> FailIngestionUseCase:
        job_repo = FakeIngestionJobRepository()
        job = IngestionJob(
            job_id=IngestionJobId(value=UUID(UUID_STR_3)),
            source_id=KnowledgeSourceId(value=UUID(UUID_STR)),
            status=IngestionStatus.RUNNING,
            started_at=NOW,
        )
        job_repo.save(job)
        return FailIngestionUseCase(
            job_repo=job_repo,
            outbox=FakeKnowledgeOutbox(),
        )

    def test_happy_path(self, use_case: FailIngestionUseCase) -> None:
        resp = use_case.execute(
            FailIngestionRequest(job_id=UUID_STR_3, error_message="Timeout")
        )
        assert resp.status == "failed"
        assert resp.error_message == "Timeout"

    def test_missing_job(self, use_case: FailIngestionUseCase) -> None:
        with pytest.raises(IngestionJobNotFoundError):
            use_case.execute(
                FailIngestionRequest(
                    job_id="00000000-0000-0000-0000-000000000000",
                    error_message="err",
                )
            )

    def test_invalid_transition(self, use_case: FailIngestionUseCase) -> None:
        use_case.execute(
            FailIngestionRequest(job_id=UUID_STR_3, error_message="First")
        )
        with pytest.raises(InvalidIngestionTransitionError):
            use_case.execute(
                FailIngestionRequest(job_id=UUID_STR_3, error_message="Again")
            )

    def test_outbox_event(self, use_case: FailIngestionUseCase) -> None:
        use_case.execute(
            FailIngestionRequest(job_id=UUID_STR_3, error_message="Fail")
        )
        assert len(use_case._outbox.events) == 1
        from backend.knowledge.domain.model import IngestionFailed
        assert isinstance(use_case._outbox.events[0], IngestionFailed)

    def test_error_message_persisted(self, use_case: FailIngestionUseCase) -> None:
        use_case.execute(
            FailIngestionRequest(job_id=UUID_STR_3, error_message="Disk full")
        )
        job = use_case._job_repo.find_by_id(
            IngestionJobId(value=UUID(UUID_STR_3))
        )
        assert job is not None
        assert job.error_message == "Disk full"

    def test_competed_job_cannot_fail(self, use_case: FailIngestionUseCase) -> None:
        completed_id = "44975c2f-4aef-7cf1-a940-ae54bf596280"
        job = IngestionJob(
            job_id=IngestionJobId(value=UUID(completed_id)),
            status=IngestionStatus.COMPLETED,
            started_at=NOW,
            completed_at=NOW,
        )
        use_case._job_repo.save(job)
        with pytest.raises(InvalidIngestionTransitionError):
            use_case.execute(
                FailIngestionRequest(job_id=completed_id, error_message="err")
            )


# ===================================================================
# GetIngestionJobUseCase
# ===================================================================


class TestGetIngestionJobUseCase:
    @pytest.fixture
    def use_case(self) -> GetIngestionJobUseCase:
        job_repo = FakeIngestionJobRepository()
        job = IngestionJob(
            job_id=IngestionJobId(value=UUID(UUID_STR_3)),
            source_id=KnowledgeSourceId(value=UUID(UUID_STR)),
            status=IngestionStatus.RUNNING,
            started_at=NOW,
        )
        job_repo.save(job)
        return GetIngestionJobUseCase(job_repo=job_repo)

    def test_existing(self, use_case: GetIngestionJobUseCase) -> None:
        resp = use_case.execute(GetIngestionJobRequest(job_id=UUID_STR_3))
        assert resp.job_id == UUID_STR_3
        assert resp.status == "running"

    def test_missing(self, use_case: GetIngestionJobUseCase) -> None:
        with pytest.raises(IngestionJobNotFoundError):
            use_case.execute(
                GetIngestionJobRequest(
                    job_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_failed_job_response(self, use_case: GetIngestionJobUseCase) -> None:
        failed_id = "55975c2f-4aef-7cf1-a940-ae54bf596280"
        job = IngestionJob(
            job_id=IngestionJobId(value=UUID(failed_id)),
            status=IngestionStatus.FAILED,
            started_at=NOW,
            completed_at=NOW,
            error_message="Error occurred",
        )
        use_case._job_repo.save(job)
        resp = use_case.execute(GetIngestionJobRequest(job_id=failed_id))
        assert resp.status == "failed"
        assert resp.error_message == "Error occurred"


# ===================================================================
# RequestReindexUseCase
# ===================================================================


class TestRequestReindexUseCase:
    @pytest.fixture
    def use_case(self) -> RequestReindexUseCase:
        source_repo = FakeKnowledgeSourceRepository()
        create_persisted_source(source_repo)
        return RequestReindexUseCase(
            source_repo=source_repo,
            outbox=FakeKnowledgeOutbox(),
        )

    def test_active_source(self, use_case: RequestReindexUseCase) -> None:
        resp = use_case.execute(RequestReindexRequest(source_id=UUID_STR))
        assert resp.source_id == UUID_STR
        assert resp.event_type == "knowledge.reindex.requested"

    def test_inactive_source(self, use_case: RequestReindexUseCase) -> None:
        disabled_id = "66975c2f-4aef-7cf1-a940-ae54bf596280"
        use_case._source_repo.save(
            KnowledgeSource(
                source_id=KnowledgeSourceId(value=UUID(disabled_id)),
                name="Disabled",
                source_type=SourceType.FILE,
                status=SourceStatus.DISABLED,
                created_at=NOW,
            )
        )
        with pytest.raises(SourceInactiveError):
            use_case.execute(RequestReindexRequest(source_id=disabled_id))

    def test_missing_source(self, use_case: RequestReindexUseCase) -> None:
        with pytest.raises(SourceNotFoundError):
            use_case.execute(
                RequestReindexRequest(
                    source_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_outbox_event(self, use_case: RequestReindexUseCase) -> None:
        use_case.execute(RequestReindexRequest(source_id=UUID_STR))
        assert len(use_case._outbox.events) == 1
        from backend.knowledge.domain.model import ReindexRequested
        assert isinstance(use_case._outbox.events[0], ReindexRequested)

    def test_deleted_source_rejected(self, use_case: RequestReindexUseCase) -> None:
        deleted_id = "77975c2f-4aef-7cf1-a940-ae54bf596280"
        use_case._source_repo.save(
            KnowledgeSource(
                source_id=KnowledgeSourceId(value=UUID(deleted_id)),
                name="Deleted",
                source_type=SourceType.FILE,
                status=SourceStatus.DELETED,
                created_at=NOW,
                deleted_at=NOW,
            )
        )
        with pytest.raises(SourceInactiveError):
            use_case.execute(RequestReindexRequest(source_id=deleted_id))


# ===================================================================
# Integration tests
# ===================================================================


class TestSourceDocumentChunkFlow:
    @pytest.fixture
    def repos(self) -> dict[str, Any]:
        return {
            "source_repo": FakeKnowledgeSourceRepository(),
            "document_repo": FakeKnowledgeDocumentRepository(),
            "chunk_repo": FakeKnowledgeChunkRepository(),
            "job_repo": FakeIngestionJobRepository(),
            "outbox": FakeKnowledgeOutbox(),
            "clock": FakeClock(now=NOW),
            "id_gen": FakeKnowledgeIdGenerator(),
        }

    def test_full_source_document_chunk_flow(self, repos: dict[str, Any]) -> None:
        register_uc = RegisterSourceUseCase(
            source_repo=repos["source_repo"],
            outbox=repos["outbox"],
            clock=repos["clock"],
            id_generator=repos["id_gen"],
        )
        source_resp = register_uc.execute(
            RegisterSourceRequest(name="Flow Source", source_type="file",
                                  location="/flow")
        )
        source = repos["source_repo"].find_by_id(
            KnowledgeSourceId(value=UUID(source_resp.source_id))
        )
        assert source is not None
        source.activate()
        repos["source_repo"].save(source)

        ingest_uc = IngestDocumentUseCase(
            source_repo=repos["source_repo"],
            document_repo=repos["document_repo"],
            outbox=repos["outbox"],
            clock=repos["clock"],
            id_generator=repos["id_gen"],
        )
        doc_resp = ingest_uc.execute(
            IngestDocumentRequest(source_id=source_resp.source_id,
                                  title="Flow Doc", checksum="flow123")
        )

        chunk_uc = CreateChunkUseCase(
            document_repo=repos["document_repo"],
            chunk_repo=repos["chunk_repo"],
            outbox=repos["outbox"],
            clock=repos["clock"],
            id_generator=repos["id_gen"],
        )
        chunk_resp = chunk_uc.execute(
            CreateChunkRequest(document_id=doc_resp.document_id,
                               chunk_index=0, content="Flow chunk")
        )

        assert source_resp.source_id is not None
        assert doc_resp.document_id is not None
        assert chunk_resp.chunk_id is not None
        assert len(repos["outbox"].events) == 3

    def test_source_ingestion_lifecycle(self, repos: dict[str, Any]) -> None:
        register_uc = RegisterSourceUseCase(
            source_repo=repos["source_repo"],
            outbox=repos["outbox"],
            clock=repos["clock"],
            id_generator=repos["id_gen"],
        )
        source_resp = register_uc.execute(
            RegisterSourceRequest(name="Ingestion Source", source_type="file",
                                  location="/ingest")
        )
        source = repos["source_repo"].find_by_id(
            KnowledgeSourceId(value=UUID(source_resp.source_id))
        )
        assert source is not None
        source.activate()
        repos["source_repo"].save(source)

        start_uc = StartIngestionUseCase(
            source_repo=repos["source_repo"],
            job_repo=repos["job_repo"],
            outbox=repos["outbox"],
            clock=repos["clock"],
            id_generator=repos["id_gen"],
        )
        start_resp = start_uc.execute(
            StartIngestionRequest(source_id=source_resp.source_id)
        )

        complete_uc = CompleteIngestionUseCase(
            job_repo=repos["job_repo"],
            outbox=repos["outbox"],
        )
        complete_resp = complete_uc.execute(
            CompleteIngestionRequest(job_id=start_resp.job_id)
        )

        assert start_resp.status == "running"
        assert complete_resp.status == "completed"

    def test_outbox_event_ordering(self, repos: dict[str, Any]) -> None:
        register_uc = RegisterSourceUseCase(
            source_repo=repos["source_repo"],
            outbox=repos["outbox"],
            clock=repos["clock"],
            id_generator=repos["id_gen"],
        )
        resp1 = register_uc.execute(
            RegisterSourceRequest(name="Event 1", source_type="file",
                                  location="/e1")
        )
        resp2 = register_uc.execute(
            RegisterSourceRequest(name="Event 2", source_type="url",
                                  location="/e2")
        )
        resp3 = register_uc.execute(
            RegisterSourceRequest(name="Event 3", source_type="manual",
                                  location="/e3")
        )
        assert len(repos["outbox"].events) == 3
        events = repos["outbox"].fetch_unpublished()
        from backend.knowledge.domain.model import KnowledgeSourceRegistered
        assert all(isinstance(e, KnowledgeSourceRegistered) for e in events)
        assert str(events[0].source_id) == resp1.source_id
        assert str(events[1].source_id) == resp2.source_id
        assert str(events[2].source_id) == resp3.source_id


# ===================================================================
# Exception hierarchy tests
# ===================================================================


class TestExceptionHierarchy:
    def test_use_case_error_base(self) -> None:
        assert issubclass(SourceNotFoundError, UseCaseError)
        assert issubclass(DocumentNotFoundError, UseCaseError)
        assert issubclass(ChunkNotFoundError, UseCaseError)
        assert issubclass(IngestionJobNotFoundError, UseCaseError)
        assert issubclass(SourceInactiveError, UseCaseError)
        assert issubclass(DocumentDeletedError, UseCaseError)
        assert issubclass(InvalidIngestionTransitionError, UseCaseError)

    def test_chunk_not_found(self) -> None:
        exc = ChunkNotFoundError(UUID_STR)
        assert exc.chunk_id == UUID_STR
        assert UUID_STR in str(exc)

    def test_source_not_found_message(self) -> None:
        exc = SourceNotFoundError(UUID_STR)
        assert UUID_STR in str(exc)

    def test_invalid_transition_message(self) -> None:
        exc = InvalidIngestionTransitionError("running", "completed")
        assert "running" in str(exc)
        assert "completed" in str(exc)

    def test_document_deleted_message(self) -> None:
        exc = DocumentDeletedError(UUID_STR_2)
        assert UUID_STR_2 in str(exc)


# ===================================================================
# Use case instantiation tests
# ===================================================================


class TestUseCaseInstantiation:
    def test_register_source_instantiation(self) -> None:
        uc = RegisterSourceUseCase(
            source_repo=FakeKnowledgeSourceRepository(),
            outbox=FakeKnowledgeOutbox(),
            clock=FakeClock(),
            id_generator=FakeKnowledgeIdGenerator(),
        )
        assert hasattr(uc, "execute")

    def test_ingest_document_instantiation(self) -> None:
        uc = IngestDocumentUseCase(
            source_repo=FakeKnowledgeSourceRepository(),
            document_repo=FakeKnowledgeDocumentRepository(),
            outbox=FakeKnowledgeOutbox(),
            clock=FakeClock(),
            id_generator=FakeKnowledgeIdGenerator(),
        )
        assert hasattr(uc, "execute")

    def test_start_ingestion_instantiation(self) -> None:
        uc = StartIngestionUseCase(
            source_repo=FakeKnowledgeSourceRepository(),
            job_repo=FakeIngestionJobRepository(),
            outbox=FakeKnowledgeOutbox(),
            clock=FakeClock(),
            id_generator=FakeKnowledgeIdGenerator(),
        )
        assert hasattr(uc, "execute")

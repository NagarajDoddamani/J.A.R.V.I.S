from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID, uuid4

import pytest

from backend.research.application.ports.clock import ResearchClockPort
from backend.research.application.ports.id_generator import ResearchIdGeneratorPort
from backend.research.application.ports.outbox import (
    ResearchOutboxEvent,
    ResearchOutboxPort,
)
from backend.research.application.ports.repository import (
    ResearchJobRepositoryPort,
    ResearchRequestRepositoryPort,
    ResearchSourceRepositoryPort,
)
from backend.research.domain.model import (
    ResearchCancelled,
    ResearchCompleted,
    ResearchFailed,
    ResearchJob,
    ResearchJobId,
    ResearchPriority,
    ResearchRequest,
    ResearchRequested,
    ResearchRequestId,
    ResearchSource,
    ResearchStarted,
    ResearchStatus,
    ResearchSummaryGenerated,
    SourceAdded,
    SourceType,
)

# =========================================================================
# Constants
# =========================================================================

_NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


# =========================================================================
# Helpers
# =========================================================================


def _make_request(
    *,
    request_id: ResearchRequestId | None = None,
    query: str = "test query",
    goal: str = "test goal",
    priority: ResearchPriority = ResearchPriority.NORMAL,
    status: ResearchStatus = ResearchStatus.CREATED,
) -> ResearchRequest:
    from backend.research.domain.factory import ResearchFactory

    request, _ = ResearchFactory.create_request(
        query=query,
        goal=goal,
        priority=priority,
    )
    if request_id is not None:
        object.__setattr__(request, "_request_id", request_id)
    if status != ResearchStatus.CREATED:
        object.__setattr__(request, "_status", status)
    return request


def _make_job(
    *,
    job_id: ResearchJobId | None = None,
    status: ResearchStatus = ResearchStatus.CREATED,
    priority: ResearchPriority = ResearchPriority.NORMAL,
) -> ResearchJob:
    job = ResearchJob(
        job_id=job_id or ResearchJobId(),
        status=status,
        priority=priority,
    )
    return job


def _make_source(
    *,
    source_id: UUID | None = None,
    source_type: SourceType = SourceType.WEB,
) -> ResearchSource:
    from backend.research.domain.model import ConfidenceScore, SourceReference

    return ResearchSource(
        source_id=source_id or uuid4(),
        source_type=source_type,
        reference=SourceReference(value="https://example.com"),
        confidence_score=ConfidenceScore(value=0.85),
    )


def _make_requested_event() -> ResearchRequested:
    return ResearchRequested(
        request_id=ResearchRequestId(),
        query="q",
        goal="g",
        priority="normal",
        occurred_at=_NOW,
    )


# =========================================================================
# Stub: ResearchRequestRepositoryPort
# =========================================================================


class StubResearchRequestRepository:
    """Minimal stub conforming to ResearchRequestRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, ResearchRequest] = {}

    def save(self, request: ResearchRequest) -> None:
        key = str(request.request_id)
        self._store[key] = request

    def find_by_id(self, request_id: ResearchRequestId) -> ResearchRequest | None:
        return self._store.get(str(request_id))

    def find_by_status(self, status: ResearchStatus) -> list[ResearchRequest]:
        return [r for r in self._store.values() if r.status == status]

    def find_by_priority(self, priority: ResearchPriority) -> list[ResearchRequest]:
        return [r for r in self._store.values() if r.priority == priority]

    def count(self) -> int:
        return len(self._store)


class TestResearchRequestRepositoryPort:
    """Contract tests for ResearchRequestRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubResearchRequestRepository:
        return StubResearchRequestRepository()

    def test_save_and_find_by_id(self, repo: StubResearchRequestRepository) -> None:
        request = _make_request()
        repo.save(request)
        found = repo.find_by_id(request.request_id)
        assert found is not None
        assert found.request_id == request.request_id

    def test_find_by_id_returns_none(self, repo: StubResearchRequestRepository) -> None:
        missing_id = ResearchRequestId()
        assert repo.find_by_id(missing_id) is None

    def test_find_by_status(self, repo: StubResearchRequestRepository) -> None:
        created = _make_request(status=ResearchStatus.CREATED)
        running = _make_request(status=ResearchStatus.RUNNING)
        repo.save(created)
        repo.save(running)

        results = repo.find_by_status(ResearchStatus.CREATED)
        assert len(results) == 1
        assert results[0].request_id == created.request_id

        results = repo.find_by_status(ResearchStatus.RUNNING)
        assert len(results) == 1
        assert results[0].request_id == running.request_id

    def test_find_by_status_multiple(self, repo: StubResearchRequestRepository) -> None:
        requests = [_make_request(status=ResearchStatus.RUNNING) for _ in range(3)]
        for r in requests:
            repo.save(r)
        repo.save(_make_request(status=ResearchStatus.CREATED))

        results = repo.find_by_status(ResearchStatus.RUNNING)
        assert len(results) == 3

    def test_find_by_status_empty(self, repo: StubResearchRequestRepository) -> None:
        assert repo.find_by_status(ResearchStatus.FAILED) == []

    def test_find_by_priority(self, repo: StubResearchRequestRepository) -> None:
        high = _make_request(priority=ResearchPriority.HIGH)
        normal = _make_request(priority=ResearchPriority.NORMAL)
        repo.save(high)
        repo.save(normal)

        results = repo.find_by_priority(ResearchPriority.HIGH)
        assert len(results) == 1
        assert results[0].request_id == high.request_id

    def test_find_by_priority_multiple(self, repo: StubResearchRequestRepository) -> None:
        items = [_make_request(priority=ResearchPriority.LOW) for _ in range(2)]
        for r in items:
            repo.save(r)
        results = repo.find_by_priority(ResearchPriority.LOW)
        assert len(results) == 2

    def test_find_by_priority_empty(self, repo: StubResearchRequestRepository) -> None:
        assert repo.find_by_priority(ResearchPriority.CRITICAL) == []

    def test_save_updates_existing(self, repo: StubResearchRequestRepository) -> None:
        request = _make_request()
        repo.save(request)
        object.__setattr__(request, "_status", ResearchStatus.RUNNING)
        repo.save(request)
        found = repo.find_by_id(request.request_id)
        assert found is not None
        assert found.status == ResearchStatus.RUNNING

    def test_count_empty(self, repo: StubResearchRequestRepository) -> None:
        assert repo.count() == 0

    def test_count_multiple(self, repo: StubResearchRequestRepository) -> None:
        for _ in range(5):
            repo.save(_make_request())
        assert repo.count() == 5

    def test_save_and_count_after_duplicate(self, repo: StubResearchRequestRepository) -> None:
        request = _make_request()
        repo.save(request)
        repo.save(request)
        assert repo.count() == 1


# =========================================================================
# Stub: ResearchJobRepositoryPort
# =========================================================================


class StubResearchJobRepository:
    """Minimal stub conforming to ResearchJobRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, ResearchJob] = {}

    def save(self, job: ResearchJob) -> None:
        key = str(job.job_id)
        self._store[key] = job

    def find_by_id(self, job_id: ResearchJobId) -> ResearchJob | None:
        return self._store.get(str(job_id))

    def find_by_status(self, status: ResearchStatus) -> list[ResearchJob]:
        return [j for j in self._store.values() if j.status == status]

    def find_by_request_id(self, request_id: ResearchRequestId) -> list[ResearchJob]:
        return [j for j in self._store.values()]

    def count(self) -> int:
        return len(self._store)


class TestResearchJobRepositoryPort:
    """Contract tests for ResearchJobRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubResearchJobRepository:
        return StubResearchJobRepository()

    def test_save_and_find_by_id(self, repo: StubResearchJobRepository) -> None:
        job = _make_job()
        repo.save(job)
        found = repo.find_by_id(job.job_id)
        assert found is not None
        assert found.job_id == job.job_id

    def test_find_by_id_returns_none(self, repo: StubResearchJobRepository) -> None:
        missing_id = ResearchJobId()
        assert repo.find_by_id(missing_id) is None

    def test_find_by_status(self, repo: StubResearchJobRepository) -> None:
        created = _make_job(status=ResearchStatus.CREATED)
        running = _make_job(status=ResearchStatus.RUNNING)
        repo.save(created)
        repo.save(running)

        results = repo.find_by_status(ResearchStatus.CREATED)
        assert len(results) == 1
        assert results[0].job_id == created.job_id

    def test_find_by_status_multiple(self, repo: StubResearchJobRepository) -> None:
        jobs = [_make_job(status=ResearchStatus.RUNNING) for _ in range(4)]
        for j in jobs:
            repo.save(j)
        assert len(repo.find_by_status(ResearchStatus.RUNNING)) == 4

    def test_find_by_status_empty(self, repo: StubResearchJobRepository) -> None:
        assert repo.find_by_status(ResearchStatus.FAILED) == []

    def test_find_by_request_id(self, repo: StubResearchJobRepository) -> None:
        job = _make_job()
        repo.save(job)
        results = repo.find_by_request_id(ResearchRequestId())
        assert len(results) == 1

    def test_find_by_request_id_empty(self, repo: StubResearchJobRepository) -> None:
        assert repo.find_by_request_id(ResearchRequestId()) == []

    def test_save_updates_existing(self, repo: StubResearchJobRepository) -> None:
        job = _make_job()
        repo.save(job)
        object.__setattr__(job, "_status", ResearchStatus.RUNNING)
        repo.save(job)
        found = repo.find_by_id(job.job_id)
        assert found is not None
        assert found.status == ResearchStatus.RUNNING

    def test_count_empty(self, repo: StubResearchJobRepository) -> None:
        assert repo.count() == 0

    def test_count_multiple(self, repo: StubResearchJobRepository) -> None:
        for _ in range(3):
            repo.save(_make_job())
        assert repo.count() == 3


# =========================================================================
# Stub: ResearchSourceRepositoryPort
# =========================================================================


class StubResearchSourceRepository:
    """Minimal stub conforming to ResearchSourceRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, ResearchSource] = {}

    def save(self, source: ResearchSource) -> None:
        key = str(source.source_id)
        self._store[key] = source

    def find_by_id(self, source_id: UUID) -> ResearchSource | None:
        return self._store.get(str(source_id))

    def find_by_type(self, source_type: SourceType) -> list[ResearchSource]:
        return [s for s in self._store.values() if s.source_type == source_type]

    def find_by_job_id(self, job_id: ResearchJobId) -> list[ResearchSource]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class TestResearchSourceRepositoryPort:
    """Contract tests for ResearchSourceRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubResearchSourceRepository:
        return StubResearchSourceRepository()

    def test_save_and_find_by_id(self, repo: StubResearchSourceRepository) -> None:
        source = _make_source()
        repo.save(source)
        found = repo.find_by_id(source.source_id)
        assert found is not None
        assert found.source_id == source.source_id

    def test_find_by_id_returns_none(self, repo: StubResearchSourceRepository) -> None:
        assert repo.find_by_id(UUID(int=999)) is None

    def test_find_by_type(self, repo: StubResearchSourceRepository) -> None:
        web = _make_source(source_type=SourceType.WEB)
        doc = _make_source(source_type=SourceType.DOCUMENT)
        repo.save(web)
        repo.save(doc)

        results = repo.find_by_type(SourceType.WEB)
        assert len(results) == 1
        assert results[0].source_id == web.source_id

    def test_find_by_type_multiple(self, repo: StubResearchSourceRepository) -> None:
        sources = [_make_source(source_type=SourceType.MEMORY) for _ in range(3)]
        for s in sources:
            repo.save(s)
        assert len(repo.find_by_type(SourceType.MEMORY)) == 3

    def test_find_by_type_empty(self, repo: StubResearchSourceRepository) -> None:
        assert repo.find_by_type(SourceType.USER) == []

    def test_find_by_job_id(self, repo: StubResearchSourceRepository) -> None:
        source = _make_source()
        repo.save(source)
        results = repo.find_by_job_id(ResearchJobId())
        assert len(results) == 1

    def test_find_by_job_id_empty(self, repo: StubResearchSourceRepository) -> None:
        assert repo.find_by_job_id(ResearchJobId()) == []

    def test_save_updates_existing(self, repo: StubResearchSourceRepository) -> None:
        source = _make_source()
        repo.save(source)
        new_ref = "https://updated.com"
        from backend.research.domain.model import SourceReference

        object.__setattr__(source, "_reference", SourceReference(value=new_ref))
        repo.save(source)
        found = repo.find_by_id(source.source_id)
        assert found is not None
        assert found.reference is not None
        assert found.reference.value == new_ref

    def test_count_empty(self, repo: StubResearchSourceRepository) -> None:
        assert repo.count() == 0

    def test_count_multiple(self, repo: StubResearchSourceRepository) -> None:
        for _ in range(4):
            repo.save(_make_source())
        assert repo.count() == 4


# =========================================================================
# Stub: ResearchOutboxPort
# =========================================================================


class StubResearchOutbox:
    """Minimal stub conforming to ResearchOutboxPort."""

    def __init__(self) -> None:
        self._store: list[tuple[str, ResearchOutboxEvent]] = []

    def append(self, event: ResearchOutboxEvent) -> None:
        aggregate_id = str(event.event_id)
        self._store.append((aggregate_id, event))

    def fetch_unpublished(self, limit: int = 100) -> list[ResearchOutboxEvent]:
        return [event for _, event in self._store[:limit]]

    def mark_published(self, aggregate_id: str) -> None:
        self._store = [
            (aid, event)
            for aid, event in self._store
            if aid != aggregate_id
        ]


class TestResearchOutboxPort:
    """Contract tests for ResearchOutboxPort."""

    @pytest.fixture
    def outbox(self) -> StubResearchOutbox:
        return StubResearchOutbox()

    def test_append_and_fetch(self, outbox: StubResearchOutbox) -> None:
        event = _make_requested_event()
        outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert unpublished[0] == event

    def test_fetch_empty(self, outbox: StubResearchOutbox) -> None:
        assert outbox.fetch_unpublished() == []

    def test_fifo_order(self, outbox: StubResearchOutbox) -> None:
        e1 = _make_requested_event()
        e2 = _make_requested_event()
        e3 = _make_requested_event()
        outbox.append(e1)
        outbox.append(e2)
        outbox.append(e3)
        unpublished = outbox.fetch_unpublished()
        assert unpublished[0] == e1
        assert unpublished[1] == e2
        assert unpublished[2] == e3

    def test_fetch_respects_limit(self, outbox: StubResearchOutbox) -> None:
        for _ in range(10):
            outbox.append(_make_requested_event())
        assert len(outbox.fetch_unpublished(limit=3)) == 3
        assert len(outbox.fetch_unpublished(limit=0)) == 0

    def test_mark_published_removes_event(self, outbox: StubResearchOutbox) -> None:
        event = _make_requested_event()
        outbox.append(event)
        outbox.mark_published(str(event.event_id))
        assert outbox.fetch_unpublished() == []

    def test_mark_published_idempotent(self, outbox: StubResearchOutbox) -> None:
        event = _make_requested_event()
        outbox.append(event)
        aid = str(event.event_id)
        outbox.mark_published(aid)
        outbox.mark_published(aid)
        assert outbox.fetch_unpublished() == []

    def test_mark_published_partial(self, outbox: StubResearchOutbox) -> None:
        e1 = _make_requested_event()
        e2 = _make_requested_event()
        outbox.append(e1)
        outbox.append(e2)
        outbox.mark_published(str(e1.event_id))
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert unpublished[0] == e2

    def test_multiple_event_types(self, outbox: StubResearchOutbox) -> None:
        rid = ResearchRequestId()
        e1: ResearchOutboxEvent = ResearchRequested(
            request_id=rid, query="q", goal="g", priority="normal", occurred_at=_NOW,
        )
        e2: ResearchOutboxEvent = ResearchStarted(
            request_id=rid, occurred_at=_NOW,
        )
        e3: ResearchOutboxEvent = ResearchCompleted(
            request_id=rid, occurred_at=_NOW,
        )
        e4: ResearchOutboxEvent = ResearchFailed(
            request_id=rid, failure_reason="err", occurred_at=_NOW,
        )
        e5: ResearchOutboxEvent = ResearchCancelled(
            request_id=rid, occurred_at=_NOW,
        )
        e6: ResearchOutboxEvent = SourceAdded(
            request_id=rid, job_id=ResearchJobId(), source_id=UUID(int=1),
            source_type="web", reference="ref", occurred_at=_NOW,
        )
        e7: ResearchOutboxEvent = ResearchSummaryGenerated(
            request_id=rid, job_id=ResearchJobId(), summary="sum", occurred_at=_NOW,
        )
        for e in [e1, e2, e3, e4, e5, e6, e7]:
            outbox.append(e)
        assert len(outbox.fetch_unpublished()) == 7


# =========================================================================
# Stub: ResearchClockPort
# =========================================================================


class StubResearchClock:
    """Minimal stub conforming to ResearchClockPort."""

    def __init__(self, now: datetime = _NOW) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class TestResearchClockPort:
    """Contract tests for ResearchClockPort."""

    def test_now_returns_datetime(self) -> None:
        clock = StubResearchClock()
        result = clock.now()
        assert isinstance(result, datetime)

    def test_now_is_utc(self) -> None:
        clock = StubResearchClock()
        result = clock.now()
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result) == timezone.utc.utcoffset(result)

    def test_now_frozen_value(self) -> None:
        expected = datetime(2025, 1, 1, tzinfo=timezone.utc)
        clock = StubResearchClock(now=expected)
        assert clock.now() == expected

    def test_now_consistent(self) -> None:
        clock = StubResearchClock()
        assert clock.now() == clock.now()


# =========================================================================
# Stub: ResearchIdGeneratorPort
# =========================================================================


class StubResearchIdGenerator:
    """Minimal stub conforming to ResearchIdGeneratorPort."""

    def __init__(self) -> None:
        self._counter = 0

    def generate_request_id(self) -> str:
        self._counter += 1
        return f"req-{self._counter}"

    def generate_job_id(self) -> str:
        self._counter += 1
        return f"job-{self._counter}"

    def generate_source_id(self) -> str:
        self._counter += 1
        return f"src-{self._counter}"


class TestResearchIdGeneratorPort:
    """Contract tests for ResearchIdGeneratorPort."""

    def test_generate_request_id_returns_string(self) -> None:
        gen = StubResearchIdGenerator()
        result = gen.generate_request_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_job_id_returns_string(self) -> None:
        gen = StubResearchIdGenerator()
        result = gen.generate_job_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_source_id_returns_string(self) -> None:
        gen = StubResearchIdGenerator()
        result = gen.generate_source_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_uniqueness(self) -> None:
        gen = StubResearchIdGenerator()
        ids = {
            gen.generate_request_id(),
            gen.generate_job_id(),
            gen.generate_source_id(),
        }
        assert len(ids) == 3

    def test_incrementing_sequence(self) -> None:
        gen = StubResearchIdGenerator()
        a = gen.generate_request_id()
        b = gen.generate_request_id()
        assert a != b


# =========================================================================
# Outbox Event Union Conformance
# =========================================================================


class TestResearchOutboxEventUnion:
    """Verify that all domain events satisfy the outbox event union."""

    def test_research_requested_is_event(self) -> None:
        event: ResearchOutboxEvent = ResearchRequested(
            request_id=ResearchRequestId(),
            query="q", goal="g", priority="normal",
            occurred_at=_NOW,
        )
        assert event is not None

    def test_research_started_is_event(self) -> None:
        event: ResearchOutboxEvent = ResearchStarted(
            request_id=ResearchRequestId(),
            occurred_at=_NOW,
        )
        assert event is not None

    def test_research_completed_is_event(self) -> None:
        event: ResearchOutboxEvent = ResearchCompleted(
            request_id=ResearchRequestId(),
            occurred_at=_NOW,
        )
        assert event is not None

    def test_research_failed_is_event(self) -> None:
        event: ResearchOutboxEvent = ResearchFailed(
            request_id=ResearchRequestId(),
            failure_reason="err",
            occurred_at=_NOW,
        )
        assert event is not None

    def test_research_cancelled_is_event(self) -> None:
        event: ResearchOutboxEvent = ResearchCancelled(
            request_id=ResearchRequestId(),
            occurred_at=_NOW,
        )
        assert event is not None

    def test_source_added_is_event(self) -> None:
        event: ResearchOutboxEvent = SourceAdded(
            request_id=ResearchRequestId(),
            job_id=ResearchJobId(),
            source_id=UUID(int=1),
            source_type="web",
            reference="ref",
            occurred_at=_NOW,
        )
        assert event is not None

    def test_research_summary_generated_is_event(self) -> None:
        event: ResearchOutboxEvent = ResearchSummaryGenerated(
            request_id=ResearchRequestId(),
            job_id=ResearchJobId(),
            summary="sum",
            occurred_at=_NOW,
        )
        assert event is not None


# =========================================================================
# Protocol Structural Conformance
# =========================================================================


class TestResearchPortProtocolConformance:
    """Verify stub classes structurally conform to their protocols."""

    def test_request_repository_has_all_methods(self) -> None:
        methods = {"save", "find_by_id", "find_by_status", "find_by_priority", "count"}
        stub_methods = {
            m for m in dir(StubResearchRequestRepository) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_job_repository_has_all_methods(self) -> None:
        methods = {"save", "find_by_id", "find_by_status", "find_by_request_id", "count"}
        stub_methods = {
            m for m in dir(StubResearchJobRepository) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_source_repository_has_all_methods(self) -> None:
        methods = {"save", "find_by_id", "find_by_type", "find_by_job_id", "count"}
        stub_methods = {
            m for m in dir(StubResearchSourceRepository) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_outbox_has_all_methods(self) -> None:
        methods = {"append", "fetch_unpublished", "mark_published"}
        stub_methods = {
            m for m in dir(StubResearchOutbox) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_clock_has_now_method(self) -> None:
        assert hasattr(StubResearchClock, "now")

    def test_id_generator_has_all_methods(self) -> None:
        methods = {"generate_request_id", "generate_job_id", "generate_source_id"}
        stub_methods = {
            m for m in dir(StubResearchIdGenerator) if not m.startswith("_")
        }
        assert methods.issubset(stub_methods)

    def test_port_modules_importable(self) -> None:
        from backend.research.application.ports import (
            ResearchClockPort,
            ResearchIdGeneratorPort,
            ResearchOutboxEvent,
            ResearchOutboxPort,
            ResearchJobRepositoryPort,
            ResearchRequestRepositoryPort,
            ResearchSourceRepositoryPort,
        )
        assert ResearchClockPort is not None
        assert ResearchIdGeneratorPort is not None
        assert ResearchOutboxEvent is not None
        assert ResearchOutboxPort is not None
        assert ResearchJobRepositoryPort is not None
        assert ResearchRequestRepositoryPort is not None
        assert ResearchSourceRepositoryPort is not None

    def test_protocols_are_abstract(self) -> None:
        with pytest.raises(TypeError):
            ResearchRequestRepositoryPort()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            ResearchJobRepositoryPort()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            ResearchSourceRepositoryPort()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            ResearchOutboxPort()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            ResearchClockPort()  # type: ignore[abstract]
        with pytest.raises(TypeError):
            ResearchIdGeneratorPort()  # type: ignore[abstract]

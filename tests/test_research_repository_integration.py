from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator
from uuid import UUID

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.research.adapters.outbound.clock import SystemClockAdapter
from backend.research.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.research.adapters.outbound.mapper import (
    ResearchJobMapperImpl,
    ResearchOutboxMapperImpl,
    ResearchRequestMapperImpl,
    ResearchSourceMapperImpl,
)
from backend.research.adapters.outbound.models import Base
from backend.research.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyResearchJobRepository,
    SqlAlchemyResearchOutboxAdapter,
    SqlAlchemyResearchRequestRepository,
    SqlAlchemyResearchSourceRepository,
)
from backend.research.domain.model import (
    ConfidenceScore,
    FailureReason,
    QueryText,
    ResearchCancelled,
    ResearchCompleted,
    ResearchFailed,
    ResearchGoal,
    ResearchJob,
    ResearchJobId,
    ResearchPriority,
    ResearchRequest,
    ResearchRequested,
    ResearchRequestId,
    ResearchSource,
    ResearchStarted,
    ResearchStatus,
    ResearchSummary,
    ResearchSummaryGenerated,
    SourceAdded,
    SourceReference,
    SourceType,
)

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


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
def request_mapper() -> ResearchRequestMapperImpl:
    return ResearchRequestMapperImpl()


@pytest.fixture
def job_mapper() -> ResearchJobMapperImpl:
    return ResearchJobMapperImpl()


@pytest.fixture
def source_mapper() -> ResearchSourceMapperImpl:
    return ResearchSourceMapperImpl()


@pytest.fixture
def outbox_mapper() -> ResearchOutboxMapperImpl:
    return ResearchOutboxMapperImpl()


@pytest.fixture
def clock() -> SystemClockAdapter:
    return SystemClockAdapter()


@pytest.fixture
def id_gen() -> UuidGeneratorAdapter:
    return UuidGeneratorAdapter()


@pytest.fixture
def request_repo(
    session: Session,
    request_mapper: ResearchRequestMapperImpl,
) -> SqlAlchemyResearchRequestRepository:
    return SqlAlchemyResearchRequestRepository(
        session=session, mapper=request_mapper
    )


@pytest.fixture
def job_repo(
    session: Session,
    job_mapper: ResearchJobMapperImpl,
) -> SqlAlchemyResearchJobRepository:
    return SqlAlchemyResearchJobRepository(
        session=session, mapper=job_mapper
    )


@pytest.fixture
def source_repo(
    session: Session,
    source_mapper: ResearchSourceMapperImpl,
) -> SqlAlchemyResearchSourceRepository:
    return SqlAlchemyResearchSourceRepository(
        session=session, mapper=source_mapper
    )


@pytest.fixture
def outbox_adapter(
    session: Session,
    outbox_mapper: ResearchOutboxMapperImpl,
) -> SqlAlchemyResearchOutboxAdapter:
    return SqlAlchemyResearchOutboxAdapter(
        session=session, mapper=outbox_mapper
    )


@pytest.fixture
def a_request(clock: SystemClockAdapter) -> ResearchRequest:
    return ResearchRequest(
        request_id=ResearchRequestId(),
        query=QueryText(value="integration query"),
        goal=ResearchGoal(value="integration goal"),
        priority=ResearchPriority.NORMAL,
        created_at=clock.now(),
    )


@pytest.fixture
def a_job(clock: SystemClockAdapter) -> ResearchJob:
    return ResearchJob(
        job_id=ResearchJobId(),
        goal=ResearchGoal(value="integration job goal"),
        priority=ResearchPriority.NORMAL,
        status=ResearchStatus.CREATED,
        created_at=clock.now(),
    )


@pytest.fixture
def a_source() -> ResearchSource:
    return ResearchSource(
        source_id=UUID("00000000-0000-0000-0000-000000000001"),
        source_type=SourceType.WEB,
        reference=SourceReference(value="https://example.com"),
        confidence_score=ConfidenceScore(value=0.9),
    )


# ===================================================================
# ResearchRequest repository integration tests
# ===================================================================


class TestResearchRequestRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        request_repo: SqlAlchemyResearchRequestRepository,
        a_request: ResearchRequest,
    ) -> None:
        request_repo.save(a_request)
        found = request_repo.find_by_id(a_request.request_id)
        assert found is not None
        assert str(found.request_id) == str(a_request.request_id)

    def test_save_updates_existing(
        self,
        request_repo: SqlAlchemyResearchRequestRepository,
        a_request: ResearchRequest,
    ) -> None:
        request_repo.save(a_request)
        a_request.start()
        request_repo.save(a_request)
        found = request_repo.find_by_id(a_request.request_id)
        assert found is not None
        assert found.status == ResearchStatus.RUNNING

    def test_find_by_id_missing(
        self,
        request_repo: SqlAlchemyResearchRequestRepository,
    ) -> None:
        found = request_repo.find_by_id(ResearchRequestId())
        assert found is None

    def test_find_by_status(
        self,
        request_repo: SqlAlchemyResearchRequestRepository,
        a_request: ResearchRequest,
    ) -> None:
        request_repo.save(a_request)
        results = request_repo.find_by_status(ResearchStatus.CREATED)
        assert len(results) >= 1
        assert results[0].request_id == a_request.request_id

    def test_find_by_status_empty(
        self,
        request_repo: SqlAlchemyResearchRequestRepository,
    ) -> None:
        results = request_repo.find_by_status(ResearchStatus.COMPLETED)
        assert len(results) == 0

    def test_find_by_priority(
        self,
        request_repo: SqlAlchemyResearchRequestRepository,
        a_request: ResearchRequest,
    ) -> None:
        request_repo.save(a_request)
        results = request_repo.find_by_priority(ResearchPriority.NORMAL)
        assert len(results) >= 1

    def test_find_by_priority_empty(
        self,
        request_repo: SqlAlchemyResearchRequestRepository,
    ) -> None:
        results = request_repo.find_by_priority(ResearchPriority.CRITICAL)
        assert len(results) == 0

    def test_count(
        self,
        request_repo: SqlAlchemyResearchRequestRepository,
        a_request: ResearchRequest,
    ) -> None:
        assert request_repo.count() == 0
        request_repo.save(a_request)
        assert request_repo.count() == 1

    def test_lifecycle_persistence(
        self,
        request_repo: SqlAlchemyResearchRequestRepository,
        a_request: ResearchRequest,
    ) -> None:
        request_repo.save(a_request)
        a_request.start()
        request_repo.save(a_request)
        found = request_repo.find_by_id(a_request.request_id)
        assert found is not None
        assert found.status == ResearchStatus.RUNNING

    def test_failure_reason_persisted(
        self,
        request_repo: SqlAlchemyResearchRequestRepository,
        a_request: ResearchRequest,
    ) -> None:
        request_repo.save(a_request)
        a_request.start()
        a_request.fail(FailureReason(value="research failure"))
        request_repo.save(a_request)
        found = request_repo.find_by_id(a_request.request_id)
        assert found is not None
        assert found.status == ResearchStatus.FAILED
        assert str(found.failure_reason) == "research failure"

    def test_multiple_requests(
        self,
        request_repo: SqlAlchemyResearchRequestRepository,
    ) -> None:
        r1 = ResearchRequest(
            request_id=ResearchRequestId(),
            query=QueryText(value="query 1"),
            goal=ResearchGoal(value="goal 1"),
            priority=ResearchPriority.HIGH,
        )
        r2 = ResearchRequest(
            request_id=ResearchRequestId(),
            query=QueryText(value="query 2"),
            goal=ResearchGoal(value="goal 2"),
            priority=ResearchPriority.LOW,
        )
        request_repo.save(r1)
        request_repo.save(r2)
        assert request_repo.count() == 2


# ===================================================================
# ResearchJob repository integration tests
# ===================================================================


class TestResearchJobRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        job_repo: SqlAlchemyResearchJobRepository,
        a_job: ResearchJob,
    ) -> None:
        job_repo.save(a_job)
        found = job_repo.find_by_id(a_job.job_id)
        assert found is not None
        assert str(found.job_id) == str(a_job.job_id)

    def test_save_updates_existing(
        self,
        job_repo: SqlAlchemyResearchJobRepository,
        a_job: ResearchJob,
    ) -> None:
        job_repo.save(a_job)
        a_job.start()
        job_repo.save(a_job)
        found = job_repo.find_by_id(a_job.job_id)
        assert found is not None
        assert found.status == ResearchStatus.RUNNING

    def test_find_by_id_missing(
        self,
        job_repo: SqlAlchemyResearchJobRepository,
    ) -> None:
        found = job_repo.find_by_id(ResearchJobId())
        assert found is None

    def test_find_by_status(
        self,
        job_repo: SqlAlchemyResearchJobRepository,
        a_job: ResearchJob,
    ) -> None:
        job_repo.save(a_job)
        results = job_repo.find_by_status(ResearchStatus.CREATED)
        assert len(results) >= 1
        assert results[0].job_id == a_job.job_id

    def test_find_by_status_empty(
        self,
        job_repo: SqlAlchemyResearchJobRepository,
    ) -> None:
        results = job_repo.find_by_status(ResearchStatus.COMPLETED)
        assert len(results) == 0

    def test_find_by_request_id(
        self,
        job_repo: SqlAlchemyResearchJobRepository,
        a_job: ResearchJob,
    ) -> None:
        job_repo.save(a_job)
        results = job_repo.find_by_request_id(ResearchRequestId())
        assert isinstance(results, list)

    def test_count(
        self,
        job_repo: SqlAlchemyResearchJobRepository,
        a_job: ResearchJob,
    ) -> None:
        assert job_repo.count() == 0
        job_repo.save(a_job)
        assert job_repo.count() == 1

    def test_failure_reason_persisted(
        self,
        job_repo: SqlAlchemyResearchJobRepository,
    ) -> None:
        job = ResearchJob(
            job_id=ResearchJobId(),
            goal=ResearchGoal(value="failing job"),
            status=ResearchStatus.FAILED,
            priority=ResearchPriority.NORMAL,
            failure_reason=FailureReason(value="job error"),
            created_at=NOW,
        )
        job_repo.save(job)
        found = job_repo.find_by_id(job.job_id)
        assert found is not None
        assert found.status == ResearchStatus.FAILED
        assert str(found.failure_reason) == "job error"

    def test_completed_job_persisted(
        self,
        job_repo: SqlAlchemyResearchJobRepository,
    ) -> None:
        job = ResearchJob(
            job_id=ResearchJobId(),
            goal=ResearchGoal(value="complete job"),
            status=ResearchStatus.COMPLETED,
            priority=ResearchPriority.NORMAL,
            summary=ResearchSummary(value="job complete"),
            created_at=NOW,
            completed_at=NOW,
        )
        job_repo.save(job)
        found = job_repo.find_by_id(job.job_id)
        assert found is not None
        assert found.status == ResearchStatus.COMPLETED
        assert str(found.summary) == "job complete"
        assert found.completed_at is not None
        assert found.completed_at.replace(tzinfo=None) == NOW.replace(tzinfo=None)

    def test_multiple_jobs(
        self,
        job_repo: SqlAlchemyResearchJobRepository,
    ) -> None:
        j1 = ResearchJob(
            job_id=ResearchJobId(),
            goal=ResearchGoal(value="job A"),
            status=ResearchStatus.CREATED,
            priority=ResearchPriority.HIGH,
        )
        j2 = ResearchJob(
            job_id=ResearchJobId(),
            goal=ResearchGoal(value="job B"),
            status=ResearchStatus.RUNNING,
            priority=ResearchPriority.LOW,
        )
        job_repo.save(j1)
        job_repo.save(j2)
        assert job_repo.count() == 2


# ===================================================================
# ResearchSource repository integration tests
# ===================================================================


class TestResearchSourceRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        source_repo: SqlAlchemyResearchSourceRepository,
        a_source: ResearchSource,
    ) -> None:
        source_repo.save(a_source)
        found = source_repo.find_by_id(a_source.source_id)
        assert found is not None
        assert found.source_id == a_source.source_id

    def test_save_updates_existing(
        self,
        source_repo: SqlAlchemyResearchSourceRepository,
        a_source: ResearchSource,
    ) -> None:
        source_repo.save(a_source)
        updated = ResearchSource(
            source_id=a_source.source_id,
            source_type=SourceType.KNOWLEDGE,
            reference=SourceReference(value="updated-ref"),
            confidence_score=ConfidenceScore(value=0.5),
        )
        source_repo.save(updated)
        found = source_repo.find_by_id(a_source.source_id)
        assert found is not None
        assert found.source_type == SourceType.KNOWLEDGE

    def test_find_by_id_missing(
        self,
        source_repo: SqlAlchemyResearchSourceRepository,
    ) -> None:
        found = source_repo.find_by_id(
            UUID("00000000-0000-0000-0000-000000000999")
        )
        assert found is None

    def test_find_by_type(
        self,
        source_repo: SqlAlchemyResearchSourceRepository,
        a_source: ResearchSource,
    ) -> None:
        source_repo.save(a_source)
        results = source_repo.find_by_type(SourceType.WEB)
        assert len(results) >= 1
        assert results[0].source_id == a_source.source_id

    def test_find_by_type_empty(
        self,
        source_repo: SqlAlchemyResearchSourceRepository,
    ) -> None:
        results = source_repo.find_by_type(SourceType.KNOWLEDGE)
        assert len(results) == 0

    def test_find_by_job_id(
        self,
        source_repo: SqlAlchemyResearchSourceRepository,
        a_source: ResearchSource,
    ) -> None:
        source_repo.save(a_source)
        results = source_repo.find_by_job_id(ResearchJobId())
        assert isinstance(results, list)

    def test_count(
        self,
        source_repo: SqlAlchemyResearchSourceRepository,
        a_source: ResearchSource,
    ) -> None:
        assert source_repo.count() == 0
        source_repo.save(a_source)
        assert source_repo.count() == 1

    def test_confidence_score_persisted(
        self,
        source_repo: SqlAlchemyResearchSourceRepository,
    ) -> None:
        source = ResearchSource(
            source_id=UUID("00000000-0000-0000-0000-000000000010"),
            source_type=SourceType.DOCUMENT,
            reference=SourceReference(value="doc-ref"),
            confidence_score=ConfidenceScore(value=0.75),
        )
        source_repo.save(source)
        found = source_repo.find_by_id(source.source_id)
        assert found is not None
        assert found.confidence_score is not None
        assert float(found.confidence_score) == 0.75

    def test_source_without_reference(
        self,
        source_repo: SqlAlchemyResearchSourceRepository,
    ) -> None:
        source = ResearchSource(
            source_id=UUID("00000000-0000-0000-0000-000000000020"),
            source_type=SourceType.USER,
        )
        source_repo.save(source)
        found = source_repo.find_by_id(source.source_id)
        assert found is not None
        assert found.reference is None
        assert found.confidence_score is None

    def test_all_source_types(
        self,
        source_repo: SqlAlchemyResearchSourceRepository,
    ) -> None:
        for i, st in enumerate(SourceType):
            s = ResearchSource(
                source_id=UUID(f"00000000-0000-0000-0000-{i+1:012d}"),
                source_type=st,
            )
            source_repo.save(s)
            found = source_repo.find_by_id(s.source_id)
            assert found is not None
            assert found.source_type == st


# ===================================================================
# Outbox adapter integration tests
# ===================================================================


class TestResearchOutboxAdapterIntegration:
    def test_append_and_fetch(
        self,
        outbox_adapter: SqlAlchemyResearchOutboxAdapter,
    ) -> None:
        event = ResearchRequested(
            request_id=ResearchRequestId(),
            query="test query",
            goal="test goal",
            priority="normal",
            occurred_at=NOW,
        )
        outbox_adapter.append(event)
        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], ResearchRequested)

    def test_fifo_ordering(
        self,
        outbox_adapter: SqlAlchemyResearchOutboxAdapter,
    ) -> None:
        t1 = ResearchRequested(
            ResearchRequestId(), "q1", "g1", "normal", NOW
        )
        t2 = ResearchRequested(
            ResearchRequestId(), "q2", "g2", "normal", NOW
        )
        outbox_adapter.append(t1)
        outbox_adapter.append(t2)
        unpublished = outbox_adapter.fetch_unpublished(limit=10)
        assert len(unpublished) == 2

    def test_mark_published(
        self,
        outbox_adapter: SqlAlchemyResearchOutboxAdapter,
        session: Session,
    ) -> None:
        event = ResearchRequested(
            ResearchRequestId(), "q", "g", "normal", NOW
        )
        outbox_adapter.append(event)
        unpublished_before = outbox_adapter.fetch_unpublished()
        assert len(unpublished_before) == 1

        unpublished_before = outbox_adapter.fetch_unpublished()
        outbox_adapter.mark_published(str(unpublished_before[0].event_id))
        session.flush()
        unpublished_after = outbox_adapter.fetch_unpublished()
        assert len(unpublished_after) == 0

    def test_mark_published_idempotent(
        self,
        outbox_adapter: SqlAlchemyResearchOutboxAdapter,
    ) -> None:
        event = ResearchRequested(
            ResearchRequestId(), "q", "g", "normal", NOW
        )
        outbox_adapter.append(event)
        fetched = outbox_adapter.fetch_unpublished()
        outbox_adapter.mark_published(str(fetched[0].event_id))
        outbox_adapter.mark_published(str(fetched[0].event_id))

    def test_fetch_limit(
        self,
        outbox_adapter: SqlAlchemyResearchOutboxAdapter,
    ) -> None:
        for i in range(5):
            event = ResearchRequested(
                ResearchRequestId(), f"q-{i}", "g", "normal", NOW
            )
            outbox_adapter.append(event)
        results = outbox_adapter.fetch_unpublished(limit=3)
        assert len(results) == 3

    def test_empty_outbox(
        self,
        outbox_adapter: SqlAlchemyResearchOutboxAdapter,
    ) -> None:
        results = outbox_adapter.fetch_unpublished()
        assert len(results) == 0

    def test_multiple_event_types(
        self,
        outbox_adapter: SqlAlchemyResearchOutboxAdapter,
    ) -> None:
        rid = ResearchRequestId()
        events = [
            ResearchRequested(rid, "q", "g", "normal", NOW),
            ResearchStarted(rid, NOW),
            ResearchCompleted(rid, NOW),
        ]
        for e in events:
            outbox_adapter.append(e)
        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 3


# ===================================================================
# Multi-entity integration tests
# ===================================================================


class TestMultiEntityIntegration:
    def test_request_job_source_independent_storage(
        self,
        request_repo: SqlAlchemyResearchRequestRepository,
        job_repo: SqlAlchemyResearchJobRepository,
        source_repo: SqlAlchemyResearchSourceRepository,
        a_request: ResearchRequest,
        a_job: ResearchJob,
        a_source: ResearchSource,
    ) -> None:
        request_repo.save(a_request)
        job_repo.save(a_job)
        source_repo.save(a_source)
        found_request = request_repo.find_by_id(a_request.request_id)
        found_job = job_repo.find_by_id(a_job.job_id)
        found_source = source_repo.find_by_id(a_source.source_id)
        assert found_request is not None
        assert found_job is not None
        assert found_source is not None

    def test_sqlite_roundtrip(
        self,
        session: Session,
        request_repo: SqlAlchemyResearchRequestRepository,
        a_request: ResearchRequest,
    ) -> None:
        request_repo.save(a_request)
        session.commit()
        session.expire_all()
        found = request_repo.find_by_id(a_request.request_id)
        assert found is not None
        assert str(found.request_id) == str(a_request.request_id)
        assert str(found.query) == "integration query"
        assert found.priority == ResearchPriority.NORMAL
        assert found.status == ResearchStatus.CREATED

    def test_outbox_with_request_persistence(
        self,
        session: Session,
        request_repo: SqlAlchemyResearchRequestRepository,
        outbox_adapter: SqlAlchemyResearchOutboxAdapter,
        a_request: ResearchRequest,
    ) -> None:
        request_repo.save(a_request)
        event = ResearchRequested(
            request_id=a_request.request_id,
            query=str(a_request.query),
            goal=str(a_request.goal),
            priority=a_request.priority.value,
            occurred_at=NOW,
        )
        outbox_adapter.append(event)
        session.flush()
        found_request = request_repo.find_by_id(a_request.request_id)
        unpublished = outbox_adapter.fetch_unpublished()
        assert found_request is not None
        assert len(unpublished) == 1

    def test_request_status_transitions(
        self,
        request_repo: SqlAlchemyResearchRequestRepository,
        a_request: ResearchRequest,
    ) -> None:
        request_repo.save(a_request)
        a_request.start()
        request_repo.save(a_request)
        found1 = request_repo.find_by_id(a_request.request_id)
        assert found1 is not None and found1.status == ResearchStatus.RUNNING
        job = ResearchJob(
            job_id=ResearchJobId(),
            goal=ResearchGoal(value="job"),
            priority=ResearchPriority.NORMAL,
            status=ResearchStatus.COMPLETED,
            summary=ResearchSummary(value="done"),
            created_at=NOW,
            completed_at=NOW,
        )
        a_request.add_job(job)
        a_request.complete()
        request_repo.save(a_request)
        found2 = request_repo.find_by_id(a_request.request_id)
        assert found2 is not None and found2.status == ResearchStatus.COMPLETED

    def test_multiple_sources_different_types(
        self,
        source_repo: SqlAlchemyResearchSourceRepository,
    ) -> None:
        sources = [
            ResearchSource(
                source_id=UUID(f"00000000-0000-0000-0000-0000000000{i:02d}"),
                source_type=st,
                reference=SourceReference(value=f"ref-{st.value}"),
            )
            for i, st in enumerate(SourceType)
        ]
        for s in sources:
            source_repo.save(s)
        assert source_repo.count() == len(SourceType)
        for s in sources:
            found = source_repo.find_by_id(s.source_id)
            assert found is not None
            assert found.source_type == s.source_type

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.api.endpoints import research as research_router
from backend.core.database import get_db
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
from backend.research.application.use_cases.add_source import AddSourceUseCase
from backend.research.application.use_cases.cancel_request import CancelRequestUseCase
from backend.research.application.use_cases.complete_job import CompleteJobUseCase
from backend.research.application.use_cases.complete_request import CompleteRequestUseCase
from backend.research.application.use_cases.create_job import CreateJobUseCase
from backend.research.application.use_cases.create_request import CreateRequestUseCase
from backend.research.application.use_cases.dto import (
    AddSourceRequest,
    CreateJobRequest,
    CreateRequestRequest,
    FailJobRequest,
    FailRequestRequest,
    GenerateSummaryRequest,
    GetJobRequest,
    GetRequestRequest,
    JobLifecycleRequest,
    ListJobsRequest,
    ListRequestsRequest,
    RequestLifecycleRequest,
)
from backend.research.application.use_cases.exceptions import (
    ResearchJobNotFoundError,
    ResearchRequestNotFoundError,
)
from backend.research.application.use_cases.fail_job import FailJobUseCase
from backend.research.application.use_cases.fail_request import FailRequestUseCase
from backend.research.application.use_cases.generate_summary import GenerateSummaryUseCase
from backend.research.application.use_cases.get_job import GetJobUseCase
from backend.research.application.use_cases.get_request import GetRequestUseCase
from backend.research.application.use_cases.list_jobs import ListJobsUseCase
from backend.research.application.use_cases.list_requests import ListRequestsUseCase
from backend.research.application.use_cases.start_job import StartJobUseCase
from backend.research.application.use_cases.start_request import StartRequestUseCase
from backend.research.domain.exceptions import ResearchDomainError
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

for _table in Base.metadata.tables.values():
    _table.schema = None


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def session() -> Iterator[Session]:
    e = create_engine(
        "sqlite://", echo=False, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=e)
    conn = e.connect()
    transaction = conn.begin()
    s = Session(bind=conn)
    yield s
    s.close()
    transaction.rollback()
    conn.close()
    e.dispose()


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
def request_repo(session: Session) -> SqlAlchemyResearchRequestRepository:
    return SqlAlchemyResearchRequestRepository(session)


@pytest.fixture
def job_repo(session: Session) -> SqlAlchemyResearchJobRepository:
    return SqlAlchemyResearchJobRepository(session)


@pytest.fixture
def source_repo(session: Session) -> SqlAlchemyResearchSourceRepository:
    return SqlAlchemyResearchSourceRepository(session)


@pytest.fixture
def outbox(session: Session) -> SqlAlchemyResearchOutboxAdapter:
    return SqlAlchemyResearchOutboxAdapter(session)


# -- Use case fixtures ------------------------------------------------


@pytest.fixture
def create_request_uc(
    request_repo: SqlAlchemyResearchRequestRepository,
    outbox: SqlAlchemyResearchOutboxAdapter,
) -> CreateRequestUseCase:
    return CreateRequestUseCase(request_repo=request_repo, outbox=outbox)


@pytest.fixture
def start_request_uc(
    request_repo: SqlAlchemyResearchRequestRepository,
    outbox: SqlAlchemyResearchOutboxAdapter,
) -> StartRequestUseCase:
    return StartRequestUseCase(request_repo=request_repo, outbox=outbox)


@pytest.fixture
def complete_request_uc(
    request_repo: SqlAlchemyResearchRequestRepository,
    outbox: SqlAlchemyResearchOutboxAdapter,
) -> CompleteRequestUseCase:
    return CompleteRequestUseCase(request_repo=request_repo, outbox=outbox)


@pytest.fixture
def fail_request_uc(
    request_repo: SqlAlchemyResearchRequestRepository,
    outbox: SqlAlchemyResearchOutboxAdapter,
) -> FailRequestUseCase:
    return FailRequestUseCase(request_repo=request_repo, outbox=outbox)


@pytest.fixture
def cancel_request_uc(
    request_repo: SqlAlchemyResearchRequestRepository,
    outbox: SqlAlchemyResearchOutboxAdapter,
) -> CancelRequestUseCase:
    return CancelRequestUseCase(request_repo=request_repo, outbox=outbox)


@pytest.fixture
def create_job_uc(
    request_repo: SqlAlchemyResearchRequestRepository,
    job_repo: SqlAlchemyResearchJobRepository,
    outbox: SqlAlchemyResearchOutboxAdapter,
) -> CreateJobUseCase:
    return CreateJobUseCase(
        request_repo=request_repo, job_repo=job_repo, outbox=outbox
    )


@pytest.fixture
def start_job_uc(
    job_repo: SqlAlchemyResearchJobRepository,
    outbox: SqlAlchemyResearchOutboxAdapter,
) -> StartJobUseCase:
    return StartJobUseCase(job_repo=job_repo, outbox=outbox)


@pytest.fixture
def complete_job_uc(
    job_repo: SqlAlchemyResearchJobRepository,
    outbox: SqlAlchemyResearchOutboxAdapter,
) -> CompleteJobUseCase:
    return CompleteJobUseCase(job_repo=job_repo, outbox=outbox)


@pytest.fixture
def fail_job_uc(
    job_repo: SqlAlchemyResearchJobRepository,
    outbox: SqlAlchemyResearchOutboxAdapter,
) -> FailJobUseCase:
    return FailJobUseCase(job_repo=job_repo, outbox=outbox)


@pytest.fixture
def add_source_uc(
    job_repo: SqlAlchemyResearchJobRepository,
    source_repo: SqlAlchemyResearchSourceRepository,
    outbox: SqlAlchemyResearchOutboxAdapter,
) -> AddSourceUseCase:
    return AddSourceUseCase(
        job_repo=job_repo, source_repo=source_repo, outbox=outbox
    )


@pytest.fixture
def generate_summary_uc(
    job_repo: SqlAlchemyResearchJobRepository,
    outbox: SqlAlchemyResearchOutboxAdapter,
) -> GenerateSummaryUseCase:
    return GenerateSummaryUseCase(job_repo=job_repo, outbox=outbox)


@pytest.fixture
def get_request_uc(
    request_repo: SqlAlchemyResearchRequestRepository,
) -> GetRequestUseCase:
    return GetRequestUseCase(request_repo=request_repo)


@pytest.fixture
def list_requests_uc(
    request_repo: SqlAlchemyResearchRequestRepository,
) -> ListRequestsUseCase:
    return ListRequestsUseCase(request_repo=request_repo)


@pytest.fixture
def get_job_uc(
    job_repo: SqlAlchemyResearchJobRepository,
) -> GetJobUseCase:
    return GetJobUseCase(job_repo=job_repo)


@pytest.fixture
def list_jobs_uc(
    job_repo: SqlAlchemyResearchJobRepository,
) -> ListJobsUseCase:
    return ListJobsUseCase(job_repo=job_repo)


# -- Helper -----------------------------------------------------------


def _create_request(
    create_request_uc: CreateRequestUseCase,
    query: str = "integration query",
    goal: str = "integration goal",
    priority: str = "normal",
) -> tuple[str, str, str]:
    resp = create_request_uc.execute(
        CreateRequestRequest(query=query, goal=goal, priority=priority)
    )
    return resp.request_id, resp.status, resp.priority


def _create_job(
    create_job_uc: CreateJobUseCase, request_id: str, goal: str = "job goal"
) -> str:
    resp = create_job_uc.execute(
        CreateJobRequest(request_id=request_id, goal=goal)
    )
    return resp.job_id


# ===================================================================
# Request lifecycle
# ===================================================================


class TestRequestLifecycle:
    def test_full_lifecycle(
        self,
        create_request_uc: CreateRequestUseCase,
        start_request_uc: StartRequestUseCase,
        create_job_uc: CreateJobUseCase,
        start_job_uc: StartJobUseCase,
        add_source_uc: AddSourceUseCase,
        generate_summary_uc: GenerateSummaryUseCase,
    ) -> None:
        rid, status, _ = _create_request(create_request_uc)
        assert status == "created"
        start_request_uc.execute(RequestLifecycleRequest(request_id=rid))
        jid = _create_job(create_job_uc, rid)
        start_job_uc.execute(JobLifecycleRequest(job_id=jid))
        add_source_uc.execute(
            AddSourceRequest(
                job_id=jid,
                reference="https://example.com",
                source_type="web",
                confidence_score=0.8,
            )
        )
        resp = generate_summary_uc.execute(
            GenerateSummaryRequest(job_id=jid, summary="research done")
        )
        assert resp.job_id == jid
        assert resp.summary == "research done"

    def test_request_created_has_correct_priority(
        self, create_request_uc: CreateRequestUseCase
    ) -> None:
        _, _, priority = _create_request(
            create_request_uc, priority="high"
        )
        assert priority == "high"

    def test_start_transition(
        self,
        create_request_uc: CreateRequestUseCase,
        start_request_uc: StartRequestUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        resp = start_request_uc.execute(
            RequestLifecycleRequest(request_id=rid)
        )
        assert resp.status == "running"

    def test_start_not_found(
        self, start_request_uc: StartRequestUseCase
    ) -> None:
        with pytest.raises(ResearchRequestNotFoundError):
            start_request_uc.execute(
                RequestLifecycleRequest(
                    request_id="00000000-0000-0000-0000-000000000001"
                )
            )

    def test_start_already_started(
        self,
        create_request_uc: CreateRequestUseCase,
        start_request_uc: StartRequestUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        start_request_uc.execute(RequestLifecycleRequest(request_id=rid))
        with pytest.raises(ResearchDomainError):
            start_request_uc.execute(
                RequestLifecycleRequest(request_id=rid)
            )

    def test_fail_from_running(
        self,
        create_request_uc: CreateRequestUseCase,
        start_request_uc: StartRequestUseCase,
        fail_request_uc: FailRequestUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        start_request_uc.execute(RequestLifecycleRequest(request_id=rid))
        resp = fail_request_uc.execute(
            FailRequestRequest(
                request_id=rid, failure_reason="research error"
            )
        )
        assert resp.status == "failed"
        assert resp.failure_reason == "research error"

    def test_fail_not_found(
        self, fail_request_uc: FailRequestUseCase
    ) -> None:
        with pytest.raises(ResearchRequestNotFoundError):
            fail_request_uc.execute(
                FailRequestRequest(
                    request_id="00000000-0000-0000-0000-000000000001",
                    failure_reason="error",
                )
            )

    def test_cancel_from_created(
        self,
        create_request_uc: CreateRequestUseCase,
        cancel_request_uc: CancelRequestUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        resp = cancel_request_uc.execute(
            RequestLifecycleRequest(request_id=rid)
        )
        assert resp.status == "cancelled"

    def test_cancel_not_found(
        self, cancel_request_uc: CancelRequestUseCase
    ) -> None:
        with pytest.raises(ResearchRequestNotFoundError):
            cancel_request_uc.execute(
                RequestLifecycleRequest(
                    request_id="00000000-0000-0000-0000-000000000001"
                )
            )

    def test_cancel_already_cancelled(
        self,
        create_request_uc: CreateRequestUseCase,
        cancel_request_uc: CancelRequestUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        cancel_request_uc.execute(RequestLifecycleRequest(request_id=rid))
        with pytest.raises(ResearchDomainError):
            cancel_request_uc.execute(
                RequestLifecycleRequest(request_id=rid)
            )

    def test_fail_before_start(
        self,
        create_request_uc: CreateRequestUseCase,
        fail_request_uc: FailRequestUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        with pytest.raises(ResearchDomainError):
            fail_request_uc.execute(
                FailRequestRequest(
                    request_id=rid, failure_reason="error"
                )
            )


# ===================================================================
# Job lifecycle
# ===================================================================


class TestJobLifecycle:
    def test_create_job(
        self,
        create_request_uc: CreateRequestUseCase,
        create_job_uc: CreateJobUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        jid = _create_job(create_job_uc, rid)
        assert jid is not None

    def test_create_job_request_not_found(
        self, create_job_uc: CreateJobUseCase
    ) -> None:
        with pytest.raises(ResearchRequestNotFoundError):
            create_job_uc.execute(
                CreateJobRequest(
                    request_id="00000000-0000-0000-0000-000000000001",
                    goal="goal",
                )
            )

    def test_start_job(
        self,
        create_request_uc: CreateRequestUseCase,
        create_job_uc: CreateJobUseCase,
        start_job_uc: StartJobUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        jid = _create_job(create_job_uc, rid)
        resp = start_job_uc.execute(JobLifecycleRequest(job_id=jid))
        assert resp.status == "running"

    def test_start_job_not_found(
        self, start_job_uc: StartJobUseCase
    ) -> None:
        with pytest.raises(ResearchJobNotFoundError):
            start_job_uc.execute(
                JobLifecycleRequest(
                    job_id="00000000-0000-0000-0000-000000000001"
                )
            )

    def test_double_start_job(
        self,
        create_request_uc: CreateRequestUseCase,
        create_job_uc: CreateJobUseCase,
        start_job_uc: StartJobUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        jid = _create_job(create_job_uc, rid)
        start_job_uc.execute(JobLifecycleRequest(job_id=jid))
        with pytest.raises(ResearchDomainError):
            start_job_uc.execute(JobLifecycleRequest(job_id=jid))

    def test_complete_job(
        self,
        create_request_uc: CreateRequestUseCase,
        create_job_uc: CreateJobUseCase,
        start_job_uc: StartJobUseCase,
        complete_job_uc: CompleteJobUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        jid = _create_job(create_job_uc, rid)
        start_job_uc.execute(JobLifecycleRequest(job_id=jid))
        resp = complete_job_uc.execute(
            GenerateSummaryRequest(job_id=jid, summary="complete")
        )
        assert resp.status == "completed"

    def test_complete_job_not_found(
        self, complete_job_uc: CompleteJobUseCase
    ) -> None:
        with pytest.raises(ResearchJobNotFoundError):
            complete_job_uc.execute(
                GenerateSummaryRequest(
                    job_id="00000000-0000-0000-0000-000000000001",
                    summary="done",
                )
            )

    def test_complete_job_before_start(
        self,
        create_request_uc: CreateRequestUseCase,
        create_job_uc: CreateJobUseCase,
        complete_job_uc: CompleteJobUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        jid = _create_job(create_job_uc, rid)
        with pytest.raises(ResearchDomainError):
            complete_job_uc.execute(
                GenerateSummaryRequest(job_id=jid, summary="done")
            )

    def test_fail_job_from_created(
        self,
        create_request_uc: CreateRequestUseCase,
        create_job_uc: CreateJobUseCase,
        start_job_uc: StartJobUseCase,
        fail_job_uc: FailJobUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        jid = _create_job(create_job_uc, rid)
        start_job_uc.execute(JobLifecycleRequest(job_id=jid))
        resp = fail_job_uc.execute(
            FailJobRequest(job_id=jid, failure_reason="job error")
        )
        assert resp.status == "failed"

    def test_fail_job_not_found(
        self, fail_job_uc: FailJobUseCase
    ) -> None:
        with pytest.raises(ResearchJobNotFoundError):
            fail_job_uc.execute(
                FailJobRequest(
                    job_id="00000000-0000-0000-0000-000000000001",
                    failure_reason="error",
                )
            )

    def test_fail_job_before_start(
        self,
        create_request_uc: CreateRequestUseCase,
        create_job_uc: CreateJobUseCase,
        fail_job_uc: FailJobUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        jid = _create_job(create_job_uc, rid)
        with pytest.raises(ResearchDomainError):
            fail_job_uc.execute(
                FailJobRequest(job_id=jid, failure_reason="error")
            )

    def test_fail_job_empty_reason(
        self,
        create_request_uc: CreateRequestUseCase,
        create_job_uc: CreateJobUseCase,
        start_job_uc: StartJobUseCase,
        fail_job_uc: FailJobUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        jid = _create_job(create_job_uc, rid)
        start_job_uc.execute(JobLifecycleRequest(job_id=jid))
        with pytest.raises(ResearchDomainError):
            fail_job_uc.execute(
                FailJobRequest(job_id=jid, failure_reason="")
            )


# ===================================================================
# Source management
# ===================================================================


class TestSourceManagement:
    def test_add_source(
        self,
        create_request_uc: CreateRequestUseCase,
        create_job_uc: CreateJobUseCase,
        start_job_uc: StartJobUseCase,
        add_source_uc: AddSourceUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        jid = _create_job(create_job_uc, rid)
        start_job_uc.execute(JobLifecycleRequest(job_id=jid))
        resp = add_source_uc.execute(
            AddSourceRequest(
                job_id=jid,
                reference="https://example.com",
                source_type="web",
                confidence_score=0.85,
            )
        )
        assert resp.source_type == "web"
        assert resp.confidence_score == 0.85

    def test_add_source_job_not_found(
        self, add_source_uc: AddSourceUseCase
    ) -> None:
        with pytest.raises(ResearchJobNotFoundError):
            add_source_uc.execute(
                AddSourceRequest(
                    job_id="00000000-0000-0000-0000-000000000001",
                    reference="https://example.com",
                    source_type="web",
                    confidence_score=0.5,
                )
            )

    def test_add_source_invalid_confidence(
        self,
        create_request_uc: CreateRequestUseCase,
        create_job_uc: CreateJobUseCase,
        start_job_uc: StartJobUseCase,
        add_source_uc: AddSourceUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        jid = _create_job(create_job_uc, rid)
        start_job_uc.execute(JobLifecycleRequest(job_id=jid))
        with pytest.raises(ResearchDomainError):
            add_source_uc.execute(
                AddSourceRequest(
                    job_id=jid,
                    reference="https://example.com",
                    source_type="web",
                    confidence_score=1.5,
                )
            )

    def test_generate_summary(
        self,
        create_request_uc: CreateRequestUseCase,
        create_job_uc: CreateJobUseCase,
        start_job_uc: StartJobUseCase,
        generate_summary_uc: GenerateSummaryUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        jid = _create_job(create_job_uc, rid)
        start_job_uc.execute(JobLifecycleRequest(job_id=jid))
        resp = generate_summary_uc.execute(
            GenerateSummaryRequest(job_id=jid, summary="great research")
        )
        assert resp.summary == "great research"
        assert resp.status == "completed"

    def test_generate_summary_not_found(
        self, generate_summary_uc: GenerateSummaryUseCase
    ) -> None:
        with pytest.raises(ResearchJobNotFoundError):
            generate_summary_uc.execute(
                GenerateSummaryRequest(
                    job_id="00000000-0000-0000-0000-000000000001",
                    summary="summary",
                )
            )

    def test_generate_summary_empty(
        self,
        create_request_uc: CreateRequestUseCase,
        create_job_uc: CreateJobUseCase,
        start_job_uc: StartJobUseCase,
        generate_summary_uc: GenerateSummaryUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        jid = _create_job(create_job_uc, rid)
        start_job_uc.execute(JobLifecycleRequest(job_id=jid))
        with pytest.raises(ResearchDomainError):
            generate_summary_uc.execute(
                GenerateSummaryRequest(job_id=jid, summary="")
            )

    def test_generate_summary_before_start(
        self,
        create_request_uc: CreateRequestUseCase,
        create_job_uc: CreateJobUseCase,
        generate_summary_uc: GenerateSummaryUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        jid = _create_job(create_job_uc, rid)
        with pytest.raises(ResearchDomainError):
            generate_summary_uc.execute(
                GenerateSummaryRequest(job_id=jid, summary="summary")
            )


# ===================================================================
# Repository roundtrip
# ===================================================================


class TestRepositoryRoundtrip:
    def test_request_domain_dto_orm_db_roundtrip(
        self,
        session: Session,
        request_repo: SqlAlchemyResearchRequestRepository,
        request_mapper: ResearchRequestMapperImpl,
    ) -> None:
        original = ResearchRequest(
            request_id=ResearchRequestId(),
            query=QueryText(value="roundtrip query"),
            goal=ResearchGoal(value="roundtrip goal"),
            priority=ResearchPriority.HIGH,
            created_at=NOW,
        )
        request_repo.save(original)
        session.commit()
        session.expire_all()
        found = request_repo.find_by_id(original.request_id)
        assert found is not None
        assert str(found.query) == "roundtrip query"
        assert found.priority == ResearchPriority.HIGH
        assert found.status == ResearchStatus.CREATED

    def test_job_domain_dto_orm_db_roundtrip(
        self,
        session: Session,
        job_repo: SqlAlchemyResearchJobRepository,
        job_mapper: ResearchJobMapperImpl,
    ) -> None:
        original = ResearchJob(
            job_id=ResearchJobId(),
            goal=ResearchGoal(value="job roundtrip"),
            status=ResearchStatus.CREATED,
            priority=ResearchPriority.CRITICAL,
            created_at=NOW,
        )
        job_repo.save(original)
        session.commit()
        session.expire_all()
        found = job_repo.find_by_id(original.job_id)
        assert found is not None
        assert str(found.goal) == "job roundtrip"
        assert found.priority == ResearchPriority.CRITICAL

    def test_source_domain_dto_orm_db_roundtrip(
        self,
        session: Session,
        source_repo: SqlAlchemyResearchSourceRepository,
        source_mapper: ResearchSourceMapperImpl,
    ) -> None:
        original = ResearchSource(
            source_id=UUID("00000000-0000-0000-0000-000000000001"),
            source_type=SourceType.DOCUMENT,
            reference=SourceReference(value="doc-ref"),
            confidence_score=ConfidenceScore(value=0.75),
        )
        source_repo.save(original)
        session.commit()
        session.expire_all()
        found = source_repo.find_by_id(original.source_id)
        assert found is not None
        assert found.source_type == SourceType.DOCUMENT
        assert float(found.confidence_score) == 0.75

    def test_request_field_preservation(
        self,
        session: Session,
        request_repo: SqlAlchemyResearchRequestRepository,
    ) -> None:
        original = ResearchRequest(
            request_id=ResearchRequestId(),
            query=QueryText(value="field test"),
            goal=ResearchGoal(value="field goal"),
            priority=ResearchPriority.LOW,
            created_at=NOW,
        )
        request_repo.save(original)
        session.commit()
        session.expire_all()
        found = request_repo.find_by_id(original.request_id)
        assert found is not None
        assert str(found.query) == "field test"
        assert str(found.goal) == "field goal"
        assert found.priority == ResearchPriority.LOW
        assert found.status == ResearchStatus.CREATED
        assert found.failure_reason is None

    def test_job_field_preservation(
        self,
        session: Session,
        job_repo: SqlAlchemyResearchJobRepository,
    ) -> None:
        original = ResearchJob(
            job_id=ResearchJobId(),
            goal=ResearchGoal(value="job fields"),
            status=ResearchStatus.COMPLETED,
            priority=ResearchPriority.HIGH,
            summary=ResearchSummary(value="job complete"),
            created_at=NOW,
            completed_at=NOW,
        )
        job_repo.save(original)
        session.commit()
        session.expire_all()
        found = job_repo.find_by_id(original.job_id)
        assert found is not None
        assert str(found.goal) == "job fields"
        assert found.status == ResearchStatus.COMPLETED
        assert found.completed_at is not None

    def test_source_field_preservation(
        self,
        session: Session,
        source_repo: SqlAlchemyResearchSourceRepository,
    ) -> None:
        original = ResearchSource(
            source_id=UUID("00000000-0000-0000-0000-000000000002"),
            source_type=SourceType.KNOWLEDGE,
            reference=SourceReference(value="kb-ref"),
            confidence_score=ConfidenceScore(value=0.9),
        )
        source_repo.save(original)
        session.commit()
        session.expire_all()
        found = source_repo.find_by_id(original.source_id)
        assert found is not None
        assert found.source_type == SourceType.KNOWLEDGE
        assert str(found.reference) == "kb-ref"
        assert float(found.confidence_score) == 0.9


# ===================================================================
# Outbox lifecycle
# ===================================================================


class TestOutboxLifecycle:
    def test_append_and_fetch(
        self,
        create_request_uc: CreateRequestUseCase,
        outbox: SqlAlchemyResearchOutboxAdapter,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) >= 1
        assert any(isinstance(e, ResearchRequested) for e in unpublished)

    def test_mark_published(
        self,
        create_request_uc: CreateRequestUseCase,
        outbox: SqlAlchemyResearchOutboxAdapter,
        session: Session,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) >= 1
        outbox.mark_published(str(unpublished[0].event_id))
        session.flush()
        after = outbox.fetch_unpublished()
        published_ids = {str(e.request_id) for e in after}
        assert str(unpublished[0].request_id) not in published_ids

    def test_mark_published_idempotent(
        self,
        create_request_uc: CreateRequestUseCase,
        outbox: SqlAlchemyResearchOutboxAdapter,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        unpublished = outbox.fetch_unpublished()
        eid = str(unpublished[0].event_id)
        outbox.mark_published(eid)
        outbox.mark_published(eid)

    def test_fetch_limit(
        self,
        create_request_uc: CreateRequestUseCase,
        outbox: SqlAlchemyResearchOutboxAdapter,
    ) -> None:
        for _ in range(3):
            _create_request(create_request_uc)
        results = outbox.fetch_unpublished(limit=2)
        assert len(results) == 2

    def test_empty_outbox(
        self, outbox: SqlAlchemyResearchOutboxAdapter
    ) -> None:
        results = outbox.fetch_unpublished()
        assert len(results) == 0


# ===================================================================
# FIFO ordering
# ===================================================================


class TestFifoOrdering:
    def test_requests_fifo(
        self,
        create_request_uc: CreateRequestUseCase,
        outbox: SqlAlchemyResearchOutboxAdapter,
    ) -> None:
        r1, _, _ = _create_request(create_request_uc, query="first")
        r2, _, _ = _create_request(create_request_uc, query="second")
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) >= 2

    def test_multiple_jobs_fifo(
        self,
        create_request_uc: CreateRequestUseCase,
        create_job_uc: CreateJobUseCase,
        start_job_uc: StartJobUseCase,
        outbox: SqlAlchemyResearchOutboxAdapter,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        start_request_uc = StartRequestUseCase(
            request_repo=SqlAlchemyResearchRequestRepository(
                outbox._session
            ),
            outbox=outbox,
        )
        start_request_uc.execute(RequestLifecycleRequest(request_id=rid))
        jid1 = _create_job(create_job_uc, rid)
        start_job_uc.execute(JobLifecycleRequest(job_id=jid1))
        jid2 = _create_job(create_job_uc, rid)
        start_job_uc.execute(JobLifecycleRequest(job_id=jid2))
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) >= 2


# ===================================================================
# Query filtering
# ===================================================================


class TestQueryFiltering:
    def test_list_requests_by_status(
        self,
        create_request_uc: CreateRequestUseCase,
        list_requests_uc: ListRequestsUseCase,
    ) -> None:
        _create_request(create_request_uc)
        resp = list_requests_uc.execute(
            ListRequestsRequest(status="created")
        )
        assert len(resp.requests) >= 1
        assert resp.total >= 1

    def test_list_requests_by_priority(
        self,
        create_request_uc: CreateRequestUseCase,
        list_requests_uc: ListRequestsUseCase,
    ) -> None:
        _create_request(create_request_uc, priority="high")
        resp = list_requests_uc.execute(
            ListRequestsRequest(priority="high")
        )
        assert len(resp.requests) >= 1

    def test_list_requests_no_match(
        self,
        list_requests_uc: ListRequestsUseCase,
    ) -> None:
        resp = list_requests_uc.execute(
            ListRequestsRequest(status="completed")
        )
        assert len(resp.requests) == 0
        assert resp.total == 0

    def test_list_requests_all(
        self,
        create_request_uc: CreateRequestUseCase,
        request_repo: SqlAlchemyResearchRequestRepository,
    ) -> None:
        _create_request(create_request_uc, query="A")
        _create_request(create_request_uc, query="B")
        all_requests = request_repo.find_by_status(ResearchStatus.CREATED)
        assert len(all_requests) >= 2

    def test_list_jobs_by_status(
        self,
        create_request_uc: CreateRequestUseCase,
        create_job_uc: CreateJobUseCase,
        list_jobs_uc: ListJobsUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        _create_job(create_job_uc, rid)
        resp = list_jobs_uc.execute(ListJobsRequest(status="created"))
        assert len(resp.jobs) >= 1

    def test_list_jobs_no_match(
        self, list_jobs_uc: ListJobsUseCase
    ) -> None:
        resp = list_jobs_uc.execute(
            ListJobsRequest(status="completed")
        )
        assert len(resp.jobs) == 0

    def test_list_jobs_all(
        self,
        create_request_uc: CreateRequestUseCase,
        start_request_uc: StartRequestUseCase,
        create_job_uc: CreateJobUseCase,
        job_repo: SqlAlchemyResearchJobRepository,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        start_request_uc.execute(RequestLifecycleRequest(request_id=rid))
        _create_job(create_job_uc, rid)
        all_jobs = job_repo.find_by_status(ResearchStatus.CREATED)
        assert len(all_jobs) >= 1

    def test_list_jobs_by_request_id(
        self,
        create_request_uc: CreateRequestUseCase,
        create_job_uc: CreateJobUseCase,
        list_jobs_uc: ListJobsUseCase,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        _create_job(create_job_uc, rid)
        resp = list_jobs_uc.execute(
            ListJobsRequest(request_id=rid)
        )
        assert isinstance(resp.jobs, list)


# ===================================================================
# Event coverage
# ===================================================================


class TestEventCoverage:
    def test_create_emits_requested(
        self,
        create_request_uc: CreateRequestUseCase,
        outbox: SqlAlchemyResearchOutboxAdapter,
    ) -> None:
        _create_request(create_request_uc)
        events = outbox.fetch_unpublished()
        assert any(isinstance(e, ResearchRequested) for e in events)

    def test_start_emits_started(
        self,
        create_request_uc: CreateRequestUseCase,
        outbox: SqlAlchemyResearchOutboxAdapter,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        start_uc = StartRequestUseCase(
            request_repo=SqlAlchemyResearchRequestRepository(
                outbox._session
            ),
            outbox=outbox,
        )
        start_uc.execute(RequestLifecycleRequest(request_id=rid))
        events = outbox.fetch_unpublished()
        assert any(isinstance(e, ResearchStarted) for e in events)

    def test_complete_request_emits_completed(
        self,
        outbox: SqlAlchemyResearchOutboxAdapter,
        clock: SystemClockAdapter,
    ) -> None:
        event = ResearchCompleted(
            request_id=ResearchRequestId(),
            occurred_at=clock.now(),
        )
        outbox.append(event)
        events = outbox.fetch_unpublished()
        assert any(isinstance(e, ResearchCompleted) for e in events)

    def test_fail_emits_failed(
        self,
        create_request_uc: CreateRequestUseCase,
        outbox: SqlAlchemyResearchOutboxAdapter,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        start_uc = StartRequestUseCase(
            request_repo=SqlAlchemyResearchRequestRepository(
                outbox._session
            ),
            outbox=outbox,
        )
        start_uc.execute(RequestLifecycleRequest(request_id=rid))
        fail_uc = FailRequestUseCase(
            request_repo=SqlAlchemyResearchRequestRepository(
                outbox._session
            ),
            outbox=outbox,
        )
        fail_uc.execute(
            FailRequestRequest(
                request_id=rid, failure_reason="error"
            )
        )
        events = outbox.fetch_unpublished()
        assert any(isinstance(e, ResearchFailed) for e in events)

    def test_cancel_emits_cancelled(
        self,
        create_request_uc: CreateRequestUseCase,
        outbox: SqlAlchemyResearchOutboxAdapter,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        cancel_uc = CancelRequestUseCase(
            request_repo=SqlAlchemyResearchRequestRepository(
                outbox._session
            ),
            outbox=outbox,
        )
        cancel_uc.execute(RequestLifecycleRequest(request_id=rid))
        events = outbox.fetch_unpublished()
        assert any(isinstance(e, ResearchCancelled) for e in events)

    def test_add_source_emits_source_added(
        self,
        create_request_uc: CreateRequestUseCase,
        outbox: SqlAlchemyResearchOutboxAdapter,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        start_uc = StartRequestUseCase(
            request_repo=SqlAlchemyResearchRequestRepository(
                outbox._session
            ),
            outbox=outbox,
        )
        start_uc.execute(RequestLifecycleRequest(request_id=rid))
        jid = _create_job(
            CreateJobUseCase(
                request_repo=SqlAlchemyResearchRequestRepository(
                    outbox._session
                ),
                job_repo=SqlAlchemyResearchJobRepository(
                    outbox._session
                ),
                outbox=outbox,
            ),
            rid,
        )
        start_job_uc = StartJobUseCase(
            job_repo=SqlAlchemyResearchJobRepository(
                outbox._session
            ),
            outbox=outbox,
        )
        start_job_uc.execute(JobLifecycleRequest(job_id=jid))
        add_uc = AddSourceUseCase(
            job_repo=SqlAlchemyResearchJobRepository(
                outbox._session
            ),
            source_repo=SqlAlchemyResearchSourceRepository(
                outbox._session
            ),
            outbox=outbox,
        )
        add_uc.execute(
            AddSourceRequest(
                job_id=jid,
                reference="https://example.com",
                source_type="web",
                confidence_score=0.8,
            )
        )
        events = outbox.fetch_unpublished()
        assert any(isinstance(e, SourceAdded) for e in events)

    def test_generate_summary_emits_summary_generated(
        self,
        create_request_uc: CreateRequestUseCase,
        outbox: SqlAlchemyResearchOutboxAdapter,
    ) -> None:
        rid, _, _ = _create_request(create_request_uc)
        start_uc = StartRequestUseCase(
            request_repo=SqlAlchemyResearchRequestRepository(
                outbox._session
            ),
            outbox=outbox,
        )
        start_uc.execute(RequestLifecycleRequest(request_id=rid))
        jid = _create_job(
            CreateJobUseCase(
                request_repo=SqlAlchemyResearchRequestRepository(
                    outbox._session
                ),
                job_repo=SqlAlchemyResearchJobRepository(
                    outbox._session
                ),
                outbox=outbox,
            ),
            rid,
        )
        start_job_uc = StartJobUseCase(
            job_repo=SqlAlchemyResearchJobRepository(
                outbox._session
            ),
            outbox=outbox,
        )
        start_job_uc.execute(JobLifecycleRequest(job_id=jid))
        gen_uc = GenerateSummaryUseCase(
            job_repo=SqlAlchemyResearchJobRepository(
                outbox._session
            ),
            outbox=outbox,
        )
        gen_uc.execute(
            GenerateSummaryRequest(job_id=jid, summary="research complete")
        )
        events = outbox.fetch_unpublished()
        assert any(
            isinstance(e, ResearchSummaryGenerated) for e in events
        )


# ===================================================================
# REST contracts
# ===================================================================


@pytest.fixture
def api_client(session: Session):
    def _override_get_db():
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    app = FastAPI()
    app.include_router(research_router.router, prefix="/api/v1/research")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


class TestRestContracts:
    def test_create_request_201(
        self, api_client: TestClient
    ) -> None:
        resp = api_client.post(
            "/api/v1/research/requests",
            json={"query": "q", "goal": "g", "priority": "normal"},
        )
        assert resp.status_code == 201
        assert "request_id" in resp.json()

    def test_create_request_422_empty(
        self, api_client: TestClient
    ) -> None:
        resp = api_client.post(
            "/api/v1/research/requests",
            json={"query": "", "goal": "", "priority": "normal"},
        )
        assert resp.status_code == 422

    def test_get_request_200(
        self, api_client: TestClient
    ) -> None:
        rid = api_client.post(
            "/api/v1/research/requests",
            json={"query": "q", "goal": "g", "priority": "normal"},
        ).json()["request_id"]
        resp = api_client.get(f"/api/v1/research/requests/{rid}")
        assert resp.status_code == 200
        assert resp.json()["request_id"] == rid

    def test_get_request_404(
        self, api_client: TestClient
    ) -> None:
        resp = api_client.get(
            "/api/v1/research/requests/00000000-0000-0000-0000-000000000999"
        )
        assert resp.status_code == 404

    def test_list_requests_200(
        self, api_client: TestClient
    ) -> None:
        resp = api_client.get("/api/v1/research/requests")
        assert resp.status_code == 200

    def test_start_request_200(
        self, api_client: TestClient
    ) -> None:
        rid = api_client.post(
            "/api/v1/research/requests",
            json={"query": "q", "goal": "g", "priority": "normal"},
        ).json()["request_id"]
        resp = api_client.post(
            f"/api/v1/research/requests/{rid}/start"
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_start_request_404(
        self, api_client: TestClient
    ) -> None:
        resp = api_client.post(
            "/api/v1/research/requests/00000000-0000-0000-0000-000000000999/start"
        )
        assert resp.status_code == 404

    def test_fail_request_200(
        self, api_client: TestClient
    ) -> None:
        rid = api_client.post(
            "/api/v1/research/requests",
            json={"query": "q", "goal": "g", "priority": "normal"},
        ).json()["request_id"]
        api_client.post(f"/api/v1/research/requests/{rid}/start")
        resp = api_client.post(
            f"/api/v1/research/requests/{rid}/fail",
            json={"failure_reason": "err"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_cancel_request_200(
        self, api_client: TestClient
    ) -> None:
        rid = api_client.post(
            "/api/v1/research/requests",
            json={"query": "q", "goal": "g", "priority": "normal"},
        ).json()["request_id"]
        resp = api_client.post(
            f"/api/v1/research/requests/{rid}/cancel"
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_create_job_201(
        self, api_client: TestClient
    ) -> None:
        rid = api_client.post(
            "/api/v1/research/requests",
            json={"query": "q", "goal": "g", "priority": "normal"},
        ).json()["request_id"]
        resp = api_client.post(
            f"/api/v1/research/requests/{rid}/jobs",
            json={"goal": "job goal"},
        )
        assert resp.status_code == 201
        assert "job_id" in resp.json()

    def test_create_job_404(
        self, api_client: TestClient
    ) -> None:
        resp = api_client.post(
            "/api/v1/research/requests/00000000-0000-0000-0000-000000000999/jobs",
            json={"goal": "job goal"},
        )
        assert resp.status_code == 404

    def test_start_job_200(
        self, api_client: TestClient
    ) -> None:
        rid = api_client.post(
            "/api/v1/research/requests",
            json={"query": "q", "goal": "g", "priority": "normal"},
        ).json()["request_id"]
        jid = api_client.post(
            f"/api/v1/research/requests/{rid}/jobs",
            json={"goal": "job goal"},
        ).json()["job_id"]
        resp = api_client.post(
            f"/api/v1/research/jobs/{jid}/start"
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_fail_job_200(
        self, api_client: TestClient
    ) -> None:
        rid = api_client.post(
            "/api/v1/research/requests",
            json={"query": "q", "goal": "g", "priority": "normal"},
        ).json()["request_id"]
        jid = api_client.post(
            f"/api/v1/research/requests/{rid}/jobs",
            json={"goal": "job goal"},
        ).json()["job_id"]
        api_client.post(f"/api/v1/research/jobs/{jid}/start")
        resp = api_client.post(
            f"/api/v1/research/jobs/{jid}/fail",
            json={"failure_reason": "err"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_get_job_200(
        self, api_client: TestClient
    ) -> None:
        rid = api_client.post(
            "/api/v1/research/requests",
            json={"query": "q", "goal": "g", "priority": "normal"},
        ).json()["request_id"]
        jid = api_client.post(
            f"/api/v1/research/requests/{rid}/jobs",
            json={"goal": "job goal"},
        ).json()["job_id"]
        resp = api_client.get(f"/api/v1/research/jobs/{jid}")
        assert resp.status_code == 200
        assert resp.json()["job_id"] == jid

    def test_get_job_404(
        self, api_client: TestClient
    ) -> None:
        resp = api_client.get(
            "/api/v1/research/jobs/00000000-0000-0000-0000-000000000999"
        )
        assert resp.status_code == 404

    def test_list_jobs_200(
        self, api_client: TestClient
    ) -> None:
        resp = api_client.get("/api/v1/research/jobs")
        assert resp.status_code == 200

    def test_add_source_201(
        self, api_client: TestClient
    ) -> None:
        rid = api_client.post(
            "/api/v1/research/requests",
            json={"query": "q", "goal": "g", "priority": "normal"},
        ).json()["request_id"]
        jid = api_client.post(
            f"/api/v1/research/requests/{rid}/jobs",
            json={"goal": "job goal"},
        ).json()["job_id"]
        api_client.post(f"/api/v1/research/jobs/{jid}/start")
        resp = api_client.post(
            f"/api/v1/research/jobs/{jid}/sources",
            json={
                "reference": "https://example.com",
                "source_type": "web",
                "confidence_score": 0.8,
            },
        )
        assert resp.status_code == 201

    def test_generate_summary_200(
        self, api_client: TestClient
    ) -> None:
        rid = api_client.post(
            "/api/v1/research/requests",
            json={"query": "q", "goal": "g", "priority": "normal"},
        ).json()["request_id"]
        jid = api_client.post(
            f"/api/v1/research/requests/{rid}/jobs",
            json={"goal": "job goal"},
        ).json()["job_id"]
        api_client.post(f"/api/v1/research/jobs/{jid}/start")
        resp = api_client.post(
            f"/api/v1/research/jobs/{jid}/summary",
            json={"summary": "great research"},
        )
        assert resp.status_code == 200
        assert resp.json()["summary"] == "great research"

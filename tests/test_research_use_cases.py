from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

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
    UseCaseError,
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
    ResearchStarted,
    ResearchStatus,
    ResearchSummaryGenerated,
    SourceAdded,
)

# =========================================================================
# Stub repositories & ports
# =========================================================================


class StubRequestRepo:
    def __init__(self) -> None:
        self._store: dict[str, ResearchRequest] = {}

    def save(self, request: ResearchRequest) -> None:
        self._store[str(request.request_id)] = request

    def find_by_id(self, request_id: ResearchRequestId) -> ResearchRequest | None:
        return self._store.get(str(request_id))

    def find_by_status(self, status: ResearchStatus) -> list[ResearchRequest]:
        return [r for r in self._store.values() if r.status == status]

    def find_by_priority(self, priority: ResearchPriority) -> list[ResearchRequest]:
        return [r for r in self._store.values() if r.priority == priority]

    def count(self) -> int:
        return len(self._store)


class StubJobRepo:
    def __init__(self) -> None:
        self._store: dict[str, ResearchJob] = {}

    def save(self, job: ResearchJob) -> None:
        self._store[str(job.job_id)] = job

    def find_by_id(self, job_id: ResearchJobId) -> ResearchJob | None:
        return self._store.get(str(job_id))

    def find_by_status(self, status: ResearchStatus) -> list[ResearchJob]:
        return [j for j in self._store.values() if j.status == status]

    def find_by_request_id(self, request_id: ResearchRequestId) -> list[ResearchJob]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class StubSourceRepo:
    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    def save(self, source: object) -> None:
        self._store[str(id(source))] = source

    def find_by_id(self, source_id: UUID) -> object | None:
        return None

    def find_by_type(self, source_type: object) -> list[object]:
        return []

    def find_by_job_id(self, job_id: ResearchJobId) -> list[object]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class StubOutbox:
    def __init__(self) -> None:
        self.events: list[ResearchOutboxEvent] = []

    def append(self, event: ResearchOutboxEvent) -> None:
        self.events.append(event)

    def fetch_unpublished(self, limit: int = 100) -> list[ResearchOutboxEvent]:
        return list(self.events[:limit])

    def mark_published(self, aggregate_id: str) -> None:
        pass


# =========================================================================
# Fixtures
# =========================================================================

_NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def request_repo() -> StubRequestRepo:
    return StubRequestRepo()


@pytest.fixture
def job_repo() -> StubJobRepo:
    return StubJobRepo()


@pytest.fixture
def source_repo() -> StubSourceRepo:
    return StubSourceRepo()


@pytest.fixture
def outbox() -> StubOutbox:
    return StubOutbox()


# =========================================================================
# Helpers
# =========================================================================


def create_request_entity(
    request_id_str: str = "00000000-0000-0000-0000-000000000001"
) -> ResearchRequest:
    from backend.research.domain.factory import ResearchFactory

    req, _ = ResearchFactory.create_request(
        query="test query",
        goal="test goal",
        priority="normal",
    )
    object.__setattr__(req, "_request_id", ResearchRequestId(value=UUID(request_id_str)))
    return req


def create_job_entity(
    job_id_str: str = "00000000-0000-0000-0000-000000000002"
) -> ResearchJob:
    job = ResearchJob(
        job_id=ResearchJobId(value=UUID(job_id_str)),
        goal=ResearchGoal(value="sub goal"),
    )
    return job


from backend.research.domain.model import (  # noqa: E402
    ResearchGoal,
)


# =========================================================================
# CreateRequestUseCase
# =========================================================================


class TestCreateRequestUseCase:
    def test_create_request(self, request_repo: StubRequestRepo, outbox: StubOutbox) -> None:
        uc = CreateRequestUseCase(request_repo=request_repo, outbox=outbox)
        req = CreateRequestRequest(query="What is AI?", goal="Research AI", priority="high")
        resp = uc.execute(req)

        assert resp.query == "What is AI?"
        assert resp.goal == "Research AI"
        assert resp.priority == "high"
        assert resp.status == "created"
        assert resp.request_id is not None
        assert resp.created_at is not None
        assert request_repo.count() == 1

    def test_emits_research_requested(self, request_repo: StubRequestRepo, outbox: StubOutbox) -> None:
        uc = CreateRequestUseCase(request_repo=request_repo, outbox=outbox)
        req = CreateRequestRequest(query="q", goal="g", priority="normal")
        uc.execute(req)

        assert len(outbox.events) == 1
        assert isinstance(outbox.events[0], ResearchRequested)

    def test_persists_request(self, request_repo: StubRequestRepo, outbox: StubOutbox) -> None:
        uc = CreateRequestUseCase(request_repo=request_repo, outbox=outbox)
        req = CreateRequestRequest(query="q", goal="g", priority="normal")
        resp = uc.execute(req)

        found = request_repo.find_by_id(ResearchRequestId(value=UUID(resp.request_id)))
        assert found is not None
        assert found.query is not None
        assert found.query.value == "q"


# =========================================================================
# StartRequestUseCase
# =========================================================================


class TestStartRequestUseCase:
    def test_start_request(self, request_repo: StubRequestRepo, outbox: StubOutbox) -> None:
        req_entity = create_request_entity()
        request_repo.save(req_entity)

        uc = StartRequestUseCase(request_repo=request_repo, outbox=outbox)
        resp = uc.execute(RequestLifecycleRequest(request_id=str(req_entity.request_id)))

        assert resp.status == "running"

    def test_raises_if_not_found(self, request_repo: StubRequestRepo, outbox: StubOutbox) -> None:
        uc = StartRequestUseCase(request_repo=request_repo, outbox=outbox)
        with pytest.raises(ResearchRequestNotFoundError):
            uc.execute(RequestLifecycleRequest(request_id="00000000-0000-0000-0000-000000009999"))

    def test_emits_research_started(self, request_repo: StubRequestRepo, outbox: StubOutbox) -> None:
        req_entity = create_request_entity()
        request_repo.save(req_entity)

        uc = StartRequestUseCase(request_repo=request_repo, outbox=outbox)
        uc.execute(RequestLifecycleRequest(request_id=str(req_entity.request_id)))

        assert any(isinstance(e, ResearchStarted) for e in outbox.events)

    def test_error_is_use_case_error(self) -> None:
        assert issubclass(ResearchRequestNotFoundError, UseCaseError)


# =========================================================================
# CompleteRequestUseCase
# =========================================================================


class TestCompleteRequestUseCase:
    def test_complete_request_with_jobs(self, request_repo: StubRequestRepo, outbox: StubOutbox) -> None:
        req_entity = create_request_entity()
        req_entity.start()
        job = create_job_entity()
        job.start()
        job.complete(str_to_summary("Done"))
        req_entity.add_job(job)
        request_repo.save(req_entity)

        uc = CompleteRequestUseCase(request_repo=request_repo, outbox=outbox)
        resp = uc.execute(RequestLifecycleRequest(request_id=str(req_entity.request_id)))

        assert resp.status == "completed"

    def test_raises_if_not_found(self, request_repo: StubRequestRepo, outbox: StubOutbox) -> None:
        uc = CompleteRequestUseCase(request_repo=request_repo, outbox=outbox)
        with pytest.raises(ResearchRequestNotFoundError):
            uc.execute(RequestLifecycleRequest(request_id="00000000-0000-0000-0000-000000009999"))

    def test_emits_research_completed(self, request_repo: StubRequestRepo, outbox: StubOutbox) -> None:
        req_entity = create_request_entity()
        req_entity.start()
        job = create_job_entity()
        job.start()
        job.complete(str_to_summary("Done"))
        req_entity.add_job(job)
        request_repo.save(req_entity)

        uc = CompleteRequestUseCase(request_repo=request_repo, outbox=outbox)
        uc.execute(RequestLifecycleRequest(request_id=str(req_entity.request_id)))

        assert any(isinstance(e, ResearchCompleted) for e in outbox.events)


def str_to_summary(text: str) -> "ResearchSummary":
    from backend.research.domain.model import ResearchSummary
    return ResearchSummary(value=text)


# =========================================================================
# FailRequestUseCase
# =========================================================================


class TestFailRequestUseCase:
    def test_fail_request(self, request_repo: StubRequestRepo, outbox: StubOutbox) -> None:
        req_entity = create_request_entity()
        req_entity.start()
        request_repo.save(req_entity)

        uc = FailRequestUseCase(request_repo=request_repo, outbox=outbox)
        resp = uc.execute(FailRequestRequest(request_id=str(req_entity.request_id), failure_reason="Error"))

        assert resp.status == "failed"
        assert resp.failure_reason == "Error"

    def test_raises_if_not_found(self, request_repo: StubRequestRepo, outbox: StubOutbox) -> None:
        uc = FailRequestUseCase(request_repo=request_repo, outbox=outbox)
        with pytest.raises(ResearchRequestNotFoundError):
            uc.execute(FailRequestRequest(request_id="00000000-0000-0000-0000-000000009999", failure_reason="err"))

    def test_emits_research_failed(self, request_repo: StubRequestRepo, outbox: StubOutbox) -> None:
        req_entity = create_request_entity()
        req_entity.start()
        request_repo.save(req_entity)

        uc = FailRequestUseCase(request_repo=request_repo, outbox=outbox)
        uc.execute(FailRequestRequest(request_id=str(req_entity.request_id), failure_reason="err"))

        assert any(isinstance(e, ResearchFailed) for e in outbox.events)


# =========================================================================
# CancelRequestUseCase
# =========================================================================


class TestCancelRequestUseCase:
    def test_cancel_request(self, request_repo: StubRequestRepo, outbox: StubOutbox) -> None:
        req_entity = create_request_entity()
        request_repo.save(req_entity)

        uc = CancelRequestUseCase(request_repo=request_repo, outbox=outbox)
        resp = uc.execute(RequestLifecycleRequest(request_id=str(req_entity.request_id)))

        assert resp.status == "cancelled"

    def test_raises_if_not_found(self, request_repo: StubRequestRepo, outbox: StubOutbox) -> None:
        uc = CancelRequestUseCase(request_repo=request_repo, outbox=outbox)
        with pytest.raises(ResearchRequestNotFoundError):
            uc.execute(RequestLifecycleRequest(request_id="00000000-0000-0000-0000-000000009999"))

    def test_emits_research_cancelled(self, request_repo: StubRequestRepo, outbox: StubOutbox) -> None:
        req_entity = create_request_entity()
        request_repo.save(req_entity)

        uc = CancelRequestUseCase(request_repo=request_repo, outbox=outbox)
        uc.execute(RequestLifecycleRequest(request_id=str(req_entity.request_id)))

        assert any(isinstance(e, ResearchCancelled) for e in outbox.events)


# =========================================================================
# CreateJobUseCase
# =========================================================================


class TestCreateJobUseCase:
    def test_create_job(self, request_repo: StubRequestRepo, job_repo: StubJobRepo, outbox: StubOutbox) -> None:
        req_entity = create_request_entity()
        request_repo.save(req_entity)

        uc = CreateJobUseCase(
            request_repo=request_repo, job_repo=job_repo, outbox=outbox,
        )
        req = CreateJobRequest(request_id=str(req_entity.request_id), goal="sub goal", priority="high")
        resp = uc.execute(req)

        assert resp.job_id is not None
        assert resp.goal == "sub goal"
        assert resp.priority == "high"
        assert resp.status == "created"
        assert job_repo.count() == 1

    def test_raises_if_request_not_found(self, request_repo: StubRequestRepo, job_repo: StubJobRepo, outbox: StubOutbox) -> None:
        uc = CreateJobUseCase(request_repo=request_repo, job_repo=job_repo, outbox=outbox)
        with pytest.raises(ResearchRequestNotFoundError):
            uc.execute(CreateJobRequest(request_id="00000000-0000-0000-0000-000000009999", goal="g"))

    def test_job_added_to_request(self, request_repo: StubRequestRepo, job_repo: StubJobRepo, outbox: StubOutbox) -> None:
        req_entity = create_request_entity()
        request_repo.save(req_entity)

        uc = CreateJobUseCase(
            request_repo=request_repo, job_repo=job_repo, outbox=outbox,
        )
        uc.execute(CreateJobRequest(request_id=str(req_entity.request_id), goal="g"))

        found = request_repo.find_by_id(req_entity.request_id)
        assert found is not None
        assert len(found.jobs) == 1


# =========================================================================
# StartJobUseCase
# =========================================================================


class TestStartJobUseCase:
    def test_start_job(self, job_repo: StubJobRepo, outbox: StubOutbox) -> None:
        job_entity = create_job_entity()
        job_repo.save(job_entity)

        uc = StartJobUseCase(job_repo=job_repo, outbox=outbox)
        resp = uc.execute(JobLifecycleRequest(job_id=str(job_entity.job_id)))

        assert resp.status == "running"

    def test_raises_if_not_found(self, job_repo: StubJobRepo, outbox: StubOutbox) -> None:
        uc = StartJobUseCase(job_repo=job_repo, outbox=outbox)
        with pytest.raises(ResearchJobNotFoundError):
            uc.execute(JobLifecycleRequest(job_id="00000000-0000-0000-0000-000000009999"))


# =========================================================================
# CompleteJobUseCase
# =========================================================================


class TestCompleteJobUseCase:
    def test_complete_job(self, job_repo: StubJobRepo, outbox: StubOutbox) -> None:
        job_entity = create_job_entity()
        job_entity.start()
        job_repo.save(job_entity)

        uc = CompleteJobUseCase(job_repo=job_repo, outbox=outbox)
        resp = uc.execute(GenerateSummaryRequest(job_id=str(job_entity.job_id), summary="Great results"))

        assert resp.status == "completed"
        assert resp.summary == "Great results"

    def test_raises_if_not_found(self, job_repo: StubJobRepo, outbox: StubOutbox) -> None:
        uc = CompleteJobUseCase(job_repo=job_repo, outbox=outbox)
        with pytest.raises(ResearchJobNotFoundError):
            uc.execute(GenerateSummaryRequest(job_id="00000000-0000-0000-0000-000000009999", summary="s"))

    def test_emits_summary_generated(self, job_repo: StubJobRepo, outbox: StubOutbox) -> None:
        job_entity = create_job_entity()
        job_entity.start()
        job_repo.save(job_entity)

        uc = CompleteJobUseCase(job_repo=job_repo, outbox=outbox)
        uc.execute(GenerateSummaryRequest(job_id=str(job_entity.job_id), summary="s"))

        assert any(isinstance(e, ResearchSummaryGenerated) for e in outbox.events)


# =========================================================================
# FailJobUseCase
# =========================================================================


class TestFailJobUseCase:
    def test_fail_job(self, job_repo: StubJobRepo, outbox: StubOutbox) -> None:
        job_entity = create_job_entity()
        job_entity.start()
        job_repo.save(job_entity)

        uc = FailJobUseCase(job_repo=job_repo, outbox=outbox)
        resp = uc.execute(FailJobRequest(job_id=str(job_entity.job_id), failure_reason="Timeout"))

        assert resp.status == "failed"
        assert resp.failure_reason == "Timeout"

    def test_raises_if_not_found(self, job_repo: StubJobRepo, outbox: StubOutbox) -> None:
        uc = FailJobUseCase(job_repo=job_repo, outbox=outbox)
        with pytest.raises(ResearchJobNotFoundError):
            uc.execute(FailJobRequest(job_id="00000000-0000-0000-0000-000000009999", failure_reason="err"))


# =========================================================================
# AddSourceUseCase
# =========================================================================


class TestAddSourceUseCase:
    def test_add_source(self, job_repo: StubJobRepo, source_repo: StubSourceRepo, outbox: StubOutbox) -> None:
        job_entity = create_job_entity()
        job_repo.save(job_entity)

        uc = AddSourceUseCase(job_repo=job_repo, source_repo=source_repo, outbox=outbox)
        req = AddSourceRequest(
            job_id=str(job_entity.job_id),
            reference="https://example.com",
            source_type="web",
            confidence_score=0.85,
        )
        resp = uc.execute(req)

        assert resp.source_id is not None
        assert resp.reference == "https://example.com"
        assert resp.source_type == "web"
        assert resp.confidence_score == 0.85

    def test_raises_if_job_not_found(self, job_repo: StubJobRepo, source_repo: StubSourceRepo, outbox: StubOutbox) -> None:
        uc = AddSourceUseCase(job_repo=job_repo, source_repo=source_repo, outbox=outbox)
        with pytest.raises(ResearchJobNotFoundError):
            uc.execute(AddSourceRequest(job_id="00000000-0000-0000-0000-000000009999", reference="ref", source_type="web", confidence_score=0.5))

    def test_emits_source_added(self, job_repo: StubJobRepo, source_repo: StubSourceRepo, outbox: StubOutbox) -> None:
        job_entity = create_job_entity()
        job_repo.save(job_entity)

        uc = AddSourceUseCase(job_repo=job_repo, source_repo=source_repo, outbox=outbox)
        uc.execute(AddSourceRequest(
            job_id=str(job_entity.job_id), reference="https://ref.com",
            source_type="knowledge", confidence_score=0.9,
        ))

        assert any(isinstance(e, SourceAdded) for e in outbox.events)

    def test_source_added_to_job(self, job_repo: StubJobRepo, source_repo: StubSourceRepo, outbox: StubOutbox) -> None:
        job_entity = create_job_entity()
        job_repo.save(job_entity)

        uc = AddSourceUseCase(job_repo=job_repo, source_repo=source_repo, outbox=outbox)
        uc.execute(AddSourceRequest(
            job_id=str(job_entity.job_id), reference="https://ref.com",
            source_type="web", confidence_score=0.5,
        ))

        job = job_repo.find_by_id(job_entity.job_id)
        assert job is not None
        assert len(job.sources) == 1


# =========================================================================
# GenerateSummaryUseCase
# =========================================================================


class TestGenerateSummaryUseCase:
    def test_generate_summary(self, job_repo: StubJobRepo, outbox: StubOutbox) -> None:
        job_entity = create_job_entity()
        job_entity.start()
        job_repo.save(job_entity)

        uc = GenerateSummaryUseCase(job_repo=job_repo, outbox=outbox)
        resp = uc.execute(GenerateSummaryRequest(job_id=str(job_entity.job_id), summary="Final summary"))

        assert resp.status == "completed"
        assert resp.summary == "Final summary"

    def test_raises_if_not_found(self, job_repo: StubJobRepo, outbox: StubOutbox) -> None:
        uc = GenerateSummaryUseCase(job_repo=job_repo, outbox=outbox)
        with pytest.raises(ResearchJobNotFoundError):
            uc.execute(GenerateSummaryRequest(job_id="00000000-0000-0000-0000-000000009999", summary="s"))

    def test_emits_summary_generated(self, job_repo: StubJobRepo, outbox: StubOutbox) -> None:
        job_entity = create_job_entity()
        job_entity.start()
        job_repo.save(job_entity)

        uc = GenerateSummaryUseCase(job_repo=job_repo, outbox=outbox)
        uc.execute(GenerateSummaryRequest(job_id=str(job_entity.job_id), summary="s"))

        assert any(isinstance(e, ResearchSummaryGenerated) for e in outbox.events)

    def test_error_is_use_case_error(self) -> None:
        assert issubclass(ResearchJobNotFoundError, UseCaseError)


# =========================================================================
# GetRequestUseCase
# =========================================================================


class TestGetRequestUseCase:
    def test_get_request(self, request_repo: StubRequestRepo) -> None:
        req_entity = create_request_entity()
        request_repo.save(req_entity)

        uc = GetRequestUseCase(request_repo=request_repo)
        resp = uc.execute(GetRequestRequest(request_id=str(req_entity.request_id)))

        assert resp.request_id == str(req_entity.request_id)
        assert resp.query == "test query"
        assert resp.goal == "test goal"
        assert resp.status == "created"

    def test_raises_if_not_found(self, request_repo: StubRequestRepo) -> None:
        uc = GetRequestUseCase(request_repo=request_repo)
        with pytest.raises(ResearchRequestNotFoundError):
            uc.execute(GetRequestRequest(request_id="00000000-0000-0000-0000-000000009999"))

    def test_returns_job_count(self, request_repo: StubRequestRepo) -> None:
        req_entity = create_request_entity()
        job = create_job_entity()
        req_entity.add_job(job)
        request_repo.save(req_entity)

        uc = GetRequestUseCase(request_repo=request_repo)
        resp = uc.execute(GetRequestRequest(request_id=str(req_entity.request_id)))

        assert resp.job_count == 1


# =========================================================================
# ListRequestsUseCase
# =========================================================================


class TestListRequestsUseCase:
    def test_list_by_status(self, request_repo: StubRequestRepo) -> None:
        req1 = create_request_entity("00000000-0000-0000-0000-000000000001")
        req2 = create_request_entity("00000000-0000-0000-0000-000000000002")
        req2.start()
        request_repo.save(req1)
        request_repo.save(req2)

        uc = ListRequestsUseCase(request_repo=request_repo)
        resp = uc.execute(ListRequestsRequest(status="created"))

        assert resp.total == 1
        assert resp.requests[0].request_id == str(req1.request_id)

    def test_list_by_priority(self, request_repo: StubRequestRepo) -> None:
        req1 = create_request_entity("00000000-0000-0000-0000-000000000001")
        req2 = create_request_entity("00000000-0000-0000-0000-000000000002")
        object.__setattr__(req2, "_priority", ResearchPriority.HIGH)
        request_repo.save(req1)
        request_repo.save(req2)

        uc = ListRequestsUseCase(request_repo=request_repo)
        resp = uc.execute(ListRequestsRequest(priority="high"))

        assert resp.total == 1

    def test_empty_when_no_filter(self, request_repo: StubRequestRepo) -> None:
        req_entity = create_request_entity()
        request_repo.save(req_entity)

        uc = ListRequestsUseCase(request_repo=request_repo)
        resp = uc.execute(ListRequestsRequest())

        assert resp.total == 0


# =========================================================================
# GetJobUseCase
# =========================================================================


class TestGetJobUseCase:
    def test_get_job(self, job_repo: StubJobRepo) -> None:
        job_entity = create_job_entity()
        job_repo.save(job_entity)

        uc = GetJobUseCase(job_repo=job_repo)
        resp = uc.execute(GetJobRequest(job_id=str(job_entity.job_id)))

        assert resp.job_id == str(job_entity.job_id)
        assert resp.goal == "sub goal"
        assert resp.status == "created"

    def test_raises_if_not_found(self, job_repo: StubJobRepo) -> None:
        uc = GetJobUseCase(job_repo=job_repo)
        with pytest.raises(ResearchJobNotFoundError):
            uc.execute(GetJobRequest(job_id="00000000-0000-0000-0000-000000009999"))

    def test_returns_source_count(self, job_repo: StubJobRepo) -> None:
        job_entity = create_job_entity()
        from backend.research.domain.model import ConfidenceScore, SourceReference

        source = ResearchSource(
            source_type=SourceType.WEB,
            reference=SourceReference(value="https://ref.com"),
            confidence_score=ConfidenceScore(value=0.5),
        )
        job_entity.add_source(source)
        job_repo.save(job_entity)

        uc = GetJobUseCase(job_repo=job_repo)
        resp = uc.execute(GetJobRequest(job_id=str(job_entity.job_id)))

        assert resp.source_count == 1


from backend.research.domain.model import (  # noqa: E402
    ResearchSource,
    SourceType,
    SourceReference,
    ConfidenceScore,
)


# =========================================================================
# ListJobsUseCase
# =========================================================================


class TestListJobsUseCase:
    def test_list_by_status(self, job_repo: StubJobRepo) -> None:
        job1 = create_job_entity("00000000-0000-0000-0000-000000000001")
        job2 = create_job_entity("00000000-0000-0000-0000-000000000002")
        job2.start()
        job_repo.save(job1)
        job_repo.save(job2)

        uc = ListJobsUseCase(job_repo=job_repo)
        resp = uc.execute(ListJobsRequest(status="created"))

        assert resp.total == 1
        assert resp.jobs[0].job_id == str(job1.job_id)

    def test_list_by_request_id(self, job_repo: StubJobRepo) -> None:
        job1 = create_job_entity("00000000-0000-0000-0000-000000000001")
        job_repo.save(job1)

        uc = ListJobsUseCase(job_repo=job_repo)
        resp = uc.execute(ListJobsRequest(request_id="00000000-0000-0000-0000-000000000099"))

        assert resp.total == 1

    def test_empty_when_no_filter(self, job_repo: StubJobRepo) -> None:
        job = create_job_entity()
        job_repo.save(job)

        uc = ListJobsUseCase(job_repo=job_repo)
        resp = uc.execute(ListJobsRequest())

        assert resp.total == 0


# =========================================================================
# Integration flows
# =========================================================================


class TestIntegrationFlows:
    def test_full_request_lifecycle(self, request_repo: StubRequestRepo, job_repo: StubJobRepo, source_repo: StubSourceRepo, outbox: StubOutbox) -> None:
        create_uc = CreateRequestUseCase(request_repo=request_repo, outbox=outbox)
        create_resp = create_uc.execute(CreateRequestRequest(query="Research AI", goal="Explore AI", priority="high"))

        start_uc = StartRequestUseCase(request_repo=request_repo, outbox=outbox)
        start_uc.execute(RequestLifecycleRequest(request_id=create_resp.request_id))

        create_job_uc = CreateJobUseCase(request_repo=request_repo, job_repo=job_repo, outbox=outbox)
        job_resp = create_job_uc.execute(CreateJobRequest(request_id=create_resp.request_id, goal="Sub task"))

        start_job_uc = StartJobUseCase(job_repo=job_repo, outbox=outbox)
        start_job_uc.execute(JobLifecycleRequest(job_id=job_resp.job_id))

        complete_job_uc = CompleteJobUseCase(job_repo=job_repo, outbox=outbox)
        complete_job_uc.execute(GenerateSummaryRequest(job_id=job_resp.job_id, summary="Results"))

        complete_uc = CompleteRequestUseCase(request_repo=request_repo, outbox=outbox)
        complete_resp = complete_uc.execute(RequestLifecycleRequest(request_id=create_resp.request_id))

        assert complete_resp.status == "completed"
        assert len(outbox.events) >= 4

    def test_full_failure_lifecycle(self, request_repo: StubRequestRepo, job_repo: StubJobRepo, outbox: StubOutbox) -> None:
        create_uc = CreateRequestUseCase(request_repo=request_repo, outbox=outbox)
        create_resp = create_uc.execute(CreateRequestRequest(query="q", goal="g", priority="normal"))

        start_uc = StartRequestUseCase(request_repo=request_repo, outbox=outbox)
        start_uc.execute(RequestLifecycleRequest(request_id=create_resp.request_id))

        fail_uc = FailRequestUseCase(request_repo=request_repo, outbox=outbox)
        fail_resp = fail_uc.execute(FailRequestRequest(request_id=create_resp.request_id, failure_reason="Error"))

        assert fail_resp.status == "failed"

    def test_add_source_flow(self, request_repo: StubRequestRepo, job_repo: StubJobRepo, source_repo: StubSourceRepo, outbox: StubOutbox) -> None:
        create_uc = CreateRequestUseCase(request_repo=request_repo, outbox=outbox)
        create_resp = create_uc.execute(CreateRequestRequest(query="q", goal="g", priority="normal"))

        create_job_uc = CreateJobUseCase(request_repo=request_repo, job_repo=job_repo, outbox=outbox)
        job_resp = create_job_uc.execute(CreateJobRequest(request_id=create_resp.request_id, goal="g"))

        add_source_uc = AddSourceUseCase(job_repo=job_repo, source_repo=source_repo, outbox=outbox)
        source_resp = add_source_uc.execute(AddSourceRequest(
            job_id=job_resp.job_id, reference="https://ref.com",
            source_type="web", confidence_score=0.9,
        ))

        assert source_resp.source_id is not None
        assert len(outbox.events) == 2  # requested + source added


# =========================================================================
# Exception hierarchy
# =========================================================================


class TestExceptionHierarchy:
    def test_request_not_found_is_use_case_error(self) -> None:
        assert issubclass(ResearchRequestNotFoundError, UseCaseError)

    def test_job_not_found_is_use_case_error(self) -> None:
        assert issubclass(ResearchJobNotFoundError, UseCaseError)

    def test_use_case_error_is_exception(self) -> None:
        assert issubclass(UseCaseError, Exception)

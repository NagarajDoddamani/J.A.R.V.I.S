from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.research.domain.exceptions import (
    CancelledJobRestartError,
    DuplicateSourceReferenceError,
    IncompleteJobsError,
    InvalidConfidenceScoreError,
    InvalidFailureReasonError,
    InvalidGoalError,
    InvalidPriorityError,
    InvalidQueryError,
    InvalidSourceReferenceError,
    InvalidSourceTypeError,
    InvalidSummaryError,
    InvalidTransitionError,
    MissingConfidenceScoreError,
    NoJobsError,
    QueryTooLongError,
    ResearchDomainError,
    ResearchImmutableError,
    SummaryTooLongError,
)
from backend.research.domain.factory import ResearchFactory
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
from backend.research.domain.rules import (
    MAX_QUERY_LENGTH,
    MAX_SUMMARY_LENGTH,
    VALID_JOB_TRANSITIONS,
    VALID_REQUEST_TRANSITIONS,
    assert_all_jobs_completed,
    assert_confidence_score_provided,
    assert_failure_reason_required,
    assert_goal_required,
    assert_job_can_transition,
    assert_job_not_cancelled,
    assert_job_not_terminal,
    assert_no_duplicate_source_references,
    assert_priority_valid,
    assert_query_length,
    assert_query_required,
    assert_request_can_transition,
    assert_request_has_jobs,
    assert_request_not_terminal,
    assert_source_reference_required,
    assert_source_type_valid,
    assert_summary_length,
    assert_summary_required,
    validate_job_creation,
    validate_request_creation,
    validate_source_creation,
)

# ===========================================================================
# Helpers
# ===========================================================================


def make_valid_request(
    query: str = "Test research query",
    goal: str = "Test research goal",
    priority: ResearchPriority = ResearchPriority.NORMAL,
) -> ResearchRequest:
    r, _ = ResearchFactory.create_request(
        query=query,
        goal=goal,
        priority=priority,
    )
    return r


def make_valid_job(
    request: ResearchRequest | None = None,
    goal: str = "Sub goal",
    priority: ResearchPriority | None = None,
) -> ResearchJob:
    if request is None:
        request = make_valid_request()
    return ResearchFactory.create_job(
        request=request,
        goal=goal,
        priority=priority,
    )


def make_valid_source(
    reference: str = "https://example.com",
    source_type: SourceType = SourceType.WEB,
    confidence_score: float = 0.85,
) -> ResearchSource:
    return ResearchSource(
        source_id=None,
        source_type=source_type,
        reference=SourceReference(value=reference),
        confidence_score=ConfidenceScore(value=confidence_score),
    )


def make_started_job(request: ResearchRequest | None = None) -> ResearchJob:
    job = make_valid_job(request=request)
    job.start()
    return job


# ===========================================================================
# Value Objects
# ===========================================================================


class TestResearchRequestId:
    def test_creation(self) -> None:
        rid = ResearchRequestId()
        assert isinstance(rid.value, UUID)

    def test_uniqueness(self) -> None:
        assert ResearchRequestId().value != ResearchRequestId().value

    def test_str(self) -> None:
        rid = ResearchRequestId()
        assert str(rid) == str(rid.value)


class TestResearchJobId:
    def test_creation(self) -> None:
        jid = ResearchJobId()
        assert isinstance(jid.value, UUID)

    def test_uniqueness(self) -> None:
        assert ResearchJobId().value != ResearchJobId().value

    def test_str(self) -> None:
        jid = ResearchJobId()
        assert str(jid) == str(jid.value)


class TestQueryText:
    def test_valid(self) -> None:
        q = QueryText(value="What is AI?")
        assert q.value == "What is AI?"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidQueryError):
            QueryText(value="")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(InvalidQueryError):
            QueryText(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            QueryText(value=123)  # type: ignore[arg-type]

    def test_str(self) -> None:
        q = QueryText(value="hello")
        assert str(q) == "hello"

    def test_len(self) -> None:
        q = QueryText(value="hello")
        assert len(q) == 5


class TestResearchGoal:
    def test_valid(self) -> None:
        g = ResearchGoal(value="Goal")
        assert g.value == "Goal"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidGoalError):
            ResearchGoal(value="")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(InvalidGoalError):
            ResearchGoal(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            ResearchGoal(value=123)  # type: ignore[arg-type]


class TestSourceReference:
    def test_valid(self) -> None:
        s = SourceReference(value="https://ref.com")
        assert s.value == "https://ref.com"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidSourceReferenceError):
            SourceReference(value="")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(InvalidSourceReferenceError):
            SourceReference(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            SourceReference(value=123)  # type: ignore[arg-type]


class TestConfidenceScore:
    @pytest.mark.parametrize("score", [0.0, 0.5, 1.0, 0.333, 0.99])
    def test_valid(self, score: float) -> None:
        cs = ConfidenceScore(value=score)
        assert cs.value == score

    @pytest.mark.parametrize("score", [-0.1, 1.1, 2.0, -1.0])
    def test_out_of_range_raises(self, score: float) -> None:
        with pytest.raises(InvalidConfidenceScoreError):
            ConfidenceScore(value=score)

    def test_non_number_raises(self) -> None:
        with pytest.raises(TypeError):
            ConfidenceScore(value="high")  # type: ignore[arg-type]

    def test_float_conversion(self) -> None:
        cs = ConfidenceScore(value=0.75)
        assert float(cs) == 0.75


class TestResearchSummary:
    def test_valid(self) -> None:
        s = ResearchSummary(value="Summary text")
        assert s.value == "Summary text"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidSummaryError):
            ResearchSummary(value="")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(InvalidSummaryError):
            ResearchSummary(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            ResearchSummary(value=123)  # type: ignore[arg-type]


class TestFailureReasonValueObject:
    def test_valid(self) -> None:
        f = FailureReason(value="Something went wrong")
        assert f.value == "Something went wrong"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidFailureReasonError):
            FailureReason(value="")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(InvalidFailureReasonError):
            FailureReason(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            FailureReason(value=123)  # type: ignore[arg-type]


# ===========================================================================
# Enums
# ===========================================================================


class TestResearchStatus:
    def test_members(self) -> None:
        assert ResearchStatus.CREATED.value == "created"
        assert ResearchStatus.RUNNING.value == "running"
        assert ResearchStatus.COMPLETED.value == "completed"
        assert ResearchStatus.FAILED.value == "failed"
        assert ResearchStatus.CANCELLED.value == "cancelled"

    def test_count(self) -> None:
        assert len(ResearchStatus) == 5

    @pytest.mark.parametrize("s", ["created", "running", "completed", "failed", "cancelled"])
    def test_from_string(self, s: str) -> None:
        assert ResearchStatus(s) is not None


class TestSourceType:
    def test_members(self) -> None:
        assert SourceType.MEMORY.value == "memory"
        assert SourceType.KNOWLEDGE.value == "knowledge"
        assert SourceType.WEB.value == "web"
        assert SourceType.DOCUMENT.value == "document"
        assert SourceType.USER.value == "user"

    def test_count(self) -> None:
        assert len(SourceType) == 5

    @pytest.mark.parametrize("s", ["memory", "knowledge", "web", "document", "user"])
    def test_from_string(self, s: str) -> None:
        assert SourceType(s) is not None


class TestResearchPriority:
    def test_members(self) -> None:
        assert ResearchPriority.LOW.value == "low"
        assert ResearchPriority.NORMAL.value == "normal"
        assert ResearchPriority.HIGH.value == "high"
        assert ResearchPriority.CRITICAL.value == "critical"

    def test_count(self) -> None:
        assert len(ResearchPriority) == 4

    @pytest.mark.parametrize("s", ["low", "normal", "high", "critical"])
    def test_from_string(self, s: str) -> None:
        assert ResearchPriority(s) is not None


# ===========================================================================
# Domain Events
# ===========================================================================


class TestResearchRequested:
    def test_creation(self) -> None:
        now = datetime.now(tz=timezone.utc)
        rid = ResearchRequestId()
        event = ResearchRequested(
            request_id=rid,
            query="test",
            goal="goal",
            priority="normal",
            occurred_at=now,
        )
        assert event.request_id == rid
        assert event.query == "test"
        assert event.goal == "goal"
        assert event.priority == "normal"
        assert event.occurred_at == now
        assert isinstance(event.event_id, UUID)

    def test_unique_event_id(self) -> None:
        now = datetime.now(tz=timezone.utc)
        rid = ResearchRequestId()
        e1 = ResearchRequested(request_id=rid, query="q", goal="g", priority="normal", occurred_at=now)
        e2 = ResearchRequested(request_id=rid, query="q", goal="g", priority="normal", occurred_at=now)
        assert e1.event_id != e2.event_id


class TestResearchStarted:
    def test_creation(self) -> None:
        now = datetime.now(tz=timezone.utc)
        rid = ResearchRequestId()
        event = ResearchStarted(request_id=rid, occurred_at=now)
        assert event.request_id == rid
        assert event.occurred_at == now


class TestResearchCompleted:
    def test_creation(self) -> None:
        now = datetime.now(tz=timezone.utc)
        rid = ResearchRequestId()
        event = ResearchCompleted(request_id=rid, occurred_at=now)
        assert event.request_id == rid


class TestResearchFailed:
    def test_creation(self) -> None:
        now = datetime.now(tz=timezone.utc)
        rid = ResearchRequestId()
        event = ResearchFailed(request_id=rid, failure_reason="error", occurred_at=now)
        assert event.failure_reason == "error"


class TestResearchCancelled:
    def test_creation(self) -> None:
        now = datetime.now(tz=timezone.utc)
        rid = ResearchRequestId()
        event = ResearchCancelled(request_id=rid, occurred_at=now)
        assert event.request_id == rid


class TestSourceAdded:
    def test_creation(self) -> None:
        now = datetime.now(tz=timezone.utc)
        event = SourceAdded(
            request_id=ResearchRequestId(),
            job_id=ResearchJobId(),
            source_id=UUID(int=1),
            source_type="web",
            reference="https://ref.com",
            occurred_at=now,
        )
        assert event.source_type == "web"
        assert event.reference == "https://ref.com"


class TestResearchSummaryGenerated:
    def test_creation(self) -> None:
        now = datetime.now(tz=timezone.utc)
        event = ResearchSummaryGenerated(
            request_id=ResearchRequestId(),
            job_id=ResearchJobId(),
            summary="The summary",
            occurred_at=now,
        )
        assert event.summary == "The summary"


# ===========================================================================
# ResearchSource
# ===========================================================================


class TestResearchSourceEntity:
    def test_default_creation(self) -> None:
        source = ResearchSource()
        assert isinstance(source.source_id, UUID)
        assert source.source_type == SourceType.WEB
        assert source.reference is None
        assert source.confidence_score is None

    def test_creation_with_all_fields(self) -> None:
        sid = UUID(int=42)
        ref = SourceReference(value="https://example.com")
        score = ConfidenceScore(value=0.9)
        source = ResearchSource(
            source_id=sid,
            source_type=SourceType.KNOWLEDGE,
            reference=ref,
            confidence_score=score,
        )
        assert source.source_id == sid
        assert source.source_type == SourceType.KNOWLEDGE
        assert source.reference == ref
        assert source.confidence_score == score

    def test_repr(self) -> None:
        source = ResearchSource(source_type=SourceType.MEMORY)
        r = repr(source)
        assert "ResearchSource" in r
        assert "memory" in r


# ===========================================================================
# ResearchJob
# ===========================================================================


class TestResearchJobCreation:
    def test_default_creation(self) -> None:
        job = ResearchJob()
        assert isinstance(job.job_id, ResearchJobId)
        assert job.status == ResearchStatus.CREATED
        assert job.priority == ResearchPriority.NORMAL
        assert job.sources == []
        assert job.summary is None
        assert job.failure_reason is None
        assert job.completed_at is None
        assert not job.events
        assert not job.is_terminal

    def test_creation_with_all_fields(self) -> None:
        jid = ResearchJobId()
        goal = ResearchGoal(value="Test goal")
        source = make_valid_source()
        summary = ResearchSummary(value="Done")
        reason = FailureReason(value="Failed")
        now = datetime.now(tz=timezone.utc)
        job = ResearchJob(
            job_id=jid,
            goal=goal,
            status=ResearchStatus.RUNNING,
            priority=ResearchPriority.HIGH,
            sources=[source],
            summary=summary,
            failure_reason=reason,
            created_at=now,
            completed_at=now,
        )
        assert job.job_id == jid
        assert job.goal == goal
        assert job.status == ResearchStatus.RUNNING
        assert job.priority == ResearchPriority.HIGH
        assert len(job.sources) == 1
        assert job.summary == summary
        assert job.failure_reason == reason
        assert job.created_at == now
        assert job.completed_at == now

    def test_goal_is_optional(self) -> None:
        job = ResearchJob()
        assert job.goal is None

    def test_repr(self) -> None:
        job = ResearchJob()
        r = repr(job)
        assert "ResearchJob" in r
        assert "created" in r


class TestResearchJobStart:
    def test_start_transitions_to_running(self) -> None:
        job = ResearchJob()
        job.start()
        assert job.status == ResearchStatus.RUNNING

    def test_start_from_running_raises(self) -> None:
        job = ResearchJob()
        job.start()
        with pytest.raises(InvalidTransitionError):
            job.start()

    def test_start_from_completed_raises(self) -> None:
        job = ResearchJob()
        job.start()
        job.complete(ResearchSummary(value="Done"))
        with pytest.raises(InvalidTransitionError):
            job.start()

    def test_start_from_failed_raises(self) -> None:
        job = ResearchJob()
        job.start()
        job.fail(FailureReason(value="Error"))
        with pytest.raises(InvalidTransitionError):
            job.start()

    def test_start_from_cancelled_raises(self) -> None:
        job = ResearchJob()
        job.cancel()
        with pytest.raises(CancelledJobRestartError):
            job.start()


class TestResearchJobComplete:
    def test_complete_stores_summary(self) -> None:
        job = make_started_job()
        summary = ResearchSummary(value="Great findings")
        job.complete(summary)
        assert job.status == ResearchStatus.COMPLETED
        assert job.summary == summary
        assert job.completed_at is not None

    def test_complete_requires_summary(self) -> None:
        job = make_started_job()
        with pytest.raises(InvalidSummaryError):
            job.complete(None)  # type: ignore[arg-type]

    def test_complete_from_created_raises(self) -> None:
        job = ResearchJob()
        summary = ResearchSummary(value="Done")
        with pytest.raises(InvalidTransitionError):
            job.complete(summary)

    def test_complete_from_completed_raises(self) -> None:
        job = make_started_job()
        job.complete(ResearchSummary(value="Done"))
        with pytest.raises(InvalidTransitionError):
            job.complete(ResearchSummary(value="Again"))

    def test_complete_from_failed_raises(self) -> None:
        job = make_started_job()
        job.fail(FailureReason(value="Error"))
        with pytest.raises(InvalidTransitionError):
            job.complete(ResearchSummary(value="Done"))

    def test_complete_from_cancelled_raises(self) -> None:
        job = ResearchJob()
        job.cancel()
        with pytest.raises(CancelledJobRestartError):
            job.complete(ResearchSummary(value="Done"))

    def test_complete_emits_summary_generated_event(self) -> None:
        job = make_started_job()
        job.complete(ResearchSummary(value="Summary"))
        events = job.events
        assert any(isinstance(e, ResearchSummaryGenerated) for e in events)

    def test_complete_generated_event_has_summary(self) -> None:
        job = make_started_job()
        job.complete(ResearchSummary(value="The result"))
        gen_events = [e for e in job.events if isinstance(e, ResearchSummaryGenerated)]
        assert len(gen_events) == 1
        assert gen_events[0].summary == "The result"


class TestResearchJobFail:
    def test_fail_stores_reason(self) -> None:
        job = make_started_job()
        reason = FailureReason(value="Timeout")
        job.fail(reason)
        assert job.status == ResearchStatus.FAILED
        assert job.failure_reason == reason
        assert job.completed_at is not None

    def test_fail_requires_reason(self) -> None:
        job = make_started_job()
        with pytest.raises(InvalidFailureReasonError):
            job.fail(None)  # type: ignore[arg-type]

    def test_fail_from_created_raises(self) -> None:
        job = ResearchJob()
        with pytest.raises(InvalidTransitionError):
            job.fail(FailureReason(value="Error"))

    def test_fail_from_completed_raises(self) -> None:
        job = make_started_job()
        job.complete(ResearchSummary(value="Done"))
        with pytest.raises(InvalidTransitionError):
            job.fail(FailureReason(value="Error"))

    def test_fail_from_failed_raises(self) -> None:
        job = make_started_job()
        job.fail(FailureReason(value="Error"))
        with pytest.raises(InvalidTransitionError):
            job.fail(FailureReason(value="Again"))

    def test_fail_from_cancelled_raises(self) -> None:
        job = ResearchJob()
        job.cancel()
        with pytest.raises(CancelledJobRestartError):
            job.fail(FailureReason(value="Error"))


class TestResearchJobCancel:
    def test_cancel_from_created(self) -> None:
        job = ResearchJob()
        job.cancel()
        assert job.status == ResearchStatus.CANCELLED

    def test_cancel_from_running(self) -> None:
        job = make_started_job()
        job.cancel()
        assert job.status == ResearchStatus.CANCELLED

    def test_cancel_from_completed_raises(self) -> None:
        job = make_started_job()
        job.complete(ResearchSummary(value="Done"))
        with pytest.raises(InvalidTransitionError):
            job.cancel()

    def test_cancel_from_failed_raises(self) -> None:
        job = make_started_job()
        job.fail(FailureReason(value="Error"))
        with pytest.raises(InvalidTransitionError):
            job.cancel()

    def test_cancel_from_cancelled_raises(self) -> None:
        job = ResearchJob()
        job.cancel()
        with pytest.raises(InvalidTransitionError):
            job.cancel()


class TestResearchJobAddSource:
    def test_add_source_to_created_job(self) -> None:
        job = ResearchJob()
        source = make_valid_source()
        job.add_source(source)
        assert len(job.sources) == 1
        assert job.sources[0] == source

    def test_add_source_to_running_job(self) -> None:
        job = make_started_job()
        source = make_valid_source()
        job.add_source(source)
        assert len(job.sources) == 1

    def test_add_source_to_completed_job_raises(self) -> None:
        job = make_started_job()
        job.complete(ResearchSummary(value="Done"))
        with pytest.raises(ResearchImmutableError):
            job.add_source(make_valid_source())

    def test_add_source_to_failed_job_raises(self) -> None:
        job = make_started_job()
        job.fail(FailureReason(value="Error"))
        with pytest.raises(ResearchImmutableError):
            job.add_source(make_valid_source())

    def test_add_source_to_cancelled_job_raises(self) -> None:
        job = ResearchJob()
        job.cancel()
        with pytest.raises(ResearchImmutableError):
            job.add_source(make_valid_source())

    def test_add_source_without_confidence_raises(self) -> None:
        job = ResearchJob()
        source = ResearchSource(
            source_type=SourceType.WEB,
            reference=SourceReference(value="https://example.com"),
            confidence_score=None,
        )
        with pytest.raises(MissingConfidenceScoreError):
            job.add_source(source)

    def test_add_duplicate_source_reference_raises(self) -> None:
        job = ResearchJob()
        ref = "https://same.com"
        s1 = ResearchSource(
            source_type=SourceType.WEB,
            reference=SourceReference(value=ref),
            confidence_score=ConfidenceScore(value=0.8),
        )
        s2 = ResearchSource(
            source_type=SourceType.DOCUMENT,
            reference=SourceReference(value=ref),
            confidence_score=ConfidenceScore(value=0.9),
        )
        job.add_source(s1)
        with pytest.raises(DuplicateSourceReferenceError):
            job.add_source(s2)

    def test_add_source_emits_event(self) -> None:
        job = ResearchJob()
        source = make_valid_source()
        job.add_source(source)
        events = job.events
        assert any(isinstance(e, SourceAdded) for e in events)


class TestResearchJobTerminal:
    def test_created_not_terminal(self) -> None:
        assert not ResearchJob().is_terminal

    def test_running_not_terminal(self) -> None:
        job = make_started_job()
        assert not job.is_terminal

    def test_completed_is_terminal(self) -> None:
        job = make_started_job()
        job.complete(ResearchSummary(value="Done"))
        assert job.is_terminal

    def test_failed_is_terminal(self) -> None:
        job = make_started_job()
        job.fail(FailureReason(value="Error"))
        assert job.is_terminal

    def test_cancelled_is_terminal(self) -> None:
        job = ResearchJob()
        job.cancel()
        assert job.is_terminal


# ===========================================================================
# ResearchRequest
# ===========================================================================


class TestResearchRequestCreation:
    def test_default_creation(self) -> None:
        request = ResearchRequest()
        assert isinstance(request.request_id, ResearchRequestId)
        assert request.query is None
        assert request.goal is None
        assert request.priority == ResearchPriority.NORMAL
        assert request.status == ResearchStatus.CREATED
        assert request.jobs == []
        assert request.failure_reason is None
        assert request.created_at is not None
        assert request.updated_at is None
        assert not request.events
        assert not request.is_terminal

    def test_creation_with_all_fields(self) -> None:
        rid = ResearchRequestId()
        query = QueryText(value="Query")
        goal = ResearchGoal(value="Goal")
        job = ResearchJob()
        now = datetime.now(tz=timezone.utc)
        request = ResearchRequest(
            request_id=rid,
            query=query,
            goal=goal,
            priority=ResearchPriority.CRITICAL,
            jobs=[job],
            created_at=now,
            updated_at=now,
        )
        assert request.request_id == rid
        assert request.query == query
        assert request.goal == goal
        assert request.priority == ResearchPriority.CRITICAL
        assert len(request.jobs) == 1
        assert request.created_at == now
        assert request.updated_at == now

    def test_repr(self) -> None:
        request = ResearchRequest()
        r = repr(request)
        assert "ResearchRequest" in r
        assert "created" in r
        assert "normal" in r


class TestResearchRequestAddJob:
    def test_add_job(self) -> None:
        request = make_valid_request()
        job = make_valid_job(request=request)
        assert len(request.jobs) == 1

    def test_add_job_to_completed_raises(self) -> None:
        request = make_valid_request()
        job1 = make_valid_job(request=request)
        job1.start()
        job1.complete(ResearchSummary(value="Done"))
        job2 = make_valid_job(request=request)
        job2.start()
        job2.complete(ResearchSummary(value="Done"))
        request.start()
        request.complete()
        with pytest.raises(ResearchImmutableError):
            request.add_job(ResearchJob())

    def test_add_job_to_failed_raises(self) -> None:
        request = make_valid_request()
        request.start()
        request.fail(FailureReason(value="Error"))
        with pytest.raises(ResearchImmutableError):
            request.add_job(ResearchJob())

    def test_add_job_to_cancelled_raises(self) -> None:
        request = make_valid_request()
        request.cancel()
        with pytest.raises(ResearchImmutableError):
            request.add_job(ResearchJob())


class TestResearchRequestStart:
    def test_start_transitions_to_running(self) -> None:
        request = make_valid_request()
        request.start()
        assert request.status == ResearchStatus.RUNNING
        assert request.updated_at is not None

    def test_start_emits_event(self) -> None:
        request = make_valid_request()
        request.start()
        events = request.events
        assert any(isinstance(e, ResearchStarted) for e in events)

    def test_start_from_running_raises(self) -> None:
        request = make_valid_request()
        request.start()
        with pytest.raises(InvalidTransitionError):
            request.start()

    def test_start_from_completed_raises(self) -> None:
        request = make_valid_request()
        job = make_valid_job(request=request)
        job.start()
        job.complete(ResearchSummary(value="Done"))
        request.start()
        request.complete()
        with pytest.raises(InvalidTransitionError):
            request.start()

    def test_start_from_failed_raises(self) -> None:
        request = make_valid_request()
        request.start()
        request.fail(FailureReason(value="Error"))
        with pytest.raises(InvalidTransitionError):
            request.start()

    def test_start_from_cancelled_raises(self) -> None:
        request = make_valid_request()
        request.cancel()
        with pytest.raises(InvalidTransitionError):
            request.start()


class TestResearchRequestComplete:
    def test_complete_transitions_to_completed(self) -> None:
        request = make_valid_request()
        job = make_valid_job(request=request)
        job.start()
        job.complete(ResearchSummary(value="Done"))
        request.start()
        request.complete()
        assert request.status == ResearchStatus.COMPLETED
        assert request.updated_at is not None

    def test_complete_emits_event(self) -> None:
        request = make_valid_request()
        job = make_valid_job(request=request)
        job.start()
        job.complete(ResearchSummary(value="Done"))
        request.start()
        request.complete()
        events = request.events
        assert any(isinstance(e, ResearchCompleted) for e in events)

    def test_complete_without_jobs_raises(self) -> None:
        request = make_valid_request()
        request.start()
        with pytest.raises(NoJobsError):
            request.complete()

    def test_complete_with_unfinished_jobs_raises(self) -> None:
        request = make_valid_request()
        make_valid_job(request=request)
        request.start()
        with pytest.raises(IncompleteJobsError):
            request.complete()

    def test_complete_from_created_raises(self) -> None:
        request = make_valid_request()
        job = make_valid_job(request=request)
        job.start()
        job.complete(ResearchSummary(value="Done"))
        with pytest.raises(InvalidTransitionError):
            request.complete()

    def test_complete_from_completed_raises(self) -> None:
        request = make_valid_request()
        job = make_valid_job(request=request)
        job.start()
        job.complete(ResearchSummary(value="Done"))
        request.start()
        request.complete()
        with pytest.raises(InvalidTransitionError):
            request.complete()

    def test_complete_from_failed_raises(self) -> None:
        request = make_valid_request()
        request.start()
        request.fail(FailureReason(value="Error"))
        with pytest.raises(InvalidTransitionError):
            request.complete()

    def test_complete_from_cancelled_raises(self) -> None:
        request = make_valid_request()
        request.cancel()
        with pytest.raises(InvalidTransitionError):
            request.complete()


class TestResearchRequestFail:
    def test_fail_stores_reason(self) -> None:
        request = make_valid_request()
        request.start()
        reason = FailureReason(value="Critical error")
        request.fail(reason)
        assert request.status == ResearchStatus.FAILED
        assert request.failure_reason == reason
        assert request.updated_at is not None

    def test_fail_emits_event(self) -> None:
        request = make_valid_request()
        request.start()
        request.fail(FailureReason(value="Error"))
        events = request.events
        assert any(isinstance(e, ResearchFailed) for e in events)

    def test_failed_event_has_reason(self) -> None:
        request = make_valid_request()
        request.start()
        request.fail(FailureReason(value="Timeout"))
        failed_events = [e for e in request.events if isinstance(e, ResearchFailed)]
        assert len(failed_events) == 1
        assert failed_events[0].failure_reason == "Timeout"

    def test_fail_requires_reason(self) -> None:
        request = make_valid_request()
        request.start()
        with pytest.raises(InvalidFailureReasonError):
            request.fail(None)  # type: ignore[arg-type]

    def test_fail_from_created_raises(self) -> None:
        request = make_valid_request()
        with pytest.raises(InvalidTransitionError):
            request.fail(FailureReason(value="Error"))

    def test_fail_from_completed_raises(self) -> None:
        request = make_valid_request()
        job = make_valid_job(request=request)
        job.start()
        job.complete(ResearchSummary(value="Done"))
        request.start()
        request.complete()
        with pytest.raises(InvalidTransitionError):
            request.fail(FailureReason(value="Error"))

    def test_fail_from_failed_raises(self) -> None:
        request = make_valid_request()
        request.start()
        request.fail(FailureReason(value="Error"))
        with pytest.raises(InvalidTransitionError):
            request.fail(FailureReason(value="Again"))

    def test_fail_from_cancelled_raises(self) -> None:
        request = make_valid_request()
        request.cancel()
        with pytest.raises(InvalidTransitionError):
            request.fail(FailureReason(value="Error"))


class TestResearchRequestCancel:
    def test_cancel_from_created(self) -> None:
        request = make_valid_request()
        request.cancel()
        assert request.status == ResearchStatus.CANCELLED

    def test_cancel_from_running(self) -> None:
        request = make_valid_request()
        request.start()
        request.cancel()
        assert request.status == ResearchStatus.CANCELLED

    def test_cancel_emits_event(self) -> None:
        request = make_valid_request()
        request.cancel()
        events = request.events
        assert any(isinstance(e, ResearchCancelled) for e in events)

    def test_cancel_from_completed_raises(self) -> None:
        request = make_valid_request()
        job = make_valid_job(request=request)
        job.start()
        job.complete(ResearchSummary(value="Done"))
        request.start()
        request.complete()
        with pytest.raises(InvalidTransitionError):
            request.cancel()

    def test_cancel_from_failed_raises(self) -> None:
        request = make_valid_request()
        request.start()
        request.fail(FailureReason(value="Error"))
        with pytest.raises(InvalidTransitionError):
            request.cancel()

    def test_cancel_from_cancelled_raises(self) -> None:
        request = make_valid_request()
        request.cancel()
        with pytest.raises(InvalidTransitionError):
            request.cancel()


class TestResearchRequestTerminal:
    def test_created_not_terminal(self) -> None:
        assert not make_valid_request().is_terminal

    def test_running_not_terminal(self) -> None:
        request = make_valid_request()
        request.start()
        assert not request.is_terminal

    def test_completed_is_terminal(self) -> None:
        request = make_valid_request()
        job = make_valid_job(request=request)
        job.start()
        job.complete(ResearchSummary(value="Done"))
        request.start()
        request.complete()
        assert request.is_terminal

    def test_failed_is_terminal(self) -> None:
        request = make_valid_request()
        request.start()
        request.fail(FailureReason(value="Error"))
        assert request.is_terminal

    def test_cancelled_is_terminal(self) -> None:
        request = make_valid_request()
        request.cancel()
        assert request.is_terminal


class TestResearchRequestEvents:
    def test_requested_event_not_in_request_events(self) -> None:
        request = make_valid_request()
        assert len(request.events) == 0

    def test_multiple_events_collected(self) -> None:
        request = make_valid_request()
        request.start()
        request.cancel()
        assert len(request.events) == 2


# ===========================================================================
# Rules
# ===========================================================================


class TestAssertQueryRequired:
    def test_valid(self) -> None:
        assert_query_required("test query")

    def test_none_raises(self) -> None:
        with pytest.raises(InvalidQueryError):
            assert_query_required(None)

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidQueryError):
            assert_query_required("")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(InvalidQueryError):
            assert_query_required("   ")


class TestAssertGoalRequired:
    def test_valid(self) -> None:
        assert_goal_required("test goal")

    def test_none_raises(self) -> None:
        with pytest.raises(InvalidGoalError):
            assert_goal_required(None)

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidGoalError):
            assert_goal_required("")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(InvalidGoalError):
            assert_goal_required("   ")


class TestAssertSourceReferenceRequired:
    def test_valid(self) -> None:
        assert_source_reference_required("https://ref.com")

    def test_none_raises(self) -> None:
        with pytest.raises(InvalidSourceReferenceError):
            assert_source_reference_required(None)

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidSourceReferenceError):
            assert_source_reference_required("")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(InvalidSourceReferenceError):
            assert_source_reference_required("   ")


class TestAssertSummaryRequired:
    def test_valid(self) -> None:
        assert_summary_required(ResearchSummary(value="Summary"))

    def test_none_raises(self) -> None:
        with pytest.raises(InvalidSummaryError):
            assert_summary_required(None)


class TestAssertFailureReasonRequired:
    def test_valid(self) -> None:
        assert_failure_reason_required(FailureReason(value="Error"))

    def test_none_raises(self) -> None:
        with pytest.raises(InvalidFailureReasonError):
            assert_failure_reason_required(None)


class TestAssertRequestNotTerminal:
    @pytest.mark.parametrize("s", [ResearchStatus.CREATED, ResearchStatus.RUNNING])
    def test_non_terminal_passes(self, s: ResearchStatus) -> None:
        assert_request_not_terminal(s)

    @pytest.mark.parametrize("s", [ResearchStatus.COMPLETED, ResearchStatus.FAILED, ResearchStatus.CANCELLED])
    def test_terminal_raises(self, s: ResearchStatus) -> None:
        with pytest.raises(ResearchImmutableError):
            assert_request_not_terminal(s)


class TestAssertJobNotTerminal:
    @pytest.mark.parametrize("s", [ResearchStatus.CREATED, ResearchStatus.RUNNING])
    def test_non_terminal_passes(self, s: ResearchStatus) -> None:
        assert_job_not_terminal(s)

    @pytest.mark.parametrize("s", [ResearchStatus.COMPLETED, ResearchStatus.FAILED, ResearchStatus.CANCELLED])
    def test_terminal_raises(self, s: ResearchStatus) -> None:
        with pytest.raises(ResearchImmutableError):
            assert_job_not_terminal(s)


class TestAssertSourceTypeValid:
    @pytest.mark.parametrize("st", ["memory", "knowledge", "web", "document", "user"])
    def test_valid_string(self, st: str) -> None:
        assert_source_type_valid(st)

    @pytest.mark.parametrize("st", [SourceType.MEMORY, SourceType.KNOWLEDGE, SourceType.WEB])
    def test_valid_enum(self, st: SourceType) -> None:
        assert_source_type_valid(st)

    def test_invalid_raises(self) -> None:
        with pytest.raises(InvalidSourceTypeError):
            assert_source_type_valid("invalid_source")

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidSourceTypeError):
            assert_source_type_valid("")


class TestAssertPriorityValid:
    @pytest.mark.parametrize("p", ["low", "normal", "high", "critical"])
    def test_valid_string(self, p: str) -> None:
        assert_priority_valid(p)

    @pytest.mark.parametrize("p", [ResearchPriority.LOW, ResearchPriority.NORMAL, ResearchPriority.HIGH, ResearchPriority.CRITICAL])
    def test_valid_enum(self, p: ResearchPriority) -> None:
        assert_priority_valid(p)

    def test_invalid_raises(self) -> None:
        with pytest.raises(InvalidPriorityError):
            assert_priority_valid("super")

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidPriorityError):
            assert_priority_valid("")


class TestAssertNoDuplicateSourceReferences:
    def test_no_duplicate_passes(self) -> None:
        source = ResearchSource(
            source_type=SourceType.WEB,
            reference=SourceReference(value="https://a.com"),
            confidence_score=ConfidenceScore(value=0.5),
        )
        existing = [
            ResearchSource(
                source_type=SourceType.DOCUMENT,
                reference=SourceReference(value="https://b.com"),
                confidence_score=ConfidenceScore(value=0.9),
            )
        ]
        assert_no_duplicate_source_references(source, existing)

    def test_duplicate_raises(self) -> None:
        ref = "https://same.com"
        source = ResearchSource(
            source_type=SourceType.WEB,
            reference=SourceReference(value=ref),
            confidence_score=ConfidenceScore(value=0.5),
        )
        existing = [
            ResearchSource(
                source_type=SourceType.DOCUMENT,
                reference=SourceReference(value=ref),
                confidence_score=ConfidenceScore(value=0.9),
            )
        ]
        with pytest.raises(DuplicateSourceReferenceError):
            assert_no_duplicate_source_references(source, existing)

    def test_source_without_reference_passes(self) -> None:
        source = ResearchSource(
            source_type=SourceType.WEB,
            reference=None,
            confidence_score=ConfidenceScore(value=0.5),
        )
        assert_no_duplicate_source_references(source, [])


class TestAssertConfidenceScoreProvided:
    def test_with_score_passes(self) -> None:
        source = ResearchSource(
            confidence_score=ConfidenceScore(value=0.5),
        )
        assert_confidence_score_provided(source)

    def test_without_score_raises(self) -> None:
        source = ResearchSource(confidence_score=None)
        with pytest.raises(MissingConfidenceScoreError):
            assert_confidence_score_provided(source)


class TestAssertAllJobsCompleted:
    def test_all_completed_passes(self) -> None:
        request = make_valid_request()
        j1 = make_valid_job(request=request)
        j1.start()
        j1.complete(ResearchSummary(value="A"))
        j2 = make_valid_job(request=request)
        j2.start()
        j2.complete(ResearchSummary(value="B"))
        assert_all_jobs_completed(request)

    def test_unfinished_job_raises(self) -> None:
        request = make_valid_request()
        make_valid_job(request=request)
        j2 = make_valid_job(request=request)
        j2.start()
        j2.complete(ResearchSummary(value="B"))
        with pytest.raises(IncompleteJobsError):
            assert_all_jobs_completed(request)

    def test_no_jobs_passes(self) -> None:
        request = make_valid_request()
        assert_all_jobs_completed(request)


class TestAssertJobNotCancelled:
    def test_created_passes(self) -> None:
        assert_job_not_cancelled(ResearchStatus.CREATED)

    def test_running_passes(self) -> None:
        assert_job_not_cancelled(ResearchStatus.RUNNING)

    def test_cancelled_raises(self) -> None:
        with pytest.raises(CancelledJobRestartError):
            assert_job_not_cancelled(ResearchStatus.CANCELLED)


class TestAssertQueryLength:
    def test_within_limit_passes(self) -> None:
        assert_query_length("short query")

    def test_exact_limit_passes(self) -> None:
        assert_query_length("x" * MAX_QUERY_LENGTH)

    def test_exceeds_limit_raises(self) -> None:
        with pytest.raises(QueryTooLongError):
            assert_query_length("x" * (MAX_QUERY_LENGTH + 1))


class TestAssertSummaryLength:
    def test_within_limit_passes(self) -> None:
        assert_summary_length("short summary")

    def test_exact_limit_passes(self) -> None:
        assert_summary_length("x" * MAX_SUMMARY_LENGTH)

    def test_exceeds_limit_raises(self) -> None:
        with pytest.raises(SummaryTooLongError):
            assert_summary_length("x" * (MAX_SUMMARY_LENGTH + 1))


class TestAssertRequestCanTransition:
    @pytest.mark.parametrize(
        "current,target",
        [
            (ResearchStatus.CREATED, ResearchStatus.RUNNING),
            (ResearchStatus.CREATED, ResearchStatus.CANCELLED),
            (ResearchStatus.RUNNING, ResearchStatus.COMPLETED),
            (ResearchStatus.RUNNING, ResearchStatus.FAILED),
            (ResearchStatus.RUNNING, ResearchStatus.CANCELLED),
        ],
    )
    def test_valid_transition(self, current: ResearchStatus, target: ResearchStatus) -> None:
        assert_request_can_transition(current, target)

    @pytest.mark.parametrize(
        "current,target",
        [
            (ResearchStatus.COMPLETED, ResearchStatus.RUNNING),
            (ResearchStatus.FAILED, ResearchStatus.RUNNING),
            (ResearchStatus.CANCELLED, ResearchStatus.RUNNING),
            (ResearchStatus.CREATED, ResearchStatus.COMPLETED),
            (ResearchStatus.CREATED, ResearchStatus.FAILED),
            (ResearchStatus.COMPLETED, ResearchStatus.COMPLETED),
        ],
    )
    def test_invalid_transition_raises(self, current: ResearchStatus, target: ResearchStatus) -> None:
        with pytest.raises(InvalidTransitionError):
            assert_request_can_transition(current, target)


class TestAssertJobCanTransition:
    @pytest.mark.parametrize(
        "current,target",
        [
            (ResearchStatus.CREATED, ResearchStatus.RUNNING),
            (ResearchStatus.CREATED, ResearchStatus.CANCELLED),
            (ResearchStatus.RUNNING, ResearchStatus.COMPLETED),
            (ResearchStatus.RUNNING, ResearchStatus.FAILED),
            (ResearchStatus.RUNNING, ResearchStatus.CANCELLED),
        ],
    )
    def test_valid_transition(self, current: ResearchStatus, target: ResearchStatus) -> None:
        assert_job_can_transition(current, target)

    @pytest.mark.parametrize(
        "current,target",
        [
            (ResearchStatus.COMPLETED, ResearchStatus.RUNNING),
            (ResearchStatus.FAILED, ResearchStatus.RUNNING),
            (ResearchStatus.CANCELLED, ResearchStatus.RUNNING),
            (ResearchStatus.CREATED, ResearchStatus.COMPLETED),
            (ResearchStatus.CREATED, ResearchStatus.FAILED),
        ],
    )
    def test_invalid_transition_raises(self, current: ResearchStatus, target: ResearchStatus) -> None:
        with pytest.raises(InvalidTransitionError):
            assert_job_can_transition(current, target)


class TestTransitionTables:
    def test_completed_has_no_valid_transitions(self) -> None:
        assert VALID_REQUEST_TRANSITIONS[ResearchStatus.COMPLETED] == set()
        assert VALID_JOB_TRANSITIONS[ResearchStatus.COMPLETED] == set()

    def test_failed_has_no_valid_transitions(self) -> None:
        assert VALID_REQUEST_TRANSITIONS[ResearchStatus.FAILED] == set()
        assert VALID_JOB_TRANSITIONS[ResearchStatus.FAILED] == set()

    def test_cancelled_has_no_valid_transitions(self) -> None:
        assert VALID_REQUEST_TRANSITIONS[ResearchStatus.CANCELLED] == set()
        assert VALID_JOB_TRANSITIONS[ResearchStatus.CANCELLED] == set()

    def test_created_valid_transitions(self) -> None:
        assert VALID_REQUEST_TRANSITIONS[ResearchStatus.CREATED] == {
            ResearchStatus.RUNNING, ResearchStatus.CANCELLED,
        }
        assert VALID_JOB_TRANSITIONS[ResearchStatus.CREATED] == {
            ResearchStatus.RUNNING, ResearchStatus.CANCELLED,
        }

    def test_running_valid_transitions(self) -> None:
        assert VALID_REQUEST_TRANSITIONS[ResearchStatus.RUNNING] == {
            ResearchStatus.COMPLETED, ResearchStatus.FAILED, ResearchStatus.CANCELLED,
        }
        assert VALID_JOB_TRANSITIONS[ResearchStatus.RUNNING] == {
            ResearchStatus.COMPLETED, ResearchStatus.FAILED, ResearchStatus.CANCELLED,
        }


# ===========================================================================
# Validation Functions
# ===========================================================================


class TestValidateRequestCreation:
    def test_valid(self) -> None:
        result = validate_request_creation(query="q", goal="g", priority="high")
        assert result == ResearchPriority.HIGH

    def test_valid_enum_priority(self) -> None:
        result = validate_request_creation(query="q", goal="g", priority=ResearchPriority.LOW)
        assert result == ResearchPriority.LOW

    def test_missing_query_raises(self) -> None:
        with pytest.raises(InvalidQueryError):
            validate_request_creation(query=None, goal="g", priority="normal")

    def test_missing_goal_raises(self) -> None:
        with pytest.raises(InvalidGoalError):
            validate_request_creation(query="q", goal=None, priority="normal")

    def test_invalid_priority_raises(self) -> None:
        with pytest.raises(InvalidPriorityError):
            validate_request_creation(query="q", goal="g", priority="invalid")

    def test_query_too_long_raises(self) -> None:
        with pytest.raises(QueryTooLongError):
            validate_request_creation(query="x" * (MAX_QUERY_LENGTH + 1), goal="g", priority="normal")


class TestValidateJobCreation:
    def test_valid_without_priority(self) -> None:
        result = validate_job_creation(goal="g")
        assert result is None

    def test_valid_with_priority(self) -> None:
        result = validate_job_creation(goal="g", priority="high")
        assert result == ResearchPriority.HIGH

    def test_valid_with_enum_priority(self) -> None:
        result = validate_job_creation(goal="g", priority=ResearchPriority.LOW)
        assert result == ResearchPriority.LOW

    def test_missing_goal_raises(self) -> None:
        with pytest.raises(InvalidGoalError):
            validate_job_creation(goal=None)

    def test_invalid_priority_raises(self) -> None:
        with pytest.raises(InvalidPriorityError):
            validate_job_creation(goal="g", priority="invalid")


class TestValidateSourceCreation:
    def test_valid(self) -> None:
        result = validate_source_creation(reference="https://ref.com", source_type="web")
        assert result == SourceType.WEB

    def test_valid_enum(self) -> None:
        result = validate_source_creation(reference="https://ref.com", source_type=SourceType.KNOWLEDGE)
        assert result == SourceType.KNOWLEDGE

    def test_missing_reference_raises(self) -> None:
        with pytest.raises(InvalidSourceReferenceError):
            validate_source_creation(reference=None, source_type="web")

    def test_invalid_source_type_raises(self) -> None:
        with pytest.raises(InvalidSourceTypeError):
            validate_source_creation(reference="https://ref.com", source_type="invalid")


# ===========================================================================
# Factory
# ===========================================================================


class TestResearchFactoryCreateRequest:
    def test_create_valid(self) -> None:
        request, event = ResearchFactory.create_request(query="q", goal="g", priority="normal")
        assert isinstance(request, ResearchRequest)
        assert isinstance(event, ResearchRequested)
        assert request.query is not None
        assert request.query.value == "q"
        assert request.goal is not None
        assert request.goal.value == "g"
        assert request.priority == ResearchPriority.NORMAL
        assert request.status == ResearchStatus.CREATED
        assert event.query == "q"
        assert event.goal == "g"
        assert event.priority == "normal"

    def test_create_with_enum_priority(self) -> None:
        request, _ = ResearchFactory.create_request(query="q", goal="g", priority=ResearchPriority.CRITICAL)
        assert request.priority == ResearchPriority.CRITICAL

    def test_empty_query_raises(self) -> None:
        with pytest.raises(InvalidQueryError):
            ResearchFactory.create_request(query="", goal="g", priority="normal")

    def test_empty_goal_raises(self) -> None:
        with pytest.raises(InvalidGoalError):
            ResearchFactory.create_request(query="q", goal="", priority="normal")

    def test_invalid_priority_raises(self) -> None:
        with pytest.raises(InvalidPriorityError):
            ResearchFactory.create_request(query="q", goal="g", priority="bogus")

    def test_query_too_long_raises(self) -> None:
        with pytest.raises(QueryTooLongError):
            ResearchFactory.create_request(query="x" * (MAX_QUERY_LENGTH + 1), goal="g", priority="normal")


class TestResearchFactoryCreateJob:
    def test_create_valid(self) -> None:
        request = make_valid_request()
        job = ResearchFactory.create_job(request=request, goal="sub goal")
        assert isinstance(job, ResearchJob)
        assert job.goal is not None
        assert job.goal.value == "sub goal"
        assert job.priority == request.priority
        assert job.status == ResearchStatus.CREATED
        assert len(request.jobs) == 1

    def test_create_with_priority(self) -> None:
        request = make_valid_request()
        job = ResearchFactory.create_job(request=request, goal="sub", priority="high")
        assert job.priority == ResearchPriority.HIGH

    def test_empty_goal_raises(self) -> None:
        request = make_valid_request()
        with pytest.raises(InvalidGoalError):
            ResearchFactory.create_job(request=request, goal="")


class TestResearchFactoryAddSource:
    def test_add_valid_source(self) -> None:
        job = ResearchJob()
        source = ResearchFactory.add_source(
            job=job,
            reference="https://example.com",
            source_type="web",
            confidence_score=0.85,
        )
        assert isinstance(source, ResearchSource)
        assert len(job.sources) == 1
        assert job.sources[0] == source
        assert source.reference is not None
        assert source.reference.value == "https://example.com"
        assert source.confidence_score is not None
        assert source.confidence_score.value == 0.85
        assert source.source_type == SourceType.WEB

    def test_add_source_with_enum_type(self) -> None:
        job = ResearchJob()
        ResearchFactory.add_source(
            job=job,
            reference="https://ref.com",
            source_type=SourceType.DOCUMENT,
            confidence_score=0.9,
        )
        assert job.sources[0].source_type == SourceType.DOCUMENT

    def test_missing_reference_raises(self) -> None:
        job = ResearchJob()
        with pytest.raises(InvalidSourceReferenceError):
            ResearchFactory.add_source(
                job=job,
                reference="",
                source_type="web",
                confidence_score=0.5,
            )

    def test_invalid_source_type_raises(self) -> None:
        job = ResearchJob()
        with pytest.raises(InvalidSourceTypeError):
            ResearchFactory.add_source(
                job=job,
                reference="https://ref.com",
                source_type="alien",
                confidence_score=0.5,
            )


class TestResearchFactoryCompleteJob:
    def test_complete_job(self) -> None:
        job = make_started_job()
        summary = ResearchFactory.complete_job(job=job, summary="Great results")
        assert isinstance(summary, ResearchSummary)
        assert summary.value == "Great results"
        assert job.status == ResearchStatus.COMPLETED

    def test_complete_job_empty_summary_raises(self) -> None:
        job = make_started_job()
        with pytest.raises(InvalidSummaryError):
            ResearchFactory.complete_job(job=job, summary="")


class TestResearchFactoryFailJob:
    def test_fail_job(self) -> None:
        job = make_started_job()
        reason = ResearchFactory.fail_job(job=job, reason="Timeout")
        assert isinstance(reason, FailureReason)
        assert reason.value == "Timeout"
        assert job.status == ResearchStatus.FAILED

    def test_fail_job_empty_reason_raises(self) -> None:
        job = make_started_job()
        with pytest.raises(InvalidFailureReasonError):
            ResearchFactory.fail_job(job=job, reason="")


# ===========================================================================
# Full Lifecycle Transitions
# ===========================================================================


class TestRequestLifecycle:
    def test_full_success_lifecycle(self) -> None:
        request = make_valid_request(query="Research AI", goal="Understand AI", priority="high")
        assert request.status == ResearchStatus.CREATED

        job = make_valid_job(request=request, goal="Literature review")
        job.start()
        source = ResearchFactory.add_source(
            job=job,
            reference="https://paper.com",
            source_type="knowledge",
            confidence_score=0.95,
        )
        assert source in job.sources
        job.complete(ResearchSummary(value="Reviewed 10 papers"))

        request.start()
        assert request.status == ResearchStatus.RUNNING

        request.complete()
        assert request.status == ResearchStatus.COMPLETED
        assert request.is_terminal

    def test_full_failure_lifecycle(self) -> None:
        request = make_valid_request(query="q", goal="g")
        request.start()
        reason = FailureReason(value="Data unavailable")
        request.fail(reason)
        assert request.status == ResearchStatus.FAILED
        assert request.failure_reason == reason

    def test_cancel_before_start(self) -> None:
        request = make_valid_request()
        request.cancel()
        assert request.status == ResearchStatus.CANCELLED

    def test_cancel_during_execution(self) -> None:
        request = make_valid_request()
        request.start()
        request.cancel()
        assert request.status == ResearchStatus.CANCELLED


class TestJobLifecycle:
    def test_full_success_lifecycle(self) -> None:
        job = ResearchJob(priority=ResearchPriority.HIGH)
        assert job.status == ResearchStatus.CREATED
        assert not job.is_terminal

        job.start()
        assert job.status == ResearchStatus.RUNNING

        job.add_source(make_valid_source())
        job.add_source(make_valid_source(reference="https://other.com"))
        assert len(job.sources) == 2

        job.complete(ResearchSummary(value="Done"))
        assert job.status == ResearchStatus.COMPLETED
        assert job.is_terminal

    def test_full_failure_lifecycle(self) -> None:
        job = make_started_job()
        job.fail(FailureReason(value="Error occurred"))
        assert job.status == ResearchStatus.FAILED
        assert job.is_terminal

    def test_cancel_lifecycle(self) -> None:
        job = ResearchJob()
        job.cancel()
        assert job.status == ResearchStatus.CANCELLED
        assert job.is_terminal


# ===========================================================================
# Cross-Entity Validation
# ===========================================================================


class TestCrossEntityValidation:
    def test_request_complete_requires_all_jobs_done(self) -> None:
        request = make_valid_request()
        make_valid_job(request=request)  # CREATED, not started
        j2 = make_valid_job(request=request, goal="second")
        j2.start()
        j2.complete(ResearchSummary(value="Done"))
        request.start()
        with pytest.raises(IncompleteJobsError):
            request.complete()

    def test_request_complete_with_two_jobs(self) -> None:
        request = make_valid_request()
        j1 = make_valid_job(request=request, goal="first")
        j1.start()
        j1.complete(ResearchSummary(value="One"))
        j2 = make_valid_job(request=request, goal="second")
        j2.start()
        j2.complete(ResearchSummary(value="Two"))
        request.start()
        request.complete()
        assert request.status == ResearchStatus.COMPLETED

    def test_duplicate_sources_in_same_job_raises(self) -> None:
        job = ResearchJob()
        ref = "https://dup.com"
        s1 = ResearchSource(
            source_type=SourceType.WEB,
            reference=SourceReference(value=ref),
            confidence_score=ConfidenceScore(value=0.8),
        )
        s2 = ResearchSource(
            source_type=SourceType.DOCUMENT,
            reference=SourceReference(value=ref),
            confidence_score=ConfidenceScore(value=0.9),
        )
        job.add_source(s1)
        with pytest.raises(DuplicateSourceReferenceError):
            job.add_source(s2)

    def test_duplicate_across_jobs_allowed(self) -> None:
        request = make_valid_request()
        j1 = make_valid_job(request=request, goal="first")
        j2 = make_valid_job(request=request, goal="second")
        ref = "https://shared.com"
        s1 = ResearchSource(
            source_type=SourceType.WEB,
            reference=SourceReference(value=ref),
            confidence_score=ConfidenceScore(value=0.8),
        )
        s2 = ResearchSource(
            source_type=SourceType.WEB,
            reference=SourceReference(value=ref),
            confidence_score=ConfidenceScore(value=0.9),
        )
        j1.add_source(s1)
        j2.add_source(s2)
        assert len(j1.sources) == 1
        assert len(j2.sources) == 1

    def test_add_source_to_completed_job_raises(self) -> None:
        job = make_started_job()
        job.complete(ResearchSummary(value="Done"))
        with pytest.raises(ResearchImmutableError):
            job.add_source(make_valid_source())


# ===========================================================================
# Multi-Error Validation
# ===========================================================================


class TestMultiErrorValidation:
    def test_empty_query_and_goal_raises_query_first(self) -> None:
        with pytest.raises(InvalidQueryError):
            validate_request_creation(query=None, goal=None, priority="normal")

    def test_missing_all_source_fields(self) -> None:
        job = ResearchJob()
        with pytest.raises(InvalidSourceReferenceError):
            ResearchFactory.add_source(
                job=job,
                reference="",
                source_type="web",
                confidence_score=0.5,
            )

    def test_fail_job_without_starting_invalid(self) -> None:
        job = ResearchJob()
        with pytest.raises(InvalidTransitionError):
            job.fail(FailureReason(value="Error"))

    def test_complete_job_without_starting_invalid(self) -> None:
        job = ResearchJob()
        with pytest.raises(InvalidTransitionError):
            job.complete(ResearchSummary(value="Done"))

    def test_fail_request_without_starting_invalid(self) -> None:
        request = make_valid_request()
        with pytest.raises(InvalidTransitionError):
            request.fail(FailureReason(value="Error"))

    def test_complete_request_without_starting_invalid(self) -> None:
        request = make_valid_request()
        job = make_valid_job(request=request)
        job.start()
        job.complete(ResearchSummary(value="Done"))
        with pytest.raises(InvalidTransitionError):
            request.complete()

    def test_cancel_then_restart_job_invalid(self) -> None:
        job = ResearchJob()
        job.cancel()
        with pytest.raises(CancelledJobRestartError):
            job.start()

    def test_cancel_then_fail_job_invalid(self) -> None:
        job = ResearchJob()
        job.cancel()
        with pytest.raises(CancelledJobRestartError):
            job.fail(FailureReason(value="Error"))

    def test_cancel_then_complete_job_invalid(self) -> None:
        job = ResearchJob()
        job.cancel()
        with pytest.raises(CancelledJobRestartError):
            job.complete(ResearchSummary(value="Done"))


# ===========================================================================
# Exception Hierarchy
# ===========================================================================


class TestExceptionHierarchy:
    def test_all_exceptions_are_domain_errors(self) -> None:
        exceptions = [
            InvalidQueryError(""),
            InvalidGoalError(""),
            InvalidSourceReferenceError(""),
            InvalidConfidenceScoreError(0.5),
            InvalidSummaryError(""),
            InvalidFailureReasonError(""),
            ResearchImmutableError("created"),
            InvalidSourceTypeError("x"),
            InvalidPriorityError("x"),
            InvalidTransitionError("e", "a", "b"),
            NoJobsError(),
            DuplicateSourceReferenceError(),
            MissingConfidenceScoreError(),
            IncompleteJobsError(),
            CancelledJobRestartError(),
            QueryTooLongError(100, 50),
            SummaryTooLongError(100, 50),
        ]
        for exc in exceptions:
            assert isinstance(exc, ResearchDomainError)

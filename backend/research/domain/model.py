from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import auto, StrEnum
from uuid import UUID, uuid4


# =============================================================================
# Enums
# =============================================================================


class ResearchStatus(StrEnum):
    CREATED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class SourceType(StrEnum):
    MEMORY = auto()
    KNOWLEDGE = auto()
    WEB = auto()
    DOCUMENT = auto()
    USER = auto()


class ResearchPriority(StrEnum):
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    CRITICAL = auto()


# =============================================================================
# Value Objects
# =============================================================================


@dataclass(frozen=True)
class ResearchRequestId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class ResearchJobId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class QueryText:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"QueryText value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.research.domain.exceptions import InvalidQueryError

            raise InvalidQueryError("Query must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class ResearchGoal:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"ResearchGoal value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.research.domain.exceptions import InvalidGoalError

            raise InvalidGoalError("Research goal must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class SourceReference:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"SourceReference value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.research.domain.exceptions import InvalidSourceReferenceError

            raise InvalidSourceReferenceError("Source reference must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class ConfidenceScore:
    value: float

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, float)):
            msg = f"ConfidenceScore value must be a number, got {type(self.value).__name__}"
            raise TypeError(msg)
        if self.value < 0.0 or self.value > 1.0:
            from backend.research.domain.exceptions import InvalidConfidenceScoreError

            raise InvalidConfidenceScoreError(self.value)

    def __float__(self) -> float:
        return float(self.value)


@dataclass(frozen=True)
class ResearchSummary:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"ResearchSummary value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.research.domain.exceptions import InvalidSummaryError

            raise InvalidSummaryError("Research summary must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class FailureReason:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"FailureReason value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.research.domain.exceptions import InvalidFailureReasonError

            raise InvalidFailureReasonError("Failure reason must not be empty")

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


# =============================================================================
# Domain Events
# =============================================================================


@dataclass(frozen=True)
class ResearchRequested:
    request_id: ResearchRequestId
    query: str
    goal: str
    priority: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class ResearchStarted:
    request_id: ResearchRequestId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class ResearchCompleted:
    request_id: ResearchRequestId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class ResearchFailed:
    request_id: ResearchRequestId
    failure_reason: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class ResearchCancelled:
    request_id: ResearchRequestId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class SourceAdded:
    request_id: ResearchRequestId
    job_id: ResearchJobId
    source_id: UUID
    source_type: str
    reference: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class ResearchSummaryGenerated:
    request_id: ResearchRequestId
    job_id: ResearchJobId
    summary: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


# =============================================================================
# Entities
# =============================================================================


class ResearchSource:
    """A source of information for a research job."""

    def __init__(
        self,
        source_id: UUID | None = None,
        source_type: SourceType = SourceType.WEB,
        reference: SourceReference | None = None,
        confidence_score: ConfidenceScore | None = None,
    ) -> None:
        self._source_id = source_id or uuid4()
        self._source_type = source_type
        self._reference = reference
        self._confidence_score = confidence_score

    @property
    def source_id(self) -> UUID:
        return self._source_id

    @property
    def source_type(self) -> SourceType:
        return self._source_type

    @property
    def reference(self) -> SourceReference | None:
        return self._reference

    @property
    def confidence_score(self) -> ConfidenceScore | None:
        return self._confidence_score

    def __repr__(self) -> str:
        return (
            f"ResearchSource(id={self._source_id}, "
            f"type={self._source_type.value})"
        )


class ResearchJob:
    """A single research job within a research request."""

    def __init__(
        self,
        job_id: ResearchJobId | None = None,
        goal: ResearchGoal | None = None,
        status: ResearchStatus = ResearchStatus.CREATED,
        priority: ResearchPriority = ResearchPriority.NORMAL,
        sources: list[ResearchSource] | None = None,
        summary: ResearchSummary | None = None,
        failure_reason: FailureReason | None = None,
        created_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        self._job_id = job_id or ResearchJobId()
        self._goal = goal
        self._status = status
        self._priority = priority
        self._sources = sources or []
        self._summary = summary
        self._failure_reason = failure_reason
        self._created_at = created_at or datetime.now(tz=timezone.utc)
        self._completed_at = completed_at
        self._events: list[SourceAdded | ResearchSummaryGenerated] = []

    @property
    def job_id(self) -> ResearchJobId:
        return self._job_id

    @property
    def goal(self) -> ResearchGoal | None:
        return self._goal

    @property
    def status(self) -> ResearchStatus:
        return self._status

    @property
    def priority(self) -> ResearchPriority:
        return self._priority

    @property
    def sources(self) -> list[ResearchSource]:
        return list(self._sources)

    @property
    def summary(self) -> ResearchSummary | None:
        return self._summary

    @property
    def failure_reason(self) -> FailureReason | None:
        return self._failure_reason

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def completed_at(self) -> datetime | None:
        return self._completed_at

    @property
    def events(self) -> list[SourceAdded | ResearchSummaryGenerated]:
        return list(self._events)

    @property
    def is_terminal(self) -> bool:
        return self._status in (
            ResearchStatus.COMPLETED,
            ResearchStatus.FAILED,
            ResearchStatus.CANCELLED,
        )

    # -- commands -----------------------------------------------------------

    def start(self) -> None:
        from backend.research.domain.rules import (
            assert_job_can_transition,
            assert_job_not_cancelled,
        )

        assert_job_not_cancelled(self._status)
        assert_job_can_transition(self._status, ResearchStatus.RUNNING)
        self._status = ResearchStatus.RUNNING

    def complete(self, summary: ResearchSummary) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.research.domain.rules import (
            assert_job_can_transition,
            assert_job_not_cancelled,
            assert_summary_required,
        )

        assert_summary_required(summary)
        assert_job_not_cancelled(self._status)
        assert_job_can_transition(self._status, ResearchStatus.COMPLETED)
        self._summary = summary
        self._status = ResearchStatus.COMPLETED
        self._completed_at = now
        self._events.append(
            ResearchSummaryGenerated(
                request_id=ResearchRequestId(),
                job_id=self._job_id,
                summary=summary.value,
                occurred_at=now,
            )
        )

    def fail(self, reason: FailureReason) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.research.domain.rules import (
            assert_failure_reason_required,
            assert_job_can_transition,
            assert_job_not_cancelled,
        )

        assert_failure_reason_required(reason)
        assert_job_not_cancelled(self._status)
        assert_job_can_transition(self._status, ResearchStatus.FAILED)
        self._failure_reason = reason
        self._status = ResearchStatus.FAILED
        self._completed_at = now

    def cancel(self) -> None:
        from backend.research.domain.rules import assert_job_can_transition

        assert_job_can_transition(self._status, ResearchStatus.CANCELLED)
        self._status = ResearchStatus.CANCELLED

    def add_source(self, source: ResearchSource) -> None:
        from backend.research.domain.rules import (
            assert_confidence_score_provided,
            assert_job_not_terminal,
            assert_no_duplicate_source_references,
        )

        assert_job_not_terminal(self._status)
        assert_confidence_score_provided(source)
        assert_no_duplicate_source_references(source, self._sources)
        self._sources.append(source)
        self._events.append(
            SourceAdded(
                request_id=ResearchRequestId(),
                job_id=self._job_id,
                source_id=source.source_id,
                source_type=source.source_type.value,
                reference=str(source.reference) if source.reference else "",
                occurred_at=datetime.now(tz=timezone.utc),
            )
        )

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"ResearchJob(id={self._job_id}, "
            f"status={self._status.value})"
        )


class ResearchRequest:
    """Aggregate root for the research domain."""

    def __init__(
        self,
        request_id: ResearchRequestId | None = None,
        query: QueryText | None = None,
        goal: ResearchGoal | None = None,
        priority: ResearchPriority = ResearchPriority.NORMAL,
        jobs: list[ResearchJob] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self._request_id = request_id or ResearchRequestId()
        self._query = query
        self._goal = goal
        self._priority = priority
        self._status: ResearchStatus = ResearchStatus.CREATED
        self._jobs = jobs or []
        self._failure_reason: FailureReason | None = None
        self._created_at = created_at or datetime.now(tz=timezone.utc)
        self._updated_at = updated_at
        self._events: list[ResearchRequested | ResearchStarted | ResearchCompleted | ResearchFailed | ResearchCancelled] = []

    @property
    def request_id(self) -> ResearchRequestId:
        return self._request_id

    @property
    def query(self) -> QueryText | None:
        return self._query

    @property
    def goal(self) -> ResearchGoal | None:
        return self._goal

    @property
    def priority(self) -> ResearchPriority:
        return self._priority

    @property
    def status(self) -> ResearchStatus:
        return self._status

    @property
    def jobs(self) -> list[ResearchJob]:
        return list(self._jobs)

    @property
    def failure_reason(self) -> FailureReason | None:
        return self._failure_reason

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    @property
    def events(self) -> list[ResearchRequested | ResearchStarted | ResearchCompleted | ResearchFailed | ResearchCancelled]:
        return list(self._events)

    @property
    def is_terminal(self) -> bool:
        return self._status in (
            ResearchStatus.COMPLETED,
            ResearchStatus.FAILED,
            ResearchStatus.CANCELLED,
        )

    # -- commands -----------------------------------------------------------

    def start(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.research.domain.rules import (
            assert_request_can_transition,
        )

        assert_request_can_transition(self._status, ResearchStatus.RUNNING)
        self._status = ResearchStatus.RUNNING
        self._updated_at = now
        self._events.append(
            ResearchStarted(request_id=self._request_id, occurred_at=now)
        )

    def complete(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.research.domain.rules import (
            assert_all_jobs_completed,
            assert_request_can_transition,
            assert_request_has_jobs,
        )

        assert_request_can_transition(self._status, ResearchStatus.COMPLETED)
        assert_request_has_jobs(self)
        assert_all_jobs_completed(self)
        self._status = ResearchStatus.COMPLETED
        self._updated_at = now
        self._events.append(
            ResearchCompleted(request_id=self._request_id, occurred_at=now)
        )

    def fail(self, reason: FailureReason) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.research.domain.rules import (
            assert_failure_reason_required,
            assert_request_can_transition,
        )

        assert_failure_reason_required(reason)
        assert_request_can_transition(self._status, ResearchStatus.FAILED)
        self._failure_reason = reason
        self._status = ResearchStatus.FAILED
        self._updated_at = now
        self._events.append(
            ResearchFailed(
                request_id=self._request_id,
                failure_reason=reason.value,
                occurred_at=now,
            )
        )

    def cancel(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.research.domain.rules import (
            assert_request_can_transition,
        )

        assert_request_can_transition(self._status, ResearchStatus.CANCELLED)
        self._status = ResearchStatus.CANCELLED
        self._updated_at = now
        self._events.append(
            ResearchCancelled(request_id=self._request_id, occurred_at=now)
        )

    def add_job(self, job: ResearchJob) -> None:
        from backend.research.domain.rules import assert_request_not_terminal

        assert_request_not_terminal(self._status)
        self._jobs.append(job)
        self._updated_at = datetime.now(tz=timezone.utc)

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"ResearchRequest(id={self._request_id}, "
            f"status={self._status.value}, "
            f"priority={self._priority.value})"
        )

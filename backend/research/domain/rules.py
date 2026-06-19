from __future__ import annotations

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
    ResearchImmutableError,
    SummaryTooLongError,
)
from backend.research.domain.model import (
    ConfidenceScore,
    FailureReason,
    QueryText,
    ResearchGoal,
    ResearchPriority,
    ResearchRequest,
    ResearchSource,
    ResearchStatus,
    SourceReference,
    SourceType,
)

# GLOBAL CONFIGURATION
MAX_QUERY_LENGTH: int = 5000
MAX_SUMMARY_LENGTH: int = 20000

VALID_REQUEST_TRANSITIONS: dict[ResearchStatus, set[ResearchStatus]] = {
    ResearchStatus.CREATED: {ResearchStatus.RUNNING, ResearchStatus.CANCELLED},
    ResearchStatus.RUNNING: {ResearchStatus.COMPLETED, ResearchStatus.FAILED, ResearchStatus.CANCELLED},
    ResearchStatus.COMPLETED: set(),
    ResearchStatus.FAILED: set(),
    ResearchStatus.CANCELLED: set(),
}

VALID_JOB_TRANSITIONS: dict[ResearchStatus, set[ResearchStatus]] = {
    ResearchStatus.CREATED: {ResearchStatus.RUNNING, ResearchStatus.CANCELLED},
    ResearchStatus.RUNNING: {ResearchStatus.COMPLETED, ResearchStatus.FAILED, ResearchStatus.CANCELLED},
    ResearchStatus.COMPLETED: set(),
    ResearchStatus.FAILED: set(),
    ResearchStatus.CANCELLED: set(),
}


# -- Rule 1: Query required ---------------------------------------------------

def assert_query_required(query: str | None) -> None:
    if not query or not query.strip():
        raise InvalidQueryError("Query is required")


# -- Rule 2: Goal required ----------------------------------------------------

def assert_goal_required(goal: str | None) -> None:
    if not goal or not goal.strip():
        raise InvalidGoalError("Research goal is required")


# -- Rule 3: Source reference required ----------------------------------------

def assert_source_reference_required(reference: str | None) -> None:
    if not reference or not reference.strip():
        raise InvalidSourceReferenceError("Source reference is required")


# -- Rule 4: Confidence score between 0.0 and 1.0 (enforced by VO) ------------

# -- Rule 5: Summary required when COMPLETED -----------------------------------

def assert_summary_required(summary: ResearchSummary | None) -> None:
    if summary is None:
        raise InvalidSummaryError("Summary is required when COMPLETED")


# -- Rule 6: Failure reason required when FAILED -------------------------------

def assert_failure_reason_required(reason: FailureReason | None) -> None:
    if reason is None:
        raise InvalidFailureReasonError("Failure reason is required when FAILED")


# -- Rule 7 & 8: COMPLETED / CANCELLED research immutable ---------------------

def assert_request_not_terminal(status: ResearchStatus) -> None:
    if status in (ResearchStatus.COMPLETED, ResearchStatus.FAILED, ResearchStatus.CANCELLED):
        raise ResearchImmutableError(status.value)


def assert_job_not_terminal(status: ResearchStatus) -> None:
    if status in (ResearchStatus.COMPLETED, ResearchStatus.FAILED, ResearchStatus.CANCELLED):
        raise ResearchImmutableError(status.value)


# -- Rule 9: Source type must be valid ----------------------------------------

def assert_source_type_valid(source_type: str | SourceType) -> None:
    if isinstance(source_type, SourceType):
        return
    try:
        SourceType(source_type)
    except ValueError:
        raise InvalidSourceTypeError(source_type)


# -- Rule 10: Priority must be valid ------------------------------------------

def assert_priority_valid(priority: str | ResearchPriority) -> None:
    if isinstance(priority, ResearchPriority):
        return
    try:
        ResearchPriority(priority)
    except ValueError:
        raise InvalidPriorityError(priority)


# -- Rule 11: Job must start before complete -----------------------------------

def assert_job_started_before_complete(status: ResearchStatus) -> None:
    if status != ResearchStatus.RUNNING:
        raise InvalidTransitionError(
            "job", status.value, ResearchStatus.COMPLETED.value
        )


# -- Rule 12: Job must start before fail ---------------------------------------

def assert_job_started_before_fail(status: ResearchStatus) -> None:
    if status != ResearchStatus.RUNNING:
        raise InvalidTransitionError(
            "job", status.value, ResearchStatus.FAILED.value
        )


# -- Rule 13: Request must contain at least one job before completion ----------

def assert_request_has_jobs(request: ResearchRequest) -> None:
    if not request.jobs:
        raise NoJobsError()


# -- Rule 14: Duplicate source references not allowed within a job -------------

def assert_no_duplicate_source_references(
    source: ResearchSource,
    existing_sources: list[ResearchSource],
) -> None:
    if source.reference is None:
        return
    for existing in existing_sources:
        if existing.reference is not None and existing.reference == source.reference:
            raise DuplicateSourceReferenceError()


# -- Rule 15: Confidence score required for every source -----------------------

def assert_confidence_score_provided(source: ResearchSource) -> None:
    if source.confidence_score is None:
        raise MissingConfidenceScoreError()


# -- Rule 16: FAILED requests require failure reason ---------------------------

# Enforced by assert_failure_reason_required in the fail() command

# -- Rule 17: COMPLETED requests require all jobs completed --------------------

def assert_all_jobs_completed(request: ResearchRequest) -> None:
    for job in request.jobs:
        if job.status != ResearchStatus.COMPLETED:
            raise IncompleteJobsError()


# -- Rule 18: CANCELLED jobs cannot restart ------------------------------------

def assert_job_not_cancelled(status: ResearchStatus) -> None:
    if status == ResearchStatus.CANCELLED:
        raise CancelledJobRestartError()


# -- Rule 19: Query length max 5000 chars --------------------------------------

def assert_query_length(query: str, max_length: int = MAX_QUERY_LENGTH) -> None:
    if len(query) > max_length:
        raise QueryTooLongError(len(query), max_length)


# -- Rule 20: Summary length max 20000 chars -----------------------------------

def assert_summary_length(summary: str, max_length: int = MAX_SUMMARY_LENGTH) -> None:
    if len(summary) > max_length:
        raise SummaryTooLongError(len(summary), max_length)


# -- Request transition enforcement --------------------------------------------

def assert_request_can_transition(current: ResearchStatus, target: ResearchStatus) -> None:
    allowed = VALID_REQUEST_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError("research request", current.value, target.value)


# -- Job transition enforcement ------------------------------------------------

def assert_job_can_transition(current: ResearchStatus, target: ResearchStatus) -> None:
    allowed = VALID_JOB_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError("research job", current.value, target.value)


# -- Composite validators ------------------------------------------------------

def validate_request_creation(
    query: str | None,
    goal: str | None,
    priority: str | ResearchPriority,
) -> ResearchPriority:
    assert_query_required(query)
    assert_query_length(query or "")
    assert_goal_required(goal)
    assert_priority_valid(priority)

    if isinstance(priority, str):
        priority_vo = ResearchPriority(priority)
    else:
        priority_vo = priority

    return priority_vo


def validate_job_creation(
    goal: str | None,
    priority: str | ResearchPriority | None = None,
) -> ResearchPriority | None:
    assert_goal_required(goal)
    if priority is not None:
        assert_priority_valid(priority)
        if isinstance(priority, str):
            return ResearchPriority(priority)
        return priority
    return None


def validate_source_creation(
    reference: str | None,
    source_type: str | SourceType,
    confidence_score: float | None = None,
) -> SourceType:
    assert_source_reference_required(reference)
    assert_source_type_valid(source_type)
    if confidence_score is not None:
        InvalidConfidenceScoreError  # validated by ConfidenceScore VO
    if isinstance(source_type, str):
        return SourceType(source_type)
    return source_type

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from backend.research.domain.exceptions import InvalidSourceTypeError
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
    SourceReference,
    SourceType,
)
from backend.research.domain.rules import (
    assert_failure_reason_required,
    assert_request_not_terminal,
    validate_job_creation,
    validate_request_creation,
    validate_source_creation,
)


class ResearchFactory:
    """Factory for creating validated research domain aggregates."""

    @staticmethod
    def create_request(
        *,
        query: str,
        goal: str,
        priority: str | ResearchPriority,
    ) -> tuple[ResearchRequest, ResearchRequested]:
        priority_vo = validate_request_creation(
            query=query,
            goal=goal,
            priority=priority,
        )

        query_vo = QueryText(value=query)
        goal_vo = ResearchGoal(value=goal)

        now = datetime.now(tz=timezone.utc)
        request = ResearchRequest(
            request_id=ResearchRequestId(),
            query=query_vo,
            goal=goal_vo,
            priority=priority_vo,
            created_at=now,
        )

        event = ResearchRequested(
            request_id=request.request_id,
            query=query,
            goal=goal,
            priority=priority_vo.value,
            occurred_at=now,
        )

        return request, event

    @staticmethod
    def create_job(
        *,
        request: ResearchRequest,
        goal: str,
        priority: str | ResearchPriority | None = None,
    ) -> ResearchJob:
        priority_vo = validate_job_creation(
            goal=goal,
            priority=priority,
        )

        goal_vo = ResearchGoal(value=goal)
        now = datetime.now(tz=timezone.utc)
        job = ResearchJob(
            job_id=ResearchJobId(),
            goal=goal_vo,
            status=ResearchStatus.CREATED,
            priority=priority_vo or request.priority,
            created_at=now,
        )

        request.add_job(job)
        return job

    @staticmethod
    def add_source(
        *,
        job: ResearchJob,
        reference: str,
        source_type: str | SourceType,
        confidence_score: float,
    ) -> ResearchSource:
        source_type_vo = validate_source_creation(
            reference=reference,
            source_type=source_type,
            confidence_score=confidence_score,
        )
        if isinstance(source_type, str):
            source_type_vo = SourceType(source_type)
        else:
            source_type_vo = source_type

        reference_vo = SourceReference(value=reference)
        score_vo = ConfidenceScore(value=confidence_score)

        source = ResearchSource(
            source_id=uuid4(),
            source_type=source_type_vo,
            reference=reference_vo,
            confidence_score=score_vo,
        )

        job.add_source(source)
        return source

    @staticmethod
    def complete_job(
        *,
        job: ResearchJob,
        summary: str,
    ) -> ResearchSummary:
        summary_vo = ResearchSummary(value=summary)
        job.complete(summary_vo)
        return summary_vo

    @staticmethod
    def fail_job(
        *,
        job: ResearchJob,
        reason: str,
    ) -> FailureReason:
        reason_vo = FailureReason(value=reason)
        job.fail(reason_vo)
        return reason_vo

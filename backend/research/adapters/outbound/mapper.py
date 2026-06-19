from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID, uuid4

from backend.research.application.persistence.dto import (
    ResearchJobStorageDTO,
    ResearchOutboxStorageDTO,
    ResearchRequestStorageDTO,
    ResearchSourceStorageDTO,
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

ResearchOutboxDomainEvent = (
    ResearchRequested
    | ResearchStarted
    | ResearchCompleted
    | ResearchFailed
    | ResearchCancelled
    | SourceAdded
    | ResearchSummaryGenerated
)

_EVENT_TYPE_MAP: dict[type, str] = {
    ResearchRequested: "research.requested",
    ResearchStarted: "research.started",
    ResearchCompleted: "research.completed",
    ResearchFailed: "research.failed",
    ResearchCancelled: "research.cancelled",
    SourceAdded: "source.added",
    ResearchSummaryGenerated: "research.summary_generated",
}

_EVENT_TYPE_REVERSE: dict[str, type] = {v: k for k, v in _EVENT_TYPE_MAP.items()}


class ResearchRequestMapperImpl:
    def domain_to_dto(
        self, request: ResearchRequest
    ) -> ResearchRequestStorageDTO:
        return ResearchRequestStorageDTO(
            request_id=str(request.request_id),
            query=str(request.query) if request.query else None,
            goal=str(request.goal) if request.goal else None,
            priority=request.priority.value,
            status=request.status.value,
            failure_reason=str(request.failure_reason)
            if request.failure_reason else None,
            created_at=request.created_at,
            updated_at=request.updated_at,
        )

    def dto_to_domain(
        self, dto: ResearchRequestStorageDTO,
    ) -> ResearchRequest:
        request = ResearchRequest(
            request_id=ResearchRequestId(value=UUID(dto.request_id)),
            query=QueryText(value=dto.query) if dto.query else None,
            goal=ResearchGoal(value=dto.goal) if dto.goal else None,
            priority=ResearchPriority(dto.priority),
            created_at=dto.created_at or datetime.now(),
            updated_at=dto.updated_at,
        )
        object.__setattr__(request, "_status", ResearchStatus(dto.status))
        if dto.failure_reason:
            object.__setattr__(
                request, "_failure_reason",
                FailureReason(value=dto.failure_reason),
            )
        return request


class ResearchJobMapperImpl:
    def domain_to_dto(self, job: ResearchJob) -> ResearchJobStorageDTO:
        return ResearchJobStorageDTO(
            job_id=str(job.job_id),
            request_id=None,
            goal=str(job.goal) if job.goal else None,
            priority=job.priority.value,
            status=job.status.value,
            summary=str(job.summary) if job.summary else None,
            failure_reason=str(job.failure_reason)
            if job.failure_reason else None,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )

    def dto_to_domain(self, dto: ResearchJobStorageDTO) -> ResearchJob:
        return ResearchJob(
            job_id=ResearchJobId(value=UUID(dto.job_id)),
            goal=ResearchGoal(value=dto.goal) if dto.goal else None,
            priority=ResearchPriority(dto.priority),
            status=ResearchStatus(dto.status),
            summary=ResearchSummary(value=dto.summary)
            if dto.summary else None,
            failure_reason=FailureReason(value=dto.failure_reason)
            if dto.failure_reason else None,
            created_at=dto.created_at or datetime.now(),
            completed_at=dto.completed_at,
        )


class ResearchSourceMapperImpl:
    def domain_to_dto(
        self, source: ResearchSource
    ) -> ResearchSourceStorageDTO:
        return ResearchSourceStorageDTO(
            source_id=str(source.source_id),
            job_id=None,
            source_type=source.source_type.value,
            reference=str(source.reference) if source.reference else None,
            confidence_score=float(source.confidence_score)
            if source.confidence_score else None,
        )

    def dto_to_domain(
        self, dto: ResearchSourceStorageDTO
    ) -> ResearchSource:
        return ResearchSource(
            source_id=UUID(dto.source_id),
            source_type=SourceType(dto.source_type),
            reference=SourceReference(value=dto.reference)
            if dto.reference else None,
            confidence_score=ConfidenceScore(value=dto.confidence_score)
            if dto.confidence_score is not None else None,
        )


class ResearchOutboxMapperImpl:
    def event_to_dto(
        self, event: ResearchOutboxDomainEvent
    ) -> ResearchOutboxStorageDTO:
        event_type = _EVENT_TYPE_MAP.get(type(event), "unknown")
        aggregate_id = self._get_aggregate_id(event)
        payload = self._build_payload(event)
        return ResearchOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type=event_type,
            aggregate_id=aggregate_id,
            occurred_at=event.occurred_at,
            payload=json.dumps(payload) if payload else None,
            published=False,
        )

    def dto_to_event(
        self, dto: ResearchOutboxStorageDTO
    ) -> ResearchOutboxDomainEvent:
        event_cls = _EVENT_TYPE_REVERSE.get(dto.event_type)
        if event_cls is None:
            raise ValueError(f"Unknown event_type: {dto.event_type}")
        if isinstance(dto.payload, dict):
            payload = dto.payload
        else:
            payload = json.loads(dto.payload) if dto.payload else {}
        aggregate_uuid = UUID(dto.aggregate_id)
        event_uuid = UUID(dto.event_id)

        if event_cls is ResearchRequested:
            return ResearchRequested(
                event_id=event_uuid,
                request_id=ResearchRequestId(value=aggregate_uuid),
                query=payload.get("query", ""),
                goal=payload.get("goal", ""),
                priority=payload.get("priority", "normal"),
                occurred_at=dto.occurred_at,
            )
        if event_cls is ResearchStarted:
            return ResearchStarted(
                event_id=event_uuid,
                request_id=ResearchRequestId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is ResearchCompleted:
            return ResearchCompleted(
                event_id=event_uuid,
                request_id=ResearchRequestId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is ResearchFailed:
            return ResearchFailed(
                event_id=event_uuid,
                request_id=ResearchRequestId(value=aggregate_uuid),
                failure_reason=payload.get("failure_reason", ""),
                occurred_at=dto.occurred_at,
            )
        if event_cls is ResearchCancelled:
            return ResearchCancelled(
                event_id=event_uuid,
                request_id=ResearchRequestId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is SourceAdded:
            return SourceAdded(
                event_id=event_uuid,
                request_id=ResearchRequestId(value=aggregate_uuid),
                job_id=ResearchJobId(value=UUID(
                    payload.get("job_id", dto.aggregate_id)
                )),
                source_id=UUID(payload.get("source_id", "00000000-0000-0000-0000-000000000000")),
                source_type=payload.get("source_type", "web"),
                reference=payload.get("reference", ""),
                occurred_at=dto.occurred_at,
            )
        if event_cls is ResearchSummaryGenerated:
            return ResearchSummaryGenerated(
                event_id=event_uuid,
                request_id=ResearchRequestId(value=aggregate_uuid),
                job_id=ResearchJobId(value=UUID(
                    payload.get("job_id", dto.aggregate_id)
                )),
                summary=payload.get("summary", ""),
                occurred_at=dto.occurred_at,
            )

        raise ValueError(f"Unsupported event type: {event_cls}")

    @staticmethod
    def _get_aggregate_id(event: ResearchOutboxDomainEvent) -> str:
        return str(event.request_id)

    @staticmethod
    def _build_payload(
        event: ResearchOutboxDomainEvent
    ) -> dict | None:
        if isinstance(event, ResearchRequested):
            return {
                "query": event.query,
                "goal": event.goal,
                "priority": event.priority,
            }
        if isinstance(event, ResearchFailed):
            return {"failure_reason": event.failure_reason}
        if isinstance(event, SourceAdded):
            return {
                "job_id": str(event.job_id),
                "source_id": str(event.source_id),
                "source_type": event.source_type,
                "reference": event.reference,
            }
        if isinstance(event, ResearchSummaryGenerated):
            return {
                "job_id": str(event.job_id),
                "summary": event.summary,
            }
        return None

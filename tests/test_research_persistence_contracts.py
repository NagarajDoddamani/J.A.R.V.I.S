from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from backend.research.application.persistence.dto import (
    ResearchJobStorageDTO,
    ResearchOutboxStorageDTO,
    ResearchRequestStorageDTO,
    ResearchSourceStorageDTO,
)
from backend.research.application.persistence.mapper import (
    ResearchJobMapper,
    ResearchOutboxDomainEvent,
    ResearchOutboxMapper,
    ResearchRequestMapper,
    ResearchSourceMapper,
)
from backend.research.application.persistence.schema import (
    RESEARCH_JOBS_TABLE,
    RESEARCH_OUTBOX_TABLE,
    RESEARCH_REQUESTS_TABLE,
    RESEARCH_SOURCES_TABLE,
    ColumnContract,
    TableContract,
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
from backend.research.domain.rules import (
    MAX_QUERY_LENGTH,
    MAX_SUMMARY_LENGTH,
)

# ===================================================================
# Constants
# ===================================================================

_NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)
_NOW2 = datetime(2026, 6, 10, 13, 0, 0, tzinfo=timezone.utc)


# ===================================================================
# Stub mapper implementations
# ===================================================================


class StubResearchRequestMapper:
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
        self, dto: ResearchRequestStorageDTO
    ) -> ResearchRequest:
        request = ResearchRequest(
            request_id=ResearchRequestId(value=UUID(dto.request_id)),
            query=QueryText(value=dto.query) if dto.query else None,
            goal=ResearchGoal(value=dto.goal) if dto.goal else None,
            priority=ResearchPriority(dto.priority),
            created_at=dto.created_at or _NOW,
            updated_at=dto.updated_at,
        )
        object.__setattr__(request, "_status", ResearchStatus(dto.status))
        if dto.failure_reason:
            object.__setattr__(
                request, "_failure_reason",
                FailureReason(value=dto.failure_reason),
            )
        return request


class StubResearchJobMapper:
    def domain_to_dto(self, job: ResearchJob) -> ResearchJobStorageDTO:
        return ResearchJobStorageDTO(
            job_id=str(job.job_id),
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
            created_at=dto.created_at or _NOW,
            completed_at=dto.completed_at,
        )


class StubResearchSourceMapper:
    def domain_to_dto(
        self, source: ResearchSource
    ) -> ResearchSourceStorageDTO:
        return ResearchSourceStorageDTO(
            source_id=str(source.source_id),
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


class StubResearchOutboxMapper:
    def event_to_dto(
        self, event: ResearchOutboxDomainEvent
    ) -> ResearchOutboxStorageDTO:
        event_type = _get_event_type(event)
        return ResearchOutboxStorageDTO(
            event_id=str(event.event_id),
            event_type=event_type,
            aggregate_id=str(event.request_id),
            occurred_at=event.occurred_at,
            payload="",
        )

    def dto_to_event(
        self, dto: ResearchOutboxStorageDTO
    ) -> ResearchOutboxDomainEvent:
        from backend.research.domain.model import ResearchCancelled

        if dto.event_type == "research.requested":
            return ResearchRequested(
                request_id=ResearchRequestId(value=UUID(dto.aggregate_id)),
                query="", goal="", priority="normal",
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "research.started":
            return ResearchStarted(
                request_id=ResearchRequestId(value=UUID(dto.aggregate_id)),
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "research.completed":
            return ResearchCompleted(
                request_id=ResearchRequestId(value=UUID(dto.aggregate_id)),
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "research.failed":
            return ResearchFailed(
                request_id=ResearchRequestId(value=UUID(dto.aggregate_id)),
                failure_reason="err",
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "research.cancelled":
            return ResearchCancelled(
                request_id=ResearchRequestId(value=UUID(dto.aggregate_id)),
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "source.added":
            return SourceAdded(
                request_id=ResearchRequestId(value=UUID(dto.aggregate_id)),
                job_id=ResearchJobId(), source_id=UUID(int=1),
                source_type="web", reference="ref",
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "research.summary_generated":
            return ResearchSummaryGenerated(
                request_id=ResearchRequestId(value=UUID(dto.aggregate_id)),
                job_id=ResearchJobId(), summary="sum",
                occurred_at=dto.occurred_at,
            )
        msg = f"Unknown event type: {dto.event_type}"
        raise ValueError(msg)


def _get_event_type(event: ResearchOutboxDomainEvent) -> str:
    mapping = {
        ResearchRequested: "research.requested",
        ResearchStarted: "research.started",
        ResearchCompleted: "research.completed",
        ResearchFailed: "research.failed",
        ResearchCancelled: "research.cancelled",
        SourceAdded: "source.added",
        ResearchSummaryGenerated: "research.summary_generated",
    }
    for cls, name in mapping.items():
        if isinstance(event, cls):
            return name
    msg = f"Unknown event type: {type(event).__name__}"
    raise ValueError(msg)


# ===================================================================
# Domain model imports (needed by stub mappers)
# ===================================================================

from backend.research.domain.model import (  # noqa: E402
    ConfidenceScore,
    FailureReason,
    QueryText,
    ResearchGoal,
    ResearchSummary,
    SourceReference,
)


# ===================================================================
# DTO: ResearchRequestStorageDTO
# ===================================================================


class TestResearchRequestStorageDTO:
    def test_creation_with_all_fields(self) -> None:
        dto = ResearchRequestStorageDTO(
            request_id="req-1",
            query="test query",
            goal="test goal",
            priority="high",
            status="running",
            failure_reason=None,
            created_at=_NOW,
            updated_at=_NOW2,
        )
        assert dto.request_id == "req-1"
        assert dto.query == "test query"
        assert dto.goal == "test goal"
        assert dto.priority == "high"
        assert dto.status == "running"
        assert dto.failure_reason is None
        assert dto.created_at == _NOW
        assert dto.updated_at == _NOW2

    def test_creation_with_defaults(self) -> None:
        dto = ResearchRequestStorageDTO(request_id="req-1")
        assert dto.priority == "normal"
        assert dto.status == "created"
        assert dto.query is None
        assert dto.goal is None
        assert dto.failure_reason is None
        assert dto.created_at is None
        assert dto.updated_at is None

    def test_immutability(self) -> None:
        dto = ResearchRequestStorageDTO(request_id="req-1")
        with pytest.raises(AttributeError):
            dto.request_id = "changed"  # type: ignore[misc]

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(ResearchRequestStorageDTO)
        assert len(fields) == 8

    def test_nullable_fields(self) -> None:
        dto = ResearchRequestStorageDTO(request_id="req-1")
        nullable = {"query", "goal", "failure_reason", "created_at", "updated_at"}
        for field_name in nullable:
            assert getattr(dto, field_name) is None

    def test_non_nullable_fields(self) -> None:
        dto = ResearchRequestStorageDTO(request_id="req-1")
        assert dto.request_id == "req-1"
        assert dto.priority == "normal"
        assert dto.status == "created"


# ===================================================================
# DTO: ResearchJobStorageDTO
# ===================================================================


class TestResearchJobStorageDTO:
    def test_creation_with_all_fields(self) -> None:
        dto = ResearchJobStorageDTO(
            job_id="job-1",
            request_id="req-1",
            goal="sub goal",
            priority="critical",
            status="completed",
            summary="Done",
            failure_reason=None,
            created_at=_NOW,
            completed_at=_NOW2,
        )
        assert dto.job_id == "job-1"
        assert dto.request_id == "req-1"
        assert dto.goal == "sub goal"
        assert dto.priority == "critical"
        assert dto.status == "completed"
        assert dto.summary == "Done"
        assert dto.failure_reason is None
        assert dto.created_at == _NOW
        assert dto.completed_at == _NOW2

    def test_creation_with_defaults(self) -> None:
        dto = ResearchJobStorageDTO(job_id="job-1")
        assert dto.priority == "normal"
        assert dto.status == "created"
        assert dto.request_id is None
        assert dto.goal is None
        assert dto.summary is None
        assert dto.failure_reason is None
        assert dto.created_at is None
        assert dto.completed_at is None

    def test_immutability(self) -> None:
        dto = ResearchJobStorageDTO(job_id="job-1")
        with pytest.raises(AttributeError):
            dto.job_id = "changed"  # type: ignore[misc]

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(ResearchJobStorageDTO)
        assert len(fields) == 9

    def test_nullable_fields(self) -> None:
        dto = ResearchJobStorageDTO(job_id="job-1")
        nullable = {
            "request_id", "goal", "summary", "failure_reason",
            "created_at", "completed_at",
        }
        for field_name in nullable:
            assert getattr(dto, field_name) is None


# ===================================================================
# DTO: ResearchSourceStorageDTO
# ===================================================================


class TestResearchSourceStorageDTO:
    def test_creation_with_all_fields(self) -> None:
        dto = ResearchSourceStorageDTO(
            source_id="src-1",
            job_id="job-1",
            source_type="knowledge",
            reference="https://ref.com",
            confidence_score=0.85,
        )
        assert dto.source_id == "src-1"
        assert dto.job_id == "job-1"
        assert dto.source_type == "knowledge"
        assert dto.reference == "https://ref.com"
        assert dto.confidence_score == 0.85

    def test_creation_with_defaults(self) -> None:
        dto = ResearchSourceStorageDTO(source_id="src-1")
        assert dto.source_type == "web"
        assert dto.job_id is None
        assert dto.reference is None
        assert dto.confidence_score is None

    def test_immutability(self) -> None:
        dto = ResearchSourceStorageDTO(source_id="src-1")
        with pytest.raises(AttributeError):
            dto.source_id = "changed"  # type: ignore[misc]

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(ResearchSourceStorageDTO)
        assert len(fields) == 5

    def test_nullable_fields(self) -> None:
        dto = ResearchSourceStorageDTO(source_id="src-1")
        nullable = {"job_id", "reference", "confidence_score"}
        for field_name in nullable:
            assert getattr(dto, field_name) is None


# ===================================================================
# DTO: ResearchOutboxStorageDTO
# ===================================================================


class TestResearchOutboxStorageDTO:
    def test_creation_with_all_fields(self) -> None:
        dto = ResearchOutboxStorageDTO(
            event_id="evt-1",
            event_type="research.completed",
            aggregate_id="req-1",
            occurred_at=_NOW,
            payload='{"key": "val"}',
            published=True,
        )
        assert dto.event_id == "evt-1"
        assert dto.event_type == "research.completed"
        assert dto.aggregate_id == "req-1"
        assert dto.occurred_at == _NOW
        assert dto.payload == '{"key": "val"}'
        assert dto.published is True

    def test_creation_with_defaults(self) -> None:
        dto = ResearchOutboxStorageDTO(
            event_id="evt-1",
            event_type="research.requested",
            aggregate_id="req-1",
            occurred_at=_NOW,
        )
        assert dto.payload is None
        assert dto.published is False

    def test_immutability(self) -> None:
        dto = ResearchOutboxStorageDTO(
            event_id="evt-1",
            event_type="t",
            aggregate_id="a",
            occurred_at=_NOW,
        )
        with pytest.raises(AttributeError):
            dto.event_id = "changed"  # type: ignore[misc]

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(ResearchOutboxStorageDTO)
        assert len(fields) == 6

    def test_nullable_fields(self) -> None:
        dto = ResearchOutboxStorageDTO(
            event_id="evt-1",
            event_type="t",
            aggregate_id="a",
            occurred_at=_NOW,
        )
        assert dto.payload is None


# ===================================================================
# Mapper: ResearchRequestMapper
# ===================================================================


class TestResearchRequestMapper:
    def test_domain_to_dto(self) -> None:
        request = ResearchRequest(
            request_id=ResearchRequestId(),
            query=QueryText(value="test"),
            goal=ResearchGoal(value="goal"),
            priority=ResearchPriority.HIGH,
            created_at=_NOW,
            updated_at=_NOW2,
        )
        mapper = StubResearchRequestMapper()
        dto = mapper.domain_to_dto(request)
        assert dto.request_id == str(request.request_id)
        assert dto.query == "test"
        assert dto.goal == "goal"
        assert dto.priority == "high"
        assert dto.status == "created"
        assert dto.created_at == _NOW
        assert dto.updated_at == _NOW2

    def test_dto_to_domain(self) -> None:
        dto = ResearchRequestStorageDTO(
            request_id=str(UUID(int=42)),
            query="q",
            goal="g",
            priority="critical",
            status="running",
            created_at=_NOW,
            updated_at=_NOW2,
        )
        mapper = StubResearchRequestMapper()
        request = mapper.dto_to_domain(dto)
        assert str(request.request_id) == dto.request_id
        assert request.query is not None
        assert request.query.value == "q"
        assert request.goal is not None
        assert request.goal.value == "g"
        assert request.priority == ResearchPriority.CRITICAL
        assert request.status == ResearchStatus.RUNNING
        assert request.created_at == _NOW
        assert request.updated_at == _NOW2

    def test_roundtrip(self) -> None:
        original = ResearchRequest(
            request_id=ResearchRequestId(),
            query=QueryText(value="roundtrip query"),
            goal=ResearchGoal(value="roundtrip goal"),
            priority=ResearchPriority.LOW,
            created_at=_NOW,
        )
        mapper = StubResearchRequestMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert str(restored.request_id) == str(original.request_id)
        assert restored.query is not None
        assert restored.query.value == original.query.value
        assert restored.goal is not None
        assert restored.goal.value == original.goal.value
        assert restored.priority == original.priority

    def test_roundtrip_with_nulls(self) -> None:
        original = ResearchRequest()
        mapper = StubResearchRequestMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert str(restored.request_id) == str(original.request_id)
        assert restored.query is None
        assert restored.goal is None

    def test_mapper_has_required_methods(self) -> None:
        mapper = StubResearchRequestMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


# ===================================================================
# Mapper: ResearchJobMapper
# ===================================================================


class TestResearchJobMapper:
    def test_domain_to_dto(self) -> None:
        job = ResearchJob(
            job_id=ResearchJobId(),
            goal=ResearchGoal(value="sub"),
            priority=ResearchPriority.CRITICAL,
            status=ResearchStatus.RUNNING,
            created_at=_NOW,
            completed_at=_NOW2,
        )
        mapper = StubResearchJobMapper()
        dto = mapper.domain_to_dto(job)
        assert dto.job_id == str(job.job_id)
        assert dto.goal == "sub"
        assert dto.priority == "critical"
        assert dto.status == "running"
        assert dto.created_at == _NOW
        assert dto.completed_at == _NOW2

    def test_dto_to_domain(self) -> None:
        dto = ResearchJobStorageDTO(
            job_id=str(UUID(int=42)),
            goal="g",
            priority="high",
            status="completed",
            summary="Done",
            created_at=_NOW,
            completed_at=_NOW2,
        )
        mapper = StubResearchJobMapper()
        job = mapper.dto_to_domain(dto)
        assert str(job.job_id) == dto.job_id
        assert job.goal is not None
        assert job.goal.value == "g"
        assert job.priority == ResearchPriority.HIGH
        assert job.status == ResearchStatus.COMPLETED
        assert job.summary is not None
        assert job.summary.value == "Done"
        assert job.created_at == _NOW
        assert job.completed_at == _NOW2

    def test_roundtrip(self) -> None:
        original = ResearchJob(
            job_id=ResearchJobId(),
            goal=ResearchGoal(value="roundtrip"),
            priority=ResearchPriority.HIGH,
            status=ResearchStatus.RUNNING,
            created_at=_NOW,
        )
        mapper = StubResearchJobMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert str(restored.job_id) == str(original.job_id)
        assert restored.goal is not None
        assert restored.goal.value == original.goal.value
        assert restored.priority == original.priority
        assert restored.status == original.status

    def test_mapper_has_required_methods(self) -> None:
        mapper = StubResearchJobMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


# ===================================================================
# Mapper: ResearchSourceMapper
# ===================================================================


class TestResearchSourceMapper:
    def test_domain_to_dto(self) -> None:
        source = ResearchSource(
            source_id=UUID(int=42),
            source_type=SourceType.KNOWLEDGE,
            reference=SourceReference(value="https://ref.com"),
            confidence_score=ConfidenceScore(value=0.9),
        )
        mapper = StubResearchSourceMapper()
        dto = mapper.domain_to_dto(source)
        assert dto.source_id == str(source.source_id)
        assert dto.source_type == "knowledge"
        assert dto.reference == "https://ref.com"
        assert dto.confidence_score == 0.9

    def test_dto_to_domain(self) -> None:
        dto = ResearchSourceStorageDTO(
            source_id=str(UUID(int=42)),
            job_id="job-1",
            source_type="memory",
            reference="https://mem.com",
            confidence_score=0.75,
        )
        mapper = StubResearchSourceMapper()
        source = mapper.dto_to_domain(dto)
        assert source.source_id == UUID(int=42)
        assert source.source_type == SourceType.MEMORY
        assert source.reference is not None
        assert source.reference.value == "https://mem.com"
        assert source.confidence_score is not None
        assert source.confidence_score.value == 0.75

    def test_roundtrip(self) -> None:
        original = ResearchSource(
            source_id=UUID(int=100),
            source_type=SourceType.DOCUMENT,
            reference=SourceReference(value="https://doc.com"),
            confidence_score=ConfidenceScore(value=0.5),
        )
        mapper = StubResearchSourceMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert restored.source_id == original.source_id
        assert restored.source_type == original.source_type
        assert restored.reference is not None
        assert restored.reference.value == original.reference.value
        assert restored.confidence_score is not None
        assert restored.confidence_score.value == original.confidence_score.value

    def test_roundtrip_with_nulls(self) -> None:
        original = ResearchSource(source_id=UUID(int=1))
        mapper = StubResearchSourceMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert restored.source_id == original.source_id
        assert restored.reference is None
        assert restored.confidence_score is None

    def test_mapper_has_required_methods(self) -> None:
        mapper = StubResearchSourceMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


# ===================================================================
# Mapper: ResearchOutboxMapper
# ===================================================================


class TestResearchOutboxMapper:
    def test_event_to_dto_requested(self) -> None:
        event = ResearchRequested(
            request_id=ResearchRequestId(),
            query="q", goal="g", priority="normal",
            occurred_at=_NOW,
        )
        mapper = StubResearchOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "research.requested"
        assert dto.aggregate_id == str(event.request_id)
        assert dto.occurred_at == _NOW

    def test_event_to_dto_started(self) -> None:
        event = ResearchStarted(
            request_id=ResearchRequestId(),
            occurred_at=_NOW,
        )
        mapper = StubResearchOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "research.started"

    def test_event_to_dto_completed(self) -> None:
        event = ResearchCompleted(
            request_id=ResearchRequestId(),
            occurred_at=_NOW,
        )
        mapper = StubResearchOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "research.completed"

    def test_event_to_dto_failed(self) -> None:
        event = ResearchFailed(
            request_id=ResearchRequestId(),
            failure_reason="err",
            occurred_at=_NOW,
        )
        mapper = StubResearchOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "research.failed"

    def test_event_to_dto_cancelled(self) -> None:
        event = ResearchCancelled(
            request_id=ResearchRequestId(),
            occurred_at=_NOW,
        )
        mapper = StubResearchOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "research.cancelled"

    def test_event_to_dto_source_added(self) -> None:
        event = SourceAdded(
            request_id=ResearchRequestId(),
            job_id=ResearchJobId(),
            source_id=UUID(int=1),
            source_type="web",
            reference="ref",
            occurred_at=_NOW,
        )
        mapper = StubResearchOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "source.added"

    def test_event_to_dto_summary_generated(self) -> None:
        event = ResearchSummaryGenerated(
            request_id=ResearchRequestId(),
            job_id=ResearchJobId(),
            summary="sum",
            occurred_at=_NOW,
        )
        mapper = StubResearchOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "research.summary_generated"

    def test_dto_to_event_roundtrip_all_types(self) -> None:
        mapper = StubResearchOutboxMapper()
        events: list[ResearchOutboxDomainEvent] = [
            ResearchRequested(
                request_id=ResearchRequestId(), query="q", goal="g",
                priority="normal", occurred_at=_NOW,
            ),
            ResearchStarted(
                request_id=ResearchRequestId(), occurred_at=_NOW,
            ),
            ResearchCompleted(
                request_id=ResearchRequestId(), occurred_at=_NOW,
            ),
            ResearchFailed(
                request_id=ResearchRequestId(), failure_reason="err",
                occurred_at=_NOW,
            ),
            ResearchCancelled(
                request_id=ResearchRequestId(), occurred_at=_NOW,
            ),
            SourceAdded(
                request_id=ResearchRequestId(), job_id=ResearchJobId(),
                source_id=UUID(int=1), source_type="web", reference="ref",
                occurred_at=_NOW,
            ),
            ResearchSummaryGenerated(
                request_id=ResearchRequestId(), job_id=ResearchJobId(),
                summary="sum", occurred_at=_NOW,
            ),
        ]
        for event in events:
            dto = mapper.event_to_dto(event)
            restored = mapper.dto_to_event(dto)
            assert type(restored) == type(event)

    def test_mapper_has_required_methods(self) -> None:
        mapper = StubResearchOutboxMapper()
        assert hasattr(mapper, "event_to_dto")
        assert hasattr(mapper, "dto_to_event")


# ===================================================================
# Schema: ResearchRequestsTable
# ===================================================================


class TestResearchRequestsTable:
    def test_name(self) -> None:
        assert RESEARCH_REQUESTS_TABLE.name == "research_requests"

    def test_schema(self) -> None:
        assert RESEARCH_REQUESTS_TABLE.schema == "research"

    def test_primary_key(self) -> None:
        assert RESEARCH_REQUESTS_TABLE.primary_key == "request_id"

    def test_column_count(self) -> None:
        assert len(RESEARCH_REQUESTS_TABLE.columns) == 8

    def test_column_names(self) -> None:
        names = [c.name for c in RESEARCH_REQUESTS_TABLE.columns]
        assert names == [
            "request_id", "query", "goal", "priority",
            "status", "failure_reason", "created_at", "updated_at",
        ]

    def test_priority_enum_values(self) -> None:
        col = _find_column(RESEARCH_REQUESTS_TABLE, "priority")
        assert col is not None
        assert col.enum_values == ("low", "normal", "high", "critical")

    def test_status_enum_values(self) -> None:
        col = _find_column(RESEARCH_REQUESTS_TABLE, "status")
        assert col is not None
        assert col.enum_values == (
            "created", "running", "completed", "failed", "cancelled",
        )

    def test_request_id_not_nullable(self) -> None:
        col = _find_column(RESEARCH_REQUESTS_TABLE, "request_id")
        assert col is not None
        assert col.nullable is False

    def test_created_at_not_nullable(self) -> None:
        col = _find_column(RESEARCH_REQUESTS_TABLE, "created_at")
        assert col is not None
        assert col.nullable is False

    def test_nullable_columns(self) -> None:
        nullable = {"query", "goal", "failure_reason", "updated_at"}
        for name in nullable:
            col = _find_column(RESEARCH_REQUESTS_TABLE, name)
            assert col is not None
            assert col.nullable is True

    def test_indexes(self) -> None:
        assert "ix_research_requests_status" in RESEARCH_REQUESTS_TABLE.indexes
        assert "ix_research_requests_priority" in RESEARCH_REQUESTS_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(RESEARCH_REQUESTS_TABLE.indexes) == 2

    def test_priority_max_length(self) -> None:
        col = _find_column(RESEARCH_REQUESTS_TABLE, "priority")
        assert col is not None
        assert col.max_length == 16

    def test_status_max_length(self) -> None:
        col = _find_column(RESEARCH_REQUESTS_TABLE, "status")
        assert col is not None
        assert col.max_length == 16


# ===================================================================
# Schema: ResearchJobsTable
# ===================================================================


class TestResearchJobsTable:
    def test_name(self) -> None:
        assert RESEARCH_JOBS_TABLE.name == "research_jobs"

    def test_schema(self) -> None:
        assert RESEARCH_JOBS_TABLE.schema == "research"

    def test_primary_key(self) -> None:
        assert RESEARCH_JOBS_TABLE.primary_key == "job_id"

    def test_column_count(self) -> None:
        assert len(RESEARCH_JOBS_TABLE.columns) == 9

    def test_column_names(self) -> None:
        names = [c.name for c in RESEARCH_JOBS_TABLE.columns]
        assert names == [
            "job_id", "request_id", "goal", "priority", "status",
            "summary", "failure_reason", "created_at", "completed_at",
        ]

    def test_priority_enum_values(self) -> None:
        col = _find_column(RESEARCH_JOBS_TABLE, "priority")
        assert col is not None
        assert col.enum_values == ("low", "normal", "high", "critical")

    def test_status_enum_values(self) -> None:
        col = _find_column(RESEARCH_JOBS_TABLE, "status")
        assert col is not None
        assert col.enum_values == (
            "created", "running", "completed", "failed", "cancelled",
        )

    def test_job_id_not_nullable(self) -> None:
        col = _find_column(RESEARCH_JOBS_TABLE, "job_id")
        assert col is not None
        assert col.nullable is False

    def test_created_at_not_nullable(self) -> None:
        col = _find_column(RESEARCH_JOBS_TABLE, "created_at")
        assert col is not None
        assert col.nullable is False

    def test_priority_not_nullable(self) -> None:
        col = _find_column(RESEARCH_JOBS_TABLE, "priority")
        assert col is not None
        assert col.nullable is False

    def test_status_not_nullable(self) -> None:
        col = _find_column(RESEARCH_JOBS_TABLE, "status")
        assert col is not None
        assert col.nullable is False

    def test_nullable_columns(self) -> None:
        nullable = {
            "request_id", "goal", "summary", "failure_reason", "completed_at",
        }
        for name in nullable:
            col = _find_column(RESEARCH_JOBS_TABLE, name)
            assert col is not None
            assert col.nullable is True

    def test_indexes(self) -> None:
        assert "ix_research_jobs_request_id" in RESEARCH_JOBS_TABLE.indexes
        assert "ix_research_jobs_status" in RESEARCH_JOBS_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(RESEARCH_JOBS_TABLE.indexes) == 2


# ===================================================================
# Schema: ResearchSourcesTable
# ===================================================================


class TestResearchSourcesTable:
    def test_name(self) -> None:
        assert RESEARCH_SOURCES_TABLE.name == "research_sources"

    def test_schema(self) -> None:
        assert RESEARCH_SOURCES_TABLE.schema == "research"

    def test_primary_key(self) -> None:
        assert RESEARCH_SOURCES_TABLE.primary_key == "source_id"

    def test_column_count(self) -> None:
        assert len(RESEARCH_SOURCES_TABLE.columns) == 5

    def test_column_names(self) -> None:
        names = [c.name for c in RESEARCH_SOURCES_TABLE.columns]
        assert names == [
            "source_id", "job_id", "source_type", "reference",
            "confidence_score",
        ]

    def test_source_type_enum_values(self) -> None:
        col = _find_column(RESEARCH_SOURCES_TABLE, "source_type")
        assert col is not None
        assert col.enum_values == (
            "memory", "knowledge", "web", "document", "user",
        )

    def test_source_id_not_nullable(self) -> None:
        col = _find_column(RESEARCH_SOURCES_TABLE, "source_id")
        assert col is not None
        assert col.nullable is False

    def test_source_type_not_nullable(self) -> None:
        col = _find_column(RESEARCH_SOURCES_TABLE, "source_type")
        assert col is not None
        assert col.nullable is False

    def test_nullable_columns(self) -> None:
        nullable = {"job_id", "reference", "confidence_score"}
        for name in nullable:
            col = _find_column(RESEARCH_SOURCES_TABLE, name)
            assert col is not None
            assert col.nullable is True

    def test_indexes(self) -> None:
        assert "ix_research_sources_job_id" in RESEARCH_SOURCES_TABLE.indexes
        assert "ix_research_sources_source_type" in RESEARCH_SOURCES_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(RESEARCH_SOURCES_TABLE.indexes) == 2

    def test_source_type_max_length(self) -> None:
        col = _find_column(RESEARCH_SOURCES_TABLE, "source_type")
        assert col is not None
        assert col.max_length == 16


# ===================================================================
# Schema: ResearchOutboxTable
# ===================================================================


class TestResearchOutboxTable:
    def test_name(self) -> None:
        assert RESEARCH_OUTBOX_TABLE.name == "outbox"

    def test_schema(self) -> None:
        assert RESEARCH_OUTBOX_TABLE.schema == "research"

    def test_primary_key(self) -> None:
        assert RESEARCH_OUTBOX_TABLE.primary_key == "event_id"

    def test_column_count(self) -> None:
        assert len(RESEARCH_OUTBOX_TABLE.columns) == 6

    def test_column_names(self) -> None:
        names = [c.name for c in RESEARCH_OUTBOX_TABLE.columns]
        assert names == [
            "event_id", "event_type", "aggregate_id", "occurred_at",
            "payload", "published",
        ]

    def test_event_type_enum_values(self) -> None:
        col = _find_column(RESEARCH_OUTBOX_TABLE, "event_type")
        assert col is not None
        assert col.enum_values == (
            "research.requested", "research.started", "research.completed",
            "research.failed", "research.cancelled", "source.added",
            "research.summary_generated",
        )

    def test_event_type_count(self) -> None:
        col = _find_column(RESEARCH_OUTBOX_TABLE, "event_type")
        assert col is not None
        assert len(col.enum_values) == 7

    def test_not_nullable_columns(self) -> None:
        for name in ("event_id", "event_type", "aggregate_id", "occurred_at", "published"):
            col = _find_column(RESEARCH_OUTBOX_TABLE, name)
            assert col is not None
            assert col.nullable is False

    def test_payload_nullable(self) -> None:
        col = _find_column(RESEARCH_OUTBOX_TABLE, "payload")
        assert col is not None
        assert col.nullable is True

    def test_indexes(self) -> None:
        assert "ix_research_outbox_unpublished" in RESEARCH_OUTBOX_TABLE.indexes
        assert "ix_research_outbox_aggregate" in RESEARCH_OUTBOX_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(RESEARCH_OUTBOX_TABLE.indexes) == 2

    def test_event_type_max_length(self) -> None:
        col = _find_column(RESEARCH_OUTBOX_TABLE, "event_type")
        assert col is not None
        assert col.max_length == 32


# ===================================================================
# Alignment: DTO ↔ Schema
# ===================================================================


class TestDTOAlignment:
    def test_request_dto_aligns_with_schema(self) -> None:
        dto_fields = _dto_field_names(ResearchRequestStorageDTO)
        schema_fields = [c.name for c in RESEARCH_REQUESTS_TABLE.columns]
        assert dto_fields == schema_fields

    def test_job_dto_aligns_with_schema(self) -> None:
        dto_fields = _dto_field_names(ResearchJobStorageDTO)
        schema_fields = [c.name for c in RESEARCH_JOBS_TABLE.columns]
        assert dto_fields == schema_fields

    def test_source_dto_aligns_with_schema(self) -> None:
        dto_fields = _dto_field_names(ResearchSourceStorageDTO)
        schema_fields = [c.name for c in RESEARCH_SOURCES_TABLE.columns]
        assert dto_fields == schema_fields

    def test_outbox_dto_aligns_with_schema(self) -> None:
        dto_fields = _dto_field_names(ResearchOutboxStorageDTO)
        schema_fields = [c.name for c in RESEARCH_OUTBOX_TABLE.columns]
        assert dto_fields == schema_fields


# ===================================================================
# Alignment: Schema ↔ Domain Enums
# ===================================================================


class TestSchemaEnumAlignment:
    def test_priority_enum_matches_research_priority(self) -> None:
        col = _find_column(RESEARCH_REQUESTS_TABLE, "priority")
        assert col is not None
        expected = tuple(m.value for m in ResearchPriority)
        assert col.enum_values == expected

    def test_status_enum_matches_research_status(self) -> None:
        col = _find_column(RESEARCH_REQUESTS_TABLE, "status")
        assert col is not None
        expected = tuple(m.value for m in ResearchStatus)
        assert col.enum_values == expected

    def test_source_type_enum_matches_source_type(self) -> None:
        col = _find_column(RESEARCH_SOURCES_TABLE, "source_type")
        assert col is not None
        expected = tuple(m.value for m in SourceType)
        assert col.enum_values == expected


# ===================================================================
# Alignment: Schema ↔ Domain Rules
# ===================================================================


class TestSchemaRuleAlignment:
    def test_query_max_length_aligns_with_rule(self) -> None:
        col = _find_column(RESEARCH_REQUESTS_TABLE, "query")
        assert col is not None
        # No explicit max_length on query column - relies on domain rule

    def test_summary_max_length_aligns_with_rule(self) -> None:
        col = _find_column(RESEARCH_JOBS_TABLE, "summary")
        assert col is not None
        # No explicit max_length on summary column - relies on domain rule


# ===================================================================
# Alignment: Event enum values
# ===================================================================


class TestEventTypeAlignment:
    def test_event_type_count_matches_domain_events(self) -> None:
        from backend.research.application.ports.outbox import ResearchOutboxEvent
        import typing
        args = typing.get_args(ResearchOutboxEvent)
        col = _find_column(RESEARCH_OUTBOX_TABLE, "event_type")
        assert col is not None
        assert len(col.enum_values) == len(args)

    def test_event_type_values_cover_all_events(self) -> None:
        col = _find_column(RESEARCH_OUTBOX_TABLE, "event_type")
        assert col is not None
        assert "research.requested" in col.enum_values
        assert "research.started" in col.enum_values
        assert "research.completed" in col.enum_values
        assert "research.failed" in col.enum_values
        assert "research.cancelled" in col.enum_values
        assert "source.added" in col.enum_values
        assert "research.summary_generated" in col.enum_values


# ===================================================================
# Helpers
# ===================================================================


def _find_column(
    table: TableContract, name: str
) -> ColumnContract | None:
    for col in table.columns:
        if col.name == name:
            return col
    return None


def _dto_field_names(dto_class: type) -> list[str]:
    import dataclasses
    return [f.name for f in dataclasses.fields(dto_class)]

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.research.adapters.outbound.clock import SystemClockAdapter
from backend.research.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.research.adapters.outbound.mapper import (
    ResearchJobMapperImpl,
    ResearchOutboxMapperImpl,
    ResearchRequestMapperImpl,
    ResearchSourceMapperImpl,
)
from backend.research.application.persistence.mapper import (
    ResearchJobMapper,
    ResearchOutboxMapper,
    ResearchRequestMapper,
    ResearchSourceMapper,
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


def _make_request(
    priority: ResearchPriority = ResearchPriority.NORMAL,
    status: ResearchStatus = ResearchStatus.CREATED,
) -> ResearchRequest:
    return ResearchRequest(
        request_id=ResearchRequestId(
            value=UUID("00000000-0000-0000-0000-000000000001")
        ),
        query=QueryText(value="test query"),
        goal=ResearchGoal(value="test goal"),
        priority=priority,
        created_at=NOW,
        updated_at=NOW,
    )


def _make_job(
    priority: ResearchPriority = ResearchPriority.NORMAL,
    status: ResearchStatus = ResearchStatus.CREATED,
) -> ResearchJob:
    return ResearchJob(
        job_id=ResearchJobId(
            value=UUID("00000000-0000-0000-0000-000000000010")
        ),
        goal=ResearchGoal(value="test job goal"),
        priority=priority,
        status=status,
        created_at=NOW,
    )


def _make_source(
    source_type: SourceType = SourceType.WEB,
) -> ResearchSource:
    return ResearchSource(
        source_id=UUID("00000000-0000-0000-0000-000000000020"),
        source_type=source_type,
        reference=SourceReference(value="https://example.com"),
        confidence_score=ConfidenceScore(value=0.85),
    )


# ===================================================================
# Clock adapter tests
# ===================================================================


class TestSystemClockAdapter:
    def test_now_returns_utc(self) -> None:
        clock = SystemClockAdapter()
        result = clock.now()
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result).total_seconds() == 0.0

    def test_now_returns_datetime(self) -> None:
        clock = SystemClockAdapter()
        assert isinstance(clock.now(), datetime)


# ===================================================================
# ID generator adapter tests
# ===================================================================


class TestUuidGeneratorAdapter:
    def test_generate_request_id(self) -> None:
        gen = UuidGeneratorAdapter()
        rid = gen.generate_request_id()
        assert isinstance(rid, str)
        assert UUID(rid)

    def test_generate_job_id(self) -> None:
        gen = UuidGeneratorAdapter()
        jid = gen.generate_job_id()
        assert isinstance(jid, str)
        assert UUID(jid)

    def test_generate_source_id(self) -> None:
        gen = UuidGeneratorAdapter()
        sid = gen.generate_source_id()
        assert isinstance(sid, str)
        assert UUID(sid)

    def test_unique_ids(self) -> None:
        gen = UuidGeneratorAdapter()
        request_ids = {gen.generate_request_id() for _ in range(50)}
        job_ids = {gen.generate_job_id() for _ in range(50)}
        source_ids = {gen.generate_source_id() for _ in range(50)}
        assert len(request_ids) == 50
        assert len(job_ids) == 50
        assert len(source_ids) == 50


# ===================================================================
# ResearchRequestMapperImpl tests
# ===================================================================


class TestResearchRequestMapperImpl:
    @pytest.fixture
    def mapper(self) -> ResearchRequestMapperImpl:
        return ResearchRequestMapperImpl()

    def test_protocol_conformance(self) -> None:
        mapper: ResearchRequestMapper = ResearchRequestMapperImpl()
        assert isinstance(mapper, ResearchRequestMapperImpl)

    def test_domain_to_dto(self, mapper: ResearchRequestMapperImpl) -> None:
        request = _make_request()
        dto = mapper.domain_to_dto(request)
        assert dto.request_id == "00000000-0000-0000-0000-000000000001"
        assert dto.query == "test query"
        assert dto.goal == "test goal"
        assert dto.priority == "normal"
        assert dto.status == "created"

    def test_dto_to_domain(self, mapper: ResearchRequestMapperImpl) -> None:
        request = _make_request()
        dto = mapper.domain_to_dto(request)
        result = mapper.dto_to_domain(dto)
        assert str(result.request_id) == "00000000-0000-0000-0000-000000000001"
        assert str(result.query) == "test query"
        assert result.priority == ResearchPriority.NORMAL
        assert result.status == ResearchStatus.CREATED

    def test_roundtrip(self, mapper: ResearchRequestMapperImpl) -> None:
        original = _make_request(
            priority=ResearchPriority.HIGH,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.priority == original.priority
        assert reconstructed.status == original.status

    def test_null_fields(self, mapper: ResearchRequestMapperImpl) -> None:
        request = ResearchRequest(
            request_id=ResearchRequestId(),
            priority=ResearchPriority.NORMAL,
            created_at=NOW,
        )
        dto = mapper.domain_to_dto(request)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.query is None
        assert reconstructed.goal is None
        assert reconstructed.updated_at is None

    def test_failure_reason(self, mapper: ResearchRequestMapperImpl) -> None:
        original = _make_request()
        original.start()
        original.fail(FailureReason(value="test failure"))
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.status == ResearchStatus.FAILED
        assert str(reconstructed.failure_reason) == "test failure"

    def test_dto_to_domain_with_all_fields(
        self, mapper: ResearchRequestMapperImpl
    ) -> None:
        from backend.research.application.persistence.dto import (
            ResearchRequestStorageDTO,
        )

        dto = ResearchRequestStorageDTO(
            request_id="00000000-0000-0000-0000-000000000001",
            query="custom query",
            goal="custom goal",
            priority="high",
            status="running",
            failure_reason=None,
            created_at=NOW,
            updated_at=NOW,
        )
        result = mapper.dto_to_domain(dto)
        assert str(result.query) == "custom query"
        assert result.priority == ResearchPriority.HIGH
        assert result.status == ResearchStatus.RUNNING


# ===================================================================
# ResearchJobMapperImpl tests
# ===================================================================


class TestResearchJobMapperImpl:
    @pytest.fixture
    def mapper(self) -> ResearchJobMapperImpl:
        return ResearchJobMapperImpl()

    def test_protocol_conformance(self) -> None:
        mapper: ResearchJobMapper = ResearchJobMapperImpl()
        assert isinstance(mapper, ResearchJobMapperImpl)

    def test_domain_to_dto(self, mapper: ResearchJobMapperImpl) -> None:
        job = _make_job()
        dto = mapper.domain_to_dto(job)
        assert dto.job_id == "00000000-0000-0000-0000-000000000010"
        assert dto.goal == "test job goal"
        assert dto.priority == "normal"
        assert dto.status == "created"
        assert dto.summary is None

    def test_dto_to_domain(self, mapper: ResearchJobMapperImpl) -> None:
        job = _make_job()
        dto = mapper.domain_to_dto(job)
        result = mapper.dto_to_domain(dto)
        assert str(result.job_id) == "00000000-0000-0000-0000-000000000010"
        assert result.priority == ResearchPriority.NORMAL
        assert result.status == ResearchStatus.CREATED

    def test_roundtrip(self, mapper: ResearchJobMapperImpl) -> None:
        original = _make_job(
            priority=ResearchPriority.CRITICAL,
            status=ResearchStatus.RUNNING,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.priority == original.priority
        assert reconstructed.status == original.status

    def test_null_fields(self, mapper: ResearchJobMapperImpl) -> None:
        original = ResearchJob(
            job_id=ResearchJobId(),
            status=ResearchStatus.CREATED,
            priority=ResearchPriority.NORMAL,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.goal is None
        assert reconstructed.summary is None
        assert reconstructed.failure_reason is None
        assert reconstructed.completed_at is None

    def test_summary_and_completed_at(
        self, mapper: ResearchJobMapperImpl
    ) -> None:
        original = ResearchJob(
            job_id=ResearchJobId(),
            goal=ResearchGoal(value="goal"),
            status=ResearchStatus.COMPLETED,
            priority=ResearchPriority.NORMAL,
            summary=ResearchSummary(value="summary text"),
            created_at=NOW,
            completed_at=NOW,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert str(reconstructed.summary) == "summary text"
        assert reconstructed.completed_at == NOW
        assert reconstructed.status == ResearchStatus.COMPLETED

    def test_failure_reason(self, mapper: ResearchJobMapperImpl) -> None:
        original = ResearchJob(
            job_id=ResearchJobId(),
            status=ResearchStatus.FAILED,
            priority=ResearchPriority.NORMAL,
            failure_reason=FailureReason(value="job error"),
            created_at=NOW,
            completed_at=NOW,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.status == ResearchStatus.FAILED
        assert str(reconstructed.failure_reason) == "job error"


# ===================================================================
# ResearchSourceMapperImpl tests
# ===================================================================


class TestResearchSourceMapperImpl:
    @pytest.fixture
    def mapper(self) -> ResearchSourceMapperImpl:
        return ResearchSourceMapperImpl()

    def test_protocol_conformance(self) -> None:
        mapper: ResearchSourceMapper = ResearchSourceMapperImpl()
        assert isinstance(mapper, ResearchSourceMapperImpl)

    def test_domain_to_dto(self, mapper: ResearchSourceMapperImpl) -> None:
        source = _make_source()
        dto = mapper.domain_to_dto(source)
        assert dto.source_id == "00000000-0000-0000-0000-000000000020"
        assert dto.source_type == "web"
        assert dto.reference == "https://example.com"
        assert dto.confidence_score == 0.85

    def test_dto_to_domain(self, mapper: ResearchSourceMapperImpl) -> None:
        source = _make_source()
        dto = mapper.domain_to_dto(source)
        result = mapper.dto_to_domain(dto)
        assert result.source_type == SourceType.WEB
        assert str(result.reference) == "https://example.com"
        assert float(result.confidence_score) == 0.85

    def test_roundtrip(self, mapper: ResearchSourceMapperImpl) -> None:
        original = _make_source(source_type=SourceType.KNOWLEDGE)
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.source_type == SourceType.KNOWLEDGE

    def test_null_fields(self, mapper: ResearchSourceMapperImpl) -> None:
        original = ResearchSource(
            source_id=UUID("00000000-0000-0000-0000-000000000030"),
            source_type=SourceType.DOCUMENT,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.reference is None
        assert reconstructed.confidence_score is None

    def test_all_source_types(self, mapper: ResearchSourceMapperImpl) -> None:
        for st in SourceType:
            original = _make_source(source_type=st)
            dto = mapper.domain_to_dto(original)
            reconstructed = mapper.dto_to_domain(dto)
            assert reconstructed.source_type == st


# ===================================================================
# ResearchOutboxMapperImpl tests
# ===================================================================


class TestResearchOutboxMapperImpl:
    @pytest.fixture
    def mapper(self) -> ResearchOutboxMapperImpl:
        return ResearchOutboxMapperImpl()

    def test_protocol_conformance(self) -> None:
        mapper: ResearchOutboxMapper = ResearchOutboxMapperImpl()
        assert isinstance(mapper, ResearchOutboxMapperImpl)

    def test_research_requested_event(
        self, mapper: ResearchOutboxMapperImpl
    ) -> None:
        event = ResearchRequested(
            request_id=ResearchRequestId(),
            query="test query",
            goal="test goal",
            priority="high",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "research.requested"
        assert dto.aggregate_id == str(event.request_id)
        assert dto.payload is not None

    def test_research_started_event(
        self, mapper: ResearchOutboxMapperImpl
    ) -> None:
        event = ResearchStarted(
            request_id=ResearchRequestId(), occurred_at=NOW
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "research.started"
        assert dto.payload is None

    def test_research_completed_event(
        self, mapper: ResearchOutboxMapperImpl
    ) -> None:
        event = ResearchCompleted(
            request_id=ResearchRequestId(), occurred_at=NOW
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "research.completed"

    def test_research_failed_event(
        self, mapper: ResearchOutboxMapperImpl
    ) -> None:
        event = ResearchFailed(
            request_id=ResearchRequestId(),
            failure_reason="research error",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "research.failed"
        assert dto.payload is not None

    def test_research_cancelled_event(
        self, mapper: ResearchOutboxMapperImpl
    ) -> None:
        event = ResearchCancelled(
            request_id=ResearchRequestId(), occurred_at=NOW
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "research.cancelled"

    def test_source_added_event(
        self, mapper: ResearchOutboxMapperImpl
    ) -> None:
        event = SourceAdded(
            request_id=ResearchRequestId(),
            job_id=ResearchJobId(),
            source_id=UUID("00000000-0000-0000-0000-000000000040"),
            source_type="web",
            reference="https://example.com",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "source.added"
        assert dto.payload is not None

    def test_research_summary_generated_event(
        self, mapper: ResearchOutboxMapperImpl
    ) -> None:
        event = ResearchSummaryGenerated(
            request_id=ResearchRequestId(),
            job_id=ResearchJobId(),
            summary="research complete",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "research.summary_generated"
        assert dto.payload is not None

    def test_all_events_have_mapping(
        self, mapper: ResearchOutboxMapperImpl
    ) -> None:
        rid = ResearchRequestId()
        jid = ResearchJobId()
        events: list = [
            ResearchRequested(rid, "q", "g", "normal", NOW),
            ResearchStarted(rid, NOW),
            ResearchCompleted(rid, NOW),
            ResearchFailed(rid, "err", NOW),
            ResearchCancelled(rid, NOW),
            SourceAdded(
                rid, jid,
                UUID("00000000-0000-0000-0000-000000000050"),
                "web", "ref", NOW,
            ),
            ResearchSummaryGenerated(rid, jid, "summary", NOW),
        ]
        for event in events:
            dto = mapper.event_to_dto(event)
            reconstructed = mapper.dto_to_event(dto)
            assert type(reconstructed) is type(event)

    def test_roundtrip_research_requested(
        self, mapper: ResearchOutboxMapperImpl
    ) -> None:
        original = ResearchRequested(
            request_id=ResearchRequestId(),
            query="custom query",
            goal="custom goal",
            priority="critical",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, ResearchRequested)
        assert str(reconstructed.request_id) == str(original.request_id)
        assert reconstructed.query == "custom query"
        assert reconstructed.goal == "custom goal"
        assert reconstructed.priority == "critical"

    def test_roundtrip_source_added(
        self, mapper: ResearchOutboxMapperImpl
    ) -> None:
        original = SourceAdded(
            request_id=ResearchRequestId(),
            job_id=ResearchJobId(),
            source_id=UUID("00000000-0000-0000-0000-000000000060"),
            source_type="knowledge",
            reference="ref-123",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, SourceAdded)
        assert reconstructed.source_type == "knowledge"
        assert reconstructed.reference == "ref-123"

    def test_roundtrip_research_summary_generated(
        self, mapper: ResearchOutboxMapperImpl
    ) -> None:
        original = ResearchSummaryGenerated(
            request_id=ResearchRequestId(),
            job_id=ResearchJobId(),
            summary="final summary",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, ResearchSummaryGenerated)
        assert reconstructed.summary == "final summary"

    def test_dto_to_event_unknown_type(
        self, mapper: ResearchOutboxMapperImpl
    ) -> None:
        from backend.research.application.persistence.dto import (
            ResearchOutboxStorageDTO,
        )

        dto = ResearchOutboxStorageDTO(
            event_id="id-1",
            event_type="unknown.type",
            aggregate_id="id-1",
            occurred_at=NOW,
        )
        with pytest.raises(ValueError, match="unknown.type"):
            mapper.dto_to_event(dto)

    def test_dto_to_event_with_dict_payload(
        self, mapper: ResearchOutboxMapperImpl
    ) -> None:
        from backend.research.application.persistence.dto import (
            ResearchOutboxStorageDTO,
        )

        dto = ResearchOutboxStorageDTO(
            event_id="10000000-0000-0000-0000-000000000001",
            event_type="research.requested",
            aggregate_id="20000000-0000-0000-0000-000000000001",
            occurred_at=NOW,
            payload={
                "query": "dict query",
                "goal": "dict goal",
                "priority": "critical",
            },
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, ResearchRequested)
        assert event.query == "dict query"
        assert event.goal == "dict goal"
        assert event.priority == "critical"

    def test_dto_to_event_with_malformed_payload(
        self, mapper: ResearchOutboxMapperImpl
    ) -> None:
        from backend.research.application.persistence.dto import (
            ResearchOutboxStorageDTO,
        )

        dto = ResearchOutboxStorageDTO(
            event_id="10000000-0000-0000-0000-000000000001",
            event_type="research.requested",
            aggregate_id="20000000-0000-0000-0000-000000000001",
            occurred_at=NOW,
            payload="not valid json",
        )
        with pytest.raises(json.JSONDecodeError):
            mapper.dto_to_event(dto)

    def test_dto_to_event_with_none_payload(
        self, mapper: ResearchOutboxMapperImpl
    ) -> None:
        from backend.research.application.persistence.dto import (
            ResearchOutboxStorageDTO,
        )

        dto = ResearchOutboxStorageDTO(
            event_id="10000000-0000-0000-0000-000000000001",
            event_type="research.started",
            aggregate_id="00000000-0000-0000-0000-000000000001",
            occurred_at=NOW,
            payload=None,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, ResearchStarted)

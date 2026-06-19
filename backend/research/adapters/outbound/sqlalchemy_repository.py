from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.research.adapters.outbound.mapper import (
    ResearchJobMapperImpl,
    ResearchOutboxDomainEvent,
    ResearchOutboxMapperImpl,
    ResearchRequestMapperImpl,
    ResearchSourceMapperImpl,
)
from backend.research.adapters.outbound.models import (
    ResearchJobModel,
    ResearchOutboxModel,
    ResearchRequestModel,
    ResearchSourceModel,
)
from backend.research.application.persistence.dto import (
    ResearchJobStorageDTO,
    ResearchOutboxStorageDTO,
    ResearchRequestStorageDTO,
    ResearchSourceStorageDTO,
)
from backend.research.domain.model import (
    ResearchJob,
    ResearchJobId,
    ResearchPriority,
    ResearchRequest,
    ResearchRequestId,
    ResearchSource,
    ResearchStatus,
    SourceType,
)


class SqlAlchemyResearchRequestRepository:
    def __init__(
        self,
        session: Session,
        mapper: ResearchRequestMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or ResearchRequestMapperImpl()

    def save(self, request: ResearchRequest) -> None:
        dto = self._mapper.domain_to_dto(request)
        existing = self._session.get(ResearchRequestModel, dto.request_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(
        self, request_id: ResearchRequestId
    ) -> ResearchRequest | None:
        model = self._session.get(
            ResearchRequestModel, str(request_id)
        )
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_status(
        self, status: ResearchStatus
    ) -> list[ResearchRequest]:
        stmt = select(ResearchRequestModel).where(
            ResearchRequestModel.status == status.value
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def find_by_priority(
        self, priority: ResearchPriority
    ) -> list[ResearchRequest]:
        stmt = select(ResearchRequestModel).where(
            ResearchRequestModel.priority == priority.value
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def count(self) -> int:
        stmt = select(ResearchRequestModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(dto: ResearchRequestStorageDTO) -> ResearchRequestModel:
        return ResearchRequestModel(
            request_id=dto.request_id,
            query=dto.query,
            goal=dto.goal,
            priority=dto.priority,
            status=dto.status,
            failure_reason=dto.failure_reason,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )

    @staticmethod
    def _model_to_dto(
        model: ResearchRequestModel,
    ) -> ResearchRequestStorageDTO:
        return ResearchRequestStorageDTO(
            request_id=model.request_id,
            query=model.query,
            goal=model.goal,
            priority=model.priority,
            status=model.status,
            failure_reason=model.failure_reason,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _model_update_from_dto(
        model: ResearchRequestModel, dto: ResearchRequestStorageDTO
    ) -> None:
        model.query = dto.query
        model.goal = dto.goal
        model.priority = dto.priority
        model.status = dto.status
        model.failure_reason = dto.failure_reason
        model.created_at = dto.created_at
        model.updated_at = dto.updated_at


class SqlAlchemyResearchJobRepository:
    def __init__(
        self,
        session: Session,
        mapper: ResearchJobMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or ResearchJobMapperImpl()

    def save(self, job: ResearchJob) -> None:
        dto = self._mapper.domain_to_dto(job)
        existing = self._session.get(ResearchJobModel, dto.job_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(self, job_id: ResearchJobId) -> ResearchJob | None:
        model = self._session.get(ResearchJobModel, str(job_id))
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_status(
        self, status: ResearchStatus
    ) -> list[ResearchJob]:
        stmt = select(ResearchJobModel).where(
            ResearchJobModel.status == status.value
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def find_by_request_id(
        self, request_id: ResearchRequestId
    ) -> list[ResearchJob]:
        stmt = select(ResearchJobModel).where(
            ResearchJobModel.request_id == str(request_id)
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def count(self) -> int:
        stmt = select(ResearchJobModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(dto: ResearchJobStorageDTO) -> ResearchJobModel:
        return ResearchJobModel(
            job_id=dto.job_id,
            request_id=dto.request_id,
            goal=dto.goal,
            priority=dto.priority,
            status=dto.status,
            summary=dto.summary,
            failure_reason=dto.failure_reason,
            created_at=dto.created_at,
            completed_at=dto.completed_at,
        )

    @staticmethod
    def _model_to_dto(
        model: ResearchJobModel,
    ) -> ResearchJobStorageDTO:
        return ResearchJobStorageDTO(
            job_id=model.job_id,
            request_id=model.request_id,
            goal=model.goal,
            priority=model.priority,
            status=model.status,
            summary=model.summary,
            failure_reason=model.failure_reason,
            created_at=model.created_at,
            completed_at=model.completed_at,
        )

    @staticmethod
    def _model_update_from_dto(
        model: ResearchJobModel, dto: ResearchJobStorageDTO
    ) -> None:
        model.request_id = dto.request_id
        model.goal = dto.goal
        model.priority = dto.priority
        model.status = dto.status
        model.summary = dto.summary
        model.failure_reason = dto.failure_reason
        model.created_at = dto.created_at
        model.completed_at = dto.completed_at


class SqlAlchemyResearchSourceRepository:
    def __init__(
        self,
        session: Session,
        mapper: ResearchSourceMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or ResearchSourceMapperImpl()

    def save(self, source: ResearchSource) -> None:
        dto = self._mapper.domain_to_dto(source)
        existing = self._session.get(
            ResearchSourceModel, dto.source_id
        )
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(self, source_id: UUID) -> ResearchSource | None:
        model = self._session.get(
            ResearchSourceModel, str(source_id)
        )
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_type(
        self, source_type: SourceType
    ) -> list[ResearchSource]:
        stmt = select(ResearchSourceModel).where(
            ResearchSourceModel.source_type == source_type.value
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def find_by_job_id(
        self, job_id: ResearchJobId
    ) -> list[ResearchSource]:
        stmt = select(ResearchSourceModel).where(
            ResearchSourceModel.job_id == str(job_id)
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def count(self) -> int:
        stmt = select(ResearchSourceModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(
        dto: ResearchSourceStorageDTO,
    ) -> ResearchSourceModel:
        return ResearchSourceModel(
            source_id=dto.source_id,
            job_id=dto.job_id,
            source_type=dto.source_type,
            reference=dto.reference,
            confidence_score=dto.confidence_score,
        )

    @staticmethod
    def _model_to_dto(
        model: ResearchSourceModel,
    ) -> ResearchSourceStorageDTO:
        return ResearchSourceStorageDTO(
            source_id=model.source_id,
            job_id=model.job_id,
            source_type=model.source_type,
            reference=model.reference,
            confidence_score=model.confidence_score,
        )

    @staticmethod
    def _model_update_from_dto(
        model: ResearchSourceModel, dto: ResearchSourceStorageDTO
    ) -> None:
        model.job_id = dto.job_id
        model.source_type = dto.source_type
        model.reference = dto.reference
        model.confidence_score = dto.confidence_score


class SqlAlchemyResearchOutboxAdapter:
    def __init__(
        self,
        session: Session,
        mapper: ResearchOutboxMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or ResearchOutboxMapperImpl()

    def append(self, event: ResearchOutboxDomainEvent) -> None:
        dto = self._mapper.event_to_dto(event)
        model = ResearchOutboxModel(
            message_id=dto.event_id,
            subject=dto.event_type,
            aggregate_id=dto.aggregate_id,
            created_at=dto.occurred_at,
            published_at=None,
            headers='{"event_type":"' + dto.event_type + '"}',
            attempts=0,
            correlation_id=dto.event_id,
            causation_id=None,
            payload=dto.payload,
        )
        self._session.add(model)
        self._session.flush()

    def fetch_unpublished(
        self, limit: int = 100
    ) -> list[ResearchOutboxDomainEvent]:
        stmt = (
            select(ResearchOutboxModel)
            .where(ResearchOutboxModel.published_at.is_(None))
            .order_by(ResearchOutboxModel.created_at.asc())
            .limit(limit)
        )
        models = list(self._session.scalars(stmt))
        return [self._model_to_event(m) for m in models]

    def mark_published(self, event_id: str) -> None:
        stmt = (
            update(ResearchOutboxModel)
            .where(ResearchOutboxModel.message_id == event_id)
            .values(published_at=datetime.now(timezone.utc))
        )
        self._session.execute(stmt)
        self._session.flush()

    def _model_to_event(
        self, model: ResearchOutboxModel
    ) -> ResearchOutboxDomainEvent:
        dto = ResearchOutboxStorageDTO(
            event_id=model.message_id,
            event_type=model.subject,
            aggregate_id=model.aggregate_id,
            occurred_at=model.created_at,
            payload=model.payload,
            published=model.published_at is not None,
        )
        return self._mapper.dto_to_event(dto)

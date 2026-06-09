from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.memory.adapters.outbound.mapper import (
    ConsentMapperImpl,
    MemoryMapperImpl,
    MemoryOutboxDomainEvent,
    MemoryOutboxMapperImpl,
)
from backend.memory.adapters.outbound.models import (
    ConsentModel,
    MemoryModel,
    MemoryOutboxModel,
)
from backend.memory.application.persistence.dto import (
    ConsentStorageDTO,
    MemoryStorageDTO,
)
from backend.memory.domain.model import (
    ConsentId,
    ConsentRecord,
    Memory,
    MemoryCategory,
    MemoryId,
)


class SqlAlchemyMemoryRepository:
    """SQLAlchemy-backed implementation of ``MemoryRepositoryPort``.

    Internally converts between ``MemoryModel`` ORM rows and
    ``MemoryStorageDTO`` (via the mapper), then to/from domain
    ``Memory`` aggregates.
    """

    def __init__(
        self,
        session: Session,
        mapper: MemoryMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or MemoryMapperImpl()

    def save(self, memory: Memory) -> None:
        dto = self._mapper.domain_to_dto(memory)
        existing = self._session.get(MemoryModel, dto.memory_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(self, memory_id: MemoryId) -> Memory | None:
        model = self._session.get(MemoryModel, str(memory_id))
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_consent_id(self, consent_id: ConsentId) -> list[Memory]:
        stmt = select(MemoryModel).where(
            MemoryModel.consent_id == str(consent_id)
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def find_by_category(self, category: MemoryCategory) -> list[Memory]:
        stmt = select(MemoryModel).where(
            MemoryModel.category == category.value
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def find_by_source(
        self, source_type: str, source_id: str | None
    ) -> list[Memory]:
        stmt = select(MemoryModel).where(
            MemoryModel.source_type == source_type
        )
        if source_id is not None:
            stmt = stmt.where(MemoryModel.source_id == source_id)
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def find_deleted(self) -> list[Memory]:
        stmt = select(MemoryModel).where(
            MemoryModel.deleted_at.isnot(None)
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def count(self) -> int:
        stmt = select(MemoryModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(dto: MemoryStorageDTO) -> MemoryModel:
        return MemoryModel(
            memory_id=dto.memory_id,
            consent_id=dto.consent_id,
            content=dto.content,
            category=dto.category,
            source_type=dto.source_type,
            source_id=dto.source_id,
            provenance_actor_id=dto.provenance_actor_id,
            provenance_timestamp=dto.provenance_timestamp,
            classification=dto.classification,
            sensitivity=dto.sensitivity,
            retention_policy=dto.retention_policy,
            retention_status=dto.retention_status,
            revision=dto.revision,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            deleted_at=dto.deleted_at,
        )

    @staticmethod
    def _model_to_dto(model: MemoryModel) -> MemoryStorageDTO:
        return MemoryStorageDTO(
            memory_id=model.memory_id,
            consent_id=model.consent_id,
            content=model.content,
            category=model.category,
            source_type=model.source_type,
            source_id=model.source_id,
            provenance_actor_id=model.provenance_actor_id,
            provenance_timestamp=model.provenance_timestamp,
            classification=model.classification,
            sensitivity=model.sensitivity,
            retention_policy=model.retention_policy,
            retention_status=model.retention_status,
            revision=model.revision,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def _model_update_from_dto(
        model: MemoryModel, dto: MemoryStorageDTO
    ) -> None:
        model.consent_id = dto.consent_id
        model.content = dto.content
        model.category = dto.category
        model.source_type = dto.source_type
        model.source_id = dto.source_id
        model.provenance_actor_id = dto.provenance_actor_id
        model.provenance_timestamp = dto.provenance_timestamp
        model.classification = dto.classification
        model.sensitivity = dto.sensitivity
        model.retention_policy = dto.retention_policy
        model.retention_status = dto.retention_status
        model.revision = dto.revision
        model.created_at = dto.created_at
        model.updated_at = dto.updated_at
        model.deleted_at = dto.deleted_at


class SqlAlchemyConsentRepository:
    """SQLAlchemy-backed implementation of ``ConsentRepositoryPort``."""

    def __init__(
        self,
        session: Session,
        mapper: ConsentMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or ConsentMapperImpl()

    def save(self, consent: ConsentRecord) -> None:
        dto = self._mapper.domain_to_dto(consent)
        existing = self._session.get(ConsentModel, dto.consent_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(self, consent_id: ConsentId) -> ConsentRecord | None:
        model = self._session.get(ConsentModel, str(consent_id))
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_active(self) -> list[ConsentRecord]:
        stmt = select(ConsentModel).where(
            ConsentModel.status == "active"
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def find_expired(self) -> list[ConsentRecord]:
        now = datetime.now(tz=timezone.utc)
        stmt = select(ConsentModel).where(
            ConsentModel.expires_at.isnot(None),
            ConsentModel.expires_at < now,
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def find_revoked(self) -> list[ConsentRecord]:
        stmt = select(ConsentModel).where(
            ConsentModel.status == "revoked"
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def count(self) -> int:
        stmt = select(ConsentModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(dto: ConsentStorageDTO) -> ConsentModel:
        return ConsentModel(
            consent_id=dto.consent_id,
            status=dto.status,
            granted_at=dto.granted_at,
            expires_at=dto.expires_at,
            revoked_at=dto.revoked_at,
            policy_version=dto.policy_version,
        )

    @staticmethod
    def _model_to_dto(model: ConsentModel) -> ConsentStorageDTO:
        return ConsentStorageDTO(
            consent_id=model.consent_id,
            status=model.status,
            granted_at=model.granted_at,
            expires_at=model.expires_at,
            revoked_at=model.revoked_at,
            policy_version=model.policy_version,
        )

    @staticmethod
    def _model_update_from_dto(
        model: ConsentModel, dto: ConsentStorageDTO
    ) -> None:
        model.status = dto.status
        model.granted_at = dto.granted_at
        model.expires_at = dto.expires_at
        model.revoked_at = dto.revoked_at
        model.policy_version = dto.policy_version


class SqlAlchemyMemoryOutboxAdapter:
    """SQLAlchemy-backed implementation of ``MemoryOutboxPort``.

    Stores domain events in the ``memory.outbox`` table. Events are
    FIFO-ordered by ``occurred_at``. The ``published`` flag provides
    at-least-once delivery semantics.
    """

    def __init__(
        self,
        session: Session,
        mapper: MemoryOutboxMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or MemoryOutboxMapperImpl()

    def append(self, event: MemoryOutboxDomainEvent) -> None:
        dto = self._mapper.event_to_dto(event)
        model = MemoryOutboxModel(
            event_id=dto.event_id,
            event_type=dto.event_type,
            aggregate_id=dto.aggregate_id,
            occurred_at=dto.occurred_at,
            correlation_id=dto.correlation_id,
            causation_id=dto.causation_id,
            payload=dto.payload,
            published=False,
        )
        self._session.add(model)
        self._session.flush()

    def fetch_unpublished(self, limit: int = 100) -> list[MemoryOutboxDomainEvent]:
        stmt = (
            select(MemoryOutboxModel)
            .where(MemoryOutboxModel.published == False)  # noqa: E712
            .order_by(MemoryOutboxModel.occurred_at.asc())
            .limit(limit)
        )
        models = list(self._session.scalars(stmt))
        return [self._dto_to_event(m) for m in models]

    def mark_published(self, event_id: str) -> None:
        stmt = (
            update(MemoryOutboxModel)
            .where(MemoryOutboxModel.aggregate_id == event_id)
            .values(published=True)
        )
        self._session.execute(stmt)
        self._session.flush()

    def _dto_to_event(self, model: MemoryOutboxModel) -> MemoryOutboxDomainEvent:
        from backend.memory.application.persistence.dto import (
            MemoryOutboxStorageDTO,
        )
        dto = MemoryOutboxStorageDTO(
            event_id=model.event_id,
            event_type=model.event_type,
            aggregate_id=model.aggregate_id,
            occurred_at=model.occurred_at,
            correlation_id=model.correlation_id,
            causation_id=model.causation_id,
            payload=model.payload,
            published=model.published,
        )
        return self._mapper.dto_to_event(dto)

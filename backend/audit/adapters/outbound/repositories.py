from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.audit.adapters.outbound.mappers import (
    AuditChainHeadMapperImpl,
    AuditEntryMapperImpl,
    AuditOutboxMapperImpl,
)
from backend.audit.adapters.outbound.models import (
    AuditChainHeadModel,
    AuditEntryModel,
    AuditOutboxModel,
)
from backend.audit.domain.model import (
    AuditChainHead,
    AuditEntry,
    AuditEntryId,
    AuditEntryRecorded,
)


class SqlAlchemyAuditEntryRepository:
    """SQLAlchemy-backed implementation of ``AuditEntryRepositoryPort``.

    Internally converts between ``AuditEntryModel`` ORM rows and
    ``AuditEntryStorageDTO`` (via the mapper), then to/from domain
    ``AuditEntry`` aggregates.
    """

    def __init__(
        self,
        session: Session,
        mapper: AuditEntryMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or AuditEntryMapperImpl()

    def save(self, entry: AuditEntry) -> None:
        dto = self._mapper.domain_to_dto(entry)
        model = self._dto_to_model(dto)
        self._session.add(model)
        self._session.flush()

    def find_by_id(self, entry_id: AuditEntryId) -> AuditEntry | None:
        stmt = select(AuditEntryModel).where(
            AuditEntryModel.entry_id == str(entry_id)
        )
        model = self._session.scalar(stmt)
        if model is None:
            return None
        dto = self._model_to_dto(model)
        return self._mapper.dto_to_domain(dto)

    def find_by_chain(
        self,
        chain_name: str,
        *,
        since_index: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        stmt = (
            select(AuditEntryModel)
            .where(AuditEntryModel.chain_name == chain_name)
            .order_by(AuditEntryModel.entry_index.asc())
        )
        if since_index is not None:
            stmt = stmt.where(
                AuditEntryModel.entry_index >= since_index
            )
        stmt = stmt.offset(offset).limit(limit)
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def find_by_correlation_id(
        self, correlation_id: str
    ) -> list[AuditEntry]:
        stmt = (
            select(AuditEntryModel)
            .where(
                AuditEntryModel.correlation_id == correlation_id
            )
            .order_by(AuditEntryModel.occurred_at.asc())
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def count_by_chain(self, chain_name: str) -> int:
        stmt = (
            select(AuditEntryModel)
            .where(AuditEntryModel.chain_name == chain_name)
        )
        return len(list(self._session.scalars(stmt)))

    # -- internal ORM <-> DTO mapping --------------------------------

    @staticmethod
    def _dto_to_model(dto: object) -> AuditEntryModel:
        from backend.audit.application.persistence.dto import (
            AuditEntryStorageDTO,
        )
        d = dto  # type: AuditEntryStorageDTO
        return AuditEntryModel(
            entry_id=d.entry_id,
            chain_name=d.chain_name,
            actor_type=d.actor_type,
            actor_id=d.actor_id,
            action=d.action,
            target_type=d.target_type,
            target_ref=d.target_ref,
            policy_decision=d.policy_decision,
            classification=d.classification,
            correlation_id=d.correlation_id,
            causation_id=d.causation_id,
            result=d.result,
            redacted_reason=d.redacted_reason,
            occurred_at=d.occurred_at,
            previous_hash=d.previous_hash,
            entry_hash=d.entry_hash,
            entry_index=d.entry_index,
        )

    @staticmethod
    def _model_to_dto(model: AuditEntryModel) -> object:
        from backend.audit.application.persistence.dto import (
            AuditEntryStorageDTO,
        )
        return AuditEntryStorageDTO(
            entry_id=model.entry_id,
            chain_name=model.chain_name,
            actor_type=model.actor_type,
            actor_id=model.actor_id,
            action=model.action,
            target_type=model.target_type,
            target_ref=model.target_ref,
            policy_decision=model.policy_decision,
            classification=model.classification,
            correlation_id=model.correlation_id,
            causation_id=model.causation_id,
            result=model.result,
            redacted_reason=model.redacted_reason,
            occurred_at=model.occurred_at,
            previous_hash=model.previous_hash,
            entry_hash=model.entry_hash,
            entry_index=model.entry_index,
        )


class SqlAlchemyAuditChainHeadRepository:
    """SQLAlchemy-backed implementation of ``AuditChainHeadRepositoryPort``."""

    def __init__(
        self,
        session: Session,
        mapper: AuditChainHeadMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or AuditChainHeadMapperImpl()

    def save(self, head: AuditChainHead) -> None:
        dto = self._mapper.domain_to_dto(head)
        model = self._find_model(head.chain_name)
        if model is None:
            model = AuditChainHeadModel(
                chain_name=head.chain_name,
                head_hash=dto.head_hash,
                entries_count=head.entries_count,
            )
            self._session.add(model)
        else:
            model.head_hash = dto.head_hash
            model.entries_count = head.entries_count
            model.updated_at = datetime.now(tz=timezone.utc)
        self._session.flush()

    def find_by_chain(
        self, chain_name: str
    ) -> AuditChainHead | None:
        model = self._find_model(chain_name)
        if model is None:
            return None
        return self._mapper.dto_to_domain(
            self._model_to_dto(model)
        )

    def find_all(self) -> list[AuditChainHead]:
        stmt = select(AuditChainHeadModel).order_by(
            AuditChainHeadModel.chain_name
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def _find_model(
        self, chain_name: str
    ) -> AuditChainHeadModel | None:
        stmt = select(AuditChainHeadModel).where(
            AuditChainHeadModel.chain_name == chain_name
        )
        return self._session.scalar(stmt)

    @staticmethod
    def _model_to_dto(model: AuditChainHeadModel) -> object:
        from backend.audit.application.persistence.dto import (
            AuditChainHeadStorageDTO,
        )
        return AuditChainHeadStorageDTO(
            chain_name=model.chain_name,
            head_hash=model.head_hash,
            entries_count=model.entries_count,
            updated_at=model.updated_at,
        )


class SqlAlchemyAuditOutboxRepository:
    """SQLAlchemy-backed implementation of ``AuditOutboxPort``.

    Stores ``AuditEntryRecorded`` domain events in the generic
    ``audit.outbox`` table. The ``payload`` JSON column holds a
    serialized copy of the event for reliable at-least-once
    delivery.
    """

    def __init__(
        self,
        session: Session,
        mapper: AuditOutboxMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or AuditOutboxMapperImpl()

    def append(self, event: AuditEntryRecorded) -> None:
        model = AuditOutboxModel(
            message_id=str(event.event_id),
            aggregate_id=str(event.entry_id),
            subject=f"jarvis.audit.signal.{event.chain_name}.v1",
            payload={
                "entry_id": str(event.entry_id),
                "chain_name": event.chain_name,
                "action": event.action,
                "actor_type": event.actor_type,
                "actor_id": event.actor_id,
                "correlation_id": event.correlation_id,
                "entry_index": event.entry_index,
                "occurred_at": event.occurred_at.isoformat(),
            },
            headers={},
            correlation_id=event.correlation_id,
        )
        self._session.add(model)
        self._session.flush()

    def mark_published(self, event_id: str) -> None:
        stmt = select(AuditOutboxModel).where(
            AuditOutboxModel.message_id == event_id,
            AuditOutboxModel.published_at.is_(None),
        )
        models = list(self._session.scalars(stmt))
        now = datetime.now(tz=timezone.utc)
        for m in models:
            m.published_at = now
        if models:
            self._session.flush()

    def fetch_unpublished(
        self, limit: int = 50
    ) -> list[AuditEntryRecorded]:
        stmt = (
            select(AuditOutboxModel)
            .where(AuditOutboxModel.published_at.is_(None))
            .order_by(AuditOutboxModel.created_at.asc())
            .limit(limit)
        )
        models = list(self._session.scalars(stmt))
        return [self._model_to_event(m) for m in models]

    @staticmethod
    def _model_to_event(model: AuditOutboxModel) -> AuditEntryRecorded:
        payload = model.payload
        return AuditEntryRecorded(
            event_id=UUID(model.message_id),
            entry_id=AuditEntryId(value=UUID(model.aggregate_id)),
            chain_name=payload["chain_name"],
            action=payload["action"],
            actor_type=payload["actor_type"],
            actor_id=payload.get("actor_id"),
            correlation_id=payload["correlation_id"],
            entry_index=payload["entry_index"],
            occurred_at=datetime.fromisoformat(payload["occurred_at"]),
        )

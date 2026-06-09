from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.notification.adapters.outbound.mapper import (
    NotificationActionMapperImpl,
    NotificationMapperImpl,
    NotificationOutboxDomainEvent,
    NotificationOutboxMapperImpl,
)
from backend.notification.adapters.outbound.models import (
    NotificationActionModel,
    NotificationModel,
    NotificationOutboxModel,
)
from backend.notification.application.persistence.dto import (
    NotificationActionStorageDTO,
    NotificationStorageDTO,
)
from backend.notification.domain.model import (
    ActionId,
    Notification,
    NotificationAction,
    NotificationId,
    NotificationPriority,
    NotificationStatus,
)


class SqlAlchemyNotificationRepository:
    """SQLAlchemy-backed implementation of ``NotificationRepositoryPort``.

    Internally converts between ``NotificationModel`` ORM rows and
    ``NotificationStorageDTO`` (via the mapper), then to/from domain
    ``Notification`` aggregates.
    """

    def __init__(
        self,
        session: Session,
        mapper: NotificationMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or NotificationMapperImpl()

    def save(self, notification: Notification) -> None:
        dto = self._mapper.domain_to_dto(notification)
        existing = self._session.get(NotificationModel, dto.notification_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(self, notification_id: NotificationId) -> Notification | None:
        model = self._session.get(NotificationModel, str(notification_id))
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_status(self, status: NotificationStatus) -> list[Notification]:
        stmt = select(NotificationModel).where(
            NotificationModel.status == status.value
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def find_by_priority(
        self, priority: NotificationPriority
    ) -> list[Notification]:
        stmt = select(NotificationModel).where(
            NotificationModel.priority == priority.value
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def find_by_target(
        self, target_type: str, target_id: str
    ) -> list[Notification]:
        stmt = (
            select(NotificationModel)
            .where(NotificationModel.target_type == target_type)
            .where(NotificationModel.target_id == target_id)
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def find_expired(self) -> list[Notification]:
        now = datetime.now(tz=timezone.utc)
        stmt = select(NotificationModel).where(
            (NotificationModel.status == "expired")
            | (
                NotificationModel.expires_at.isnot(None)
                & (NotificationModel.expires_at < now)
            )
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def count(self) -> int:
        stmt = select(NotificationModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(dto: NotificationStorageDTO) -> NotificationModel:
        return NotificationModel(
            notification_id=dto.notification_id,
            title=dto.title,
            message=dto.message,
            priority=dto.priority,
            channel=dto.channel,
            target_type=dto.target_type,
            target_id=dto.target_id,
            status=dto.status,
            created_at=dto.created_at,
            shown_at=dto.shown_at,
            acknowledged_at=dto.acknowledged_at,
            dismissed_at=dto.dismissed_at,
            expires_at=dto.expires_at,
        )

    @staticmethod
    def _model_to_dto(model: NotificationModel) -> NotificationStorageDTO:
        return NotificationStorageDTO(
            notification_id=model.notification_id,
            title=model.title,
            message=model.message,
            priority=model.priority,
            channel=model.channel,
            target_type=model.target_type,
            target_id=model.target_id,
            status=model.status,
            created_at=model.created_at,
            shown_at=model.shown_at,
            acknowledged_at=model.acknowledged_at,
            dismissed_at=model.dismissed_at,
            expires_at=model.expires_at,
        )

    @staticmethod
    def _model_update_from_dto(
        model: NotificationModel, dto: NotificationStorageDTO
    ) -> None:
        model.title = dto.title
        model.message = dto.message
        model.priority = dto.priority
        model.channel = dto.channel
        model.target_type = dto.target_type
        model.target_id = dto.target_id
        model.status = dto.status
        model.created_at = dto.created_at
        model.shown_at = dto.shown_at
        model.acknowledged_at = dto.acknowledged_at
        model.dismissed_at = dto.dismissed_at
        model.expires_at = dto.expires_at


class SqlAlchemyNotificationActionRepository:
    """SQLAlchemy-backed implementation of ``NotificationActionRepositoryPort``."""

    def __init__(
        self,
        session: Session,
        mapper: NotificationActionMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or NotificationActionMapperImpl()

    def save(self, action: NotificationAction) -> None:
        dto = self._mapper.domain_to_dto(action)
        existing = self._session.get(NotificationActionModel, dto.action_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(self, action_id: ActionId) -> NotificationAction | None:
        model = self._session.get(NotificationActionModel, str(action_id))
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_notification_id(
        self, notification_id: NotificationId
    ) -> list[NotificationAction]:
        stmt = select(NotificationActionModel).where(
            NotificationActionModel.notification_id == str(notification_id)
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def count(self) -> int:
        stmt = select(NotificationActionModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(dto: NotificationActionStorageDTO) -> NotificationActionModel:
        return NotificationActionModel(
            action_id=dto.action_id,
            notification_id=dto.notification_id,
            label=dto.label,
            callback_name=dto.callback_name,
            created_at=dto.created_at,
        )

    @staticmethod
    def _model_to_dto(
        model: NotificationActionModel,
    ) -> NotificationActionStorageDTO:
        return NotificationActionStorageDTO(
            action_id=model.action_id,
            notification_id=model.notification_id,
            label=model.label,
            callback_name=model.callback_name,
            created_at=model.created_at,
        )

    @staticmethod
    def _model_update_from_dto(
        model: NotificationActionModel, dto: NotificationActionStorageDTO
    ) -> None:
        model.notification_id = dto.notification_id
        model.label = dto.label
        model.callback_name = dto.callback_name
        model.created_at = dto.created_at


class SqlAlchemyNotificationOutboxAdapter:
    """SQLAlchemy-backed implementation of ``NotificationOutboxPort``.

    Stores domain events in the ``notification.outbox`` table. Events are
    FIFO-ordered by ``occurred_at``. The ``published`` flag provides
    at-least-once delivery semantics.
    """

    def __init__(
        self,
        session: Session,
        mapper: NotificationOutboxMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or NotificationOutboxMapperImpl()

    def append(self, event: NotificationOutboxDomainEvent) -> None:
        dto = self._mapper.event_to_dto(event)
        model = NotificationOutboxModel(
            event_id=dto.event_id,
            event_type=dto.event_type,
            aggregate_id=dto.aggregate_id,
            occurred_at=dto.occurred_at,
            payload=dto.payload,
            published=False,
        )
        self._session.add(model)
        self._session.flush()

    def fetch_unpublished(
        self, limit: int = 100
    ) -> list[NotificationOutboxDomainEvent]:
        stmt = (
            select(NotificationOutboxModel)
            .where(NotificationOutboxModel.published == False)  # noqa: E712
            .order_by(NotificationOutboxModel.occurred_at.asc())
            .limit(limit)
        )
        models = list(self._session.scalars(stmt))
        return [self._dto_to_event(m) for m in models]

    def mark_published(self, notification_id: str) -> None:
        stmt = (
            update(NotificationOutboxModel)
            .where(NotificationOutboxModel.aggregate_id == notification_id)
            .values(published=True)
        )
        self._session.execute(stmt)
        self._session.flush()

    def _dto_to_event(
        self, model: NotificationOutboxModel
    ) -> NotificationOutboxDomainEvent:
        from backend.notification.application.persistence.dto import (
            NotificationOutboxStorageDTO,
        )
        dto = NotificationOutboxStorageDTO(
            event_id=model.event_id,
            event_type=model.event_type,
            aggregate_id=model.aggregate_id,
            occurred_at=model.occurred_at,
            payload=model.payload,
            published=model.published,
        )
        return self._mapper.dto_to_event(dto)

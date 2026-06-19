from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID, uuid4

from backend.notification.application.persistence.dto import (
    NotificationActionStorageDTO,
    NotificationOutboxStorageDTO,
    NotificationStorageDTO,
)
from backend.notification.domain.model import (
    ActionId,
    Notification,
    NotificationAcknowledged,
    NotificationAction,
    NotificationActionInvoked,
    NotificationChannel,
    NotificationCreated,
    NotificationDismissed,
    NotificationExpired,
    NotificationId,
    NotificationMessage,
    NotificationPriority,
    NotificationShown,
    NotificationStatus,
    NotificationTarget,
    NotificationTitle,
)

NotificationOutboxDomainEvent = (
    NotificationCreated
    | NotificationShown
    | NotificationAcknowledged
    | NotificationDismissed
    | NotificationExpired
    | NotificationActionInvoked
)

_EVENT_TYPE_MAP: dict[type, str] = {
    NotificationCreated: "notification.created",
    NotificationShown: "notification.shown",
    NotificationAcknowledged: "notification.acknowledged",
    NotificationDismissed: "notification.dismissed",
    NotificationExpired: "notification.expired",
    NotificationActionInvoked: "notification.action.invoked",
}

_EVENT_TYPE_REVERSE: dict[str, type] = {v: k for k, v in _EVENT_TYPE_MAP.items()}


class NotificationMapperImpl:
    """Concrete implementation of the ``NotificationMapper`` protocol.

    Flattens ``Notification`` value objects into a ``NotificationStorageDTO``
    and reconstructs them on the reverse path. The mapping is lossless
    for all DTO-representable fields.
    """

    def domain_to_dto(self, notification: Notification) -> NotificationStorageDTO:
        return NotificationStorageDTO(
            notification_id=str(notification.notification_id),
            title=str(notification.title) if notification.title else "",
            message=str(notification.message) if notification.message else "",
            priority=notification.priority.value,
            channel=notification.channel.value,
            target_type=notification.target.target_type if notification.target else "",
            target_id=notification.target.target_id if notification.target else "",
            status=notification.status.value,
            created_at=notification.created_at,
            shown_at=notification.shown_at,
            acknowledged_at=notification.acknowledged_at,
            dismissed_at=notification.dismissed_at,
            expires_at=notification.expires_at,
        )

    def dto_to_domain(self, dto: NotificationStorageDTO) -> Notification:
        return Notification(
            notification_id=NotificationId(value=UUID(dto.notification_id)),
            title=NotificationTitle(value=dto.title) if dto.title else None,
            message=NotificationMessage(value=dto.message) if dto.message else None,
            priority=NotificationPriority(dto.priority),
            channel=NotificationChannel(dto.channel),
            target=NotificationTarget(
                target_type=dto.target_type,
                target_id=dto.target_id,
            ) if dto.target_type and dto.target_id else None,
            status=NotificationStatus(dto.status),
            created_at=dto.created_at,
            shown_at=dto.shown_at,
            acknowledged_at=dto.acknowledged_at,
            dismissed_at=dto.dismissed_at,
            expires_at=dto.expires_at,
        )


class NotificationActionMapperImpl:
    """Concrete implementation of the ``NotificationActionMapper`` protocol.

    Flattens ``NotificationAction`` into ``NotificationActionStorageDTO``
    and reconstructs it on the reverse path. The mapping is lossless.
    """

    def domain_to_dto(
        self, action: NotificationAction
    ) -> NotificationActionStorageDTO:
        return NotificationActionStorageDTO(
            action_id=str(action.action_id),
            notification_id=str(action.notification_id) if action.notification_id else "",
            label=action.label,
            callback_name=action.callback_name,
            created_at=action.created_at,
        )

    def dto_to_domain(
        self, dto: NotificationActionStorageDTO
    ) -> NotificationAction:
        return NotificationAction(
            action_id=ActionId(value=UUID(dto.action_id)),
            notification_id=NotificationId(value=UUID(dto.notification_id))
            if dto.notification_id
            else None,
            label=dto.label,
            callback_name=dto.callback_name,
            created_at=dto.created_at,
        )


class NotificationOutboxMapperImpl:
    """Concrete implementation of the ``NotificationOutboxMapper`` protocol.

    Converts notification domain events into ``NotificationOutboxStorageDTO``
    and reconstructs them on the reverse path. Event-specific fields are
    serialised into the ``payload`` JSON string.
    """

    def event_to_dto(
        self, event: NotificationOutboxDomainEvent
    ) -> NotificationOutboxStorageDTO:
        event_type = _EVENT_TYPE_MAP.get(type(event), "unknown")
        aggregate_id = self._get_aggregate_id(event)
        payload = self._build_payload(event)
        return NotificationOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type=event_type,
            aggregate_id=aggregate_id,
            occurred_at=event.occurred_at,
            payload=json.dumps(payload) if payload else None,
            published=False,
        )

    def dto_to_event(
        self, dto: NotificationOutboxStorageDTO
    ) -> NotificationOutboxDomainEvent:
        event_cls = _EVENT_TYPE_REVERSE.get(dto.event_type)
        if event_cls is None:
            raise ValueError(f"Unknown event_type: {dto.event_type}")
        payload = json.loads(dto.payload) if dto.payload else {}
        aggregate_uuid = UUID(dto.aggregate_id)
        event_uuid = UUID(dto.event_id)

        if event_cls is NotificationCreated:

            def _str(v: object) -> str:
                if isinstance(v, str):
                    return v
                return str(v) if v is not None else ""

            return NotificationCreated(
                event_id=event_uuid,
                notification_id=NotificationId(value=aggregate_uuid),
                title=_str(payload.get("title", "")),
                message=_str(payload.get("message", "")),
                priority=_str(payload.get("priority", "normal")),
                channel=_str(payload.get("channel", "in_app")),
                target_type=_str(payload.get("target_type", "")),
                target_id=_str(payload.get("target_id", "")),
                occurred_at=dto.occurred_at,
            )
        if event_cls is NotificationShown:
            return NotificationShown(
                event_id=event_uuid,
                notification_id=NotificationId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is NotificationAcknowledged:
            return NotificationAcknowledged(
                event_id=event_uuid,
                notification_id=NotificationId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is NotificationDismissed:
            return NotificationDismissed(
                event_id=event_uuid,
                notification_id=NotificationId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is NotificationExpired:
            return NotificationExpired(
                event_id=event_uuid,
                notification_id=NotificationId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is NotificationActionInvoked:
            return NotificationActionInvoked(
                event_id=event_uuid,
                notification_id=NotificationId(value=UUID(payload.get("notification_id", dto.aggregate_id))),
                action_id=ActionId(value=aggregate_uuid),
                callback_name=payload.get("callback_name", ""),
                occurred_at=dto.occurred_at,
            )

        raise ValueError(f"Unsupported event type: {event_cls}")

    @staticmethod
    def _get_aggregate_id(event: NotificationOutboxDomainEvent) -> str:
        if isinstance(event, NotificationActionInvoked):
            return str(event.action_id)
        return str(event.notification_id)

    @staticmethod
    def _build_payload(event: NotificationOutboxDomainEvent) -> dict | None:
        if isinstance(event, NotificationCreated):
            return {
                "title": event.title,
                "message": event.message,
                "priority": event.priority,
                "channel": event.channel,
                "target_type": event.target_type,
                "target_id": event.target_id,
            }
        if isinstance(event, NotificationActionInvoked):
            return {
                "notification_id": str(event.notification_id),
                "callback_name": event.callback_name,
            }
        return None

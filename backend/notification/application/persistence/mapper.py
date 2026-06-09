from __future__ import annotations

from typing import Protocol, Union

from backend.notification.application.persistence.dto import (
    NotificationActionStorageDTO,
    NotificationOutboxStorageDTO,
    NotificationStorageDTO,
)
from backend.notification.domain.model import (
    Notification,
    NotificationAcknowledged,
    NotificationAction,
    NotificationActionInvoked,
    NotificationCreated,
    NotificationDismissed,
    NotificationExpired,
    NotificationShown,
)

NotificationOutboxDomainEvent = Union[
    NotificationCreated,
    NotificationShown,
    NotificationAcknowledged,
    NotificationDismissed,
    NotificationExpired,
    NotificationActionInvoked,
]


class NotificationMapper(Protocol):
    def domain_to_dto(self, notification: Notification) -> NotificationStorageDTO:
        ...

    def dto_to_domain(self, dto: NotificationStorageDTO) -> Notification:
        ...


class NotificationActionMapper(Protocol):
    def domain_to_dto(self, action: NotificationAction) -> NotificationActionStorageDTO:
        ...

    def dto_to_domain(self, dto: NotificationActionStorageDTO) -> NotificationAction:
        ...


class NotificationOutboxMapper(Protocol):
    def event_to_dto(self, event: NotificationOutboxDomainEvent) -> NotificationOutboxStorageDTO:
        ...

    def dto_to_event(self, dto: NotificationOutboxStorageDTO) -> NotificationOutboxDomainEvent:
        ...

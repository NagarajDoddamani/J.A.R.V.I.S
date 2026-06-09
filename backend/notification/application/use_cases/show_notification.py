from __future__ import annotations

from uuid import UUID

from backend.notification.application.ports.outbox import NotificationOutboxPort
from backend.notification.application.ports.repository import (
    NotificationRepositoryPort,
)
from backend.notification.application.use_cases.dto import (
    ShowNotificationRequest,
    ShowNotificationResponse,
)
from backend.notification.application.use_cases.exceptions import (
    NotificationNotFoundError,
)
from backend.notification.domain.factory import NotificationFactory
from backend.notification.domain.model import NotificationId


class ShowNotificationUseCase:
    def __init__(
        self,
        notification_repo: NotificationRepositoryPort,
        outbox: NotificationOutboxPort,
    ) -> None:
        self._notification_repo = notification_repo
        self._outbox = outbox

    def execute(self, request: ShowNotificationRequest) -> ShowNotificationResponse:
        notification_id = NotificationId(value=UUID(request.notification_id))
        notification = self._notification_repo.find_by_id(notification_id)
        if notification is None:
            raise NotificationNotFoundError(request.notification_id)

        event = NotificationFactory.show_notification(notification)
        self._notification_repo.save(notification)
        self._outbox.append(event)

        return ShowNotificationResponse(
            notification_id=str(notification.notification_id),
            status=notification.status.value,
            shown_at=notification.shown_at,
        )

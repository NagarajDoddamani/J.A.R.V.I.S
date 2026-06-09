from __future__ import annotations

from uuid import UUID

from backend.notification.application.ports.repository import (
    NotificationRepositoryPort,
)
from backend.notification.application.use_cases.dto import (
    GetNotificationRequest,
    NotificationResponse,
)
from backend.notification.application.use_cases.exceptions import (
    NotificationNotFoundError,
)
from backend.notification.domain.model import NotificationId


class GetNotificationUseCase:
    def __init__(
        self,
        notification_repo: NotificationRepositoryPort,
    ) -> None:
        self._notification_repo = notification_repo

    def execute(self, request: GetNotificationRequest) -> NotificationResponse:
        notification_id = NotificationId(value=UUID(request.notification_id))
        notification = self._notification_repo.find_by_id(notification_id)
        if notification is None:
            raise NotificationNotFoundError(request.notification_id)

        return NotificationResponse(
            notification_id=str(notification.notification_id),
            title=str(notification.title) if notification.title else None,
            message=str(notification.message) if notification.message else None,
            priority=notification.priority.value,
            channel=notification.channel.value,
            target_type=notification.target.target_type if notification.target else None,
            target_id=notification.target.target_id if notification.target else None,
            status=notification.status.value,
            created_at=notification.created_at,
            shown_at=notification.shown_at,
            acknowledged_at=notification.acknowledged_at,
            dismissed_at=notification.dismissed_at,
            expires_at=notification.expires_at,
        )

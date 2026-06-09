from __future__ import annotations

from datetime import datetime, timezone

from backend.notification.application.ports.outbox import NotificationOutboxPort
from backend.notification.application.ports.repository import (
    NotificationRepositoryPort,
)
from backend.notification.application.use_cases.dto import (
    CreateNotificationRequest,
    CreateNotificationResponse,
)
from backend.notification.domain.factory import NotificationFactory
from backend.notification.domain.model import (
    ExpirationPolicy,
    NotificationTarget,
)


class CreateNotificationUseCase:
    def __init__(
        self,
        notification_repo: NotificationRepositoryPort,
        outbox: NotificationOutboxPort,
    ) -> None:
        self._notification_repo = notification_repo
        self._outbox = outbox

    def execute(self, request: CreateNotificationRequest) -> CreateNotificationResponse:
        target = NotificationTarget(
            target_type=request.target_type,
            target_id=request.target_id,
        )
        expiration = None
        if request.expires_at is not None:
            if request.expires_at.tzinfo is None:
                request.expires_at = request.expires_at.replace(tzinfo=timezone.utc)
            expiration = ExpirationPolicy(expires_at=request.expires_at)

        notification, event = NotificationFactory.create_notification(
            title=request.title,
            message=request.message,
            priority=request.priority,
            channel=request.channel,
            target=target,
            expiration_policy=expiration,
        )
        self._notification_repo.save(notification)
        self._outbox.append(event)

        return CreateNotificationResponse(
            notification_id=str(notification.notification_id),
            title=str(notification.title) if notification.title else None,
            message=str(notification.message) if notification.message else None,
            priority=notification.priority.value,
            channel=notification.channel.value,
            target_type=notification.target.target_type if notification.target else None,
            target_id=notification.target.target_id if notification.target else None,
            status=notification.status.value,
            created_at=notification.created_at,
            expires_at=notification.expires_at,
        )

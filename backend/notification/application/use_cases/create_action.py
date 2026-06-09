from __future__ import annotations

from uuid import UUID

from backend.notification.application.ports.repository import (
    NotificationActionRepositoryPort,
    NotificationRepositoryPort,
)
from backend.notification.application.use_cases.dto import (
    CreateActionRequest,
    CreateActionResponse,
)
from backend.notification.application.use_cases.exceptions import (
    NotificationNotFoundError,
)
from backend.notification.domain.factory import NotificationFactory
from backend.notification.domain.model import NotificationId


class CreateActionUseCase:
    def __init__(
        self,
        notification_repo: NotificationRepositoryPort,
        action_repo: NotificationActionRepositoryPort,
    ) -> None:
        self._notification_repo = notification_repo
        self._action_repo = action_repo

    def execute(self, request: CreateActionRequest) -> CreateActionResponse:
        notification_id = NotificationId(value=UUID(request.notification_id))
        notification = self._notification_repo.find_by_id(notification_id)
        if notification is None:
            raise NotificationNotFoundError(request.notification_id)

        action = NotificationFactory.create_action(
            notification=notification,
            label=request.label,
            callback_name=request.callback_name,
        )
        self._action_repo.save(action)

        return CreateActionResponse(
            action_id=str(action.action_id),
            notification_id=str(action.notification_id) if action.notification_id else None,
            label=action.label,
            callback_name=action.callback_name,
            created_at=action.created_at,
        )

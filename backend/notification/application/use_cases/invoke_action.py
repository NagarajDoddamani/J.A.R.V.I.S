from __future__ import annotations

from uuid import UUID

from backend.notification.application.ports.outbox import NotificationOutboxPort
from backend.notification.application.ports.repository import (
    NotificationActionRepositoryPort,
    NotificationRepositoryPort,
)
from backend.notification.application.use_cases.dto import (
    InvokeActionRequest,
    InvokeActionResponse,
)
from backend.notification.application.use_cases.exceptions import (
    NotificationActionNotFoundError,
)
from backend.notification.domain.factory import NotificationFactory
from backend.notification.domain.model import ActionId, NotificationId


class InvokeActionUseCase:
    def __init__(
        self,
        action_repo: NotificationActionRepositoryPort,
        notification_repo: NotificationRepositoryPort,
        outbox: NotificationOutboxPort,
    ) -> None:
        self._action_repo = action_repo
        self._notification_repo = notification_repo
        self._outbox = outbox

    def execute(self, request: InvokeActionRequest) -> InvokeActionResponse:
        action_id = ActionId(value=UUID(request.action_id))
        action = self._action_repo.find_by_id(action_id)
        if action is None:
            raise NotificationActionNotFoundError(request.action_id)

        notification_id = action.notification_id
        if notification_id is None:
            raise NotificationActionNotFoundError(request.action_id)
        notification = self._notification_repo.find_by_id(notification_id)
        if notification is None:
            raise NotificationActionNotFoundError(request.action_id)

        event = NotificationFactory.invoke_action(
            notification=notification,
            action=action,
        )
        self._action_repo.save(action)
        self._notification_repo.save(notification)
        self._outbox.append(event)

        return InvokeActionResponse(
            action_id=str(action.action_id),
            notification_id=str(action.notification_id) if action.notification_id else None,
            callback_name=action.callback_name,
            occurred_at=event.occurred_at,
        )

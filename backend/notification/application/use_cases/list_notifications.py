from __future__ import annotations

from backend.notification.application.ports.repository import (
    NotificationRepositoryPort,
)
from backend.notification.application.use_cases.dto import (
    ListNotificationsRequest,
    ListNotificationsResponse,
    NotificationResponse,
)
from backend.notification.domain.model import NotificationPriority, NotificationStatus


class ListNotificationsUseCase:
    def __init__(
        self,
        notification_repo: NotificationRepositoryPort,
    ) -> None:
        self._notification_repo = notification_repo

    def execute(
        self, request: ListNotificationsRequest
    ) -> ListNotificationsResponse:
        results: list | None = None

        if request.status is not None:
            results = self._notification_repo.find_by_status(
                NotificationStatus(request.status)
            )

        if request.priority is not None:
            priority_results = self._notification_repo.find_by_priority(
                NotificationPriority(request.priority)
            )
            if results is not None:
                result_ids = {n.notification_id.value for n in results}
                results = [n for n in priority_results if n.notification_id.value in result_ids]
            else:
                results = priority_results

        if request.target_type is not None or request.target_id is not None:
            target_type = request.target_type or ""
            target_id = request.target_id or ""
            target_results = self._notification_repo.find_by_target(
                target_type, target_id
            )
            if results is not None:
                result_ids = {n.notification_id.value for n in results}
                results = [n for n in target_results if n.notification_id.value in result_ids]
            else:
                results = target_results

        if results is None:
            total = self._notification_repo.count()
            if total == 0:
                return ListNotificationsResponse(notifications=[], total=0)
            results = []
            for status in NotificationStatus:
                results.extend(self._notification_repo.find_by_status(status))

        notifications = [
            NotificationResponse(
                notification_id=str(n.notification_id),
                title=str(n.title) if n.title else None,
                message=str(n.message) if n.message else None,
                priority=n.priority.value,
                channel=n.channel.value,
                target_type=n.target.target_type if n.target else None,
                target_id=n.target.target_id if n.target else None,
                status=n.status.value,
                created_at=n.created_at,
                shown_at=n.shown_at,
                acknowledged_at=n.acknowledged_at,
                dismissed_at=n.dismissed_at,
                expires_at=n.expires_at,
            )
            for n in results
        ]

        return ListNotificationsResponse(
            notifications=notifications,
            total=len(notifications),
        )

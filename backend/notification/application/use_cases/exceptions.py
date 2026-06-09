from __future__ import annotations


class UseCaseError(Exception):
    """Base exception for all use-case-level errors."""


class NotificationNotFoundError(UseCaseError):
    def __init__(self, notification_id: str) -> None:
        super().__init__(f"Notification not found: {notification_id}")
        self.notification_id = notification_id


class NotificationActionNotFoundError(UseCaseError):
    def __init__(self, action_id: str) -> None:
        super().__init__(f"Notification action not found: {action_id}")
        self.action_id = action_id

from __future__ import annotations


class NotificationDomainError(Exception):
    """Base exception for all notification domain errors."""


class InvalidNotificationTitleError(NotificationDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid notification title: {reason}")


class InvalidNotificationMessageError(NotificationDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid notification message: {reason}")


class InvalidNotificationTargetError(NotificationDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid notification target: {reason}")


class InvalidNotificationStatusError(NotificationDomainError):
    def __init__(self, status: str) -> None:
        super().__init__(f"Invalid notification status: {status!r}")
        self.status = status


class InvalidNotificationPriorityError(NotificationDomainError):
    def __init__(self, priority: str) -> None:
        super().__init__(f"Invalid notification priority: {priority!r}")
        self.priority = priority


class InvalidNotificationChannelError(NotificationDomainError):
    def __init__(self, channel: str) -> None:
        super().__init__(f"Invalid notification channel: {channel!r}")
        self.channel = channel


class InvalidExpirationError(NotificationDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid expiration: {reason}")


class NotificationExpiredError(NotificationDomainError):
    def __init__(self) -> None:
        super().__init__("Expired notifications are immutable")


class NotificationDismissedError(NotificationDomainError):
    def __init__(self) -> None:
        super().__init__("Dismissed notifications are immutable")


class InvalidNotificationTransitionError(NotificationDomainError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            f"Invalid notification transition from {current!r} to {target!r}"
        )
        self.current = current
        self.target = target


class InvalidActionLabelError(NotificationDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid action label: {reason}")


class InvalidCallbackError(NotificationDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid callback: {reason}")


class InvalidActionOwnershipError(NotificationDomainError):
    def __init__(self) -> None:
        super().__init__("Action must belong to an existing notification")


class SecretDetectedError(NotificationDomainError):
    def __init__(self, field: str) -> None:
        super().__init__(f"Notification content must not contain secrets: {field}")
        self.field = field

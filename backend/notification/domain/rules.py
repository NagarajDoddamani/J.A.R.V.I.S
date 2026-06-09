from __future__ import annotations

import re

from backend.notification.domain.exceptions import (
    InvalidActionLabelError,
    InvalidCallbackError,
    InvalidNotificationChannelError,
    InvalidNotificationPriorityError,
    InvalidNotificationTransitionError,
    InvalidNotificationTargetError,
    NotificationDismissedError,
    NotificationExpiredError,
    SecretDetectedError,
)
from backend.notification.domain.model import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    NotificationTarget,
)

# GLOBAL CONFIGURATION
MAX_TITLE_LENGTH: int = 200
MAX_MESSAGE_LENGTH: int = 5000

SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bpassword\b", re.IGNORECASE),
    re.compile(r"\btoken\b", re.IGNORECASE),
    re.compile(r"api[_\-]?key", re.IGNORECASE),
    re.compile(r"private[_\-]?key", re.IGNORECASE),
    re.compile(r"authorization", re.IGNORECASE),
    re.compile(r"\bbearer\b", re.IGNORECASE),
)

VALID_NOTIFICATION_TRANSITIONS: dict[NotificationStatus, set[NotificationStatus]] = {
    NotificationStatus.PENDING: {NotificationStatus.SHOWN, NotificationStatus.EXPIRED},
    NotificationStatus.SHOWN: {NotificationStatus.ACKNOWLEDGED, NotificationStatus.DISMISSED, NotificationStatus.EXPIRED},
    NotificationStatus.ACKNOWLEDGED: {NotificationStatus.EXPIRED},
    NotificationStatus.DISMISSED: set(),
    NotificationStatus.EXPIRED: set(),
}


# -- Rule 1: Title required -------------------------------------------------

def assert_title_required(title: str | None) -> None:
    if not title or not title.strip():
        from backend.notification.domain.exceptions import InvalidNotificationTitleError
        raise InvalidNotificationTitleError("Title is required")


# -- Rule 2: Message required -----------------------------------------------

def assert_message_required(message: str | None) -> None:
    if not message or not message.strip():
        from backend.notification.domain.exceptions import InvalidNotificationMessageError
        raise InvalidNotificationMessageError("Message is required")


# -- Rule 3: Target required ------------------------------------------------

def assert_target_required(target: NotificationTarget | None) -> None:
    if target is None:
        raise InvalidNotificationTargetError("Target is required")


# -- Rule 4: Priority must be valid -----------------------------------------

def assert_priority_valid(priority: str | NotificationPriority) -> None:
    if isinstance(priority, str):
        try:
            NotificationPriority(priority)
        except ValueError:
            raise InvalidNotificationPriorityError(priority)


# -- Rule 5: Channel must be valid ------------------------------------------

def assert_channel_valid(channel: str | NotificationChannel) -> None:
    if isinstance(channel, str):
        try:
            NotificationChannel(channel)
        except ValueError:
            raise InvalidNotificationChannelError(channel)


# -- Rule 6: Expiration must be after creation (enforced by ExpirationPolicy VO)


# -- Rule 7: Cannot acknowledge before SHOWN --------------------------------

def assert_can_acknowledge(status: NotificationStatus) -> None:
    if status != NotificationStatus.SHOWN:
        raise InvalidNotificationTransitionError(status.value, NotificationStatus.ACKNOWLEDGED.value)


# -- Rule 8: Cannot dismiss before SHOWN ------------------------------------

def assert_can_dismiss(status: NotificationStatus) -> None:
    if status != NotificationStatus.SHOWN:
        raise InvalidNotificationTransitionError(status.value, NotificationStatus.DISMISSED.value)


# -- Rule 9: Expired notifications are immutable ----------------------------

def assert_not_expired(notification: Notification) -> None:
    if notification.is_expired:
        raise NotificationExpiredError()


# -- Rule 10: Dismissed notifications are immutable -------------------------

def assert_not_dismissed(notification: Notification) -> None:
    if notification.is_dismissed:
        raise NotificationDismissedError()


# -- Combined immutable check -----------------------------------------------

def assert_not_immutable(notification: Notification) -> None:
    assert_not_expired(notification)
    assert_not_dismissed(notification)


# -- Rule 11: Action label required -----------------------------------------

def assert_action_label_required(label: str) -> None:
    if not label or not label.strip():
        raise InvalidActionLabelError("Action label is required")


# -- Rule 12: Callback name required ----------------------------------------

def assert_callback_name_required(callback_name: str) -> None:
    if not callback_name or not callback_name.strip():
        raise InvalidCallbackError("Callback name is required")


# -- Rule 13: Action must belong to an existing notification (enforced by factory)


# -- Rule 14: CRITICAL notifications cannot use SMS channel -----------------

def assert_critical_not_sms(priority: NotificationPriority, channel: NotificationChannel) -> None:
    if priority == NotificationPriority.CRITICAL and channel == NotificationChannel.SMS:
        raise InvalidNotificationChannelError("CRITICAL notifications cannot use SMS channel")


# -- Rule 15: Secret detection ----------------------------------------------

def assert_content_no_secrets(content: str) -> None:
    lower = content.lower()
    for pattern in SECRET_PATTERNS:
        if pattern.search(lower) or pattern.search(content):
            match = pattern.search(content)
            matched = match.group(0) if match else ""
            raise SecretDetectedError(matched[:40])


# -- Rule 16: Valid lifecycle transitions -----------------------------------

def assert_notification_can_transition(
    current: NotificationStatus, target: NotificationStatus
) -> None:
    allowed = VALID_NOTIFICATION_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidNotificationTransitionError(current.value, target.value)


# -- Composite validators ---------------------------------------------------

def validate_notification_creation(
    title: str | None,
    message: str | None,
    priority: str | NotificationPriority,
    channel: str | NotificationChannel,
    target: NotificationTarget | None,
) -> tuple[NotificationPriority, NotificationChannel]:
    assert_title_required(title)
    assert_message_required(message)
    assert_target_required(target)
    assert_priority_valid(priority)
    assert_channel_valid(channel)

    if isinstance(priority, str):
        priority = NotificationPriority(priority)
    if isinstance(channel, str):
        channel = NotificationChannel(channel)

    assert_critical_not_sms(priority, channel)
    assert_content_no_secrets(title or "")
    assert_content_no_secrets(message or "")

    return priority, channel


def validate_notification_update(notification: Notification) -> None:
    assert_not_immutable(notification)


def validate_action_creation(
    label: str,
    callback_name: str,
    notification: Notification | None,
) -> None:
    assert_action_label_required(label)
    assert_callback_name_required(callback_name)
    if notification is None:
        from backend.notification.domain.exceptions import InvalidActionOwnershipError
        raise InvalidActionOwnershipError()
    assert_content_no_secrets(label)

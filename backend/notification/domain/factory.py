from __future__ import annotations

from datetime import datetime, timezone

from backend.notification.domain.exceptions import InvalidNotificationPriorityError
from backend.notification.domain.model import (
    ActionId,
    ExpirationPolicy,
    Notification,
    NotificationAcknowledged,
    NotificationAction,
    NotificationActionInvoked,
    NotificationChannel,
    NotificationCreated,
    NotificationDismissed,
    NotificationExpired,
    NotificationId,
    NotificationMessage,
    NotificationPriority,
    NotificationShown,
    NotificationStatus,
    NotificationTarget,
    NotificationTitle,
)
from backend.notification.domain.rules import (
    validate_action_creation,
    validate_notification_creation,
)


class NotificationFactory:
    """Factory for creating validated notification domain aggregates."""

    @staticmethod
    def create_notification(
        *,
        title: str,
        message: str,
        priority: str | NotificationPriority,
        channel: str | NotificationChannel,
        target: NotificationTarget,
        expiration_policy: ExpirationPolicy | None = None,
    ) -> tuple[Notification, NotificationCreated]:
        priority_vo, channel_vo = validate_notification_creation(
            title=title,
            message=message,
            priority=priority,
            channel=channel,
            target=target,
        )

        title_vo = NotificationTitle(value=title)
        message_vo = NotificationMessage(value=message)

        now = datetime.now(tz=timezone.utc)
        notification = Notification(
            notification_id=NotificationId(),
            title=title_vo,
            message=message_vo,
            priority=priority_vo,
            channel=channel_vo,
            target=target,
            status=NotificationStatus.PENDING,
            created_at=now,
            expires_at=expiration_policy.expires_at if expiration_policy else None,
        )

        event = NotificationCreated(
            notification_id=notification.notification_id,
            title=title,
            message=message,
            priority=priority_vo.value,
            channel=channel_vo.value,
            target_type=target.target_type,
            target_id=target.target_id,
            occurred_at=now,
        )

        return notification, event

    @staticmethod
    def show_notification(
        notification: Notification,
    ) -> NotificationShown:
        notification.show()
        return notification.events[-1]

    @staticmethod
    def acknowledge_notification(
        notification: Notification,
    ) -> NotificationAcknowledged:
        notification.acknowledge()
        return notification.events[-1]

    @staticmethod
    def dismiss_notification(
        notification: Notification,
    ) -> NotificationDismissed:
        notification.dismiss()
        return notification.events[-1]

    @staticmethod
    def expire_notification(
        notification: Notification,
    ) -> NotificationExpired:
        notification.expire()
        return notification.events[-1]

    @staticmethod
    def create_action(
        *,
        notification: Notification,
        label: str,
        callback_name: str,
    ) -> NotificationAction:
        validate_action_creation(
            label=label,
            callback_name=callback_name,
            notification=notification,
        )

        action = NotificationAction(
            action_id=ActionId(),
            notification_id=notification.notification_id,
            label=label,
            callback_name=callback_name,
            created_at=datetime.now(tz=timezone.utc),
        )

        return action

    @staticmethod
    def invoke_action(
        action: NotificationAction,
    ) -> NotificationActionInvoked:
        return action.invoke()

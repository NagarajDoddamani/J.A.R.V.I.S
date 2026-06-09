from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NotificationActionResponse:
    action_id: str
    notification_id: str | None
    label: str
    callback_name: str
    created_at: datetime


@dataclass
class NotificationResponse:
    notification_id: str
    title: str | None
    message: str | None
    priority: str
    channel: str
    target_type: str | None
    target_id: str | None
    status: str
    created_at: datetime
    shown_at: datetime | None
    acknowledged_at: datetime | None
    dismissed_at: datetime | None
    expires_at: datetime | None


@dataclass
class CreateNotificationRequest:
    title: str
    message: str
    priority: str = "normal"
    channel: str = "in_app"
    target_type: str = "user"
    target_id: str = ""
    expires_at: datetime | None = None


@dataclass
class CreateNotificationResponse:
    notification_id: str
    title: str | None
    message: str | None
    priority: str
    channel: str
    target_type: str | None
    target_id: str | None
    status: str
    created_at: datetime
    expires_at: datetime | None


@dataclass
class ShowNotificationRequest:
    notification_id: str


@dataclass
class ShowNotificationResponse:
    notification_id: str
    status: str
    shown_at: datetime


@dataclass
class AcknowledgeNotificationRequest:
    notification_id: str


@dataclass
class AcknowledgeNotificationResponse:
    notification_id: str
    status: str
    acknowledged_at: datetime


@dataclass
class DismissNotificationRequest:
    notification_id: str


@dataclass
class DismissNotificationResponse:
    notification_id: str
    status: str
    dismissed_at: datetime


@dataclass
class ExpireNotificationRequest:
    notification_id: str


@dataclass
class ExpireNotificationResponse:
    notification_id: str
    status: str


@dataclass
class GetNotificationRequest:
    notification_id: str


@dataclass
class ListNotificationsRequest:
    status: str | None = None
    priority: str | None = None
    target_type: str | None = None
    target_id: str | None = None


@dataclass
class ListNotificationsResponse:
    notifications: list[NotificationResponse] = field(default_factory=list)
    total: int = 0


@dataclass
class CreateActionRequest:
    notification_id: str
    label: str
    callback_name: str


@dataclass
class CreateActionResponse:
    action_id: str
    notification_id: str | None
    label: str
    callback_name: str
    created_at: datetime


@dataclass
class InvokeActionRequest:
    action_id: str


@dataclass
class InvokeActionResponse:
    action_id: str
    notification_id: str | None
    callback_name: str
    occurred_at: datetime

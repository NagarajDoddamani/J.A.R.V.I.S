from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NotificationStorageDTO:
    notification_id: str
    title: str
    message: str
    priority: str
    channel: str
    target_type: str
    target_id: str
    status: str
    created_at: datetime
    shown_at: datetime | None = None
    acknowledged_at: datetime | None = None
    dismissed_at: datetime | None = None
    expires_at: datetime | None = None


@dataclass(frozen=True)
class NotificationActionStorageDTO:
    action_id: str
    notification_id: str
    label: str
    callback_name: str
    created_at: datetime


@dataclass(frozen=True)
class NotificationOutboxStorageDTO:
    event_id: str
    event_type: str
    aggregate_id: str
    occurred_at: datetime
    payload: str | None = None
    published: bool = False

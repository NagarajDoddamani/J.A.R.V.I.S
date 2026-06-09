from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ColumnContract:
    name: str
    py_type: type[Any]
    nullable: bool
    max_length: int | None = None
    enum_values: tuple[str, ...] | None = None


@dataclass(frozen=True)
class TableContract:
    name: str
    schema: str
    columns: tuple[ColumnContract, ...]
    primary_key: str | tuple[str, ...]
    indexes: tuple[str, ...] = ()
    unique_constraints: tuple[str, ...] = ()


NOTIFICATIONS_TABLE: TableContract = TableContract(
    name="notifications",
    schema="notification",
    columns=(
        ColumnContract("notification_id", str, nullable=False),
        ColumnContract("title", str, nullable=False),
        ColumnContract("message", str, nullable=False),
        ColumnContract("priority", str, nullable=False, max_length=16,
                       enum_values=("low", "normal", "high", "critical")),
        ColumnContract("channel", str, nullable=False, max_length=16,
                       enum_values=("in_app", "desktop", "email", "sms")),
        ColumnContract("target_type", str, nullable=False, max_length=64),
        ColumnContract("target_id", str, nullable=False, max_length=256),
        ColumnContract("status", str, nullable=False, max_length=16,
                       enum_values=("pending", "shown", "acknowledged", "dismissed", "expired")),
        ColumnContract("created_at", datetime, nullable=False),
        ColumnContract("shown_at", datetime, nullable=True),
        ColumnContract("acknowledged_at", datetime, nullable=True),
        ColumnContract("dismissed_at", datetime, nullable=True),
        ColumnContract("expires_at", datetime, nullable=True),
    ),
    primary_key="notification_id",
    indexes=(
        "ix_notifications_status",
        "ix_notifications_priority",
        "ix_notifications_target",
        "ix_notifications_expires_at",
    ),
)

NOTIFICATION_ACTIONS_TABLE: TableContract = TableContract(
    name="actions",
    schema="notification",
    columns=(
        ColumnContract("action_id", str, nullable=False),
        ColumnContract("notification_id", str, nullable=False),
        ColumnContract("label", str, nullable=False),
        ColumnContract("callback_name", str, nullable=False),
        ColumnContract("created_at", datetime, nullable=False),
    ),
    primary_key="action_id",
    indexes=(
        "ix_notification_actions_notification_id",
    ),
)

NOTIFICATION_OUTBOX_TABLE: TableContract = TableContract(
    name="outbox",
    schema="notification",
    columns=(
        ColumnContract("event_id", str, nullable=False),
        ColumnContract("event_type", str, nullable=False, max_length=32,
                       enum_values=("notification.created",
                                    "notification.shown",
                                    "notification.acknowledged",
                                    "notification.dismissed",
                                    "notification.expired",
                                    "notification.action.invoked")),
        ColumnContract("aggregate_id", str, nullable=False),
        ColumnContract("occurred_at", datetime, nullable=False),
        ColumnContract("payload", str, nullable=True),
        ColumnContract("published", bool, nullable=False),
    ),
    primary_key="event_id",
    indexes=(
        "ix_notification_outbox_unpublished",
        "ix_notification_outbox_aggregate",
    ),
)

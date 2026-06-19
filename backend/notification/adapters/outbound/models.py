from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


NOTIFICATION_SCHEMA: str | None = "notification"


def _schema(name: str) -> dict:
    return {"schema": NOTIFICATION_SCHEMA} if NOTIFICATION_SCHEMA else {}


class NotificationModel(Base):
    __tablename__ = "notifications"
    __table_args__ = _schema("notifications")

    notification_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    shown_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class NotificationActionModel(Base):
    __tablename__ = "actions"
    __table_args__ = _schema("actions")

    action_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    notification_id: Mapped[str] = mapped_column(String(256), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    callback_name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class NotificationOutboxModel(Base):
    __tablename__ = "outbox"
    __table_args__ = _schema("outbox")

    message_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    headers: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    causation_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    aggregate_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

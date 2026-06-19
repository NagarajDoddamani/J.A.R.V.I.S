from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


SETTINGS_SCHEMA: str | None = "settings"


def _schema(name: str) -> dict:
    return {"schema": SETTINGS_SCHEMA} if SETTINGS_SCHEMA else {}


class SettingsProfileModel(Base):
    __tablename__ = "profiles"
    __table_args__ = _schema("profiles")

    profile_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    schema_version_major: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    schema_version_minor: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )


class SettingModel(Base):
    __tablename__ = "settings"
    __table_args__ = _schema("settings")

    profile_id: Mapped[str] = mapped_column(
        String(256), primary_key=True
    )
    key: Mapped[str] = mapped_column(
        String(256), primary_key=True
    )
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    value_type: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )


class SettingsOutboxModel(Base):
    __tablename__ = "outbox"
    __table_args__ = _schema("outbox")

    message_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    aggregate_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    headers: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    causation_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)

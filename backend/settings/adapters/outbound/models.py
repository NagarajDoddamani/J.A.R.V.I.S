from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
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

    event_id: Mapped[str] = mapped_column(
        String(256), primary_key=True
    )
    profile_id: Mapped[str] = mapped_column(String(256), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

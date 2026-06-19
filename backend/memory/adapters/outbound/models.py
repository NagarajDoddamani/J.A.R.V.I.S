from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


MEMORY_SCHEMA: str | None = "memory"


def _schema(name: str) -> dict:
    return {"schema": MEMORY_SCHEMA} if MEMORY_SCHEMA else {}


class MemoryModel(Base):
    __tablename__ = "memories"
    __table_args__ = _schema("memories")

    memory_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    consent_id: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    provenance_actor_id: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )
    provenance_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    classification: Mapped[str] = mapped_column(String(16), nullable=False)
    sensitivity: Mapped[str] = mapped_column(String(16), nullable=False)
    retention_policy: Mapped[str] = mapped_column(String(16), nullable=False)
    retention_status: Mapped[str] = mapped_column(String(16), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ConsentModel(Base):
    __tablename__ = "consents"
    __table_args__ = _schema("consents")

    consent_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    policy_version: Mapped[str] = mapped_column(String(16), nullable=False)


class MemoryOutboxModel(Base):
    __tablename__ = "outbox"
    __table_args__ = _schema("outbox")

    message_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )
    correlation_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    causation_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    headers: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

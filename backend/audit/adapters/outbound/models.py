from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    JSON,
    LargeBinary,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# Override this in tests to None for SQLite compatibility.
AUDIT_SCHEMA: str | None = "audit"


def _schema(name: str) -> dict:
    return {"schema": AUDIT_SCHEMA} if AUDIT_SCHEMA else {}


class AuditEntryModel(Base):
    __tablename__ = "audit_entries"
    __table_args__ = _schema("audit_entries")

    entry_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True
    )
    chain_name: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    policy_decision: Mapped[str] = mapped_column(String(32), nullable=False)
    classification: Mapped[str] = mapped_column(String(16), nullable=False)
    correlation_id: Mapped[str] = mapped_column(
        String(256), nullable=False
    )
    causation_id: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    redacted_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    previous_hash: Mapped[bytes | None] = mapped_column(
        LargeBinary(64), nullable=True
    )
    entry_hash: Mapped[bytes] = mapped_column(LargeBinary(64), nullable=False)
    entry_index: Mapped[int] = mapped_column(BigInteger, nullable=False)


class AuditChainHeadModel(Base):
    __tablename__ = "audit_chain_heads"
    __table_args__ = _schema("audit_chain_heads")

    chain_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    head_hash: Mapped[bytes | None] = mapped_column(
        LargeBinary(64), nullable=True
    )
    entries_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )


class AuditOutboxModel(Base):
    __tablename__ = "outbox"
    __table_args__ = _schema("outbox")

    message_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True
    )
    aggregate_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False), nullable=True
    )
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    headers: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempts: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str] = mapped_column(
        String(256), nullable=False
    )
    causation_id: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )

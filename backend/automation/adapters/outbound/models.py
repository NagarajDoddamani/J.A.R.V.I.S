from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


AUTOMATION_SCHEMA: str | None = "automation"


def _schema(name: str) -> dict:
    return {"schema": AUTOMATION_SCHEMA} if AUTOMATION_SCHEMA else {}


class AutomationModel(Base):
    __tablename__ = "automations"
    __table_args__ = _schema("automations")

    automation_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class TriggerModel(Base):
    __tablename__ = "triggers"
    __table_args__ = _schema("triggers")

    trigger_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    automation_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(16), nullable=False)
    expression: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AutomationExecutionModel(Base):
    __tablename__ = "executions"
    __table_args__ = _schema("executions")

    execution_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    automation_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AutomationOutboxModel(Base):
    __tablename__ = "outbox"
    __table_args__ = _schema("outbox")

    message_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    aggregate_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    headers: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    causation_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)

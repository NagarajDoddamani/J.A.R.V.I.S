from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


ORCHESTRATOR_SCHEMA: str | None = "orchestration"


def _schema(name: str) -> dict:
    return {"schema": ORCHESTRATOR_SCHEMA} if ORCHESTRATOR_SCHEMA else {}


class OrchestrationModel(Base):
    __tablename__ = "orchestrations"
    __table_args__ = _schema("orchestrations")

    orchestration_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class WorkflowModel(Base):
    __tablename__ = "workflows"
    __table_args__ = _schema("workflows")

    workflow_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    orchestration_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)


class WorkflowStepModel(Base):
    __tablename__ = "workflow_steps"
    __table_args__ = _schema("workflow_steps")

    step_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    workflow_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    agent_role: Mapped[str] = mapped_column(String(16), nullable=False)
    execution_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class OrchestratorOutboxModel(Base):
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
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    headers: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    causation_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)

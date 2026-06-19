from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


POLICY_SCHEMA: str | None = "policy"


def _schema(name: str) -> dict:
    return {"schema": POLICY_SCHEMA} if POLICY_SCHEMA else {}


class PolicyModel(Base):
    __tablename__ = "policies"
    __table_args__ = _schema("policies")

    policy_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PolicyRuleModel(Base):
    __tablename__ = "rules"
    __table_args__ = _schema("rules")

    rule_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    policy_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str | None] = mapped_column(String(64), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PolicyEvaluationModel(Base):
    __tablename__ = "evaluations"
    __table_args__ = _schema("evaluations")

    evaluation_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    policy_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PolicyOutboxModel(Base):
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
    aggregate_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

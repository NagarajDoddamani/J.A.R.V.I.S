from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.planner.adapters.outbound.clock import SystemClockAdapter
from backend.planner.adapters.outbound.mapper import PlanMapperImpl
from backend.planner.adapters.outbound.models import Base
from backend.planner.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyPlanRepository,
    SqlAlchemyPlannerOutboxAdapter,
)
from backend.planner.application.use_cases.create_plan import CreatePlanUseCase
from backend.planner.application.use_cases.dto import CreatePlanRequest
from backend.planner.domain.model import (
    AgentType,
    Plan,
    PlanApproved,
    PlanCancelled,
    PlanCompleted,
    PlanCreated,
    PlanExecutionStarted,
    PlanFailed,
    PlanGoal,
    PlanId,
    PlanPriority,
    PlanReady,
    PlanStatus,
    TaskAssigned,
    TaskCompleted,
    TaskCreated,
    TaskFailed,
    TaskId,
    TaskStatus,
    UserRequest,
)
from backend.planner.nats import (
    PlannerOutboxEvent,
    publish_planner_outbox_events,
)

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)

for _table in Base.metadata.tables.values():
    _table.schema = None


@pytest.fixture
def session():
    e = create_engine("sqlite://", echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    conn = e.connect()
    transaction = conn.begin()
    s = Session(bind=conn)
    yield s
    s.close()
    transaction.rollback()
    conn.close()
    e.dispose()


@pytest.fixture
def outbox(session):
    return SqlAlchemyPlannerOutboxAdapter(session)


@pytest.fixture
def mock_js():
    js = AsyncMock()
    js.publish = AsyncMock()
    return js


def _add_plan_outbox_entries(
    outbox: SqlAlchemyPlannerOutboxAdapter, session, count: int = 3
):
    plan_repo = SqlAlchemyPlanRepository(session, mapper=PlanMapperImpl())
    uc = CreatePlanUseCase(plan_repo=plan_repo, outbox=outbox)
    for i in range(count):
        uc.execute(
            CreatePlanRequest(
                user_request=f"request-{i}",
                goal=f"goal-{i}",
                priority="normal",
                strategy="sequential",
            )
        )


# ===================================================================
# NATS publisher tests
# ===================================================================


class TestPlannerNATSPublisher:
    @pytest.mark.asyncio
    async def test_publishes_events(
        self, outbox: SqlAlchemyPlannerOutboxAdapter, mock_js
    ) -> None:
        _add_plan_outbox_entries(outbox, outbox._session, count=2)
        await publish_planner_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        assert mock_js.publish.call_count >= 2

    @pytest.mark.asyncio
    async def test_fifo_ordering(
        self, outbox: SqlAlchemyPlannerOutboxAdapter, mock_js
    ) -> None:
        _add_plan_outbox_entries(outbox, outbox._session, count=3)
        await publish_planner_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        calls = [call[0][1] for call in mock_js.publish.call_args_list]
        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_batch_limit(
        self, outbox: SqlAlchemyPlannerOutboxAdapter, mock_js
    ) -> None:
        _add_plan_outbox_entries(outbox, outbox._session, count=5)
        await publish_planner_outbox_events(
            mock_js,
            outbox=outbox,
            batch=2,
            interval_seconds=0.1,
            max_iterations=1,
        )
        assert mock_js.publish.call_count <= 2

    @pytest.mark.asyncio
    async def test_max_iterations(
        self, outbox: SqlAlchemyPlannerOutboxAdapter, mock_js
    ) -> None:
        _add_plan_outbox_entries(outbox, outbox._session, count=2)
        await publish_planner_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=2,
        )
        assert mock_js.publish.call_count >= 2

    @pytest.mark.asyncio
    async def test_mark_published_after_publish(
        self, outbox: SqlAlchemyPlannerOutboxAdapter, mock_js, session
    ) -> None:
        _add_plan_outbox_entries(outbox, session, count=2)
        unpublished_before = outbox.fetch_unpublished()
        assert len(unpublished_before) == 2

        await publish_planner_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        session.flush()
        unpublished_after = outbox.fetch_unpublished()
        assert len(unpublished_after) == 0

    @pytest.mark.asyncio
    async def test_rollback_on_exception(
        self, outbox: SqlAlchemyPlannerOutboxAdapter, mock_js, session
    ) -> None:
        mock_js.publish = AsyncMock(side_effect=Exception("NATS error"))
        _add_plan_outbox_entries(outbox, session, count=1)
        await publish_planner_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )

    @pytest.mark.asyncio
    async def test_empty_outbox(
        self, outbox: SqlAlchemyPlannerOutboxAdapter, mock_js
    ) -> None:
        await publish_planner_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        mock_js.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_subject_for_plan_created(
        self, outbox: SqlAlchemyPlannerOutboxAdapter, mock_js
    ) -> None:
        _add_plan_outbox_entries(outbox, outbox._session, count=1)
        await publish_planner_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        args, _ = mock_js.publish.call_args
        subject = args[0]
        assert subject == "jarvis.event.planner.created.v1"

    @pytest.mark.asyncio
    async def test_all_event_subjects(
        self, outbox: SqlAlchemyPlannerOutboxAdapter, mock_js
    ) -> None:
        events = [
            PlanCreated(PlanId(), "R", "G", "normal", "seq", NOW),
            PlanApproved(PlanId(), NOW),
            PlanReady(PlanId(), NOW),
            PlanExecutionStarted(PlanId(), NOW),
            PlanCompleted(PlanId(), NOW),
            PlanFailed(PlanId(), "err", NOW),
            PlanCancelled(PlanId(), NOW),
            TaskCreated(TaskId(), "desc", NOW),
            TaskAssigned(TaskId(), AgentType.PLANNER, NOW),
            TaskCompleted(TaskId(), NOW),
            TaskFailed(TaskId(), "err", NOW),
        ]
        for event in events:
            outbox.append(event)
        await publish_planner_outbox_events(
            mock_js,
            outbox=outbox,
            batch=20,
            interval_seconds=0.1,
            max_iterations=1,
        )
        assert mock_js.publish.call_count == 11

    @pytest.mark.asyncio
    async def test_envelope_contains_producer(
        self, outbox: SqlAlchemyPlannerOutboxAdapter, mock_js
    ) -> None:
        _add_plan_outbox_entries(outbox, outbox._session, count=1)
        await publish_planner_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        args, _ = mock_js.publish.call_args
        import json
        payload = json.loads(args[1].decode())
        assert payload["producer"] == "planner"
        assert "event_id" in payload
        assert "event_type" in payload
        assert "kind" in payload
        assert "aggregate_id" in payload
        assert "occurred_at" in payload

    @pytest.mark.asyncio
    async def test_plan_failed_envelope_has_failure_reason(
        self, outbox: SqlAlchemyPlannerOutboxAdapter, mock_js
    ) -> None:
        event = PlanFailed(
            plan_id=PlanId(), failure_reason="test error", occurred_at=NOW
        )
        outbox.append(event)
        await publish_planner_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        import json
        args, _ = mock_js.publish.call_args
        payload = json.loads(args[1].decode())
        assert payload["failure_reason"] == "test error"

    @pytest.mark.asyncio
    async def test_task_created_envelope_has_description(
        self, outbox: SqlAlchemyPlannerOutboxAdapter, mock_js
    ) -> None:
        event = TaskCreated(
            task_id=TaskId(), description="my task", occurred_at=NOW
        )
        outbox.append(event)
        await publish_planner_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        import json
        args, _ = mock_js.publish.call_args
        payload = json.loads(args[1].decode())
        assert payload["description"] == "my task"

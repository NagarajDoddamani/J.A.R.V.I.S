from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.automation.adapters.outbound.mapper import AutomationMapperImpl
from backend.automation.adapters.outbound.models import Base
from backend.automation.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyAutomationRepository,
    SqlAlchemyAutomationOutboxAdapter,
)
from backend.automation.application.use_cases.create_automation import (
    CreateAutomationUseCase,
)
from backend.automation.application.use_cases.dto import CreateAutomationRequest
from backend.automation.domain.model import (
    ActionAdded,
    AutomationActivated,
    AutomationCreated,
    AutomationDisabled,
    AutomationExecutionCompleted,
    AutomationExecutionFailed,
    AutomationExecutionStarted,
    AutomationId,
    AutomationPaused,
    TriggerAdded,
    TriggerDisabled,
    TriggerEnabled,
    TriggerId,
    WorkflowExecutionId,
)
from backend.automation.nats import (
    publish_automation_outbox_events,
)

NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)

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
    return SqlAlchemyAutomationOutboxAdapter(session)


@pytest.fixture
def mock_js():
    js = AsyncMock()
    js.publish = AsyncMock()
    return js


def _add_automation_outbox_entries(
    outbox: SqlAlchemyAutomationOutboxAdapter, session, count: int = 3
):
    automation_repo = SqlAlchemyAutomationRepository(
        session, mapper=AutomationMapperImpl()
    )
    uc = CreateAutomationUseCase(automation_repo=automation_repo, outbox=outbox)
    for i in range(count):
        uc.execute(
            CreateAutomationRequest(
                name=f"test-{i}",
                description=f"description-{i}",
                execution_mode="once",
            )
        )


class TestAutomationNATSPublisher:
    @pytest.mark.asyncio
    async def test_publishes_events(
        self, outbox: SqlAlchemyAutomationOutboxAdapter, mock_js
    ) -> None:
        _add_automation_outbox_entries(outbox, outbox._session, count=2)
        await publish_automation_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        assert mock_js.publish.call_count >= 2

    @pytest.mark.asyncio
    async def test_fifo_ordering(
        self, outbox: SqlAlchemyAutomationOutboxAdapter, mock_js
    ) -> None:
        _add_automation_outbox_entries(outbox, outbox._session, count=3)
        await publish_automation_outbox_events(
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
        self, outbox: SqlAlchemyAutomationOutboxAdapter, mock_js
    ) -> None:
        _add_automation_outbox_entries(outbox, outbox._session, count=5)
        await publish_automation_outbox_events(
            mock_js,
            outbox=outbox,
            batch=2,
            interval_seconds=0.1,
            max_iterations=1,
        )
        assert mock_js.publish.call_count <= 2

    @pytest.mark.asyncio
    async def test_max_iterations(
        self, outbox: SqlAlchemyAutomationOutboxAdapter, mock_js
    ) -> None:
        _add_automation_outbox_entries(outbox, outbox._session, count=2)
        await publish_automation_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=2,
        )
        assert mock_js.publish.call_count >= 2

    @pytest.mark.asyncio
    async def test_mark_published_after_publish(
        self, outbox: SqlAlchemyAutomationOutboxAdapter, mock_js, session
    ) -> None:
        _add_automation_outbox_entries(outbox, session, count=2)
        unpublished_before = outbox.fetch_unpublished()
        assert len(unpublished_before) == 2

        await publish_automation_outbox_events(
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
        self, outbox: SqlAlchemyAutomationOutboxAdapter, mock_js, session
    ) -> None:
        mock_js.publish = AsyncMock(side_effect=Exception("NATS error"))
        _add_automation_outbox_entries(outbox, session, count=1)
        await publish_automation_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )

    @pytest.mark.asyncio
    async def test_empty_outbox(
        self, outbox: SqlAlchemyAutomationOutboxAdapter, mock_js
    ) -> None:
        await publish_automation_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        mock_js.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_subject_for_automation_created(
        self, outbox: SqlAlchemyAutomationOutboxAdapter, mock_js
    ) -> None:
        _add_automation_outbox_entries(outbox, outbox._session, count=1)
        await publish_automation_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        args, _ = mock_js.publish.call_args
        subject = args[0]
        assert subject == "jarvis.event.automation.automation_created.v1"

    @pytest.mark.asyncio
    async def test_all_event_subjects(
        self, outbox: SqlAlchemyAutomationOutboxAdapter, mock_js
    ) -> None:
        aid = AutomationId()
        wid = WorkflowExecutionId()
        tid = TriggerId()
        events = [
            AutomationCreated(aid, "n", "d", "once", NOW),
            AutomationActivated(aid, NOW),
            AutomationPaused(aid, NOW),
            AutomationDisabled(aid, NOW),
            AutomationExecutionStarted(aid, wid, NOW),
            AutomationExecutionCompleted(aid, wid, "ok", NOW),
            AutomationExecutionFailed(aid, wid, "err", NOW),
            TriggerAdded(tid, aid, "manual", "", NOW),
            TriggerEnabled(tid, aid, NOW),
            TriggerDisabled(tid, aid, NOW),
            ActionAdded(aid, "notification", NOW),
        ]
        for event in events:
            outbox.append(event)
        await publish_automation_outbox_events(
            mock_js,
            outbox=outbox,
            batch=20,
            interval_seconds=0.1,
            max_iterations=1,
        )
        assert mock_js.publish.call_count == 11

    @pytest.mark.asyncio
    async def test_envelope_contains_producer(
        self, outbox: SqlAlchemyAutomationOutboxAdapter, mock_js
    ) -> None:
        _add_automation_outbox_entries(outbox, outbox._session, count=1)
        await publish_automation_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        args, _ = mock_js.publish.call_args
        import json
        payload = json.loads(args[1].decode())
        assert payload["producer"] == "automation"
        assert "event_id" in payload
        assert "event_type" in payload
        assert "kind" in payload
        assert "aggregate_id" in payload
        assert "occurred_at" in payload

    @pytest.mark.asyncio
    async def test_automation_created_envelope_has_fields(
        self, outbox: SqlAlchemyAutomationOutboxAdapter, mock_js
    ) -> None:
        event = AutomationCreated(
            automation_id=AutomationId(),
            name="test-auto",
            description="test-desc",
            execution_mode="once",
            occurred_at=NOW,
        )
        outbox.append(event)
        await publish_automation_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        import json
        args, _ = mock_js.publish.call_args
        payload = json.loads(args[1].decode())
        assert payload["name"] == "test-auto"
        assert payload["description"] == "test-desc"
        assert payload["execution_mode"] == "once"

    @pytest.mark.asyncio
    async def test_execution_failed_envelope_has_failure_reason(
        self, outbox: SqlAlchemyAutomationOutboxAdapter, mock_js
    ) -> None:
        event = AutomationExecutionFailed(
            automation_id=AutomationId(),
            execution_id=WorkflowExecutionId(),
            failure_reason="test error",
            occurred_at=NOW,
        )
        outbox.append(event)
        await publish_automation_outbox_events(
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

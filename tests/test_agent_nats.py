from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from backend.agent.domain.model import (
    AgentActivated,
    AgentCreated,
    AgentDisabled,
    AgentExecutionCompleted,
    AgentExecutionFailed,
    AgentExecutionStarted,
    AgentId,
    AgentPaused,
    AgentTaskCancelled,
    AgentTaskCompleted,
    AgentTaskCreated,
    AgentTaskFailed,
    AgentTaskId,
    AgentExecutionId,
    AgentTaskStarted,
)
from backend.agent.nats import (
    _build_envelope,
    _EVENT_TYPE_MAP,
    _get_aggregate_id,
    _NATS_SUBJECT_MAP,
    publish_agent_outbox_events,
)

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


class TestEventTypeMap:
    def test_all_12_events_mapped(self) -> None:
        assert len(_EVENT_TYPE_MAP) == 12

    def test_event_type_values(self) -> None:
        assert _EVENT_TYPE_MAP[AgentCreated] == "agent_created"
        assert _EVENT_TYPE_MAP[AgentActivated] == "agent_activated"
        assert _EVENT_TYPE_MAP[AgentPaused] == "agent_paused"
        assert _EVENT_TYPE_MAP[AgentDisabled] == "agent_disabled"
        assert _EVENT_TYPE_MAP[AgentTaskCreated] == "agent_task_created"
        assert _EVENT_TYPE_MAP[AgentTaskStarted] == "agent_task_started"
        assert _EVENT_TYPE_MAP[AgentTaskCompleted] == "agent_task_completed"
        assert _EVENT_TYPE_MAP[AgentTaskFailed] == "agent_task_failed"
        assert _EVENT_TYPE_MAP[AgentTaskCancelled] == "agent_task_cancelled"
        assert (
            _EVENT_TYPE_MAP[AgentExecutionStarted]
            == "agent_execution_started"
        )
        assert (
            _EVENT_TYPE_MAP[AgentExecutionCompleted]
            == "agent_execution_completed"
        )
        assert (
            _EVENT_TYPE_MAP[AgentExecutionFailed]
            == "agent_execution_failed"
        )


class TestNatsSubjects:
    def test_all_12_subjects(self) -> None:
        assert len(_NATS_SUBJECT_MAP) == 12

    def test_subject_format(self) -> None:
        assert (
            _NATS_SUBJECT_MAP[AgentCreated]
            == "jarvis.event.agent.agent_created.v1"
        )
        assert (
            _NATS_SUBJECT_MAP[AgentTaskCreated]
            == "jarvis.event.agent.agent_task_created.v1"
        )
        assert (
            _NATS_SUBJECT_MAP[AgentExecutionStarted]
            == "jarvis.event.agent.agent_execution_started.v1"
        )


class TestGetAggregateId:
    def test_agent_created(self) -> None:
        e = AgentCreated(
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            agent_type="coordinator",
            name="Test",
            occurred_at=NOW,
        )
        assert _get_aggregate_id(e) == str(e.agent_id)

    def test_agent_activated(self) -> None:
        e = AgentActivated(
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            occurred_at=NOW,
        )
        assert _get_aggregate_id(e) == str(e.agent_id)

    def test_task_event(self) -> None:
        e = AgentTaskCreated(
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            goal="g",
            instruction="i",
            occurred_at=NOW,
        )
        assert _get_aggregate_id(e) == str(e.agent_id)

    def test_execution_event(self) -> None:
        e = AgentExecutionStarted(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            occurred_at=NOW,
        )
        assert _get_aggregate_id(e) == str(e.agent_id)


class TestBuildEnvelope:
    def test_agent_created_envelope(self) -> None:
        e = AgentCreated(
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            agent_type="coordinator",
            name="Test Agent",
            occurred_at=NOW,
        )
        env = _build_envelope(e)
        assert env["event_type"] == "agent_created"
        assert env["producer"] == "agent"
        assert env["aggregate_id"] == str(e.agent_id)
        assert env["name"] == "Test Agent"
        assert env["agent_type"] == "coordinator"

    def test_agent_activated_envelope(self) -> None:
        e = AgentActivated(
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            occurred_at=NOW,
        )
        env = _build_envelope(e)
        assert env["event_type"] == "agent_activated"
        assert "name" not in env

    def test_task_created_envelope(self) -> None:
        e = AgentTaskCreated(
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            goal="test goal",
            instruction="test instr",
            occurred_at=NOW,
        )
        env = _build_envelope(e)
        assert env["event_type"] == "agent_task_created"
        assert env["goal"] == "test goal"
        assert env["instruction"] == "test instr"

    def test_execution_failed_envelope(self) -> None:
        e = AgentExecutionFailed(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            failure_reason="error",
            occurred_at=NOW,
        )
        env = _build_envelope(e)
        assert env["event_type"] == "agent_execution_failed"
        assert env["failure_reason"] == "error"


class TestPublishAgentOutboxEvents:
    @pytest.mark.asyncio
    async def test_publishes_and_marks(self) -> None:
        js = AsyncMock()
        outbox = MagicMock()
        event = AgentCreated(
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            agent_type="coordinator",
            name="Test",
            occurred_at=NOW,
        )
        outbox.fetch_unpublished.return_value = [event]
        outbox.mark_published = MagicMock()

        await publish_agent_outbox_events(
            js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        outbox.fetch_unpublished.assert_called_once_with(limit=10)
        js.publish.assert_awaited_once()
        outbox.mark_published.assert_called_once()

    @pytest.mark.asyncio
    async def test_fifo_ordering_preserved(self) -> None:
        js = AsyncMock()
        outbox = MagicMock()
        event1 = AgentCreated(
            agent_id=AgentId(), agent_type="coordinator", name="A",
            occurred_at=NOW,
        )
        event2 = AgentActivated(
            agent_id=AgentId(), occurred_at=NOW,
        )
        outbox.fetch_unpublished.return_value = [event1, event2]

        await publish_agent_outbox_events(
            js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        assert js.publish.await_count == 2

    @pytest.mark.asyncio
    async def test_rollback_on_exception(self) -> None:
        js = AsyncMock()
        js.publish.side_effect = RuntimeError("NATS down")
        outbox = MagicMock()
        event = AgentCreated(
            agent_id=AgentId(), agent_type="coordinator", name="T",
            occurred_at=NOW,
        )
        outbox.fetch_unpublished.return_value = [event]

        await publish_agent_outbox_events(
            js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        outbox.fetch_unpublished.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_iterations_stops(self) -> None:
        js = AsyncMock()
        outbox = MagicMock()
        outbox.fetch_unpublished.return_value = []

        await publish_agent_outbox_events(
            js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        assert js.publish.await_count == 0

    @pytest.mark.asyncio
    async def test_subject_mapping(self) -> None:
        js = AsyncMock()
        outbox = MagicMock()
        event = AgentCreated(
            agent_id=AgentId(), agent_type="coordinator", name="T",
            occurred_at=NOW,
        )
        outbox.fetch_unpublished.return_value = [event]

        await publish_agent_outbox_events(
            js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        call_args = js.publish.await_args
        assert call_args is not None
        assert call_args[0][0] == "jarvis.event.agent.agent_created.v1"

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from backend.orchestrator.domain.model import (
    OrchestrationCancelled,
    OrchestrationCompleted,
    OrchestrationCreated,
    OrchestrationExecutionStarted,
    OrchestrationFailed,
    OrchestrationId,
    OrchestrationPlanningStarted,
    OrchestrationResearchStarted,
    WorkflowCompleted,
    WorkflowCreated,
    WorkflowFailed,
    WorkflowId,
    WorkflowStepCompleted,
    WorkflowStepFailed,
    WorkflowStepStarted,
)
from backend.orchestrator.nats import (
    _NATS_SUBJECT_MAP,
    publish_orchestrator_outbox_events,
)

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


def _make_created() -> OrchestrationCreated:
    return OrchestrationCreated(
        orchestration_id=OrchestrationId(),
        intent="test intent",
        goal="test goal",
        occurred_at=NOW,
    )


def _make_planning_started() -> OrchestrationPlanningStarted:
    return OrchestrationPlanningStarted(
        orchestration_id=OrchestrationId(), occurred_at=NOW
    )


def _make_research_started() -> OrchestrationResearchStarted:
    return OrchestrationResearchStarted(
        orchestration_id=OrchestrationId(), occurred_at=NOW
    )


def _make_execution_started() -> OrchestrationExecutionStarted:
    return OrchestrationExecutionStarted(
        orchestration_id=OrchestrationId(), occurred_at=NOW
    )


def _make_completed() -> OrchestrationCompleted:
    return OrchestrationCompleted(
        orchestration_id=OrchestrationId(), occurred_at=NOW
    )


def _make_failed() -> OrchestrationFailed:
    return OrchestrationFailed(
        orchestration_id=OrchestrationId(),
        failure_reason="error",
        occurred_at=NOW,
    )


def _make_cancelled() -> OrchestrationCancelled:
    return OrchestrationCancelled(
        orchestration_id=OrchestrationId(), occurred_at=NOW
    )


def _make_wf_created() -> WorkflowCreated:
    return WorkflowCreated(
        workflow_id=WorkflowId(),
        orchestration_id=OrchestrationId(),
        goal="wf goal",
        mode="sequential",
        occurred_at=NOW,
    )


def _make_wf_completed() -> WorkflowCompleted:
    return WorkflowCompleted(
        workflow_id=WorkflowId(), occurred_at=NOW
    )


def _make_wf_failed() -> WorkflowFailed:
    return WorkflowFailed(
        workflow_id=WorkflowId(),
        failure_reason="wf error",
        occurred_at=NOW,
    )


def _make_step_started() -> WorkflowStepStarted:
    return WorkflowStepStarted(
        step_id=WorkflowId(), occurred_at=NOW
    )


def _make_step_completed() -> WorkflowStepCompleted:
    return WorkflowStepCompleted(
        step_id=WorkflowId(), result="done", occurred_at=NOW
    )


def _make_step_failed() -> WorkflowStepFailed:
    return WorkflowStepFailed(
        step_id=WorkflowId(),
        failure_reason="step error",
        occurred_at=NOW,
    )


# ===================================================================
# NATS subject map tests
# ===================================================================


class TestNatsSubjectMap:
    def test_all_event_types_have_subjects(self) -> None:
        events = [
            _make_created(),
            _make_planning_started(),
            _make_research_started(),
            _make_execution_started(),
            _make_completed(),
            _make_failed(),
            _make_cancelled(),
            _make_wf_created(),
            _make_wf_completed(),
            _make_wf_failed(),
            _make_step_started(),
            _make_step_completed(),
            _make_step_failed(),
        ]
        for event in events:
            subject = _NATS_SUBJECT_MAP.get(type(event))
            assert subject is not None, f"Missing subject for {type(event).__name__}"

    def test_subject_patterns(self) -> None:
        assert (
            _NATS_SUBJECT_MAP[OrchestrationCreated]
            == "jarvis.event.orchestrator.created.v1"
        )
        assert (
            _NATS_SUBJECT_MAP[OrchestrationPlanningStarted]
            == "jarvis.event.orchestrator.planning_started.v1"
        )
        assert (
            _NATS_SUBJECT_MAP[OrchestrationResearchStarted]
            == "jarvis.event.orchestrator.research_started.v1"
        )
        assert (
            _NATS_SUBJECT_MAP[OrchestrationExecutionStarted]
            == "jarvis.event.orchestrator.execution_started.v1"
        )
        assert (
            _NATS_SUBJECT_MAP[OrchestrationCompleted]
            == "jarvis.event.orchestrator.completed.v1"
        )
        assert (
            _NATS_SUBJECT_MAP[OrchestrationFailed]
            == "jarvis.event.orchestrator.failed.v1"
        )
        assert (
            _NATS_SUBJECT_MAP[OrchestrationCancelled]
            == "jarvis.event.orchestrator.cancelled.v1"
        )
        assert (
            _NATS_SUBJECT_MAP[WorkflowCreated]
            == "jarvis.event.orchestrator.workflow_created.v1"
        )
        assert (
            _NATS_SUBJECT_MAP[WorkflowCompleted]
            == "jarvis.event.orchestrator.workflow_completed.v1"
        )
        assert (
            _NATS_SUBJECT_MAP[WorkflowFailed]
            == "jarvis.event.orchestrator.workflow_failed.v1"
        )
        assert (
            _NATS_SUBJECT_MAP[WorkflowStepStarted]
            == "jarvis.event.orchestrator.step_started.v1"
        )
        assert (
            _NATS_SUBJECT_MAP[WorkflowStepCompleted]
            == "jarvis.event.orchestrator.step_completed.v1"
        )
        assert (
            _NATS_SUBJECT_MAP[WorkflowStepFailed]
            == "jarvis.event.orchestrator.step_failed.v1"
        )


# ===================================================================
# Publisher tests
# ===================================================================


class TestPublishOrchestratorOutboxEvents:
    @pytest.mark.asyncio
    async def test_publishes_events(self) -> None:
        outbox = MagicMock()
        events = [_make_created(), _make_planning_started()]
        outbox.fetch_unpublished.return_value = events
        js = AsyncMock()

        await publish_orchestrator_outbox_events(
            js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )

        assert js.publish.call_count == 2
        outbox.mark_published.assert_called()

    @pytest.mark.asyncio
    async def test_all_13_event_types_published(self) -> None:
        outbox = MagicMock()
        events = [
            _make_created(),
            _make_planning_started(),
            _make_research_started(),
            _make_execution_started(),
            _make_completed(),
            _make_failed(),
            _make_cancelled(),
            _make_wf_created(),
            _make_wf_completed(),
            _make_wf_failed(),
            _make_step_started(),
            _make_step_completed(),
            _make_step_failed(),
        ]
        outbox.fetch_unpublished.return_value = events
        js = AsyncMock()

        await publish_orchestrator_outbox_events(
            js,
            outbox=outbox,
            batch=20,
            interval_seconds=0.1,
            max_iterations=1,
        )

        assert js.publish.call_count == 13

    @pytest.mark.asyncio
    async def test_fifo_ordering(self) -> None:
        outbox = MagicMock()
        e1 = _make_created()
        e2 = _make_planning_started()
        outbox.fetch_unpublished.return_value = [e1, e2]
        js = AsyncMock()

        await publish_orchestrator_outbox_events(
            js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )

        calls = js.publish.call_args_list
        assert len(calls) == 2

    @pytest.mark.asyncio
    async def test_batch_respected(self) -> None:
        outbox = MagicMock()
        outbox.fetch_unpublished.return_value = [_make_created()]
        js = AsyncMock()

        await publish_orchestrator_outbox_events(
            js,
            outbox=outbox,
            batch=5,
            interval_seconds=0.1,
            max_iterations=1,
        )

        outbox.fetch_unpublished.assert_called_with(limit=5)

    @pytest.mark.asyncio
    async def test_rollback_on_publish_failure(self) -> None:
        outbox = MagicMock()
        outbox.fetch_unpublished.return_value = [_make_created()]
        js = AsyncMock()
        js.publish.side_effect = Exception("NATS unavailable")

        with patch("backend.orchestrator.nats.logger") as mock_logger:
            await publish_orchestrator_outbox_events(
                js,
                outbox=outbox,
                batch=10,
                interval_seconds=0.1,
                max_iterations=1,
            )
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_subject_selection_orchestration_created(self) -> None:
        outbox = MagicMock()
        event = _make_created()
        outbox.fetch_unpublished.return_value = [event]
        js = AsyncMock()

        await publish_orchestrator_outbox_events(
            js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )

        js.publish.assert_called_once_with(
            "jarvis.event.orchestrator.created.v1",
            json.dumps(
                {
                    "event_id": str(event.event_id),
                    "event_type": "OrchestrationCreated",
                    "kind": "event",
                    "producer": "orchestrator",
                    "aggregate_id": str(event.orchestration_id),
                    "occurred_at": event.occurred_at.isoformat(),
                    "intent": event.intent,
                    "goal": event.goal,
                },
                separators=(",", ":"),
            ).encode("utf-8"),
        )

    @pytest.mark.asyncio
    async def test_subject_selection_orchestration_failed(self) -> None:
        outbox = MagicMock()
        event = _make_failed()
        outbox.fetch_unpublished.return_value = [event]
        js = AsyncMock()

        await publish_orchestrator_outbox_events(
            js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )

        js.publish.assert_called_once()
        call_args = js.publish.call_args[0]
        assert call_args[0] == "jarvis.event.orchestrator.failed.v1"
        payload = json.loads(call_args[1])
        assert payload["failure_reason"] == "error"

    @pytest.mark.asyncio
    async def test_subject_selection_workflow_created(self) -> None:
        outbox = MagicMock()
        event = _make_wf_created()
        outbox.fetch_unpublished.return_value = [event]
        js = AsyncMock()

        await publish_orchestrator_outbox_events(
            js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )

        js.publish.assert_called_once()
        call_args = js.publish.call_args[0]
        assert call_args[0] == "jarvis.event.orchestrator.workflow_created.v1"
        payload = json.loads(call_args[1])
        assert payload["goal"] == "wf goal"

    @pytest.mark.asyncio
    async def test_subject_selection_step_completed(self) -> None:
        outbox = MagicMock()
        event = _make_step_completed()
        outbox.fetch_unpublished.return_value = [event]
        js = AsyncMock()

        await publish_orchestrator_outbox_events(
            js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )

        js.publish.assert_called_once()
        call_args = js.publish.call_args[0]
        assert call_args[0] == "jarvis.event.orchestrator.step_completed.v1"
        payload = json.loads(call_args[1])
        assert payload["result"] == "done"

    @pytest.mark.asyncio
    async def test_subject_selection_step_failed(self) -> None:
        outbox = MagicMock()
        event = _make_step_failed()
        outbox.fetch_unpublished.return_value = [event]
        js = AsyncMock()

        await publish_orchestrator_outbox_events(
            js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )

        js.publish.assert_called_once()
        call_args = js.publish.call_args[0]
        assert call_args[0] == "jarvis.event.orchestrator.step_failed.v1"
        payload = json.loads(call_args[1])
        assert payload["failure_reason"] == "step error"

    @pytest.mark.asyncio
    async def test_mark_published_per_event(self) -> None:
        outbox = MagicMock()
        events = [_make_created(), _make_planning_started()]
        outbox.fetch_unpublished.return_value = events
        js = AsyncMock()

        await publish_orchestrator_outbox_events(
            js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )

        assert outbox.mark_published.call_count == 2

    @pytest.mark.asyncio
    async def test_skip_on_empty_outbox(self) -> None:
        outbox = MagicMock()
        outbox.fetch_unpublished.return_value = []
        js = AsyncMock()

        await publish_orchestrator_outbox_events(
            js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )

        js.publish.assert_not_called()
        outbox.mark_published.assert_not_called()

    @pytest.mark.asyncio
    async def test_envelope_has_required_fields(self) -> None:
        outbox = MagicMock()
        event = _make_created()
        outbox.fetch_unpublished.return_value = [event]
        js = AsyncMock()

        await publish_orchestrator_outbox_events(
            js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )

        call_args = js.publish.call_args[0]
        payload = json.loads(call_args[1])
        assert "event_id" in payload
        assert "event_type" in payload
        assert "kind" in payload
        assert "producer" in payload
        assert "aggregate_id" in payload
        assert "occurred_at" in payload
        assert payload["kind"] == "event"
        assert payload["producer"] == "orchestrator"

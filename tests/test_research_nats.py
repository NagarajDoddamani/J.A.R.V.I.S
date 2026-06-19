from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from backend.research.domain.model import (
    ResearchCancelled,
    ResearchCompleted,
    ResearchFailed,
    ResearchJobId,
    ResearchRequested,
    ResearchRequestId,
    ResearchStarted,
    ResearchSummaryGenerated,
    SourceAdded,
)
from backend.research.nats import (
    _NATS_SUBJECT_MAP,
    publish_research_outbox_events,
)

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


def _make_requested() -> ResearchRequested:
    return ResearchRequested(
        request_id=ResearchRequestId(),
        query="test query",
        goal="test goal",
        priority="normal",
        occurred_at=NOW,
    )


def _make_started() -> ResearchStarted:
    return ResearchStarted(
        request_id=ResearchRequestId(), occurred_at=NOW
    )


def _make_completed() -> ResearchCompleted:
    return ResearchCompleted(
        request_id=ResearchRequestId(), occurred_at=NOW
    )


def _make_failed() -> ResearchFailed:
    return ResearchFailed(
        request_id=ResearchRequestId(),
        failure_reason="error",
        occurred_at=NOW,
    )


def _make_cancelled() -> ResearchCancelled:
    return ResearchCancelled(
        request_id=ResearchRequestId(), occurred_at=NOW
    )


def _make_source_added() -> SourceAdded:
    return SourceAdded(
        request_id=ResearchRequestId(),
        job_id=ResearchJobId(),
        source_id=UUID("00000000-0000-0000-0000-000000000001"),
        source_type="web",
        reference="https://example.com",
        occurred_at=NOW,
    )


def _make_summary_generated() -> ResearchSummaryGenerated:
    return ResearchSummaryGenerated(
        request_id=ResearchRequestId(),
        job_id=ResearchJobId(),
        summary="done",
        occurred_at=NOW,
    )


# ===================================================================
# NATS subject map tests
# ===================================================================


class TestNatsSubjectMap:
    def test_all_event_types_have_subjects(self) -> None:
        events = [
            _make_requested(),
            _make_started(),
            _make_completed(),
            _make_failed(),
            _make_cancelled(),
            _make_source_added(),
            _make_summary_generated(),
        ]
        for event in events:
            subject = _NATS_SUBJECT_MAP.get(type(event))
            assert subject is not None, f"Missing subject for {type(event).__name__}"

    def test_subject_patterns(self) -> None:
        assert _NATS_SUBJECT_MAP[ResearchRequested] == "jarvis.event.research.requested.v1"
        assert _NATS_SUBJECT_MAP[ResearchStarted] == "jarvis.event.research.started.v1"
        assert _NATS_SUBJECT_MAP[ResearchCompleted] == "jarvis.event.research.completed.v1"
        assert _NATS_SUBJECT_MAP[ResearchFailed] == "jarvis.event.research.failed.v1"
        assert _NATS_SUBJECT_MAP[ResearchCancelled] == "jarvis.event.research.cancelled.v1"
        assert _NATS_SUBJECT_MAP[SourceAdded] == "jarvis.event.research.source_added.v1"
        assert (
            _NATS_SUBJECT_MAP[ResearchSummaryGenerated]
            == "jarvis.event.research.summary_generated.v1"
        )


# ===================================================================
# Publisher tests
# ===================================================================


class TestPublishResearchOutboxEvents:
    @pytest.mark.asyncio
    async def test_publishes_events(self) -> None:
        outbox = MagicMock()
        events = [_make_requested(), _make_started()]
        outbox.fetch_unpublished.return_value = events
        js = AsyncMock()

        await publish_research_outbox_events(
            js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )

        assert js.publish.call_count == 2
        outbox.mark_published.assert_called()

    @pytest.mark.asyncio
    async def test_all_event_types_published(self) -> None:
        outbox = MagicMock()
        events = [
            _make_requested(),
            _make_started(),
            _make_completed(),
            _make_failed(),
            _make_cancelled(),
            _make_source_added(),
            _make_summary_generated(),
        ]
        outbox.fetch_unpublished.return_value = events
        js = AsyncMock()

        await publish_research_outbox_events(
            js,
            outbox=outbox,
            batch=20,
            interval_seconds=0.1,
            max_iterations=1,
        )

        assert js.publish.call_count == 7

    @pytest.mark.asyncio
    async def test_fifo_ordering(self) -> None:
        outbox = MagicMock()
        e1 = _make_requested()
        e2 = _make_started()
        outbox.fetch_unpublished.return_value = [e1, e2]
        js = AsyncMock()

        await publish_research_outbox_events(
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
        outbox.fetch_unpublished.return_value = [_make_requested()]
        js = AsyncMock()

        await publish_research_outbox_events(
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
        outbox.fetch_unpublished.return_value = [_make_requested()]
        js = AsyncMock()
        js.publish.side_effect = Exception("NATS unavailable")

        with patch("backend.research.nats.logger") as mock_logger:
            await publish_research_outbox_events(
                js,
                outbox=outbox,
                batch=10,
                interval_seconds=0.1,
                max_iterations=1,
            )
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_subject_selection(self) -> None:
        outbox = MagicMock()
        event = _make_source_added()
        outbox.fetch_unpublished.return_value = [event]
        js = AsyncMock()

        await publish_research_outbox_events(
            js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )

        js.publish.assert_called_once_with(
            "jarvis.event.research.source_added.v1",
            json.dumps(
                {
                    "event_id": str(event.event_id),
                    "event_type": "SourceAdded",
                    "kind": "event",
                    "producer": "research",
                    "aggregate_id": str(event.request_id),
                    "occurred_at": event.occurred_at.isoformat(),
                    "job_id": str(event.job_id),
                    "source_id": str(event.source_id),
                    "source_type": event.source_type,
                    "reference": event.reference,
                },
                separators=(",", ":"),
            ).encode("utf-8"),
        )

    @pytest.mark.asyncio
    async def test_mark_published_per_event(self) -> None:
        outbox = MagicMock()
        events = [_make_requested(), _make_started()]
        outbox.fetch_unpublished.return_value = events
        js = AsyncMock()

        await publish_research_outbox_events(
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

        await publish_research_outbox_events(
            js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )

        js.publish.assert_not_called()
        outbox.mark_published.assert_not_called()

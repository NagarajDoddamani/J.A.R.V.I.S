from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.settings.adapters.outbound.clock import SystemClockAdapter
from backend.settings.adapters.outbound.mapper import (
    SettingMapperImpl,
    SettingsOutboxMapperImpl,
    SettingsProfileMapperImpl,
    _infer_type,
)
from backend.settings.adapters.outbound.models import (
    Base,
    SettingModel,
    SettingsOutboxModel,
    SettingsProfileModel,
)
from backend.settings.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemySettingsOutboxAdapter,
    SqlAlchemySettingsRepository,
)
from backend.settings.application.use_cases.dto import (
    PatchSettingsRequest,
)
from backend.settings.application.use_cases.patch_settings import (
    PatchSettingsUseCase,
)
from backend.settings.bootstrap import DEFAULT_REGISTRY
from backend.settings.domain.factory import SettingsProfileFactory
from backend.settings.domain.model import (
    SettingCategory,
    SettingId,
    SettingsReset,
    SettingUpdated,
)
from backend.settings.nats import publish_settings_outbox_events

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
def profile(session):
    factory = SettingsProfileFactory.create(DEFAULT_REGISTRY)
    repo = SqlAlchemySettingsRepository(session)
    repo.save(factory)
    session.commit()
    return factory


@pytest.fixture
def outbox(session):
    return SqlAlchemySettingsOutboxAdapter(session)


@pytest.fixture
def clock():
    return SystemClockAdapter()


@pytest.fixture
def mock_js():
    js = AsyncMock()
    js.publish = AsyncMock()
    return js


def add_outbox_entries(session, count: int = 3):
    """Helper: simulate outbox entries by running patch settings."""
    clock = SystemClockAdapter()
    repo = SqlAlchemySettingsRepository(session)
    outbox = SqlAlchemySettingsOutboxAdapter(session)
    uc = PatchSettingsUseCase(
        repo=repo,
        outbox=outbox,
        clock=clock,
        registry=DEFAULT_REGISTRY,
    )
    for i in range(count):
        uc.execute(
            PatchSettingsRequest(updates={"system.language": f"lang-{i}"})
        )
    session.commit()
    return outbox


class TestPublishSettingsOutboxEvents:
    @pytest.mark.asyncio
    async def test_publishes_all_events(self, session, mock_js) -> None:
        add_outbox_entries(session, count=2)
        outbox = SqlAlchemySettingsOutboxAdapter(session)

        await publish_settings_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        assert mock_js.publish.await_count == 2

    @pytest.mark.asyncio
    async def test_marks_events_published(self, session, mock_js) -> None:
        add_outbox_entries(session, count=1)
        outbox = SqlAlchemySettingsOutboxAdapter(session)

        await publish_settings_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        remaining = outbox.fetch_unpublished()
        assert len(remaining) == 0

    @pytest.mark.asyncio
    async def test_no_events_no_publish(self, session, mock_js) -> None:
        outbox = SqlAlchemySettingsOutboxAdapter(session)

        await publish_settings_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        mock_js.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_respects_limit(self, session, mock_js) -> None:
        add_outbox_entries(session, count=5)

        await publish_settings_outbox_events(
            mock_js,
            outbox=SqlAlchemySettingsOutboxAdapter(session),
            batch=2,
            interval_seconds=0.01,
            max_iterations=1,
        )

        assert mock_js.publish.await_count == 2

    @pytest.mark.asyncio
    async def test_publish_called_with_correct_subject(
        self, session, mock_js
    ) -> None:
        add_outbox_entries(session, count=1)
        outbox = SqlAlchemySettingsOutboxAdapter(session)

        await publish_settings_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject.startswith("jarvis.settings.event.")

    @pytest.mark.asyncio
    async def test_payload_is_json_bytes(
        self, session, mock_js
    ) -> None:
        add_outbox_entries(session, count=1)
        outbox = SqlAlchemySettingsOutboxAdapter(session)

        await publish_settings_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        payload = mock_js.publish.await_args[0][1]
        assert isinstance(payload, bytes)

    @pytest.mark.asyncio
    async def test_payload_contains_envelope_fields(
        self, session, mock_js
    ) -> None:
        add_outbox_entries(session, count=1)
        outbox = SqlAlchemySettingsOutboxAdapter(session)

        await publish_settings_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        import json

        payload = json.loads(mock_js.publish.await_args[0][1])
        assert "event_id" in payload
        assert "event_type" in payload
        assert "kind" in payload
        assert payload["kind"] == "event"
        assert "producer" in payload
        assert payload["producer"] == "settings"

    @pytest.mark.asyncio
    async def test_event_type_setting_updated(
        self, session, mock_js
    ) -> None:
        add_outbox_entries(session, count=1)
        outbox = SqlAlchemySettingsOutboxAdapter(session)

        await publish_settings_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        import json

        payload = json.loads(mock_js.publish.await_args[0][1])
        assert payload["event_type"] == "SETTING_UPDATED"
        assert "key" in payload
        assert "old_value" in payload
        assert "new_value" in payload
        assert "category" in payload

    @pytest.mark.asyncio
    async def test_creates_session_when_no_outbox_provided(
        self, mock_js
    ) -> None:
        with patch("backend.settings.nats.create_session") as mock_create:
            mock_session = MagicMock()
            mock_create.return_value = mock_session

            await publish_settings_outbox_events(
                mock_js,
                batch=10,
                interval_seconds=0.01,
                max_iterations=1,
            )

            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_logs_error_on_exception(self, session, mock_js) -> None:
        mock_js.publish.side_effect = Exception("NATS down")
        add_outbox_entries(session, count=1)
        outbox = SqlAlchemySettingsOutboxAdapter(session)

        with patch("backend.settings.nats.logger.error") as mock_log:
            await publish_settings_outbox_events(
                mock_js,
                outbox=outbox,
                batch=10,
                interval_seconds=0.01,
                max_iterations=1,
            )
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_iterations_zero_runs_indefinitely(
        self, session, mock_js, monkeypatch
    ) -> None:
        add_outbox_entries(session, count=1)
        outbox = SqlAlchemySettingsOutboxAdapter(session)

        async def fake_sleep(_):
            raise asyncio.CancelledError()

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)

        with pytest.raises(asyncio.CancelledError):
            await publish_settings_outbox_events(
                mock_js,
                outbox=outbox,
                batch=10,
                interval_seconds=0.01,
                max_iterations=0,
            )

    @pytest.mark.asyncio
    async def test_handles_reset_events(self, session, mock_js) -> None:
        """Simulate a reset event in the outbox."""
        outbox = SqlAlchemySettingsOutboxAdapter(session)
        event = SettingsReset(
            profile_id=SettingId(),
            previous_count=5,
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_settings_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        mock_js.publish.assert_called_once()
        import json

        payload = json.loads(mock_js.publish.await_args[0][1])
        assert payload["event_type"] == "SETTINGS_RESET"
        assert "previous_count" in payload

    @pytest.mark.asyncio
    async def test_iteration_count_limits(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemySettingsOutboxAdapter(session)

        await publish_settings_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=2,
        )

        # Two iterations should each sleep 0.01 and find nothing
        mock_js.publish.assert_not_called()


class TestPublishSubscription:
    @pytest.mark.asyncio
    async def test_subject_for_setting_updated(self, session, mock_js) -> None:
        add_outbox_entries(session, count=1)
        outbox = SqlAlchemySettingsOutboxAdapter(session)

        await publish_settings_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.settings.event.setting_updated.v1"

    @pytest.mark.asyncio
    async def test_subject_for_settings_reset(self, session, mock_js) -> None:
        outbox = SqlAlchemySettingsOutboxAdapter(session)
        event = SettingsReset(
            profile_id=SettingId(),
            previous_count=0,
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_settings_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.settings.event.settings_reset.v1"

    @pytest.mark.asyncio
    async def test_mark_published_on_single_item(
        self, session, mock_js
    ) -> None:
        add_outbox_entries(session, count=1)
        outbox = SqlAlchemySettingsOutboxAdapter(session)

        await publish_settings_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        remaining = outbox.fetch_unpublished()
        assert len(remaining) == 0

    @pytest.mark.asyncio
    async def test_mark_published_after_commit(
        self, session, mock_js
    ) -> None:
        add_outbox_entries(session, count=2)
        outbox = SqlAlchemySettingsOutboxAdapter(session)

        await publish_settings_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        models = session.query(SettingsOutboxModel).all()
        for m in models:
            assert m.published is True

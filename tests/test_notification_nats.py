from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.notification.adapters.outbound.mapper import (
    NotificationMapperImpl,
)
from backend.notification.adapters.outbound.models import Base
from backend.notification.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyNotificationActionRepository,
    SqlAlchemyNotificationOutboxAdapter,
    SqlAlchemyNotificationRepository,
)
from backend.notification.domain.model import (
    ActionId,
    Notification,
    NotificationAcknowledged,
    NotificationAction,
    NotificationActionInvoked,
    NotificationChannel,
    NotificationCreated,
    NotificationDismissed,
    NotificationExpired,
    NotificationId,
    NotificationMessage,
    NotificationPriority,
    NotificationShown,
    NotificationTarget,
    NotificationTitle,
)
from backend.notification.nats import (
    publish_notification_outbox_events,
)

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
    return SqlAlchemyNotificationOutboxAdapter(session)


@pytest.fixture
def mock_js():
    js = AsyncMock()
    js.publish = AsyncMock()
    return js


@pytest.fixture
def notif_repo(session):
    return SqlAlchemyNotificationRepository(session, mapper=NotificationMapperImpl())


@pytest.fixture
def action_repo(session):
    return SqlAlchemyNotificationActionRepository(session)


def create_notification_in_repo(notif_repo, title="Test") -> str:
    notif = Notification(
        notification_id=NotificationId(),
        title=NotificationTitle(value=title),
        message=NotificationMessage(value="Test message"),
        priority=NotificationPriority.NORMAL,
        channel=NotificationChannel.IN_APP,
        target=NotificationTarget(target_type="user", target_id="user-1"),
    )
    notif_repo.save(notif)
    return str(notif.notification_id)


def add_simple_outbox_entries(session, count: int = 3):
    outbox = SqlAlchemyNotificationOutboxAdapter(session)
    for i in range(count):
        event = NotificationCreated(
            notification_id=NotificationId(),
            title=f"Event {i}",
            message="Test",
            priority="normal",
            channel="in_app",
            target_type="user",
            target_id="user-1",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
    session.commit()
    return outbox


class TestPublishNotificationOutboxEvents:
    @pytest.mark.asyncio
    async def test_publishes_all_events(self, session, mock_js) -> None:
        add_simple_outbox_entries(session, count=2)
        outbox = SqlAlchemyNotificationOutboxAdapter(session)

        await publish_notification_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        assert mock_js.publish.await_count == 2

    @pytest.mark.asyncio
    async def test_marks_events_published(self, session, mock_js) -> None:
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyNotificationOutboxAdapter(session)

        await publish_notification_outbox_events(
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
        outbox = SqlAlchemyNotificationOutboxAdapter(session)

        await publish_notification_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        mock_js.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_respects_limit(self, session, mock_js) -> None:
        add_simple_outbox_entries(session, count=5)
        outbox = SqlAlchemyNotificationOutboxAdapter(session)

        await publish_notification_outbox_events(
            mock_js,
            outbox=outbox,
            batch=2,
            interval_seconds=0.01,
            max_iterations=1,
        )

        assert mock_js.publish.await_count == 2

    @pytest.mark.asyncio
    async def test_publish_called_with_correct_subject(
        self, session, mock_js
    ) -> None:
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyNotificationOutboxAdapter(session)

        await publish_notification_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject.startswith("jarvis.event.notification.")

    @pytest.mark.asyncio
    async def test_payload_is_json_bytes(
        self, session, mock_js
    ) -> None:
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyNotificationOutboxAdapter(session)

        await publish_notification_outbox_events(
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
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyNotificationOutboxAdapter(session)

        await publish_notification_outbox_events(
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
        assert payload["producer"] == "notification"

    @pytest.mark.asyncio
    async def test_notification_created_event_type(
        self, session, mock_js
    ) -> None:
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyNotificationOutboxAdapter(session)

        await publish_notification_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        import json
        payload = json.loads(mock_js.publish.await_args[0][1])
        assert payload["event_type"] == "NOTIFICATION_CREATED"
        assert "title" in payload
        assert "message" in payload
        assert "priority" in payload
        assert "channel" in payload

    @pytest.mark.asyncio
    async def test_notification_action_invoked_event_type(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyNotificationOutboxAdapter(session)
        event = NotificationActionInvoked(
            notification_id=NotificationId(),
            action_id=ActionId(),
            callback_name="test_callback",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_notification_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        import json
        payload = json.loads(mock_js.publish.await_args[0][1])
        assert payload["event_type"] == "NOTIFICATION_ACTION_INVOKED"
        assert payload["callback_name"] == "test_callback"

    @pytest.mark.asyncio
    async def test_subject_for_notification_created(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyNotificationOutboxAdapter(session)
        event = NotificationCreated(
            notification_id=NotificationId(),
            title="Test",
            message="Hello",
            priority="normal",
            channel="in_app",
            target_type="user",
            target_id="user-1",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_notification_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.event.notification.created.v1"

    @pytest.mark.asyncio
    async def test_subject_for_notification_shown(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyNotificationOutboxAdapter(session)
        event = NotificationShown(
            notification_id=NotificationId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_notification_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.event.notification.shown.v1"

    @pytest.mark.asyncio
    async def test_subject_for_notification_acknowledged(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyNotificationOutboxAdapter(session)
        event = NotificationAcknowledged(
            notification_id=NotificationId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_notification_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.event.notification.acknowledged.v1"

    @pytest.mark.asyncio
    async def test_subject_for_notification_dismissed(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyNotificationOutboxAdapter(session)
        event = NotificationDismissed(
            notification_id=NotificationId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_notification_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.event.notification.dismissed.v1"

    @pytest.mark.asyncio
    async def test_subject_for_notification_expired(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyNotificationOutboxAdapter(session)
        event = NotificationExpired(
            notification_id=NotificationId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_notification_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.event.notification.expired.v1"

    @pytest.mark.asyncio
    async def test_subject_for_notification_action_invoked(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyNotificationOutboxAdapter(session)
        event = NotificationActionInvoked(
            notification_id=NotificationId(),
            action_id=ActionId(),
            callback_name="test",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        await publish_notification_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        subject = mock_js.publish.await_args[0][0]
        assert subject == "jarvis.event.notification.action_invoked.v1"

    @pytest.mark.asyncio
    async def test_creates_session_when_no_outbox_provided(
        self, mock_js
    ) -> None:
        with patch("backend.notification.nats.create_session") as mock_create:
            mock_session = MagicMock()
            mock_create.return_value = mock_session

            await publish_notification_outbox_events(
                mock_js,
                batch=10,
                interval_seconds=0.01,
                max_iterations=1,
            )

            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_logs_error_on_exception(self, session, mock_js) -> None:
        mock_js.publish.side_effect = Exception("NATS down")
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyNotificationOutboxAdapter(session)

        with patch("backend.notification.nats.logger.error") as mock_log:
            await publish_notification_outbox_events(
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
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyNotificationOutboxAdapter(session)

        async def fake_sleep(_):
            raise asyncio.CancelledError()

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)

        with pytest.raises(asyncio.CancelledError):
            await publish_notification_outbox_events(
                mock_js,
                outbox=outbox,
                batch=10,
                interval_seconds=0.01,
                max_iterations=0,
            )

    @pytest.mark.asyncio
    async def test_iteration_count_limits(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyNotificationOutboxAdapter(session)

        await publish_notification_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=2,
        )

        mock_js.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_envelope_has_aggregate_id(
        self, session, mock_js
    ) -> None:
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyNotificationOutboxAdapter(session)

        await publish_notification_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        import json
        payload = json.loads(mock_js.publish.await_args[0][1])
        assert "aggregate_id" in payload

    @pytest.mark.asyncio
    async def test_envelope_has_occurred_at(
        self, session, mock_js
    ) -> None:
        add_simple_outbox_entries(session, count=1)
        outbox = SqlAlchemyNotificationOutboxAdapter(session)

        await publish_notification_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        import json
        payload = json.loads(mock_js.publish.await_args[0][1])
        assert "occurred_at" in payload

    @pytest.mark.asyncio
    async def test_mark_published_after_publish(
        self, session, mock_js
    ) -> None:
        add_simple_outbox_entries(session, count=2)
        outbox = SqlAlchemyNotificationOutboxAdapter(session)

        await publish_notification_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        from backend.notification.adapters.outbound.models import NotificationOutboxModel
        models = session.query(NotificationOutboxModel).all()
        for m in models:
            assert m.published_at is not None

    @pytest.mark.asyncio
    async def test_publishes_all_event_types(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyNotificationOutboxAdapter(session)
        now = datetime.now(tz=timezone.utc)
        events = [
            NotificationCreated(NotificationId(), "T", "M", "normal", "in_app", "user", "u1", now),
            NotificationShown(NotificationId(), now),
            NotificationAcknowledged(NotificationId(), now),
            NotificationDismissed(NotificationId(), now),
            NotificationExpired(NotificationId(), now),
            NotificationActionInvoked(NotificationId(), ActionId(), "cb", now),
        ]
        for e in events:
            outbox.append(e)
        session.commit()

        await publish_notification_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        assert mock_js.publish.await_count == 6

    @pytest.mark.asyncio
    async def test_fifo_order_preserved(
        self, session, mock_js
    ) -> None:
        outbox = SqlAlchemyNotificationOutboxAdapter(session)
        now = datetime.now(tz=timezone.utc)
        for i in range(3):
            outbox.append(
                NotificationCreated(
                    notification_id=NotificationId(),
                    title=f"E{i}",
                    message="M",
                    priority="normal",
                    channel="in_app",
                    target_type="user",
                    target_id="u1",
                    occurred_at=now,
                )
            )
        session.commit()

        await publish_notification_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        assert mock_js.publish.await_count == 3

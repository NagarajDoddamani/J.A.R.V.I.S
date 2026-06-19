from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.notification.adapters.outbound.mapper import (
    NotificationActionMapperImpl,
    NotificationMapperImpl,
    NotificationOutboxMapperImpl,
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
    NotificationAction,
    NotificationChannel,
    NotificationId,
    NotificationMessage,
    NotificationPriority,
    NotificationStatus,
    NotificationTarget,
    NotificationTitle,
)


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def engine() -> Iterator[Engine]:
    e = create_engine("sqlite://", echo=False)
    for t in Base.metadata.tables.values():
        t.schema = None
    Base.metadata.create_all(bind=e)
    yield e
    e.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    S = sessionmaker(bind=engine)
    s = S()
    yield s
    s.close()


@pytest.fixture
def notification_mapper() -> NotificationMapperImpl:
    return NotificationMapperImpl()


@pytest.fixture
def action_mapper() -> NotificationActionMapperImpl:
    return NotificationActionMapperImpl()


@pytest.fixture
def outbox_mapper() -> NotificationOutboxMapperImpl:
    return NotificationOutboxMapperImpl()


@pytest.fixture
def notification_repo(
    session: Session,
    notification_mapper: NotificationMapperImpl,
) -> SqlAlchemyNotificationRepository:
    return SqlAlchemyNotificationRepository(
        session=session, mapper=notification_mapper
    )


@pytest.fixture
def action_repo(
    session: Session,
    action_mapper: NotificationActionMapperImpl,
) -> SqlAlchemyNotificationActionRepository:
    return SqlAlchemyNotificationActionRepository(
        session=session, mapper=action_mapper
    )


@pytest.fixture
def outbox_adapter(
    session: Session,
    outbox_mapper: NotificationOutboxMapperImpl,
) -> SqlAlchemyNotificationOutboxAdapter:
    return SqlAlchemyNotificationOutboxAdapter(
        session=session, mapper=outbox_mapper
    )


NOW = datetime.now(tz=timezone.utc)


def _make_notification(
    *,
    title: str = "Test notification",
    message: str = "Test message",
    priority: NotificationPriority = NotificationPriority.NORMAL,
    channel: NotificationChannel = NotificationChannel.IN_APP,
    target_type: str = "user",
    target_id: str = "user-001",
    status: NotificationStatus = NotificationStatus.PENDING,
    expires_at: datetime | None = None,
) -> Notification:
    return Notification(
        notification_id=NotificationId(),
        title=NotificationTitle(value=title),
        message=NotificationMessage(value=message),
        priority=priority,
        channel=channel,
        target=NotificationTarget(target_type=target_type, target_id=target_id),
        status=status,
        created_at=NOW,
        expires_at=expires_at,
    )


# ===================================================================
# Notification repository integration tests
# ===================================================================


class TestNotificationRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        notification_repo: SqlAlchemyNotificationRepository,
    ) -> None:
        notification = _make_notification()
        notification_repo.save(notification)
        found = notification_repo.find_by_id(notification.notification_id)
        assert found is not None
        assert str(found.notification_id) == str(notification.notification_id)
        assert str(found.title) == "Test notification"

    def test_find_by_id_returns_none(
        self,
        notification_repo: SqlAlchemyNotificationRepository,
    ) -> None:
        result = notification_repo.find_by_id(NotificationId())
        assert result is None

    def test_find_by_status(
        self,
        notification_repo: SqlAlchemyNotificationRepository,
    ) -> None:
        n1 = _make_notification(title="N1", status=NotificationStatus.PENDING)
        n2 = _make_notification(title="N2", status=NotificationStatus.SHOWN)
        n3 = _make_notification(title="N3", status=NotificationStatus.PENDING)
        notification_repo.save(n1)
        notification_repo.save(n2)
        notification_repo.save(n3)

        pending = notification_repo.find_by_status(NotificationStatus.PENDING)
        assert len(pending) == 2

        shown = notification_repo.find_by_status(NotificationStatus.SHOWN)
        assert len(shown) == 1

        expired = notification_repo.find_by_status(NotificationStatus.EXPIRED)
        assert len(expired) == 0

    def test_find_by_priority(
        self,
        notification_repo: SqlAlchemyNotificationRepository,
    ) -> None:
        n1 = _make_notification(title="High", priority=NotificationPriority.HIGH)
        n2 = _make_notification(title="Low", priority=NotificationPriority.LOW)
        n3 = _make_notification(title="Normal", priority=NotificationPriority.NORMAL)
        notification_repo.save(n1)
        notification_repo.save(n2)
        notification_repo.save(n3)

        high = notification_repo.find_by_priority(NotificationPriority.HIGH)
        assert len(high) == 1
        assert high[0].title is not None and high[0].title.value == "High"

    def test_find_by_target(
        self,
        notification_repo: SqlAlchemyNotificationRepository,
    ) -> None:
        n1 = _make_notification(
            title="User note", target_type="user", target_id="u-001"
        )
        n2 = _make_notification(
            title="Admin note", target_type="admin", target_id="a-001"
        )
        notification_repo.save(n1)
        notification_repo.save(n2)

        user_results = notification_repo.find_by_target("user", "u-001")
        assert len(user_results) == 1
        assert user_results[0].title is not None and user_results[0].title.value == "User note"

        admin_results = notification_repo.find_by_target("admin", "a-001")
        assert len(admin_results) == 1

        no_results = notification_repo.find_by_target("user", "nonexistent")
        assert len(no_results) == 0

    def test_find_expired_by_status(
        self,
        notification_repo: SqlAlchemyNotificationRepository,
    ) -> None:
        n1 = _make_notification(
            title="Expired status",
            status=NotificationStatus.EXPIRED,
        )
        n2 = _make_notification(title="Still pending")
        notification_repo.save(n1)
        notification_repo.save(n2)

        expired = notification_repo.find_expired()
        assert len(expired) == 1
        assert expired[0].title is not None and expired[0].title.value == "Expired status"

    def test_find_expired_by_date(
        self,
        notification_repo: SqlAlchemyNotificationRepository,
    ) -> None:
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        n1 = _make_notification(
            title="Past expiry",
            status=NotificationStatus.PENDING,
            expires_at=past,
        )
        n2 = _make_notification(title="No expiry")
        notification_repo.save(n1)
        notification_repo.save(n2)

        expired = notification_repo.find_expired()
        assert len(expired) == 1
        assert expired[0].title is not None and expired[0].title.value == "Past expiry"

    def test_count(
        self,
        notification_repo: SqlAlchemyNotificationRepository,
    ) -> None:
        assert notification_repo.count() == 0
        notification_repo.save(_make_notification(title="A"))
        assert notification_repo.count() == 1
        notification_repo.save(_make_notification(title="B"))
        assert notification_repo.count() == 2

    def test_update_semantics(
        self,
        notification_repo: SqlAlchemyNotificationRepository,
    ) -> None:
        notification = _make_notification(title="Original")
        notification_repo.save(notification)
        assert notification_repo.count() == 1

        updated = Notification(
            notification_id=notification.notification_id,
            title=NotificationTitle(value="Updated"),
            message=notification.message,
            priority=notification.priority,
            channel=notification.channel,
            target=notification.target,
            status=NotificationStatus.SHOWN,
            created_at=notification.created_at,
            shown_at=NOW,
        )
        notification_repo.save(updated)

        retrieved = notification_repo.find_by_id(notification.notification_id)
        assert retrieved is not None
        assert str(retrieved.title) == "Updated"
        assert retrieved.status == NotificationStatus.SHOWN
        assert notification_repo.count() == 1

    def test_multiple_notifications(
        self,
        notification_repo: SqlAlchemyNotificationRepository,
    ) -> None:
        for i in range(5):
            notification_repo.save(
                _make_notification(title=f"Notification {i}")
            )
        assert notification_repo.count() == 5

    def test_find_by_target_type_only_not_supported(
        self,
        notification_repo: SqlAlchemyNotificationRepository,
    ) -> None:
        notification_repo.save(
            _make_notification(target_type="user", target_id="u-001")
        )
        notification_repo.save(
            _make_notification(target_type="user", target_id="u-002")
        )
        result = notification_repo.find_by_target("user", "")
        assert len(result) == 0


# ===================================================================
# Action repository integration tests
# ===================================================================


class TestActionRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        action_repo: SqlAlchemyNotificationActionRepository,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        action = NotificationAction(
            action_id=ActionId(),
            notification_id=NotificationId(),
            label="View",
            callback_name="view_action",
            created_at=now,
        )
        action_repo.save(action)

        found = action_repo.find_by_id(action.action_id)
        assert found is not None
        assert str(found.action_id) == str(action.action_id)
        assert found.label == "View"

    def test_find_by_id_returns_none(
        self,
        action_repo: SqlAlchemyNotificationActionRepository,
    ) -> None:
        result = action_repo.find_by_id(ActionId())
        assert result is None

    def test_find_by_notification_id(
        self,
        action_repo: SqlAlchemyNotificationActionRepository,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        nid = NotificationId()
        other_nid = NotificationId()

        action_repo.save(
            NotificationAction(
                action_id=ActionId(),
                notification_id=nid,
                label="A1",
                callback_name="c1",
                created_at=now,
            )
        )
        action_repo.save(
            NotificationAction(
                action_id=ActionId(),
                notification_id=nid,
                label="A2",
                callback_name="c2",
                created_at=now,
            )
        )
        action_repo.save(
            NotificationAction(
                action_id=ActionId(),
                notification_id=other_nid,
                label="Other",
                callback_name="c3",
                created_at=now,
            )
        )

        results = action_repo.find_by_notification_id(nid)
        assert len(results) == 2
        assert results[0].label == "A1"
        assert results[1].label == "A2"

    def test_count(
        self,
        action_repo: SqlAlchemyNotificationActionRepository,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        assert action_repo.count() == 0
        action_repo.save(
            NotificationAction(
                action_id=ActionId(),
                notification_id=NotificationId(),
                label="L",
                callback_name="c",
                created_at=now,
            )
        )
        assert action_repo.count() == 1

    def test_update_semantics(
        self,
        action_repo: SqlAlchemyNotificationActionRepository,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        action = NotificationAction(
            action_id=ActionId(),
            notification_id=NotificationId(),
            label="Original",
            callback_name="orig",
            created_at=now,
        )
        action_repo.save(action)
        assert action_repo.count() == 1

        updated = NotificationAction(
            action_id=action.action_id,
            notification_id=action.notification_id,
            label="Updated",
            callback_name="orig",
            created_at=now,
        )
        action_repo.save(updated)
        assert action_repo.count() == 1

        found = action_repo.find_by_id(action.action_id)
        assert found is not None
        assert found.label == "Updated"

    def test_find_by_notification_id_empty(
        self,
        action_repo: SqlAlchemyNotificationActionRepository,
    ) -> None:
        results = action_repo.find_by_notification_id(NotificationId())
        assert results == []


# ===================================================================
# Outbox adapter integration tests
# ===================================================================


class TestOutboxAdapterIntegration:
    def test_append_and_fetch(
        self,
        outbox_adapter: SqlAlchemyNotificationOutboxAdapter,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        event = NotificationStatus.__len__  # placeholder
        event = __import__(
            "backend.notification.domain.model",
            fromlist=["NotificationCreated"],
        ).NotificationCreated(
            notification_id=NotificationId(),
            title="Test",
            message="Msg",
            priority="normal",
            channel="in_app",
            target_type="user",
            target_id="u-001",
            occurred_at=now,
        )
        outbox_adapter.append(event)

        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 1
        assert type(unpublished[0]).__name__ == "NotificationCreated"

    def test_fifo_ordering(
        self,
        outbox_adapter: SqlAlchemyNotificationOutboxAdapter,
    ) -> None:
        nid = NotificationId()
        t1 = datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 2, 0, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 1, 1, 3, 0, 0, tzinfo=timezone.utc)

        from backend.notification.domain.model import (
            NotificationShown,
        )
        outbox_adapter.append(NotificationShown(notification_id=nid, occurred_at=t1))
        outbox_adapter.append(NotificationShown(notification_id=nid, occurred_at=t2))
        outbox_adapter.append(NotificationShown(notification_id=nid, occurred_at=t3))

        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 3
        types = [e.__class__.__name__ for e in unpublished]
        assert types == ["NotificationShown", "NotificationShown", "NotificationShown"]

    def test_mark_published(
        self,
        outbox_adapter: SqlAlchemyNotificationOutboxAdapter,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        nid = NotificationId()
        from backend.notification.domain.model import (
            NotificationShown,
        )
        event = NotificationShown(notification_id=nid, occurred_at=now)
        outbox_adapter.append(event)

        unpublished_before = outbox_adapter.fetch_unpublished()
        assert len(unpublished_before) == 1

        outbox_adapter.mark_published(str(unpublished_before[0].event_id))

        unpublished_after = outbox_adapter.fetch_unpublished()
        assert len(unpublished_after) == 0

    def test_mark_published_idempotent(
        self,
        outbox_adapter: SqlAlchemyNotificationOutboxAdapter,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        nid = NotificationId()
        from backend.notification.domain.model import (
            NotificationShown,
        )
        outbox_adapter.append(NotificationShown(notification_id=nid, occurred_at=now))
        fetched = outbox_adapter.fetch_unpublished()
        outbox_adapter.mark_published(str(fetched[0].event_id))
        outbox_adapter.mark_published(str(fetched[0].event_id))

        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 0

    def test_fetch_unpublished_limit(
        self,
        outbox_adapter: SqlAlchemyNotificationOutboxAdapter,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        nid = NotificationId()
        from backend.notification.domain.model import (
            NotificationShown,
        )
        for _ in range(5):
            outbox_adapter.append(NotificationShown(notification_id=nid, occurred_at=now))

        limited = outbox_adapter.fetch_unpublished(limit=3)
        assert len(limited) == 3

        all_events = outbox_adapter.fetch_unpublished(limit=100)
        assert len(all_events) == 5

    def test_partial_mark(
        self,
        outbox_adapter: SqlAlchemyNotificationOutboxAdapter,
    ) -> None:
        nid1 = NotificationId()
        nid2 = NotificationId()
        now = datetime.now(tz=timezone.utc)
        from backend.notification.domain.model import (
            NotificationShown,
        )
        outbox_adapter.append(NotificationShown(notification_id=nid1, occurred_at=now))
        outbox_adapter.append(NotificationShown(notification_id=nid2, occurred_at=now))

        unpublished = outbox_adapter.fetch_unpublished()
        outbox_adapter.mark_published(str(unpublished[0].event_id))

        remaining = outbox_adapter.fetch_unpublished()
        assert len(remaining) == 1
        assert remaining[0].notification_id == nid2

    def test_multiple_event_types(
        self,
        outbox_adapter: SqlAlchemyNotificationOutboxAdapter,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        nid = NotificationId()
        from backend.notification.domain.model import (
            NotificationAcknowledged,
            NotificationCreated,
            NotificationDismissed,
            NotificationExpired,
            NotificationShown,
        )
        outbox_adapter.append(
            NotificationCreated(
                notification_id=nid, title="T", message="M", priority="normal",
                channel="in_app", target_type="user", target_id="u-001",
                occurred_at=now,
            )
        )
        outbox_adapter.append(NotificationShown(notification_id=nid, occurred_at=now))
        outbox_adapter.append(NotificationAcknowledged(notification_id=nid, occurred_at=now))
        outbox_adapter.append(NotificationDismissed(notification_id=nid, occurred_at=now))
        outbox_adapter.append(NotificationExpired(notification_id=nid, occurred_at=now))

        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 5
        types = [type(e).__name__ for e in unpublished]
        assert types == [
            "NotificationCreated",
            "NotificationShown",
            "NotificationAcknowledged",
            "NotificationDismissed",
            "NotificationExpired",
        ]


# ===================================================================
# Integration: Full persistence lifecycle
# ===================================================================


class TestFullPersistenceLifecycle:
    def test_notification_save_and_state_transition(
        self,
        notification_repo: SqlAlchemyNotificationRepository,
        outbox_adapter: SqlAlchemyNotificationOutboxAdapter,
    ) -> None:
        notification = _make_notification(title="Lifecycle test")

        # Save
        notification_repo.save(notification)
        assert notification_repo.count() == 1

        # Transition: show
        shown = Notification(
            notification_id=notification.notification_id,
            title=notification.title,
            message=notification.message,
            priority=notification.priority,
            channel=notification.channel,
            target=notification.target,
            status=NotificationStatus.SHOWN,
            created_at=notification.created_at,
            shown_at=NOW,
        )
        notification_repo.save(shown)
        found = notification_repo.find_by_id(notification.notification_id)
        assert found is not None
        assert found.status == NotificationStatus.SHOWN

        # Outbox
        from backend.notification.domain.model import NotificationShown
        outbox_adapter.append(
            NotificationShown(notification_id=notification.notification_id, occurred_at=NOW)
        )
        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 1

    def test_notification_with_expiry(
        self,
        notification_repo: SqlAlchemyNotificationRepository,
    ) -> None:
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        notification = _make_notification(
            title="With expiry",
            expires_at=future,
        )
        notification_repo.save(notification)

        found = notification_repo.find_by_id(notification.notification_id)
        assert found is not None
        assert found.expires_at is not None
        assert found.expires_at.year == 2099

    def test_multiple_notifications_filter_by_target(
        self,
        notification_repo: SqlAlchemyNotificationRepository,
    ) -> None:
        notification_repo.save(
            _make_notification(
                title="User1 high",
                target_type="user",
                target_id="u-001",
                priority=NotificationPriority.HIGH,
            )
        )
        notification_repo.save(
            _make_notification(
                title="User1 low",
                target_type="user",
                target_id="u-001",
                priority=NotificationPriority.LOW,
            )
        )
        notification_repo.save(
            _make_notification(
                title="User2 normal",
                target_type="user",
                target_id="u-002",
            )
        )

        user1 = notification_repo.find_by_target("user", "u-001")
        assert len(user1) == 2

        user2 = notification_repo.find_by_target("user", "u-002")
        assert len(user2) == 1

        high = notification_repo.find_by_priority(NotificationPriority.HIGH)
        assert len(high) == 1

    def test_action_and_notification_roundtrip(
        self,
        notification_repo: SqlAlchemyNotificationRepository,
        action_repo: SqlAlchemyNotificationActionRepository,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        notification = _make_notification(title="With action")
        notification_repo.save(notification)

        action = NotificationAction(
            action_id=ActionId(),
            notification_id=notification.notification_id,
            label="Click me",
            callback_name="click_me",
            created_at=now,
        )
        action_repo.save(action)

        found_action = action_repo.find_by_id(action.action_id)
        assert found_action is not None
        assert found_action.label == "Click me"
        assert found_action.notification_id is not None
        assert str(found_action.notification_id) == str(notification.notification_id)

        actions_for_notification = action_repo.find_by_notification_id(
            notification.notification_id
        )
        assert len(actions_for_notification) == 1
        assert actions_for_notification[0].label == "Click me"

    def test_outbox_lifecycle(
        self,
        outbox_adapter: SqlAlchemyNotificationOutboxAdapter,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        nid = NotificationId()
        from backend.notification.domain.model import (
            NotificationCreated,
            NotificationShown,
        )

        # Append events
        created = NotificationCreated(
            notification_id=nid, title="T", message="M", priority="normal",
            channel="in_app", target_type="user", target_id="u-001",
            occurred_at=now,
        )
        outbox_adapter.append(created)
        outbox_adapter.append(NotificationShown(notification_id=nid, occurred_at=now))

        before = outbox_adapter.fetch_unpublished()
        assert len(before) == 2

        # Mark both as published (each event has its own event_id)
        outbox_adapter.mark_published(str(before[0].event_id))
        outbox_adapter.mark_published(str(before[1].event_id))

        after = outbox_adapter.fetch_unpublished()
        assert len(after) == 0

        # Append another
        outbox_adapter.append(
            NotificationShown(notification_id=NotificationId(), occurred_at=now)
        )
        assert len(outbox_adapter.fetch_unpublished()) == 1

    def test_expired_notification_query(
        self,
        notification_repo: SqlAlchemyNotificationRepository,
    ) -> None:
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        notification_repo.save(
            _make_notification(
                title="Expired by status",
                status=NotificationStatus.EXPIRED,
            )
        )
        notification_repo.save(
            _make_notification(
                title="Expired by date",
                expires_at=past,
            )
        )
        notification_repo.save(
            _make_notification(title="Active"),
        )
        notification_repo.save(
            _make_notification(
                title="Future expiry",
                expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            )
        )

        expired = notification_repo.find_expired()
        assert len(expired) == 2
        titles = {str(e.title) for e in expired if e.title}
        assert titles == {"Expired by status", "Expired by date"}

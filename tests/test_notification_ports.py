from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import UUID

import pytest

from backend.notification.application.ports.clock import NotificationClockPort
from backend.notification.application.ports.id_generator import NotificationIdGeneratorPort
from backend.notification.application.ports.outbox import (
    NotificationOutboxEvent,
    NotificationOutboxPort,
)
from backend.notification.application.ports.repository import (
    NotificationActionRepositoryPort,
    NotificationRepositoryPort,
)
from backend.notification.domain.model import (
    ActionId,
    ExpirationPolicy,
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
    NotificationStatus,
    NotificationTarget,
    NotificationTitle,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_target(
    target_type: str = "user", target_id: str = "user-123"
) -> NotificationTarget:
    return NotificationTarget(target_type=target_type, target_id=target_id)


def _make_notification(
    *,
    notification_id: NotificationId | None = None,
    title: str = "Test Notification",
    message: str = "This is a test message",
    priority: NotificationPriority = NotificationPriority.NORMAL,
    channel: NotificationChannel = NotificationChannel.IN_APP,
    status: NotificationStatus = NotificationStatus.PENDING,
    target: NotificationTarget | None = None,
    expires_at: datetime | None = None,
    shown_at: datetime | None = None,
    acknowledged_at: datetime | None = None,
    dismissed_at: datetime | None = None,
) -> Notification:
    now = datetime.now(tz=timezone.utc)
    t = target or _make_target()
    return Notification(
        notification_id=notification_id or NotificationId(),
        title=NotificationTitle(value=title),
        message=NotificationMessage(value=message),
        priority=priority,
        channel=channel,
        target=t,
        status=status,
        created_at=now,
        expires_at=expires_at,
        shown_at=shown_at,
        acknowledged_at=acknowledged_at,
        dismissed_at=dismissed_at,
    )


def _make_action(
    *,
    action_id: ActionId | None = None,
    notification_id: NotificationId | None = None,
    label: str = "Mark Read",
    callback_name: str = "mark_read",
) -> NotificationAction:
    return NotificationAction(
        action_id=action_id or ActionId(),
        notification_id=notification_id or NotificationId(),
        label=label,
        callback_name=callback_name,
    )


_now = datetime.now(tz=timezone.utc)


def _make_created_event() -> NotificationCreated:
    return NotificationCreated(
        notification_id=NotificationId(),
        title="Test",
        message="Body",
        priority="normal",
        channel="in_app",
        target_type="user",
        target_id="u-1",
        occurred_at=_now,
    )


def _make_shown_event() -> NotificationShown:
    return NotificationShown(
        notification_id=NotificationId(),
        occurred_at=_now,
    )


# ---------------------------------------------------------------------------
# NotificationRepositoryPort Stub
# ---------------------------------------------------------------------------


class StubNotificationRepository:
    """Minimal stub conforming to NotificationRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, Notification] = {}

    def save(self, notification: Notification) -> None:
        key = str(notification.notification_id)
        self._store[key] = notification

    def find_by_id(self, notification_id: NotificationId) -> Notification | None:
        return self._store.get(str(notification_id))

    def find_by_status(self, status: NotificationStatus) -> list[Notification]:
        return [n for n in self._store.values() if n.status == status]

    def find_by_priority(self, priority: NotificationPriority) -> list[Notification]:
        return [n for n in self._store.values() if n.priority == priority]

    def find_by_target(self, target_type: str, target_id: str) -> list[Notification]:
        return [
            n
            for n in self._store.values()
            if n.target is not None
            and n.target.target_type == target_type
            and n.target.target_id == target_id
        ]

    def find_expired(self) -> list[Notification]:
        now = datetime.now(tz=timezone.utc)
        return [
            n
            for n in self._store.values()
            if n.status == NotificationStatus.EXPIRED
            or (n.expires_at is not None and n.expires_at < now)
        ]

    def count(self) -> int:
        return len(self._store)


class TestNotificationRepositoryPort:
    """Contract tests for NotificationRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubNotificationRepository:
        return StubNotificationRepository()

    def test_save_and_find_by_id(self, repo: StubNotificationRepository) -> None:
        notification = _make_notification()
        repo.save(notification)
        found = repo.find_by_id(notification.notification_id)
        assert found is not None
        assert found.notification_id == notification.notification_id

    def test_find_by_id_returns_none(self, repo: StubNotificationRepository) -> None:
        missing_id = NotificationId()
        assert repo.find_by_id(missing_id) is None

    def test_find_by_status(self, repo: StubNotificationRepository) -> None:
        pending = _make_notification(status=NotificationStatus.PENDING)
        shown = _make_notification(status=NotificationStatus.SHOWN)
        repo.save(pending)
        repo.save(shown)

        results = repo.find_by_status(NotificationStatus.PENDING)
        assert len(results) == 1
        assert results[0].status == NotificationStatus.PENDING

    def test_find_by_status_empty(self, repo: StubNotificationRepository) -> None:
        results = repo.find_by_status(NotificationStatus.EXPIRED)
        assert results == []

    def test_find_by_priority(self, repo: StubNotificationRepository) -> None:
        high = _make_notification(priority=NotificationPriority.HIGH)
        normal = _make_notification(priority=NotificationPriority.NORMAL)
        repo.save(high)
        repo.save(normal)

        results = repo.find_by_priority(NotificationPriority.HIGH)
        assert len(results) == 1
        assert results[0].priority == NotificationPriority.HIGH

    def test_find_by_priority_empty(self, repo: StubNotificationRepository) -> None:
        results = repo.find_by_priority(NotificationPriority.CRITICAL)
        assert results == []

    def test_find_by_target(self, repo: StubNotificationRepository) -> None:
        n1 = _make_notification(
            target=NotificationTarget(target_type="user", target_id="u-1"),
        )
        n2 = _make_notification(
            target=NotificationTarget(target_type="user", target_id="u-1"),
        )
        n3 = _make_notification(
            target=NotificationTarget(target_type="admin", target_id="a-1"),
        )
        repo.save(n1)
        repo.save(n2)
        repo.save(n3)

        results = repo.find_by_target("user", "u-1")
        assert len(results) == 2
        assert all(r.target is not None and r.target.target_id == "u-1" for r in results)

    def test_find_by_target_empty(self, repo: StubNotificationRepository) -> None:
        results = repo.find_by_target("user", "nonexistent")
        assert results == []

    def test_find_expired_by_status(self, repo: StubNotificationRepository) -> None:
        expired = _make_notification(status=NotificationStatus.EXPIRED)
        pending = _make_notification(status=NotificationStatus.PENDING)
        repo.save(expired)
        repo.save(pending)

        results = repo.find_expired()
        assert len(results) == 1
        assert results[0].status == NotificationStatus.EXPIRED

    def test_find_expired_by_date(self, repo: StubNotificationRepository) -> None:
        past = datetime.now(tz=timezone.utc) - timedelta(days=1)
        expired = _make_notification(
            status=NotificationStatus.PENDING, expires_at=past,
        )
        repo.save(expired)

        results = repo.find_expired()
        assert len(results) == 1

    def test_find_expired_excludes_future(self, repo: StubNotificationRepository) -> None:
        future = datetime.now(tz=timezone.utc) + timedelta(days=1)
        not_expired = _make_notification(expires_at=future)
        repo.save(not_expired)
        results = repo.find_expired()
        assert results == []

    def test_find_expired_empty(self, repo: StubNotificationRepository) -> None:
        assert repo.find_expired() == []

    def test_count(self, repo: StubNotificationRepository) -> None:
        assert repo.count() == 0
        repo.save(_make_notification())
        assert repo.count() == 1
        repo.save(_make_notification())
        assert repo.count() == 2

    def test_empty_repo_count(self, repo: StubNotificationRepository) -> None:
        assert repo.count() == 0

    def test_save_update_semantics(self, repo: StubNotificationRepository) -> None:
        n = _make_notification(title="Original")
        repo.save(n)
        found = repo.find_by_id(n.notification_id)
        assert found is not None
        assert found.title is not None
        assert found.title.value == "Original"

        updated = _make_notification(
            notification_id=n.notification_id,
            title="Updated",
        )
        repo.save(updated)
        found = repo.find_by_id(n.notification_id)
        assert found is not None
        assert found.title is not None
        assert found.title.value == "Updated"

    def test_find_by_status_multiple(self, repo: StubNotificationRepository) -> None:
        for _ in range(3):
            repo.save(_make_notification(status=NotificationStatus.PENDING))
        for _ in range(2):
            repo.save(_make_notification(status=NotificationStatus.SHOWN))

        pending = repo.find_by_status(NotificationStatus.PENDING)
        shown = repo.find_by_status(NotificationStatus.SHOWN)
        assert len(pending) == 3
        assert len(shown) == 2

    def test_find_by_priority_multiple(self, repo: StubNotificationRepository) -> None:
        for _ in range(4):
            repo.save(_make_notification(priority=NotificationPriority.LOW))
        results = repo.find_by_priority(NotificationPriority.LOW)
        assert len(results) == 4

    def test_find_by_target_different_types(self, repo: StubNotificationRepository) -> None:
        repo.save(_make_notification(
            target=NotificationTarget(target_type="user", target_id="u-1"),
        ))
        repo.save(_make_notification(
            target=NotificationTarget(target_type="admin", target_id="a-1"),
        ))

        users = repo.find_by_target("user", "u-1")
        admins = repo.find_by_target("admin", "a-1")
        assert len(users) == 1
        assert len(admins) == 1


# ---------------------------------------------------------------------------
# NotificationActionRepositoryPort Stub
# ---------------------------------------------------------------------------


class StubNotificationActionRepository:
    """Minimal stub conforming to NotificationActionRepositoryPort."""

    def __init__(self) -> None:
        self._store: dict[str, NotificationAction] = {}

    def save(self, action: NotificationAction) -> None:
        key = str(action.action_id)
        self._store[key] = action

    def find_by_id(self, action_id: ActionId) -> NotificationAction | None:
        return self._store.get(str(action_id))

    def find_by_notification_id(
        self, notification_id: NotificationId
    ) -> list[NotificationAction]:
        return [
            a
            for a in self._store.values()
            if a.notification_id == notification_id
        ]

    def count(self) -> int:
        return len(self._store)


class TestNotificationActionRepositoryPort:
    """Contract tests for NotificationActionRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubNotificationActionRepository:
        return StubNotificationActionRepository()

    def test_save_and_find_by_id(self, repo: StubNotificationActionRepository) -> None:
        action = _make_action()
        repo.save(action)
        found = repo.find_by_id(action.action_id)
        assert found is not None
        assert found.action_id == action.action_id

    def test_find_by_id_returns_none(self, repo: StubNotificationActionRepository) -> None:
        missing_id = ActionId()
        assert repo.find_by_id(missing_id) is None

    def test_find_by_notification_id(self, repo: StubNotificationActionRepository) -> None:
        nid = NotificationId()
        a1 = _make_action(notification_id=nid, label="Read")
        a2 = _make_action(notification_id=nid, label="Archive")
        a3 = _make_action(notification_id=NotificationId(), label="Other")
        repo.save(a1)
        repo.save(a2)
        repo.save(a3)

        results = repo.find_by_notification_id(nid)
        assert len(results) == 2
        assert all(a.notification_id == nid for a in results)

    def test_find_by_notification_id_empty(self, repo: StubNotificationActionRepository) -> None:
        results = repo.find_by_notification_id(NotificationId())
        assert results == []

    def test_count(self, repo: StubNotificationActionRepository) -> None:
        assert repo.count() == 0
        repo.save(_make_action())
        assert repo.count() == 1
        repo.save(_make_action())
        assert repo.count() == 2

    def test_empty_repo_count(self, repo: StubNotificationActionRepository) -> None:
        assert repo.count() == 0

    def test_save_update_semantics(self, repo: StubNotificationActionRepository) -> None:
        action = _make_action(label="Original")
        repo.save(action)
        found = repo.find_by_id(action.action_id)
        assert found is not None
        assert found.label == "Original"

        updated = _make_action(
            action_id=action.action_id,
            label="Updated",
        )
        repo.save(updated)
        found = repo.find_by_id(action.action_id)
        assert found is not None
        assert found.label == "Updated"

    def test_multiple_actions_same_notification(
        self, repo: StubNotificationActionRepository
    ) -> None:
        nid = NotificationId()
        for label in ["A", "B", "C"]:
            repo.save(_make_action(notification_id=nid, label=label))
        results = repo.find_by_notification_id(nid)
        assert len(results) == 3

    def test_actions_different_notifications(
        self, repo: StubNotificationActionRepository
    ) -> None:
        repo.save(_make_action(notification_id=NotificationId()))
        repo.save(_make_action(notification_id=NotificationId()))
        assert repo.count() == 2


# ---------------------------------------------------------------------------
# NotificationOutboxPort Stub
# ---------------------------------------------------------------------------


class StubNotificationOutbox:
    """Minimal stub conforming to NotificationOutboxPort."""

    def __init__(self) -> None:
        self._events: list[NotificationOutboxEvent] = []
        self._published: set[str] = set()

    def append(self, event: NotificationOutboxEvent) -> None:
        self._events.append(event)

    def fetch_unpublished(
        self, limit: int = 100
    ) -> list[NotificationOutboxEvent]:
        results = [
            e
            for i, e in enumerate(self._events)
            if self._event_key(e, i) not in self._published
        ]
        return results[:limit]

    def mark_published(self, notification_id: str) -> None:
        self._published.add(notification_id)

    @staticmethod
    def _event_key(event: NotificationOutboxEvent, index: int) -> str:
        if hasattr(event, "notification_id"):
            return f"notification:{event.notification_id}"
        return f"index:{index}"


class TestNotificationOutboxPort:
    """Contract tests for NotificationOutboxPort."""

    @pytest.fixture
    def outbox(self) -> StubNotificationOutbox:
        return StubNotificationOutbox()

    def test_append_and_fetch(self, outbox: StubNotificationOutbox) -> None:
        event = _make_created_event()
        outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert unpublished[0].notification_id == event.notification_id

    def test_mark_published_excludes(self, outbox: StubNotificationOutbox) -> None:
        event = _make_created_event()
        outbox.append(event)
        outbox.mark_published(f"notification:{event.notification_id}")
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 0

    def test_fetch_respects_limit(self, outbox: StubNotificationOutbox) -> None:
        for _ in range(10):
            outbox.append(_make_created_event())
        fetched = outbox.fetch_unpublished(limit=3)
        assert len(fetched) == 3

    def test_fetch_default_limit(self, outbox: StubNotificationOutbox) -> None:
        for _ in range(200):
            outbox.append(_make_created_event())
        fetched = outbox.fetch_unpublished()
        assert len(fetched) == 100

    def test_fifo_ordering(self, outbox: StubNotificationOutbox) -> None:
        ids = [NotificationId() for _ in range(5)]
        for nid in ids:
            outbox.append(
                NotificationCreated(
                    notification_id=nid,
                    title="Test",
                    message="Body",
                    priority="normal",
                    channel="in_app",
                    target_type="user",
                    target_id="u-1",
                    occurred_at=_now,
                )
            )
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 5
        for i, e in enumerate(unpublished):
            assert e.notification_id == ids[i]

    def test_idempotent_mark_published(self, outbox: StubNotificationOutbox) -> None:
        event = _make_created_event()
        outbox.append(event)
        key = f"notification:{event.notification_id}"
        outbox.mark_published(key)
        outbox.mark_published(key)
        outbox.mark_published(key)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 0

    def test_partial_publish(self, outbox: StubNotificationOutbox) -> None:
        events = [_make_created_event() for _ in range(5)]
        for e in events:
            outbox.append(e)
        outbox.mark_published(f"notification:{events[0].notification_id}")
        outbox.mark_published(f"notification:{events[2].notification_id}")

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 3

    def test_fetch_unpublished_empty(self, outbox: StubNotificationOutbox) -> None:
        assert outbox.fetch_unpublished() == []

    def test_shown_event_outbox(self, outbox: StubNotificationOutbox) -> None:
        event = _make_shown_event()
        outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], NotificationShown)

    def test_multiple_event_types(self, outbox: StubNotificationOutbox) -> None:
        outbox.append(_make_created_event())
        outbox.append(_make_shown_event())
        assert len(outbox.fetch_unpublished()) == 2


# ---------------------------------------------------------------------------
# NotificationClockPort Stubs + Tests
# ---------------------------------------------------------------------------


class SystemClockStub:
    """Returns real system time — conforms to NotificationClockPort."""

    def now(self) -> datetime:
        return datetime.now(tz=timezone.utc)


class FixedClock:
    """Returns a fixed time — conforms to NotificationClockPort."""

    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        return self._fixed


class TestNotificationClockPort:
    """Contract tests for NotificationClockPort."""

    def test_system_clock_returns_utc(self) -> None:
        clock: NotificationClockPort = SystemClockStub()
        result = clock.now()
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result).total_seconds() == 0.0

    def test_fixed_clock_returns_configured_time(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        clock: NotificationClockPort = FixedClock(dt)
        assert clock.now() == dt

    def test_fixed_clock_is_deterministic(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        clock: NotificationClockPort = FixedClock(dt)
        assert clock.now() == clock.now() == dt

    def test_clock_protocol_conformance(self) -> None:
        def use_clock(c: NotificationClockPort) -> datetime:
            return c.now()

        assert use_clock(SystemClockStub()) is not None
        assert use_clock(
            FixedClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
        ) is not None

    def test_fixed_clock_accepts_naive_datetime(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0)
        clock: NotificationClockPort = FixedClock(dt)
        result = clock.now()
        assert result.tzinfo is None

    def test_system_clock_consistent_type(self) -> None:
        clock: NotificationClockPort = SystemClockStub()
        result = clock.now()
        assert isinstance(result, datetime)


# ---------------------------------------------------------------------------
# NotificationIdGeneratorPort Stubs + Tests
# ---------------------------------------------------------------------------


class UuidNotificationIdGeneratorStub:
    """Generates UUID-based IDs — conforms to NotificationIdGeneratorPort."""

    def generate_notification_id(self) -> NotificationId:
        return NotificationId()

    def generate_action_id(self) -> ActionId:
        return ActionId()


class FixedNotificationIdGenerator:
    """Generates IDs with deterministic counter — conforms to NotificationIdGeneratorPort."""

    def __init__(self) -> None:
        self._calls: list[str] = []

    def generate_notification_id(self) -> NotificationId:
        self._calls.append("notification")
        return NotificationId()

    def generate_action_id(self) -> ActionId:
        self._calls.append("action")
        return ActionId()

    @property
    def call_count(self) -> int:
        return len(self._calls)

    @property
    def last_call(self) -> str | None:
        return self._calls[-1] if self._calls else None


class TestNotificationIdGeneratorPort:
    """Contract tests for NotificationIdGeneratorPort."""

    def test_notification_id_returns_notification_id(self) -> None:
        gen: NotificationIdGeneratorPort = UuidNotificationIdGeneratorStub()
        result = gen.generate_notification_id()
        assert isinstance(result, NotificationId)
        assert isinstance(result.value, UUID)

    def test_action_id_returns_action_id(self) -> None:
        gen: NotificationIdGeneratorPort = UuidNotificationIdGeneratorStub()
        result = gen.generate_action_id()
        assert isinstance(result, ActionId)
        assert isinstance(result.value, UUID)

    def test_uuid_generator_unique_notification_ids(self) -> None:
        gen: NotificationIdGeneratorPort = UuidNotificationIdGeneratorStub()
        ids = {gen.generate_notification_id() for _ in range(100)}
        assert len(ids) == 100

    def test_uuid_generator_unique_action_ids(self) -> None:
        gen: NotificationIdGeneratorPort = UuidNotificationIdGeneratorStub()
        ids = {gen.generate_action_id() for _ in range(100)}
        assert len(ids) == 100

    def test_fixed_generator_tracks_calls(self) -> None:
        gen: NotificationIdGeneratorPort = FixedNotificationIdGenerator()
        assert gen.call_count == 0

        gen.generate_notification_id()
        assert gen.call_count == 1
        assert gen.last_call == "notification"

        gen.generate_action_id()
        assert gen.call_count == 2
        assert gen.last_call == "action"

    def test_generator_protocol_conformance(self) -> None:
        def use_generator(
            g: NotificationIdGeneratorPort,
        ) -> tuple[NotificationId, ActionId]:
            return g.generate_notification_id(), g.generate_action_id()

        nid, aid = use_generator(UuidNotificationIdGeneratorStub())
        assert isinstance(nid, NotificationId)
        assert isinstance(aid, ActionId)

        nid2, aid2 = use_generator(FixedNotificationIdGenerator())
        assert isinstance(nid2, NotificationId)
        assert isinstance(aid2, ActionId)

    def test_notification_and_action_ids_distinct(self) -> None:
        gen: NotificationIdGeneratorPort = UuidNotificationIdGeneratorStub()
        nid = gen.generate_notification_id()
        aid = gen.generate_action_id()
        assert isinstance(nid, NotificationId)
        assert isinstance(aid, ActionId)


# ---------------------------------------------------------------------------
# Port method signature cross-verification
# ---------------------------------------------------------------------------


class TestMethodSignatures:
    """Verify that each port method signature matches expectations."""

    def test_notification_repo_signatures(self) -> None:
        import inspect

        methods = {
            "save": {"notification": Notification},
            "find_by_id": {"notification_id": NotificationId, "return": Notification | None},
            "find_by_status": {"status": NotificationStatus, "return": list},
            "find_by_priority": {"priority": NotificationPriority, "return": list},
            "find_by_target": {"target_type": str, "target_id": str, "return": list},
            "find_expired": {"return": list},
            "count": {"return": int},
        }
        stub = StubNotificationRepository()
        for method_name, expected_params in methods.items():
            method = getattr(stub, method_name)
            sig = inspect.signature(method)
            for param_name in expected_params:
                if param_name == "return":
                    continue
                assert param_name in sig.parameters, (
                    f"{method_name} missing parameter {param_name!r}"
                )

    def test_action_repo_signatures(self) -> None:
        methods = [
            "save", "find_by_id", "find_by_notification_id", "count",
        ]
        for m in methods:
            assert hasattr(StubNotificationActionRepository(), m)

    def test_outbox_signatures(self) -> None:
        methods = ["append", "fetch_unpublished", "mark_published"]
        for m in methods:
            assert hasattr(StubNotificationOutbox(), m)

    def test_clock_signature(self) -> None:
        assert hasattr(SystemClockStub(), "now")
        assert hasattr(FixedClock(datetime.now(tz=timezone.utc)), "now")

    def test_id_generator_signatures(self) -> None:
        assert hasattr(UuidNotificationIdGeneratorStub(), "generate_notification_id")
        assert hasattr(UuidNotificationIdGeneratorStub(), "generate_action_id")
        assert hasattr(FixedNotificationIdGenerator(), "generate_notification_id")
        assert hasattr(FixedNotificationIdGenerator(), "generate_action_id")

    def test_notification_repo_method_count(self) -> None:
        port_methods = {
            m for m in dir(NotificationRepositoryPort) if not m.startswith("_")
        }
        assert port_methods == {
            "save",
            "find_by_id",
            "find_by_status",
            "find_by_priority",
            "find_by_target",
            "find_expired",
            "count",
        }

    def test_action_repo_method_count(self) -> None:
        port_methods = {
            m for m in dir(NotificationActionRepositoryPort) if not m.startswith("_")
        }
        assert port_methods == {
            "save",
            "find_by_id",
            "find_by_notification_id",
            "count",
        }

    def test_outbox_method_count(self) -> None:
        port_methods = {
            m for m in dir(NotificationOutboxPort) if not m.startswith("_")
        }
        assert port_methods == {"append", "fetch_unpublished", "mark_published"}

    def test_clock_method_count(self) -> None:
        port_methods = {
            m for m in dir(NotificationClockPort) if not m.startswith("_")
        }
        assert port_methods == {"now"}

    def test_id_generator_method_count(self) -> None:
        port_methods = {
            m for m in dir(NotificationIdGeneratorPort) if not m.startswith("_")
        }
        assert port_methods == {"generate_notification_id", "generate_action_id"}

    def test_notification_repo_nullable_return(self) -> None:
        stub = StubNotificationRepository()
        result = stub.find_by_id(NotificationId())
        assert result is None

    def test_action_repo_nullable_return(self) -> None:
        stub = StubNotificationActionRepository()
        result = stub.find_by_id(ActionId())
        assert result is None

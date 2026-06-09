from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from backend.notification.domain.exceptions import (
    InvalidActionLabelError,
    InvalidActionOwnershipError,
    InvalidCallbackError,
    InvalidExpirationError,
    InvalidNotificationChannelError,
    InvalidNotificationMessageError,
    InvalidNotificationPriorityError,
    InvalidNotificationTargetError,
    InvalidNotificationTitleError,
    InvalidNotificationTransitionError,
    NotificationDismissedError,
    NotificationExpiredError,
    SecretDetectedError,
)
from backend.notification.domain.factory import NotificationFactory
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
from backend.notification.domain.rules import (
    MAX_MESSAGE_LENGTH,
    MAX_TITLE_LENGTH,
    SECRET_PATTERNS,
    VALID_NOTIFICATION_TRANSITIONS,
    assert_action_label_required,
    assert_callback_name_required,
    assert_can_acknowledge,
    assert_can_dismiss,
    assert_channel_valid,
    assert_content_no_secrets,
    assert_critical_not_sms,
    assert_message_required,
    assert_not_dismissed,
    assert_not_expired,
    assert_not_immutable,
    assert_notification_can_transition,
    assert_priority_valid,
    assert_target_required,
    assert_title_required,
    validate_action_creation,
    validate_notification_creation,
    validate_notification_update,
)

# ===========================================================================
# Helpers
# ===========================================================================


def make_valid_target(
    target_type: str = "user", target_id: str = "user-123"
) -> NotificationTarget:
    return NotificationTarget(target_type=target_type, target_id=target_id)


def make_valid_expiration(days: int = 7) -> ExpirationPolicy:
    return ExpirationPolicy(
        expires_at=datetime.now(tz=timezone.utc) + timedelta(days=days)
    )


def make_valid_notification(
    title: str = "Test Notification",
    message: str = "This is a test notification message",
    priority: NotificationPriority = NotificationPriority.NORMAL,
    channel: NotificationChannel = NotificationChannel.IN_APP,
    target: NotificationTarget | None = None,
    expires_at: datetime | None = None,
) -> Notification:
    t = target or make_valid_target()
    if expires_at is None:
        exp = make_valid_expiration()
        expires_at = exp.expires_at
    n, _ = NotificationFactory.create_notification(
        title=title,
        message=message,
        priority=priority,
        channel=channel,
        target=t,
        expiration_policy=ExpirationPolicy(expires_at=expires_at) if expires_at else None,
    )
    return n


# =============================================================================
# 1. Value Object Tests
# =============================================================================


class TestNotificationId:
    def test_creation(self) -> None:
        nid = NotificationId()
        assert isinstance(nid.value, UUID)

    def test_str_representation(self) -> None:
        nid = NotificationId()
        assert str(nid) == str(nid.value)

    def test_equality(self) -> None:
        v = UUID("00000000-0000-0000-0000-000000000001")
        a = NotificationId(value=v)
        b = NotificationId(value=v)
        assert a == b

    def test_inequality(self) -> None:
        assert NotificationId() != NotificationId()

    def test_immutability(self) -> None:
        nid = NotificationId()
        with pytest.raises(AttributeError):
            nid.value = UUID(int=0)  # type: ignore

    def test_default_factory(self) -> None:
        nid = NotificationId()
        assert nid.value is not None


class TestActionId:
    def test_creation(self) -> None:
        aid = ActionId()
        assert isinstance(aid.value, UUID)

    def test_str(self) -> None:
        aid = ActionId()
        assert str(aid) == str(aid.value)

    def test_equality(self) -> None:
        v = UUID("00000000-0000-0000-0000-000000000001")
        assert ActionId(value=v) == ActionId(value=v)

    def test_immutability(self) -> None:
        aid = ActionId()
        with pytest.raises(AttributeError):
            aid.value = UUID(int=0)  # type: ignore


class TestNotificationTitle:
    def test_creation(self) -> None:
        t = NotificationTitle(value="Hello")
        assert t.value == "Hello"

    def test_str_conversion(self) -> None:
        t = NotificationTitle(value="Test")
        assert str(t) == "Test"

    def test_length(self) -> None:
        t = NotificationTitle(value="abcde")
        assert len(t) == 5

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidNotificationTitleError, match="not be empty"):
            NotificationTitle(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidNotificationTitleError, match="not be empty"):
            NotificationTitle(value="   ")

    def test_max_length(self) -> None:
        NotificationTitle(value="x" * 200)

    def test_exceeds_max_length_raises(self) -> None:
        with pytest.raises(InvalidNotificationTitleError, match="exceeds maximum 200"):
            NotificationTitle(value="x" * 201)

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            NotificationTitle(value=123)  # type: ignore

    def test_equality(self) -> None:
        assert NotificationTitle(value="a") == NotificationTitle(value="a")

    def test_frozen(self) -> None:
        t = NotificationTitle(value="a")
        with pytest.raises(AttributeError):
            t.value = "b"  # type: ignore


class TestNotificationMessage:
    def test_creation(self) -> None:
        m = NotificationMessage(value="Hello world")
        assert m.value == "Hello world"

    def test_str_conversion(self) -> None:
        m = NotificationMessage(value="Test")
        assert str(m) == "Test"

    def test_length(self) -> None:
        m = NotificationMessage(value="abcde")
        assert len(m) == 5

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidNotificationMessageError, match="not be empty"):
            NotificationMessage(value="")

    def test_blank_raises(self) -> None:
        with pytest.raises(InvalidNotificationMessageError, match="not be empty"):
            NotificationMessage(value="   ")

    def test_max_length(self) -> None:
        NotificationMessage(value="x" * 5000)

    def test_exceeds_max_length_raises(self) -> None:
        with pytest.raises(InvalidNotificationMessageError, match="exceeds maximum 5000"):
            NotificationMessage(value="x" * 5001)

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            NotificationMessage(value=123)  # type: ignore

    def test_equality(self) -> None:
        assert NotificationMessage(value="a") == NotificationMessage(value="a")

    def test_frozen(self) -> None:
        m = NotificationMessage(value="a")
        with pytest.raises(AttributeError):
            m.value = "b"  # type: ignore


class TestNotificationTarget:
    def test_creation(self) -> None:
        t = NotificationTarget(target_type="user", target_id="u-1")
        assert t.target_type == "user"
        assert t.target_id == "u-1"

    def test_str_conversion(self) -> None:
        t = NotificationTarget(target_type="user", target_id="u-1")
        assert str(t) == "user:u-1"

    def test_empty_target_type_raises(self) -> None:
        with pytest.raises(InvalidNotificationTargetError, match="target_type"):
            NotificationTarget(target_type="", target_id="u-1")

    def test_blank_target_type_raises(self) -> None:
        with pytest.raises(InvalidNotificationTargetError, match="target_type"):
            NotificationTarget(target_type="   ", target_id="u-1")

    def test_empty_target_id_raises(self) -> None:
        with pytest.raises(InvalidNotificationTargetError, match="target_id"):
            NotificationTarget(target_type="user", target_id="")

    def test_blank_target_id_raises(self) -> None:
        with pytest.raises(InvalidNotificationTargetError, match="target_id"):
            NotificationTarget(target_type="user", target_id="   ")

    def test_frozen(self) -> None:
        t = NotificationTarget(target_type="user", target_id="u-1")
        with pytest.raises(AttributeError):
            t.target_type = "admin"  # type: ignore

    def test_equality(self) -> None:
        a = NotificationTarget(target_type="user", target_id="u-1")
        b = NotificationTarget(target_type="user", target_id="u-1")
        assert a == b


class TestExpirationPolicy:
    def test_creation(self) -> None:
        future = datetime.now(tz=timezone.utc) + timedelta(days=1)
        ep = ExpirationPolicy(expires_at=future)
        assert ep.expires_at == future

    def test_past_raises(self) -> None:
        past = datetime.now(tz=timezone.utc) - timedelta(days=1)
        with pytest.raises(InvalidExpirationError, match="future"):
            ExpirationPolicy(expires_at=past)

    def test_now_raises(self) -> None:
        with pytest.raises(InvalidExpirationError, match="future"):
            ExpirationPolicy(expires_at=datetime.now(tz=timezone.utc))

    def test_naive_datetime_gets_utc(self) -> None:
        future = datetime.now() + timedelta(days=1)
        ep = ExpirationPolicy(expires_at=future)
        assert ep.expires_at.tzinfo is not None
        assert ep.expires_at.tzinfo.utcoffset(None) == timedelta(0)

    def test_frozen(self) -> None:
        future = datetime.now(tz=timezone.utc) + timedelta(days=1)
        ep = ExpirationPolicy(expires_at=future)
        with pytest.raises(AttributeError):
            ep.expires_at = datetime.now(tz=timezone.utc)  # type: ignore

    def test_far_future(self) -> None:
        future = datetime.now(tz=timezone.utc) + timedelta(days=365)
        ep = ExpirationPolicy(expires_at=future)
        assert ep.expires_at == future


# =============================================================================
# 2. Enum Tests
# =============================================================================


class TestNotificationStatus:
    def test_members(self) -> None:
        assert NotificationStatus.PENDING.value == "pending"
        assert NotificationStatus.SHOWN.value == "shown"
        assert NotificationStatus.ACKNOWLEDGED.value == "acknowledged"
        assert NotificationStatus.DISMISSED.value == "dismissed"
        assert NotificationStatus.EXPIRED.value == "expired"

    def test_order(self) -> None:
        members = list(NotificationStatus)
        assert members == [
            NotificationStatus.PENDING,
            NotificationStatus.SHOWN,
            NotificationStatus.ACKNOWLEDGED,
            NotificationStatus.DISMISSED,
            NotificationStatus.EXPIRED,
        ]

    def test_from_string(self) -> None:
        assert NotificationStatus("pending") == NotificationStatus.PENDING
        assert NotificationStatus("shown") == NotificationStatus.SHOWN

    def test_unique_values(self) -> None:
        values = [s.value for s in NotificationStatus]
        assert len(values) == len(set(values))


class TestNotificationPriority:
    def test_members(self) -> None:
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.NORMAL.value == "normal"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.CRITICAL.value == "critical"

    def test_from_string(self) -> None:
        assert NotificationPriority("high") == NotificationPriority.HIGH

    def test_unique_values(self) -> None:
        values = [p.value for p in NotificationPriority]
        assert len(values) == len(set(values))


class TestNotificationChannel:
    def test_members(self) -> None:
        assert NotificationChannel.IN_APP.value == "in_app"
        assert NotificationChannel.DESKTOP.value == "desktop"
        assert NotificationChannel.EMAIL.value == "email"
        assert NotificationChannel.SMS.value == "sms"

    def test_from_string(self) -> None:
        assert NotificationChannel("email") == NotificationChannel.EMAIL

    def test_unique_values(self) -> None:
        values = [c.value for c in NotificationChannel]
        assert len(values) == len(set(values))


# =============================================================================
# 3. Domain Event Tests
# =============================================================================


class TestNotificationCreated:
    def test_creation(self) -> None:
        nid = NotificationId()
        now = datetime.now(tz=timezone.utc)
        ev = NotificationCreated(
            notification_id=nid,
            title="Test",
            message="Body",
            priority="normal",
            channel="in_app",
            target_type="user",
            target_id="u-1",
            occurred_at=now,
        )
        assert ev.notification_id == nid
        assert ev.title == "Test"
        assert ev.message == "Body"
        assert ev.priority == "normal"
        assert ev.channel == "in_app"
        assert ev.target_type == "user"
        assert ev.target_id == "u-1"
        assert ev.occurred_at == now
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        nid = NotificationId()
        ev = NotificationCreated(
            notification_id=nid,
            title="Test",
            message="Body",
            priority="normal",
            channel="in_app",
            target_type="user",
            target_id="u-1",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.title = "changed"  # type: ignore

    def test_unique_event_ids(self) -> None:
        nid = NotificationId()
        now = datetime.now(tz=timezone.utc)
        ev1 = NotificationCreated(
            notification_id=nid, title="A", message="B",
            priority="low", channel="in_app",
            target_type="user", target_id="u-1", occurred_at=now,
        )
        ev2 = NotificationCreated(
            notification_id=nid, title="A", message="B",
            priority="low", channel="in_app",
            target_type="user", target_id="u-1", occurred_at=now,
        )
        assert ev1.event_id != ev2.event_id


class TestNotificationShown:
    def test_creation(self) -> None:
        nid = NotificationId()
        now = datetime.now(tz=timezone.utc)
        ev = NotificationShown(notification_id=nid, occurred_at=now)
        assert ev.notification_id == nid
        assert ev.occurred_at == now
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        nid = NotificationId()
        ev = NotificationShown(
            notification_id=nid, occurred_at=datetime.now(tz=timezone.utc)
        )
        with pytest.raises(AttributeError):
            ev.notification_id = NotificationId()  # type: ignore


class TestNotificationAcknowledged:
    def test_creation(self) -> None:
        nid = NotificationId()
        now = datetime.now(tz=timezone.utc)
        ev = NotificationAcknowledged(notification_id=nid, occurred_at=now)
        assert ev.notification_id == nid
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        nid = NotificationId()
        ev = NotificationAcknowledged(
            notification_id=nid, occurred_at=datetime.now(tz=timezone.utc)
        )
        with pytest.raises(AttributeError):
            ev.occurred_at = datetime.now(tz=timezone.utc)  # type: ignore


class TestNotificationDismissed:
    def test_creation(self) -> None:
        nid = NotificationId()
        now = datetime.now(tz=timezone.utc)
        ev = NotificationDismissed(notification_id=nid, occurred_at=now)
        assert ev.notification_id == nid
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        nid = NotificationId()
        ev = NotificationDismissed(
            notification_id=nid, occurred_at=datetime.now(tz=timezone.utc)
        )
        with pytest.raises(AttributeError):
            ev.notification_id = NotificationId()  # type: ignore


class TestNotificationExpired:
    def test_creation(self) -> None:
        nid = NotificationId()
        now = datetime.now(tz=timezone.utc)
        ev = NotificationExpired(notification_id=nid, occurred_at=now)
        assert ev.notification_id == nid
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        nid = NotificationId()
        ev = NotificationExpired(
            notification_id=nid, occurred_at=datetime.now(tz=timezone.utc)
        )
        with pytest.raises(AttributeError):
            ev.occurred_at = datetime.now(tz=timezone.utc)  # type: ignore


class TestNotificationActionInvoked:
    def test_creation(self) -> None:
        nid = NotificationId()
        aid = ActionId()
        now = datetime.now(tz=timezone.utc)
        ev = NotificationActionInvoked(
            notification_id=nid,
            action_id=aid,
            callback_name="mark_read",
            occurred_at=now,
        )
        assert ev.notification_id == nid
        assert ev.action_id == aid
        assert ev.callback_name == "mark_read"
        assert ev.occurred_at == now
        assert isinstance(ev.event_id, UUID)

    def test_frozen(self) -> None:
        nid = NotificationId()
        aid = ActionId()
        ev = NotificationActionInvoked(
            notification_id=nid,
            action_id=aid,
            callback_name="mark_read",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.callback_name = "other"  # type: ignore


# =============================================================================
# 4. Notification Entity Tests
# =============================================================================


class TestNotificationCreation:
    def test_default_status_is_pending(self) -> None:
        n = make_valid_notification()
        assert n.status == NotificationStatus.PENDING

    def test_default_id_is_generated(self) -> None:
        n = make_valid_notification()
        assert isinstance(n.notification_id, NotificationId)

    def test_initial_events_empty(self) -> None:
        n = make_valid_notification()
        assert n.events == []

    def test_not_expired_initially(self) -> None:
        n = make_valid_notification()
        assert n.is_expired is False

    def test_not_dismissed_initially(self) -> None:
        n = make_valid_notification()
        assert n.is_dismissed is False

    def test_priority_default(self) -> None:
        n = make_valid_notification()
        assert n.priority == NotificationPriority.NORMAL

    def test_channel_default(self) -> None:
        n = make_valid_notification()
        assert n.channel == NotificationChannel.IN_APP

    def test_created_at_set(self) -> None:
        n = make_valid_notification()
        assert n.created_at is not None
        assert n.created_at.tzinfo is not None

    def test_repr(self) -> None:
        n = make_valid_notification()
        r = repr(n)
        assert "Notification" in r
        assert str(n.notification_id) in r


class TestNotificationShow:
    def test_show_sets_shown(self) -> None:
        n = make_valid_notification()
        n.show()
        assert n.status == NotificationStatus.SHOWN

    def test_show_sets_shown_at(self) -> None:
        n = make_valid_notification()
        n.show()
        assert n.shown_at is not None

    def test_show_emits_event(self) -> None:
        n = make_valid_notification()
        n.show()
        assert len(n.events) == 1
        assert isinstance(n.events[0], NotificationShown)

    def test_show_event_has_correct_id(self) -> None:
        n = make_valid_notification()
        nid = n.notification_id
        n.show()
        assert n.events[0].notification_id == nid

    def test_double_show_raises(self) -> None:
        n = make_valid_notification()
        n.show()
        with pytest.raises(InvalidNotificationTransitionError):
            n.show()

    def test_show_after_acknowledge_raises(self) -> None:
        n = make_valid_notification()
        n.show()
        n.acknowledge()
        with pytest.raises(InvalidNotificationTransitionError):
            n.show()


class TestNotificationAcknowledge:
    def test_acknowledge_requires_shown(self) -> None:
        n = make_valid_notification()
        with pytest.raises(InvalidNotificationTransitionError):
            n.acknowledge()

    def test_acknowledge_sets_acknowledged(self) -> None:
        n = make_valid_notification()
        n.show()
        n.acknowledge()
        assert n.status == NotificationStatus.ACKNOWLEDGED

    def test_acknowledge_sets_acknowledged_at(self) -> None:
        n = make_valid_notification()
        n.show()
        n.acknowledge()
        assert n.acknowledged_at is not None

    def test_acknowledge_emits_event(self) -> None:
        n = make_valid_notification()
        n.show()
        n.acknowledge()
        assert len(n.events) == 2
        assert isinstance(n.events[1], NotificationAcknowledged)

    def test_double_acknowledge_raises(self) -> None:
        n = make_valid_notification()
        n.show()
        n.acknowledge()
        with pytest.raises(InvalidNotificationTransitionError):
            n.acknowledge()

    def test_acknowledge_from_pending_raises(self) -> None:
        n = make_valid_notification()
        with pytest.raises(InvalidNotificationTransitionError):
            n.acknowledge()


class TestNotificationDismiss:
    def test_dismiss_requires_shown(self) -> None:
        n = make_valid_notification()
        with pytest.raises(InvalidNotificationTransitionError):
            n.dismiss()

    def test_dismiss_sets_dismissed(self) -> None:
        n = make_valid_notification()
        n.show()
        n.dismiss()
        assert n.status == NotificationStatus.DISMISSED

    def test_dismiss_sets_dismissed_at(self) -> None:
        n = make_valid_notification()
        n.show()
        n.dismiss()
        assert n.dismissed_at is not None

    def test_dismiss_emits_event(self) -> None:
        n = make_valid_notification()
        n.show()
        n.dismiss()
        assert len(n.events) == 2
        assert isinstance(n.events[1], NotificationDismissed)

    def test_double_dismiss_raises(self) -> None:
        n = make_valid_notification()
        n.show()
        n.dismiss()
        with pytest.raises(NotificationDismissedError):
            n.dismiss()

    def test_dismiss_from_pending_raises(self) -> None:
        n = make_valid_notification()
        with pytest.raises(InvalidNotificationTransitionError):
            n.dismiss()


class TestNotificationExpire:
    def test_expire_from_pending(self) -> None:
        n = make_valid_notification()
        n.expire()
        assert n.status == NotificationStatus.EXPIRED

    def test_expire_from_shown(self) -> None:
        n = make_valid_notification()
        n.show()
        n.expire()
        assert n.status == NotificationStatus.EXPIRED

    def test_expire_from_acknowledged(self) -> None:
        n = make_valid_notification()
        n.show()
        n.acknowledge()
        n.expire()
        assert n.status == NotificationStatus.EXPIRED

    def test_expire_emits_event(self) -> None:
        n = make_valid_notification()
        n.expire()
        assert len(n.events) == 1
        assert isinstance(n.events[0], NotificationExpired)

    def test_double_expire_raises(self) -> None:
        n = make_valid_notification()
        n.expire()
        with pytest.raises(NotificationExpiredError):
            n.expire()

    def test_expire_from_dismissed_raises(self) -> None:
        n = make_valid_notification()
        n.show()
        n.dismiss()
        with pytest.raises(NotificationDismissedError):
            n.expire()


class TestNotificationExpiredImmutable:
    def test_expired_cannot_show(self) -> None:
        n = make_valid_notification()
        n.expire()
        with pytest.raises(NotificationExpiredError):
            n.show()

    def test_expired_cannot_acknowledge(self) -> None:
        n = make_valid_notification()
        n.expire()
        with pytest.raises(NotificationExpiredError):
            n.acknowledge()

    def test_expired_cannot_dismiss(self) -> None:
        n = make_valid_notification()
        n.expire()
        with pytest.raises(NotificationExpiredError):
            n.dismiss()

    def test_expired_cannot_expire(self) -> None:
        n = make_valid_notification()
        n.expire()
        with pytest.raises(NotificationExpiredError):
            n.expire()


class TestNotificationDismissedImmutable:
    def test_dismissed_cannot_show(self) -> None:
        n = make_valid_notification()
        n.show()
        n.dismiss()
        with pytest.raises(NotificationDismissedError):
            n.show()

    def test_dismissed_cannot_acknowledge(self) -> None:
        n = make_valid_notification()
        n.show()
        n.dismiss()
        with pytest.raises(NotificationDismissedError):
            n.acknowledge()

    def test_dismissed_cannot_dismiss(self) -> None:
        n = make_valid_notification()
        n.show()
        n.dismiss()
        with pytest.raises(NotificationDismissedError):
            n.dismiss()

    def test_dismissed_cannot_expire(self) -> None:
        n = make_valid_notification()
        n.show()
        n.dismiss()
        with pytest.raises(NotificationDismissedError):
            n.expire()


class TestNotificationTimestampBehavior:
    def test_shown_at_only_after_show(self) -> None:
        n = make_valid_notification()
        assert n.shown_at is None
        n.show()
        assert n.shown_at is not None

    def test_acknowledged_at_only_after_acknowledge(self) -> None:
        n = make_valid_notification()
        n.show()
        assert n.acknowledged_at is None
        n.acknowledge()
        assert n.acknowledged_at is not None

    def test_dismissed_at_only_after_dismiss(self) -> None:
        n = make_valid_notification()
        n.show()
        assert n.dismissed_at is None
        n.dismiss()
        assert n.dismissed_at is not None

    def test_timestamps_are_utc(self) -> None:
        n = make_valid_notification()
        n.show()
        assert n.shown_at is not None
        assert n.shown_at.tzinfo is not None

    def test_is_expired_with_past_expires_at(self) -> None:
        past = datetime.now(tz=timezone.utc) - timedelta(days=1)
        n = Notification(
            title=NotificationTitle(value="Test"),
            message=NotificationMessage(value="Body"),
            target=make_valid_target(),
            expires_at=past,
        )
        assert n.is_expired is True


class TestNotificationClearEvents:
    def test_clear_events(self) -> None:
        n = make_valid_notification()
        n.show()
        assert len(n.events) == 1
        n._clear_events()
        assert n.events == []


# =============================================================================
# 5. NotificationAction Entity Tests
# =============================================================================


class TestNotificationActionCreation:
    def test_creation(self) -> None:
        nid = NotificationId()
        action = NotificationAction(
            notification_id=nid,
            label="Mark Read",
            callback_name="mark_read",
        )
        assert action.notification_id == nid
        assert action.label == "Mark Read"
        assert action.callback_name == "mark_read"
        assert isinstance(action.action_id, ActionId)

    def test_default_id_generated(self) -> None:
        action = NotificationAction(
            notification_id=NotificationId(),
            label="Test",
            callback_name="test",
        )
        assert isinstance(action.action_id, ActionId)

    def test_created_at_set(self) -> None:
        action = NotificationAction(
            notification_id=NotificationId(),
            label="Test",
            callback_name="test",
        )
        assert action.created_at is not None
        assert action.created_at.tzinfo is not None

    def test_initial_events_empty(self) -> None:
        action = NotificationAction(
            notification_id=NotificationId(),
            label="Test",
            callback_name="test",
        )
        assert action.events == []

    def test_repr(self) -> None:
        action = NotificationAction(
            notification_id=NotificationId(),
            label="Mark Read",
            callback_name="mark_read",
        )
        r = repr(action)
        assert "NotificationAction" in r
        assert "Mark Read" in r


class TestNotificationActionInvoke:
    def test_invoke_returns_event(self) -> None:
        nid = NotificationId()
        action = NotificationAction(
            notification_id=nid,
            label="Mark Read",
            callback_name="mark_read",
        )
        event = action.invoke()
        assert isinstance(event, NotificationActionInvoked)
        assert event.notification_id == nid
        assert event.action_id == action.action_id
        assert event.callback_name == "mark_read"

    def test_invoke_appends_event(self) -> None:
        action = NotificationAction(
            notification_id=NotificationId(),
            label="Mark Read",
            callback_name="mark_read",
        )
        action.invoke()
        assert len(action.events) == 1

    def test_invoke_multiple(self) -> None:
        action = NotificationAction(
            notification_id=NotificationId(),
            label="Mark Read",
            callback_name="mark_read",
        )
        action.invoke()
        action.invoke()
        assert len(action.events) == 2

    def test_invoke_clear_events(self) -> None:
        action = NotificationAction(
            notification_id=NotificationId(),
            label="Mark Read",
            callback_name="mark_read",
        )
        action.invoke()
        action._clear_events()
        assert action.events == []


# =============================================================================
# 6. Rules Tests
# =============================================================================


class TestTitleRule:
    def test_title_required(self) -> None:
        assert_title_required("Hello")

    def test_title_empty_raises(self) -> None:
        with pytest.raises(InvalidNotificationTitleError):
            assert_title_required("")

    def test_title_none_raises(self) -> None:
        with pytest.raises(InvalidNotificationTitleError):
            assert_title_required(None)

    def test_title_blank_raises(self) -> None:
        with pytest.raises(InvalidNotificationTitleError):
            assert_title_required("   ")


class TestMessageRule:
    def test_message_required(self) -> None:
        assert_message_required("Hello")

    def test_message_empty_raises(self) -> None:
        with pytest.raises(InvalidNotificationMessageError):
            assert_message_required("")

    def test_message_none_raises(self) -> None:
        with pytest.raises(InvalidNotificationMessageError):
            assert_message_required(None)

    def test_message_blank_raises(self) -> None:
        with pytest.raises(InvalidNotificationMessageError):
            assert_message_required("   ")


class TestTargetRule:
    def test_target_required(self) -> None:
        assert_target_required(make_valid_target())

    def test_target_none_raises(self) -> None:
        with pytest.raises(InvalidNotificationTargetError):
            assert_target_required(None)


class TestPriorityRule:
    def test_valid_priority(self) -> None:
        assert_priority_valid("low")
        assert_priority_valid("normal")
        assert_priority_valid("high")
        assert_priority_valid("critical")

    def test_valid_priority_enum(self) -> None:
        assert_priority_valid(NotificationPriority.HIGH)

    def test_invalid_priority_raises(self) -> None:
        with pytest.raises(InvalidNotificationPriorityError):
            assert_priority_valid("urgent")

    def test_empty_string_raises(self) -> None:
        with pytest.raises(InvalidNotificationPriorityError):
            assert_priority_valid("")


class TestChannelRule:
    def test_valid_channel(self) -> None:
        assert_channel_valid("in_app")
        assert_channel_valid("desktop")
        assert_channel_valid("email")
        assert_channel_valid("sms")

    def test_valid_channel_enum(self) -> None:
        assert_channel_valid(NotificationChannel.EMAIL)

    def test_invalid_channel_raises(self) -> None:
        with pytest.raises(InvalidNotificationChannelError):
            assert_channel_valid("push")

    def test_empty_string_raises(self) -> None:
        with pytest.raises(InvalidNotificationChannelError):
            assert_channel_valid("")


class TestCriticalNotSmsRule:
    def test_critical_in_app_allowed(self) -> None:
        assert_critical_not_sms(NotificationPriority.CRITICAL, NotificationChannel.IN_APP)

    def test_critical_desktop_allowed(self) -> None:
        assert_critical_not_sms(NotificationPriority.CRITICAL, NotificationChannel.DESKTOP)

    def test_critical_email_allowed(self) -> None:
        assert_critical_not_sms(NotificationPriority.CRITICAL, NotificationChannel.EMAIL)

    def test_critical_sms_raises(self) -> None:
        with pytest.raises(InvalidNotificationChannelError, match="CRITICAL"):
            assert_critical_not_sms(NotificationPriority.CRITICAL, NotificationChannel.SMS)

    def test_normal_sms_allowed(self) -> None:
        assert_critical_not_sms(NotificationPriority.NORMAL, NotificationChannel.SMS)

    def test_low_sms_allowed(self) -> None:
        assert_critical_not_sms(NotificationPriority.LOW, NotificationChannel.SMS)


class TestSecretDetectionRule:
    def test_no_secrets_passes(self) -> None:
        assert_content_no_secrets("This is a safe message")

    def test_password_detected(self) -> None:
        with pytest.raises(SecretDetectedError, match="password"):
            assert_content_no_secrets("my password is secret")

    def test_token_detected(self) -> None:
        with pytest.raises(SecretDetectedError, match="token"):
            assert_content_no_secrets("auth token abc123")

    def test_api_key_detected(self) -> None:
        with pytest.raises(SecretDetectedError, match="api_key"):
            assert_content_no_secrets("use api_key=xyz")

    def test_api_key_variant_detected(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("api-key=secret")

    def test_private_key_detected(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("private_key data")

    def test_authorization_detected(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("authorization header")

    def test_bearer_detected(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("bearer token123")

    def test_case_insensitive_password(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("PASSWORD=secret")

    def test_empty_string_passes(self) -> None:
        assert_content_no_secrets("")


class TestTransitionRule:
    def test_pending_to_shown(self) -> None:
        assert_notification_can_transition(NotificationStatus.PENDING, NotificationStatus.SHOWN)

    def test_pending_to_expired(self) -> None:
        assert_notification_can_transition(NotificationStatus.PENDING, NotificationStatus.EXPIRED)

    def test_shown_to_acknowledged(self) -> None:
        assert_notification_can_transition(NotificationStatus.SHOWN, NotificationStatus.ACKNOWLEDGED)

    def test_shown_to_dismissed(self) -> None:
        assert_notification_can_transition(NotificationStatus.SHOWN, NotificationStatus.DISMISSED)

    def test_shown_to_expired(self) -> None:
        assert_notification_can_transition(NotificationStatus.SHOWN, NotificationStatus.EXPIRED)

    def test_acknowledged_to_expired(self) -> None:
        assert_notification_can_transition(NotificationStatus.ACKNOWLEDGED, NotificationStatus.EXPIRED)

    def test_pending_to_dismissed_raises(self) -> None:
        with pytest.raises(InvalidNotificationTransitionError):
            assert_notification_can_transition(NotificationStatus.PENDING, NotificationStatus.DISMISSED)

    def test_pending_to_acknowledged_raises(self) -> None:
        with pytest.raises(InvalidNotificationTransitionError):
            assert_notification_can_transition(NotificationStatus.PENDING, NotificationStatus.ACKNOWLEDGED)

    def test_dismissed_to_anything_raises(self) -> None:
        for target in NotificationStatus:
            if target == NotificationStatus.DISMISSED:
                continue
            with pytest.raises(InvalidNotificationTransitionError):
                assert_notification_can_transition(NotificationStatus.DISMISSED, target)

    def test_expired_to_anything_raises(self) -> None:
        for target in NotificationStatus:
            if target == NotificationStatus.EXPIRED:
                continue
            with pytest.raises(InvalidNotificationTransitionError):
                assert_notification_can_transition(NotificationStatus.EXPIRED, target)

    def test_valid_transitions_dict_structure(self) -> None:
        assert NotificationStatus.PENDING in VALID_NOTIFICATION_TRANSITIONS
        assert NotificationStatus.SHOWN in VALID_NOTIFICATION_TRANSITIONS
        assert NotificationStatus.ACKNOWLEDGED in VALID_NOTIFICATION_TRANSITIONS
        assert NotificationStatus.DISMISSED in VALID_NOTIFICATION_TRANSITIONS
        assert NotificationStatus.EXPIRED in VALID_NOTIFICATION_TRANSITIONS


class TestCanAcknowledge:
    def test_shown_allowed(self) -> None:
        assert_can_acknowledge(NotificationStatus.SHOWN)

    def test_pending_raises(self) -> None:
        with pytest.raises(InvalidNotificationTransitionError):
            assert_can_acknowledge(NotificationStatus.PENDING)


class TestCanDismiss:
    def test_shown_allowed(self) -> None:
        assert_can_dismiss(NotificationStatus.SHOWN)

    def test_pending_raises(self) -> None:
        with pytest.raises(InvalidNotificationTransitionError):
            assert_can_dismiss(NotificationStatus.PENDING)


class TestNotExpired:
    def test_not_expired_passes(self) -> None:
        n = make_valid_notification()
        assert_not_expired(n)

    def test_expired_raises(self) -> None:
        n = make_valid_notification()
        n.expire()
        with pytest.raises(NotificationExpiredError):
            assert_not_expired(n)


class TestNotDismissed:
    def test_not_dismissed_passes(self) -> None:
        n = make_valid_notification()
        assert_not_dismissed(n)

    def test_dismissed_raises(self) -> None:
        n = make_valid_notification()
        n.show()
        n.dismiss()
        with pytest.raises(NotificationDismissedError):
            assert_not_dismissed(n)


class TestActionLabelRule:
    def test_label_required(self) -> None:
        assert_action_label_required("Mark Read")

    def test_label_empty_raises(self) -> None:
        with pytest.raises(InvalidActionLabelError):
            assert_action_label_required("")

    def test_label_blank_raises(self) -> None:
        with pytest.raises(InvalidActionLabelError):
            assert_action_label_required("   ")


class TestCallbackNameRule:
    def test_callback_required(self) -> None:
        assert_callback_name_required("mark_read")

    def test_callback_empty_raises(self) -> None:
        with pytest.raises(InvalidCallbackError):
            assert_callback_name_required("")

    def test_callback_blank_raises(self) -> None:
        with pytest.raises(InvalidCallbackError):
            assert_callback_name_required("   ")


class TestNotImmutable:
    def test_active_passes(self) -> None:
        n = make_valid_notification()
        assert_not_immutable(n)

    def test_expired_raises(self) -> None:
        n = make_valid_notification()
        n.expire()
        with pytest.raises(NotificationExpiredError):
            assert_not_immutable(n)

    def test_dismissed_raises(self) -> None:
        n = make_valid_notification()
        n.show()
        n.dismiss()
        with pytest.raises(NotificationDismissedError):
            assert_not_immutable(n)


# =============================================================================
# 7. Composite Validator Tests
# =============================================================================


class TestValidateNotificationCreation:
    def test_valid_creation(self) -> None:
        priority, channel = validate_notification_creation(
            title="Test",
            message="Body",
            priority="normal",
            channel="in_app",
            target=make_valid_target(),
        )
        assert priority == NotificationPriority.NORMAL
        assert channel == NotificationChannel.IN_APP

    def test_empty_title_raises(self) -> None:
        with pytest.raises(InvalidNotificationTitleError):
            validate_notification_creation(
                title="", message="Body", priority="normal",
                channel="in_app", target=make_valid_target(),
            )

    def test_empty_message_raises(self) -> None:
        with pytest.raises(InvalidNotificationMessageError):
            validate_notification_creation(
                title="Test", message="", priority="normal",
                channel="in_app", target=make_valid_target(),
            )

    def test_no_target_raises(self) -> None:
        with pytest.raises(InvalidNotificationTargetError):
            validate_notification_creation(
                title="Test", message="Body", priority="normal",
                channel="in_app", target=None,
            )

    def test_invalid_priority_raises(self) -> None:
        with pytest.raises(InvalidNotificationPriorityError):
            validate_notification_creation(
                title="Test", message="Body", priority="urgent",
                channel="in_app", target=make_valid_target(),
            )

    def test_invalid_channel_raises(self) -> None:
        with pytest.raises(InvalidNotificationChannelError):
            validate_notification_creation(
                title="Test", message="Body", priority="normal",
                channel="push", target=make_valid_target(),
            )

    def test_critical_sms_raises(self) -> None:
        with pytest.raises(InvalidNotificationChannelError, match="CRITICAL"):
            validate_notification_creation(
                title="Test", message="Body", priority="critical",
                channel="sms", target=make_valid_target(),
            )

    def test_secret_in_title_raises(self) -> None:
        with pytest.raises(SecretDetectedError):
            validate_notification_creation(
                title="my password is 123", message="Body",
                priority="normal", channel="in_app",
                target=make_valid_target(),
            )

    def test_secret_in_message_raises(self) -> None:
        with pytest.raises(SecretDetectedError):
            validate_notification_creation(
                title="Test", message="api_key=abc123",
                priority="normal", channel="in_app",
                target=make_valid_target(),
            )

    def test_priority_enum_accepted(self) -> None:
        priority, channel = validate_notification_creation(
            title="Test", message="Body",
            priority=NotificationPriority.HIGH,
            channel=NotificationChannel.DESKTOP,
            target=make_valid_target(),
        )
        assert priority == NotificationPriority.HIGH


class TestValidateNotificationUpdate:
    def test_valid_update(self) -> None:
        n = make_valid_notification()
        validate_notification_update(n)

    def test_expired_raises(self) -> None:
        n = make_valid_notification()
        n.expire()
        with pytest.raises(NotificationExpiredError):
            validate_notification_update(n)

    def test_dismissed_raises(self) -> None:
        n = make_valid_notification()
        n.show()
        n.dismiss()
        with pytest.raises(NotificationDismissedError):
            validate_notification_update(n)


class TestValidateActionCreation:
    def test_valid_action(self) -> None:
        n = make_valid_notification()
        validate_action_creation(
            label="Mark Read",
            callback_name="mark_read",
            notification=n,
        )

    def test_empty_label_raises(self) -> None:
        n = make_valid_notification()
        with pytest.raises(InvalidActionLabelError):
            validate_action_creation(
                label="", callback_name="mark_read", notification=n,
            )

    def test_empty_callback_raises(self) -> None:
        n = make_valid_notification()
        with pytest.raises(InvalidCallbackError):
            validate_action_creation(
                label="Mark Read", callback_name="", notification=n,
            )

    def test_none_notification_raises(self) -> None:
        with pytest.raises(InvalidActionOwnershipError):
            validate_action_creation(
                label="Mark Read", callback_name="mark_read", notification=None,
            )

    def test_secret_in_label_raises(self) -> None:
        n = make_valid_notification()
        with pytest.raises(SecretDetectedError):
            validate_action_creation(
                label="token secret", callback_name="mark_read", notification=n,
            )


# =============================================================================
# 8. Factory Tests
# =============================================================================


class TestFactoryCreateNotification:
    def test_happy_path(self) -> None:
        n, ev = NotificationFactory.create_notification(
            title="Welcome",
            message="Welcome to the app!",
            priority="normal",
            channel="in_app",
            target=make_valid_target(),
        )
        assert isinstance(n, Notification)
        assert isinstance(ev, NotificationCreated)
        assert n.title is not None
        assert n.title.value == "Welcome"
        assert n.message is not None
        assert n.message.value == "Welcome to the app!"
        assert n.priority == NotificationPriority.NORMAL
        assert n.channel == NotificationChannel.IN_APP

    def test_event_has_correct_fields(self) -> None:
        n, ev = NotificationFactory.create_notification(
            title="Alert",
            message="Something happened",
            priority="high",
            channel="email",
            target=make_valid_target(target_type="admin", target_id="adm-1"),
        )
        assert ev.notification_id == n.notification_id
        assert ev.title == "Alert"
        assert ev.message == "Something happened"
        assert ev.priority == "high"
        assert ev.channel == "email"
        assert ev.target_type == "admin"
        assert ev.target_id == "adm-1"

    def test_with_expiration(self) -> None:
        exp = make_valid_expiration(days=3)
        n, ev = NotificationFactory.create_notification(
            title="Timed",
            message="This expires",
            priority="low",
            channel="desktop",
            target=make_valid_target(),
            expiration_policy=exp,
        )
        assert n.expires_at is not None
        assert n.expires_at == exp.expires_at

    def test_without_expiration(self) -> None:
        n, ev = NotificationFactory.create_notification(
            title="No Expiry",
            message="No expiry set",
            priority="normal",
            channel="in_app",
            target=make_valid_target(),
        )
        assert n.expires_at is None

    def test_critical_with_sms_raises(self) -> None:
        with pytest.raises(InvalidNotificationChannelError, match="CRITICAL"):
            NotificationFactory.create_notification(
                title="Urgent",
                message="Critical alert",
                priority="critical",
                channel="sms",
                target=make_valid_target(),
            )

    def test_secret_in_title_raises(self) -> None:
        with pytest.raises(SecretDetectedError):
            NotificationFactory.create_notification(
                title="password is 123",
                message="Body",
                priority="normal",
                channel="in_app",
                target=make_valid_target(),
            )

    def test_priority_enum_accepted(self) -> None:
        n, ev = NotificationFactory.create_notification(
            title="Test",
            message="Body",
            priority=NotificationPriority.HIGH,
            channel=NotificationChannel.DESKTOP,
            target=make_valid_target(),
        )
        assert n.priority == NotificationPriority.HIGH

    def test_channel_conversion(self) -> None:
        n, ev = NotificationFactory.create_notification(
            title="Test",
            message="Body",
            priority="high",
            channel="sms",
            target=make_valid_target(),
        )
        assert n.channel == NotificationChannel.SMS


class TestFactoryShowNotification:
    def test_show_returns_event(self) -> None:
        n = make_valid_notification()
        event = NotificationFactory.show_notification(n)
        assert isinstance(event, NotificationShown)
        assert n.status == NotificationStatus.SHOWN

    def test_show_twice_raises(self) -> None:
        n = make_valid_notification()
        NotificationFactory.show_notification(n)
        with pytest.raises(InvalidNotificationTransitionError):
            NotificationFactory.show_notification(n)


class TestFactoryAcknowledgeNotification:
    def test_acknowledge_returns_event(self) -> None:
        n = make_valid_notification()
        n.show()
        event = NotificationFactory.acknowledge_notification(n)
        assert isinstance(event, NotificationAcknowledged)
        assert n.status == NotificationStatus.ACKNOWLEDGED

    def test_acknowledge_without_show_raises(self) -> None:
        n = make_valid_notification()
        with pytest.raises(InvalidNotificationTransitionError):
            NotificationFactory.acknowledge_notification(n)


class TestFactoryDismissNotification:
    def test_dismiss_returns_event(self) -> None:
        n = make_valid_notification()
        n.show()
        event = NotificationFactory.dismiss_notification(n)
        assert isinstance(event, NotificationDismissed)
        assert n.status == NotificationStatus.DISMISSED

    def test_dismiss_without_show_raises(self) -> None:
        n = make_valid_notification()
        with pytest.raises(InvalidNotificationTransitionError):
            NotificationFactory.dismiss_notification(n)


class TestFactoryExpireNotification:
    def test_expire_returns_event(self) -> None:
        n = make_valid_notification()
        event = NotificationFactory.expire_notification(n)
        assert isinstance(event, NotificationExpired)
        assert n.status == NotificationStatus.EXPIRED

    def test_double_expire_raises(self) -> None:
        n = make_valid_notification()
        NotificationFactory.expire_notification(n)
        with pytest.raises(NotificationExpiredError):
            NotificationFactory.expire_notification(n)


class TestFactoryCreateAction:
    def test_happy_path(self) -> None:
        n = make_valid_notification()
        action = NotificationFactory.create_action(
            notification=n,
            label="Mark Read",
            callback_name="mark_read",
        )
        assert isinstance(action, NotificationAction)
        assert action.notification_id == n.notification_id
        assert action.label == "Mark Read"
        assert action.callback_name == "mark_read"

    def test_empty_label_raises(self) -> None:
        n = make_valid_notification()
        with pytest.raises(InvalidActionLabelError):
            NotificationFactory.create_action(
                notification=n, label="", callback_name="mark_read",
            )

    def test_empty_callback_raises(self) -> None:
        n = make_valid_notification()
        with pytest.raises(InvalidCallbackError):
            NotificationFactory.create_action(
                notification=n, label="Mark Read", callback_name="",
            )

    def test_secret_in_label_raises(self) -> None:
        n = make_valid_notification()
        with pytest.raises(SecretDetectedError):
            NotificationFactory.create_action(
                notification=n, label="token abc", callback_name="mark_read",
            )


class TestFactoryInvokeAction:
    def test_happy_path(self) -> None:
        n = make_valid_notification()
        action = NotificationFactory.create_action(
            notification=n, label="Mark Read", callback_name="mark_read",
        )
        event = NotificationFactory.invoke_action(action)
        assert isinstance(event, NotificationActionInvoked)
        assert event.action_id == action.action_id
        assert event.callback_name == "mark_read"

    def test_invoke_twice(self) -> None:
        n = make_valid_notification()
        action = NotificationFactory.create_action(
            notification=n, label="Mark Read", callback_name="mark_read",
        )
        NotificationFactory.invoke_action(action)
        NotificationFactory.invoke_action(action)
        assert len(action.events) == 2


# =============================================================================
# 9. Edge Case Tests
# =============================================================================


class TestEdgeCases:
    def test_full_lifecycle_pending_to_expired(self) -> None:
        n = make_valid_notification()
        assert n.status == NotificationStatus.PENDING
        n.show()
        assert n.status == NotificationStatus.SHOWN
        n.acknowledge()
        assert n.status == NotificationStatus.ACKNOWLEDGED
        n.expire()
        assert n.status == NotificationStatus.EXPIRED
        assert len(n.events) == 3

    def test_full_lifecycle_pending_to_dismissed(self) -> None:
        n = make_valid_notification()
        n.show()
        n.dismiss()
        assert n.status == NotificationStatus.DISMISSED
        assert n.dismissed_at is not None

    def test_full_lifecycle_pending_to_expired_direct(self) -> None:
        n = make_valid_notification()
        n.expire()
        assert n.status == NotificationStatus.EXPIRED

    def test_show_to_expired(self) -> None:
        n = make_valid_notification()
        n.show()
        n.expire()
        assert n.status == NotificationStatus.EXPIRED

    def test_multiple_actions_on_notification(self) -> None:
        n = make_valid_notification()
        a1 = NotificationFactory.create_action(
            notification=n, label="Read", callback_name="mark_read",
        )
        a2 = NotificationFactory.create_action(
            notification=n, label="Archive", callback_name="archive",
        )
        assert a1.notification_id == n.notification_id
        assert a2.notification_id == n.notification_id
        assert a1.action_id != a2.action_id

    def test_created_at_preserved(self) -> None:
        n = make_valid_notification()
        created = n.created_at
        n.show()
        n.acknowledge()
        assert n.created_at == created

    def test_max_title_length_boundary(self) -> None:
        t = NotificationTitle(value="x" * 200)
        assert len(t) == 200

    def test_max_message_length_boundary(self) -> None:
        m = NotificationMessage(value="x" * 5000)
        assert len(m) == 5000

    def test_secret_patterns_list_not_empty(self) -> None:
        assert len(SECRET_PATTERNS) > 0

    def test_max_title_constant(self) -> None:
        assert MAX_TITLE_LENGTH == 200

    def test_max_message_constant(self) -> None:
        assert MAX_MESSAGE_LENGTH == 5000

    def test_notification_target_invalid_type_empty_raises(self) -> None:
        with pytest.raises(InvalidNotificationTargetError):
            NotificationTarget(target_type="", target_id="u-1")

    def test_notification_target_invalid_id_empty_raises(self) -> None:
        with pytest.raises(InvalidNotificationTargetError):
            NotificationTarget(target_type="user", target_id="")

    def test_is_expired_returns_true_for_expired_status(self) -> None:
        n = make_valid_notification()
        n.expire()
        assert n.is_expired is True

    def test_is_dismissed_returns_true_for_dismissed(self) -> None:
        n = make_valid_notification()
        n.show()
        n.dismiss()
        assert n.is_dismissed is True

    def test_is_expired_none_expires_at(self) -> None:
        n = Notification(
            title=NotificationTitle(value="Test"),
            message=NotificationMessage(value="Body"),
            target=make_valid_target(),
            expires_at=None,
        )
        assert n.is_expired is False


class TestNotificationActionEdgeCases:
    def test_action_with_special_chars_in_label(self) -> None:
        n = make_valid_notification()
        action = NotificationFactory.create_action(
            notification=n,
            label="Mark as Read! (click here)",
            callback_name="mark_read",
        )
        assert action.label == "Mark as Read! (click here)"

    def test_action_invoke_after_notification_expired(self) -> None:
        n = make_valid_notification()
        action = NotificationFactory.create_action(
            notification=n, label="Read", callback_name="mark_read",
        )
        n.expire()
        event = action.invoke()
        assert isinstance(event, NotificationActionInvoked)


class TestSecretDetectionContentEdgeCases:
    def test_password_in_middle_of_word(self) -> None:
        assert_content_no_secrets("passwords are secure here")

    def test_password_as_whole_word(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("my password is secret")

    def test_api_key_with_underscore(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("use api_key for auth")

    def test_api_key_with_hyphen(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("api-key=abc")

    def test_private_key_with_underscore(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("private_key content")

    def test_private_key_with_hyphen(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("private-key content")


class TestExpirationEdgeCases:
    def test_expiration_one_second_in_future(self) -> None:
        future = datetime.now(tz=timezone.utc) + timedelta(seconds=1)
        ep = ExpirationPolicy(expires_at=future)
        assert ep.expires_at > datetime.now(tz=timezone.utc)

    def test_expiration_far_future(self) -> None:
        future = datetime.now(tz=timezone.utc) + timedelta(days=3650)
        ep = ExpirationPolicy(expires_at=future)
        assert ep.expires_at == future


class TestValidationEdgeCases:
    def test_validate_creation_with_enum_values(self) -> None:
        priority, channel = validate_notification_creation(
            title="Test",
            message="Body",
            priority=NotificationPriority.CRITICAL,
            channel=NotificationChannel.EMAIL,
            target=make_valid_target(),
        )
        assert priority == NotificationPriority.CRITICAL
        assert channel == NotificationChannel.EMAIL

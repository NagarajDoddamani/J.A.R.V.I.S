from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.notification.adapters.outbound.clock import SystemClockAdapter
from backend.notification.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.notification.adapters.outbound.mapper import (
    NotificationActionMapperImpl,
    NotificationMapperImpl,
    NotificationOutboxMapperImpl,
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
    NotificationStatus,
    NotificationTarget,
    NotificationTitle,
)


# ===================================================================
# Clock adapter tests
# ===================================================================


class TestSystemClockAdapter:
    def test_now_returns_utc(self) -> None:
        clock = SystemClockAdapter()
        result = clock.now()
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result).total_seconds() == 0.0

    def test_now_returns_datetime(self) -> None:
        clock = SystemClockAdapter()
        assert isinstance(clock.now(), datetime)


# ===================================================================
# ID generator adapter tests
# ===================================================================


class TestUuidGeneratorAdapter:
    def test_generate_notification_id(self) -> None:
        gen = UuidGeneratorAdapter()
        nid = gen.generate_notification_id()
        assert isinstance(nid, NotificationId)

    def test_generate_action_id(self) -> None:
        gen = UuidGeneratorAdapter()
        aid = gen.generate_action_id()
        assert isinstance(aid, ActionId)

    def test_unique_notification_ids(self) -> None:
        gen = UuidGeneratorAdapter()
        ids = {gen.generate_notification_id() for _ in range(100)}
        assert len(ids) == 100

    def test_unique_action_ids(self) -> None:
        gen = UuidGeneratorAdapter()
        ids = {gen.generate_action_id() for _ in range(100)}
        assert len(ids) == 100


# ===================================================================
# NotificationMapperImpl tests
# ===================================================================


def _make_notification(
    *,
    title: str = "Test title",
    message: str = "Test message",
    priority: NotificationPriority = NotificationPriority.NORMAL,
    channel: NotificationChannel = NotificationChannel.IN_APP,
    target_type: str = "user",
    target_id: str = "user-001",
    status: NotificationStatus = NotificationStatus.PENDING,
    shown_at: datetime | None = None,
    acknowledged_at: datetime | None = None,
    dismissed_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> Notification:
    now = datetime.now(tz=timezone.utc)
    return Notification(
        notification_id=NotificationId(),
        title=NotificationTitle(value=title),
        message=NotificationMessage(value=message),
        priority=priority,
        channel=channel,
        target=NotificationTarget(target_type=target_type, target_id=target_id),
        status=status,
        created_at=now,
        shown_at=shown_at,
        acknowledged_at=acknowledged_at,
        dismissed_at=dismissed_at,
        expires_at=expires_at,
    )


class TestNotificationMapperImpl:
    @pytest.fixture
    def mapper(self) -> NotificationMapperImpl:
        return NotificationMapperImpl()

    def test_domain_to_dto(self, mapper: NotificationMapperImpl) -> None:
        notification = _make_notification()
        dto = mapper.domain_to_dto(notification)

        assert dto.notification_id == str(notification.notification_id)
        assert dto.title == "Test title"
        assert dto.message == "Test message"
        assert dto.priority == "normal"
        assert dto.channel == "in_app"
        assert dto.target_type == "user"
        assert dto.target_id == "user-001"
        assert dto.status == "pending"
        assert dto.shown_at is None

    def test_dto_to_domain(self, mapper: NotificationMapperImpl) -> None:
        notification = _make_notification()
        dto = mapper.domain_to_dto(notification)
        reconstructed = mapper.dto_to_domain(dto)

        assert str(reconstructed.notification_id) == dto.notification_id
        assert str(reconstructed.title) == "Test title"
        assert reconstructed.priority == NotificationPriority.NORMAL

    def test_roundtrip(self, mapper: NotificationMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = Notification(
            notification_id=NotificationId(),
            title=NotificationTitle(value="Roundtrip"),
            message=NotificationMessage(value="Roundtrip message"),
            priority=NotificationPriority.HIGH,
            channel=NotificationChannel.DESKTOP,
            target=NotificationTarget(target_type="admin", target_id="admin-001"),
            status=NotificationStatus.SHOWN,
            created_at=now,
            shown_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)

        assert str(reconstructed.notification_id) == str(original.notification_id)
        assert str(reconstructed.title) == "Roundtrip"
        assert reconstructed.priority == NotificationPriority.HIGH
        assert reconstructed.channel == NotificationChannel.DESKTOP
        assert reconstructed.status == NotificationStatus.SHOWN
        assert reconstructed.shown_at is not None
        assert reconstructed.acknowledged_at is None

    def test_nullable_fields_roundtrip(self, mapper: NotificationMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = Notification(
            notification_id=NotificationId(),
            title=NotificationTitle(value="Nulls"),
            message=NotificationMessage(value="Nullable fields"),
            priority=NotificationPriority.LOW,
            channel=NotificationChannel.IN_APP,
            target=NotificationTarget(target_type="user", target_id="u-001"),
            status=NotificationStatus.PENDING,
            created_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)

        assert reconstructed.shown_at is None
        assert reconstructed.acknowledged_at is None
        assert reconstructed.dismissed_at is None
        assert reconstructed.expires_at is None

    def test_all_statuses_mapped(self, mapper: NotificationMapperImpl) -> None:
        for status in NotificationStatus:
            notification = _make_notification(status=status)
            dto = mapper.domain_to_dto(notification)
            assert dto.status == status.value
            reconstructed = mapper.dto_to_domain(dto)
            assert reconstructed.status == status

    def test_all_priorities_mapped(self, mapper: NotificationMapperImpl) -> None:
        for priority in NotificationPriority:
            notification = _make_notification(priority=priority)
            dto = mapper.domain_to_dto(notification)
            assert dto.priority == priority.value
            reconstructed = mapper.dto_to_domain(dto)
            assert reconstructed.priority == priority

    def test_all_channels_mapped(self, mapper: NotificationMapperImpl) -> None:
        for channel in NotificationChannel:
            notification = _make_notification(channel=channel)
            dto = mapper.domain_to_dto(notification)
            assert dto.channel == channel.value
            reconstructed = mapper.dto_to_domain(dto)
            assert reconstructed.channel == channel

    def test_timestamps_preserved(self, mapper: NotificationMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        notification = _make_notification(
            status=NotificationStatus.SHOWN,
            shown_at=now,
        )
        dto = mapper.domain_to_dto(notification)
        assert dto.shown_at == now
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.shown_at == now


# ===================================================================
# NotificationActionMapperImpl tests
# ===================================================================


class TestNotificationActionMapperImpl:
    @pytest.fixture
    def mapper(self) -> NotificationActionMapperImpl:
        return NotificationActionMapperImpl()

    def test_domain_to_dto(self, mapper: NotificationActionMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        action = NotificationAction(
            action_id=ActionId(),
            notification_id=NotificationId(),
            label="View details",
            callback_name="view_details",
            created_at=now,
        )
        dto = mapper.domain_to_dto(action)
        assert dto.action_id == str(action.action_id)
        assert dto.notification_id == str(action.notification_id)
        assert dto.label == "View details"
        assert dto.callback_name == "view_details"
        assert dto.created_at == now

    def test_dto_to_domain(self, mapper: NotificationActionMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        action = NotificationAction(
            action_id=ActionId(),
            notification_id=NotificationId(),
            label="Dismiss",
            callback_name="dismiss_action",
            created_at=now,
        )
        dto = mapper.domain_to_dto(action)
        reconstructed = mapper.dto_to_domain(dto)
        assert str(reconstructed.action_id) == dto.action_id
        assert reconstructed.label == "Dismiss"
        assert reconstructed.callback_name == "dismiss_action"
        assert reconstructed.created_at == now

    def test_roundtrip(self, mapper: NotificationActionMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = NotificationAction(
            action_id=ActionId(),
            notification_id=NotificationId(),
            label="Approve",
            callback_name="approve_action",
            created_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert str(reconstructed.action_id) == str(original.action_id)
        assert reconstructed.label == "Approve"
        assert reconstructed.callback_name == "approve_action"
        assert reconstructed.created_at == now

    def test_notification_id_preserved(self, mapper: NotificationActionMapperImpl) -> None:
        nid = NotificationId()
        now = datetime.now(tz=timezone.utc)
        action = NotificationAction(
            action_id=ActionId(),
            notification_id=nid,
            label="Test",
            callback_name="test",
            created_at=now,
        )
        dto = mapper.domain_to_dto(action)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.notification_id is not None
        assert str(reconstructed.notification_id) == str(nid)

    def test_null_notification_id(self, mapper: NotificationActionMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        action = NotificationAction(
            action_id=ActionId(),
            notification_id=None,
            label="Orphan",
            callback_name="orphan",
            created_at=now,
        )
        dto = mapper.domain_to_dto(action)
        assert dto.notification_id == ""
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.notification_id is None


# ===================================================================
# NotificationOutboxMapperImpl tests
# ===================================================================


class TestNotificationOutboxMapperImpl:
    @pytest.fixture
    def mapper(self) -> NotificationOutboxMapperImpl:
        return NotificationOutboxMapperImpl()

    def test_created_event_to_dto(self, mapper: NotificationOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        event = NotificationCreated(
            notification_id=NotificationId(),
            title="Test",
            message="Message",
            priority="high",
            channel="desktop",
            target_type="user",
            target_id="u-001",
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "notification.created"
        assert dto.aggregate_id == str(event.notification_id)
        assert dto.occurred_at == now
        assert dto.published is False
        assert dto.payload is not None

    def test_shown_event_to_dto(self, mapper: NotificationOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        event = NotificationShown(
            notification_id=NotificationId(),
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "notification.shown"
        assert dto.aggregate_id == str(event.notification_id)

    def test_acknowledged_event_to_dto(self, mapper: NotificationOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        event = NotificationAcknowledged(
            notification_id=NotificationId(),
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "notification.acknowledged"

    def test_dismissed_event_to_dto(self, mapper: NotificationOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        event = NotificationDismissed(
            notification_id=NotificationId(),
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "notification.dismissed"

    def test_expired_event_to_dto(self, mapper: NotificationOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        event = NotificationExpired(
            notification_id=NotificationId(),
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "notification.expired"

    def test_action_invoked_event_to_dto(self, mapper: NotificationOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        event = NotificationActionInvoked(
            notification_id=NotificationId(),
            action_id=ActionId(),
            callback_name="handle_click",
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "notification.action.invoked"
        assert dto.aggregate_id == str(event.action_id)
        assert dto.payload is not None

    def test_all_six_event_types(self, mapper: NotificationOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        nid = NotificationId()
        aid = ActionId()
        events = [
            NotificationCreated(nid, "T", "M", "normal", "in_app", "user", "u-001", now),
            NotificationShown(nid, now),
            NotificationAcknowledged(nid, now),
            NotificationDismissed(nid, now),
            NotificationExpired(nid, now),
            NotificationActionInvoked(nid, aid, "cb", now),
        ]
        for event in events:
            dto = mapper.event_to_dto(event)
            assert dto.event_id is not None
            assert dto.event_type is not None
            assert dto.aggregate_id is not None

    def test_dto_to_event_created(self, mapper: NotificationOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = NotificationCreated(
            notification_id=NotificationId(),
            title="Title",
            message="Msg",
            priority="low",
            channel="sms",
            target_type="user",
            target_id="u-001",
            occurred_at=now,
        )
        dto = mapper.event_to_dto(original)
        event = mapper.dto_to_event(dto)
        assert isinstance(event, NotificationCreated)
        assert str(event.notification_id) == str(original.notification_id)
        assert event.title == "Title"

    def test_dto_to_event_shown(self, mapper: NotificationOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = NotificationShown(
            notification_id=NotificationId(),
            occurred_at=now,
        )
        dto = mapper.event_to_dto(original)
        event = mapper.dto_to_event(dto)
        assert isinstance(event, NotificationShown)
        assert str(event.notification_id) == str(original.notification_id)

    def test_dto_to_event_action_invoked(self, mapper: NotificationOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = NotificationActionInvoked(
            notification_id=NotificationId(),
            action_id=ActionId(),
            callback_name="on_click",
            occurred_at=now,
        )
        dto = mapper.event_to_dto(original)
        event = mapper.dto_to_event(dto)
        assert isinstance(event, NotificationActionInvoked)
        assert str(event.action_id) == str(original.action_id)
        assert event.callback_name == "on_click"

    def test_roundtrip_created(self, mapper: NotificationOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = NotificationCreated(
            notification_id=NotificationId(),
            title="Roundtrip title",
            message="Roundtrip msg",
            priority="critical",
            channel="desktop",
            target_type="admin",
            target_id="a-001",
            occurred_at=now,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert type(reconstructed) is type(original)
        assert str(reconstructed.notification_id) == str(original.notification_id)
        assert reconstructed.title == "Roundtrip title"

    def test_roundtrip_action_invoked(self, mapper: NotificationOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        original = NotificationActionInvoked(
            notification_id=NotificationId(),
            action_id=ActionId(),
            callback_name="test_cb",
            occurred_at=now,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, NotificationActionInvoked)
        assert reconstructed.callback_name == "test_cb"

    def test_roundtrip_simple_events(self, mapper: NotificationOutboxMapperImpl) -> None:
        now = datetime.now(tz=timezone.utc)
        nid = NotificationId()
        for event_cls in [NotificationShown, NotificationAcknowledged,
                          NotificationDismissed, NotificationExpired]:
            original = event_cls(notification_id=nid, occurred_at=now)
            dto = mapper.event_to_dto(original)
            reconstructed = mapper.dto_to_event(dto)
            assert type(reconstructed) is event_cls
            assert str(reconstructed.notification_id) == str(nid)

    def test_unknown_event_type_raises(self, mapper: NotificationOutboxMapperImpl) -> None:
        from backend.notification.application.persistence.dto import (
            NotificationOutboxStorageDTO,
        )
        dto = NotificationOutboxStorageDTO(
            event_id="id-1",
            event_type="nonexistent.type",
            aggregate_id="agg-1",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(ValueError, match="Unknown event_type"):
            mapper.dto_to_event(dto)

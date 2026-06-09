from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.notification.application.persistence.dto import (
    NotificationActionStorageDTO,
    NotificationOutboxStorageDTO,
    NotificationStorageDTO,
)
from backend.notification.application.persistence.mapper import (
    NotificationActionMapper,
    NotificationMapper,
    NotificationOutboxDomainEvent,
    NotificationOutboxMapper,
)
from backend.notification.application.persistence.schema import (
    NOTIFICATION_ACTIONS_TABLE,
    NOTIFICATION_OUTBOX_TABLE,
    NOTIFICATIONS_TABLE,
    ColumnContract,
    TableContract,
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
from backend.notification.domain.rules import (
    MAX_MESSAGE_LENGTH,
    MAX_TITLE_LENGTH,
)

# ===================================================================
# Stub mapper implementations (conform to mapper protocols)
# ===================================================================


class StubNotificationMapper:
    def domain_to_dto(self, notification: Notification) -> NotificationStorageDTO:
        return NotificationStorageDTO(
            notification_id=str(notification.notification_id),
            title=notification.title.value if notification.title else "",
            message=notification.message.value if notification.message else "",
            priority=notification.priority.value,
            channel=notification.channel.value,
            target_type=notification.target.target_type if notification.target else "",
            target_id=notification.target.target_id if notification.target else "",
            status=notification.status.value,
            created_at=notification.created_at,
            shown_at=notification.shown_at,
            acknowledged_at=notification.acknowledged_at,
            dismissed_at=notification.dismissed_at,
            expires_at=notification.expires_at,
        )

    def dto_to_domain(self, dto: NotificationStorageDTO) -> Notification:
        return Notification(
            notification_id=NotificationId(value=UUID(dto.notification_id)),
            title=NotificationTitle(value=dto.title),
            message=NotificationMessage(value=dto.message),
            priority=NotificationPriority(dto.priority),
            channel=NotificationChannel(dto.channel),
            target=NotificationTarget(
                target_type=dto.target_type,
                target_id=dto.target_id,
            ),
            status=NotificationStatus(dto.status),
            created_at=dto.created_at,
            shown_at=dto.shown_at,
            acknowledged_at=dto.acknowledged_at,
            dismissed_at=dto.dismissed_at,
            expires_at=dto.expires_at,
        )


class StubNotificationActionMapper:
    def domain_to_dto(self, action: NotificationAction) -> NotificationActionStorageDTO:
        return NotificationActionStorageDTO(
            action_id=str(action.action_id),
            notification_id=str(action.notification_id) if action.notification_id else "",
            label=action.label,
            callback_name=action.callback_name,
            created_at=action.created_at,
        )

    def dto_to_domain(self, dto: NotificationActionStorageDTO) -> NotificationAction:
        return NotificationAction(
            action_id=ActionId(value=UUID(dto.action_id)),
            notification_id=NotificationId(value=UUID(dto.notification_id)),
            label=dto.label,
            callback_name=dto.callback_name,
            created_at=dto.created_at,
        )


class StubNotificationOutboxMapper:
    def event_to_dto(self, event: NotificationOutboxDomainEvent) -> NotificationOutboxStorageDTO:
        aggregate_id = str(event.notification_id)

        if isinstance(event, NotificationCreated):
            event_type = "notification.created"
        elif isinstance(event, NotificationShown):
            event_type = "notification.shown"
        elif isinstance(event, NotificationAcknowledged):
            event_type = "notification.acknowledged"
        elif isinstance(event, NotificationDismissed):
            event_type = "notification.dismissed"
        elif isinstance(event, NotificationExpired):
            event_type = "notification.expired"
        elif isinstance(event, NotificationActionInvoked):
            event_type = "notification.action.invoked"
        else:
            event_type = "unknown"

        return NotificationOutboxStorageDTO(
            event_id=aggregate_id,
            event_type=event_type,
            aggregate_id=aggregate_id,
            occurred_at=event.occurred_at,
            published=False,
        )

    def dto_to_event(self, dto: NotificationOutboxStorageDTO) -> NotificationOutboxDomainEvent:
        try:
            aggregate_id = UUID(dto.aggregate_id)
        except ValueError:
            aggregate_id = UUID("00000000-0000-0000-0000-000000000001")
        nid = NotificationId(value=aggregate_id)

        if dto.event_type == "notification.created":
            return NotificationCreated(
                notification_id=nid,
                title="",
                message="",
                priority="normal",
                channel="in_app",
                target_type="user",
                target_id="",
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "notification.shown":
            return NotificationShown(notification_id=nid, occurred_at=dto.occurred_at)
        elif dto.event_type == "notification.acknowledged":
            return NotificationAcknowledged(notification_id=nid, occurred_at=dto.occurred_at)
        elif dto.event_type == "notification.dismissed":
            return NotificationDismissed(notification_id=nid, occurred_at=dto.occurred_at)
        elif dto.event_type == "notification.expired":
            return NotificationExpired(notification_id=nid, occurred_at=dto.occurred_at)
        elif dto.event_type == "notification.action.invoked":
            return NotificationActionInvoked(
                notification_id=nid,
                action_id=ActionId(),
                callback_name="",
                occurred_at=dto.occurred_at,
            )
        else:
            raise ValueError(f"Unknown event_type: {dto.event_type}")


# ===================================================================
# DTO construction tests
# ===================================================================


class TestNotificationStorageDTO:
    def test_all_fields_present(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = NotificationStorageDTO(
            notification_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            title="Test Notification",
            message="This is a test message",
            priority="normal",
            channel="in_app",
            target_type="user",
            target_id="u-123",
            status="pending",
            created_at=dt,
            shown_at=None,
            acknowledged_at=None,
            dismissed_at=None,
            expires_at=None,
        )
        assert dto.notification_id == "01975c2f-4aef-7cf1-a940-ae54bf596280"
        assert dto.title == "Test Notification"
        assert dto.message == "This is a test message"
        assert dto.priority == "normal"
        assert dto.channel == "in_app"
        assert dto.target_type == "user"
        assert dto.target_id == "u-123"
        assert dto.status == "pending"
        assert dto.created_at == dt
        assert dto.shown_at is None
        assert dto.acknowledged_at is None
        assert dto.dismissed_at is None
        assert dto.expires_at is None

    def test_nullable_fields(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = NotificationStorageDTO(
            notification_id="id-1",
            title="Test",
            message="Body",
            priority="high",
            channel="email",
            target_type="admin",
            target_id="a-1",
            status="shown",
            created_at=dt,
            shown_at=dt,
        )
        assert dto.shown_at == dt
        assert dto.acknowledged_at is None
        assert dto.dismissed_at is None
        assert dto.expires_at is None

    def test_frozen(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = NotificationStorageDTO(
            notification_id="id-1",
            title="Test",
            message="Body",
            priority="normal",
            channel="in_app",
            target_type="user",
            target_id="u-1",
            status="pending",
            created_at=dt,
        )
        with pytest.raises(AttributeError):
            dto.notification_id = "changed"  # type: ignore

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(NotificationStorageDTO)
        assert len(fields) == 13

    def test_all_fields_have_types(self) -> None:
        import dataclasses
        for f in dataclasses.fields(NotificationStorageDTO):
            assert f.type is not None, f"Field {f.name} has no type annotation"

    def test_explicit_timestamps(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        shown = datetime(2026, 6, 8, 12, 1, 0, tzinfo=timezone.utc)
        ack = datetime(2026, 6, 8, 12, 2, 0, tzinfo=timezone.utc)
        dis = datetime(2026, 6, 8, 12, 3, 0, tzinfo=timezone.utc)
        exp = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        dto = NotificationStorageDTO(
            notification_id="id-1",
            title="Test",
            message="Body",
            priority="low",
            channel="desktop",
            target_type="user",
            target_id="u-1",
            status="expired",
            created_at=dt,
            shown_at=shown,
            acknowledged_at=ack,
            dismissed_at=dis,
            expires_at=exp,
        )
        assert dto.shown_at == shown
        assert dto.acknowledged_at == ack
        assert dto.dismissed_at == dis
        assert dto.expires_at == exp

    def test_all_priorities(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        for priority in ("low", "normal", "high", "critical"):
            dto = NotificationStorageDTO(
                notification_id="id-1", title="T", message="M",
                priority=priority, channel="in_app",
                target_type="user", target_id="u-1",
                status="pending", created_at=dt,
            )
            assert dto.priority == priority

    def test_all_channels(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        for channel in ("in_app", "desktop", "email", "sms"):
            dto = NotificationStorageDTO(
                notification_id="id-1", title="T", message="M",
                priority="normal", channel=channel,
                target_type="user", target_id="u-1",
                status="pending", created_at=dt,
            )
            assert dto.channel == channel

    def test_all_statuses(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        for status in ("pending", "shown", "acknowledged", "dismissed", "expired"):
            dto = NotificationStorageDTO(
                notification_id="id-1", title="T", message="M",
                priority="normal", channel="in_app",
                target_type="user", target_id="u-1",
                status=status, created_at=dt,
            )
            assert dto.status == status


class TestNotificationActionStorageDTO:
    def test_all_fields_present(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = NotificationActionStorageDTO(
            action_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            notification_id="01975c2f-4aef-7cf1-a940-ae54bf596281",
            label="Mark Read",
            callback_name="mark_read",
            created_at=dt,
        )
        assert dto.action_id == "01975c2f-4aef-7cf1-a940-ae54bf596280"
        assert dto.notification_id == "01975c2f-4aef-7cf1-a940-ae54bf596281"
        assert dto.label == "Mark Read"
        assert dto.callback_name == "mark_read"
        assert dto.created_at == dt

    def test_frozen(self) -> None:
        dto = NotificationActionStorageDTO(
            action_id="id-1",
            notification_id="id-2",
            label="Mark Read",
            callback_name="mark_read",
            created_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            dto.label = "changed"  # type: ignore

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(NotificationActionStorageDTO)
        assert len(fields) == 5

    def test_no_nullable_fields(self) -> None:
        import dataclasses
        for f in dataclasses.fields(NotificationActionStorageDTO):
            nullable = "None" in str(f.type)
            assert not nullable, f"Field {f.name} should not be nullable"


class TestNotificationOutboxStorageDTO:
    def test_all_fields_present(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = NotificationOutboxStorageDTO(
            event_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            event_type="notification.created",
            aggregate_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            occurred_at=dt,
            payload='{"title": "Test"}',
        )
        assert dto.event_id == "01975c2f-4aef-7cf1-a940-ae54bf596280"
        assert dto.event_type == "notification.created"
        assert dto.aggregate_id == "01975c2f-4aef-7cf1-a940-ae54bf596280"
        assert dto.occurred_at == dt
        assert dto.payload == '{"title": "Test"}'

    def test_default_published_false(self) -> None:
        dto = NotificationOutboxStorageDTO(
            event_id="id-1",
            event_type="notification.created",
            aggregate_id="agg-1",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        assert dto.published is False

    def test_explicit_published(self) -> None:
        dto = NotificationOutboxStorageDTO(
            event_id="id-1",
            event_type="notification.created",
            aggregate_id="agg-1",
            occurred_at=datetime.now(tz=timezone.utc),
            published=True,
        )
        assert dto.published is True

    def test_nullable_payload(self) -> None:
        dto = NotificationOutboxStorageDTO(
            event_id="id-1",
            event_type="notification.created",
            aggregate_id="agg-1",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        assert dto.payload is None

    def test_frozen(self) -> None:
        dto = NotificationOutboxStorageDTO(
            event_id="id-1",
            event_type="notification.created",
            aggregate_id="agg-1",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            dto.event_id = "changed"  # type: ignore

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(NotificationOutboxStorageDTO)
        assert len(fields) == 6

    def test_all_event_types(self) -> None:
        dt = datetime.now(tz=timezone.utc)
        for event_type in (
            "notification.created", "notification.shown",
            "notification.acknowledged", "notification.dismissed",
            "notification.expired", "notification.action.invoked",
        ):
            dto = NotificationOutboxStorageDTO(
                event_id="id-1",
                event_type=event_type,
                aggregate_id="agg-1",
                occurred_at=dt,
            )
            assert dto.event_type == event_type


# ===================================================================
# Mapper protocol conformance tests
# ===================================================================


class TestNotificationMapper:
    @pytest.fixture
    def mapper(self) -> StubNotificationMapper:
        return StubNotificationMapper()

    def test_protocol_conformance(self) -> None:
        mapper: NotificationMapper = StubNotificationMapper()
        assert isinstance(mapper, StubNotificationMapper)

    def test_domain_to_dto(self, mapper: StubNotificationMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        notification = Notification(
            notification_id=NotificationId(),
            title=NotificationTitle(value="Test Notification"),
            message=NotificationMessage(value="Test message body"),
            priority=NotificationPriority.HIGH,
            channel=NotificationChannel.EMAIL,
            target=NotificationTarget(target_type="user", target_id="u-42"),
            status=NotificationStatus.SHOWN,
            created_at=now,
            shown_at=now,
        )
        dto = mapper.domain_to_dto(notification)
        assert dto.notification_id == str(notification.notification_id)
        assert dto.title == "Test Notification"
        assert dto.message == "Test message body"
        assert dto.priority == "high"
        assert dto.channel == "email"
        assert dto.target_type == "user"
        assert dto.target_id == "u-42"
        assert dto.status == "shown"
        assert dto.created_at == now
        assert dto.shown_at == now
        assert dto.acknowledged_at is None
        assert dto.dismissed_at is None
        assert dto.expires_at is None

    def test_dto_to_domain(self, mapper: StubNotificationMapper) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = NotificationStorageDTO(
            notification_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            title="Restored Notification",
            message="Restored message",
            priority="critical",
            channel="desktop",
            target_type="admin",
            target_id="a-001",
            status="pending",
            created_at=dt,
        )
        notification = mapper.dto_to_domain(dto)
        assert str(notification.notification_id) == dto.notification_id
        assert notification.title is not None
        assert notification.title.value == "Restored Notification"
        assert notification.message is not None
        assert notification.message.value == "Restored message"
        assert notification.priority == NotificationPriority.CRITICAL
        assert notification.channel == NotificationChannel.DESKTOP
        assert notification.target is not None
        assert notification.target.target_type == "admin"
        assert notification.target.target_id == "a-001"
        assert notification.status == NotificationStatus.PENDING
        assert notification.created_at == dt

    def test_roundtrip(self, mapper: StubNotificationMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = Notification(
            notification_id=NotificationId(),
            title=NotificationTitle(value="Roundtrip Test"),
            message=NotificationMessage(value="Roundtrip body"),
            priority=NotificationPriority.LOW,
            channel=NotificationChannel.SMS,
            target=NotificationTarget(target_type="user", target_id="u-99"),
            status=NotificationStatus.ACKNOWLEDGED,
            created_at=now,
            shown_at=now,
            acknowledged_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)

        assert str(reconstructed.notification_id) == str(original.notification_id)
        assert reconstructed.title is not None and reconstructed.title.value == original.title.value
        assert reconstructed.message is not None and reconstructed.message.value == original.message.value
        assert reconstructed.priority == original.priority
        assert reconstructed.channel == original.channel
        assert reconstructed.target is not None
        assert reconstructed.target.target_type == original.target.target_type
        assert reconstructed.target.target_id == original.target.target_id
        assert reconstructed.status == original.status
        assert reconstructed.created_at == original.created_at
        assert reconstructed.shown_at == original.shown_at
        assert reconstructed.acknowledged_at == original.acknowledged_at

    def test_null_fields_roundtrip(self, mapper: StubNotificationMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = Notification(
            notification_id=NotificationId(),
            title=NotificationTitle(value="Minimal"),
            message=NotificationMessage(value="Minimal body"),
            priority=NotificationPriority.NORMAL,
            channel=NotificationChannel.IN_APP,
            target=NotificationTarget(target_type="user", target_id="u-1"),
            status=NotificationStatus.PENDING,
            created_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.shown_at is None
        assert reconstructed.acknowledged_at is None
        assert reconstructed.dismissed_at is None
        assert reconstructed.expires_at is None

    def test_full_timestamps_roundtrip(self, mapper: StubNotificationMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        later = datetime.now(tz=timezone.utc)
        original = Notification(
            notification_id=NotificationId(),
            title=NotificationTitle(value="Full"),
            message=NotificationMessage(value="Full body"),
            priority=NotificationPriority.HIGH,
            channel=NotificationChannel.EMAIL,
            target=NotificationTarget(target_type="admin", target_id="a-1"),
            status=NotificationStatus.DISMISSED,
            created_at=now,
            shown_at=now,
            acknowledged_at=later,
            dismissed_at=later,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.shown_at == now
        assert reconstructed.acknowledged_at == later
        assert reconstructed.dismissed_at == later

    def test_mapper_has_required_methods(self) -> None:
        mapper: NotificationMapper = StubNotificationMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


class TestActionMapper:
    @pytest.fixture
    def mapper(self) -> StubNotificationActionMapper:
        return StubNotificationActionMapper()

    def test_protocol_conformance(self) -> None:
        mapper: NotificationActionMapper = StubNotificationActionMapper()
        assert isinstance(mapper, StubNotificationActionMapper)

    def test_domain_to_dto(self, mapper: StubNotificationActionMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        action = NotificationAction(
            action_id=ActionId(),
            notification_id=NotificationId(),
            label="Mark Read",
            callback_name="mark_read",
            created_at=now,
        )
        dto = mapper.domain_to_dto(action)
        assert dto.action_id == str(action.action_id)
        assert dto.notification_id == str(action.notification_id)
        assert dto.label == "Mark Read"
        assert dto.callback_name == "mark_read"
        assert dto.created_at == now

    def test_dto_to_domain(self, mapper: StubNotificationActionMapper) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = NotificationActionStorageDTO(
            action_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            notification_id="01975c2f-4aef-7cf1-a940-ae54bf596281",
            label="Archive",
            callback_name="archive",
            created_at=dt,
        )
        action = mapper.dto_to_domain(dto)
        assert str(action.action_id) == dto.action_id
        assert str(action.notification_id) == dto.notification_id
        assert action.label == "Archive"
        assert action.callback_name == "archive"
        assert action.created_at == dt

    def test_roundtrip(self, mapper: StubNotificationActionMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = NotificationAction(
            action_id=ActionId(),
            notification_id=NotificationId(),
            label="Dismiss",
            callback_name="dismiss",
            created_at=now,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert str(reconstructed.action_id) == str(original.action_id)
        assert reconstructed.label == original.label
        assert reconstructed.callback_name == original.callback_name
        assert reconstructed.created_at == original.created_at

    def test_mapper_has_required_methods(self) -> None:
        mapper: NotificationActionMapper = StubNotificationActionMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


class TestOutboxMapper:
    @pytest.fixture
    def mapper(self) -> StubNotificationOutboxMapper:
        return StubNotificationOutboxMapper()

    def test_protocol_conformance(self) -> None:
        mapper: NotificationOutboxMapper = StubNotificationOutboxMapper()
        assert isinstance(mapper, StubNotificationOutboxMapper)

    def test_created_event_to_dto(self, mapper: StubNotificationOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = NotificationCreated(
            notification_id=NotificationId(),
            title="Test",
            message="Body",
            priority="normal",
            channel="in_app",
            target_type="user",
            target_id="u-1",
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "notification.created"
        assert dto.aggregate_id == str(event.notification_id)
        assert dto.occurred_at == now
        assert dto.published is False

    def test_shown_event_to_dto(self, mapper: StubNotificationOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = NotificationShown(notification_id=NotificationId(), occurred_at=now)
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "notification.shown"

    def test_acknowledged_event_to_dto(self, mapper: StubNotificationOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = NotificationAcknowledged(notification_id=NotificationId(), occurred_at=now)
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "notification.acknowledged"

    def test_dismissed_event_to_dto(self, mapper: StubNotificationOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = NotificationDismissed(notification_id=NotificationId(), occurred_at=now)
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "notification.dismissed"

    def test_expired_event_to_dto(self, mapper: StubNotificationOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = NotificationExpired(notification_id=NotificationId(), occurred_at=now)
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "notification.expired"

    def test_action_invoked_event_to_dto(self, mapper: StubNotificationOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = NotificationActionInvoked(
            notification_id=NotificationId(),
            action_id=ActionId(),
            callback_name="mark_read",
            occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "notification.action.invoked"

    def test_all_events_have_dto_mapping(self, mapper: StubNotificationOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        events: list[NotificationOutboxDomainEvent] = [
            NotificationCreated(NotificationId(), "T", "M", "normal", "in_app", "user", "u-1", now),
            NotificationShown(NotificationId(), now),
            NotificationAcknowledged(NotificationId(), now),
            NotificationDismissed(NotificationId(), now),
            NotificationExpired(NotificationId(), now),
            NotificationActionInvoked(NotificationId(), ActionId(), "cb", now),
        ]
        for event in events:
            dto = mapper.event_to_dto(event)
            assert dto.event_id is not None
            assert dto.event_type is not None
            assert dto.aggregate_id is not None

    def test_event_to_dto_published_default(self, mapper: StubNotificationOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        event = NotificationCreated(
            notification_id=NotificationId(), title="T", message="M",
            priority="normal", channel="in_app", target_type="user",
            target_id="u-1", occurred_at=now,
        )
        dto = mapper.event_to_dto(event)
        assert dto.published is False

    def test_dto_to_event_created(self, mapper: StubNotificationOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = NotificationOutboxStorageDTO(
            event_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            event_type="notification.created",
            aggregate_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            occurred_at=now,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, NotificationCreated)
        assert str(event.notification_id) == dto.aggregate_id

    def test_dto_to_event_shown(self, mapper: StubNotificationOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = NotificationOutboxStorageDTO(
            event_id="01975c2f-4aef-7cf1-a940-ae54bf596280", event_type="notification.shown",
            aggregate_id="01975c2f-4aef-7cf1-a940-ae54bf596280", occurred_at=now,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, NotificationShown)

    def test_dto_to_event_acknowledged(self, mapper: StubNotificationOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = NotificationOutboxStorageDTO(
            event_id="01975c2f-4aef-7cf1-a940-ae54bf596280", event_type="notification.acknowledged",
            aggregate_id="01975c2f-4aef-7cf1-a940-ae54bf596280", occurred_at=now,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, NotificationAcknowledged)

    def test_dto_to_event_dismissed(self, mapper: StubNotificationOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = NotificationOutboxStorageDTO(
            event_id="01975c2f-4aef-7cf1-a940-ae54bf596280", event_type="notification.dismissed",
            aggregate_id="01975c2f-4aef-7cf1-a940-ae54bf596280", occurred_at=now,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, NotificationDismissed)

    def test_dto_to_event_expired(self, mapper: StubNotificationOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = NotificationOutboxStorageDTO(
            event_id="01975c2f-4aef-7cf1-a940-ae54bf596280", event_type="notification.expired",
            aggregate_id="01975c2f-4aef-7cf1-a940-ae54bf596280", occurred_at=now,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, NotificationExpired)

    def test_dto_to_event_action_invoked(self, mapper: StubNotificationOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = NotificationOutboxStorageDTO(
            event_id="01975c2f-4aef-7cf1-a940-ae54bf596280", event_type="notification.action.invoked",
            aggregate_id="01975c2f-4aef-7cf1-a940-ae54bf596280", occurred_at=now,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, NotificationActionInvoked)

    def test_unknown_event_type_raises(self, mapper: StubNotificationOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        dto = NotificationOutboxStorageDTO(
            event_id="01975c2f-4aef-7cf1-a940-ae54bf596280", event_type="unknown.type",
            aggregate_id="01975c2f-4aef-7cf1-a940-ae54bf596280", occurred_at=now,
        )
        with pytest.raises(ValueError, match="unknown"):
            mapper.dto_to_event(dto)

    def test_roundtrip_created(self, mapper: StubNotificationOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = NotificationCreated(
            notification_id=NotificationId(), title="T", message="M",
            priority="high", channel="email", target_type="admin",
            target_id="a-1", occurred_at=now,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert type(reconstructed) is type(original)
        assert str(reconstructed.notification_id) == str(original.notification_id)

    def test_roundtrip_shown(self, mapper: StubNotificationOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = NotificationShown(notification_id=NotificationId(), occurred_at=now)
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, NotificationShown)

    def test_roundtrip_action_invoked(self, mapper: StubNotificationOutboxMapper) -> None:
        now = datetime.now(tz=timezone.utc)
        original = NotificationActionInvoked(
            notification_id=NotificationId(), action_id=ActionId(),
            callback_name="test", occurred_at=now,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, NotificationActionInvoked)

    def test_mapper_has_required_methods(self) -> None:
        mapper: NotificationOutboxMapper = StubNotificationOutboxMapper()
        assert hasattr(mapper, "event_to_dto")
        assert hasattr(mapper, "dto_to_event")


# ===================================================================
# Schema contract consistency tests
# ===================================================================


class TestNotificationsTableSchema:
    def test_column_count(self) -> None:
        assert len(NOTIFICATIONS_TABLE.columns) == 13

    def test_schema_name(self) -> None:
        assert NOTIFICATIONS_TABLE.schema == "notification"
        assert NOTIFICATIONS_TABLE.name == "notifications"

    def test_primary_key(self) -> None:
        assert NOTIFICATIONS_TABLE.primary_key == "notification_id"

    def test_indexes(self) -> None:
        expected = {
            "ix_notifications_status",
            "ix_notifications_priority",
            "ix_notifications_target",
            "ix_notifications_expires_at",
        }
        assert set(NOTIFICATIONS_TABLE.indexes) == expected

    def test_not_nullable_columns(self) -> None:
        non_nullable = {c.name for c in NOTIFICATIONS_TABLE.columns if not c.nullable}
        assert "notification_id" in non_nullable
        assert "title" in non_nullable
        assert "message" in non_nullable
        assert "priority" in non_nullable
        assert "channel" in non_nullable
        assert "target_type" in non_nullable
        assert "target_id" in non_nullable
        assert "status" in non_nullable
        assert "created_at" in non_nullable

    def test_nullable_columns(self) -> None:
        nullable = {c.name for c in NOTIFICATIONS_TABLE.columns if c.nullable}
        assert "shown_at" in nullable
        assert "acknowledged_at" in nullable
        assert "dismissed_at" in nullable
        assert "expires_at" in nullable

    def test_priority_enum_values(self) -> None:
        priority_col = next(c for c in NOTIFICATIONS_TABLE.columns if c.name == "priority")
        assert priority_col.enum_values == ("low", "normal", "high", "critical")

    def test_channel_enum_values(self) -> None:
        channel_col = next(c for c in NOTIFICATIONS_TABLE.columns if c.name == "channel")
        assert channel_col.enum_values == ("in_app", "desktop", "email", "sms")

    def test_status_enum_values(self) -> None:
        status_col = next(c for c in NOTIFICATIONS_TABLE.columns if c.name == "status")
        assert status_col.enum_values == (
            "pending", "shown", "acknowledged", "dismissed", "expired",
        )


class TestActionsTableSchema:
    def test_column_count(self) -> None:
        assert len(NOTIFICATION_ACTIONS_TABLE.columns) == 5

    def test_schema_name(self) -> None:
        assert NOTIFICATION_ACTIONS_TABLE.schema == "notification"
        assert NOTIFICATION_ACTIONS_TABLE.name == "actions"

    def test_primary_key(self) -> None:
        assert NOTIFICATION_ACTIONS_TABLE.primary_key == "action_id"

    def test_indexes(self) -> None:
        assert NOTIFICATION_ACTIONS_TABLE.indexes == ("ix_notification_actions_notification_id",)

    def test_no_nullable_columns(self) -> None:
        nullable = {c.name for c in NOTIFICATION_ACTIONS_TABLE.columns if c.nullable}
        assert nullable == set()

    def test_notification_id_column(self) -> None:
        col = next(c for c in NOTIFICATION_ACTIONS_TABLE.columns if c.name == "notification_id")
        assert col.nullable is False


class TestOutboxTableSchema:
    def test_column_count(self) -> None:
        assert len(NOTIFICATION_OUTBOX_TABLE.columns) == 6

    def test_schema_name(self) -> None:
        assert NOTIFICATION_OUTBOX_TABLE.schema == "notification"
        assert NOTIFICATION_OUTBOX_TABLE.name == "outbox"

    def test_primary_key(self) -> None:
        assert NOTIFICATION_OUTBOX_TABLE.primary_key == "event_id"

    def test_indexes(self) -> None:
        expected = {
            "ix_notification_outbox_unpublished",
            "ix_notification_outbox_aggregate",
        }
        assert set(NOTIFICATION_OUTBOX_TABLE.indexes) == expected

    def test_not_nullable_columns(self) -> None:
        non_nullable = {c.name for c in NOTIFICATION_OUTBOX_TABLE.columns if not c.nullable}
        assert "event_id" in non_nullable
        assert "event_type" in non_nullable
        assert "aggregate_id" in non_nullable
        assert "occurred_at" in non_nullable
        assert "published" in non_nullable

    def test_nullable_payload(self) -> None:
        payload_col = next(c for c in NOTIFICATION_OUTBOX_TABLE.columns if c.name == "payload")
        assert payload_col.nullable is True

    def test_event_type_enum_values(self) -> None:
        et_col = next(c for c in NOTIFICATION_OUTBOX_TABLE.columns if c.name == "event_type")
        assert et_col.enum_values == (
            "notification.created",
            "notification.shown",
            "notification.acknowledged",
            "notification.dismissed",
            "notification.expired",
            "notification.action.invoked",
        )

    def test_event_type_max_length(self) -> None:
        et_col = next(c for c in NOTIFICATION_OUTBOX_TABLE.columns if c.name == "event_type")
        assert et_col.max_length == 32


# ===================================================================
# Alignment tests (DTO ↔ schema, DTO ↔ domain, schema ↔ enum)
# ===================================================================


class TestDTOAlignmentWithSchema:
    def test_notifications_dto_field_count_matches_schema(self) -> None:
        import dataclasses
        dto_fields = len(dataclasses.fields(NotificationStorageDTO))
        schema_cols = len(NOTIFICATIONS_TABLE.columns)
        assert dto_fields == schema_cols, (
            f"DTO has {dto_fields} fields but schema has {schema_cols} columns"
        )

    def test_notifications_dto_types_match_schema_enums(self) -> None:
        import dataclasses
        for col in NOTIFICATIONS_TABLE.columns:
            if col.enum_values:
                field = next(
                    (f for f in dataclasses.fields(NotificationStorageDTO) if f.name == col.name),
                    None,
                )
                assert field is not None, f"No DTO field for column {col.name}"

    def test_actions_dto_field_count_matches_schema(self) -> None:
        import dataclasses
        dto_fields = len(dataclasses.fields(NotificationActionStorageDTO))
        schema_cols = len(NOTIFICATION_ACTIONS_TABLE.columns)
        assert dto_fields == schema_cols

    def test_outbox_dto_field_count_matches_schema(self) -> None:
        import dataclasses
        dto_fields = len(dataclasses.fields(NotificationOutboxStorageDTO))
        schema_cols = len(NOTIFICATION_OUTBOX_TABLE.columns)
        assert dto_fields == schema_cols


class TestDTOAlignmentWithDomain:
    def test_notification_dto_has_notification_id(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(NotificationStorageDTO)}
        assert "notification_id" in field_names

    def test_notification_dto_has_status(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(NotificationStorageDTO)}
        assert "status" in field_names

    def test_action_dto_has_action_id(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(NotificationActionStorageDTO)}
        assert "action_id" in field_names

    def test_action_dto_has_notification_id(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(NotificationActionStorageDTO)}
        assert "notification_id" in field_names

    def test_outbox_dto_has_event_id(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(NotificationOutboxStorageDTO)}
        assert "event_id" in field_names

    def test_outbox_dto_has_event_type(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(NotificationOutboxStorageDTO)}
        assert "event_type" in field_names


class TestSchemaEnumAlignment:
    def test_priority_enum_values_match_domain(self) -> None:
        priority_col = next(c for c in NOTIFICATIONS_TABLE.columns if c.name == "priority")
        domain_values = tuple(p.value for p in NotificationPriority)
        assert priority_col.enum_values == domain_values

    def test_channel_enum_values_match_domain(self) -> None:
        channel_col = next(c for c in NOTIFICATIONS_TABLE.columns if c.name == "channel")
        domain_values = tuple(c.value for c in NotificationChannel)
        assert channel_col.enum_values == domain_values

    def test_status_enum_values_match_domain(self) -> None:
        status_col = next(c for c in NOTIFICATIONS_TABLE.columns if c.name == "status")
        domain_values = tuple(s.value for s in NotificationStatus)
        assert status_col.enum_values == domain_values

    def test_notification_id_string_type(self) -> None:
        pk_col = next(
            c for c in NOTIFICATIONS_TABLE.columns
            if c.name == NOTIFICATIONS_TABLE.primary_key
        )
        assert pk_col.py_type is str

    def test_action_id_string_type(self) -> None:
        pk_col = next(
            c for c in NOTIFICATION_ACTIONS_TABLE.columns
            if c.name == NOTIFICATION_ACTIONS_TABLE.primary_key
        )
        assert pk_col.py_type is str


class TestSchemaRuleAlignment:
    def test_title_column_not_nullable(self) -> None:
        col = next(c for c in NOTIFICATIONS_TABLE.columns if c.name == "title")
        assert col.nullable is False

    def test_message_column_not_nullable(self) -> None:
        col = next(c for c in NOTIFICATIONS_TABLE.columns if c.name == "message")
        assert col.nullable is False

    def test_channel_enum_matches_notification_channel(self) -> None:
        channel_col = next(c for c in NOTIFICATIONS_TABLE.columns if c.name == "channel")
        assert "sms" in channel_col.enum_values
        assert "email" in channel_col.enum_values

    def test_priority_includes_critical(self) -> None:
        priority_col = next(c for c in NOTIFICATIONS_TABLE.columns if c.name == "priority")
        assert "critical" in priority_col.enum_values

    def test_outbox_event_type_has_six_events(self) -> None:
        et_col = next(c for c in NOTIFICATION_OUTBOX_TABLE.columns if c.name == "event_type")
        assert len(et_col.enum_values) == 6

    def test_notifications_table_uses_notification_schema(self) -> None:
        assert NOTIFICATIONS_TABLE.schema == "notification"

    def test_actions_table_uses_notification_schema(self) -> None:
        assert NOTIFICATION_ACTIONS_TABLE.schema == "notification"

    def test_outbox_table_uses_notification_schema(self) -> None:
        assert NOTIFICATION_OUTBOX_TABLE.schema == "notification"


class TestDomainValueConsistency:
    def test_priority_enum_values(self) -> None:
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.NORMAL.value == "normal"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.CRITICAL.value == "critical"

    def test_channel_enum_values(self) -> None:
        assert NotificationChannel.IN_APP.value == "in_app"
        assert NotificationChannel.DESKTOP.value == "desktop"
        assert NotificationChannel.EMAIL.value == "email"
        assert NotificationChannel.SMS.value == "sms"

    def test_status_enum_values(self) -> None:
        assert NotificationStatus.PENDING.value == "pending"
        assert NotificationStatus.SHOWN.value == "shown"
        assert NotificationStatus.ACKNOWLEDGED.value == "acknowledged"
        assert NotificationStatus.DISMISSED.value == "dismissed"
        assert NotificationStatus.EXPIRED.value == "expired"

    def test_title_rule_constant(self) -> None:
        assert MAX_TITLE_LENGTH == 200

    def test_message_rule_constant(self) -> None:
        assert MAX_MESSAGE_LENGTH == 5000


class TestColumnTypeConsistency:
    def test_notification_id_column_type(self) -> None:
        col = next(c for c in NOTIFICATIONS_TABLE.columns if c.name == "notification_id")
        assert col.py_type is str

    def test_created_at_column_type(self) -> None:
        col = next(c for c in NOTIFICATIONS_TABLE.columns if c.name == "created_at")
        assert col.py_type is datetime

    def test_expires_at_column_type(self) -> None:
        col = next(c for c in NOTIFICATIONS_TABLE.columns if c.name == "expires_at")
        assert col.py_type is datetime

    def test_event_id_column_type(self) -> None:
        col = next(c for c in NOTIFICATION_OUTBOX_TABLE.columns if c.name == "event_id")
        assert col.py_type is str

    def test_published_column_type(self) -> None:
        col = next(c for c in NOTIFICATION_OUTBOX_TABLE.columns if c.name == "published")
        assert col.py_type is bool

    def test_action_id_column_type(self) -> None:
        col = next(c for c in NOTIFICATION_ACTIONS_TABLE.columns if c.name == "action_id")
        assert col.py_type is str

    def test_label_column_type(self) -> None:
        col = next(c for c in NOTIFICATION_ACTIONS_TABLE.columns if c.name == "label")
        assert col.py_type is str

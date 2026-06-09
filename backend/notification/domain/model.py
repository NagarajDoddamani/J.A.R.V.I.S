from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import auto, StrEnum
from uuid import UUID, uuid4


# =============================================================================
# Enums
# =============================================================================


class NotificationStatus(StrEnum):
    PENDING = auto()
    SHOWN = auto()
    ACKNOWLEDGED = auto()
    DISMISSED = auto()
    EXPIRED = auto()


class NotificationPriority(StrEnum):
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    CRITICAL = auto()


class NotificationChannel(StrEnum):
    IN_APP = auto()
    DESKTOP = auto()
    EMAIL = auto()
    SMS = auto()


# =============================================================================
# Value Objects
# =============================================================================


@dataclass(frozen=True)
class NotificationId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class ActionId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class NotificationTitle:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"NotificationTitle value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.notification.domain.exceptions import InvalidNotificationTitleError
            raise InvalidNotificationTitleError("Notification title must not be empty")
        if len(self.value) > 200:
            from backend.notification.domain.exceptions import InvalidNotificationTitleError
            raise InvalidNotificationTitleError(
                f"Notification title length {len(self.value)} exceeds maximum 200"
            )

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class NotificationMessage:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            msg = f"NotificationMessage value must be a string, got {type(self.value).__name__}"
            raise TypeError(msg)
        if not self.value.strip():
            from backend.notification.domain.exceptions import InvalidNotificationMessageError
            raise InvalidNotificationMessageError("Notification message must not be empty")
        if len(self.value) > 5000:
            from backend.notification.domain.exceptions import InvalidNotificationMessageError
            raise InvalidNotificationMessageError(
                f"Notification message length {len(self.value)} exceeds maximum 5000"
            )

    def __str__(self) -> str:
        return self.value

    def __len__(self) -> int:
        return len(self.value)


@dataclass(frozen=True)
class NotificationTarget:
    target_type: str
    target_id: str

    def __post_init__(self) -> None:
        if not self.target_type or not self.target_type.strip():
            from backend.notification.domain.exceptions import InvalidNotificationTargetError
            raise InvalidNotificationTargetError("target_type must not be empty")
        if not self.target_id or not self.target_id.strip():
            from backend.notification.domain.exceptions import InvalidNotificationTargetError
            raise InvalidNotificationTargetError("target_id must not be empty")

    def __str__(self) -> str:
        return f"{self.target_type}:{self.target_id}"


@dataclass(frozen=True)
class ExpirationPolicy:
    expires_at: datetime

    def __post_init__(self) -> None:
        from backend.notification.domain.exceptions import InvalidExpirationError
        if self.expires_at.tzinfo is None:
            object.__setattr__(
                self, "expires_at", self.expires_at.replace(tzinfo=timezone.utc)
            )
        if self.expires_at <= datetime.now(tz=timezone.utc):
            raise InvalidExpirationError("Expiration must be in the future")


# =============================================================================
# Domain Events
# =============================================================================


@dataclass(frozen=True)
class NotificationCreated:
    notification_id: NotificationId
    title: str
    message: str
    priority: str
    channel: str
    target_type: str
    target_id: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class NotificationShown:
    notification_id: NotificationId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class NotificationAcknowledged:
    notification_id: NotificationId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class NotificationDismissed:
    notification_id: NotificationId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class NotificationExpired:
    notification_id: NotificationId
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class NotificationActionInvoked:
    notification_id: NotificationId
    action_id: ActionId
    callback_name: str
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


# =============================================================================
# Entities
# =============================================================================


class Notification:
    """Aggregate root for the notification domain."""

    def __init__(
        self,
        notification_id: NotificationId | None = None,
        title: NotificationTitle | None = None,
        message: NotificationMessage | None = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        target: NotificationTarget | None = None,
        status: NotificationStatus = NotificationStatus.PENDING,
        created_at: datetime | None = None,
        shown_at: datetime | None = None,
        acknowledged_at: datetime | None = None,
        dismissed_at: datetime | None = None,
        expires_at: datetime | None = None,
    ) -> None:
        self._notification_id = notification_id or NotificationId()
        self._title = title
        self._message = message
        self._priority = priority
        self._channel = channel
        self._target = target
        self._status = status
        self._created_at = created_at or datetime.now(tz=timezone.utc)
        self._shown_at = shown_at
        self._acknowledged_at = acknowledged_at
        self._dismissed_at = dismissed_at
        self._expires_at = expires_at
        self._events: list[NotificationShown | NotificationAcknowledged | NotificationDismissed | NotificationExpired] = []

    # -- properties ---------------------------------------------------------

    @property
    def notification_id(self) -> NotificationId:
        return self._notification_id

    @property
    def title(self) -> NotificationTitle | None:
        return self._title

    @property
    def message(self) -> NotificationMessage | None:
        return self._message

    @property
    def priority(self) -> NotificationPriority:
        return self._priority

    @property
    def channel(self) -> NotificationChannel:
        return self._channel

    @property
    def target(self) -> NotificationTarget | None:
        return self._target

    @property
    def status(self) -> NotificationStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def shown_at(self) -> datetime | None:
        return self._shown_at

    @property
    def acknowledged_at(self) -> datetime | None:
        return self._acknowledged_at

    @property
    def dismissed_at(self) -> datetime | None:
        return self._dismissed_at

    @property
    def expires_at(self) -> datetime | None:
        return self._expires_at

    @property
    def events(self) -> list[NotificationShown | NotificationAcknowledged | NotificationDismissed | NotificationExpired]:
        return list(self._events)

    @property
    def is_expired(self) -> bool:
        if self._status == NotificationStatus.EXPIRED:
            return True
        if self._expires_at is not None and self._expires_at < datetime.now(tz=timezone.utc):
            return True
        return False

    @property
    def is_dismissed(self) -> bool:
        return self._status == NotificationStatus.DISMISSED

    # -- commands -----------------------------------------------------------

    def show(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.notification.domain.rules import assert_notification_can_transition, assert_not_immutable

        assert_not_immutable(self)
        assert_notification_can_transition(self._status, NotificationStatus.SHOWN)
        self._status = NotificationStatus.SHOWN
        self._shown_at = now
        self._events.append(
            NotificationShown(notification_id=self._notification_id, occurred_at=now)
        )

    def acknowledge(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.notification.domain.rules import assert_notification_can_transition, assert_not_immutable

        assert_not_immutable(self)
        assert_notification_can_transition(self._status, NotificationStatus.ACKNOWLEDGED)
        self._status = NotificationStatus.ACKNOWLEDGED
        self._acknowledged_at = now
        self._events.append(
            NotificationAcknowledged(notification_id=self._notification_id, occurred_at=now)
        )

    def dismiss(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.notification.domain.rules import assert_notification_can_transition, assert_not_immutable

        assert_not_immutable(self)
        assert_notification_can_transition(self._status, NotificationStatus.DISMISSED)
        self._status = NotificationStatus.DISMISSED
        self._dismissed_at = now
        self._events.append(
            NotificationDismissed(notification_id=self._notification_id, occurred_at=now)
        )

    def expire(self) -> None:
        now = datetime.now(tz=timezone.utc)
        from backend.notification.domain.rules import assert_notification_can_transition, assert_not_immutable

        assert_not_immutable(self)
        assert_notification_can_transition(self._status, NotificationStatus.EXPIRED)
        self._status = NotificationStatus.EXPIRED
        self._events.append(
            NotificationExpired(notification_id=self._notification_id, occurred_at=now)
        )

    # -- internal -----------------------------------------------------------

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"Notification(id={self._notification_id}, "
            f"status={self._status.value}, "
            f"priority={self._priority.value})"
        )


class NotificationAction:
    """Action that can be invoked on a notification."""

    def __init__(
        self,
        action_id: ActionId | None = None,
        notification_id: NotificationId | None = None,
        label: str = "",
        callback_name: str = "",
        created_at: datetime | None = None,
    ) -> None:
        self._action_id = action_id or ActionId()
        self._notification_id = notification_id
        self._label = label
        self._callback_name = callback_name
        self._created_at = created_at or datetime.now(tz=timezone.utc)
        self._events: list[NotificationActionInvoked] = []

    # -- properties ---------------------------------------------------------

    @property
    def action_id(self) -> ActionId:
        return self._action_id

    @property
    def notification_id(self) -> NotificationId | None:
        return self._notification_id

    @property
    def label(self) -> str:
        return self._label

    @property
    def callback_name(self) -> str:
        return self._callback_name

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def events(self) -> list[NotificationActionInvoked]:
        return list(self._events)

    # -- commands -----------------------------------------------------------

    def invoke(self) -> NotificationActionInvoked:
        now = datetime.now(tz=timezone.utc)
        event = NotificationActionInvoked(
            notification_id=self._notification_id,
            action_id=self._action_id,
            callback_name=self._callback_name,
            occurred_at=now,
        )
        self._events.append(event)
        return event

    # -- internal -----------------------------------------------------------

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"NotificationAction(id={self._action_id}, "
            f"label={self._label!r}, "
            f"callback={self._callback_name!r})"
        )

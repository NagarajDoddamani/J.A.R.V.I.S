from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.notification.application.ports.clock import NotificationClockPort
from backend.notification.application.ports.id_generator import (
    NotificationIdGeneratorPort,
)
from backend.notification.application.ports.outbox import (
    NotificationOutboxPort,
)
from backend.notification.application.ports.repository import (
    NotificationActionRepositoryPort,
    NotificationRepositoryPort,
)
from backend.notification.application.use_cases.acknowledge_notification import (
    AcknowledgeNotificationUseCase,
)
from backend.notification.application.use_cases.create_action import (
    CreateActionUseCase,
)
from backend.notification.application.use_cases.create_notification import (
    CreateNotificationUseCase,
)
from backend.notification.application.use_cases.dismiss_notification import (
    DismissNotificationUseCase,
)
from backend.notification.application.use_cases.dto import (
    AcknowledgeNotificationRequest,
    AcknowledgeNotificationResponse,
    CreateActionRequest,
    CreateActionResponse,
    CreateNotificationRequest,
    CreateNotificationResponse,
    DismissNotificationRequest,
    DismissNotificationResponse,
    ExpireNotificationRequest,
    ExpireNotificationResponse,
    GetNotificationRequest,
    InvokeActionRequest,
    InvokeActionResponse,
    ListNotificationsRequest,
    ListNotificationsResponse,
    NotificationActionResponse,
    NotificationResponse,
    ShowNotificationRequest,
    ShowNotificationResponse,
)
from backend.notification.application.use_cases.exceptions import (
    NotificationActionNotFoundError,
    NotificationNotFoundError,
    UseCaseError,
)
from backend.notification.application.use_cases.expire_notification import (
    ExpireNotificationUseCase,
)
from backend.notification.application.use_cases.get_notification import (
    GetNotificationUseCase,
)
from backend.notification.application.use_cases.invoke_action import (
    InvokeActionUseCase,
)
from backend.notification.application.use_cases.list_notifications import (
    ListNotificationsUseCase,
)
from backend.notification.application.use_cases.show_notification import (
    ShowNotificationUseCase,
)
from backend.notification.domain.exceptions import (
    InvalidActionLabelError,
    InvalidCallbackError,
    InvalidNotificationTransitionError,
    InvalidNotificationTargetError,
    NotificationDismissedError,
    NotificationExpiredError,
    SecretDetectedError,
)
from backend.notification.domain.model import (
    ActionId,
    Notification,
    NotificationAction,
    NotificationAcknowledged,
    NotificationActionInvoked,
    NotificationChannel,
    NotificationCreated,
    NotificationDismissed,
    NotificationExpired,
    NotificationId,
    NotificationPriority,
    NotificationShown,
    NotificationStatus,
    NotificationTarget,
    NotificationTitle,
    NotificationMessage,
)

# ===================================================================
# Fake port implementations (in-memory)
# ===================================================================


class FakeNotificationRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, Notification] = {}
        self.save_calls: list[Notification] = []

    def save(self, notification: Notification) -> None:
        self._store[notification.notification_id.value] = notification
        self.save_calls.append(notification)

    def find_by_id(
        self, notification_id: NotificationId
    ) -> Notification | None:
        return self._store.get(notification_id.value)

    def find_by_status(
        self, status: NotificationStatus
    ) -> list[Notification]:
        return [n for n in self._store.values() if n.status == status]

    def find_by_priority(
        self, priority: NotificationPriority
    ) -> list[Notification]:
        return [n for n in self._store.values() if n.priority == priority]

    def find_by_target(
        self, target_type: str, target_id: str
    ) -> list[Notification]:
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


class FakeNotificationActionRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, NotificationAction] = {}
        self.save_calls: list[NotificationAction] = []

    def save(self, action: NotificationAction) -> None:
        self._store[action.action_id.value] = action
        self.save_calls.append(action)

    def find_by_id(
        self, action_id: ActionId
    ) -> NotificationAction | None:
        return self._store.get(action_id.value)

    def find_by_notification_id(
        self, notification_id: NotificationId
    ) -> list[NotificationAction]:
        return [
            a
            for a in self._store.values()
            if a.notification_id is not None
            and a.notification_id.value == notification_id.value
        ]

    def count(self) -> int:
        return len(self._store)


class FakeNotificationOutbox:
    def __init__(self) -> None:
        self._events: list = []
        self.append_calls: list = []

    def append(self, event: object) -> None:
        self._events.append(event)
        self.append_calls.append(event)

    def fetch_unpublished(self, limit: int = 100) -> list:
        return list(self._events[:limit])

    def mark_published(self, notification_id: str) -> None:
        pass


class FakeClock:
    def __init__(self, fixed: datetime | None = None) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        if self._fixed is not None:
            return self._fixed
        return datetime.now(tz=timezone.utc)


class FakeIdGenerator:
    def generate_notification_id(self) -> NotificationId:
        return NotificationId()

    def generate_action_id(self) -> ActionId:
        return ActionId()


# ===================================================================
# Fixtures
# ===================================================================


FUTURE = datetime(2099, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def fake_notification_repo() -> FakeNotificationRepository:
    return FakeNotificationRepository()


@pytest.fixture
def fake_action_repo() -> FakeNotificationActionRepository:
    return FakeNotificationActionRepository()


@pytest.fixture
def fake_outbox() -> FakeNotificationOutbox:
    return FakeNotificationOutbox()


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def fake_id_gen() -> FakeIdGenerator:
    return FakeIdGenerator()


@pytest.fixture
def create_use_case(
    fake_notification_repo: FakeNotificationRepository,
    fake_outbox: FakeNotificationOutbox,
) -> CreateNotificationUseCase:
    return CreateNotificationUseCase(
        notification_repo=fake_notification_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def show_use_case(
    fake_notification_repo: FakeNotificationRepository,
    fake_outbox: FakeNotificationOutbox,
) -> ShowNotificationUseCase:
    return ShowNotificationUseCase(
        notification_repo=fake_notification_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def acknowledge_use_case(
    fake_notification_repo: FakeNotificationRepository,
    fake_outbox: FakeNotificationOutbox,
) -> AcknowledgeNotificationUseCase:
    return AcknowledgeNotificationUseCase(
        notification_repo=fake_notification_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def dismiss_use_case(
    fake_notification_repo: FakeNotificationRepository,
    fake_outbox: FakeNotificationOutbox,
) -> DismissNotificationUseCase:
    return DismissNotificationUseCase(
        notification_repo=fake_notification_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def expire_use_case(
    fake_notification_repo: FakeNotificationRepository,
    fake_outbox: FakeNotificationOutbox,
) -> ExpireNotificationUseCase:
    return ExpireNotificationUseCase(
        notification_repo=fake_notification_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def get_use_case(
    fake_notification_repo: FakeNotificationRepository,
) -> GetNotificationUseCase:
    return GetNotificationUseCase(
        notification_repo=fake_notification_repo,
    )


@pytest.fixture
def list_use_case(
    fake_notification_repo: FakeNotificationRepository,
) -> ListNotificationsUseCase:
    return ListNotificationsUseCase(
        notification_repo=fake_notification_repo,
    )


@pytest.fixture
def create_action_use_case(
    fake_notification_repo: FakeNotificationRepository,
    fake_action_repo: FakeNotificationActionRepository,
) -> CreateActionUseCase:
    return CreateActionUseCase(
        notification_repo=fake_notification_repo,
        action_repo=fake_action_repo,
    )


@pytest.fixture
def invoke_action_use_case(
    fake_action_repo: FakeNotificationActionRepository,
    fake_notification_repo: FakeNotificationRepository,
    fake_outbox: FakeNotificationOutbox,
) -> InvokeActionUseCase:
    return InvokeActionUseCase(
        action_repo=fake_action_repo,
        notification_repo=fake_notification_repo,
        outbox=fake_outbox,
    )


# ===================================================================
# Helpers
# ===================================================================


def _create_notification(
    create_use_case: CreateNotificationUseCase,
    *,
    title: str = "Test title",
    message: str = "Test message",
    priority: str = "normal",
    channel: str = "in_app",
    target_type: str = "user",
    target_id: str = "user-001",
    expires_at: datetime | None = None,
) -> CreateNotificationResponse:
    return create_use_case.execute(
        CreateNotificationRequest(
            title=title,
            message=message,
            priority=priority,
            channel=channel,
            target_type=target_type,
            target_id=target_id,
            expires_at=expires_at,
        )
    )


def _create_and_show(
    create_use_case: CreateNotificationUseCase,
    show_use_case: ShowNotificationUseCase,
    *,
    title: str = "Test title",
    message: str = "Test message",
) -> tuple[str, CreateNotificationResponse, ShowNotificationResponse]:
    create_resp = _create_notification(create_use_case, title=title, message=message)
    show_resp = show_use_case.execute(
        ShowNotificationRequest(notification_id=create_resp.notification_id)
    )
    return create_resp.notification_id, create_resp, show_resp


# ===================================================================
# CreateNotificationUseCase Tests
# ===================================================================


class TestCreateNotificationUseCase:
    def test_happy_path(
        self,
        create_use_case: CreateNotificationUseCase,
        fake_notification_repo: FakeNotificationRepository,
        fake_outbox: FakeNotificationOutbox,
    ) -> None:
        response = _create_notification(create_use_case)

        assert response.title == "Test title"
        assert response.message == "Test message"
        assert response.priority == "normal"
        assert response.channel == "in_app"
        assert response.target_type == "user"
        assert response.target_id == "user-001"
        assert response.status == "pending"
        assert response.expires_at is None

        stored = fake_notification_repo.find_by_id(
            NotificationId(value=UUID(response.notification_id))
        )
        assert stored is not None

        assert len(fake_outbox.append_calls) == 1
        assert isinstance(fake_outbox.append_calls[0], NotificationCreated)

    def test_notification_persisted(
        self,
        create_use_case: CreateNotificationUseCase,
        fake_notification_repo: FakeNotificationRepository,
    ) -> None:
        response = _create_notification(create_use_case)
        assert fake_notification_repo.count() == 1

        stored = fake_notification_repo.find_by_id(
            NotificationId(value=UUID(response.notification_id))
        )
        assert stored is not None
        assert str(stored.title) == "Test title"
        assert str(stored.message) == "Test message"

    def test_notification_created_event_emitted(
        self,
        create_use_case: CreateNotificationUseCase,
        fake_outbox: FakeNotificationOutbox,
    ) -> None:
        response = _create_notification(create_use_case)
        assert len(fake_outbox.append_calls) == 1
        event = fake_outbox.append_calls[0]
        assert isinstance(event, NotificationCreated)
        assert str(event.notification_id) == response.notification_id
        assert event.title == "Test title"
        assert event.priority == "normal"

    def test_response_fields_populated(
        self,
        create_use_case: CreateNotificationUseCase,
    ) -> None:
        response = _create_notification(
            create_use_case,
            title="Custom title",
            message="Custom message",
            priority="high",
            channel="desktop",
            target_type="admin",
            target_id="admin-001",
        )
        assert isinstance(response, CreateNotificationResponse)
        assert response.title == "Custom title"
        assert response.message == "Custom message"
        assert response.priority == "high"
        assert response.channel == "desktop"
        assert response.target_type == "admin"
        assert response.target_id == "admin-001"
        assert response.created_at is not None

    def test_expires_at(
        self,
        create_use_case: CreateNotificationUseCase,
    ) -> None:
        response = _create_notification(
            create_use_case, expires_at=FUTURE
        )
        assert response.expires_at is not None
        assert response.expires_at == FUTURE

    def test_critical_notification_rejects_sms(
        self,
        create_use_case: CreateNotificationUseCase,
    ) -> None:
        with pytest.raises(Exception, match="SMS"):
            create_use_case.execute(
                CreateNotificationRequest(
                    title="Critical alert",
                    message="Something important",
                    priority="critical",
                    channel="sms",
                    target_type="user",
                    target_id="user-001",
                )
            )

    def test_invalid_target_rejected(
        self,
        create_use_case: CreateNotificationUseCase,
    ) -> None:
        with pytest.raises(InvalidNotificationTargetError):
            create_use_case.execute(
                CreateNotificationRequest(
                    title="Test",
                    message="Test",
                    target_type="",
                    target_id="",
                )
            )

    def test_secret_in_title_rejected(
        self,
        create_use_case: CreateNotificationUseCase,
    ) -> None:
        with pytest.raises(SecretDetectedError):
            _create_notification(create_use_case, title="my password is secret")

    def test_secret_in_message_rejected(
        self,
        create_use_case: CreateNotificationUseCase,
    ) -> None:
        with pytest.raises(SecretDetectedError):
            _create_notification(create_use_case, message="api_key=abc123")

    def test_save_called(
        self,
        create_use_case: CreateNotificationUseCase,
        fake_notification_repo: FakeNotificationRepository,
    ) -> None:
        _create_notification(create_use_case)
        assert len(fake_notification_repo.save_calls) == 1

    def test_multiple_notifications(
        self,
        create_use_case: CreateNotificationUseCase,
        fake_notification_repo: FakeNotificationRepository,
    ) -> None:
        _create_notification(create_use_case, title="First")
        _create_notification(create_use_case, title="Second")
        assert fake_notification_repo.count() == 2


# ===================================================================
# ShowNotificationUseCase Tests
# ===================================================================


class TestShowNotificationUseCase:
    def test_pending_to_shown(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        response = show_use_case.execute(
            ShowNotificationRequest(
                notification_id=create_resp.notification_id
            )
        )
        assert response.status == "shown"
        assert response.shown_at is not None
        assert isinstance(response, ShowNotificationResponse)

    def test_event_emitted(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
        fake_outbox: FakeNotificationOutbox,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        show_use_case.execute(
            ShowNotificationRequest(
                notification_id=create_resp.notification_id
            )
        )
        shown_events = [
            e
            for e in fake_outbox.append_calls
            if isinstance(e, NotificationShown)
        ]
        assert len(shown_events) == 1
        assert str(shown_events[0].notification_id) == create_resp.notification_id

    def test_save_called(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
        fake_notification_repo: FakeNotificationRepository,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        show_use_case.execute(
            ShowNotificationRequest(
                notification_id=create_resp.notification_id
            )
        )
        assert len(fake_notification_repo.save_calls) == 2

    def test_missing_notification_raises_error(
        self,
        show_use_case: ShowNotificationUseCase,
    ) -> None:
        with pytest.raises(NotificationNotFoundError):
            show_use_case.execute(
                ShowNotificationRequest(
                    notification_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_repeated_show_rejected(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        show_use_case.execute(
            ShowNotificationRequest(
                notification_id=create_resp.notification_id
            )
        )
        with pytest.raises(InvalidNotificationTransitionError):
            show_use_case.execute(
                ShowNotificationRequest(
                    notification_id=create_resp.notification_id
                )
            )

    def test_stored_notification_status_updated(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
        fake_notification_repo: FakeNotificationRepository,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        show_use_case.execute(
            ShowNotificationRequest(
                notification_id=create_resp.notification_id
            )
        )
        stored = fake_notification_repo.find_by_id(
            NotificationId(value=UUID(create_resp.notification_id))
        )
        assert stored is not None
        assert stored.status == NotificationStatus.SHOWN
        assert stored.shown_at is not None


# ===================================================================
# AcknowledgeNotificationUseCase Tests
# ===================================================================


class TestAcknowledgeNotificationUseCase:
    def test_shown_to_acknowledged(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
        acknowledge_use_case: AcknowledgeNotificationUseCase,
    ) -> None:
        notification_id, _, _ = _create_and_show(
            create_use_case, show_use_case
        )
        response = acknowledge_use_case.execute(
            AcknowledgeNotificationRequest(notification_id=notification_id)
        )
        assert response.status == "acknowledged"
        assert response.acknowledged_at is not None
        assert isinstance(response, AcknowledgeNotificationResponse)

    def test_event_emitted(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
        acknowledge_use_case: AcknowledgeNotificationUseCase,
        fake_outbox: FakeNotificationOutbox,
    ) -> None:
        notification_id, _, _ = _create_and_show(
            create_use_case, show_use_case
        )
        acknowledge_use_case.execute(
            AcknowledgeNotificationRequest(notification_id=notification_id)
        )
        ack_events = [
            e
            for e in fake_outbox.append_calls
            if isinstance(e, NotificationAcknowledged)
        ]
        assert len(ack_events) == 1
        assert str(ack_events[0].notification_id) == notification_id

    def test_missing_notification_raises_error(
        self,
        acknowledge_use_case: AcknowledgeNotificationUseCase,
    ) -> None:
        with pytest.raises(NotificationNotFoundError):
            acknowledge_use_case.execute(
                AcknowledgeNotificationRequest(
                    notification_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_acknowledge_before_shown_blocked(
        self,
        create_use_case: CreateNotificationUseCase,
        acknowledge_use_case: AcknowledgeNotificationUseCase,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        with pytest.raises(InvalidNotificationTransitionError):
            acknowledge_use_case.execute(
                AcknowledgeNotificationRequest(
                    notification_id=create_resp.notification_id
                )
            )

    def test_repeated_acknowledge_blocked(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
        acknowledge_use_case: AcknowledgeNotificationUseCase,
    ) -> None:
        notification_id, _, _ = _create_and_show(
            create_use_case, show_use_case
        )
        acknowledge_use_case.execute(
            AcknowledgeNotificationRequest(notification_id=notification_id)
        )
        with pytest.raises(InvalidNotificationTransitionError):
            acknowledge_use_case.execute(
                AcknowledgeNotificationRequest(notification_id=notification_id)
            )

    def test_save_called(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
        acknowledge_use_case: AcknowledgeNotificationUseCase,
        fake_notification_repo: FakeNotificationRepository,
    ) -> None:
        notification_id, _, _ = _create_and_show(
            create_use_case, show_use_case
        )
        acknowledge_use_case.execute(
            AcknowledgeNotificationRequest(notification_id=notification_id)
        )
        assert len(fake_notification_repo.save_calls) == 3


# ===================================================================
# DismissNotificationUseCase Tests
# ===================================================================


class TestDismissNotificationUseCase:
    def test_shown_to_dismissed(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
        dismiss_use_case: DismissNotificationUseCase,
    ) -> None:
        notification_id, _, _ = _create_and_show(
            create_use_case, show_use_case
        )
        response = dismiss_use_case.execute(
            DismissNotificationRequest(notification_id=notification_id)
        )
        assert response.status == "dismissed"
        assert response.dismissed_at is not None
        assert isinstance(response, DismissNotificationResponse)

    def test_event_emitted(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
        dismiss_use_case: DismissNotificationUseCase,
        fake_outbox: FakeNotificationOutbox,
    ) -> None:
        notification_id, _, _ = _create_and_show(
            create_use_case, show_use_case
        )
        dismiss_use_case.execute(
            DismissNotificationRequest(notification_id=notification_id)
        )
        dismiss_events = [
            e
            for e in fake_outbox.append_calls
            if isinstance(e, NotificationDismissed)
        ]
        assert len(dismiss_events) == 1
        assert str(dismiss_events[0].notification_id) == notification_id

    def test_missing_notification_raises_error(
        self,
        dismiss_use_case: DismissNotificationUseCase,
    ) -> None:
        with pytest.raises(NotificationNotFoundError):
            dismiss_use_case.execute(
                DismissNotificationRequest(
                    notification_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_dismiss_before_shown_blocked(
        self,
        create_use_case: CreateNotificationUseCase,
        dismiss_use_case: DismissNotificationUseCase,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        with pytest.raises(InvalidNotificationTransitionError):
            dismiss_use_case.execute(
                DismissNotificationRequest(
                    notification_id=create_resp.notification_id
                )
            )

    def test_repeated_dismiss_blocked(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
        dismiss_use_case: DismissNotificationUseCase,
    ) -> None:
        notification_id, _, _ = _create_and_show(
            create_use_case, show_use_case
        )
        dismiss_use_case.execute(
            DismissNotificationRequest(notification_id=notification_id)
        )
        with pytest.raises(NotificationDismissedError):
            dismiss_use_case.execute(
                DismissNotificationRequest(notification_id=notification_id)
            )

    def test_save_called(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
        dismiss_use_case: DismissNotificationUseCase,
        fake_notification_repo: FakeNotificationRepository,
    ) -> None:
        notification_id, _, _ = _create_and_show(
            create_use_case, show_use_case
        )
        dismiss_use_case.execute(
            DismissNotificationRequest(notification_id=notification_id)
        )
        assert len(fake_notification_repo.save_calls) == 3


# ===================================================================
# ExpireNotificationUseCase Tests
# ===================================================================


class TestExpireNotificationUseCase:
    def test_pending_to_expired(
        self,
        create_use_case: CreateNotificationUseCase,
        expire_use_case: ExpireNotificationUseCase,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        response = expire_use_case.execute(
            ExpireNotificationRequest(
                notification_id=create_resp.notification_id
            )
        )
        assert response.status == "expired"
        assert isinstance(response, ExpireNotificationResponse)

    def test_shown_to_expired(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
        expire_use_case: ExpireNotificationUseCase,
    ) -> None:
        notification_id, _, _ = _create_and_show(
            create_use_case, show_use_case
        )
        response = expire_use_case.execute(
            ExpireNotificationRequest(notification_id=notification_id)
        )
        assert response.status == "expired"

    def test_acknowledged_to_expired(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
        acknowledge_use_case: AcknowledgeNotificationUseCase,
        expire_use_case: ExpireNotificationUseCase,
    ) -> None:
        notification_id, _, _ = _create_and_show(
            create_use_case, show_use_case
        )
        acknowledge_use_case.execute(
            AcknowledgeNotificationRequest(notification_id=notification_id)
        )
        response = expire_use_case.execute(
            ExpireNotificationRequest(notification_id=notification_id)
        )
        assert response.status == "expired"

    def test_event_emitted(
        self,
        create_use_case: CreateNotificationUseCase,
        expire_use_case: ExpireNotificationUseCase,
        fake_outbox: FakeNotificationOutbox,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        expire_use_case.execute(
            ExpireNotificationRequest(
                notification_id=create_resp.notification_id
            )
        )
        expire_events = [
            e
            for e in fake_outbox.append_calls
            if isinstance(e, NotificationExpired)
        ]
        assert len(expire_events) == 1
        assert str(expire_events[0].notification_id) == create_resp.notification_id

    def test_missing_notification_raises_error(
        self,
        expire_use_case: ExpireNotificationUseCase,
    ) -> None:
        with pytest.raises(NotificationNotFoundError):
            expire_use_case.execute(
                ExpireNotificationRequest(
                    notification_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_expired_remains_terminal(
        self,
        create_use_case: CreateNotificationUseCase,
        expire_use_case: ExpireNotificationUseCase,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        expire_use_case.execute(
            ExpireNotificationRequest(
                notification_id=create_resp.notification_id
            )
        )
        with pytest.raises(NotificationExpiredError):
            expire_use_case.execute(
                ExpireNotificationRequest(
                    notification_id=create_resp.notification_id
                )
            )

    def test_dismissed_cannot_expire(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
        dismiss_use_case: DismissNotificationUseCase,
        expire_use_case: ExpireNotificationUseCase,
    ) -> None:
        notification_id, _, _ = _create_and_show(
            create_use_case, show_use_case
        )
        dismiss_use_case.execute(
            DismissNotificationRequest(notification_id=notification_id)
        )
        with pytest.raises(NotificationDismissedError):
            expire_use_case.execute(
                ExpireNotificationRequest(notification_id=notification_id)
            )

    def test_save_called(
        self,
        create_use_case: CreateNotificationUseCase,
        expire_use_case: ExpireNotificationUseCase,
        fake_notification_repo: FakeNotificationRepository,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        expire_use_case.execute(
            ExpireNotificationRequest(
                notification_id=create_resp.notification_id
            )
        )
        assert len(fake_notification_repo.save_calls) == 2


# ===================================================================
# GetNotificationUseCase Tests
# ===================================================================


class TestGetNotificationUseCase:
    def test_existing_notification(
        self,
        create_use_case: CreateNotificationUseCase,
        get_use_case: GetNotificationUseCase,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        response = get_use_case.execute(
            GetNotificationRequest(
                notification_id=create_resp.notification_id
            )
        )
        assert isinstance(response, NotificationResponse)
        assert response.notification_id == create_resp.notification_id
        assert response.title == "Test title"
        assert response.status == "pending"

    def test_missing_notification_raises_error(
        self,
        get_use_case: GetNotificationUseCase,
    ) -> None:
        with pytest.raises(NotificationNotFoundError):
            get_use_case.execute(
                GetNotificationRequest(
                    notification_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_all_fields_mapped(
        self,
        create_use_case: CreateNotificationUseCase,
        get_use_case: GetNotificationUseCase,
    ) -> None:
        create_resp = _create_notification(
            create_use_case,
            title="Full fields",
            message="All fields test",
            priority="high",
            channel="desktop",
            target_type="admin",
            target_id="admin-001",
        )
        response = get_use_case.execute(
            GetNotificationRequest(
                notification_id=create_resp.notification_id
            )
        )
        assert response.notification_id == create_resp.notification_id
        assert response.title == "Full fields"
        assert response.message == "All fields test"
        assert response.priority == "high"
        assert response.channel == "desktop"
        assert response.target_type == "admin"
        assert response.target_id == "admin-001"
        assert response.status == "pending"
        assert response.created_at is not None
        assert response.shown_at is None
        assert response.acknowledged_at is None
        assert response.dismissed_at is None

    def test_error_is_use_case_error(
        self,
        get_use_case: GetNotificationUseCase,
    ) -> None:
        with pytest.raises(UseCaseError):
            get_use_case.execute(
                GetNotificationRequest(
                    notification_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_response_after_state_transition(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
        get_use_case: GetNotificationUseCase,
    ) -> None:
        notification_id, _, _ = _create_and_show(
            create_use_case, show_use_case
        )
        response = get_use_case.execute(
            GetNotificationRequest(notification_id=notification_id)
        )
        assert response.status == "shown"
        assert response.shown_at is not None


# ===================================================================
# ListNotificationsUseCase Tests
# ===================================================================


class TestListNotificationsUseCase:
    @pytest.fixture
    def setup_notifications(
        self,
        create_use_case: CreateNotificationUseCase,
    ) -> dict[str, str]:
        id1 = _create_notification(
            create_use_case,
            title="High priority",
            priority="high",
            target_type="user",
            target_id="user-001",
        ).notification_id

        id2 = _create_notification(
            create_use_case,
            title="Critical alert",
            priority="critical",
            channel="desktop",
            target_type="admin",
            target_id="admin-001",
        ).notification_id

        id3 = _create_notification(
            create_use_case,
            title="Low priority",
            priority="low",
            target_type="user",
            target_id="user-002",
        ).notification_id

        return {
            "high": id1,
            "critical": id2,
            "low": id3,
        }

    def test_no_filters_returns_all(
        self,
        list_use_case: ListNotificationsUseCase,
        setup_notifications: dict[str, str],
    ) -> None:
        response = list_use_case.execute(ListNotificationsRequest())
        assert response.total == 3
        assert len(response.notifications) == 3

    def test_status_filter(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
        list_use_case: ListNotificationsUseCase,
    ) -> None:
        _create_notification(create_use_case, title="Pending")
        shown_id = _create_notification(
            create_use_case, title="Shown"
        ).notification_id
        show_use_case.execute(
            ShowNotificationRequest(notification_id=shown_id)
        )

        response = list_use_case.execute(
            ListNotificationsRequest(status="shown")
        )
        assert response.total == 1
        assert response.notifications[0].title == "Shown"

    def test_priority_filter(
        self,
        list_use_case: ListNotificationsUseCase,
        setup_notifications: dict[str, str],
    ) -> None:
        response = list_use_case.execute(
            ListNotificationsRequest(priority="critical")
        )
        assert response.total == 1
        assert response.notifications[0].title == "Critical alert"

    def test_target_type_filter(
        self,
        list_use_case: ListNotificationsUseCase,
        setup_notifications: dict[str, str],
    ) -> None:
        response = list_use_case.execute(
            ListNotificationsRequest(
                target_type="admin", target_id="admin-001"
            )
        )
        assert response.total == 1
        assert response.notifications[0].title == "Critical alert"

    def test_target_id_filter(
        self,
        list_use_case: ListNotificationsUseCase,
        setup_notifications: dict[str, str],
    ) -> None:
        response = list_use_case.execute(
            ListNotificationsRequest(
                target_type="user", target_id="user-001"
            )
        )
        assert response.total == 1
        assert response.notifications[0].title == "High priority"

    def test_combined_filters(
        self,
        list_use_case: ListNotificationsUseCase,
        setup_notifications: dict[str, str],
    ) -> None:
        response = list_use_case.execute(
            ListNotificationsRequest(
                priority="high",
                target_type="user",
                target_id="user-001",
            )
        )
        assert response.total == 1
        assert response.notifications[0].title == "High priority"

    def test_empty_result(
        self,
        list_use_case: ListNotificationsUseCase,
    ) -> None:
        response = list_use_case.execute(
            ListNotificationsRequest(status="acknowledged")
        )
        assert response.total == 0
        assert response.notifications == []

    def test_no_match_returns_empty(
        self,
        list_use_case: ListNotificationsUseCase,
        setup_notifications: dict[str, str],
    ) -> None:
        response = list_use_case.execute(
            ListNotificationsRequest(priority="normal")
        )
        assert response.total == 0

    def test_target_type_and_id_combined(
        self,
        create_use_case: CreateNotificationUseCase,
        list_use_case: ListNotificationsUseCase,
    ) -> None:
        _create_notification(
            create_use_case,
            title="User notification",
            target_type="user",
            target_id="user-001",
        )
        _create_notification(
            create_use_case,
            title="Admin notification",
            target_type="admin",
            target_id="admin-001",
        )

        response = list_use_case.execute(
            ListNotificationsRequest(
                target_type="user", target_id="user-001"
            )
        )
        assert response.total == 1
        assert response.notifications[0].title == "User notification"

    def test_multiple_statuses(
        self,
        create_use_case: CreateNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
        list_use_case: ListNotificationsUseCase,
    ) -> None:
        n1 = _create_notification(create_use_case, title="N1").notification_id
        n2 = _create_notification(create_use_case, title="N2").notification_id
        show_use_case.execute(ShowNotificationRequest(notification_id=n1))

        shown = list_use_case.execute(ListNotificationsRequest(status="shown"))
        pending = list_use_case.execute(
            ListNotificationsRequest(status="pending")
        )
        assert shown.total == 1
        assert pending.total == 1


# ===================================================================
# CreateActionUseCase Tests
# ===================================================================


class TestCreateActionUseCase:
    def test_action_created(
        self,
        create_use_case: CreateNotificationUseCase,
        create_action_use_case: CreateActionUseCase,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        response = create_action_use_case.execute(
            CreateActionRequest(
                notification_id=create_resp.notification_id,
                label="View details",
                callback_name="view_details",
            )
        )
        assert isinstance(response, CreateActionResponse)
        assert response.label == "View details"
        assert response.callback_name == "view_details"
        assert response.notification_id == create_resp.notification_id
        assert response.created_at is not None

    def test_action_persisted(
        self,
        create_use_case: CreateNotificationUseCase,
        create_action_use_case: CreateActionUseCase,
        fake_action_repo: FakeNotificationActionRepository,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        response = create_action_use_case.execute(
            CreateActionRequest(
                notification_id=create_resp.notification_id,
                label="Dismiss",
                callback_name="dismiss_action",
            )
        )
        assert fake_action_repo.count() == 1
        stored = fake_action_repo.find_by_id(
            ActionId(value=UUID(response.action_id))
        )
        assert stored is not None
        assert stored.label == "Dismiss"

    def test_notification_ownership(
        self,
        create_use_case: CreateNotificationUseCase,
        create_action_use_case: CreateActionUseCase,
        fake_action_repo: FakeNotificationActionRepository,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        response = create_action_use_case.execute(
            CreateActionRequest(
                notification_id=create_resp.notification_id,
                label="Owned action",
                callback_name="owned_action",
            )
        )
        stored = fake_action_repo.find_by_id(
            ActionId(value=UUID(response.action_id))
        )
        assert stored is not None
        assert stored.notification_id is not None
        assert str(stored.notification_id) == create_resp.notification_id

    def test_missing_notification_raises_error(
        self,
        create_action_use_case: CreateActionUseCase,
    ) -> None:
        with pytest.raises(NotificationNotFoundError):
            create_action_use_case.execute(
                CreateActionRequest(
                    notification_id="00000000-0000-0000-0000-000000000000",
                    label="Test",
                    callback_name="test",
                )
            )

    def test_invalid_callback_rejected(
        self,
        create_use_case: CreateNotificationUseCase,
        create_action_use_case: CreateActionUseCase,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        with pytest.raises(InvalidCallbackError):
            create_action_use_case.execute(
                CreateActionRequest(
                    notification_id=create_resp.notification_id,
                    label="Test",
                    callback_name="",
                )
            )

    def test_invalid_label_rejected(
        self,
        create_use_case: CreateNotificationUseCase,
        create_action_use_case: CreateActionUseCase,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        with pytest.raises(InvalidActionLabelError):
            create_action_use_case.execute(
                CreateActionRequest(
                    notification_id=create_resp.notification_id,
                    label="",
                    callback_name="test",
                )
            )

    def test_save_called(
        self,
        create_use_case: CreateNotificationUseCase,
        create_action_use_case: CreateActionUseCase,
        fake_action_repo: FakeNotificationActionRepository,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        create_action_use_case.execute(
            CreateActionRequest(
                notification_id=create_resp.notification_id,
                label="Save test",
                callback_name="save_test",
            )
        )
        assert len(fake_action_repo.save_calls) == 1

    def test_multiple_actions_same_notification(
        self,
        create_use_case: CreateNotificationUseCase,
        create_action_use_case: CreateActionUseCase,
        fake_action_repo: FakeNotificationActionRepository,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        r1 = create_action_use_case.execute(
            CreateActionRequest(
                notification_id=create_resp.notification_id,
                label="Action 1",
                callback_name="action_1",
            )
        )
        r2 = create_action_use_case.execute(
            CreateActionRequest(
                notification_id=create_resp.notification_id,
                label="Action 2",
                callback_name="action_2",
            )
        )
        assert r1.action_id != r2.action_id
        stored = fake_action_repo.find_by_notification_id(
            NotificationId(value=UUID(create_resp.notification_id))
        )
        assert len(stored) == 2


# ===================================================================
# InvokeActionUseCase Tests
# ===================================================================


class TestInvokeActionUseCase:
    @pytest.fixture
    def existing_action(
        self,
        create_use_case: CreateNotificationUseCase,
        create_action_use_case: CreateActionUseCase,
        fake_outbox: FakeNotificationOutbox,
    ) -> str:
        fake_outbox.append_calls.clear()
        create_resp = _create_notification(create_use_case)
        action_resp = create_action_use_case.execute(
            CreateActionRequest(
                notification_id=create_resp.notification_id,
                label="Invoke me",
                callback_name="invoke_me",
            )
        )
        fake_outbox.append_calls.clear()
        return action_resp.action_id

    def test_action_invocation(
        self,
        invoke_action_use_case: InvokeActionUseCase,
        existing_action: str,
    ) -> None:
        response = invoke_action_use_case.execute(
            InvokeActionRequest(action_id=existing_action)
        )
        assert isinstance(response, InvokeActionResponse)
        assert response.action_id == existing_action
        assert response.callback_name == "invoke_me"
        assert response.occurred_at is not None

    def test_notification_action_invoked_emitted(
        self,
        invoke_action_use_case: InvokeActionUseCase,
        existing_action: str,
        fake_outbox: FakeNotificationOutbox,
    ) -> None:
        invoke_action_use_case.execute(
            InvokeActionRequest(action_id=existing_action)
        )
        invoke_events = [
            e
            for e in fake_outbox.append_calls
            if isinstance(e, NotificationActionInvoked)
        ]
        assert len(invoke_events) == 1
        assert str(invoke_events[0].action_id) == existing_action

    def test_missing_action_raises_error(
        self,
        invoke_action_use_case: InvokeActionUseCase,
    ) -> None:
        with pytest.raises(NotificationActionNotFoundError):
            invoke_action_use_case.execute(
                InvokeActionRequest(
                    action_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_outbox_write(
        self,
        invoke_action_use_case: InvokeActionUseCase,
        existing_action: str,
        fake_outbox: FakeNotificationOutbox,
    ) -> None:
        invoke_action_use_case.execute(
            InvokeActionRequest(action_id=existing_action)
        )
        assert len(fake_outbox.append_calls) == 1

    def test_payload_correctness(
        self,
        create_use_case: CreateNotificationUseCase,
        create_action_use_case: CreateActionUseCase,
        invoke_action_use_case: InvokeActionUseCase,
        fake_notification_repo: FakeNotificationRepository,
        fake_action_repo: FakeNotificationActionRepository,
        fake_outbox: FakeNotificationOutbox,
    ) -> None:
        create_resp = _create_notification(create_use_case)
        action_resp = create_action_use_case.execute(
            CreateActionRequest(
                notification_id=create_resp.notification_id,
                label="Payload check",
                callback_name="payload_check",
            )
        )
        fake_outbox.append_calls.clear()
        response = invoke_action_use_case.execute(
            InvokeActionRequest(action_id=action_resp.action_id)
        )

        assert len(fake_outbox.append_calls) == 1
        event = fake_outbox.append_calls[0]
        assert isinstance(event, NotificationActionInvoked)
        assert str(event.action_id) == action_resp.action_id
        assert str(event.notification_id) == create_resp.notification_id
        assert event.callback_name == "payload_check"
        assert response.occurred_at == event.occurred_at

    def test_save_called(
        self,
        invoke_action_use_case: InvokeActionUseCase,
        existing_action: str,
        fake_action_repo: FakeNotificationActionRepository,
    ) -> None:
        invoke_action_use_case.execute(
            InvokeActionRequest(action_id=existing_action)
        )
        assert len(fake_action_repo.save_calls) >= 1


# ===================================================================
# Integration Tests
# ===================================================================


class TestUseCaseIntegration:
    def test_full_lifecycle(
        self,
        fake_notification_repo: FakeNotificationRepository,
        fake_action_repo: FakeNotificationActionRepository,
        fake_outbox: FakeNotificationOutbox,
    ) -> None:
        create = CreateNotificationUseCase(
            notification_repo=fake_notification_repo,
            outbox=fake_outbox,
        )
        show = ShowNotificationUseCase(
            notification_repo=fake_notification_repo,
            outbox=fake_outbox,
        )
        acknowledge = AcknowledgeNotificationUseCase(
            notification_repo=fake_notification_repo,
            outbox=fake_outbox,
        )
        dismiss = DismissNotificationUseCase(
            notification_repo=fake_notification_repo,
            outbox=fake_outbox,
        )
        expire = ExpireNotificationUseCase(
            notification_repo=fake_notification_repo,
            outbox=fake_outbox,
        )
        get = GetNotificationUseCase(
            notification_repo=fake_notification_repo,
        )
        list_uc = ListNotificationsUseCase(
            notification_repo=fake_notification_repo,
        )
        create_action = CreateActionUseCase(
            notification_repo=fake_notification_repo,
            action_repo=fake_action_repo,
        )
        invoke_action = InvokeActionUseCase(
            action_repo=fake_action_repo,
            notification_repo=fake_notification_repo,
            outbox=fake_outbox,
        )

        # Create notification
        create_resp = create.execute(
            CreateNotificationRequest(
                title="Lifecycle test",
                message="Testing full lifecycle",
                priority="high",
                channel="desktop",
                target_type="user",
                target_id="user-001",
            )
        )
        assert create_resp.status == "pending"
        assert create_resp.status == "pending"
        nid = create_resp.notification_id

        # Show
        show_resp = show.execute(
            ShowNotificationRequest(notification_id=nid)
        )
        assert show_resp.status == "shown"

        # Acknowledge
        ack_resp = acknowledge.execute(
            AcknowledgeNotificationRequest(notification_id=nid)
        )
        assert ack_resp.status == "acknowledged"

        # Create action
        action_resp = create_action.execute(
            CreateActionRequest(
                notification_id=nid,
                label="Review",
                callback_name="review_action",
            )
        )
        assert action_resp.label == "Review"

        # Invoke action
        invoke_resp = invoke_action.execute(
            InvokeActionRequest(action_id=action_resp.action_id)
        )
        assert invoke_resp.callback_name == "review_action"

        # Get
        get_resp = get.execute(GetNotificationRequest(notification_id=nid))
        assert get_resp.status == "acknowledged"
        assert get_resp.shown_at is not None
        assert get_resp.acknowledged_at is not None

        # List
        list_resp = list_uc.execute(ListNotificationsRequest())
        assert list_resp.total == 1

        # Expire
        expire_resp = expire.execute(
            ExpireNotificationRequest(notification_id=nid)
        )
        assert expire_resp.status == "expired"

    def test_outbox_event_sequence(
        self,
        fake_notification_repo: FakeNotificationRepository,
        fake_action_repo: FakeNotificationActionRepository,
        fake_outbox: FakeNotificationOutbox,
    ) -> None:
        create = CreateNotificationUseCase(
            notification_repo=fake_notification_repo,
            outbox=fake_outbox,
        )
        show = ShowNotificationUseCase(
            notification_repo=fake_notification_repo,
            outbox=fake_outbox,
        )
        acknowledge = AcknowledgeNotificationUseCase(
            notification_repo=fake_notification_repo,
            outbox=fake_outbox,
        )
        create_action = CreateActionUseCase(
            notification_repo=fake_notification_repo,
            action_repo=fake_action_repo,
        )
        invoke_action = InvokeActionUseCase(
            action_repo=fake_action_repo,
            notification_repo=fake_notification_repo,
            outbox=fake_outbox,
        )

        create_resp = create.execute(
            CreateNotificationRequest(
                title="Event sequence",
                message="Testing event order",
                channel="in_app",
                target_type="user",
                target_id="user-001",
            )
        )
        nid = create_resp.notification_id
        show.execute(ShowNotificationRequest(notification_id=nid))
        acknowledge.execute(AcknowledgeNotificationRequest(notification_id=nid))
        action_resp = create_action.execute(
            CreateActionRequest(
                notification_id=nid, label="Act", callback_name="act"
            )
        )
        invoke_action.execute(
            InvokeActionRequest(action_id=action_resp.action_id)
        )

        types = [type(e).__name__ for e in fake_outbox.append_calls]
        assert types == [
            "NotificationCreated",
            "NotificationShown",
            "NotificationAcknowledged",
            "NotificationActionInvoked",
        ]

    def test_state_transitions(
        self,
        fake_notification_repo: FakeNotificationRepository,
        fake_action_repo: FakeNotificationActionRepository,
        fake_outbox: FakeNotificationOutbox,
    ) -> None:
        create = CreateNotificationUseCase(
            notification_repo=fake_notification_repo,
            outbox=fake_outbox,
        )
        show = ShowNotificationUseCase(
            notification_repo=fake_notification_repo,
            outbox=fake_outbox,
        )
        dismiss = DismissNotificationUseCase(
            notification_repo=fake_notification_repo,
            outbox=fake_outbox,
        )

        create_resp = create.execute(
            CreateNotificationRequest(
                title="Transition test",
                message="Testing transitions",
                target_type="user",
                target_id="user-001",
            )
        )
        nid = create_resp.notification_id

        show.execute(ShowNotificationRequest(notification_id=nid))

        stored = fake_notification_repo.find_by_id(
            NotificationId(value=UUID(nid))
        )
        assert stored is not None
        assert stored.status == NotificationStatus.SHOWN

        dismiss.execute(DismissNotificationRequest(notification_id=nid))

        stored = fake_notification_repo.find_by_id(
            NotificationId(value=UUID(nid))
        )
        assert stored is not None
        assert stored.status == NotificationStatus.DISMISSED

    def test_not_found_error_is_use_case_error(
        self,
        get_use_case: GetNotificationUseCase,
        show_use_case: ShowNotificationUseCase,
        acknowledge_use_case: AcknowledgeNotificationUseCase,
        dismiss_use_case: DismissNotificationUseCase,
        expire_use_case: ExpireNotificationUseCase,
    ) -> None:
        for use_case, request in [
            (get_use_case, GetNotificationRequest(notification_id="00000000-0000-0000-0000-000000000000")),
            (show_use_case, ShowNotificationRequest(notification_id="00000000-0000-0000-0000-000000000000")),
            (acknowledge_use_case, AcknowledgeNotificationRequest(notification_id="00000000-0000-0000-0000-000000000000")),
            (dismiss_use_case, DismissNotificationRequest(notification_id="00000000-0000-0000-0000-000000000000")),
            (expire_use_case, ExpireNotificationRequest(notification_id="00000000-0000-0000-0000-000000000000")),
        ]:
            with pytest.raises(UseCaseError):
                use_case.execute(request)


# ===================================================================
# Exception Hierarchy Tests
# ===================================================================


class TestExceptionHierarchy:
    def test_use_case_error_base(self) -> None:
        assert issubclass(NotificationNotFoundError, UseCaseError)
        assert issubclass(NotificationActionNotFoundError, UseCaseError)

    def test_notification_not_found_error_message(self) -> None:
        err = NotificationNotFoundError("notif-001")
        assert "notif-001" in str(err)
        assert err.notification_id == "notif-001"

    def test_notification_action_not_found_error_message(self) -> None:
        err = NotificationActionNotFoundError("act-001")
        assert "act-001" in str(err)
        assert err.action_id == "act-001"

    def test_use_case_error_is_exception(self) -> None:
        assert issubclass(UseCaseError, Exception)

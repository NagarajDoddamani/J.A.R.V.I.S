from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api.endpoints import notification as notification_router
from backend.core.database import get_db
from backend.notification.adapters.outbound.mapper import (
    NotificationActionMapperImpl,
    NotificationMapperImpl,
    NotificationOutboxMapperImpl,
)
from backend.notification.adapters.outbound.models import Base, NotificationOutboxModel
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
    NotificationStatus,
    NotificationTarget,
    NotificationTitle,
)
from backend.notification.nats import (
    NotificationOutboxDomainEvent,
    publish_notification_outbox_events,
)

for _table in Base.metadata.tables.values():
    _table.schema = None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite://", echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    return e


@pytest.fixture
def session(engine):
    conn = engine.connect()
    transaction = conn.begin()
    s = Session(bind=conn)
    yield s
    s.close()
    transaction.rollback()
    conn.close()


@pytest.fixture
def notif_repo(session):
    return SqlAlchemyNotificationRepository(session, mapper=NotificationMapperImpl())


@pytest.fixture
def action_repo(session):
    return SqlAlchemyNotificationActionRepository(session, mapper=NotificationActionMapperImpl())


@pytest.fixture
def outbox(session):
    return SqlAlchemyNotificationOutboxAdapter(session)


@pytest.fixture
def mock_js():
    js = AsyncMock()
    js.publish = AsyncMock()
    return js


@pytest.fixture
def client(session):
    def _override_get_db():
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    app = FastAPI()
    app.include_router(notification_router.router, prefix="/api/v1/notification")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_notif(title="Test", message="Message") -> Notification:
    return Notification(
        notification_id=NotificationId(),
        title=NotificationTitle(value=title),
        message=NotificationMessage(value=message),
        priority=NotificationPriority.NORMAL,
        channel=NotificationChannel.IN_APP,
        target=NotificationTarget(target_type="user", target_id="user-1"),
    )


def save_notif(notif_repo, notif=None, title=None) -> str:
    if notif is not None:
        n = notif
    elif title is not None:
        n = make_notif(title=title)
    else:
        n = make_notif()
    notif_repo.save(n)
    return str(n.notification_id)


# ===================================================================
# 1. Notification Lifecycle
# ===================================================================


class TestNotificationLifecycle:
    """Create -> Show -> Acknowledge -> Get -> List"""

    def test_full_lifecycle(self, client, session, notif_repo) -> None:
        create_resp = client.post(
            "/api/v1/notification/notifications",
            json={"title": "Lifecycle", "message": "Test", "priority": "normal",
                  "channel": "in_app", "target_type": "user", "target_id": "u1"},
        )
        assert create_resp.status_code == 201
        nid = create_resp.json()["notification_id"]

        show_resp = client.post(f"/api/v1/notification/notifications/{nid}/show")
        assert show_resp.status_code == 200
        assert show_resp.json()["status"] == "shown"

        ack_resp = client.post(f"/api/v1/notification/notifications/{nid}/acknowledge")
        assert ack_resp.status_code == 200
        assert ack_resp.json()["status"] == "acknowledged"

        get_resp = client.get(f"/api/v1/notification/notifications/{nid}")
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "acknowledged"

        list_resp = client.get("/api/v1/notification/notifications")
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] >= 1

    def test_lifecycle_through_use_case(self, session, notif_repo, outbox) -> None:
        from backend.notification.application.use_cases.create_notification import (
            CreateNotificationUseCase,
        )
        from backend.notification.application.use_cases.show_notification import (
            ShowNotificationUseCase,
        )
        from backend.notification.application.use_cases.acknowledge_notification import (
            AcknowledgeNotificationUseCase,
        )
        from backend.notification.application.use_cases.get_notification import (
            GetNotificationUseCase,
        )
        from backend.notification.application.use_cases.list_notifications import (
            ListNotificationsUseCase,
        )
        from backend.notification.application.use_cases.dto import (
            AcknowledgeNotificationRequest,
            CreateNotificationRequest,
            GetNotificationRequest,
            ListNotificationsRequest,
            ShowNotificationRequest,
        )

        creator = CreateNotificationUseCase(notif_repo, outbox)
        create_resp = creator.execute(
            CreateNotificationRequest(title="UC", message="M", priority="normal",
                                      channel="in_app", target_type="user", target_id="u1")
        )
        session.commit()

        shower = ShowNotificationUseCase(notif_repo, outbox)
        show_resp = shower.execute(ShowNotificationRequest(notification_id=create_resp.notification_id))
        session.commit()
        assert show_resp.status == "shown"

        ack = AcknowledgeNotificationUseCase(notif_repo, outbox)
        ack_resp = ack.execute(AcknowledgeNotificationRequest(notification_id=create_resp.notification_id))
        session.commit()
        assert ack_resp.status == "acknowledged"

        getter = GetNotificationUseCase(notif_repo)
        get_resp = getter.execute(GetNotificationRequest(notification_id=create_resp.notification_id))
        assert get_resp.status == "acknowledged"

        lister = ListNotificationsUseCase(notif_repo)
        list_resp = lister.execute(ListNotificationsRequest())
        assert list_resp.total >= 1


# ===================================================================
# 2. Dismiss Flow
# ===================================================================


class TestDismissFlow:
    """Create -> Show -> Dismiss"""

    def test_dismiss_flow(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()

        client.post(f"/api/v1/notification/notifications/{nid}/show")
        dismiss_resp = client.post(f"/api/v1/notification/notifications/{nid}/dismiss")
        assert dismiss_resp.status_code == 200
        assert dismiss_resp.json()["status"] == "dismissed"

        get_resp = client.get(f"/api/v1/notification/notifications/{nid}")
        assert get_resp.json()["status"] == "dismissed"
        assert get_resp.json()["dismissed_at"] is not None

    def test_dismiss_then_show_returns_400(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        client.post(f"/api/v1/notification/notifications/{nid}/show")
        client.post(f"/api/v1/notification/notifications/{nid}/dismiss")
        resp = client.post(f"/api/v1/notification/notifications/{nid}/show")
        assert resp.status_code == 400

    def test_dismiss_then_acknowledge_returns_400(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        client.post(f"/api/v1/notification/notifications/{nid}/show")
        client.post(f"/api/v1/notification/notifications/{nid}/dismiss")
        resp = client.post(f"/api/v1/notification/notifications/{nid}/acknowledge")
        assert resp.status_code == 400


# ===================================================================
# 3. Expiration Flow
# ===================================================================


class TestExpirationFlow:
    """Create -> Expire"""

    def test_expire_flow(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()

        expire_resp = client.post(f"/api/v1/notification/notifications/{nid}/expire")
        assert expire_resp.status_code == 200
        assert expire_resp.json()["status"] == "expired"

        get_resp = client.get(f"/api/v1/notification/notifications/{nid}")
        assert get_resp.json()["status"] == "expired"

    def test_expire_then_show_returns_400(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        client.post(f"/api/v1/notification/notifications/{nid}/expire")
        resp = client.post(f"/api/v1/notification/notifications/{nid}/show")
        assert resp.status_code == 400

    def test_expire_then_acknowledge_returns_400(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        client.post(f"/api/v1/notification/notifications/{nid}/expire")
        resp = client.post(f"/api/v1/notification/notifications/{nid}/acknowledge")
        assert resp.status_code == 400

    def test_expire_pending_then_dismiss_returns_400(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        resp = client.post(f"/api/v1/notification/notifications/{nid}/dismiss")
        assert resp.status_code == 400

    def test_expire_with_show_allowed(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        client.post(f"/api/v1/notification/notifications/{nid}/show")
        expire_resp = client.post(f"/api/v1/notification/notifications/{nid}/expire")
        assert expire_resp.status_code == 200


# ===================================================================
# 4. Action Lifecycle
# ===================================================================


class TestActionLifecycle:
    """Create -> CreateAction -> InvokeAction"""

    def test_action_full_lifecycle(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()

        create_resp = client.post(
            f"/api/v1/notification/notifications/{nid}/actions",
            json={"notification_id": nid, "label": "OK", "callback_name": "ok_callback"},
        )
        assert create_resp.status_code == 201
        aid = create_resp.json()["action_id"]

        invoke_resp = client.post(f"/api/v1/notification/notifications/actions/{aid}/invoke")
        assert invoke_resp.status_code == 200
        assert invoke_resp.json()["callback_name"] == "ok_callback"
        assert invoke_resp.json()["occurred_at"] is not None

    def test_action_lifecycle_through_use_cases(self, session, notif_repo, action_repo, outbox) -> None:
        from backend.notification.application.use_cases.create_action import (
            CreateActionUseCase,
        )
        from backend.notification.application.use_cases.invoke_action import (
            InvokeActionUseCase,
        )
        from backend.notification.application.use_cases.dto import (
            CreateActionRequest,
            InvokeActionRequest,
        )

        nid = save_notif(notif_repo)
        session.commit()
        nid_obj = NotificationId(value=UUID(nid))

        creator = CreateActionUseCase(notif_repo, action_repo)
        create_resp = creator.execute(
            CreateActionRequest(notification_id=nid, label="OK", callback_name="cb")
        )
        assert create_resp.label == "OK"

        invoker = InvokeActionUseCase(action_repo=action_repo, notification_repo=notif_repo, outbox=outbox)
        invoke_resp = invoker.execute(InvokeActionRequest(action_id=create_resp.action_id))
        assert invoke_resp.callback_name == "cb"

        remaining = outbox.fetch_unpublished()
        action_invoked_events = [e for e in remaining if isinstance(e, NotificationActionInvoked)]
        assert len(action_invoked_events) == 1

    def test_multiple_actions_on_notification(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()

        a1 = client.post(
            f"/api/v1/notification/notifications/{nid}/actions",
            json={"notification_id": nid, "label": "OK", "callback_name": "ok"},
        )
        a2 = client.post(
            f"/api/v1/notification/notifications/{nid}/actions",
            json={"notification_id": nid, "label": "Cancel", "callback_name": "cancel"},
        )
        assert a1.status_code == 201
        assert a2.status_code == 201
        assert a1.json()["action_id"] != a2.json()["action_id"]

    def test_invoke_action_creates_outbox_event(self, session, notif_repo, action_repo, outbox) -> None:
        nid = save_notif(notif_repo)
        session.commit()

        from backend.notification.application.use_cases.create_action import (
            CreateActionUseCase,
        )
        from backend.notification.application.use_cases.invoke_action import (
            InvokeActionUseCase,
        )
        from backend.notification.application.use_cases.dto import (
            CreateActionRequest,
            InvokeActionRequest,
        )

        creator = CreateActionUseCase(notif_repo, action_repo)
        cr = creator.execute(CreateActionRequest(notification_id=nid, label="X", callback_name="y"))

        invoker = InvokeActionUseCase(action_repo=action_repo, notification_repo=notif_repo, outbox=outbox)
        invoker.execute(InvokeActionRequest(action_id=cr.action_id))

        unpublished = outbox.fetch_unpublished()
        assert any(isinstance(e, NotificationActionInvoked) for e in unpublished)


# ===================================================================
# 5. Repository Roundtrip
# ===================================================================


class TestRepositoryRoundtrip:
    """Notification <-> DTO <-> ORM <-> DB <-> Domain"""

    def test_notification_roundtrip_preserves_all_fields(self, session, notif_repo) -> None:
        nid_val = NotificationId()
        title_val = "Roundtrip Title"
        msg_val = "Roundtrip Message"
        now = datetime.now(tz=timezone.utc)

        notif = Notification(
            notification_id=nid_val,
            title=NotificationTitle(value=title_val),
            message=NotificationMessage(value=msg_val),
            priority=NotificationPriority.HIGH,
            channel=NotificationChannel.DESKTOP,
            target=NotificationTarget(target_type="admin", target_id="a1"),
            created_at=now,
        )
        notif_repo.save(notif)
        session.commit()

        loaded = notif_repo.find_by_id(nid_val)
        assert loaded is not None
        assert str(loaded.notification_id) == str(nid_val)
        assert str(loaded.title) == title_val
        assert str(loaded.message) == msg_val
        assert loaded.priority == NotificationPriority.HIGH
        assert loaded.channel == NotificationChannel.DESKTOP
        assert loaded.target.target_type == "admin"
        assert loaded.target.target_id == "a1"
        assert loaded.status == NotificationStatus.PENDING

    def test_notification_roundtrip_with_status_transition(self, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()

        nid_obj = NotificationId(value=UUID(nid))
        notif = notif_repo.find_by_id(nid_obj)
        assert notif is not None
        notif.show()
        notif_repo.save(notif)
        session.commit()

        loaded = notif_repo.find_by_id(nid_obj)
        assert loaded is not None
        assert loaded.status == NotificationStatus.SHOWN
        assert loaded.shown_at is not None

    def test_action_roundtrip_preserves_all_fields(self, session, notif_repo, action_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()

        action = NotificationAction(
            action_id=ActionId(),
            notification_id=NotificationId(value=UUID(nid)),
            label="Test Action",
            callback_name="test_callback",
        )
        action_repo.save(action)
        session.commit()

        loaded = action_repo.find_by_id(action.action_id)
        assert loaded is not None
        assert str(loaded.action_id) == str(action.action_id)
        assert loaded.label == "Test Action"
        assert loaded.callback_name == "test_callback"

    def test_outbox_dto_roundtrip(self, session) -> None:
        mapper = NotificationOutboxMapperImpl()
        event = NotificationCreated(
            notification_id=NotificationId(),
            title="DTO Test",
            message="DTO Msg",
            priority="high",
            channel="desktop",
            target_type="user",
            target_id="u1",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "notification.created"
        assert dto.aggregate_id == str(event.notification_id)
        assert dto.payload is not None
        payload = json.loads(dto.payload)
        assert payload["title"] == "DTO Test"

        recon = mapper.dto_to_event(dto)
        assert isinstance(recon, NotificationCreated)
        assert recon.title == "DTO Test"

    def test_repo_find_by_status_filters_correctly(self, session, notif_repo) -> None:
        nid1 = save_notif(notif_repo)
        nid2 = save_notif(notif_repo, title="Second")
        session.commit()

        n1 = notif_repo.find_by_id(NotificationId(value=UUID(nid1)))
        assert n1 is not None
        n1.show()
        notif_repo.save(n1)
        session.commit()

        pending = notif_repo.find_by_status(NotificationStatus.PENDING)
        shown = notif_repo.find_by_status(NotificationStatus.SHOWN)
        assert len(pending) == 1
        assert len(shown) == 1

    def test_repo_find_by_priority(self, session, notif_repo) -> None:
        n = make_notif()
        n._priority = NotificationPriority.CRITICAL
        notif_repo.save(n)
        session.commit()

        results = notif_repo.find_by_priority(NotificationPriority.CRITICAL)
        assert len(results) >= 1

    def test_repo_find_by_target(self, session, notif_repo) -> None:
        save_notif(notif_repo)
        session.commit()

        results = notif_repo.find_by_target("user", "user-1")
        assert len(results) >= 1

    def test_repo_count(self, session, notif_repo) -> None:
        save_notif(notif_repo)
        save_notif(notif_repo, title="Another")
        session.commit()
        assert notif_repo.count() >= 2

    def test_action_find_by_notification_id(self, session, notif_repo, action_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()

        action_repo.save(NotificationAction(
            action_id=ActionId(),
            notification_id=NotificationId(value=UUID(nid)),
            label="A1", callback_name="c1",
        ))
        action_repo.save(NotificationAction(
            action_id=ActionId(),
            notification_id=NotificationId(value=UUID(nid)),
            label="A2", callback_name="c2",
        ))
        session.commit()

        results = action_repo.find_by_notification_id(NotificationId(value=UUID(nid)))
        assert len(results) == 2

    def test_action_count(self, session, notif_repo, action_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        action_repo.save(NotificationAction(
            action_id=ActionId(), notification_id=NotificationId(value=UUID(nid)),
            label="X", callback_name="y",
        ))
        session.commit()
        assert action_repo.count() >= 1


# ===================================================================
# 6. Outbox Lifecycle
# ===================================================================


class TestOutboxLifecycle:
    """Append -> Fetch -> Publish -> Mark"""

    def test_append_then_fetch(self, session, outbox) -> None:
        event = NotificationCreated(
            notification_id=NotificationId(),
            title="Append", message="Test", priority="normal",
            channel="in_app", target_type="user", target_id="u1",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], NotificationCreated)
        assert unpublished[0].title == "Append"

    def test_fetch_unpublished_only(self, session, outbox) -> None:
        e1 = NotificationCreated(
            notification_id=NotificationId(), title="A", message="M",
            priority="normal", channel="in_app", target_type="user", target_id="u1",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        e2 = NotificationShown(
            notification_id=NotificationId(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(e1)
        outbox.append(e2)
        session.commit()

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 2

        outbox.mark_published(str(unpublished[0].event_id))
        session.flush()

        remaining = outbox.fetch_unpublished()
        assert len(remaining) == 1

    def test_mark_all_published(self, session, outbox) -> None:
        for i in range(3):
            outbox.append(NotificationCreated(
                notification_id=NotificationId(), title=f"E{i}", message="M",
                priority="normal", channel="in_app", target_type="user", target_id="u1",
                occurred_at=datetime.now(tz=timezone.utc),
            ))
        session.commit()

        all_events = outbox.fetch_unpublished(limit=10)
        for e in all_events:
            outbox.mark_published(str(e.event_id))
        session.flush()

        remaining = outbox.fetch_unpublished()
        assert len(remaining) == 0

    def test_mark_published_idempotent(self, session, outbox) -> None:
        event = NotificationCreated(
            notification_id=NotificationId(), title="Idempotent", message="M",
            priority="normal", channel="in_app", target_type="user", target_id="u1",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        fetched = outbox.fetch_unpublished()
        outbox.mark_published(str(fetched[0].event_id))
        outbox.mark_published(str(fetched[0].event_id))
        outbox.mark_published(str(fetched[0].event_id))
        session.flush()

        remaining = outbox.fetch_unpublished()
        assert len(remaining) == 0

    def test_outbox_respects_fetch_limit(self, session, outbox) -> None:
        for i in range(5):
            outbox.append(NotificationCreated(
                notification_id=NotificationId(), title=f"E{i}", message="M",
                priority="normal", channel="in_app", target_type="user", target_id="u1",
                occurred_at=datetime.now(tz=timezone.utc),
            ))
        session.commit()

        fetched = outbox.fetch_unpublished(limit=3)
        assert len(fetched) == 3

    @pytest.mark.asyncio
    async def test_full_outbox_nats_lifecycle(self, session, outbox, mock_js) -> None:
        for i in range(2):
            outbox.append(NotificationCreated(
                notification_id=NotificationId(), title=f"N{i}", message="M",
                priority="normal", channel="in_app", target_type="user", target_id="u1",
                occurred_at=datetime.now(tz=timezone.utc),
            ))
        session.commit()

        await publish_notification_outbox_events(
            mock_js, outbox=outbox, batch=10, interval_seconds=0.01, max_iterations=1,
        )

        assert mock_js.publish.await_count == 2
        remaining = outbox.fetch_unpublished()
        assert len(remaining) == 0


# ===================================================================
# 7. FIFO Ordering
# ===================================================================


class TestFifoOrdering:
    """Multiple notifications and actions maintain FIFO order."""

    def test_notification_created_fifo(self, session, outbox) -> None:
        now = datetime.now(tz=timezone.utc)
        for i in range(5):
            outbox.append(NotificationCreated(
                notification_id=NotificationId(), title=f"E{i}", message="M",
                priority="normal", channel="in_app", target_type="user", target_id="u1",
                occurred_at=now,
            ))
        session.commit()

        events = outbox.fetch_unpublished(limit=10)
        assert len(events) == 5
        for i, e in enumerate(events):
            assert e.title == f"E{i}"

    def test_mixed_event_types_fifo(self, session, outbox) -> None:
        now = datetime.now(tz=timezone.utc)
        outbox.append(NotificationCreated(NotificationId(), "C1", "M", "normal", "in_app", "user", "u1", now))
        outbox.append(NotificationShown(NotificationId(), now))
        outbox.append(NotificationCreated(NotificationId(), "C2", "M", "normal", "in_app", "user", "u1", now))
        session.commit()

        events = outbox.fetch_unpublished(limit=10)
        assert len(events) == 3
        assert isinstance(events[0], NotificationCreated) and events[0].title == "C1"
        assert isinstance(events[1], NotificationShown)
        assert isinstance(events[2], NotificationCreated) and events[2].title == "C2"

    def test_action_invoked_fifo(self, session, outbox) -> None:
        now = datetime.now(tz=timezone.utc)
        for i in range(3):
            outbox.append(NotificationActionInvoked(
                notification_id=NotificationId(), action_id=ActionId(),
                callback_name=f"cb{i}", occurred_at=now,
            ))
        session.commit()

        events = outbox.fetch_unpublished(limit=10)
        assert len(events) == 3
        for i, e in enumerate(events):
            assert e.callback_name == f"cb{i}"

    def test_multiple_notifications_fifo_across_commits(self, session, outbox) -> None:
        now = datetime.now(tz=timezone.utc)
        outbox.append(NotificationCreated(NotificationId(), "First", "M", "normal", "in_app", "user", "u1", now))
        session.commit()

        outbox.append(NotificationCreated(NotificationId(), "Second", "M", "normal", "in_app", "user", "u1", now))
        session.commit()

        events = outbox.fetch_unpublished(limit=10)
        assert len(events) == 2
        assert events[0].title == "First"
        assert events[1].title == "Second"


# ===================================================================
# 8. REST Contracts
# ===================================================================


class TestRestContractCreate:
    URL = "/api/v1/notification/notifications"

    def test_create_201(self, client) -> None:
        resp = client.post(self.URL, json={
            "title": "REST", "message": "Test", "priority": "normal",
            "channel": "in_app", "target_type": "user", "target_id": "u1",
        })
        assert resp.status_code == 201

    def test_create_with_expiry(self, client) -> None:
        future = (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat()
        resp = client.post(self.URL, json={
            "title": "Exp", "message": "Test", "priority": "normal",
            "channel": "in_app", "target_type": "user", "target_id": "u1",
            "expires_at": future,
        })
        assert resp.status_code == 201
        assert resp.json()["expires_at"] is not None

    def test_create_dto_shape(self, client) -> None:
        resp = client.post(self.URL, json={
            "title": "Shape", "message": "Test", "priority": "high",
            "channel": "desktop", "target_type": "admin", "target_id": "a1",
        })
        data = resp.json()
        assert "notification_id" in data
        assert "title" in data
        assert "message" in data
        assert "priority" in data
        assert "channel" in data
        assert "target_type" in data
        assert "target_id" in data
        assert "status" in data
        assert "created_at" in data

    def test_create_422_empty_title(self, client) -> None:
        resp = client.post(self.URL, json={
            "title": "", "message": "M", "priority": "normal",
            "channel": "in_app", "target_type": "user", "target_id": "u1",
        })
        assert resp.status_code == 422

    def test_create_422_empty_message(self, client) -> None:
        resp = client.post(self.URL, json={
            "title": "T", "message": "", "priority": "normal",
            "channel": "in_app", "target_type": "user", "target_id": "u1",
        })
        assert resp.status_code == 422

    def test_create_422_invalid_priority(self, client) -> None:
        resp = client.post(self.URL, json={
            "title": "T", "message": "M", "priority": "invalid",
            "channel": "in_app", "target_type": "user", "target_id": "u1",
        })
        assert resp.status_code == 422


class TestRestContractShow:
    URL = "/api/v1/notification/notifications"

    def test_show_200(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        resp = client.post(f"{self.URL}/{nid}/show")
        assert resp.status_code == 200
        assert resp.json()["status"] == "shown"
        assert "shown_at" in resp.json()

    def test_show_404(self, client) -> None:
        resp = client.post(f"{self.URL}/00000000-0000-0000-0000-000000000000/show")
        assert resp.status_code == 404

    def test_show_400_twice(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        client.post(f"{self.URL}/{nid}/show")
        resp = client.post(f"{self.URL}/{nid}/show")
        assert resp.status_code == 400


class TestRestContractAcknowledge:
    URL = "/api/v1/notification/notifications"

    def test_acknowledge_200(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        client.post(f"{self.URL}/{nid}/show")
        resp = client.post(f"{self.URL}/{nid}/acknowledge")
        assert resp.status_code == 200
        assert resp.json()["status"] == "acknowledged"

    def test_acknowledge_404(self, client) -> None:
        resp = client.post(f"{self.URL}/00000000-0000-0000-0000-000000000000/acknowledge")
        assert resp.status_code == 404

    def test_acknowledge_400_pending(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        resp = client.post(f"{self.URL}/{nid}/acknowledge")
        assert resp.status_code == 400


class TestRestContractDismiss:
    URL = "/api/v1/notification/notifications"

    def test_dismiss_200(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        client.post(f"{self.URL}/{nid}/show")
        resp = client.post(f"{self.URL}/{nid}/dismiss")
        assert resp.status_code == 200

    def test_dismiss_404(self, client) -> None:
        resp = client.post(f"{self.URL}/00000000-0000-0000-0000-000000000000/dismiss")
        assert resp.status_code == 404

    def test_dismiss_400_pending(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        resp = client.post(f"{self.URL}/{nid}/dismiss")
        assert resp.status_code == 400


class TestRestContractExpire:
    URL = "/api/v1/notification/notifications"

    def test_expire_200(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        resp = client.post(f"{self.URL}/{nid}/expire")
        assert resp.status_code == 200

    def test_expire_404(self, client) -> None:
        resp = client.post(f"{self.URL}/00000000-0000-0000-0000-000000000000/expire")
        assert resp.status_code == 404

    def test_expire_400_twice(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        client.post(f"{self.URL}/{nid}/expire")
        resp = client.post(f"{self.URL}/{nid}/expire")
        assert resp.status_code == 400


class TestRestContractGet:
    URL = "/api/v1/notification/notifications"

    def test_get_200(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        resp = client.get(f"{self.URL}/{nid}")
        assert resp.status_code == 200
        assert resp.json()["notification_id"] == nid

    def test_get_404(self, client) -> None:
        resp = client.get(f"{self.URL}/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_get_dto_shape(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        data = client.get(f"{self.URL}/{nid}").json()
        assert "notification_id" in data
        assert "title" in data
        assert "message" in data
        assert "priority" in data
        assert "channel" in data
        assert "target_type" in data
        assert "target_id" in data
        assert "status" in data
        assert "created_at" in data


class TestRestContractList:
    URL = "/api/v1/notification/notifications"

    def test_list_200_empty(self, client) -> None:
        resp = client.get(self.URL)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_200_with_data(self, client, session, notif_repo) -> None:
        save_notif(notif_repo)
        session.commit()
        resp = client.get(self.URL)
        assert resp.json()["total"] >= 1

    def test_list_dto_shape(self, client, session, notif_repo) -> None:
        save_notif(notif_repo)
        session.commit()
        data = client.get(self.URL).json()
        assert "notifications" in data
        assert "total" in data


class TestRestContractCreateAction:
    URL = "/api/v1/notification/notifications"

    def test_create_action_201(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        resp = client.post(f"{self.URL}/{nid}/actions", json={
            "notification_id": nid, "label": "OK", "callback_name": "ok",
        })
        assert resp.status_code == 201

    def test_create_action_404(self, client) -> None:
        resp = client.post(
            f"{self.URL}/00000000-0000-0000-0000-000000000000/actions",
            json={"notification_id": "00000000-0000-0000-0000-000000000000", "label": "OK", "callback_name": "ok"},
        )
        assert resp.status_code == 404

    def test_create_action_dto_shape(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        data = client.post(f"{self.URL}/{nid}/actions", json={
            "notification_id": nid, "label": "OK", "callback_name": "ok",
        }).json()
        assert "action_id" in data
        assert "label" in data
        assert "callback_name" in data
        assert "created_at" in data


class TestRestContractInvokeAction:
    URL = "/api/v1/notification/notifications"

    def test_invoke_action_200(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        create_resp = client.post(f"{self.URL}/{nid}/actions", json={
            "notification_id": nid, "label": "OK", "callback_name": "cb",
        })
        aid = create_resp.json()["action_id"]
        resp = client.post(f"{self.URL}/actions/{aid}/invoke")
        assert resp.status_code == 200

    def test_invoke_action_404(self, client) -> None:
        resp = client.post(
            f"{self.URL}/actions/00000000-0000-0000-0000-000000000000/invoke"
        )
        assert resp.status_code == 404

    def test_invoke_action_dto_shape(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        create_resp = client.post(f"{self.URL}/{nid}/actions", json={
            "notification_id": nid, "label": "OK", "callback_name": "cb",
        })
        aid = create_resp.json()["action_id"]
        data = client.post(f"{self.URL}/actions/{aid}/invoke").json()
        assert "action_id" in data
        assert "callback_name" in data
        assert "occurred_at" in data


# ===================================================================
# 9. Target Filtering
# ===================================================================


class TestTargetFiltering:
    URL = "/api/v1/notification/notifications"

    def test_filter_by_target_type(self, client, session, notif_repo) -> None:
        n = make_notif()
        n._target = NotificationTarget(target_type="admin", target_id="a1")
        notif_repo.save(n)
        session.commit()
        resp = client.get(f"{self.URL}?target_type=admin&target_id=a1")
        assert resp.json()["total"] >= 1

    def test_filter_by_target_id(self, client, session, notif_repo) -> None:
        n = make_notif()
        n._target = NotificationTarget(target_type="user", target_id="specific_user")
        notif_repo.save(n)
        session.commit()
        resp = client.get(f"{self.URL}?target_type=user&target_id=specific_user")
        assert resp.json()["total"] >= 1

    def test_filter_combined(self, client, session, notif_repo) -> None:
        n1 = make_notif()
        n1._target = NotificationTarget(target_type="user", target_id="u1")
        notif_repo.save(n1)
        n2 = make_notif(title="Other")
        n2._target = NotificationTarget(target_type="admin", target_id="a1")
        notif_repo.save(n2)
        session.commit()
        resp = client.get(f"{self.URL}?target_type=admin&target_id=a1")
        assert resp.json()["total"] == 1

    def test_filter_no_match(self, client, session, notif_repo) -> None:
        save_notif(notif_repo)
        session.commit()
        resp = client.get(f"{self.URL}?target_type=nonexistent&target_id=none")
        assert resp.json()["total"] == 0

    def test_filter_by_status(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        client.post(f"{self.URL}/{nid}/expire")
        resp = client.get(f"{self.URL}?status=expired")
        assert resp.json()["total"] == 1

    def test_filter_by_priority(self, client, session, notif_repo) -> None:
        n = make_notif()
        n._priority = NotificationPriority.CRITICAL
        notif_repo.save(n)
        session.commit()
        resp = client.get(f"{self.URL}?priority=critical")
        assert resp.json()["total"] >= 1

    def test_filter_by_priority_no_match(self, client) -> None:
        resp = client.get(f"{self.URL}?priority=critical")
        assert resp.json()["total"] == 0


# ===================================================================
# 10. Event Coverage
# ===================================================================


class TestEventCoverage:
    """All 6 event types flow through outbox correctly."""

    EVENT_TYPES = [
        ("NotificationCreated", lambda: NotificationCreated(
            NotificationId(), "Title", "Msg", "normal", "in_app", "user", "u1",
            datetime.now(tz=timezone.utc),
        )),
        ("NotificationShown", lambda: NotificationShown(
            NotificationId(), datetime.now(tz=timezone.utc),
        )),
        ("NotificationAcknowledged", lambda: NotificationAcknowledged(
            NotificationId(), datetime.now(tz=timezone.utc),
        )),
        ("NotificationDismissed", lambda: NotificationDismissed(
            NotificationId(), datetime.now(tz=timezone.utc),
        )),
        ("NotificationExpired", lambda: NotificationExpired(
            NotificationId(), datetime.now(tz=timezone.utc),
        )),
        ("NotificationActionInvoked", lambda: NotificationActionInvoked(
            NotificationId(), ActionId(), "cb", datetime.now(tz=timezone.utc),
        )),
    ]

    @pytest.mark.parametrize("name,factory", EVENT_TYPES, ids=[e[0] for e in EVENT_TYPES])
    def test_event_type_append_and_fetch(self, session, outbox, name, factory) -> None:
        event = factory()
        outbox.append(event)
        session.commit()

        unpublished = outbox.fetch_unpublished()
        found = any(type(e).__name__ == name for e in unpublished)
        assert found, f"Event type {name} not found in outbox"

    @pytest.mark.parametrize("name,factory", EVENT_TYPES, ids=[e[0] for e in EVENT_TYPES])
    def test_event_type_mark_published(self, session, outbox, name, factory) -> None:
        event = factory()
        outbox.append(event)
        session.commit()

        unpublished = outbox.fetch_unpublished()
        for e in unpublished:
            if isinstance(e, type(event)):
                from backend.notification.nats import _get_aggregate_id
                outbox.mark_published(str(e.event_id))
        session.flush()

        remaining = outbox.fetch_unpublished()
        matching = [e for e in remaining if isinstance(e, type(event))]
        assert len(matching) == 0, f"Event type {name} remained after mark"

    @pytest.mark.parametrize("name,factory", EVENT_TYPES, ids=[e[0] for e in EVENT_TYPES])
    @pytest.mark.asyncio
    async def test_event_type_nats_publish(self, session, outbox, mock_js, name, factory) -> None:
        event = factory()
        outbox.append(event)
        session.commit()

        await publish_notification_outbox_events(
            mock_js, outbox=outbox, batch=10, interval_seconds=0.01, max_iterations=1,
        )

        remaining = outbox.fetch_unpublished()
        matching = [e for e in remaining if isinstance(e, type(event))]
        assert len(matching) == 0, f"Event type {name} not published"


# ===================================================================
# Additional cross-cutting scenarios
# ===================================================================


class TestCrossCuttingScenarios:
    def test_create_and_outbox_has_event(self, client, session, outbox) -> None:
        client.post("/api/v1/notification/notifications", json={
            "title": "Outbox", "message": "Test", "priority": "normal",
            "channel": "in_app", "target_type": "user", "target_id": "u1",
        })
        events = outbox.fetch_unpublished()
        assert any(isinstance(e, NotificationCreated) for e in events)

    def test_show_creates_outbox_event(self, client, session, notif_repo, outbox) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        client.post(f"/api/v1/notification/notifications/{nid}/show")
        events = outbox.fetch_unpublished()
        assert any(isinstance(e, NotificationShown) for e in events)

    def test_expire_via_api_creates_outbox_event(self, client, session, notif_repo, outbox) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        client.post(f"/api/v1/notification/notifications/{nid}/expire")
        events = outbox.fetch_unpublished()
        assert any(isinstance(e, NotificationExpired) for e in events)

    def test_create_list_show_acknowledge_dismiss_cycle(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()

        client.post(f"/api/v1/notification/notifications/{nid}/show")
        client.post(f"/api/v1/notification/notifications/{nid}/acknowledge")
        get_resp = client.get(f"/api/v1/notification/notifications/{nid}")
        assert get_resp.json()["status"] == "acknowledged"

    def test_create_notification_then_list_by_status(self, client, session, notif_repo) -> None:
        nid = save_notif(notif_repo)
        session.commit()
        client.post(f"/api/v1/notification/notifications/{nid}/show")
        resp = client.get("/api/v1/notification/notifications?status=shown")
        assert resp.json()["total"] >= 1

    def test_nats_payload_structure(self, session, outbox, mock_js) -> None:
        event = NotificationCreated(
            NotificationId(), "Payload", "Test", "high", "desktop", "admin", "a1",
            datetime.now(tz=timezone.utc),
        )
        outbox.append(event)
        session.commit()

        import backend.notification.nats as nats_mod
        asyncio.run(nats_mod.publish_notification_outbox_events(
            mock_js, outbox=outbox, batch=10, interval_seconds=0.01, max_iterations=1,
        ))

        payload = json.loads(mock_js.publish.await_args[0][1])
        assert payload["event_type"] == "NOTIFICATION_CREATED"
        assert payload["producer"] == "notification"
        assert payload["kind"] == "event"
        assert "event_id" in payload
        assert "aggregate_id" in payload
        assert "occurred_at" in payload
        assert payload["title"] == "Payload"
        assert payload["message"] == "Test"
        assert payload["priority"] == "high"
        assert payload["channel"] == "desktop"

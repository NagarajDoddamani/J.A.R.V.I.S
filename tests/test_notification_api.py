from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api.endpoints import notification
from backend.core.database import get_db
from backend.notification.adapters.outbound.mapper import (
    NotificationActionMapperImpl,
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
    NotificationAction,
    NotificationChannel,
    NotificationId,
    NotificationMessage,
    NotificationPriority,
    NotificationTarget,
    NotificationTitle,
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
def client(session):
    def _override_get_db():
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    app = FastAPI()
    app.include_router(notification.router, prefix="/api/v1/notification")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


@pytest.fixture
def notif_repo(session):
    return SqlAlchemyNotificationRepository(session, mapper=NotificationMapperImpl())


@pytest.fixture
def action_repo(session):
    return SqlAlchemyNotificationActionRepository(session, mapper=NotificationActionMapperImpl())


def create_notification_in_repo(notif_repo, title="Test title", message="Test message") -> str:
    notif = Notification(
        notification_id=NotificationId(),
        title=NotificationTitle(value=title),
        message=NotificationMessage(value=message),
        priority=NotificationPriority.NORMAL,
        channel=NotificationChannel.IN_APP,
        target=NotificationTarget(target_type="user", target_id="user-1"),
    )
    notif_repo.save(notif)
    return str(notif.notification_id)


class TestCreateNotification:
    URL = "/api/v1/notification/notifications"

    def test_create_notification_success(self, client) -> None:
        resp = client.post(
            self.URL,
            json={
                "title": "Welcome",
                "message": "Hello world",
                "priority": "normal",
                "channel": "in_app",
                "target_type": "user",
                "target_id": "user-1",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Welcome"
        assert data["message"] == "Hello world"
        assert data["status"] == "pending"

    def test_create_notification_response_shape(self, client) -> None:
        resp = client.post(
            self.URL,
            json={
                "title": "Shape",
                "message": "Test",
                "priority": "high",
                "channel": "desktop",
                "target_type": "user",
                "target_id": "user-2",
            },
        )
        assert resp.status_code == 201
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

    def test_create_notification_with_expiry(self, client) -> None:
        future = (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat()
        resp = client.post(
            self.URL,
            json={
                "title": "Expiring",
                "message": "Will expire",
                "priority": "normal",
                "channel": "in_app",
                "target_type": "user",
                "target_id": "user-1",
                "expires_at": future,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["expires_at"] is not None

    def test_create_notification_empty_title_returns_422(self, client) -> None:
        resp = client.post(
            self.URL,
            json={
                "title": "",
                "message": "Hello",
                "priority": "normal",
                "channel": "in_app",
                "target_type": "user",
                "target_id": "user-1",
            },
        )
        assert resp.status_code == 422

    def test_create_notification_empty_message_returns_422(self, client) -> None:
        resp = client.post(
            self.URL,
            json={
                "title": "Test",
                "message": "",
                "priority": "normal",
                "channel": "in_app",
                "target_type": "user",
                "target_id": "user-1",
            },
        )
        assert resp.status_code == 422

    def test_create_notification_invalid_priority_returns_422(self, client) -> None:
        resp = client.post(
            self.URL,
            json={
                "title": "Test",
                "message": "Hello",
                "priority": "urgent",
                "channel": "in_app",
                "target_type": "user",
                "target_id": "user-1",
            },
        )
        assert resp.status_code == 422

    def test_create_notification_past_expiry_returns_422(self, client) -> None:
        past = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat()
        resp = client.post(
            self.URL,
            json={
                "title": "Test",
                "message": "Hello",
                "priority": "normal",
                "channel": "in_app",
                "target_type": "user",
                "target_id": "user-1",
                "expires_at": past,
            },
        )
        assert resp.status_code == 422


class TestShowNotification:
    URL = "/api/v1/notification/notifications"

    def test_show_notification_success(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        resp = client.post(f"{self.URL}/{nid}/show")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "shown"
        assert data["shown_at"] is not None

    def test_show_notification_not_found(self, client) -> None:
        resp = client.post(
            f"{self.URL}/00000000-0000-0000-0000-000000000000/show"
        )
        assert resp.status_code == 404

    def test_show_notification_twice_returns_400(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        client.post(f"{self.URL}/{nid}/show")
        resp = client.post(f"{self.URL}/{nid}/show")
        assert resp.status_code == 400

    def test_show_notification_response_shape(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        resp = client.post(f"{self.URL}/{nid}/show")
        data = resp.json()
        assert "notification_id" in data
        assert "status" in data
        assert "shown_at" in data


class TestAcknowledgeNotification:
    URL = "/api/v1/notification/notifications"

    def test_acknowledge_notification_success(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        client.post(f"{self.URL}/{nid}/show")
        resp = client.post(f"{self.URL}/{nid}/acknowledge")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "acknowledged"
        assert data["acknowledged_at"] is not None

    def test_acknowledge_notification_not_found(self, client) -> None:
        resp = client.post(
            f"{self.URL}/00000000-0000-0000-0000-000000000000/acknowledge"
        )
        assert resp.status_code == 404

    def test_acknowledge_pending_returns_400(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        resp = client.post(f"{self.URL}/{nid}/acknowledge")
        assert resp.status_code == 400

    def test_acknowledge_notification_response_shape(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        client.post(f"{self.URL}/{nid}/show")
        resp = client.post(f"{self.URL}/{nid}/acknowledge")
        data = resp.json()
        assert "notification_id" in data
        assert "status" in data
        assert "acknowledged_at" in data


class TestDismissNotification:
    URL = "/api/v1/notification/notifications"

    def test_dismiss_notification_success(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        client.post(f"{self.URL}/{nid}/show")
        resp = client.post(f"{self.URL}/{nid}/dismiss")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "dismissed"
        assert data["dismissed_at"] is not None

    def test_dismiss_notification_not_found(self, client) -> None:
        resp = client.post(
            f"{self.URL}/00000000-0000-0000-0000-000000000000/dismiss"
        )
        assert resp.status_code == 404

    def test_dismiss_pending_returns_400(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        resp = client.post(f"{self.URL}/{nid}/dismiss")
        assert resp.status_code == 400

    def test_dismiss_notification_response_shape(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        client.post(f"{self.URL}/{nid}/show")
        resp = client.post(f"{self.URL}/{nid}/dismiss")
        data = resp.json()
        assert "notification_id" in data
        assert "status" in data
        assert "dismissed_at" in data


class TestExpireNotification:
    URL = "/api/v1/notification/notifications"

    def test_expire_notification_success(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        resp = client.post(f"{self.URL}/{nid}/expire")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "expired"

    def test_expire_notification_not_found(self, client) -> None:
        resp = client.post(
            f"{self.URL}/00000000-0000-0000-0000-000000000000/expire"
        )
        assert resp.status_code == 404

    def test_expire_already_expired_returns_400(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        client.post(f"{self.URL}/{nid}/expire")
        resp = client.post(f"{self.URL}/{nid}/expire")
        assert resp.status_code == 400

    def test_expire_notification_response_shape(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        resp = client.post(f"{self.URL}/{nid}/expire")
        data = resp.json()
        assert "notification_id" in data
        assert "status" in data


class TestGetNotification:
    URL = "/api/v1/notification/notifications"

    def test_get_notification_success(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        resp = client.get(f"{self.URL}/{nid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["notification_id"] == nid

    def test_get_notification_not_found(self, client) -> None:
        resp = client.get(
            f"{self.URL}/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_get_notification_response_shape(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        resp = client.get(f"{self.URL}/{nid}")
        data = resp.json()
        assert "notification_id" in data
        assert "title" in data
        assert "message" in data
        assert "priority" in data
        assert "channel" in data
        assert "status" in data
        assert "created_at" in data

    def test_get_notification_after_show(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        client.post(f"{self.URL}/{nid}/show")
        resp = client.get(f"{self.URL}/{nid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "shown"


class TestListNotifications:
    URL = "/api/v1/notification/notifications"

    def test_list_empty(self, client) -> None:
        resp = client.get(self.URL)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_with_notifications(self, client, session, notif_repo) -> None:
        create_notification_in_repo(notif_repo)
        create_notification_in_repo(notif_repo, title="Second")
        session.commit()
        resp = client.get(self.URL)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 2

    def test_list_by_status(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        client.post(f"{self.URL}/{nid}/show")
        resp = client.get(f"{self.URL}?status=shown")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_by_priority(self, client, session, notif_repo) -> None:
        create_notification_in_repo(notif_repo)
        session.commit()
        resp = client.get(f"{self.URL}?priority=normal")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_list_by_target_type_and_id(self, client, session, notif_repo) -> None:
        create_notification_in_repo(notif_repo)
        session.commit()
        resp = client.get(f"{self.URL}?target_type=user&target_id=user-1")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_list_by_target_id(self, client, session, notif_repo) -> None:
        create_notification_in_repo(notif_repo)
        session.commit()
        resp = client.get(f"{self.URL}?target_id=user-1")
        assert resp.status_code == 200

    def test_list_response_shape(self, client, session, notif_repo) -> None:
        create_notification_in_repo(notif_repo)
        session.commit()
        resp = client.get(self.URL)
        data = resp.json()
        assert "notifications" in data
        assert "total" in data
        assert isinstance(data["notifications"], list)


class TestCreateAction:
    URL = "/api/v1/notification/notifications"

    def test_create_action_success(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        resp = client.post(
            f"{self.URL}/{nid}/actions",
            json={"notification_id": nid, "label": "OK", "callback_name": "ok_callback"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["label"] == "OK"
        assert data["callback_name"] == "ok_callback"

    def test_create_action_notification_not_found(self, client) -> None:
        resp = client.post(
            f"{self.URL}/00000000-0000-0000-0000-000000000000/actions",
            json={"notification_id": "00000000-0000-0000-0000-000000000000", "label": "OK", "callback_name": "ok_callback"},
        )
        assert resp.status_code == 404

    def test_create_action_response_shape(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        resp = client.post(
            f"{self.URL}/{nid}/actions",
            json={"notification_id": nid, "label": "OK", "callback_name": "ok_callback"},
        )
        data = resp.json()
        assert "action_id" in data
        assert "label" in data
        assert "callback_name" in data
        assert "created_at" in data

    def test_create_action_empty_label_returns_422(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        resp = client.post(
            f"{self.URL}/{nid}/actions",
            json={"notification_id": nid, "label": "", "callback_name": "ok_callback"},
        )
        assert resp.status_code == 422


class TestInvokeAction:
    URL = "/api/v1/notification/notifications"

    def test_invoke_action_success(self, client, session, notif_repo, action_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        create_resp = client.post(
            f"{self.URL}/{nid}/actions",
            json={"notification_id": nid, "label": "OK", "callback_name": "ok_callback"},
        )
        aid = create_resp.json()["action_id"]
        resp = client.post(f"{self.URL}/actions/{aid}/invoke")
        assert resp.status_code == 200
        data = resp.json()
        assert data["callback_name"] == "ok_callback"
        assert data["occurred_at"] is not None

    def test_invoke_action_not_found(self, client) -> None:
        resp = client.post(
            f"{self.URL}/actions/00000000-0000-0000-0000-000000000000/invoke"
        )
        assert resp.status_code == 404

    def test_invoke_action_response_shape(self, client, session, notif_repo, action_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        create_resp = client.post(
            f"{self.URL}/{nid}/actions",
            json={"notification_id": nid, "label": "OK", "callback_name": "ok_callback"},
        )
        aid = create_resp.json()["action_id"]
        resp = client.post(f"{self.URL}/actions/{aid}/invoke")
        data = resp.json()
        assert "action_id" in data
        assert "callback_name" in data
        assert "occurred_at" in data


class TestIntegrationFlows:
    def test_create_then_get_notification(self, client) -> None:
        create_resp = client.post(
            "/api/v1/notification/notifications",
            json={
                "title": "Integration",
                "message": "Test",
                "priority": "normal",
                "channel": "in_app",
                "target_type": "user",
                "target_id": "user-1",
            },
        )
        assert create_resp.status_code == 201
        nid = create_resp.json()["notification_id"]
        get_resp = client.get(f"/api/v1/notification/notifications/{nid}")
        assert get_resp.status_code == 200
        assert get_resp.json()["title"] == "Integration"

    def test_create_show_then_get(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        client.post(f"/api/v1/notification/notifications/{nid}/show")
        get_resp = client.get(f"/api/v1/notification/notifications/{nid}")
        assert get_resp.json()["status"] == "shown"

    def test_show_acknowledge_then_get(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        client.post(f"/api/v1/notification/notifications/{nid}/show")
        client.post(f"/api/v1/notification/notifications/{nid}/acknowledge")
        get_resp = client.get(f"/api/v1/notification/notifications/{nid}")
        assert get_resp.json()["status"] == "acknowledged"

    def test_create_action_then_invoke(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        create_resp = client.post(
            f"/api/v1/notification/notifications/{nid}/actions",
            json={"notification_id": nid, "label": "OK", "callback_name": "ok_callback"},
        )
        aid = create_resp.json()["action_id"]
        invoke_resp = client.post(
            f"/api/v1/notification/notifications/actions/{aid}/invoke"
        )
        assert invoke_resp.status_code == 200

    def test_list_after_create(self, client) -> None:
        client.post(
            "/api/v1/notification/notifications",
            json={
                "title": "List test",
                "message": "Test",
                "priority": "normal",
                "channel": "in_app",
                "target_type": "user",
                "target_id": "user-1",
            },
        )
        resp = client.get("/api/v1/notification/notifications")
        assert resp.json()["total"] >= 1


class TestErrorMapping:
    def test_show_nonexistent_notification_404(self, client) -> None:
        resp = client.post(
            "/api/v1/notification/notifications/00000000-0000-0000-0000-000000000000/show"
        )
        assert resp.status_code == 404

    def test_acknowledge_nonexistent_notification_404(self, client) -> None:
        resp = client.post(
            "/api/v1/notification/notifications/00000000-0000-0000-0000-000000000000/acknowledge"
        )
        assert resp.status_code == 404

    def test_dismiss_nonexistent_notification_404(self, client) -> None:
        resp = client.post(
            "/api/v1/notification/notifications/00000000-0000-0000-0000-000000000000/dismiss"
        )
        assert resp.status_code == 404

    def test_expire_nonexistent_notification_404(self, client) -> None:
        resp = client.post(
            "/api/v1/notification/notifications/00000000-0000-0000-0000-000000000000/expire"
        )
        assert resp.status_code == 404

    def test_get_nonexistent_notification_404(self, client) -> None:
        resp = client.get(
            "/api/v1/notification/notifications/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_invoke_nonexistent_action_404(self, client) -> None:
        resp = client.post(
            "/api/v1/notification/notifications/actions/00000000-0000-0000-0000-000000000000/invoke"
        )
        assert resp.status_code == 404

    def test_create_notification_invalid_priority_422(self, client) -> None:
        resp = client.post(
            "/api/v1/notification/notifications",
            json={
                "title": "Test",
                "message": "Hello",
                "priority": "invalid",
                "channel": "in_app",
                "target_type": "user",
                "target_id": "user-1",
            },
        )
        assert resp.status_code == 422

    def test_show_already_shown_400(self, client, session, notif_repo) -> None:
        nid = create_notification_in_repo(notif_repo)
        session.commit()
        client.post(f"/api/v1/notification/notifications/{nid}/show")
        resp = client.post(f"/api/v1/notification/notifications/{nid}/show")
        assert resp.status_code == 400

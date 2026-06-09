from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api.endpoints import notification
from backend.core.database import get_db
from backend.notification.adapters.outbound.models import Base
from backend.notification.bootstrap import (
    acknowledge_notification_use_case,
    create_action_use_case,
    create_notification_use_case,
    dismiss_notification_use_case,
    expire_notification_use_case,
    get_notification_use_case,
    invoke_action_use_case,
    list_notifications_use_case,
    show_notification_use_case,
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


class TestBootstrapUseCases:
    def test_create_notification_use_case(self, session) -> None:
        with patch("backend.notification.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = create_notification_use_case()
            assert isinstance(uc, CreateNotificationUseCase)

    def test_show_notification_use_case(self, session) -> None:
        with patch("backend.notification.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = show_notification_use_case()
            assert isinstance(uc, ShowNotificationUseCase)

    def test_acknowledge_notification_use_case(self, session) -> None:
        with patch("backend.notification.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = acknowledge_notification_use_case()
            assert isinstance(uc, AcknowledgeNotificationUseCase)

    def test_dismiss_notification_use_case(self, session) -> None:
        with patch("backend.notification.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = dismiss_notification_use_case()
            assert isinstance(uc, DismissNotificationUseCase)

    def test_expire_notification_use_case(self, session) -> None:
        with patch("backend.notification.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = expire_notification_use_case()
            assert isinstance(uc, ExpireNotificationUseCase)

    def test_get_notification_use_case(self, session) -> None:
        with patch("backend.notification.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = get_notification_use_case()
            assert isinstance(uc, GetNotificationUseCase)

    def test_list_notifications_use_case(self, session) -> None:
        with patch("backend.notification.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = list_notifications_use_case()
            assert isinstance(uc, ListNotificationsUseCase)

    def test_create_action_use_case(self, session) -> None:
        with patch("backend.notification.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = create_action_use_case()
            assert isinstance(uc, CreateActionUseCase)

    def test_invoke_action_use_case(self, session) -> None:
        with patch("backend.notification.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = invoke_action_use_case()
            assert isinstance(uc, InvokeActionUseCase)


class TestBootstrapThroughApi:
    def test_create_notification_success(self, client) -> None:
        resp = client.post(
            "/api/v1/notification/notifications",
            json={
                "title": "Test",
                "message": "Hello",
                "priority": "normal",
                "channel": "in_app",
                "target_type": "user",
                "target_id": "user-1",
            },
        )
        assert resp.status_code == 201

    def test_list_notifications_empty(self, client) -> None:
        resp = client.get("/api/v1/notification/notifications")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    def test_get_notification_not_found(self, client) -> None:
        resp = client.get(
            "/api/v1/notification/notifications/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_show_notification_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/notification/notifications/00000000-0000-0000-0000-000000000000/show"
        )
        assert resp.status_code == 404

    def test_acknowledge_notification_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/notification/notifications/00000000-0000-0000-0000-000000000000/acknowledge"
        )
        assert resp.status_code == 404

    def test_dismiss_notification_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/notification/notifications/00000000-0000-0000-0000-000000000000/dismiss"
        )
        assert resp.status_code == 404

    def test_expire_notification_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/notification/notifications/00000000-0000-0000-0000-000000000000/expire"
        )
        assert resp.status_code == 404

    def test_create_action_notification_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/notification/notifications/00000000-0000-0000-0000-000000000000/actions",
            json={"notification_id": "00000000-0000-0000-0000-000000000000", "label": "OK", "callback_name": "ok_action"},
        )
        assert resp.status_code == 404

    def test_invoke_action_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/notification/notifications/actions/00000000-0000-0000-0000-000000000000/invoke"
        )
        assert resp.status_code == 404

    def test_create_notification_empty_title_returns_422(self, client) -> None:
        resp = client.post(
            "/api/v1/notification/notifications",
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

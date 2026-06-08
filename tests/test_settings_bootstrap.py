from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api.endpoints import settings
from backend.core.database import get_db
from backend.settings.adapters.outbound.clock import SystemClockAdapter
from backend.settings.adapters.outbound.models import (
    Base,
    SettingModel,
    SettingsOutboxModel,
    SettingsProfileModel,
)
from backend.settings.bootstrap import (
    DEFAULT_REGISTRY,
    get_setting_by_key_use_case,
    get_settings_use_case,
    patch_settings_use_case,
    reset_settings_use_case,
)
from backend.settings.application.use_cases.get_setting_by_key import (
    GetSettingByKeyUseCase,
)
from backend.settings.application.use_cases.get_settings import (
    GetSettingsUseCase,
)
from backend.settings.application.use_cases.patch_settings import (
    PatchSettingsUseCase,
)
from backend.settings.application.use_cases.reset_settings import (
    ResetSettingsUseCase,
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
    app.include_router(settings.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


class TestDefaultRegistry:
    def test_registry_contains_expected_keys(self) -> None:
        expected_keys = {
            "system.language",
            "system.timezone",
            "system.auto_start",
            "privacy.history_retention_days",
            "privacy.analytics_enabled",
            "privacy.consent_required",
            "voice.wake_word",
            "voice.microphone",
            "voice.wake_word_enabled",
            "voice.retain_audio",
            "voice.tts_enabled",
            "voice.tts_speed",
            "notification.sounds_enabled",
            "notification.quiet_hours_start",
            "notification.quiet_hours_end",
            "model.temperature",
            "model.top_p",
            "model.max_tokens",
            "ui.theme",
            "ui.reduced_motion",
        }
        assert set(DEFAULT_REGISTRY.keys()) == expected_keys

    def test_registry_categories(self) -> None:
        cat_keys = {v.category.value for v in DEFAULT_REGISTRY.values()}
        assert cat_keys == {"system", "privacy", "voice", "notification", "model", "ui"}

    def test_registry_has_no_missing_defaults(self) -> None:
        for key, definition in DEFAULT_REGISTRY.items():
            assert definition.default_value is not None, f"{key} missing default"

    def test_registry_types(self) -> None:
        for key, definition in DEFAULT_REGISTRY.items():
            assert definition.key == key


class TestBootstrapUseCases:
    def test_get_settings_use_case(self, session) -> None:
        with patch("backend.settings.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = get_settings_use_case()
            assert isinstance(uc, GetSettingsUseCase)

    def test_get_setting_by_key_use_case(self, session) -> None:
        with patch("backend.settings.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = get_setting_by_key_use_case()
            assert isinstance(uc, GetSettingByKeyUseCase)

    def test_patch_settings_use_case(self, session) -> None:
        with patch("backend.settings.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = patch_settings_use_case()
            assert isinstance(uc, PatchSettingsUseCase)

    def test_reset_settings_use_case(self, session) -> None:
        with patch("backend.settings.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = session
            uc = reset_settings_use_case()
            assert isinstance(uc, ResetSettingsUseCase)

    def test_patch_use_case_has_registry(self) -> None:
        with patch("backend.settings.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = MagicMock()
            uc = patch_settings_use_case()
            assert uc._registry is DEFAULT_REGISTRY

    def test_reset_use_case_has_registry(self) -> None:
        with patch("backend.settings.bootstrap.get_db") as mock_get_db:
            mock_get_db.return_value = MagicMock()
            uc = reset_settings_use_case()
            assert uc._registry is DEFAULT_REGISTRY


class TestBootstrapThroughApi:
    def test_get_settings_empty(self, client) -> None:
        resp = client.get("/api/v1/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["settings"] == []

    def test_patch_settings_creates_profile_and_returns_updates(self, client) -> None:
        resp = client.patch(
            "/api/v1/settings",
            json={"updates": {"system.language": "de-DE", "system.timezone": "Europe/Berlin"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated_count"] == 2
        assert len(data["updated_settings"]) == 2
        assert data["profile_version"] == "1.0"

    def test_get_settings_after_patch(self, client) -> None:
        client.patch("/api/v1/settings", json={"updates": {"system.language": "de-DE"}})
        resp = client.get("/api/v1/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0

    def test_get_settings_filter_by_category(self, client) -> None:
        client.patch("/api/v1/settings", json={"updates": {"system.language": "de-DE"}})
        resp = client.get("/api/v1/settings?category=system")
        assert resp.status_code == 200
        data = resp.json()
        for s in data["settings"]:
            assert s["category"] == "system"

    def test_get_setting_by_key_after_patch(self, client) -> None:
        client.patch("/api/v1/settings", json={"updates": {"system.language": "fr"}})
        resp = client.get("/api/v1/settings/system.language")
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"] == "system.language"
        assert data["value"] == "fr"

    def test_get_setting_by_key_not_found(self, client) -> None:
        resp = client.get("/api/v1/settings/nonexistent.key")
        assert resp.status_code == 404

    def test_patch_single_setting(self, client) -> None:
        resp = client.patch("/api/v1/settings/system.language", json={"value": "ja"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated_count"] == 1
        assert data["updated_settings"][0]["key"] == "system.language"
        assert data["updated_settings"][0]["value"] == "ja"

    def test_patch_single_setting_missing_value(self, client) -> None:
        resp = client.patch("/api/v1/settings/system.language", json={})
        assert resp.status_code == 422

    def test_patch_settings_missing_updates(self, client) -> None:
        resp = client.patch("/api/v1/settings", json={})
        assert resp.status_code == 422

    def test_patch_settings_invalid_updates_type(self, client) -> None:
        resp = client.patch("/api/v1/settings", json={"updates": "not-a-dict"})
        assert resp.status_code == 422

    def test_patch_invalid_value_type(self, client) -> None:
        resp = client.patch(
            "/api/v1/settings",
            json={"updates": {"system.language": 123}},
        )
        assert resp.status_code == 400

    def test_patch_unknown_key(self, client) -> None:
        resp = client.patch(
            "/api/v1/settings",
            json={"updates": {"unknown.key": "value"}},
        )
        assert resp.status_code == 400

    def test_reset_settings(self, client) -> None:
        client.patch("/api/v1/settings", json={"updates": {"system.language": "de"}})
        resp = client.post("/api/v1/settings/reset")
        assert resp.status_code == 200
        data = resp.json()
        assert data["reset_count"] == len(DEFAULT_REGISTRY)

    def test_reset_settings_with_category(self, client) -> None:
        client.patch("/api/v1/settings", json={"updates": {"system.language": "de"}})
        resp = client.post("/api/v1/settings/reset", json={"category": "voice"})
        assert resp.status_code == 200

    def test_reset_restores_defaults(self, client) -> None:
        client.patch("/api/v1/settings", json={"updates": {"system.language": "de"}})
        resp = client.post("/api/v1/settings/reset")
        assert resp.status_code == 200
        assert resp.json()["reset_count"] == len(DEFAULT_REGISTRY)

    def test_reserved_key_can_be_patched(self, client) -> None:
        resp = client.patch(
            "/api/v1/settings",
            json={"updates": {"privacy.consent_required": False}},
        )
        assert resp.status_code == 200

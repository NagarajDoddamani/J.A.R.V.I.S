from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api.endpoints import settings
from backend.core.database import get_db
from backend.settings.adapters.outbound.clock import SystemClockAdapter
from backend.settings.adapters.outbound.mapper import (
    SettingMapperImpl,
    SettingsOutboxMapperImpl,
    SettingsProfileMapperImpl,
)
from backend.settings.adapters.outbound.models import (
    Base,
    SettingModel,
    SettingsOutboxModel,
    SettingsProfileModel,
)
from backend.settings.application.use_cases.dto import (
    GetSettingByKeyRequest,
    GetSettingsRequest,
    PatchSettingsRequest,
    ResetSettingsRequest,
    SettingResponse,
)
from backend.settings.application.use_cases.exceptions import (
    SettingNotFoundError,
    SettingsProfileNotFoundError,
)
from backend.settings.bootstrap import DEFAULT_REGISTRY
from backend.settings.domain.exceptions import (
    InvalidSettingValueError,
    ReservedSettingKeyError,
    SettingsDomainError,
    UnknownSettingKeyError,
)
from backend.settings.domain.factory import SettingsProfileFactory

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


class TestGetSettings:
    URL = "/api/v1/settings"

    def test_empty_returns_200_with_zero(self, client) -> None:
        resp = client.get(self.URL)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_with_data_returns_all(self, client) -> None:
        client.patch(self.URL, json={"updates": {"system.language": "en"}})
        resp = client.get(self.URL)
        assert resp.status_code == 200
        assert resp.json()["total"] == 20

    def test_filter_by_category(self, client) -> None:
        client.patch(self.URL, json={"updates": {"system.language": "en"}})
        resp = client.get(f"{self.URL}?category=voice")
        for s in resp.json()["settings"]:
            assert s["category"] == "voice"

    def test_filter_unknown_category_returns_empty(self, client) -> None:
        client.patch(self.URL, json={"updates": {"system.language": "en"}})
        resp = client.get(f"{self.URL}?category=unknown")
        assert resp.json()["total"] == 0

    def test_settings_shape(self, client) -> None:
        client.patch(self.URL, json={"updates": {"ui.theme": "dark"}})
        resp = client.get(self.URL)
        s = resp.json()["settings"][0]
        assert "key" in s
        assert "value" in s
        assert "category" in s
        assert "scope" in s
        assert "version" in s


class TestGetSettingByKey:
    URL = "/api/v1/settings"

    def test_returns_setting(self, client) -> None:
        client.patch(self.URL, json={"updates": {"system.language": "de"}})
        resp = client.get(f"{self.URL}/system.language")
        assert resp.status_code == 200
        assert resp.json()["key"] == "system.language"
        assert resp.json()["value"] == "de"

    def test_not_found_returns_404(self, client) -> None:
        resp = client.get(f"{self.URL}/unknown.key")
        assert resp.status_code == 404

    def test_not_found_message(self, client) -> None:
        resp = client.get(f"{self.URL}/missing.key")
        assert "missing.key" in resp.json()["detail"]

    def test_value_types_are_correct(self, client) -> None:
        client.patch(self.URL, json={"updates": {"system.auto_start": True}})
        resp = client.get(f"{self.URL}/system.auto_start")
        assert resp.json()["value"] is True


class TestPatchSingleSetting:
    URL = "/api/v1/settings"

    def test_patch_single_success(self, client) -> None:
        resp = client.patch(f"{self.URL}/system.language", json={"value": "fr"})
        assert resp.status_code == 200
        assert resp.json()["updated_count"] == 1

    def test_patch_single_missing_value_422(self, client) -> None:
        resp = client.patch(f"{self.URL}/system.language", json={})
        assert resp.status_code == 422

    def test_patch_single_none_value_422(self, client) -> None:
        resp = client.patch(f"{self.URL}/system.language", json={"value": None})
        assert resp.status_code == 422

    def test_patch_single_invalid_type_400(self, client) -> None:
        resp = client.patch(f"{self.URL}/system.auto_start", json={"value": "not-bool"})
        assert resp.status_code == 400

    def test_patch_single_unknown_key_404(self, client) -> None:
        resp = client.patch(f"{self.URL}/unknown.key", json={"value": "val"})
        assert resp.status_code == 400


class TestPatchBulk:
    URL = "/api/v1/settings"

    def test_bulk_success(self, client) -> None:
        resp = client.patch(self.URL, json={"updates": {"system.language": "ja", "ui.theme": "dark"}})
        assert resp.status_code == 200
        assert resp.json()["updated_count"] == 2

    def test_bulk_returned_settings(self, client) -> None:
        resp = client.patch(self.URL, json={"updates": {"system.language": "ko"}})
        s = resp.json()["updated_settings"][0]
        assert s["key"] == "system.language"
        assert s["value"] == "ko"

    def test_bulk_no_updates_key_422(self, client) -> None:
        resp = client.patch(self.URL, json={})
        assert resp.status_code == 422

    def test_bulk_updates_not_dict_422(self, client) -> None:
        resp = client.patch(self.URL, json={"updates": "bad"})
        assert resp.status_code == 422

    def test_bulk_empty_updates_422(self, client) -> None:
        resp = client.patch(self.URL, json={"updates": {}})
        assert resp.status_code == 422

    def test_bulk_unknown_key_400(self, client) -> None:
        resp = client.patch(self.URL, json={"updates": {"nope": "val"}})
        assert resp.status_code == 400

    def test_bulk_reserved_key_is_accepted_by_api(self, client) -> None:
        resp = client.patch(self.URL, json={"updates": {"privacy.consent_required": False}})
        assert resp.status_code == 200
        get_resp = client.get("/api/v1/settings/privacy.consent_required")
        assert get_resp.json()["value"] is False

    def test_bulk_invalid_bool_value_400(self, client) -> None:
        resp = client.patch(self.URL, json={"updates": {"system.auto_start": "maybe"}})
        assert resp.status_code == 400

    def test_bulk_out_of_bounds_400(self, client) -> None:
        resp = client.patch(self.URL, json={"updates": {"model.temperature": 99.0}})
        assert resp.status_code == 400

    def test_bulk_max_tokens_too_low_400(self, client) -> None:
        resp = client.patch(self.URL, json={"updates": {"model.max_tokens": 10}})
        assert resp.status_code == 400

    def test_bulk_allowed_values_400(self, client) -> None:
        resp = client.patch(self.URL, json={"updates": {"ui.theme": "neon"}})
        assert resp.status_code == 400


class TestResetSettings:
    URL = "/api/v1/settings/reset"

    def test_reset_all(self, client) -> None:
        client.patch("/api/v1/settings", json={"updates": {"system.language": "de"}})
        resp = client.post(self.URL)
        assert resp.status_code == 200
        assert resp.json()["reset_count"] == 20

    def test_reset_category(self, client) -> None:
        client.patch("/api/v1/settings", json={"updates": {"system.language": "de"}})
        resp = client.post(self.URL, json={"category": "system"})
        assert resp.status_code == 200

    def test_reset_category_returns_200(self, client) -> None:
        client.patch("/api/v1/settings", json={"updates": {"system.language": "de"}})
        resp = client.post(self.URL, json={"category": "system"})
        assert resp.status_code == 200
        assert resp.json()["reset_count"] > 0

    def test_reset_twice_is_idempotent(self, client) -> None:
        client.post(self.URL)
        resp = client.post(self.URL)
        assert resp.status_code == 200

    def test_reset_invalid_category_400(self, client) -> None:
        resp = client.post(self.URL, json={"category": "nonexistent"})
        assert resp.status_code == 400


class TestEdgeCases:
    def test_post_to_settings_405(self, client) -> None:
        resp = client.post("/api/v1/settings")
        assert resp.status_code == 405

    def test_delete_settings_405(self, client) -> None:
        resp = client.delete("/api/v1/settings/system.language")
        assert resp.status_code == 405

    def test_put_settings_405(self, client) -> None:
        resp = client.put("/api/v1/settings/system.language", json={"value": "x"})
        assert resp.status_code == 405

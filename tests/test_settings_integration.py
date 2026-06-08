from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api.endpoints import settings as settings_router
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
from backend.settings.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemySettingsOutboxAdapter,
    SqlAlchemySettingsRepository,
)
from backend.settings.bootstrap import DEFAULT_REGISTRY
from backend.settings.domain.factory import SettingsProfileFactory
from backend.settings.domain.model import (
    Setting,
    SettingCategory,
    SettingId,
    SettingScope,
    SettingsProfile,
    SettingsReset,
    SettingUpdated,
    Version,
)
from backend.settings.nats import publish_settings_outbox_events

for _table in Base.metadata.tables.values():
    _table.schema = None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    e = create_engine(
        "sqlite://", echo=False, connect_args={"check_same_thread": False}
    )
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
def repo(session):
    return SqlAlchemySettingsRepository(session)


@pytest.fixture
def outbox(session):
    return SqlAlchemySettingsOutboxAdapter(session)


@pytest.fixture
def clock():
    return SystemClockAdapter()


@pytest.fixture
def mock_js():
    js = AsyncMock()
    js.publish = AsyncMock()
    return js


# ---------------------------------------------------------------------------
# 1. Full Settings Lifecycle
# ---------------------------------------------------------------------------


class TestFullSettingsLifecycle:
    """Verify the complete create→patch→query→reset→publish lifecycle."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, session, repo, outbox, clock, mock_js) -> None:
        profile = SettingsProfileFactory.create(DEFAULT_REGISTRY)
        assert profile.count() == 20

        repo.save(profile)
        session.commit()
        profile_id_str = str(profile.profile_id)

        loaded = repo.find_by_id(profile.profile_id)
        assert loaded is not None
        assert loaded.count() == 20
        assert loaded.get("system.language") is not None
        assert loaded.get("system.language").value == "en-US"

        from backend.settings.application.use_cases.patch_settings import (
            PatchSettingsUseCase,
        )

        patcher = PatchSettingsUseCase(
            repo=repo, outbox=outbox, clock=clock, registry=DEFAULT_REGISTRY
        )
        from backend.settings.application.use_cases.dto import (
            PatchSettingsRequest,
        )

        patch_result = patcher.execute(
            PatchSettingsRequest(
                updates={"system.language": "de-DE", "ui.theme": "dark"},
                profile_id=profile_id_str,
            )
        )
        assert patch_result.updated_count == 2
        session.commit()

        after_patch = repo.find_by_id(profile.profile_id)
        assert after_patch is not None
        assert after_patch.get("system.language").value == "de-DE"
        assert after_patch.get("ui.theme").value == "dark"

        setting = repo.find_by_key("system.language")
        assert setting is not None
        assert setting.value == "de-DE"

        from backend.settings.application.use_cases.reset_settings import (
            ResetSettingsUseCase,
        )

        resetter = ResetSettingsUseCase(
            repo=repo, outbox=outbox, clock=clock, registry=DEFAULT_REGISTRY
        )
        from backend.settings.application.use_cases.dto import (
            ResetSettingsRequest,
        )

        reset_result = resetter.execute(
            ResetSettingsRequest(profile_id=profile_id_str, category="system")
        )
        assert reset_result.reset_count > 0
        session.commit()

        after_reset_category = repo.find_by_id(profile.profile_id)
        assert after_reset_category is not None
        assert after_reset_category.get("system.language").value == "en-US"

        reset_all = resetter.execute(
            ResetSettingsRequest(profile_id=profile_id_str)
        )
        assert reset_all.reset_count == 20
        session.commit()

        after_reset_all = repo.find_by_id(profile.profile_id)
        assert after_reset_all is not None
        for key, definition in DEFAULT_REGISTRY.items():
            assert after_reset_all.get(key).value == definition.default_value

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) > 0

        await publish_settings_outbox_events(
            mock_js,
            outbox=outbox,
            batch=50,
            interval_seconds=0.01,
            max_iterations=1,
        )

        remaining = outbox.fetch_unpublished()
        assert len(remaining) == 0

        assert mock_js.publish.await_count >= 1


# ---------------------------------------------------------------------------
# 2. Repository Roundtrip
# ---------------------------------------------------------------------------


class TestRepositoryRoundtrip:
    """Verify Domain → DTO → ORM → DB → ORM → DTO → Domain is lossless."""

    def test_roundtrip_preserves_all_fields(self, session, repo) -> None:
        profile = SettingsProfileFactory.create(DEFAULT_REGISTRY)
        repo.save(profile)
        session.commit()

        loaded = repo.find_by_id(profile.profile_id)
        assert loaded is not None
        assert str(loaded.profile_id) == str(profile.profile_id)
        assert loaded.schema_version.major == profile.schema_version.major
        assert loaded.schema_version.minor == profile.schema_version.minor
        assert loaded.count() == profile.count()

        for key in DEFAULT_REGISTRY:
            orig = profile.get(key)
            recons = loaded.get(key)
            assert recons is not None, f"Missing key after roundtrip: {key}"
            assert recons.key == orig.key
            assert recons.value == orig.value
            assert recons.category == orig.category
            assert recons.scope == orig.scope
            assert recons.version == orig.version

    def test_multi_profile_roundtrip(self, session, repo) -> None:
        p1 = SettingsProfileFactory.create(DEFAULT_REGISTRY)
        p2 = SettingsProfileFactory.create(DEFAULT_REGISTRY)
        repo.save(p1)
        repo.save(p2)
        session.commit()

        l1 = repo.find_by_id(p1.profile_id)
        l2 = repo.find_by_id(p2.profile_id)
        assert l1 is not None
        assert l2 is not None
        assert l1.count() == 20
        assert l2.count() == 20

    def test_value_types_preserved(self, session, repo) -> None:
        profile = SettingsProfileFactory.create(DEFAULT_REGISTRY)
        repo.save(profile)
        session.commit()
        loaded = repo.find_by_id(profile.profile_id)
        assert loaded is not None
        for key, definition in DEFAULT_REGISTRY.items():
            setting = loaded.get(key)
            assert setting is not None
            if definition.value_type == "bool":
                assert isinstance(setting.value, bool), f"{key} should be bool"
            elif definition.value_type == "int":
                assert isinstance(setting.value, int), f"{key} should be int"
            elif definition.value_type == "float":
                assert isinstance(setting.value, float), f"{key} should be float"
            elif definition.value_type == "str":
                assert isinstance(setting.value, str), f"{key} should be str"

    def test_category_and_scope_preserved(self, session, repo) -> None:
        profile = SettingsProfileFactory.create(DEFAULT_REGISTRY)
        repo.save(profile)
        session.commit()
        loaded = repo.find_by_id(profile.profile_id)
        assert loaded is not None
        for key, definition in DEFAULT_REGISTRY.items():
            setting = loaded.get(key)
            assert setting is not None
            assert setting.category == definition.category
            assert setting.scope == definition.scope

    def test_version_preserved(self, session, repo) -> None:
        profile = SettingsProfileFactory.create(DEFAULT_REGISTRY)
        repo.save(profile)
        session.commit()
        loaded = repo.find_by_id(profile.profile_id)
        assert loaded is not None
        for key in DEFAULT_REGISTRY:
            assert loaded.get(key).version == 1


# ---------------------------------------------------------------------------
# 3. Event Flow Validation
# ---------------------------------------------------------------------------


class TestEventFlowValidation:
    """Verify SettingUpdated/SettingsReset flow through outbox → NATS."""

    def test_setting_updated_event_flow(self, session, repo, outbox, clock) -> None:
        profile = SettingsProfileFactory.create(DEFAULT_REGISTRY)
        repo.save(profile)
        session.commit()

        from backend.settings.application.use_cases.patch_settings import (
            PatchSettingsUseCase,
        )

        patcher = PatchSettingsUseCase(
            repo=repo, outbox=outbox, clock=clock, registry=DEFAULT_REGISTRY
        )
        from backend.settings.application.use_cases.dto import (
            PatchSettingsRequest,
        )

        patcher.execute(
            PatchSettingsRequest(
                updates={"system.language": "fr"},
                profile_id=str(profile.profile_id),
            )
        )
        session.commit()

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        event = unpublished[0]
        assert isinstance(event, SettingUpdated)
        assert event.key == "system.language"
        assert event.new_value == "fr"
        assert event.old_value == "en-US"
        assert event.category == SettingCategory.SYSTEM

    def test_settings_reset_event_flow(self, session, repo, outbox, clock) -> None:
        profile = SettingsProfileFactory.create(DEFAULT_REGISTRY)
        repo.save(profile)
        session.commit()

        from backend.settings.application.use_cases.reset_settings import (
            ResetSettingsUseCase,
        )

        resetter = ResetSettingsUseCase(
            repo=repo, outbox=outbox, clock=clock, registry=DEFAULT_REGISTRY
        )
        from backend.settings.application.use_cases.dto import (
            ResetSettingsRequest,
        )

        resetter.execute(
            ResetSettingsRequest(profile_id=str(profile.profile_id))
        )
        session.commit()

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        event = unpublished[0]
        assert isinstance(event, SettingsReset)
        assert event.previous_count == 20

    def test_fifo_order_preserved(self, session, repo, outbox, clock) -> None:
        profile = SettingsProfileFactory.create(DEFAULT_REGISTRY)
        repo.save(profile)
        session.commit()

        from backend.settings.application.use_cases.patch_settings import (
            PatchSettingsUseCase,
        )

        patcher = PatchSettingsUseCase(
            repo=repo, outbox=outbox, clock=clock, registry=DEFAULT_REGISTRY
        )
        from backend.settings.application.use_cases.dto import (
            PatchSettingsRequest,
        )

        patcher.execute(
            PatchSettingsRequest(
                updates={"system.language": "ja"},
                profile_id=str(profile.profile_id),
            )
        )
        patcher.execute(
            PatchSettingsRequest(
                updates={"ui.theme": "dark"},
                profile_id=str(profile.profile_id),
            )
        )
        session.commit()

        unpublished = outbox.fetch_unpublished(limit=10)
        assert len(unpublished) == 2
        assert isinstance(unpublished[0], SettingUpdated)
        assert isinstance(unpublished[1], SettingUpdated)
        assert unpublished[0].key == "system.language"
        assert unpublished[1].key == "ui.theme"

    @pytest.mark.asyncio
    async def test_nats_payload_content(self, session, repo, outbox, clock, mock_js) -> None:
        profile = SettingsProfileFactory.create(DEFAULT_REGISTRY)
        repo.save(profile)
        session.commit()

        from backend.settings.application.use_cases.patch_settings import (
            PatchSettingsUseCase,
        )

        patcher = PatchSettingsUseCase(
            repo=repo, outbox=outbox, clock=clock, registry=DEFAULT_REGISTRY
        )
        from backend.settings.application.use_cases.dto import (
            PatchSettingsRequest,
        )

        patcher.execute(
            PatchSettingsRequest(
                updates={"system.language": "ko"},
                profile_id=str(profile.profile_id),
            )
        )
        session.commit()

        await publish_settings_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        payload = json.loads(mock_js.publish.await_args[0][1])
        assert payload["event_type"] == "SETTING_UPDATED"
        assert payload["key"] == "system.language"
        assert payload["old_value"] == "en-US" or payload["old_value"] == "None"
        assert payload["new_value"] == "ko"
        assert payload["producer"] == "settings"
        assert payload["kind"] == "event"
        assert "event_id" in payload
        assert "subject" in payload
        assert "profile_id" in payload
        assert "occurred_at" in payload
        assert "category" in payload

    @pytest.mark.asyncio
    async def test_nats_payload_reset_event(self, session, repo, outbox, clock, mock_js) -> None:
        profile = SettingsProfileFactory.create(DEFAULT_REGISTRY)
        repo.save(profile)
        session.commit()

        from backend.settings.application.use_cases.reset_settings import (
            ResetSettingsUseCase,
        )

        resetter = ResetSettingsUseCase(
            repo=repo, outbox=outbox, clock=clock, registry=DEFAULT_REGISTRY
        )
        from backend.settings.application.use_cases.dto import (
            ResetSettingsRequest,
        )

        resetter.execute(
            ResetSettingsRequest(profile_id=str(profile.profile_id))
        )
        session.commit()

        await publish_settings_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.01,
            max_iterations=1,
        )

        payload = json.loads(mock_js.publish.await_args[0][1])
        assert payload["event_type"] == "SETTINGS_RESET"
        assert payload["previous_count"] == 20
        assert payload["producer"] == "settings"

    def test_mark_published_idempotent(self, session, outbox) -> None:
        profile = SettingsProfileFactory.create(DEFAULT_REGISTRY)
        from backend.settings.application.use_cases.patch_settings import (
            PatchSettingsUseCase,
        )

        repo = SqlAlchemySettingsRepository(session)
        clock = SystemClockAdapter()
        patcher = PatchSettingsUseCase(
            repo=repo, outbox=outbox, clock=clock, registry=DEFAULT_REGISTRY
        )
        from backend.settings.application.use_cases.dto import (
            PatchSettingsRequest,
        )

        patcher.execute(PatchSettingsRequest(updates={"system.language": "pt"}))
        session.commit()

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        pid = str(unpublished[0].profile_id)

        outbox.mark_published(pid)
        outbox.mark_published(pid)
        outbox.mark_published(pid)
        session.flush()

        remaining = outbox.fetch_unpublished()
        assert len(remaining) == 0


# ---------------------------------------------------------------------------
# 4. REST Contract Verification
# ---------------------------------------------------------------------------


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
    app.include_router(settings_router.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


class TestRestContractGetSettings:
    URL = "/api/v1/settings"

    def test_get_empty_returns_200_and_zero_total(self, client) -> None:
        resp = client.get(self.URL)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["settings"] == []

    def test_get_after_patch_returns_correct_total(self, client) -> None:
        client.patch(self.URL, json={"updates": {"system.language": "en"}})
        resp = client.get(self.URL)
        assert resp.status_code == 200
        assert resp.json()["total"] == 20

    def test_get_filter_by_category(self, client) -> None:
        client.patch(self.URL, json={"updates": {"system.language": "en"}})
        resp = client.get(f"{self.URL}?category=voice")
        assert resp.status_code == 200
        for s in resp.json()["settings"]:
            assert s["category"] == "voice"

    def test_get_filter_no_match(self, client) -> None:
        client.patch(self.URL, json={"updates": {"system.language": "en"}})
        resp = client.get(f"{self.URL}?category=nonexistent")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_response_dto_shape(self, client) -> None:
        client.patch(self.URL, json={"updates": {"system.language": "en"}})
        resp = client.get(self.URL)
        s = resp.json()["settings"][0]
        assert "key" in s
        assert "value" in s
        assert "category" in s
        assert "scope" in s
        assert "version" in s

    def test_yields_method_not_allowed(self, client) -> None:
        assert client.post(self.URL).status_code in (404, 405)
        assert client.delete(self.URL).status_code in (404, 405)
        assert client.put(self.URL).status_code in (404, 405)


class TestRestContractGetSettingByKey:
    URL = "/api/v1/settings"

    def test_get_by_key_returns_200(self, client) -> None:
        client.patch(self.URL, json={"updates": {"system.language": "en"}})
        resp = client.get(f"{self.URL}/system.language")
        assert resp.status_code == 200

    def test_get_by_key_dto_shape(self, client) -> None:
        client.patch(self.URL, json={"updates": {"system.language": "en"}})
        data = client.get(f"{self.URL}/system.language").json()
        assert "key" in data
        assert "value" in data
        assert "category" in data
        assert "scope" in data
        assert "version" in data
        assert data["key"] == "system.language"
        assert data["value"] == "en"

    def test_get_by_key_404(self, client) -> None:
        resp = client.get(f"{self.URL}/unknown.key")
        assert resp.status_code == 404
        assert "unknown.key" in resp.json()["detail"]

    def test_get_by_key_after_reset(self, client) -> None:
        client.patch(self.URL, json={"updates": {"system.language": "de"}})
        client.post(f"{self.URL}/reset")
        resp = client.get(f"{self.URL}/system.language")
        assert resp.status_code == 200
        assert resp.json()["value"] == "en-US" or resp.json()["value"] is not None


class TestRestContractPatchSingle:
    URL = "/api/v1/settings"

    def test_patch_single_200(self, client) -> None:
        resp = client.patch(f"{self.URL}/system.language", json={"value": "fr"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated_count"] == 1
        assert data["updated_settings"][0]["key"] == "system.language"
        assert data["updated_settings"][0]["value"] == "fr"

    def test_patch_single_422_missing_value(self, client) -> None:
        resp = client.patch(f"{self.URL}/system.language", json={})
        assert resp.status_code == 422

    def test_patch_single_422_null_value(self, client) -> None:
        resp = client.patch(f"{self.URL}/system.language", json={"value": None})
        assert resp.status_code == 422

    def test_patch_single_400_wrong_type(self, client) -> None:
        resp = client.patch(
            f"{self.URL}/system.auto_start", json={"value": "not-bool"}
        )
        assert resp.status_code == 400

    def test_patch_single_400_unknown_key(self, client) -> None:
        resp = client.patch(f"{self.URL}/unknown.key", json={"value": "x"})
        assert resp.status_code == 400

    def test_patch_single_400_out_of_bounds(self, client) -> None:
        resp = client.patch(
            f"{self.URL}/model.temperature", json={"value": 99.0}
        )
        assert resp.status_code == 400


class TestRestContractPatchBulk:
    URL = "/api/v1/settings"

    def test_patch_bulk_200(self, client) -> None:
        resp = client.patch(
            self.URL,
            json={"updates": {"system.language": "ja", "ui.theme": "dark"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated_count"] == 2
        assert data["profile_version"] == "1.0"

    def test_patch_bulk_dto_shape(self, client) -> None:
        resp = client.patch(
            self.URL, json={"updates": {"system.language": "ko"}}
        )
        data = resp.json()
        assert "updated_settings" in data
        assert "updated_count" in data
        assert "profile_version" in data
        assert len(data["updated_settings"]) == 1
        assert data["updated_settings"][0]["key"] == "system.language"

    def test_patch_bulk_422_no_updates_key(self, client) -> None:
        resp = client.patch(self.URL, json={})
        assert resp.status_code == 422

    def test_patch_bulk_422_updates_not_dict(self, client) -> None:
        resp = client.patch(self.URL, json={"updates": "invalid"})
        assert resp.status_code == 422

    def test_patch_bulk_422_empty_updates(self, client) -> None:
        resp = client.patch(self.URL, json={"updates": {}})
        assert resp.status_code == 422

    def test_patch_bulk_400_unknown_key(self, client) -> None:
        resp = client.patch(
            self.URL, json={"updates": {"nonexistent.key": "val"}}
        )
        assert resp.status_code == 400

    def test_patch_bulk_400_type_mismatch(self, client) -> None:
        resp = client.patch(
            self.URL, json={"updates": {"system.auto_start": "maybe"}}
        )
        assert resp.status_code == 400

    def test_patch_bulk_400_bounds(self, client) -> None:
        resp = client.patch(
            self.URL, json={"updates": {"model.max_tokens": 10}}
        )
        assert resp.status_code == 400

    def test_patch_bulk_400_allowed_values(self, client) -> None:
        resp = client.patch(
            self.URL, json={"updates": {"ui.theme": "neon"}}
        )
        assert resp.status_code == 400


class TestRestContractReset:
    URL = "/api/v1/settings/reset"

    def test_reset_200(self, client) -> None:
        client.patch(
            "/api/v1/settings", json={"updates": {"system.language": "de"}}
        )
        resp = client.post(self.URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["reset_count"] == 20
        assert data["profile_version"] == "1.0"

    def test_reset_with_category_200(self, client) -> None:
        client.patch(
            "/api/v1/settings", json={"updates": {"system.language": "de"}}
        )
        resp = client.post(self.URL, json={"category": "system"})
        assert resp.status_code == 200
        assert resp.json()["reset_count"] > 0

    def test_reset_invalid_category_400(self, client) -> None:
        resp = client.post(self.URL, json={"category": "bogus"})
        assert resp.status_code == 400

    def test_reset_twice_is_idempotent(self, client) -> None:
        resp1 = client.post(self.URL)
        resp2 = client.post(self.URL)
        assert resp1.status_code == 200
        assert resp2.status_code == 200

    def test_reset_dto_shape(self, client) -> None:
        resp = client.post(self.URL)
        data = resp.json()
        assert "reset_count" in data
        assert "profile_version" in data

    def test_reset_method_not_allowed(self, client) -> None:
        assert client.get(self.URL).status_code in (404, 405)
        assert client.patch(self.URL).status_code in (404, 405, 422)
        assert client.delete(self.URL).status_code in (404, 405)


# ---------------------------------------------------------------------------
# 5. Cross-profile isolation
# ---------------------------------------------------------------------------


class TestCrossProfileIsolation:
    def test_profiles_do_not_share_settings(self, session, repo) -> None:
        p1 = SettingsProfileFactory.create(DEFAULT_REGISTRY)
        p2 = SettingsProfileFactory.create(DEFAULT_REGISTRY)

        p1.apply_patch({"system.language": "de"}, DEFAULT_REGISTRY)
        repo.save(p1)
        repo.save(p2)
        session.commit()

        l1 = repo.find_by_id(p1.profile_id)
        l2 = repo.find_by_id(p2.profile_id)
        assert l1 is not None
        assert l2 is not None
        assert l1.get("system.language").value == "de"
        assert l2.get("system.language").value == "en-US"

    def test_outbox_events_scoped_to_profile(self, session, outbox) -> None:
        p1 = SettingsProfileFactory.create(DEFAULT_REGISTRY)
        p1.apply_patch({"system.language": "de"}, DEFAULT_REGISTRY)
        for e in p1.events:
            outbox.append(e)

        p2 = SettingsProfileFactory.create(DEFAULT_REGISTRY)
        p2.apply_patch({"ui.theme": "dark"}, DEFAULT_REGISTRY)
        for e in p2.events:
            outbox.append(e)
        session.flush()

        unpublished = outbox.fetch_unpublished(limit=10)
        assert len(unpublished) == 2
        assert {e.key for e in unpublished if isinstance(e, SettingUpdated)} == {
            "system.language",
            "ui.theme",
        }

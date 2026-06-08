from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.settings.application.ports.repository import (
    SettingsRepositoryPort,
)
from backend.settings.application.ports.outbox import (
    SettingsDomainEvent,
    SettingsOutboxPort,
)
from backend.settings.application.ports.clock import SettingsClockPort
from backend.settings.application.use_cases.dto import (
    GetSettingByKeyRequest,
    GetSettingsRequest,
    GetSettingsResponse,
    PatchSettingsRequest,
    PatchSettingsResponse,
    ResetSettingsRequest,
    ResetSettingsResponse,
    SettingResponse,
)
from backend.settings.application.use_cases.exceptions import (
    SettingNotFoundError,
    SettingsProfileNotFoundError,
)
from backend.settings.application.use_cases.get_settings import (
    GetSettingsUseCase,
)
from backend.settings.application.use_cases.get_setting_by_key import (
    GetSettingByKeyUseCase,
)
from backend.settings.application.use_cases.patch_settings import (
    PatchSettingsUseCase,
)
from backend.settings.application.use_cases.reset_settings import (
    ResetSettingsUseCase,
)
from backend.settings.domain.factory import SettingsProfileFactory
from backend.settings.domain.model import (
    Setting,
    SettingCategory,
    SettingDefinition,
    SettingId,
    SettingScope,
    SettingsProfile,
    SettingsReset,
    SettingUpdated,
)


# ===================================================================
# Fakes
# ===================================================================


class FakeSettingsRepo:
    """Minimal fake conforming to SettingsRepositoryPort."""

    def __init__(self) -> None:
        self._profiles: dict[str, SettingsProfile] = {}
        self._all_settings: dict[str, Setting] = {}

    def save(self, profile: SettingsProfile) -> None:
        pid = str(profile.profile_id)
        self._profiles[pid] = profile
        s_copy = profile.settings
        for key, setting in s_copy.items():
            self._all_settings[f"{pid}:{key}"] = setting

    def find_by_id(self, profile_id: SettingId) -> SettingsProfile | None:
        return self._profiles.get(str(profile_id))

    def find_by_key(self, key: str) -> Setting | None:
        for setting in self._all_settings.values():
            if setting.key == key:
                return setting
        return None

    def get_all(self) -> list[Setting]:
        return list(self._all_settings.values())


class FakeSettingsOutbox:
    """Minimal fake conforming to SettingsOutboxPort."""

    def __init__(self) -> None:
        self.events: list[SettingsDomainEvent] = []

    def append(self, event: SettingsDomainEvent) -> None:
        self.events.append(event)

    def fetch_unpublished(self, limit: int = 50) -> list[SettingsDomainEvent]:
        return list(self.events)

    def mark_published(self, event_id: str) -> None:
        pass


class FixedClock:
    """Returns a fixed UTC datetime."""

    def __init__(self, dt: datetime | None = None) -> None:
        self._dt = dt or datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._dt


# ===================================================================
# Test registry
# ===================================================================

TEST_REGISTRY: dict[str, SettingDefinition] = {
    "ui.theme": SettingDefinition(
        key="ui.theme",
        category=SettingCategory.UI,
        scope=SettingScope.USER,
        value_type="str",
        default_value="system",
        allowed_values=("light", "dark", "system"),
    ),
    "ui.reduced_motion": SettingDefinition(
        key="ui.reduced_motion",
        category=SettingCategory.UI,
        scope=SettingScope.USER,
        value_type="bool",
        default_value=False,
    ),
    "voice.wake_word_enabled": SettingDefinition(
        key="voice.wake_word_enabled",
        category=SettingCategory.VOICE,
        scope=SettingScope.USER,
        value_type="bool",
        default_value=True,
    ),
    "voice.input_device": SettingDefinition(
        key="voice.input_device",
        category=SettingCategory.VOICE,
        scope=SettingScope.USER,
        value_type="str",
        default_value="default",
    ),
    "system.language": SettingDefinition(
        key="system.language",
        category=SettingCategory.SYSTEM,
        scope=SettingScope.USER,
        value_type="str",
        default_value="en-US",
    ),
}

SETTING_COUNT = len(TEST_REGISTRY)


# ===================================================================
# GetSettingsUseCase
# ===================================================================


class TestGetSettingsUseCase:
    @pytest.fixture
    def repo(self) -> FakeSettingsRepo:
        r = FakeSettingsRepo()
        profile = SettingsProfileFactory.create(TEST_REGISTRY)
        r.save(profile)
        return r

    @pytest.fixture
    def use_case(self, repo: FakeSettingsRepo) -> GetSettingsUseCase:
        return GetSettingsUseCase(repo)

    def test_returns_all_settings(self, use_case: GetSettingsUseCase) -> None:
        response = use_case.execute(GetSettingsRequest())
        assert isinstance(response, GetSettingsResponse)
        assert response.total == SETTING_COUNT
        assert len(response.settings) == SETTING_COUNT

    def test_each_setting_has_expected_fields(
        self, use_case: GetSettingsUseCase
    ) -> None:
        response = use_case.execute(GetSettingsRequest())
        s = response.settings[0]
        assert isinstance(s, SettingResponse)
        assert s.key
        assert isinstance(s.category, str)
        assert isinstance(s.scope, str)
        assert isinstance(s.version, int)

    def test_filter_by_category(
        self, use_case: GetSettingsUseCase
    ) -> None:
        response = use_case.execute(
            GetSettingsRequest(category="ui")
        )
        assert response.total == 2
        assert all(s.category == "ui" for s in response.settings)

    def test_filter_voice_category(
        self, use_case: GetSettingsUseCase
    ) -> None:
        response = use_case.execute(
            GetSettingsRequest(category="voice")
        )
        assert response.total == 2

    def test_filter_system_category(
        self, use_case: GetSettingsUseCase
    ) -> None:
        response = use_case.execute(
            GetSettingsRequest(category="system")
        )
        assert response.total == 1

    def test_filter_nonexistent_category(
        self, use_case: GetSettingsUseCase
    ) -> None:
        response = use_case.execute(
            GetSettingsRequest(category="privacy")
        )
        assert response.total == 0
        assert response.settings == []

    def test_empty_repo(self) -> None:
        use_case = GetSettingsUseCase(FakeSettingsRepo())
        response = use_case.execute(GetSettingsRequest())
        assert response.total == 0
        assert response.settings == []

    def test_response_is_dataclass(self, use_case: GetSettingsUseCase) -> None:
        response = use_case.execute(GetSettingsRequest())
        assert isinstance(response, GetSettingsResponse)

    def test_settings_contain_correct_values(
        self, use_case: GetSettingsUseCase
    ) -> None:
        response = use_case.execute(GetSettingsRequest())
        theme = next(s for s in response.settings if s.key == "ui.theme")
        assert theme.value == "system"
        assert theme.category == "ui"
        assert theme.scope == "user"


# ===================================================================
# GetSettingByKeyUseCase
# ===================================================================


class TestGetSettingByKeyUseCase:
    @pytest.fixture
    def repo(self) -> FakeSettingsRepo:
        r = FakeSettingsRepo()
        profile = SettingsProfileFactory.create(TEST_REGISTRY)
        r.save(profile)
        return r

    @pytest.fixture
    def use_case(
        self, repo: FakeSettingsRepo
    ) -> GetSettingByKeyUseCase:
        return GetSettingByKeyUseCase(repo)

    def test_returns_setting(self, use_case: GetSettingByKeyUseCase) -> None:
        response = use_case.execute(GetSettingByKeyRequest(key="ui.theme"))
        assert isinstance(response, SettingResponse)
        assert response.key == "ui.theme"
        assert response.value == "system"

    def test_returns_bool_setting(
        self, use_case: GetSettingByKeyUseCase
    ) -> None:
        response = use_case.execute(
            GetSettingByKeyRequest(key="voice.wake_word_enabled")
        )
        assert response.value is True

    def test_raises_not_found(
        self, use_case: GetSettingByKeyUseCase
    ) -> None:
        with pytest.raises(SettingNotFoundError) as exc:
            use_case.execute(
                GetSettingByKeyRequest(key="nonexistent.key")
            )
        assert exc.value.key == "nonexistent.key"

    def test_returns_version(
        self, use_case: GetSettingByKeyUseCase
    ) -> None:
        response = use_case.execute(
            GetSettingByKeyRequest(key="system.language")
        )
        assert isinstance(response.version, int)
        assert response.version >= 1

    def test_returns_category_and_scope(
        self, use_case: GetSettingByKeyUseCase
    ) -> None:
        response = use_case.execute(
            GetSettingByKeyRequest(key="system.language")
        )
        assert response.category == "system"
        assert response.scope == "user"

    def test_empty_repo_raises(self) -> None:
        use_case = GetSettingByKeyUseCase(FakeSettingsRepo())
        with pytest.raises(SettingNotFoundError):
            use_case.execute(GetSettingByKeyRequest(key="ui.theme"))

    def test_string_value(self, use_case: GetSettingByKeyUseCase) -> None:
        response = use_case.execute(
            GetSettingByKeyRequest(key="voice.input_device")
        )
        assert isinstance(response.value, str)
        assert response.value == "default"


# ===================================================================
# PatchSettingsUseCase
# ===================================================================


class TestPatchSettingsUseCase:
    @pytest.fixture
    def repo(self) -> FakeSettingsRepo:
        return FakeSettingsRepo()

    @pytest.fixture
    def outbox(self) -> FakeSettingsOutbox:
        return FakeSettingsOutbox()

    @pytest.fixture
    def clock(self) -> FixedClock:
        return FixedClock()

    @pytest.fixture
    def use_case(
        self, repo: FakeSettingsRepo, outbox: FakeSettingsOutbox,
        clock: FixedClock,
    ) -> PatchSettingsUseCase:
        return PatchSettingsUseCase(repo, outbox, clock, TEST_REGISTRY)

    def test_updates_setting(self, use_case: PatchSettingsUseCase) -> None:
        response = use_case.execute(
            PatchSettingsRequest(updates={"ui.theme": "dark"})
        )
        assert isinstance(response, PatchSettingsResponse)
        assert response.updated_count == 1

    def test_updated_setting_response(
        self, use_case: PatchSettingsUseCase
    ) -> None:
        response = use_case.execute(
            PatchSettingsRequest(updates={"ui.theme": "dark"})
        )
        s = response.updated_settings[0]
        assert s.key == "ui.theme"
        assert s.value == "dark"
        assert s.category == "ui"

    def test_multiple_updates(
        self, use_case: PatchSettingsUseCase
    ) -> None:
        response = use_case.execute(
            PatchSettingsRequest(
                updates={"ui.theme": "dark", "voice.wake_word_enabled": False}
            )
        )
        assert response.updated_count == 2
        keys = {s.key for s in response.updated_settings}
        assert keys == {"ui.theme", "voice.wake_word_enabled"}

    def test_unknown_key_raises(
        self, use_case: PatchSettingsUseCase
    ) -> None:
        with pytest.raises(Exception):
            use_case.execute(
                PatchSettingsRequest(updates={"unknown.key": "val"})
            )

    def test_wrong_type_raises(
        self, use_case: PatchSettingsUseCase
    ) -> None:
        with pytest.raises(Exception):
            use_case.execute(
                PatchSettingsRequest(
                    updates={"voice.wake_word_enabled": "not-a-bool"}
                )
            )

    def test_emits_setting_updated_event(
        self, use_case: PatchSettingsUseCase, outbox: FakeSettingsOutbox
    ) -> None:
        use_case.execute(
            PatchSettingsRequest(updates={"ui.theme": "dark"})
        )
        assert len(outbox.events) == 1
        event = outbox.events[0]
        assert isinstance(event, SettingUpdated)
        assert event.key == "ui.theme"
        assert event.new_value == "dark"

    def test_emits_multiple_events(
        self, use_case: PatchSettingsUseCase, outbox: FakeSettingsOutbox
    ) -> None:
        use_case.execute(
            PatchSettingsRequest(
                updates={"ui.theme": "dark", "voice.wake_word_enabled": False}
            )
        )
        assert len(outbox.events) == 2

    def test_profile_persisted(
        self, use_case: PatchSettingsUseCase
    ) -> None:
        use_case.execute(
            PatchSettingsRequest(updates={"ui.theme": "dark"})
        )
        setting = use_case._repo.find_by_key("ui.theme")
        assert setting is not None
        assert setting.value == "dark"

    def test_profile_version_in_response(
        self, use_case: PatchSettingsUseCase
    ) -> None:
        response = use_case.execute(
            PatchSettingsRequest(updates={"ui.theme": "dark"})
        )
        assert response.profile_version == "1.0"

    def test_existing_profile_with_id(
        self, use_case: PatchSettingsUseCase
    ) -> None:
        profile = SettingsProfileFactory.create(TEST_REGISTRY)
        use_case._repo.save(profile)
        pid = str(profile.profile_id)

        response = use_case.execute(
            PatchSettingsRequest(
                updates={"ui.theme": "dark"}, profile_id=pid
            )
        )
        assert response.updated_count == 1

    def test_profile_id_not_found_raises(
        self, use_case: PatchSettingsUseCase
    ) -> None:
        with pytest.raises(SettingsProfileNotFoundError):
            use_case.execute(
                PatchSettingsRequest(
                    updates={"ui.theme": "dark"},
                    profile_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
                )
            )

    def test_safety_floor_violation_raises(
        self, use_case: PatchSettingsUseCase
    ) -> None:
        reg = dict(TEST_REGISTRY)
        reg["system.auto_start"] = SettingDefinition(
            key="system.auto_start",
            category=SettingCategory.SYSTEM,
            scope=SettingScope.USER,
            value_type="bool",
            default_value=True,
            safety_floor=True,
        )
        uc = PatchSettingsUseCase(
            use_case._repo, use_case._outbox, use_case._clock, reg
        )
        with pytest.raises(Exception):
            uc.execute(
                PatchSettingsRequest(updates={"system.auto_start": False})
            )

    def test_version_increments_on_update(
        self, use_case: PatchSettingsUseCase
    ) -> None:
        use_case.execute(
            PatchSettingsRequest(updates={"ui.theme": "dark"})
        )
        setting = use_case._repo.find_by_key("ui.theme")
        assert setting is not None
        assert setting.version == 2

    def test_version_increments_twice(
        self, use_case: PatchSettingsUseCase
    ) -> None:
        profile = SettingsProfileFactory.create(TEST_REGISTRY)
        use_case._repo.save(profile)
        pid = str(profile.profile_id)

        use_case.execute(
            PatchSettingsRequest(
                updates={"ui.theme": "dark"}, profile_id=pid
            )
        )
        use_case.execute(
            PatchSettingsRequest(
                updates={"ui.theme": "light"}, profile_id=pid
            )
        )
        setting = use_case._repo.find_by_key("ui.theme")
        assert setting is not None
        assert setting.version == 3

    def test_multiple_updates_does_not_duplicate_profile(
        self, use_case: PatchSettingsUseCase
    ) -> None:
        profile = SettingsProfileFactory.create(TEST_REGISTRY)
        use_case._repo.save(profile)
        pid = str(profile.profile_id)

        use_case.execute(
            PatchSettingsRequest(
                updates={"ui.theme": "dark"}, profile_id=pid
            )
        )
        use_case.execute(
            PatchSettingsRequest(
                updates={"ui.theme": "light"}, profile_id=pid
            )
        )
        all_s = use_case._repo.get_all()
        themes = [s for s in all_s if s.key == "ui.theme"]
        assert len(themes) == 1


# ===================================================================
# ResetSettingsUseCase
# ===================================================================


class TestResetSettingsUseCase:
    @pytest.fixture
    def repo(self) -> FakeSettingsRepo:
        return FakeSettingsRepo()

    @pytest.fixture
    def outbox(self) -> FakeSettingsOutbox:
        return FakeSettingsOutbox()

    @pytest.fixture
    def clock(self) -> FixedClock:
        return FixedClock()

    @pytest.fixture
    def patch_use_case(
        self, repo: FakeSettingsRepo, outbox: FakeSettingsOutbox,
        clock: FixedClock,
    ) -> PatchSettingsUseCase:
        return PatchSettingsUseCase(repo, outbox, clock, TEST_REGISTRY)

    @pytest.fixture
    def use_case(
        self, repo: FakeSettingsRepo, outbox: FakeSettingsOutbox,
        clock: FixedClock,
    ) -> ResetSettingsUseCase:
        return ResetSettingsUseCase(repo, outbox, clock, TEST_REGISTRY)

    def test_reset_all(
        self, use_case: ResetSettingsUseCase
    ) -> None:
        response = use_case.execute(ResetSettingsRequest())
        assert isinstance(response, ResetSettingsResponse)
        assert response.reset_count == SETTING_COUNT

    def test_reset_persists_defaults(
        self, use_case: ResetSettingsUseCase, repo: FakeSettingsRepo
    ) -> None:
        profile = SettingsProfileFactory.create(TEST_REGISTRY)
        repo.save(profile)
        pid = str(profile.profile_id)

        patch_uc = PatchSettingsUseCase(
            repo, FakeSettingsOutbox(), FixedClock(), TEST_REGISTRY
        )
        patch_uc.execute(
            PatchSettingsRequest(
                updates={"ui.theme": "dark"}, profile_id=pid
            )
        )

        use_case._repo = repo
        use_case.execute(ResetSettingsRequest(profile_id=pid))
        setting = repo.find_by_key("ui.theme")
        assert setting is not None
        assert setting.value == "system"

    def test_reset_emits_settings_reset_event(
        self, use_case: ResetSettingsUseCase, outbox: FakeSettingsOutbox
    ) -> None:
        repo = use_case._repo
        profile = SettingsProfileFactory.create(TEST_REGISTRY)
        repo.save(profile)
        pid = str(profile.profile_id)

        patch_uc = PatchSettingsUseCase(
            repo, FakeSettingsOutbox(), FixedClock(), TEST_REGISTRY
        )
        patch_uc.execute(
            PatchSettingsRequest(
                updates={"ui.theme": "dark"}, profile_id=pid
            )
        )

        use_case.execute(ResetSettingsRequest(profile_id=pid))
        assert len(outbox.events) >= 1
        reset_events = [
            e for e in outbox.events if isinstance(e, SettingsReset)
        ]
        assert len(reset_events) >= 1

    def test_reset_profile_version(
        self, use_case: ResetSettingsUseCase
    ) -> None:
        response = use_case.execute(ResetSettingsRequest())
        assert response.profile_version == "1.0"

    def test_reset_category(
        self, use_case: ResetSettingsUseCase
    ) -> None:
        response = use_case.execute(
            ResetSettingsRequest(category="ui")
        )
        assert response.reset_count == SETTING_COUNT

    def test_reset_category_ui(
        self, use_case: ResetSettingsUseCase, repo: FakeSettingsRepo
    ) -> None:
        profile = SettingsProfileFactory.create(TEST_REGISTRY)
        repo.save(profile)
        pid = str(profile.profile_id)

        patch_uc = PatchSettingsUseCase(
            repo, FakeSettingsOutbox(), FixedClock(), TEST_REGISTRY
        )
        patch_uc.execute(
            PatchSettingsRequest(
                updates={"ui.theme": "dark"}, profile_id=pid
            )
        )

        use_case._repo = repo
        use_case.execute(ResetSettingsRequest(category="ui", profile_id=pid))
        theme = repo.find_by_key("ui.theme")
        assert theme is not None
        assert theme.value == "system"

    def test_reset_voice_does_not_affect_ui(
        self, use_case: ResetSettingsUseCase, repo: FakeSettingsRepo
    ) -> None:
        profile = SettingsProfileFactory.create(TEST_REGISTRY)
        repo.save(profile)
        pid = str(profile.profile_id)

        patch_uc = PatchSettingsUseCase(
            repo, FakeSettingsOutbox(), FixedClock(), TEST_REGISTRY
        )
        patch_uc.execute(
            PatchSettingsRequest(
                updates={"ui.theme": "dark", "voice.input_device": "headset"},
                profile_id=pid,
            )
        )

        use_case._repo = repo
        use_case.execute(ResetSettingsRequest(category="voice", profile_id=pid))
        theme = repo.find_by_key("ui.theme")
        assert theme is not None
        assert theme.value == "dark"

    def test_nonexistent_profile_id_raises(
        self, use_case: ResetSettingsUseCase
    ) -> None:
        with pytest.raises(SettingsProfileNotFoundError):
            use_case.execute(
                ResetSettingsRequest(
                    profile_id="01975c2f-4aef-7cf1-a940-ae54bf596280"
                )
            )

    def test_reset_with_profile_id(
        self, use_case: ResetSettingsUseCase
    ) -> None:
        profile = SettingsProfileFactory.create(TEST_REGISTRY)
        use_case._repo.save(profile)
        pid = str(profile.profile_id)
        response = use_case.execute(
            ResetSettingsRequest(profile_id=pid)
        )
        assert response.reset_count == SETTING_COUNT


# ===================================================================
# DTO integrity tests
# ===================================================================


class TestDTOIntegrity:
    def test_get_settings_request_defaults(self) -> None:
        req = GetSettingsRequest()
        assert req.category is None

    def test_get_settings_request_with_category(self) -> None:
        req = GetSettingsRequest(category="ui")
        assert req.category == "ui"

    def test_get_setting_by_key_request(self) -> None:
        req = GetSettingByKeyRequest(key="ui.theme")
        assert req.key == "ui.theme"

    def test_patch_settings_request_defaults(self) -> None:
        req = PatchSettingsRequest(updates={"k": "v"})
        assert req.updates == {"k": "v"}
        assert req.profile_id is None

    def test_patch_settings_request_with_profile(self) -> None:
        req = PatchSettingsRequest(
            updates={"k": "v"}, profile_id="prof-001"
        )
        assert req.profile_id == "prof-001"

    def test_reset_settings_request_defaults(self) -> None:
        req = ResetSettingsRequest()
        assert req.category is None
        assert req.profile_id is None

    def test_reset_settings_request_with_all(self) -> None:
        req = ResetSettingsRequest(category="ui", profile_id="prof-001")
        assert req.category == "ui"
        assert req.profile_id == "prof-001"

    def test_setting_response(self) -> None:
        s = SettingResponse(
            key="k", value="v", category="c", scope="s", version=1
        )
        assert s.key == "k"
        assert s.value == "v"
        assert s.category == "c"
        assert s.scope == "s"
        assert s.version == 1

    def test_get_settings_response_defaults(self) -> None:
        r = GetSettingsResponse()
        assert r.settings == []
        assert r.total == 0

    def test_patch_settings_response_defaults(self) -> None:
        r = PatchSettingsResponse()
        assert r.updated_settings == []
        assert r.updated_count == 0
        assert r.profile_version == ""

    def test_reset_settings_response_defaults(self) -> None:
        r = ResetSettingsResponse()
        assert r.reset_count == 0
        assert r.profile_version == ""


# ===================================================================
# Exception tests
# ===================================================================


class TestExceptions:
    def test_setting_not_found_str(self) -> None:
        exc = SettingNotFoundError("ui.theme")
        assert str(exc) == "Setting not found: ui.theme"
        assert exc.key == "ui.theme"

    def test_settings_profile_not_found_str(self) -> None:
        exc = SettingsProfileNotFoundError("prof-001")
        assert str(exc) == "Settings profile not found: prof-001"
        assert exc.profile_id == "prof-001"

    def test_setting_not_found_is_use_case_error(self) -> None:
        from backend.settings.application.use_cases.exceptions import (
            UseCaseError,
        )
        assert issubclass(SettingNotFoundError, UseCaseError)

    def test_settings_profile_not_found_is_use_case_error(self) -> None:
        from backend.settings.application.use_cases.exceptions import (
            UseCaseError,
        )
        assert issubclass(SettingsProfileNotFoundError, UseCaseError)

from __future__ import annotations

from uuid import UUID

import pytest

from backend.settings.domain.exceptions import (
    InvalidSettingCategoryError,
    InvalidSettingKeyError,
    InvalidSettingScopeError,
    ReservedSettingKeyError,
    SafetyFloorViolationError,
    SettingAllowedValuesError,
    SettingBoundsError,
    SettingMaxLengthError,
    SettingTypeMismatchError,
    UnknownSettingKeyError,
)
from backend.settings.domain.factory import SettingsProfileFactory
from backend.settings.domain.model import (
    Setting,
    SettingCategory,
    SettingDefinition,
    SettingId,
    SettingScope,
    SettingsProfile,
    Version,
)
from backend.settings.domain.rules import (
    assert_category_valid,
    assert_key_format,
    assert_key_known,
    assert_key_not_reserved,
    assert_safety_floor,
    assert_scope_valid,
    assert_value_in_allowed,
    assert_value_in_bounds,
    assert_value_not_exceeds_max_length,
    assert_value_type,
    assert_version_valid,
    validate_setting_value,
)


# =========================================================================
# Value objects
# =========================================================================


class TestSettingId:
    def test_generates_uuid(self) -> None:
        sid = SettingId()
        assert isinstance(sid.value, UUID)

    def test_unique(self) -> None:
        ids = {SettingId() for _ in range(100)}
        assert len(ids) == 100

    def test_string_representation(self) -> None:
        sid = SettingId()
        assert str(sid) == str(sid.value)

    def test_from_value(self) -> None:
        uid = UUID("00000000-0000-0000-0000-000000000001")
        sid = SettingId(value=uid)
        assert sid.value == uid


class TestVersion:
    def test_valid_version(self) -> None:
        v = Version(major=1, minor=0)
        assert v.major == 1
        assert v.minor == 0

    def test_negative_major_raises(self) -> None:
        with pytest.raises(ValueError):
            Version(major=-1, minor=0)

    def test_negative_minor_raises(self) -> None:
        with pytest.raises(ValueError):
            Version(major=1, minor=-1)

    def test_string_representation(self) -> None:
        assert str(Version(2, 3)) == "2.3"

    def test_current(self) -> None:
        assert Version.current() == Version(1, 0)

    def test_equality(self) -> None:
        assert Version(1, 0) == Version(1, 0)
        assert Version(1, 0) != Version(1, 1)


class TestSettingCategory:
    def test_all_categories_present(self) -> None:
        expected = {"system", "privacy", "voice", "notification", "model", "ui"}
        actual = {c.value for c in SettingCategory}
        assert actual == expected

    def test_category_is_string_enum(self) -> None:
        assert SettingCategory.SYSTEM.value == "system"
        assert SettingCategory.UI.value == "ui"


class TestSettingScope:
    def test_all_scopes_present(self) -> None:
        expected = {"user", "system", "service"}
        actual = {s.value for s in SettingScope}
        assert actual == expected


class TestSettingDefinition:
    def test_minimal_definition(self) -> None:
        d = SettingDefinition(
            key="test.key",
            category=SettingCategory.SYSTEM,
            scope=SettingScope.USER,
            value_type="bool",
            default_value=True,
        )
        assert d.key == "test.key"
        assert d.default_value is True
        assert d.safety_floor is False
        assert d.reserved is False

    def test_full_definition(self) -> None:
        d = SettingDefinition(
            key="test.full",
            category=SettingCategory.VOICE,
            scope=SettingScope.USER,
            value_type="int",
            default_value=50,
            min_value=0,
            max_value=100,
            description="Volume level",
            safety_floor=True,
            reserved=False,
        )
        assert d.description == "Volume level"
        assert d.min_value == 0
        assert d.max_value == 100


class TestSetting:
    def test_creation(self) -> None:
        s = Setting(
            key="voice.volume",
            value=75,
            category=SettingCategory.VOICE,
            scope=SettingScope.USER,
        )
        assert s.key == "voice.volume"
        assert s.value == 75
        assert s.category == SettingCategory.VOICE
        assert s.scope == SettingScope.USER
        assert s.version == 1

    def test_version_increment(self) -> None:
        s = Setting(
            key="test.key",
            value=1,
            category=SettingCategory.SYSTEM,
            scope=SettingScope.USER,
            version=5,
        )
        assert s.version == 5


# =========================================================================
# Domain rules - Key validation
# =========================================================================


class TestKeyValidation:
    def test_valid_key(self) -> None:
        assert_key_format("voice.wake_word_enabled")
        assert_key_format("privacy.history_retention_days")
        assert_key_format("a")
        assert_key_format("a.b.c")

    def test_empty_key_raises(self) -> None:
        with pytest.raises(InvalidSettingKeyError):
            assert_key_format("")

    def test_key_starting_with_dot_raises(self) -> None:
        with pytest.raises(InvalidSettingKeyError):
            assert_key_format(".invalid")

    def test_key_ending_with_dot_raises(self) -> None:
        with pytest.raises(InvalidSettingKeyError):
            assert_key_format("invalid.")

    def test_key_with_uppercase_raises(self) -> None:
        with pytest.raises(InvalidSettingKeyError):
            assert_key_format("Voice.Volume")

    def test_key_with_spaces_raises(self) -> None:
        with pytest.raises(InvalidSettingKeyError):
            assert_key_format("voice. volume")

    def test_key_with_special_chars_raises(self) -> None:
        with pytest.raises(InvalidSettingKeyError):
            assert_key_format("voice@volume")

    def test_key_starting_with_number_raises(self) -> None:
        with pytest.raises(InvalidSettingKeyError):
            assert_key_format("1voice")

    def test_deeply_nested_key(self) -> None:
        assert_key_format("a.b.c.d.e.f")


class TestKeyKnown:
    def test_key_in_registry(self) -> None:
        registry = {
            "voice.volume": SettingDefinition(
                key="voice.volume",
                category=SettingCategory.VOICE,
                scope=SettingScope.USER,
                value_type="int",
                default_value=50,
            )
        }
        assert_key_known("voice.volume", registry)

    def test_key_not_in_registry_raises(self) -> None:
        registry: dict[str, SettingDefinition] = {}
        with pytest.raises(UnknownSettingKeyError):
            assert_key_known("unknown.key", registry)


class TestKeyNotReserved:
    def test_non_reserved_allowed(self) -> None:
        d = SettingDefinition(
            key="user.key",
            category=SettingCategory.UI,
            scope=SettingScope.USER,
            value_type="bool",
            default_value=False,
            reserved=False,
        )
        assert_key_not_reserved(d)

    def test_reserved_raises(self) -> None:
        d = SettingDefinition(
            key="reserved.key",
            category=SettingCategory.SYSTEM,
            scope=SettingScope.SYSTEM,
            value_type="bool",
            default_value=True,
            reserved=True,
        )
        with pytest.raises(ReservedSettingKeyError):
            assert_key_not_reserved(d)


# =========================================================================
# Domain rules - Category and scope
# =========================================================================


class TestCategoryValidation:
    def test_valid_categories(self) -> None:
        for c in SettingCategory:
            assert_category_valid(c.value)

    def test_invalid_category_raises(self) -> None:
        with pytest.raises(InvalidSettingCategoryError):
            assert_category_valid("invalid")


class TestScopeValidation:
    def test_valid_scopes(self) -> None:
        for s in SettingScope:
            assert_scope_valid(s.value)

    def test_invalid_scope_raises(self) -> None:
        with pytest.raises(InvalidSettingScopeError):
            assert_scope_valid("invalid")


class TestVersionValidation:
    def test_valid_version(self) -> None:
        assert_version_valid(Version(1, 0))

    def test_negative_major_raises(self) -> None:
        with pytest.raises(ValueError, match="must be >= 0"):
            Version(-1, 0)


# =========================================================================
# Domain rules - Value validation
# =========================================================================


class TestValueTypeValidation:
    def test_bool_accepts_bool(self) -> None:
        assert_value_type("test.key", True, "bool")
        assert_value_type("test.key", False, "bool")

    def test_bool_rejects_int(self) -> None:
        with pytest.raises(SettingTypeMismatchError):
            assert_value_type("test.key", 1, "bool")

    def test_bool_rejects_str(self) -> None:
        with pytest.raises(SettingTypeMismatchError):
            assert_value_type("test.key", "true", "bool")

    def test_int_accepts_int(self) -> None:
        assert_value_type("test.key", 42, "int")

    def test_int_rejects_float(self) -> None:
        with pytest.raises(SettingTypeMismatchError):
            assert_value_type("test.key", 42.0, "int")

    def test_float_accepts_float(self) -> None:
        assert_value_type("test.key", 3.14, "float")

    def test_float_accepts_int(self) -> None:
        assert_value_type("test.key", 42, "float")

    def test_str_accepts_str(self) -> None:
        assert_value_type("test.key", "hello", "str")

    def test_str_rejects_int(self) -> None:
        with pytest.raises(SettingTypeMismatchError):
            assert_value_type("test.key", 42, "str")

    def test_list_accepts_list(self) -> None:
        assert_value_type("test.key", [1, 2, 3], "list")

    def test_dict_accepts_dict(self) -> None:
        assert_value_type("test.key", {"a": 1}, "dict")


class TestValueMaxLength:
    def test_within_bounds(self) -> None:
        assert_value_not_exceeds_max_length("key", "hello", 10)

    def test_exactly_at_limit(self) -> None:
        assert_value_not_exceeds_max_length("key", "12345", 5)

    def test_exceeds_raises(self) -> None:
        with pytest.raises(SettingMaxLengthError):
            assert_value_not_exceeds_max_length("key", "hello", 3)

    def test_no_limit_set(self) -> None:
        assert_value_not_exceeds_max_length("key", "any length", None)


class TestValueBounds:
    def test_within_bounds(self) -> None:
        assert_value_in_bounds("key", 50, 0, 100)

    def test_at_minimum(self) -> None:
        assert_value_in_bounds("key", 0, 0, 100)

    def test_at_maximum(self) -> None:
        assert_value_in_bounds("key", 100, 0, 100)

    def test_below_min_raises(self) -> None:
        with pytest.raises(SettingBoundsError):
            assert_value_in_bounds("key", -1, 0, 100)

    def test_above_max_raises(self) -> None:
        with pytest.raises(SettingBoundsError):
            assert_value_in_bounds("key", 101, 0, 100)

    def test_no_bounds_set_float(self) -> None:
        assert_value_in_bounds("key", 999.0, None, None)


class TestValueAllowed:
    def test_value_in_allowed(self) -> None:
        assert_value_in_allowed("key", "en", ("en", "fr", "de"))

    def test_value_not_in_allowed_raises(self) -> None:
        with pytest.raises(SettingAllowedValuesError):
            assert_value_in_allowed("key", "es", ("en", "fr", "de"))

    def test_no_allowed_list(self) -> None:
        assert_value_in_allowed("key", "anything", None)


class TestSafetyFloor:
    def test_non_safety_floor_allows_any(self) -> None:
        d = SettingDefinition(
            key="test.key",
            category=SettingCategory.UI,
            scope=SettingScope.USER,
            value_type="int",
            default_value=50,
            safety_floor=False,
        )
        assert_safety_floor("test.key", 0, d)

    def test_safety_floor_min_value(self) -> None:
        d = SettingDefinition(
            key="test.key",
            category=SettingCategory.PRIVACY,
            scope=SettingScope.USER,
            value_type="int",
            default_value=30,
            min_value=7,
            safety_floor=True,
        )
        assert_safety_floor("test.key", 7, d)

    def test_safety_floor_below_min_raises(self) -> None:
        d = SettingDefinition(
            key="test.key",
            category=SettingCategory.PRIVACY,
            scope=SettingScope.USER,
            value_type="int",
            default_value=30,
            min_value=7,
            safety_floor=True,
        )
        with pytest.raises(SafetyFloorViolationError):
            assert_safety_floor("test.key", 3, d)

    def test_safety_floor_bool_default_true_cannot_be_false(self) -> None:
        d = SettingDefinition(
            key="test.bool_safety",
            category=SettingCategory.PRIVACY,
            scope=SettingScope.USER,
            value_type="bool",
            default_value=True,
            safety_floor=True,
        )
        with pytest.raises(SafetyFloorViolationError):
            assert_safety_floor("test.bool_safety", False, d)

    def test_safety_floor_bool_default_false_allows_false(self) -> None:
        d = SettingDefinition(
            key="test.bool_safe",
            category=SettingCategory.UI,
            scope=SettingScope.USER,
            value_type="bool",
            default_value=False,
            safety_floor=True,
        )
        assert_safety_floor("test.bool_safe", False, d)


# =========================================================================
# Combined value validation
# =========================================================================


class TestValidateSettingValue:
    def test_valid_values_pass(self) -> None:
        d = SettingDefinition(
            key="test.int_val",
            category=SettingCategory.SYSTEM,
            scope=SettingScope.USER,
            value_type="int",
            default_value=50,
            min_value=0,
            max_value=100,
        )
        validate_setting_value("test.int_val", 50, d)

    def test_type_mismatch_raises(self) -> None:
        d = SettingDefinition(
            key="test.bool_val",
            category=SettingCategory.UI,
            scope=SettingScope.USER,
            value_type="bool",
            default_value=False,
        )
        with pytest.raises(SettingTypeMismatchError):
            validate_setting_value("test.bool_val", "yes", d)

    def test_bounds_violation_raises(self) -> None:
        d = SettingDefinition(
            key="test.range",
            category=SettingCategory.SYSTEM,
            scope=SettingScope.USER,
            value_type="int",
            default_value=50,
            min_value=0,
            max_value=100,
        )
        with pytest.raises(SettingBoundsError):
            validate_setting_value("test.range", 200, d)

    def test_max_length_violation_raises(self) -> None:
        d = SettingDefinition(
            key="test.name",
            category=SettingCategory.UI,
            scope=SettingScope.USER,
            value_type="str",
            default_value="default",
            max_length=10,
        )
        with pytest.raises(SettingMaxLengthError):
            validate_setting_value("test.name", "this is too long", d)

    def test_allowed_values_violation_raises(self) -> None:
        d = SettingDefinition(
            key="test.lang",
            category=SettingCategory.UI,
            scope=SettingScope.USER,
            value_type="str",
            default_value="en",
            allowed_values=("en", "fr", "de"),
        )
        with pytest.raises(SettingAllowedValuesError):
            validate_setting_value("test.lang", "es", d)

    def test_safety_floor_violation_raises(self) -> None:
        d = SettingDefinition(
            key="test.safe",
            category=SettingCategory.PRIVACY,
            scope=SettingScope.USER,
            value_type="int",
            default_value=30,
            min_value=7,
            safety_floor=True,
        )
        with pytest.raises(SafetyFloorViolationError):
            validate_setting_value("test.safe", 1, d)


# =========================================================================
# Registry / fixture helpers
# =========================================================================


@pytest.fixture
def sample_registry() -> dict[str, SettingDefinition]:
    return {
        "system.language": SettingDefinition(
            key="system.language",
            category=SettingCategory.SYSTEM,
            scope=SettingScope.USER,
            value_type="str",
            default_value="en",
            allowed_values=("en", "fr", "de", "es", "ja", "zh"),
            description="UI language",
        ),
        "privacy.history_retention_days": SettingDefinition(
            key="privacy.history_retention_days",
            category=SettingCategory.PRIVACY,
            scope=SettingScope.USER,
            value_type="int",
            default_value=30,
            min_value=7,
            max_value=365,
            safety_floor=True,
            description="Days to retain history (minimum 7)",
        ),
        "voice.wake_word_enabled": SettingDefinition(
            key="voice.wake_word_enabled",
            category=SettingCategory.VOICE,
            scope=SettingScope.USER,
            value_type="bool",
            default_value=True,
            description="Enable wake word detection",
        ),
        "notification.sounds_enabled": SettingDefinition(
            key="notification.sounds_enabled",
            category=SettingCategory.NOTIFICATION,
            scope=SettingScope.USER,
            value_type="bool",
            default_value=True,
            description="Play notification sounds",
        ),
        "model.temperature": SettingDefinition(
            key="model.temperature",
            category=SettingCategory.MODEL,
            scope=SettingScope.USER,
            value_type="float",
            default_value=0.7,
            min_value=0.0,
            max_value=2.0,
            description="LLM temperature",
        ),
        "ui.theme": SettingDefinition(
            key="ui.theme",
            category=SettingCategory.UI,
            scope=SettingScope.USER,
            value_type="str",
            default_value="system",
            allowed_values=("light", "dark", "system"),
            description="UI theme",
        ),
    }


# =========================================================================
# Factory
# =========================================================================


class TestSettingsProfileFactory:
    def test_create_profile_with_defaults(
        self,
        sample_registry: dict[str, SettingDefinition],
    ) -> None:
        profile = SettingsProfileFactory.create(sample_registry)
        assert isinstance(profile, SettingsProfile)
        assert isinstance(profile.profile_id, SettingId)
        assert profile.schema_version == Version(1, 0)
        assert profile.count() == 6

    def test_all_defaults_match_registry(
        self,
        sample_registry: dict[str, SettingDefinition],
    ) -> None:
        profile = SettingsProfileFactory.create(sample_registry)
        for key, definition in sample_registry.items():
            setting = profile.get(key)
            assert setting is not None, f"Missing setting: {key}"
            assert setting.value == definition.default_value
            assert setting.category == definition.category

    def test_create_with_custom_schema_version(
        self,
        sample_registry: dict[str, SettingDefinition],
    ) -> None:
        profile = SettingsProfileFactory.create(
            sample_registry, schema_version=Version(2, 1)
        )
        assert profile.schema_version == Version(2, 1)

    def test_empty_registry_creates_empty_profile(self) -> None:
        profile = SettingsProfileFactory.create({})
        assert profile.count() == 0

    def test_invalid_definition_key_raises(self) -> None:
        bad_registry = {
            "bad.key": SettingDefinition(
                key="Bad.Key",  # uppercase in key
                category=SettingCategory.UI,
                scope=SettingScope.USER,
                value_type="bool",
                default_value=True,
            )
        }
        with pytest.raises(InvalidSettingKeyError):
            SettingsProfileFactory.create(bad_registry)

    def test_invalid_category_raises(self) -> None:
        from backend.settings.domain.model import SettingCategory as SC

        bad_registry = {
            "bad.key": SettingDefinition(
                key="bad.key",
                category=SC.UI,
                scope=SettingScope.USER,
                value_type="bool",
                default_value=True,
            )
        }
        # category is valid (UI), so this should pass
        profile = SettingsProfileFactory.create(bad_registry)
        assert profile.count() == 1


# =========================================================================
# SettingsProfile aggregate
# =========================================================================


class TestSettingsProfile:
    def test_initial_state(self) -> None:
        profile = SettingsProfile(profile_id=SettingId())
        assert profile.count() == 0
        assert len(profile.events) == 0

    def test_create_with_settings(self) -> None:
        s = Setting(
            key="existing.key",
            value=True,
            category=SettingCategory.UI,
            scope=SettingScope.USER,
        )
        profile = SettingsProfile(
            profile_id=SettingId(),
            settings={"existing.key": s},
        )
        assert profile.count() == 1
        assert profile.get("existing.key") is not None

    def test_get_nonexistent_returns_none(self) -> None:
        profile = SettingsProfile(profile_id=SettingId())
        assert profile.get("nonexistent") is None

    def test_has_key(self) -> None:
        s = Setting(
            key="present",
            value=True,
            category=SettingCategory.UI,
            scope=SettingScope.USER,
        )
        profile = SettingsProfile(
            profile_id=SettingId(),
            settings={"present": s},
        )
        assert profile.has_key("present")
        assert not profile.has_key("absent")


class TestSettingsProfileApplySetting:
    def test_apply_new_setting(
        self,
        sample_registry: dict[str, SettingDefinition],
    ) -> None:
        profile = SettingsProfileFactory.create({})
        definition = sample_registry["ui.theme"]
        profile.apply_setting("ui.theme", "dark", definition)

        setting = profile.get("ui.theme")
        assert setting is not None
        assert setting.value == "dark"
        assert setting.version == 1

    def test_apply_updates_existing(
        self,
        sample_registry: dict[str, SettingDefinition],
    ) -> None:
        profile = SettingsProfileFactory.create(sample_registry)
        definition = sample_registry["ui.theme"]
        profile.apply_setting("ui.theme", "dark", definition)

        setting = profile.get("ui.theme")
        assert setting is not None
        assert setting.value == "dark"
        assert setting.version == 2  # incremented from default

    def test_apply_emits_event(
        self,
        sample_registry: dict[str, SettingDefinition],
    ) -> None:
        profile = SettingsProfileFactory.create(sample_registry)
        definition = sample_registry["ui.theme"]
        profile.apply_setting("ui.theme", "dark", definition)

        assert len(profile.events) == 1
        event = profile.events[0]
        from backend.settings.domain.model import SettingUpdated

        assert isinstance(event, SettingUpdated)
        assert event.key == "ui.theme"
        assert event.new_value == "dark"
        assert event.old_value == "system"  # default
        assert event.category == SettingCategory.UI


class TestSettingsProfileApplyPatch:
    def test_patch_updates_multiple(
        self,
        sample_registry: dict[str, SettingDefinition],
    ) -> None:
        profile = SettingsProfileFactory.create(sample_registry)
        updates = {
            "ui.theme": "dark",
            "voice.wake_word_enabled": False,
            "model.temperature": 1.5,
        }
        profile.apply_patch(updates, sample_registry)

        assert profile.get("ui.theme").value == "dark"  # type: ignore[union-attr]
        assert profile.get("voice.wake_word_enabled").value is False  # type: ignore[union-attr]
        assert profile.get("model.temperature").value == 1.5  # type: ignore[union-attr]
        assert len(profile.events) == 3

    def test_patch_unknown_key_raises(
        self,
        sample_registry: dict[str, SettingDefinition],
    ) -> None:
        profile = SettingsProfileFactory.create(sample_registry)
        with pytest.raises(UnknownSettingKeyError):
            profile.apply_patch({"nonexistent.key": True}, sample_registry)

    def test_patch_validates_values(
        self,
        sample_registry: dict[str, SettingDefinition],
    ) -> None:
        profile = SettingsProfileFactory.create(sample_registry)
        with pytest.raises(SettingTypeMismatchError):
            profile.apply_patch(
                {"model.temperature": "not-a-number"}, sample_registry
            )

    def test_patch_empty_does_nothing(
        self,
        sample_registry: dict[str, SettingDefinition],
    ) -> None:
        profile = SettingsProfileFactory.create(sample_registry)
        profile.apply_patch({}, sample_registry)
        assert len(profile.events) == 0

    def test_patch_safety_floor_raises(
        self,
        sample_registry: dict[str, SettingDefinition],
    ) -> None:
        profile = SettingsProfileFactory.create(sample_registry)
        with pytest.raises(SafetyFloorViolationError):
            profile.apply_patch(
                {"privacy.history_retention_days": 1}, sample_registry
            )


class TestSettingsProfileGetAllInCategory:
    def test_get_all_in_category(
        self,
        sample_registry: dict[str, SettingDefinition],
    ) -> None:
        profile = SettingsProfileFactory.create(sample_registry)
        ui_settings = profile.get_all_in_category(SettingCategory.UI)
        assert len(ui_settings) == 1
        assert ui_settings[0].key == "ui.theme"

    def test_empty_category(self) -> None:
        profile = SettingsProfile(profile_id=SettingId())
        result = profile.get_all_in_category(SettingCategory.VOICE)
        assert result == []


class TestSettingsProfileReset:
    def test_reset_clears_and_sets_defaults(
        self,
        sample_registry: dict[str, SettingDefinition],
    ) -> None:
        profile = SettingsProfileFactory.create(sample_registry)
        profile.apply_patch(
            {"ui.theme": "dark", "model.temperature": 1.5}, sample_registry
        )

        defaults = SettingsProfileFactory.create(sample_registry).settings
        profile.reset_to_defaults(defaults)

        assert profile.get("ui.theme").value == "system"  # type: ignore[union-attr]
        assert profile.get("model.temperature").value == 0.7  # type: ignore[union-attr]

    def test_reset_emits_event(
        self,
        sample_registry: dict[str, SettingDefinition],
    ) -> None:
        profile = SettingsProfileFactory.create(sample_registry)
        defaults = SettingsProfileFactory.create(sample_registry).settings
        profile.reset_to_defaults(defaults)

        assert len(profile.events) == 1
        from backend.settings.domain.model import SettingsReset

        assert isinstance(profile.events[0], SettingsReset)


class TestSettingsProfileEvents:
    def test_events_accumulate(
        self,
        sample_registry: dict[str, SettingDefinition],
    ) -> None:
        profile = SettingsProfileFactory.create(sample_registry)
        profile.apply_patch(
            {"ui.theme": "dark", "voice.wake_word_enabled": False},
            sample_registry,
        )
        assert len(profile.events) == 2

    def test_events_readonly_copy(
        self,
        sample_registry: dict[str, SettingDefinition],
    ) -> None:
        profile = SettingsProfileFactory.create(sample_registry)
        profile.apply_patch({"ui.theme": "dark"}, sample_registry)
        events = profile.events
        events.clear()
        assert len(profile.events) == 1  # original unchanged


# =========================================================================
# Edge cases
# =========================================================================


class TestEdgeCases:
    def test_unknown_key_in_patch_raises(
        self,
        sample_registry: dict[str, SettingDefinition],
    ) -> None:
        profile = SettingsProfileFactory.create(sample_registry)
        with pytest.raises(UnknownSettingKeyError):
            profile.apply_patch({"user.custom_key": "value"}, sample_registry)

    def test_valid_int_but_string_type_definition_rejects(
        self,
    ) -> None:
        d = SettingDefinition(
            key="test.str_val",
            category=SettingCategory.UI,
            scope=SettingScope.USER,
            value_type="str",
            default_value="hello",
        )
        with pytest.raises(SettingTypeMismatchError):
            validate_setting_value("test.str_val", 123, d)

    def test_float_value_in_int_definition_rejected(
        self,
    ) -> None:
        d = SettingDefinition(
            key="test.int_val",
            category=SettingCategory.SYSTEM,
            scope=SettingScope.USER,
            value_type="int",
            default_value=5,
        )
        with pytest.raises(SettingTypeMismatchError):
            validate_setting_value("test.int_val", 3.14, d)

    def test_bool_value_in_str_definition_rejected(
        self,
    ) -> None:
        d = SettingDefinition(
            key="test.str_val",
            category=SettingCategory.UI,
            scope=SettingScope.USER,
            value_type="str",
            default_value="yes",
        )
        with pytest.raises(SettingTypeMismatchError):
            validate_setting_value("test.str_val", True, d)

    def test_int_value_zero_is_valid(
        self,
    ) -> None:
        d = SettingDefinition(
            key="test.zero",
            category=SettingCategory.SYSTEM,
            scope=SettingScope.USER,
            value_type="int",
            default_value=0,
            min_value=0,
            max_value=100,
        )
        validate_setting_value("test.zero", 0, d)

    def test_none_value_rejected(self) -> None:
        d = SettingDefinition(
            key="test.none_val",
            category=SettingCategory.UI,
            scope=SettingScope.USER,
            value_type="str",
            default_value="",
        )
        with pytest.raises(SettingTypeMismatchError):
            validate_setting_value("test.none_val", None, d)

    def test_profile_representation(self) -> None:
        profile = SettingsProfile(profile_id=SettingId())
        rep = repr(profile)
        assert "SettingsProfile" in rep
        assert "count=0" in rep


# =========================================================================
# Default setting definitions
# =========================================================================


def get_default_registry() -> dict[str, SettingDefinition]:
    """Canonical default settings registry for the Settings Service."""
    return {
        # -- System -----------------------------------------------------------------
        "system.language": SettingDefinition(
            key="system.language",
            category=SettingCategory.SYSTEM,
            scope=SettingScope.USER,
            value_type="str",
            default_value="en",
            allowed_values=("en", "fr", "de", "es", "ja", "zh"),
            description="UI language",
        ),
        "system.timezone": SettingDefinition(
            key="system.timezone",
            category=SettingCategory.SYSTEM,
            scope=SettingScope.USER,
            value_type="str",
            default_value="UTC",
            max_length=64,
            description="Timezone identifier (IANA tz)",
        ),
        "system.auto_start": SettingDefinition(
            key="system.auto_start",
            category=SettingCategory.SYSTEM,
            scope=SettingScope.USER,
            value_type="bool",
            default_value=False,
            description="Launch on system startup",
        ),
        # -- Privacy ----------------------------------------------------------------
        "privacy.history_retention_days": SettingDefinition(
            key="privacy.history_retention_days",
            category=SettingCategory.PRIVACY,
            scope=SettingScope.USER,
            value_type="int",
            default_value=30,
            min_value=7,
            max_value=365,
            safety_floor=True,
            description="Days to retain history (minimum 7)",
        ),
        "privacy.analytics_enabled": SettingDefinition(
            key="privacy.analytics_enabled",
            category=SettingCategory.PRIVACY,
            scope=SettingScope.USER,
            value_type="bool",
            default_value=False,
            description="Share anonymous usage data",
        ),
        "privacy.consent_required": SettingDefinition(
            key="privacy.consent_required",
            category=SettingCategory.PRIVACY,
            scope=SettingScope.SYSTEM,
            value_type="bool",
            default_value=True,
            reserved=True,
            description="Require explicit consent for memory",
        ),
        # -- Voice ------------------------------------------------------------------
        "voice.wake_word_enabled": SettingDefinition(
            key="voice.wake_word_enabled",
            category=SettingCategory.VOICE,
            scope=SettingScope.USER,
            value_type="bool",
            default_value=True,
            description="Enable wake word detection",
        ),
        "voice.mic_enabled": SettingDefinition(
            key="voice.mic_enabled",
            category=SettingCategory.VOICE,
            scope=SettingScope.USER,
            value_type="bool",
            default_value=True,
            description="Enable microphone",
        ),
        "voice.retain_audio": SettingDefinition(
            key="voice.retain_audio",
            category=SettingCategory.VOICE,
            scope=SettingScope.USER,
            value_type="bool",
            default_value=False,
            description="Retain audio after transcription",
        ),
        "voice.tts_enabled": SettingDefinition(
            key="voice.tts_enabled",
            category=SettingCategory.VOICE,
            scope=SettingScope.USER,
            value_type="bool",
            default_value=True,
            description="Enable text-to-speech",
        ),
        "voice.tts_speed": SettingDefinition(
            key="voice.tts_speed",
            category=SettingCategory.VOICE,
            scope=SettingScope.USER,
            value_type="float",
            default_value=1.0,
            min_value=0.5,
            max_value=2.0,
            description="TTS playback speed",
        ),
        # -- Notification ----------------------------------------------------------
        "notification.sounds_enabled": SettingDefinition(
            key="notification.sounds_enabled",
            category=SettingCategory.NOTIFICATION,
            scope=SettingScope.USER,
            value_type="bool",
            default_value=True,
            description="Play notification sounds",
        ),
        "notification.quiet_hours_start": SettingDefinition(
            key="notification.quiet_hours_start",
            category=SettingCategory.NOTIFICATION,
            scope=SettingScope.USER,
            value_type="str",
            default_value="22:00",
            max_length=5,
            description="Quiet hours start time (HH:MM)",
        ),
        "notification.quiet_hours_end": SettingDefinition(
            key="notification.quiet_hours_end",
            category=SettingCategory.NOTIFICATION,
            scope=SettingScope.USER,
            value_type="str",
            default_value="07:00",
            max_length=5,
            description="Quiet hours end time (HH:MM)",
        ),
        # -- Model ------------------------------------------------------------------
        "model.temperature": SettingDefinition(
            key="model.temperature",
            category=SettingCategory.MODEL,
            scope=SettingScope.USER,
            value_type="float",
            default_value=0.7,
            min_value=0.0,
            max_value=2.0,
            description="LLM temperature",
        ),
        "model.top_p": SettingDefinition(
            key="model.top_p",
            category=SettingCategory.MODEL,
            scope=SettingScope.USER,
            value_type="float",
            default_value=0.9,
            min_value=0.0,
            max_value=1.0,
            description="LLM top-p sampling",
        ),
        "model.max_tokens": SettingDefinition(
            key="model.max_tokens",
            category=SettingCategory.MODEL,
            scope=SettingScope.USER,
            value_type="int",
            default_value=2048,
            min_value=128,
            max_value=8192,
            description="Maximum output tokens",
        ),
        # -- UI ---------------------------------------------------------------------
        "ui.theme": SettingDefinition(
            key="ui.theme",
            category=SettingCategory.UI,
            scope=SettingScope.USER,
            value_type="str",
            default_value="system",
            allowed_values=("light", "dark", "system"),
            description="UI theme",
        ),
        "ui.reduced_motion": SettingDefinition(
            key="ui.reduced_motion",
            category=SettingCategory.UI,
            scope=SettingScope.USER,
            value_type="bool",
            default_value=False,
            description="Reduce UI animations",
        ),
    }


class TestDefaultRegistry:
    def test_all_definitions_create_valid_profile(self) -> None:
        registry = get_default_registry()
        profile = SettingsProfileFactory.create(registry)
        assert profile.count() == len(registry)

    def test_all_categories_represented(self) -> None:
        registry = get_default_registry()
        categories = {d.category for d in registry.values()}
        assert categories == {
            SettingCategory.SYSTEM,
            SettingCategory.PRIVACY,
            SettingCategory.VOICE,
            SettingCategory.NOTIFICATION,
            SettingCategory.MODEL,
            SettingCategory.UI,
        }

    def test_all_defaults_validated(self) -> None:
        registry = get_default_registry()
        for key, d in registry.items():
            validate_setting_value(key, d.default_value, d)

    def test_category_counts(self) -> None:
        registry = get_default_registry()
        from collections import Counter

        counts = Counter(d.category for d in registry.values())
        assert counts[SettingCategory.SYSTEM] == 3
        assert counts[SettingCategory.PRIVACY] == 3
        assert counts[SettingCategory.VOICE] == 5
        assert counts[SettingCategory.NOTIFICATION] == 3
        assert counts[SettingCategory.MODEL] == 3
        assert counts[SettingCategory.UI] == 2

    def test_reserved_key_consent_cannot_be_modified(self) -> None:
        registry = get_default_registry()
        consent_def = registry["privacy.consent_required"]
        assert consent_def.reserved is True
        with pytest.raises(ReservedSettingKeyError):
            assert_key_not_reserved(consent_def)

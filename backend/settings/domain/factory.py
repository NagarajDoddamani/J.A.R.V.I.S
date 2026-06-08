from __future__ import annotations

from backend.settings.domain.model import (
    Setting,
    SettingDefinition,
    SettingId,
    SettingsProfile,
    Version,
)
from backend.settings.domain.rules import (
    assert_category_valid,
    assert_key_format,
    assert_scope_valid,
    validate_setting_value,
)


class SettingsProfileFactory:
    """Factory for creating validated SettingsProfile aggregates.

    Creates profiles with default values from a registry of
    ``SettingDefinition`` objects. All domain rules are enforced
    at creation time.
    """

    @staticmethod
    def create(
        registry: dict[str, SettingDefinition],
        schema_version: Version | None = None,
    ) -> SettingsProfile:
        _settings: dict[str, Setting] = {}

        for key, definition in registry.items():
            assert_key_format(key)
            assert_key_format(definition.key)
            assert_category_valid(definition.category.value)
            assert_scope_valid(definition.scope.value)
            validate_setting_value(key, definition.default_value, definition)

            _settings[key] = Setting(
                key=key,
                value=definition.default_value,
                category=definition.category,
                scope=definition.scope,
                version=1,
            )

        return SettingsProfile(
            profile_id=SettingId(),
            settings=_settings,
            schema_version=schema_version or Version.current(),
        )

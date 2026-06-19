from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import auto, StrEnum
from typing import Any
from uuid import UUID, uuid4

from backend.settings.domain.exceptions import UnknownSettingKeyError


class SettingCategory(StrEnum):
    SYSTEM = auto()
    PRIVACY = auto()
    VOICE = auto()
    NOTIFICATION = auto()
    MODEL = auto()
    UI = auto()


class SettingScope(StrEnum):
    USER = auto()
    SYSTEM = auto()
    SERVICE = auto()


@dataclass(frozen=True)
class SettingId:
    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class Version:
    major: int
    minor: int

    def __post_init__(self) -> None:
        if self.major < 0 or self.minor < 0:
            msg = f"Version components must be >= 0, got ({self.major}.{self.minor})"
            raise ValueError(msg)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"

    @classmethod
    def current(cls) -> Version:
        return cls(major=1, minor=0)


SETTING_KEY_PATTERN = r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$"
BOOLEAN_VALUES: tuple[bool, ...] = (True, False)


@dataclass(frozen=True)
class SettingDefinition:
    """Schema definition for a single setting key."""

    key: str
    category: SettingCategory
    scope: SettingScope
    value_type: str
    default_value: Any
    min_value: int | float | None = None
    max_value: int | float | None = None
    max_length: int | None = None
    allowed_values: tuple[str, ...] | None = None
    description: str = ""
    safety_floor: bool = False
    reserved: bool = False


@dataclass(frozen=True)
class Setting:
    """A single resolved setting key-value pair."""

    key: str
    value: Any
    category: SettingCategory
    scope: SettingScope
    version: int = 1


@dataclass(frozen=True)
class SettingUpdated:
    """Domain event emitted when a setting value changes."""

    profile_id: SettingId
    key: str
    old_value: Any
    new_value: Any
    category: SettingCategory
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class SettingsReset:
    """Domain event emitted when all settings reset to defaults."""

    profile_id: SettingId
    previous_count: int
    occurred_at: datetime
    event_id: UUID = field(default_factory=uuid4)


class SettingsProfile:
    """Aggregate root for the settings domain.

    A SettingsProfile represents a user's complete collection of settings
    across all categories. Settings are validated against their definitions
    at write time and reject type mismatches, bounds violations, safety floor
    weakenings, and modifications to reserved keys.
    """

    def __init__(
        self,
        profile_id: SettingId,
        settings: dict[str, Setting] | None = None,
        schema_version: Version | None = None,
    ) -> None:
        self._profile_id = profile_id
        self._schema_version = schema_version or Version.current()
        self._settings: dict[str, Setting] = settings or {}
        self._events: list[SettingUpdated | SettingsReset] = []

    # -- properties -----------------------------------------------------------

    @property
    def profile_id(self) -> SettingId:
        return self._profile_id

    @property
    def schema_version(self) -> Version:
        return self._schema_version

    @property
    def settings(self) -> dict[str, Setting]:
        return dict(self._settings)

    @property
    def events(self) -> list[SettingUpdated | SettingsReset]:
        return list(self._events)

    # -- queries --------------------------------------------------------------

    def get(self, key: str) -> Setting | None:
        return self._settings.get(key)

    def get_all_in_category(self, category: SettingCategory) -> list[Setting]:
        return [s for s in self._settings.values() if s.category == category]

    def count(self) -> int:
        return len(self._settings)

    def has_key(self, key: str) -> bool:
        return key in self._settings

    # -- commands -------------------------------------------------------------

    def apply_setting(
        self,
        key: str,
        value: Any,
        definition: SettingDefinition,
    ) -> None:
        old = self._settings.get(key)
        setting = Setting(
            key=key,
            value=value,
            category=definition.category,
            scope=definition.scope,
            version=(old.version + 1) if old else 1,
        )
        self._settings[key] = setting

        self._events.append(
            SettingUpdated(
                profile_id=self._profile_id,
                key=key,
                old_value=old.value if old else None,
                new_value=value,
                category=definition.category,
                occurred_at=datetime.now(tz=timezone.utc),
            )
        )

    def reset_to_defaults(
        self, defaults: dict[str, Setting]
    ) -> None:
        previous_count = len(self._settings)
        self._settings = dict(defaults)
        self._events.append(
            SettingsReset(
                profile_id=self._profile_id,
                previous_count=previous_count,
                occurred_at=datetime.now(tz=timezone.utc),
            )
        )

    def apply_patch(
        self,
        updates: dict[str, Any],
        definitions: dict[str, SettingDefinition],
    ) -> None:
        for key, value in updates.items():
            definition = definitions.get(key)
            if definition is None:
                raise UnknownSettingKeyError(key)
            from backend.settings.domain.rules import validate_setting_value

            validate_setting_value(key, value, definition)
            self.apply_setting(key, value, definition)

    # -- internal -------------------------------------------------------------

    def _clear_events(self) -> None:
        self._events.clear()

    def __repr__(self) -> str:
        return (
            f"SettingsProfile(id={self._profile_id}, "
            f"schema={self._schema_version}, "
            f"count={len(self._settings)})"
        )

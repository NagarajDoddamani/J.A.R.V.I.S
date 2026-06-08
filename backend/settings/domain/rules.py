from __future__ import annotations

import re
from typing import Any

from backend.settings.domain.exceptions import (
    InvalidSettingCategoryError,
    InvalidSettingKeyError,
    InvalidSettingScopeError,
    InvalidVersionError,
    ReservedSettingKeyError,
    SafetyFloorViolationError,
    SettingAllowedValuesError,
    SettingBoundsError,
    SettingMaxLengthError,
    SettingTypeMismatchError,
    UnknownSettingKeyError,
)
from backend.settings.domain.model import (
    SETTING_KEY_PATTERN,
    SettingCategory,
    SettingDefinition,
    SettingScope,
    Version,
)

VALID_CATEGORIES: frozenset[str] = frozenset(c.value for c in SettingCategory)
VALID_SCOPES: frozenset[str] = frozenset(s.value for s in SettingScope)


def assert_key_format(key: str) -> None:
    if not key or not re.match(SETTING_KEY_PATTERN, key):
        raise InvalidSettingKeyError(key)


def assert_key_known(key: str, registry: dict[str, SettingDefinition]) -> None:
    if key not in registry:
        raise UnknownSettingKeyError(key)


def assert_key_not_reserved(definition: SettingDefinition) -> None:
    if definition.reserved:
        raise ReservedSettingKeyError(definition.key)


def assert_category_valid(category: str) -> None:
    if category not in VALID_CATEGORIES:
        raise InvalidSettingCategoryError(category)


def assert_scope_valid(scope: str) -> None:
    if scope not in VALID_SCOPES:
        raise InvalidSettingScopeError(scope)


def assert_version_valid(version: Version) -> None:
    try:
        _ = version.major
        _ = version.minor
    except ValueError as exc:
        raise InvalidVersionError(-1, -1) from exc
    if version.major < 0 or version.minor < 0:
        raise InvalidVersionError(version.major, version.minor)


def assert_value_type(key: str, value: Any, expected_type: str) -> None:
    type_map: dict[str, tuple[type, ...]] = {
        "bool": (bool,),
        "int": (int,),
        "float": (int, float),
        "str": (str,),
        "list": (list,),
        "dict": (dict,),
    }
    allowed = type_map.get(expected_type)
    if allowed is None:
        return
    if not isinstance(value, allowed):
        actual = type(value).__name__
        raise SettingTypeMismatchError(key, expected_type, actual)


def assert_value_not_exceeds_max_length(
    key: str, value: str, max_length: int | None
) -> None:
    if max_length is not None and len(value) > max_length:
        raise SettingMaxLengthError(key, len(value), max_length)


def assert_value_in_bounds(
    key: str,
    value: int | float,
    min_val: int | float | None,
    max_val: int | float | None,
) -> None:
    if min_val is not None and value < min_val:
        raise SettingBoundsError(key, value, min_val, max_val)
    if max_val is not None and value > max_val:
        raise SettingBoundsError(key, value, min_val, max_val)


def assert_value_in_allowed(
    key: str, value: str, allowed: tuple[str, ...] | None
) -> None:
    if allowed is not None and value not in allowed:
        raise SettingAllowedValuesError(key, value, allowed)


def assert_safety_floor(
    key: str,
    new_value: Any,
    definition: SettingDefinition,
) -> None:
    if not definition.safety_floor:
        return
    if definition.min_value is not None and isinstance(new_value, (int, float)):
        if new_value < definition.min_value:
            raise SafetyFloorViolationError(
                key, new_value, definition.min_value
            )
    if isinstance(new_value, bool) and new_value is False:
        if definition.default_value is True:
            raise SafetyFloorViolationError(key, new_value, definition.default_value)


def validate_setting_value(
    key: str,
    value: Any,
    definition: SettingDefinition,
) -> None:
    assert_value_type(key, value, definition.value_type)
    assert_safety_floor(key, value, definition)
    if isinstance(value, str):
        assert_value_not_exceeds_max_length(key, value, definition.max_length)
    if isinstance(value, (int, float)):
        assert_value_in_bounds(key, value, definition.min_value, definition.max_value)
    if isinstance(value, str):
        assert_value_in_allowed(key, value, definition.allowed_values)

from __future__ import annotations


class SettingsDomainError(Exception):
    """Base exception for all settings domain errors."""


class InvalidSettingKeyError(SettingsDomainError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Invalid setting key: {key!r}")


class UnknownSettingKeyError(SettingsDomainError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Unknown setting key: {key!r}")


class InvalidSettingValueError(SettingsDomainError):
    def __init__(self, key: str, value: object, reason: str) -> None:
        super().__init__(f"Invalid value for {key!r}: {value!r} - {reason}")


class InvalidSettingCategoryError(SettingsDomainError):
    def __init__(self, category: str) -> None:
        super().__init__(f"Invalid setting category: {category!r}")


class InvalidSettingScopeError(SettingsDomainError):
    def __init__(self, scope: str) -> None:
        super().__init__(f"Invalid setting scope: {scope!r}")


class SafetyFloorViolationError(SettingsDomainError):
    def __init__(self, key: str, attempted: object, floor: object) -> None:
        super().__init__(
            f"Safety floor violation for {key!r}: attempted {attempted!r}, "
            f"minimum allowed is {floor!r}"
        )


class ReservedSettingKeyError(SettingsDomainError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Cannot modify reserved setting key: {key!r}")


class SchemaVersionMismatchError(SettingsDomainError):
    def __init__(self, current: str, expected: str) -> None:
        super().__init__(
            f"Schema version mismatch: current {current!r}, expected {expected!r}"
        )


class InvalidVersionError(SettingsDomainError):
    def __init__(self, major: int, minor: int) -> None:
        super().__init__(f"Invalid version ({major}.{minor}): must be >= 0.0")


class SettingTypeMismatchError(SettingsDomainError):
    def __init__(self, key: str, expected: str, actual: str) -> None:
        super().__init__(
            f"Type mismatch for {key!r}: expected {expected!r}, got {actual!r}"
        )


class SettingBoundsError(SettingsDomainError):
    def __init__(
        self, key: str, value: object, min_val: object, max_val: object
    ) -> None:
        super().__init__(
            f"Value {value!r} for {key!r} is outside bounds "
            f"[{min_val!r}, {max_val!r}]"
        )


class SettingMaxLengthError(SettingsDomainError):
    def __init__(self, key: str, length: int, max_length: int) -> None:
        super().__init__(
            f"Value length {length} for {key!r} exceeds maximum {max_length}"
        )


class SettingAllowedValuesError(SettingsDomainError):
    def __init__(self, key: str, value: object, allowed: tuple[str, ...]) -> None:
        super().__init__(
            f"Value {value!r} for {key!r} is not in allowed values: {allowed}"
        )


class DuplicateSettingKeyError(SettingsDomainError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Duplicate setting key: {key!r}")

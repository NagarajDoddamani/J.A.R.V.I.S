from __future__ import annotations


class UseCaseError(Exception):
    """Base exception for all use-case-level errors."""


class SettingNotFoundError(UseCaseError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Setting not found: {key}")
        self.key = key


class SettingsProfileNotFoundError(UseCaseError):
    def __init__(self, profile_id: str) -> None:
        super().__init__(f"Settings profile not found: {profile_id}")
        self.profile_id = profile_id

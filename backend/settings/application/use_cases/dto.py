from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Shared response pieces
# ---------------------------------------------------------------------------

@dataclass
class SettingResponse:
    key: str
    value: Any
    category: str
    scope: str
    version: int


# ---------------------------------------------------------------------------
# GetSettingsUseCase
# ---------------------------------------------------------------------------

@dataclass
class GetSettingsRequest:
    category: str | None = None


@dataclass
class GetSettingsResponse:
    settings: list[SettingResponse] = field(default_factory=list)
    total: int = 0


# ---------------------------------------------------------------------------
# GetSettingByKeyUseCase
# ---------------------------------------------------------------------------

@dataclass
class GetSettingByKeyRequest:
    key: str


# ---------------------------------------------------------------------------
# PatchSettingsUseCase
# ---------------------------------------------------------------------------

@dataclass
class PatchSettingsRequest:
    updates: dict[str, Any]
    profile_id: str | None = None


@dataclass
class PatchSettingsResponse:
    updated_settings: list[SettingResponse] = field(default_factory=list)
    updated_count: int = 0
    profile_version: str = ""


# ---------------------------------------------------------------------------
# ResetSettingsUseCase
# ---------------------------------------------------------------------------

@dataclass
class ResetSettingsRequest:
    category: str | None = None
    profile_id: str | None = None


@dataclass
class ResetSettingsResponse:
    reset_count: int = 0
    profile_version: str = ""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.settings.adapters.outbound.clock import SystemClockAdapter
from backend.settings.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemySettingsOutboxAdapter,
    SqlAlchemySettingsRepository,
)
from backend.settings.application.use_cases.get_setting_by_key import (
    GetSettingByKeyUseCase,
)
from backend.settings.application.use_cases.get_settings import (
    GetSettingsUseCase,
)
from backend.settings.application.use_cases.patch_settings import (
    PatchSettingsUseCase,
)
from backend.settings.application.use_cases.reset_settings import (
    ResetSettingsUseCase,
)
from backend.settings.domain.model import (
    SettingCategory,
    SettingDefinition,
    SettingScope,
)

DEFAULT_REGISTRY: dict[str, SettingDefinition] = {
    "system.language": SettingDefinition(
        key="system.language",
        category=SettingCategory.SYSTEM,
        scope=SettingScope.USER,
        value_type="str",
        default_value="en-US",
    ),
    "system.timezone": SettingDefinition(
        key="system.timezone",
        category=SettingCategory.SYSTEM,
        scope=SettingScope.USER,
        value_type="str",
        default_value="UTC",
    ),
    "system.auto_start": SettingDefinition(
        key="system.auto_start",
        category=SettingCategory.SYSTEM,
        scope=SettingScope.SYSTEM,
        value_type="bool",
        default_value=False,
    ),
    "privacy.history_retention_days": SettingDefinition(
        key="privacy.history_retention_days",
        category=SettingCategory.PRIVACY,
        scope=SettingScope.USER,
        value_type="int",
        default_value=30,
        min_value=1,
        max_value=365,
    ),
    "privacy.analytics_enabled": SettingDefinition(
        key="privacy.analytics_enabled",
        category=SettingCategory.PRIVACY,
        scope=SettingScope.USER,
        value_type="bool",
        default_value=True,
    ),
    "privacy.consent_required": SettingDefinition(
        key="privacy.consent_required",
        category=SettingCategory.PRIVACY,
        scope=SettingScope.SYSTEM,
        value_type="bool",
        default_value=True,
        reserved=True,
    ),
    "voice.wake_word": SettingDefinition(
        key="voice.wake_word",
        category=SettingCategory.VOICE,
        scope=SettingScope.USER,
        value_type="str",
        default_value="jarvis",
    ),
    "voice.microphone": SettingDefinition(
        key="voice.microphone",
        category=SettingCategory.VOICE,
        scope=SettingScope.USER,
        value_type="str",
        default_value="default",
    ),
    "voice.wake_word_enabled": SettingDefinition(
        key="voice.wake_word_enabled",
        category=SettingCategory.VOICE,
        scope=SettingScope.USER,
        value_type="bool",
        default_value=True,
    ),
    "voice.retain_audio": SettingDefinition(
        key="voice.retain_audio",
        category=SettingCategory.VOICE,
        scope=SettingScope.USER,
        value_type="bool",
        default_value=False,
    ),
    "voice.tts_enabled": SettingDefinition(
        key="voice.tts_enabled",
        category=SettingCategory.VOICE,
        scope=SettingScope.USER,
        value_type="bool",
        default_value=True,
    ),
    "voice.tts_speed": SettingDefinition(
        key="voice.tts_speed",
        category=SettingCategory.VOICE,
        scope=SettingScope.USER,
        value_type="float",
        default_value=1.0,
        min_value=0.5,
        max_value=2.0,
    ),
    "notification.sounds_enabled": SettingDefinition(
        key="notification.sounds_enabled",
        category=SettingCategory.NOTIFICATION,
        scope=SettingScope.USER,
        value_type="bool",
        default_value=True,
    ),
    "notification.quiet_hours_start": SettingDefinition(
        key="notification.quiet_hours_start",
        category=SettingCategory.NOTIFICATION,
        scope=SettingScope.USER,
        value_type="str",
        default_value="22:00",
    ),
    "notification.quiet_hours_end": SettingDefinition(
        key="notification.quiet_hours_end",
        category=SettingCategory.NOTIFICATION,
        scope=SettingScope.USER,
        value_type="str",
        default_value="07:00",
    ),
    "model.temperature": SettingDefinition(
        key="model.temperature",
        category=SettingCategory.MODEL,
        scope=SettingScope.USER,
        value_type="float",
        default_value=0.7,
        min_value=0.0,
        max_value=2.0,
    ),
    "model.top_p": SettingDefinition(
        key="model.top_p",
        category=SettingCategory.MODEL,
        scope=SettingScope.USER,
        value_type="float",
        default_value=0.9,
        min_value=0.0,
        max_value=1.0,
    ),
    "model.max_tokens": SettingDefinition(
        key="model.max_tokens",
        category=SettingCategory.MODEL,
        scope=SettingScope.USER,
        value_type="int",
        default_value=2048,
        min_value=64,
        max_value=32768,
    ),
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
}


def _settings_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemySettingsRepository:
    return SqlAlchemySettingsRepository(db)


def _settings_outbox(
    db: Session = Depends(get_db),
) -> SqlAlchemySettingsOutboxAdapter:
    return SqlAlchemySettingsOutboxAdapter(db)


def _clock() -> SystemClockAdapter:
    return SystemClockAdapter()


def get_settings_use_case(
    repo: SqlAlchemySettingsRepository = Depends(_settings_repo),
) -> GetSettingsUseCase:
    return GetSettingsUseCase(repo=repo)


def get_setting_by_key_use_case(
    repo: SqlAlchemySettingsRepository = Depends(_settings_repo),
) -> GetSettingByKeyUseCase:
    return GetSettingByKeyUseCase(repo=repo)


def patch_settings_use_case(
    repo: SqlAlchemySettingsRepository = Depends(_settings_repo),
    outbox: SqlAlchemySettingsOutboxAdapter = Depends(_settings_outbox),
    clock: SystemClockAdapter = Depends(_clock),
) -> PatchSettingsUseCase:
    return PatchSettingsUseCase(
        repo=repo,
        outbox=outbox,
        clock=clock,
        registry=DEFAULT_REGISTRY,
    )


def reset_settings_use_case(
    repo: SqlAlchemySettingsRepository = Depends(_settings_repo),
    outbox: SqlAlchemySettingsOutboxAdapter = Depends(_settings_outbox),
    clock: SystemClockAdapter = Depends(_clock),
) -> ResetSettingsUseCase:
    return ResetSettingsUseCase(
        repo=repo,
        outbox=outbox,
        clock=clock,
        registry=DEFAULT_REGISTRY,
    )

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from backend.settings.application.persistence.dto import (
    SettingStorageDto,
    SettingsOutboxStorageDto,
    SettingsProfileStorageDto,
)
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


def _infer_type(value: object) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    return "str"


def _convert_value(value: object, value_type: str) -> str:
    if value is None:
        return ""
    if value_type == "bool":
        return "true" if value else "false"
    return str(value)


def _parse_value(raw: str, value_type: str) -> Any:
    if value_type == "bool":
        return raw == "true"
    if value_type == "int":
        return int(raw)
    if value_type == "float":
        return float(raw)
    return raw


class SettingMapperImpl:
    """Concrete implementation of ``SettingMapperProtocol``.

    Flattens ``Setting`` value objects into ``SettingStorageDto``
    and reconstructs them on the reverse path. The mapping is
    lossless with respect to key, value, category, and scope.
    """

    def domain_to_dto(self, setting: Setting, profile_id: str) -> SettingStorageDto:
        vt = _infer_type(setting.value)
        return SettingStorageDto(
            profile_id=profile_id,
            key=setting.key,
            value=_convert_value(setting.value, vt),
            category=setting.category.value,
            scope=setting.scope.value,
            value_type=vt,
            updated_at=datetime.now(tz=timezone.utc),
        )

    def dto_to_domain(self, dto: SettingStorageDto) -> Setting:
        return Setting(
            key=dto.key,
            value=_parse_value(
                str(dto.value) if dto.value is not None else "",
                dto.value_type,
            ),
            category=SettingCategory(dto.category),
            scope=SettingScope(dto.scope),
        )

    def dto_to_domain_with_version(
        self, dto: SettingStorageDto, version: int
    ) -> Setting:
        return Setting(
            key=dto.key,
            value=_parse_value(
                str(dto.value) if dto.value is not None else "",
                dto.value_type,
            ),
            category=SettingCategory(dto.category),
            scope=SettingScope(dto.scope),
            version=version,
        )


class SettingsProfileMapperImpl:
    """Concrete implementation of ``SettingsProfileMapperProtocol``.

    Flattens ``SettingsProfile`` aggregates into profile-level DTOs
    and individual setting DTOs, and reconstructs them on the
    reverse path.
    """

    def __init__(self, setting_mapper: SettingMapperImpl | None = None) -> None:
        self._setting_mapper = setting_mapper or SettingMapperImpl()

    def domain_to_dto(self, profile: SettingsProfile) -> SettingsProfileStorageDto:
        return SettingsProfileStorageDto(
            profile_id=str(profile.profile_id),
            schema_version_major=profile.schema_version.major,
            schema_version_minor=profile.schema_version.minor,
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc),
        )

    def dto_to_domain(
        self, dto: SettingsProfileStorageDto, settings: list[Setting]
    ) -> SettingsProfile:
        sdict: dict[str, Setting] = {s.key: s for s in settings}
        return SettingsProfile(
            profile_id=SettingId(value=UUID(dto.profile_id)),
            settings=sdict,
            schema_version=Version(
                major=dto.schema_version_major,
                minor=dto.schema_version_minor,
            ),
        )

    def domain_settings_to_dtos(
        self, profile: SettingsProfile
    ) -> list[SettingStorageDto]:
        pid = str(profile.profile_id)
        return [
            self._setting_mapper.domain_to_dto(s, pid)
            for s in profile.settings.values()
        ]


class SettingsOutboxMapperImpl:
    """Mapping between settings domain events and ``SettingsOutboxStorageDto``.

    Converts ``SettingUpdated`` and ``SettingsReset`` events into
    a flattened outbox row and reconstructs them on the reverse
    path.
    """

    def event_to_dto(
        self, event: SettingUpdated | SettingsReset
    ) -> SettingsOutboxStorageDto:
        pid = str(event.profile_id)
        if isinstance(event, SettingUpdated):
            return SettingsOutboxStorageDto(
                event_id=pid,
                profile_id=pid,
                event_type="setting_updated",
                key=event.key,
                old_value=str(event.old_value) if event.old_value is not None else None,
                new_value=str(event.new_value) if event.new_value is not None else None,
                category=event.category.value,
                occurred_at=event.occurred_at,
            )
        return SettingsOutboxStorageDto(
            event_id=pid,
            profile_id=pid,
            event_type="settings_reset",
            key=None,
            old_value=str(event.previous_count),
            new_value=None,
            category=None,
            occurred_at=event.occurred_at,
        )

    def dto_to_event(
        self, dto: SettingsOutboxStorageDto
    ) -> SettingUpdated | SettingsReset:
        pid = SettingId(value=UUID(dto.profile_id))
        if dto.event_type == "setting_updated":
            return SettingUpdated(
                profile_id=pid,
                key=dto.key or "",
                old_value=dto.old_value,
                new_value=dto.new_value,
                category=SettingCategory(dto.category) if dto.category else SettingCategory.UI,
                occurred_at=dto.occurred_at,
            )
        previous_count = int(dto.old_value) if dto.old_value else 0
        return SettingsReset(
            profile_id=pid,
            previous_count=previous_count,
            occurred_at=dto.occurred_at,
        )

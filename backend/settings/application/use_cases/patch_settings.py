from __future__ import annotations

from uuid import UUID

from backend.settings.application.ports.clock import SettingsClockPort
from backend.settings.application.ports.outbox import SettingsOutboxPort
from backend.settings.application.ports.repository import (
    SettingsRepositoryPort,
)
from backend.settings.application.use_cases.dto import (
    PatchSettingsRequest,
    PatchSettingsResponse,
    SettingResponse,
)
from backend.settings.application.use_cases.exceptions import (
    SettingsProfileNotFoundError,
)
from backend.settings.domain.factory import SettingsProfileFactory
from backend.settings.domain.model import (
    SettingDefinition,
    SettingId,
    SettingsProfile,
)


class PatchSettingsUseCase:
    """Apply a patch of setting changes to a profile.

    Loads the current profile (creating one if none exists), validates
    and applies each update through the aggregate, persists the result,
    and writes generated domain events to the outbox.
    """

    def __init__(
        self,
        repo: SettingsRepositoryPort,
        outbox: SettingsOutboxPort,
        clock: SettingsClockPort,
        registry: dict[str, SettingDefinition],
    ) -> None:
        self._repo = repo
        self._outbox = outbox
        self._clock = clock
        self._registry = registry

    def execute(
        self, request: PatchSettingsRequest
    ) -> PatchSettingsResponse:
        profile = self._load_or_create_profile(request.profile_id)

        for key, value in request.updates.items():
            definition = self._registry.get(key)
            if definition is not None:
                from backend.settings.domain.rules import (
                    validate_setting_value,
                )

                validate_setting_value(key, value, definition)

        profile.apply_patch(request.updates, self._registry)

        self._repo.save(profile)

        for event in profile.events:
            self._outbox.append(event)

        updated_settings = [
            SettingResponse(
                key=s.key,
                value=s.value,
                category=s.category.value,
                scope=s.scope.value,
                version=s.version,
            )
            for s in profile.settings.values()
            if s.key in request.updates
        ]

        return PatchSettingsResponse(
            updated_settings=updated_settings,
            updated_count=len(updated_settings),
            profile_version=str(profile.schema_version),
        )

    def _load_or_create_profile(
        self, profile_id: str | None
    ) -> SettingsProfile:
        if profile_id:
            pid = SettingId(value=UUID(profile_id))
            profile = self._repo.find_by_id(pid)
            if profile is None:
                raise SettingsProfileNotFoundError(profile_id)
            return profile

        return SettingsProfileFactory.create(self._registry)

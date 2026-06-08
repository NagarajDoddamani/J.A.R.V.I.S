from __future__ import annotations

from uuid import UUID

from backend.settings.application.ports.clock import SettingsClockPort
from backend.settings.application.ports.outbox import SettingsOutboxPort
from backend.settings.application.ports.repository import (
    SettingsRepositoryPort,
)
from backend.settings.application.use_cases.dto import (
    ResetSettingsRequest,
    ResetSettingsResponse,
)
from backend.settings.application.use_cases.exceptions import (
    SettingsProfileNotFoundError,
)
from backend.settings.domain.factory import SettingsProfileFactory
from backend.settings.domain.model import (
    SettingCategory,
    SettingDefinition,
    SettingId,
    SettingsProfile,
)


class ResetSettingsUseCase:
    """Reset all or category-specific settings to their defaults.

    Loads the current profile (creating one if none exists), resets
    to factory defaults, persists the result, and writes generated
    domain events to the outbox.
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
        self, request: ResetSettingsRequest
    ) -> ResetSettingsResponse:
        profile = self._load_or_create_profile(request.profile_id)
        defaults = SettingsProfileFactory.create(self._registry)

        if request.category:
            cat = SettingCategory(request.category)
            category_defaults = {
                k: v
                for k, v in defaults.settings.items()
                if v.category == cat
            }
            profile.apply_patch(
                {k: v.value for k, v in category_defaults.items()},
                self._registry,
            )
        else:
            profile.reset_to_defaults(defaults.settings)

        self._repo.save(profile)

        for event in profile.events:
            self._outbox.append(event)

        return ResetSettingsResponse(
            reset_count=profile.count(),
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

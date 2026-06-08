from __future__ import annotations

from backend.settings.application.ports.repository import (
    SettingsRepositoryPort,
)
from backend.settings.application.use_cases.dto import (
    GetSettingsRequest,
    GetSettingsResponse,
    SettingResponse,
)


class GetSettingsUseCase:
    """Return all settings across profiles, optionally filtered by category."""

    def __init__(self, repo: SettingsRepositoryPort) -> None:
        self._repo = repo

    def execute(
        self, request: GetSettingsRequest
    ) -> GetSettingsResponse:
        all_settings = self._repo.get_all()

        if request.category:
            filtered = [
                s for s in all_settings
                if s.category.value == request.category
            ]
        else:
            filtered = all_settings

        return GetSettingsResponse(
            settings=[
                SettingResponse(
                    key=s.key,
                    value=s.value,
                    category=s.category.value,
                    scope=s.scope.value,
                    version=s.version,
                )
                for s in filtered
            ],
            total=len(filtered),
        )

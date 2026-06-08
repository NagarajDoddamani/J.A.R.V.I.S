from __future__ import annotations

from backend.settings.application.ports.repository import (
    SettingsRepositoryPort,
)
from backend.settings.application.use_cases.dto import (
    GetSettingByKeyRequest,
    SettingResponse,
)
from backend.settings.application.use_cases.exceptions import (
    SettingNotFoundError,
)


class GetSettingByKeyUseCase:
    """Retrieve a single setting by its dotted key."""

    def __init__(self, repo: SettingsRepositoryPort) -> None:
        self._repo = repo

    def execute(
        self, request: GetSettingByKeyRequest
    ) -> SettingResponse:
        setting = self._repo.find_by_key(request.key)
        if setting is None:
            raise SettingNotFoundError(request.key)

        return SettingResponse(
            key=setting.key,
            value=setting.value,
            category=setting.category.value,
            scope=setting.scope.value,
            version=setting.version,
        )

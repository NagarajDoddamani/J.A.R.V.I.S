from __future__ import annotations

from uuid import UUID

from backend.memory.application.ports.repository import ConsentRepositoryPort
from backend.memory.application.use_cases.dto import (
    ConsentResponse,
    GetConsentRequest,
)
from backend.memory.application.use_cases.exceptions import ConsentNotFoundError
from backend.memory.domain.model import ConsentId


class GetConsentUseCase:
    """Retrieve a single consent record by its unique identifier."""

    def __init__(self, consent_repo: ConsentRepositoryPort) -> None:
        self._consent_repo = consent_repo

    def execute(self, request: GetConsentRequest) -> ConsentResponse:
        consent_id = ConsentId(value=UUID(request.consent_id))
        consent = self._consent_repo.find_by_id(consent_id)
        if consent is None:
            raise ConsentNotFoundError(request.consent_id)

        return ConsentResponse(
            consent_id=str(consent.consent_id),
            status=consent.status.value,
            granted_at=consent.granted_at,
            expires_at=consent.expires_at,
            revoked_at=consent.revoked_at,
            policy_version=consent.policy_version,
        )

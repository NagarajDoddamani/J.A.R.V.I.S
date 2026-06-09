from __future__ import annotations

from uuid import UUID

from backend.memory.application.ports.outbox import MemoryOutboxPort
from backend.memory.application.ports.repository import ConsentRepositoryPort
from backend.memory.application.use_cases.dto import (
    RevokeConsentRequest,
    RevokeConsentResponse,
)
from backend.memory.application.use_cases.exceptions import ConsentNotFoundError
from backend.memory.domain.model import ConsentId, ConsentRevoked


class RevokeConsentUseCase:
    """Revoke an existing consent record.

    Loads the consent, transitions it to REVOKED status, persists
    the change, and emits a ``ConsentRevoked`` domain event to the
    outbox.
    """

    def __init__(
        self,
        consent_repo: ConsentRepositoryPort,
        outbox: MemoryOutboxPort,
    ) -> None:
        self._consent_repo = consent_repo
        self._outbox = outbox

    def execute(self, request: RevokeConsentRequest) -> RevokeConsentResponse:
        consent_id = ConsentId(value=UUID(request.consent_id))
        consent = self._consent_repo.find_by_id(consent_id)
        if consent is None:
            raise ConsentNotFoundError(request.consent_id)

        consent.revoke()

        self._consent_repo.save(consent)

        event = ConsentRevoked(
            consent_id=consent_id,
            occurred_at=consent.revoked_at,  # type: ignore[arg-type]
        )
        self._outbox.append(event)

        return RevokeConsentResponse(
            consent_id=str(consent_id),
            status=consent.status.value,
            revoked_at=consent.revoked_at,  # type: ignore[arg-type]
        )

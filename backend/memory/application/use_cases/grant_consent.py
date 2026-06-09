from __future__ import annotations

from backend.memory.application.ports.clock import MemoryClockPort
from backend.memory.application.ports.id_generator import MemoryIdGeneratorPort
from backend.memory.application.ports.outbox import MemoryOutboxPort
from backend.memory.application.ports.repository import ConsentRepositoryPort
from backend.memory.application.use_cases.dto import (
    GrantConsentRequest,
    GrantConsentResponse,
)
from backend.memory.domain.model import (
    ConsentGranted,
    ConsentRecord,
)


class GrantConsentUseCase:
    """Create and activate a new consent record.

    Generates a unique consent identifier, creates a ``ConsentRecord``
    in ACTIVE status, persists it, and emits a ``ConsentGranted``
    domain event to the outbox.
    """

    def __init__(
        self,
        consent_repo: ConsentRepositoryPort,
        outbox: MemoryOutboxPort,
        clock: MemoryClockPort,
        id_generator: MemoryIdGeneratorPort,
    ) -> None:
        self._consent_repo = consent_repo
        self._outbox = outbox
        self._clock = clock
        self._id_generator = id_generator

    def execute(self, request: GrantConsentRequest) -> GrantConsentResponse:
        consent_id = self._id_generator.generate_consent_id()
        now = self._clock.now()

        consent = ConsentRecord(
            consent_id=consent_id,
            expires_at=request.expires_at,
            policy_version=request.policy_version,
        )
        consent.grant()

        self._consent_repo.save(consent)

        event = ConsentGranted(consent_id=consent_id, occurred_at=now)
        self._outbox.append(event)

        return GrantConsentResponse(
            consent_id=str(consent_id),
            status=consent.status.value,
            granted_at=now,
            expires_at=consent.expires_at,
            policy_version=consent.policy_version,
        )

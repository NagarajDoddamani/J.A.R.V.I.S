from __future__ import annotations

from uuid import UUID

from backend.audit.application.ports.repository import (
    AuditEntryRepositoryPort,
)
from backend.audit.application.use_cases.dto import (
    AuditEntryResponse,
    GetAuditEntryRequest,
)
from backend.audit.application.use_cases.exceptions import (
    AuditEntryNotFoundError,
)
from backend.audit.domain.model import AuditEntryId


class GetAuditEntryUseCase:
    """Retrieve a single audit entry by its unique identifier."""

    def __init__(
        self, entry_repo: AuditEntryRepositoryPort
    ) -> None:
        self._entry_repo = entry_repo

    def execute(
        self, request: GetAuditEntryRequest
    ) -> AuditEntryResponse:
        entry_id = AuditEntryId(value=UUID(request.entry_id))
        entry = self._entry_repo.find_by_id(entry_id)
        if entry is None:
            raise AuditEntryNotFoundError(request.entry_id)

        return AuditEntryResponse(
            entry_id=str(entry.entry_id),
            chain_name=entry.chain_name,
            actor_type=entry.actor.actor_type,
            actor_id=entry.actor.actor_id,
            action=entry.action,
            target_type=(
                entry.target.target_type if entry.target else None
            ),
            target_ref=(
                entry.target.target_ref if entry.target else None
            ),
            policy_decision=entry.policy_decision,
            classification=entry.classification,
            correlation_id=entry.correlation_id,
            causation_id=entry.causation_id,
            result=entry.result,
            redacted_reason=entry.redacted_reason,
            occurred_at=entry.occurred_at.value,
            previous_hash_hex=(
                entry.previous_hash.hex() if entry.previous_hash else None
            ),
            entry_hash_hex=entry.entry_hash.hex(),
            entry_index=entry.entry_index.value,
        )

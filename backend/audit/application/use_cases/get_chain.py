from __future__ import annotations

from backend.audit.application.ports.repository import (
    AuditEntryRepositoryPort,
)
from backend.audit.application.use_cases.dto import (
    AuditEntryResponse,
    GetAuditChainRequest,
    GetAuditChainResponse,
)


class GetAuditChainUseCase:
    """Retrieve paginated entries from a named audit chain."""

    def __init__(
        self, entry_repo: AuditEntryRepositoryPort
    ) -> None:
        self._entry_repo = entry_repo

    def execute(
        self, request: GetAuditChainRequest
    ) -> GetAuditChainResponse:
        entries = self._entry_repo.find_by_chain(
            chain_name=request.chain_name,
            since_index=request.since_index,
            limit=request.limit,
            offset=request.offset,
        )
        total = self._entry_repo.count_by_chain(request.chain_name)

        return GetAuditChainResponse(
            entries=[
                AuditEntryResponse(
                    entry_id=str(e.entry_id),
                    chain_name=e.chain_name,
                    actor_type=e.actor.actor_type,
                    actor_id=e.actor.actor_id,
                    action=e.action,
                    target_type=(
                        e.target.target_type if e.target else None
                    ),
                    target_ref=(
                        e.target.target_ref if e.target else None
                    ),
                    policy_decision=e.policy_decision,
                    classification=e.classification,
                    correlation_id=e.correlation_id,
                    causation_id=e.causation_id,
                    result=e.result,
                    redacted_reason=e.redacted_reason,
                    occurred_at=e.occurred_at.value,
                    previous_hash_hex=(
                        e.previous_hash.hex()
                        if e.previous_hash
                        else None
                    ),
                    entry_hash_hex=e.entry_hash.hex(),
                    entry_index=e.entry_index.value,
                )
                for e in entries
            ],
            total=total,
        )

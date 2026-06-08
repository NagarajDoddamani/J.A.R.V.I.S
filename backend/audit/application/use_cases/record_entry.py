from __future__ import annotations

from datetime import datetime
from typing import Protocol

from backend.audit.application.ports.clock import AuditClockPort
from backend.audit.application.ports.id_generator import AuditIdGeneratorPort
from backend.audit.application.ports.outbox import AuditOutboxPort
from backend.audit.application.ports.repository import (
    AuditChainHeadRepositoryPort,
    AuditEntryRepositoryPort,
)
from backend.audit.application.use_cases.dto import (
    RecordAuditEntryRequest,
    RecordAuditEntryResponse,
)
from backend.audit.domain.factory import AuditEntryFactory
from backend.audit.domain.model import AuditChainHead


class RecordAuditEntryUseCase:
    """Record a new audit entry.

    Creates an ``AuditEntry`` aggregate through the domain factory,
    persists it, updates the chain head, and writes the resulting
    domain event to the outbox. All operations are synchronous;
    transactional coordination is the caller's responsibility.
    """

    def __init__(
        self,
        entry_repo: AuditEntryRepositoryPort,
        chain_head_repo: AuditChainHeadRepositoryPort,
        outbox: AuditOutboxPort,
        clock: AuditClockPort,
        id_generator: AuditIdGeneratorPort,  # kept for future use
    ) -> None:
        self._entry_repo = entry_repo
        self._chain_head_repo = chain_head_repo
        self._outbox = outbox
        self._clock = clock
        self._id_generator = id_generator

    def execute(
        self, request: RecordAuditEntryRequest
    ) -> RecordAuditEntryResponse:
        occurred_at = (
            request.occurred_at if request.occurred_at else self._clock.now()
        )

        head = self._chain_head_repo.find_by_chain(request.chain_name)
        previous_entry_hash: bytes | None = (
            head.head_hash.value if head and head.head_hash else None
        )
        previous_entry_index: int | None = (
            head.entries_count - 1 if head else None
        )

        entry, domain_event = AuditEntryFactory.create(
            chain_name=request.chain_name,
            action=request.action,
            policy_decision=request.policy_decision,
            classification=request.classification,
            correlation_id=request.correlation_id,
            result=request.result,
            actor_type=request.actor_type,
            actor_id=request.actor_id,
            causation_id=request.causation_id,
            target_type=request.target_type,
            target_ref=request.target_ref,
            redacted_reason=request.redacted_reason,
            occurred_at=occurred_at,
            previous_entry_hash=previous_entry_hash,
            previous_entry_index=previous_entry_index,
        )

        self._entry_repo.save(entry)

        new_head = AuditChainHead(
            chain_name=request.chain_name,
            head_hash=entry.entry_hash,
            entries_count=(head.entries_count + 1 if head else 1),
        )
        self._chain_head_repo.save(new_head)

        self._outbox.append(domain_event)

        return RecordAuditEntryResponse(
            entry_id=str(entry.entry_id),
            chain_name=entry.chain_name,
            action=entry.action,
            policy_decision=entry.policy_decision,
            classification=entry.classification,
            correlation_id=entry.correlation_id,
            causation_id=entry.causation_id,
            result=entry.result,
            actor_type=entry.actor.actor_type,
            actor_id=entry.actor.actor_id,
            entry_index=entry.entry_index.value,
            entry_hash_hex=entry.entry_hash.hex(),
            previous_hash_hex=(
                entry.previous_hash.hex() if entry.previous_hash else None
            ),
            occurred_at=entry.occurred_at.value,
        )

from __future__ import annotations

from uuid import UUID

from backend.audit.application.persistence.dto import (
    AuditChainHeadStorageDTO,
    AuditEntryStorageDTO,
    AuditOutboxStorageDTO,
)
from backend.audit.domain.model import (
    ActorRef,
    AuditChainHead,
    AuditEntry,
    AuditEntryId,
    AuditEntryRecorded,
    AuditEntryState,
    EntryHash,
    EntryIndex,
    OccurredAt,
    TargetRef,
)


class AuditEntryMapperImpl:
    """Concrete implementation of the ``AuditEntryMapper`` protocol.

    Flattens ``AuditEntry`` value objects into a ``AuditEntryStorageDTO``
    and reconstructs them on the reverse path. The mapping is lossless.
    """

    def domain_to_dto(self, entry: AuditEntry) -> AuditEntryStorageDTO:
        return AuditEntryStorageDTO(
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
            previous_hash=(
                entry.previous_hash.value if entry.previous_hash else None
            ),
            entry_hash=entry.entry_hash.value,
            entry_index=entry.entry_index.value,
        )

    def dto_to_domain(self, dto: AuditEntryStorageDTO) -> AuditEntry:
        return AuditEntry(
            entry_id=AuditEntryId(value=UUID(dto.entry_id)),
            chain_name=dto.chain_name,
            actor=ActorRef(
                actor_type=dto.actor_type, actor_id=dto.actor_id
            ),
            action=dto.action,
            target=(
                TargetRef(
                    target_type=dto.target_type,
                    target_ref=dto.target_ref,
                )
                if dto.target_type or dto.target_ref
                else None
            ),
            policy_decision=dto.policy_decision,
            classification=dto.classification,
            correlation_id=dto.correlation_id,
            causation_id=dto.causation_id,
            result=dto.result,
            redacted_reason=dto.redacted_reason,
            occurred_at=OccurredAt(value=dto.occurred_at),
            previous_hash=(
                EntryHash(value=dto.previous_hash)
                if dto.previous_hash is not None
                else None
            ),
            entry_hash=EntryHash(value=dto.entry_hash),
            entry_index=EntryIndex(value=dto.entry_index),
            state=AuditEntryState.RECORDED,
        )


class AuditChainHeadMapperImpl:
    """Concrete implementation of the ``AuditChainHeadMapper`` protocol."""

    def domain_to_dto(
        self, head: AuditChainHead
    ) -> AuditChainHeadStorageDTO:
        return AuditChainHeadStorageDTO(
            chain_name=head.chain_name,
            head_hash=head.head_hash.value if head.head_hash else None,
            entries_count=head.entries_count,
        )

    def dto_to_domain(
        self, dto: AuditChainHeadStorageDTO
    ) -> AuditChainHead:
        return AuditChainHead(
            chain_name=dto.chain_name,
            head_hash=(
                EntryHash(value=dto.head_hash)
                if dto.head_hash is not None
                else None
            ),
            entries_count=dto.entries_count,
        )


class AuditOutboxMapperImpl:
    """Concrete implementation of the ``AuditOutboxMapper`` protocol."""

    def event_to_dto(
        self, event: AuditEntryRecorded
    ) -> AuditOutboxStorageDTO:
        return AuditOutboxStorageDTO(
            entry_id=str(event.entry_id),
            chain_name=event.chain_name,
            action=event.action,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            correlation_id=event.correlation_id,
            entry_index=event.entry_index,
            occurred_at=event.occurred_at,
            published=False,
        )

    def dto_to_event(
        self, dto: AuditOutboxStorageDTO
    ) -> AuditEntryRecorded:
        return AuditEntryRecorded(
            entry_id=AuditEntryId(value=UUID(dto.entry_id)),
            chain_name=dto.chain_name,
            action=dto.action,
            actor_type=dto.actor_type,
            actor_id=dto.actor_id,
            correlation_id=dto.correlation_id,
            entry_index=dto.entry_index,
            occurred_at=dto.occurred_at,
        )

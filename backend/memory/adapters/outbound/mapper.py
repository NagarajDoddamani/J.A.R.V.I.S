from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID, uuid4

from backend.memory.application.persistence.dto import (
    ConsentStorageDTO,
    MemoryOutboxStorageDTO,
    MemoryStorageDTO,
)
from backend.memory.domain.model import (
    ConsentGranted,
    ConsentId,
    ConsentRecord,
    ConsentRevoked,
    ConsentStatus,
    Memory,
    MemoryCategory,
    MemoryContent,
    MemoryCreated,
    MemoryDeleted,
    MemoryId,
    MemoryPurgeScheduled,
    MemoryPurged,
    MemoryRetentionExpired,
    MemoryState,
    MemoryUpdated,
    Provenance,
    RetentionPolicy,
    RetentionStatus,
    RevisionNumber,
)

MemoryOutboxDomainEvent = (
    MemoryCreated
    | MemoryUpdated
    | MemoryDeleted
    | MemoryRetentionExpired
    | MemoryPurgeScheduled
    | MemoryPurged
    | ConsentGranted
    | ConsentRevoked
)

_EVENT_TYPE_MAP: dict[type, str] = {
    MemoryCreated: "memory.created",
    MemoryUpdated: "memory.updated",
    MemoryDeleted: "memory.deleted",
    MemoryRetentionExpired: "memory.retention_expired",
    MemoryPurgeScheduled: "memory.purge_scheduled",
    MemoryPurged: "memory.purged",
    ConsentGranted: "consent.granted",
    ConsentRevoked: "consent.revoked",
}

_EVENT_TYPE_REVERSE: dict[str, type] = {v: k for k, v in _EVENT_TYPE_MAP.items()}


class MemoryMapperImpl:
    """Concrete implementation of the ``MemoryMapper`` protocol.

    Flattens ``Memory`` value objects into a ``MemoryStorageDTO``
    and reconstructs them on the reverse path. The mapping is lossless
    for all DTO-representable fields.
    """

    def domain_to_dto(self, memory: Memory) -> MemoryStorageDTO:
        return MemoryStorageDTO(
            memory_id=str(memory.memory_id),
            consent_id=str(memory.consent_id),
            content=memory.content.value,
            category=memory.category.value,
            source_type=memory.source_type,
            source_id=memory.source_id,
            provenance_actor_id=memory.provenance.actor_id,
            provenance_timestamp=memory.provenance.timestamp,
            classification=memory.classification,
            sensitivity=memory.sensitivity,
            retention_policy=memory.retention.policy,
            retention_status=memory.retention_status.value,
            revision=int(memory.revision),
            created_at=memory.created_at,
            updated_at=memory.updated_at,
            deleted_at=memory.deleted_at,
        )

    def dto_to_domain(self, dto: MemoryStorageDTO) -> Memory:
        retention_kw: dict[str, object] = {"policy": dto.retention_policy}
        if dto.retention_policy == "time_bound":
            retention_kw["ttl_days"] = 30
        state = MemoryState.DELETED if dto.deleted_at is not None else MemoryState.CREATED
        return Memory(
            memory_id=MemoryId(value=UUID(dto.memory_id)),
            consent_id=ConsentId(value=UUID(dto.consent_id)),
            content=MemoryContent(value=dto.content),
            category=MemoryCategory(dto.category),
            source_type=dto.source_type,
            source_id=dto.source_id,
            provenance=Provenance(
                source=dto.source_type,
                timestamp=dto.provenance_timestamp,
                actor_id=dto.provenance_actor_id,
            ),
            classification=dto.classification,
            sensitivity=dto.sensitivity,
            retention=RetentionPolicy(**retention_kw),  # type: ignore[arg-type]
            retention_status=RetentionStatus(dto.retention_status),
            revision=RevisionNumber(value=dto.revision),
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            deleted_at=dto.deleted_at,
            state=state,
        )


class ConsentMapperImpl:
    """Concrete implementation of the ``ConsentMapper`` protocol.

    Flattens ``ConsentRecord`` into ``ConsentStorageDTO`` and
    reconstructs it on the reverse path. The mapping is lossless.
    """

    def domain_to_dto(self, consent: ConsentRecord) -> ConsentStorageDTO:
        return ConsentStorageDTO(
            consent_id=str(consent.consent_id),
            status=consent.status.value,
            policy_version=consent.policy_version,
            granted_at=consent.granted_at,
            expires_at=consent.expires_at,
            revoked_at=consent.revoked_at,
        )

    def dto_to_domain(self, dto: ConsentStorageDTO) -> ConsentRecord:
        return ConsentRecord(
            consent_id=ConsentId(value=UUID(dto.consent_id)),
            status=ConsentStatus(dto.status),
            policy_version=dto.policy_version,
            granted_at=dto.granted_at,
            expires_at=dto.expires_at,
            revoked_at=dto.revoked_at,
        )


class MemoryOutboxMapperImpl:
    """Concrete implementation of the ``MemoryOutboxMapper`` protocol.

    Converts memory domain events (``MemoryCreated``, ``ConsentGranted``,
    etc.) into ``MemoryOutboxStorageDTO`` and reconstructs them on the
    reverse path. Event-specific fields are serialised into the
    ``payload`` JSON string.
    """

    def event_to_dto(self, event: MemoryOutboxDomainEvent) -> MemoryOutboxStorageDTO:
        event_type = _EVENT_TYPE_MAP.get(type(event), "unknown")
        aggregate_id = self._get_aggregate_id(event)
        payload = self._build_payload(event)
        return MemoryOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type=event_type,
            aggregate_id=aggregate_id,
            occurred_at=event.occurred_at,
            payload=json.dumps(payload) if payload else None,
            published=False,
        )

    def dto_to_event(self, dto: MemoryOutboxStorageDTO) -> MemoryOutboxDomainEvent:
        event_cls = _EVENT_TYPE_REVERSE.get(dto.event_type)
        if event_cls is None:
            raise ValueError(f"Unknown event_type: {dto.event_type}")
        payload = json.loads(dto.payload) if dto.payload else {}
        aggregate_uuid = UUID(dto.aggregate_id)

        if event_cls is MemoryCreated:
            return MemoryCreated(
                memory_id=MemoryId(value=aggregate_uuid),
                consent_id=ConsentId(value=UUID(payload["consent_id"])),
                category=MemoryCategory(payload["category"]),
                source_type=payload["source_type"],
                source_id=payload.get("source_id"),
                sensitivity=payload["sensitivity"],
                occurred_at=dto.occurred_at,
            )
        if event_cls is MemoryUpdated:
            return MemoryUpdated(
                memory_id=MemoryId(value=aggregate_uuid),
                revision=payload["revision"],
                occurred_at=dto.occurred_at,
            )
        if event_cls is MemoryDeleted:
            return MemoryDeleted(
                memory_id=MemoryId(value=aggregate_uuid),
                revision=payload["revision"],
                occurred_at=dto.occurred_at,
            )
        if event_cls is MemoryRetentionExpired:
            return MemoryRetentionExpired(
                memory_id=MemoryId(value=aggregate_uuid),
                revision=payload["revision"],
                occurred_at=dto.occurred_at,
            )
        if event_cls is MemoryPurgeScheduled:
            return MemoryPurgeScheduled(
                memory_id=MemoryId(value=aggregate_uuid),
                revision=payload["revision"],
                occurred_at=dto.occurred_at,
            )
        if event_cls is MemoryPurged:
            return MemoryPurged(
                memory_id=MemoryId(value=aggregate_uuid),
                revision=payload["revision"],
                occurred_at=dto.occurred_at,
            )
        if event_cls is ConsentGranted:
            return ConsentGranted(
                consent_id=ConsentId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is ConsentRevoked:
            return ConsentRevoked(
                consent_id=ConsentId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )

        raise ValueError(f"Unsupported event type: {event_cls}")

    @staticmethod
    def _get_aggregate_id(event: MemoryOutboxDomainEvent) -> str:
        if isinstance(event, (MemoryCreated, MemoryUpdated, MemoryDeleted,
                              MemoryRetentionExpired, MemoryPurgeScheduled, MemoryPurged)):
            return str(event.memory_id)
        return str(event.consent_id)

    @staticmethod
    def _build_payload(event: MemoryOutboxDomainEvent) -> dict | None:
        if isinstance(event, MemoryCreated):
            return {
                "consent_id": str(event.consent_id),
                "category": event.category.value,
                "source_type": event.source_type,
                "source_id": event.source_id,
                "sensitivity": event.sensitivity,
            }
        if isinstance(event, (MemoryUpdated, MemoryDeleted,
                             MemoryRetentionExpired, MemoryPurgeScheduled, MemoryPurged)):
            return {"revision": event.revision}
        return None

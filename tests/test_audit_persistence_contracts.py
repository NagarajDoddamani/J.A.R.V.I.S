from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

import pytest

from backend.audit.application.persistence.dto import (
    AuditChainHeadStorageDTO,
    AuditEntryStorageDTO,
    AuditOutboxStorageDTO,
)
from backend.audit.application.persistence.mapper import (
    AuditChainHeadMapper,
    AuditEntryMapper,
    AuditOutboxMapper,
)
from backend.audit.application.persistence.schema import (
    AUDIT_CHAIN_HEADS_TABLE,
    AUDIT_ENTRIES_TABLE,
    AUDIT_OUTBOX_TABLE,
    ColumnContract,
    TableContract,
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
from backend.audit.domain.factory import AuditEntryFactory

# ===================================================================
# Stub mapper implementations (conform to mapper protocols)
# ===================================================================


class StubAuditEntryMapper:
    """Stub mapper conforming to ``AuditEntryMapper`` protocol."""

    def domain_to_dto(self, entry: AuditEntry) -> AuditEntryStorageDTO:
        return AuditEntryStorageDTO(
            entry_id=str(entry.entry_id),
            chain_name=entry.chain_name,
            actor_type=entry.actor.actor_type,
            actor_id=entry.actor.actor_id,
            action=entry.action,
            target_type=entry.target.target_type if entry.target else None,
            target_ref=entry.target.target_ref if entry.target else None,
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
            entry_id=AuditEntryId(
                value=__import__("uuid", fromlist=["UUID"]).UUID(dto.entry_id)
            ),
            chain_name=dto.chain_name,
            actor=ActorRef(
                actor_type=dto.actor_type, actor_id=dto.actor_id
            ),
            action=dto.action,
            target=(
                TargetRef(
                    target_type=dto.target_type, target_ref=dto.target_ref
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


class StubAuditChainHeadMapper:
    """Stub mapper conforming to ``AuditChainHeadMapper`` protocol."""

    def domain_to_dto(
        self, head: AuditChainHead
    ) -> AuditChainHeadStorageDTO:
        return AuditChainHeadStorageDTO(
            chain_name=head.chain_name,
            head_hash=head.head_hash.value if head.head_hash else None,
            entries_count=head.entries_count,
            updated_at=datetime.now(tz=timezone.utc),
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


class StubAuditOutboxMapper:
    """Stub mapper conforming to ``AuditOutboxMapper`` protocol."""

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
            entry_id=AuditEntryId(
                value=__import__("uuid", fromlist=["UUID"]).UUID(dto.entry_id)
            ),
            chain_name=dto.chain_name,
            action=dto.action,
            actor_type=dto.actor_type,
            actor_id=dto.actor_id,
            correlation_id=dto.correlation_id,
            entry_index=dto.entry_index,
            occurred_at=dto.occurred_at,
        )


# ===================================================================
# DTO construction tests
# ===================================================================


class TestAuditEntryStorageDTO:
    def test_all_fields_present(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = AuditEntryStorageDTO(
            entry_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            chain_name="security",
            actor_type="user",
            actor_id="alice",
            action="memory.create",
            target_type="memory",
            target_ref="mem-001",
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-001",
            causation_id="cause-001",
            result="success",
            redacted_reason=None,
            occurred_at=dt,
            previous_hash=b"\x01" * 32,
            entry_hash=b"\x02" * 32,
            entry_index=0,
        )
        assert dto.entry_id == "01975c2f-4aef-7cf1-a940-ae54bf596280"
        assert dto.chain_name == "security"
        assert dto.actor_type == "user"
        assert dto.actor_id == "alice"
        assert dto.entry_hash == b"\x02" * 32
        assert dto.entry_index == 0

    def test_nullable_target_fields(self) -> None:
        dto = AuditEntryStorageDTO(
            entry_id="id-1",
            chain_name="system",
            actor_type="service",
            actor_id="svc",
            action="startup",
            target_type=None,
            target_ref=None,
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-null",
            causation_id=None,
            result="success",
            redacted_reason=None,
            occurred_at=datetime.now(tz=timezone.utc),
            previous_hash=None,
            entry_hash=b"\x00" * 32,
            entry_index=0,
        )
        assert dto.target_type is None
        assert dto.target_ref is None
        assert dto.causation_id is None
        assert dto.redacted_reason is None
        assert dto.previous_hash is None

    def test_frozen(self) -> None:
        dto = AuditEntryStorageDTO(
            entry_id="id-1",
            chain_name="test",
            actor_type="user",
            actor_id=None,
            action="test",
            target_type=None,
            target_ref=None,
            policy_decision="grant",
            classification="public",
            correlation_id="corr-1",
            causation_id=None,
            result="ok",
            redacted_reason=None,
            occurred_at=datetime.now(tz=timezone.utc),
            previous_hash=None,
            entry_hash=b"\x00" * 32,
            entry_index=0,
        )
        with pytest.raises(AttributeError):
            dto.entry_id = "changed"


class TestAuditChainHeadStorageDTO:
    def test_minimal(self) -> None:
        dto = AuditChainHeadStorageDTO(
            chain_name="security", head_hash=None, entries_count=0
        )
        assert dto.chain_name == "security"
        assert dto.head_hash is None
        assert dto.entries_count == 0
        assert dto.updated_at is None

    def test_with_hash(self) -> None:
        dto = AuditChainHeadStorageDTO(
            chain_name="consent",
            head_hash=b"\xab" * 32,
            entries_count=42,
            updated_at=datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc),
        )
        assert dto.head_hash == b"\xab" * 32
        assert dto.entries_count == 42
        assert dto.updated_at is not None


class TestAuditOutboxStorageDTO:
    def test_default_published_false(self) -> None:
        dto = AuditOutboxStorageDTO(
            entry_id="id-1",
            chain_name="security",
            action="test.action",
            actor_type="user",
            actor_id="alice",
            correlation_id="corr-1",
            entry_index=0,
            occurred_at=datetime.now(tz=timezone.utc),
        )
        assert dto.published is False

    def test_explicit_published(self) -> None:
        dto = AuditOutboxStorageDTO(
            entry_id="id-1",
            chain_name="security",
            action="test.action",
            actor_type="user",
            actor_id="alice",
            correlation_id="corr-1",
            entry_index=0,
            occurred_at=datetime.now(tz=timezone.utc),
            published=True,
        )
        assert dto.published is True


# ===================================================================
# Mapper protocol conformance tests
# ===================================================================


class TestAuditEntryMapper:
    @pytest.fixture
    def mapper(self) -> StubAuditEntryMapper:
        return StubAuditEntryMapper()

    def test_protocol_conformance(self) -> None:
        mapper: AuditEntryMapper = StubAuditEntryMapper()
        assert isinstance(mapper, StubAuditEntryMapper)

    def test_domain_to_dto(self, mapper: StubAuditEntryMapper) -> None:
        entry, _ = AuditEntryFactory.create(
            chain_name="security",
            action="memory.create",
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-map",
            result="success",
            actor_type="user",
            actor_id="alice",
            target_type="memory",
            target_ref="mem-001",
        )
        dto = mapper.domain_to_dto(entry)
        assert dto.entry_id == str(entry.entry_id)
        assert dto.chain_name == "security"
        assert dto.actor_type == "user"
        assert dto.actor_id == "alice"
        assert dto.action == "memory.create"
        assert dto.target_type == "memory"
        assert dto.target_ref == "mem-001"
        assert dto.policy_decision == "grant"
        assert dto.classification == "internal"
        assert dto.correlation_id == "corr-map"
        assert dto.result == "success"
        assert dto.entry_hash == entry.entry_hash.value
        assert dto.entry_index == 0

    def test_dto_to_domain(self, mapper: StubAuditEntryMapper) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = AuditEntryStorageDTO(
            entry_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            chain_name="consent",
            actor_type="service",
            actor_id="audit-svc",
            action="consent.revoke",
            target_type="consent",
            target_ref="cons-001",
            policy_decision="deny",
            classification="sensitive",
            correlation_id="corr-rev",
            causation_id="cause-rev",
            result="denied",
            redacted_reason="User revoked consent",
            occurred_at=dt,
            previous_hash=b"\x01" * 32,
            entry_hash=b"\x02" * 32,
            entry_index=5,
        )
        entry = mapper.dto_to_domain(dto)
        assert entry.entry_id is not None
        assert entry.chain_name == "consent"
        assert entry.actor.actor_type == "service"
        assert entry.actor.actor_id == "audit-svc"
        assert entry.action == "consent.revoke"
        assert entry.target is not None
        assert entry.target.target_type == "consent"
        assert entry.target.target_ref == "cons-001"
        assert entry.policy_decision == "deny"
        assert entry.classification == "sensitive"
        assert entry.causation_id == "cause-rev"
        assert entry.result == "denied"
        assert entry.redacted_reason == "User revoked consent"
        assert entry.occurred_at.value == dt
        assert entry.previous_hash == EntryHash(value=b"\x01" * 32)
        assert entry.entry_hash == EntryHash(value=b"\x02" * 32)
        assert entry.entry_index == EntryIndex(value=5)
        assert entry.state == AuditEntryState.RECORDED

    def test_roundtrip(self, mapper: StubAuditEntryMapper) -> None:
        """domain → dto → domain preserves all values."""
        original, _ = AuditEntryFactory.create(
            chain_name="roundtrip",
            action="verify.roundtrip",
            policy_decision="require_confirmation",
            classification="restricted",
            correlation_id="corr-rt",
            causation_id="cause-rt",
            result="pending",
            actor_type="agent",
            actor_id="jarvis",
            target_type="document",
            target_ref="doc-099",
            redacted_reason="Needs user approval",
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)

        assert str(reconstructed.entry_id) == str(original.entry_id)
        assert reconstructed.chain_name == original.chain_name
        assert reconstructed.actor.actor_type == original.actor.actor_type
        assert reconstructed.actor.actor_id == original.actor.actor_id
        assert reconstructed.action == original.action
        assert reconstructed.target is not None
        assert reconstructed.target.target_type == original.target.target_type
        assert reconstructed.target.target_ref == original.target.target_ref
        assert reconstructed.policy_decision == original.policy_decision
        assert reconstructed.classification == original.classification
        assert reconstructed.correlation_id == original.correlation_id
        assert reconstructed.causation_id == original.causation_id
        assert reconstructed.result == original.result
        assert reconstructed.redacted_reason == original.redacted_reason
        assert reconstructed.occurred_at.value == original.occurred_at.value
        assert reconstructed.previous_hash == original.previous_hash
        assert reconstructed.entry_hash == original.entry_hash
        assert reconstructed.entry_index == original.entry_index

    def test_null_fields_roundtrip(self, mapper: StubAuditEntryMapper) -> None:
        """Null fields survive the roundtrip."""
        original, _ = AuditEntryFactory.create(
            chain_name="null-test",
            action="verify.nulls",
            policy_decision="grant",
            classification="public",
            correlation_id="corr-null-rt",
            result="success",
            actor_type="user",
            actor_id=None,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.actor.actor_id is None
        assert reconstructed.target is None
        assert reconstructed.previous_hash is None


class TestAuditChainHeadMapper:
    @pytest.fixture
    def mapper(self) -> StubAuditChainHeadMapper:
        return StubAuditChainHeadMapper()

    def test_protocol_conformance(self) -> None:
        mapper: AuditChainHeadMapper = StubAuditChainHeadMapper()
        assert isinstance(mapper, StubAuditChainHeadMapper)

    def test_domain_to_dto(self, mapper: StubAuditChainHeadMapper) -> None:
        head = AuditChainHead(
            chain_name="security",
            head_hash=EntryHash(value=b"\xab" * 32),
            entries_count=100,
        )
        dto = mapper.domain_to_dto(head)
        assert dto.chain_name == "security"
        assert dto.head_hash == b"\xab" * 32
        assert dto.entries_count == 100
        assert dto.updated_at is not None

    def test_dto_to_domain(self, mapper: StubAuditChainHeadMapper) -> None:
        dto = AuditChainHeadStorageDTO(
            chain_name="consent",
            head_hash=b"\xcd" * 32,
            entries_count=42,
        )
        head = mapper.dto_to_domain(dto)
        assert head.chain_name == "consent"
        assert head.head_hash == EntryHash(value=b"\xcd" * 32)
        assert head.entries_count == 42

    def test_roundtrip(self, mapper: StubAuditChainHeadMapper) -> None:
        original = AuditChainHead(
            chain_name="policy", head_hash=EntryHash(value=b"\xef" * 32), entries_count=7
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.chain_name == original.chain_name
        assert reconstructed.head_hash == original.head_hash
        assert reconstructed.entries_count == original.entries_count

    def test_null_head_hash_roundtrip(
        self, mapper: StubAuditChainHeadMapper
    ) -> None:
        original = AuditChainHead(
            chain_name="empty", head_hash=None, entries_count=0
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.head_hash is None
        assert reconstructed.entries_count == 0


class TestAuditOutboxMapper:
    @pytest.fixture
    def mapper(self) -> StubAuditOutboxMapper:
        return StubAuditOutboxMapper()

    def test_protocol_conformance(self) -> None:
        mapper: AuditOutboxMapper = StubAuditOutboxMapper()
        assert isinstance(mapper, StubAuditOutboxMapper)

    def test_event_to_dto(self, mapper: StubAuditOutboxMapper) -> None:
        entry, event = AuditEntryFactory.create(
            chain_name="security",
            action="test.event",
            policy_decision="grant",
            classification="public",
            correlation_id="corr-evt",
            result="success",
            actor_type="user",
            actor_id="alice",
        )
        dto = mapper.event_to_dto(event)
        assert dto.entry_id == str(entry.entry_id)
        assert dto.chain_name == "security"
        assert dto.action == "test.event"
        assert dto.actor_type == "user"
        assert dto.actor_id == "alice"
        assert dto.correlation_id == "corr-evt"
        assert dto.entry_index == 0
        assert dto.published is False

    def test_dto_to_event(self, mapper: StubAuditOutboxMapper) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        dto = AuditOutboxStorageDTO(
            entry_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            chain_name="system",
            action="service.start",
            actor_type="service",
            actor_id="audit-svc",
            correlation_id="corr-svc",
            entry_index=3,
            occurred_at=dt,
        )
        event = mapper.dto_to_event(dto)
        assert str(event.entry_id) == dto.entry_id
        assert event.chain_name == "system"
        assert event.action == "service.start"
        assert event.actor_type == "service"
        assert event.actor_id == "audit-svc"
        assert event.correlation_id == "corr-svc"
        assert event.entry_index == 3
        assert event.occurred_at == dt

    def test_roundtrip(self, mapper: StubAuditOutboxMapper) -> None:
        _, original_event = AuditEntryFactory.create(
            chain_name="roundtrip-outbox",
            action="verify.outbox",
            policy_decision="deny",
            classification="sensitive",
            correlation_id="corr-ob",
            result="denied",
            actor_type="agent",
            actor_id="jarvis",
        )
        dto = mapper.event_to_dto(original_event)
        reconstructed = mapper.dto_to_event(dto)

        assert str(reconstructed.entry_id) == str(original_event.entry_id)
        assert reconstructed.chain_name == original_event.chain_name
        assert reconstructed.action == original_event.action
        assert reconstructed.actor_type == original_event.actor_type
        assert reconstructed.actor_id == original_event.actor_id
        assert reconstructed.correlation_id == original_event.correlation_id
        assert reconstructed.entry_index == original_event.entry_index
        assert reconstructed.occurred_at == original_event.occurred_at

    def test_null_actor_id_roundtrip(
        self, mapper: StubAuditOutboxMapper
    ) -> None:
        _, event = AuditEntryFactory.create(
            chain_name="null-actor",
            action="verify.null.actor",
            policy_decision="grant",
            classification="public",
            correlation_id="corr-na",
            result="success",
            actor_type="service",
            actor_id=None,
        )
        dto = mapper.event_to_dto(event)
        reconstructed = mapper.dto_to_event(dto)
        assert reconstructed.actor_id is None


# ===================================================================
# Schema contract consistency tests
# ===================================================================


class TestSchemaContracts:
    def test_audit_entries_column_count(self) -> None:
        assert len(AUDIT_ENTRIES_TABLE.columns) == 17

    def test_audit_entries_schema_name(self) -> None:
        assert AUDIT_ENTRIES_TABLE.schema == "audit"
        assert AUDIT_ENTRIES_TABLE.name == "audit_entries"

    def test_audit_entries_primary_key(self) -> None:
        assert AUDIT_ENTRIES_TABLE.primary_key == "entry_id"

    def test_audit_entries_indexes(self) -> None:
        expected = {
            "ix_audit_entries_chain_index",
            "ix_audit_entries_correlation",
            "ix_audit_entries_actor",
        }
        assert set(AUDIT_ENTRIES_TABLE.indexes) == expected

    def test_audit_entries_actor_type_enum(self) -> None:
        col = next(
            c
            for c in AUDIT_ENTRIES_TABLE.columns
            if c.name == "actor_type"
        )
        assert col.enum_values == ("user", "service", "agent")
        assert col.max_length == 16
        assert col.nullable is False

    def test_audit_entries_classification_enum(self) -> None:
        col = next(
            c
            for c in AUDIT_ENTRIES_TABLE.columns
            if c.name == "classification"
        )
        assert col.enum_values == (
            "public", "internal", "sensitive", "restricted"
        )
        assert col.max_length == 16
        assert col.nullable is False

    def test_audit_entries_nullable_columns(self) -> None:
        nullable = {
            c.name
            for c in AUDIT_ENTRIES_TABLE.columns
            if c.nullable
        }
        assert nullable == {
            "actor_id", "target_type", "target_ref",
            "causation_id", "redacted_reason", "previous_hash",
        }

    def test_audit_chain_heads_column_count(self) -> None:
        assert len(AUDIT_CHAIN_HEADS_TABLE.columns) == 4

    def test_audit_chain_heads_primary_key(self) -> None:
        assert AUDIT_CHAIN_HEADS_TABLE.primary_key == "chain_name"

    def test_audit_chain_heads_schema(self) -> None:
        assert AUDIT_CHAIN_HEADS_TABLE.schema == "audit"
        assert AUDIT_CHAIN_HEADS_TABLE.name == "audit_chain_heads"

    def test_audit_outbox_column_count(self) -> None:
        assert len(AUDIT_OUTBOX_TABLE.columns) == 9

    def test_audit_outbox_schema(self) -> None:
        assert AUDIT_OUTBOX_TABLE.schema == "audit"
        assert AUDIT_OUTBOX_TABLE.name == "outbox"


# ===================================================================
# DTO ↔ Schema field alignment tests
# ===================================================================


class TestDTOFieldAlignment:
    """Verify DTO fields match schema column contracts."""

    def test_entry_dto_fields_match_schema_columns(self) -> None:
        dto_fields = {
            "entry_id", "chain_name", "actor_type", "actor_id",
            "action", "target_type", "target_ref",
            "policy_decision", "classification",
            "correlation_id", "causation_id",
            "result", "redacted_reason",
            "occurred_at", "previous_hash", "entry_hash",
            "entry_index",
        }
        schema_cols = {c.name for c in AUDIT_ENTRIES_TABLE.columns}
        assert dto_fields == schema_cols, (
            f"DTO fields not aligned with schema columns. "
            f"Missing from DTO: {schema_cols - dto_fields}. "
            f"Missing from schema: {dto_fields - schema_cols}."
        )

    def test_chain_head_dto_fields_match_schema(self) -> None:
        dto_fields = {"chain_name", "head_hash", "entries_count", "updated_at"}
        schema_cols = {c.name for c in AUDIT_CHAIN_HEADS_TABLE.columns}
        assert dto_fields == schema_cols

    def test_entry_dto_field_types_match_schema(self) -> None:
        schema_map = {c.name: c.py_type for c in AUDIT_ENTRIES_TABLE.columns}
        assert schema_map["entry_id"] == str
        assert schema_map["chain_name"] == str
        assert schema_map["actor_type"] == str
        assert schema_map["entry_hash"] == bytes
        assert schema_map["entry_index"] == int
        assert schema_map["occurred_at"] == datetime

    def test_chain_head_dto_field_types_match_schema(self) -> None:
        schema_map = {c.name: c.py_type for c in AUDIT_CHAIN_HEADS_TABLE.columns}
        assert schema_map["chain_name"] == str
        assert schema_map["head_hash"] == bytes
        assert schema_map["entries_count"] == int
        assert schema_map["updated_at"] == datetime

    def test_entry_dto_nullability_matches_schema(self) -> None:
        schema_nullable = {
            c.name
            for c in AUDIT_ENTRIES_TABLE.columns
            if c.nullable
        }
        dto_nullable_hints = {
            "actor_id", "target_type", "target_ref",
            "causation_id", "redacted_reason", "previous_hash",
        }
        assert schema_nullable == dto_nullable_hints

    def test_entry_dto_non_nullable_fields(self) -> None:
        schema_non_nullable = {
            c.name
            for c in AUDIT_ENTRIES_TABLE.columns
            if not c.nullable
        }
        dto_non_nullable = {
            "entry_id", "chain_name", "actor_type",
            "action", "policy_decision", "classification",
            "correlation_id", "result",
            "occurred_at", "entry_hash", "entry_index",
        }
        assert schema_non_nullable == dto_non_nullable


# ===================================================================
# Mapper interface signature verification
# ===================================================================


class TestMapperMethodSignatures:
    def test_audit_entry_mapper_methods(self) -> None:
        mapper: AuditEntryMapper = StubAuditEntryMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")

    def test_audit_chain_head_mapper_methods(self) -> None:
        mapper: AuditChainHeadMapper = StubAuditChainHeadMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")

    def test_audit_outbox_mapper_methods(self) -> None:
        mapper: AuditOutboxMapper = StubAuditOutboxMapper()
        assert hasattr(mapper, "event_to_dto")
        assert hasattr(mapper, "dto_to_event")


# ===================================================================
# Schema value constraint alignment with domain rules
# ===================================================================


class TestSchemaDomainAlignment:
    """Verify schema enum values match domain rule constants."""

    def test_actor_type_enum_matches_domain(self) -> None:
        from backend.audit.domain.rules import VALID_ACTOR_TYPES
        col = next(
            c for c in AUDIT_ENTRIES_TABLE.columns
            if c.name == "actor_type"
        )
        assert col.enum_values is not None
        assert set(col.enum_values) == VALID_ACTOR_TYPES

    def test_classification_enum_matches_domain(self) -> None:
        from backend.audit.domain.rules import VALID_CLASSIFICATIONS
        col = next(
            c for c in AUDIT_ENTRIES_TABLE.columns
            if c.name == "classification"
        )
        assert col.enum_values is not None
        assert set(col.enum_values) == VALID_CLASSIFICATIONS

    def test_policy_decision_not_in_schema_enum(self) -> None:
        """policy_decision has no DB check constraint — validated at domain layer."""
        col = next(
            c for c in AUDIT_ENTRIES_TABLE.columns
            if c.name == "policy_decision"
        )
        assert col.enum_values is None

    def test_entry_id_max_length_not_set(self) -> None:
        """UUID-as-string has no practical max_length beyond format."""
        col = next(
            c for c in AUDIT_ENTRIES_TABLE.columns
            if c.name == "entry_id"
        )
        assert col.max_length is None

    def test_chain_name_max_length(self) -> None:
        col = next(
            c for c in AUDIT_ENTRIES_TABLE.columns
            if c.name == "chain_name"
        )
        assert col.max_length == 128

    def test_action_max_length(self) -> None:
        col = next(
            c for c in AUDIT_ENTRIES_TABLE.columns
            if c.name == "action"
        )
        assert col.max_length == 128

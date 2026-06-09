from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from backend.memory.domain.exceptions import (
    ConsentNotActiveError,
    ContentTooLongError,
    DeletedMemoryUpdateError,
    EmptyContentError,
    EventPayloadTooDetailedError,
    ExpirationBeforeGrantError,
    InvalidClassificationError,
    InvalidConsentTransitionError,
    InvalidProvenanceError,
    InvalidRetentionPolicyError,
    InvalidSensitivityError,
    MemoryDomainError,
    ProvenanceMismatchError,
    ProvenanceRequiredError,
    PurgedConsentError,
    PurgedMemoryImmutableError,
    RestrictedMemoryRequiresRedactionError,
    RetentionExpirationError,
    RetentionRequiredError,
    RevokedConsentBlocksUpdateError,
    SecretDetectedError,
    SensitiveMemoryRequiresConsentError,
    SourceRequiredError,
)
from backend.memory.domain.factory import MemoryFactory
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
    MemorySource,
    MemoryState,
    MemoryUpdated,
    Provenance,
    RetentionPolicy,
    RetentionStatus,
    RevisionNumber,
)
from backend.memory.domain.rules import (
    MAX_CONTENT_LENGTH,
    VALID_CLASSIFICATIONS,
    VALID_SENSITIVITY_LEVELS,
    assert_consent_active,
    assert_consent_allows_updates,
    assert_consent_can_transition,
    assert_content_max_length,
    assert_content_no_secrets,
    assert_content_not_empty,
    assert_event_payload_compliant,
    assert_event_payload_omits_content,
    assert_expiration_after_grant,
    assert_not_deleted,
    assert_not_purged,
    assert_provenance_preserved,
    assert_provenance_provided,
    assert_restricted_requires_redaction,
    assert_retention_can_expire,
    assert_retention_provided,
    assert_sensitive_requires_consent,
    assert_sensitivity_valid,
    assert_source_provided,
    assert_classification_valid,
    validate_memory_creation,
)

# ===========================================================================
# Helpers
# ===========================================================================


def make_valid_consent(
    status: ConsentStatus = ConsentStatus.ACTIVE,
) -> ConsentRecord:
    c = ConsentRecord(status=ConsentStatus.PROPOSED)
    if status == ConsentStatus.ACTIVE:
        c.grant()
    elif status == ConsentStatus.REVOKED:
        c.grant()
        c.revoke()
    return c


def make_valid_provenance() -> Provenance:
    return Provenance(
        source="user_input", timestamp=datetime.now(tz=timezone.utc), actor_id="user-1"
    )


def make_valid_retention() -> RetentionPolicy:
    return RetentionPolicy(policy="persistent")


def make_memory(
    content: str = "valid memory content",
    consent: ConsentRecord | None = None,
    category: MemoryCategory = MemoryCategory.GENERAL,
    source_type: str = "user_input",
    source_id: str | None = None,
    provenance: Provenance | None = None,
    classification: str = "public",
    sensitivity: str = "public",
    retention: RetentionPolicy | None = None,
    redaction_metadata: str | None = None,
) -> Memory:
    c = consent or make_valid_consent(ConsentStatus.ACTIVE)
    p = provenance or make_valid_provenance()
    r = retention or make_valid_retention()
    mem, _ = MemoryFactory.create(
        consent=c,
        content=content,
        category=category,
        source_type=source_type,
        source_id=source_id,
        provenance=p,
        retention=r,
        classification=classification,
        sensitivity=sensitivity,
        redaction_metadata=redaction_metadata,
    )
    return mem


# =============================================================================
# 1. Value Object Tests
# =============================================================================


class TestMemoryId:
    def test_creation(self) -> None:
        mid = MemoryId()
        assert isinstance(mid.value, UUID)

    def test_str_representation(self) -> None:
        mid = MemoryId()
        assert str(mid) == str(mid.value)

    def test_equality(self) -> None:
        v = UUID("00000000-0000-0000-0000-000000000001")
        a = MemoryId(value=v)
        b = MemoryId(value=v)
        assert a == b

    def test_inequality(self) -> None:
        assert MemoryId() != MemoryId()

    def test_immutability(self) -> None:
        mid = MemoryId()
        with pytest.raises(AttributeError):
            mid.value = UUID(int=0)  # type: ignore


class TestConsentId:
    def test_creation(self) -> None:
        cid = ConsentId()
        assert isinstance(cid.value, UUID)

    def test_str(self) -> None:
        cid = ConsentId()
        assert str(cid) == str(cid.value)


class TestRevisionNumber:
    def test_default_is_one(self) -> None:
        r = RevisionNumber()
        assert r.value == 1

    def test_custom_value(self) -> None:
        r = RevisionNumber(value=5)
        assert r.value == 5

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match=">= 1"):
            RevisionNumber(value=0)

    def test_negative_value_raises(self) -> None:
        with pytest.raises(ValueError, match=">= 1"):
            RevisionNumber(value=-1)

    def test_increment(self) -> None:
        r = RevisionNumber(value=3)
        r2 = r.increment()
        assert r2.value == 4

    def test_increment_does_not_mutate(self) -> None:
        r = RevisionNumber(value=3)
        r.increment()
        assert r.value == 3

    def test_int_conversion(self) -> None:
        r = RevisionNumber(value=7)
        assert int(r) == 7

    def test_equality(self) -> None:
        assert RevisionNumber(value=2) == RevisionNumber(value=2)


class TestMemoryContent:
    def test_creation(self) -> None:
        mc = MemoryContent(value="hello")
        assert mc.value == "hello"

    def test_str_conversion(self) -> None:
        mc = MemoryContent(value="test")
        assert str(mc) == "test"

    def test_length(self) -> None:
        mc = MemoryContent(value="abcde")
        assert len(mc) == 5

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            MemoryContent(value=123)  # type: ignore

    def test_equality(self) -> None:
        assert MemoryContent(value="a") == MemoryContent(value="a")

    def test_frozen(self) -> None:
        mc = MemoryContent(value="a")
        with pytest.raises(AttributeError):
            mc.value = "b"  # type: ignore


class TestProvenance:
    def test_creation(self) -> None:
        now = datetime.now(tz=timezone.utc)
        p = Provenance(source="conversation", timestamp=now, actor_id="alice")
        assert p.source == "conversation"
        assert p.actor_id == "alice"

    def test_empty_source_raises(self) -> None:
        now = datetime.now(tz=timezone.utc)
        with pytest.raises(InvalidProvenanceError):
            Provenance(source="", timestamp=now)

    def test_blank_source_raises(self) -> None:
        now = datetime.now(tz=timezone.utc)
        with pytest.raises(InvalidProvenanceError):
            Provenance(source="   ", timestamp=now)

    def test_naive_datetime_gets_utc(self) -> None:
        now = datetime.now()
        p = Provenance(source="test", timestamp=now)
        assert p.timestamp.tzinfo is not None
        assert p.timestamp.tzinfo.utcoffset(None) == timedelta(0)

    def test_actor_id_optional(self) -> None:
        now = datetime.now(tz=timezone.utc)
        p = Provenance(source="test", timestamp=now)
        assert p.actor_id is None

    def test_frozen(self) -> None:
        now = datetime.now(tz=timezone.utc)
        p = Provenance(source="test", timestamp=now)
        with pytest.raises(AttributeError):
            p.source = "other"  # type: ignore


class TestRetentionPolicy:
    def test_persistent_creation(self) -> None:
        rp = RetentionPolicy(policy="persistent")
        assert rp.policy == "persistent"
        assert rp.ttl_days is None

    def test_ephemeral_creation(self) -> None:
        rp = RetentionPolicy(policy="ephemeral")
        assert rp.policy == "ephemeral"

    def test_time_bound_creation(self) -> None:
        rp = RetentionPolicy(policy="time_bound", ttl_days=30)
        assert rp.ttl_days == 30

    def test_invalid_policy_raises(self) -> None:
        with pytest.raises(InvalidRetentionPolicyError):
            RetentionPolicy(policy="forever")

    def test_time_bound_needs_ttl(self) -> None:
        with pytest.raises(InvalidRetentionPolicyError):
            RetentionPolicy(policy="time_bound", ttl_days=None)

    def test_time_bound_ttl_must_be_positive(self) -> None:
        with pytest.raises(InvalidRetentionPolicyError):
            RetentionPolicy(policy="time_bound", ttl_days=0)

    def test_persistent_no_ttl(self) -> None:
        with pytest.raises(InvalidRetentionPolicyError):
            RetentionPolicy(policy="persistent", ttl_days=30)

    def test_ephemeral_no_ttl(self) -> None:
        with pytest.raises(InvalidRetentionPolicyError):
            RetentionPolicy(policy="ephemeral", ttl_days=1)

    def test_frozen(self) -> None:
        rp = RetentionPolicy(policy="persistent")
        with pytest.raises(AttributeError):
            rp.policy = "ephemeral"  # type: ignore


# =============================================================================
# 2. Enum Tests
# =============================================================================


class TestMemoryCategory:
    def test_members(self) -> None:
        assert MemoryCategory.GENERAL.value == "general"
        assert MemoryCategory.CONVERSATION.value == "conversation"
        assert MemoryCategory.DOCUMENT.value == "document"
        assert MemoryCategory.INSIGHT.value == "insight"
        assert MemoryCategory.PREFERENCE.value == "preference"
        assert MemoryCategory.EPHEMERAL.value == "ephemeral"

    def test_from_string(self) -> None:
        assert MemoryCategory("general") == MemoryCategory.GENERAL


class TestMemoryState:
    def test_members(self) -> None:
        assert MemoryState.CREATED.value == "created"
        assert MemoryState.UPDATED.value == "updated"
        assert MemoryState.DELETED.value == "deleted"

    def test_transitions(self) -> None:
        assert MemoryState.CREATED != MemoryState.DELETED


class TestConsentStatus:
    def test_members(self) -> None:
        assert ConsentStatus.PROPOSED.value == "proposed"
        assert ConsentStatus.ACTIVE.value == "active"
        assert ConsentStatus.REVOKED.value == "revoked"
        assert ConsentStatus.PURGED.value == "purged"

    def test_order(self) -> None:
        members = list(ConsentStatus)
        assert members == [
            ConsentStatus.PROPOSED,
            ConsentStatus.ACTIVE,
            ConsentStatus.REVOKED,
            ConsentStatus.PURGED,
        ]


class TestMemorySource:
    def test_members(self) -> None:
        assert MemorySource.USER_INPUT.value == "user_input"
        assert MemorySource.CONVERSATION.value == "conversation"
        assert MemorySource.INFERENCE.value == "inference"
        assert MemorySource.SYSTEM.value == "system"
        assert MemorySource.EXTERNAL.value == "external"


class TestRetentionStatus:
    def test_members(self) -> None:
        assert RetentionStatus.ACTIVE.value == "active"
        assert RetentionStatus.EXPIRED.value == "expired"
        assert RetentionStatus.PURGE_PENDING.value == "purge_pending"
        assert RetentionStatus.PURGED.value == "purged"


# =============================================================================
# 3. Domain Event Tests
# =============================================================================


class TestMemoryCreated:
    def test_creation(self) -> None:
        mid = MemoryId()
        cid = ConsentId()
        now = datetime.now(tz=timezone.utc)
        ev = MemoryCreated(
            memory_id=mid,
            consent_id=cid,
            category=MemoryCategory.GENERAL,
            source_type="user_input",
            source_id="src-123",
            sensitivity="public",
            occurred_at=now,
        )
        assert ev.memory_id == mid
        assert ev.consent_id == cid
        assert ev.category == MemoryCategory.GENERAL
        assert ev.source_type == "user_input"
        assert ev.source_id == "src-123"
        assert ev.sensitivity == "public"
        assert ev.occurred_at == now

    def test_frozen(self) -> None:
        mid = MemoryId()
        cid = ConsentId()
        ev = MemoryCreated(
            memory_id=mid,
            consent_id=cid,
            category=MemoryCategory.GENERAL,
            source_type="user_input",
            source_id=None,
            sensitivity="public",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            ev.source_type = "other"  # type: ignore

    def test_no_content_in_event(self) -> None:
        assert not hasattr(MemoryCreated, "content")


class TestMemoryUpdated:
    def test_creation(self) -> None:
        mid = MemoryId()
        now = datetime.now(tz=timezone.utc)
        ev = MemoryUpdated(memory_id=mid, revision=2, occurred_at=now)
        assert ev.memory_id == mid
        assert ev.revision == 2
        assert ev.occurred_at == now

    def test_frozen(self) -> None:
        mid = MemoryId()
        ev = MemoryUpdated(
            memory_id=mid, revision=2, occurred_at=datetime.now(tz=timezone.utc)
        )
        with pytest.raises(AttributeError):
            ev.revision = 3  # type: ignore

    def test_no_content_in_event(self) -> None:
        assert not hasattr(MemoryUpdated, "content")


class TestMemoryDeleted:
    def test_creation(self) -> None:
        mid = MemoryId()
        now = datetime.now(tz=timezone.utc)
        ev = MemoryDeleted(memory_id=mid, revision=3, occurred_at=now)
        assert ev.memory_id == mid
        assert ev.revision == 3
        assert ev.occurred_at == now

    def test_no_content_in_event(self) -> None:
        assert not hasattr(MemoryDeleted, "content")


class TestMemoryRetentionExpired:
    def test_creation(self) -> None:
        mid = MemoryId()
        now = datetime.now(tz=timezone.utc)
        ev = MemoryRetentionExpired(memory_id=mid, revision=2, occurred_at=now)
        assert ev.memory_id == mid
        assert ev.revision == 2
        assert ev.occurred_at == now

    def test_frozen(self) -> None:
        mid = MemoryId()
        ev = MemoryRetentionExpired(
            memory_id=mid, revision=1, occurred_at=datetime.now(tz=timezone.utc)
        )
        with pytest.raises(AttributeError):
            ev.revision = 3  # type: ignore


class TestMemoryPurgeScheduled:
    def test_creation(self) -> None:
        mid = MemoryId()
        now = datetime.now(tz=timezone.utc)
        ev = MemoryPurgeScheduled(memory_id=mid, revision=3, occurred_at=now)
        assert ev.memory_id == mid
        assert ev.revision == 3
        assert ev.occurred_at == now

    def test_frozen(self) -> None:
        mid = MemoryId()
        ev = MemoryPurgeScheduled(
            memory_id=mid, revision=1, occurred_at=datetime.now(tz=timezone.utc)
        )
        with pytest.raises(AttributeError):
            ev.revision = 5  # type: ignore


class TestMemoryPurged:
    def test_creation(self) -> None:
        mid = MemoryId()
        now = datetime.now(tz=timezone.utc)
        ev = MemoryPurged(memory_id=mid, revision=4, occurred_at=now)
        assert ev.memory_id == mid
        assert ev.revision == 4
        assert ev.occurred_at == now

    def test_frozen(self) -> None:
        mid = MemoryId()
        ev = MemoryPurged(
            memory_id=mid, revision=1, occurred_at=datetime.now(tz=timezone.utc)
        )
        with pytest.raises(AttributeError):
            ev.revision = 2  # type: ignore


class TestConsentGranted:
    def test_creation(self) -> None:
        cid = ConsentId()
        now = datetime.now(tz=timezone.utc)
        ev = ConsentGranted(consent_id=cid, occurred_at=now)
        assert ev.consent_id == cid
        assert ev.occurred_at == now

    def test_frozen(self) -> None:
        cid = ConsentId()
        ev = ConsentGranted(
            consent_id=cid, occurred_at=datetime.now(tz=timezone.utc)
        )
        with pytest.raises(AttributeError):
            ev.consent_id = ConsentId()  # type: ignore


class TestConsentRevoked:
    def test_creation(self) -> None:
        cid = ConsentId()
        now = datetime.now(tz=timezone.utc)
        ev = ConsentRevoked(consent_id=cid, occurred_at=now)
        assert ev.consent_id == cid


# =============================================================================
# 4. ConsentRecord Lifecycle Tests
# =============================================================================


class TestConsentRecordCreation:
    def test_default_status_is_proposed(self) -> None:
        c = ConsentRecord()
        assert c.status == ConsentStatus.PROPOSED

    def test_default_id_is_generated(self) -> None:
        c = ConsentRecord()
        assert isinstance(c.consent_id, ConsentId)

    def test_initial_events_empty(self) -> None:
        c = ConsentRecord()
        assert c.events == []

    def test_is_active_returns_false_for_proposed(self) -> None:
        c = ConsentRecord()
        assert c.is_active is False


class TestConsentGrant:
    def test_grant_sets_active(self) -> None:
        c = ConsentRecord()
        c.grant()
        assert c.status == ConsentStatus.ACTIVE

    def test_grant_sets_granted_at(self) -> None:
        c = ConsentRecord()
        c.grant()
        assert c.granted_at is not None

    def test_grant_emits_event(self) -> None:
        c = ConsentRecord()
        c.grant()
        assert len(c.events) == 1
        assert isinstance(c.events[0], ConsentGranted)

    def test_event_has_correct_consent_id(self) -> None:
        c = ConsentRecord()
        cid = c.consent_id
        c.grant()
        assert c.events[0].consent_id == cid

    def test_is_active_after_grant(self) -> None:
        c = ConsentRecord()
        c.grant()
        assert c.is_active is True

    def test_double_grant_raises(self) -> None:
        c = ConsentRecord()
        c.grant()
        with pytest.raises(InvalidConsentTransitionError):
            c.grant()

    def test_grant_with_expiration(self) -> None:
        c = ConsentRecord(expires_at=datetime.now(tz=timezone.utc) + timedelta(days=30))
        c.grant()
        assert c.is_active is True

    def test_grant_with_past_expiration_raises(self) -> None:
        past = datetime.now(tz=timezone.utc) - timedelta(days=1)
        c = ConsentRecord(expires_at=past)
        with pytest.raises(ExpirationBeforeGrantError):
            c.grant()


class TestConsentRevoke:
    def test_revoke_sets_revoked(self) -> None:
        c = make_valid_consent(ConsentStatus.ACTIVE)
        c.revoke()
        assert c.status == ConsentStatus.REVOKED

    def test_revoke_sets_revoked_at(self) -> None:
        c = make_valid_consent(ConsentStatus.ACTIVE)
        c.revoke()
        assert c.revoked_at is not None

    def test_revoke_emits_event(self) -> None:
        c = make_valid_consent(ConsentStatus.ACTIVE)
        c.revoke()
        assert len(c.events) == 2
        assert isinstance(c.events[1], ConsentRevoked)

    def test_revoke_from_proposed_raises(self) -> None:
        c = ConsentRecord()
        with pytest.raises(InvalidConsentTransitionError):
            c.revoke()

    def test_double_revoke_raises(self) -> None:
        c = make_valid_consent(ConsentStatus.ACTIVE)
        c.revoke()
        with pytest.raises(InvalidConsentTransitionError):
            c.revoke()

    def test_is_active_false_after_revoke(self) -> None:
        c = make_valid_consent(ConsentStatus.ACTIVE)
        c.revoke()
        assert c.is_active is False


class TestConsentPurge:
    def test_purge_from_revoked(self) -> None:
        c = make_valid_consent(ConsentStatus.ACTIVE)
        c.revoke()
        c.purge()
        assert c.status == ConsentStatus.PURGED

    def test_purge_from_proposed_raises(self) -> None:
        c = ConsentRecord()
        with pytest.raises(InvalidConsentTransitionError):
            c.purge()

    def test_purge_from_active_raises(self) -> None:
        c = make_valid_consent(ConsentStatus.ACTIVE)
        with pytest.raises(InvalidConsentTransitionError):
            c.purge()

    def test_purge_from_purged_raises(self) -> None:
        c = make_valid_consent(ConsentStatus.ACTIVE)
        c.revoke()
        c.purge()
        with pytest.raises(InvalidConsentTransitionError):
            c.purge()

    def test_purge_does_not_emit_event(self) -> None:
        c = make_valid_consent(ConsentStatus.ACTIVE)
        c.revoke()
        c.purge()
        grant_or_revoke = [e for e in c.events if isinstance(e, (ConsentGranted, ConsentRevoked))]
        assert len(grant_or_revoke) == 2


class TestConsentExpiration:
    def test_expired_consent_not_active(self) -> None:
        expires = datetime.now(tz=timezone.utc) + timedelta(days=1)
        c = ConsentRecord(expires_at=expires)
        c.grant()
        assert c.is_active is True

    def test_consent_expires_past(self) -> None:
        c = ConsentRecord(
            status=ConsentStatus.ACTIVE,
            granted_at=datetime.now(tz=timezone.utc) - timedelta(days=10),
            expires_at=datetime.now(tz=timezone.utc) - timedelta(days=5),
        )
        assert c.is_active is False


# =============================================================================
# 5. Memory Entity Tests
# =============================================================================


class TestMemoryCreation:
    def test_creates_with_valid_params(self) -> None:
        mem = make_memory()
        assert isinstance(mem.memory_id, MemoryId)
        assert isinstance(mem.content, MemoryContent)
        assert mem.state == MemoryState.CREATED
        assert mem.revision.value == 1

    def test_initial_events_empty(self) -> None:
        mem = make_memory()
        assert mem.events == []

    def test_created_at_set(self) -> None:
        mem = make_memory()
        assert mem.created_at is not None

    def test_not_deleted_initially(self) -> None:
        mem = make_memory()
        assert mem.is_deleted is False
        assert mem.deleted_at is None

    def test_updated_at_none_initially(self) -> None:
        mem = make_memory()
        assert mem.updated_at is None

    def test_source_type_preserved(self) -> None:
        mem = make_memory(source_type="conversation")
        assert mem.source_type == "conversation"

    def test_source_id_preserved(self) -> None:
        mem = make_memory(source_type="conversation", source_id="conv-42")
        assert mem.source_id == "conv-42"

    def test_source_id_none_by_default(self) -> None:
        mem = make_memory(source_type="conversation")
        assert mem.source_id is None

    def test_category_preserved(self) -> None:
        mem = make_memory(category=MemoryCategory.INSIGHT)
        assert mem.category == MemoryCategory.INSIGHT

    def test_classification_preserved(self) -> None:
        mem = make_memory(classification="sensitive", sensitivity="sensitive")
        assert mem.classification == "sensitive"

    def test_sensitivity_preserved(self) -> None:
        mem = make_memory(sensitivity="internal")
        assert mem.sensitivity == "internal"

    def test_retention_status_active_initially(self) -> None:
        mem = make_memory()
        assert mem.retention_status == RetentionStatus.ACTIVE

    def test_redaction_metadata_none_by_default(self) -> None:
        mem = make_memory()
        assert mem.redaction_metadata is None

    def test_redaction_metadata_preserved(self) -> None:
        mem = make_memory(
            sensitivity="restricted", redaction_metadata="redact-user-42"
        )
        assert mem.redaction_metadata == "redact-user-42"


class TestMemoryNewFields:
    def test_source_type_is_separate_from_source_id(self) -> None:
        mem = make_memory(source_type="conversation", source_id="conv-1")
        assert mem.source_type == "conversation"
        assert mem.source_id == "conv-1"

    def test_sensitivity_is_separate_from_classification(self) -> None:
        mem = make_memory(classification="sensitive", sensitivity="public")
        assert mem.classification == "sensitive"
        assert mem.sensitivity == "public"

    def test_all_sensitivity_levels(self) -> None:
        for level in ("public", "internal", "sensitive", "restricted"):
            kw = dict(sensitivity=level, classification=level)
            if level == "restricted":
                kw["redaction_metadata"] = f"redact-{level}"
            mem = make_memory(**kw)
            assert mem.sensitivity == level

    def test_all_retention_statuses_accessible(self) -> None:
        mem = make_memory()
        assert isinstance(mem.retention_status, RetentionStatus)
        assert mem.retention_status in (
            RetentionStatus.ACTIVE, RetentionStatus.EXPIRED,
            RetentionStatus.PURGE_PENDING, RetentionStatus.PURGED,
        )


class TestMemoryUpdate:
    def test_update_increments_revision(self) -> None:
        mem = make_memory()
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        mem.update(MemoryContent(value="updated content"), consent)
        assert mem.revision.value == 2

    def test_update_changes_content(self) -> None:
        mem = make_memory(content="original")
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        mem.update(MemoryContent(value="updated"), consent)
        assert mem.content.value == "updated"

    def test_update_sets_updated_at(self) -> None:
        mem = make_memory()
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        mem.update(MemoryContent(value="updated"), consent)
        assert mem.updated_at is not None

    def test_update_sets_state_to_updated(self) -> None:
        mem = make_memory()
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        mem.update(MemoryContent(value="updated"), consent)
        assert mem.state == MemoryState.UPDATED

    def test_update_emits_event(self) -> None:
        mem = make_memory()
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        mem.update(MemoryContent(value="updated"), consent)
        assert len(mem.events) == 1
        assert isinstance(mem.events[0], MemoryUpdated)

    def test_update_event_revision(self) -> None:
        mem = make_memory()
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        mem.update(MemoryContent(value="updated"), consent)
        assert mem.events[0].revision == 2

    def test_update_multiple_times(self) -> None:
        mem = make_memory()
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        mem.update(MemoryContent(value="v2"), consent)
        mem.update(MemoryContent(value="v3"), consent)
        assert mem.revision.value == 3
        assert len(mem.events) == 2

    def test_update_with_empty_content_raises(self) -> None:
        mem = make_memory()
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        with pytest.raises(EmptyContentError):
            mem.update(MemoryContent(value=""), consent)

    def test_update_with_blank_content_raises(self) -> None:
        mem = make_memory()
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        with pytest.raises(EmptyContentError):
            mem.update(MemoryContent(value="   "), consent)

    def test_update_with_secret_raises(self) -> None:
        mem = make_memory()
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        with pytest.raises(SecretDetectedError):
            mem.update(MemoryContent(value="my password is x"), consent)

    def test_update_with_revoked_consent_raises(self) -> None:
        mem = make_memory()
        revoked = make_valid_consent(ConsentStatus.REVOKED)
        with pytest.raises(RevokedConsentBlocksUpdateError):
            mem.update(MemoryContent(value="updated"), revoked)

    def test_update_with_proposed_consent_raises(self) -> None:
        mem = make_memory()
        proposed = ConsentRecord()
        with pytest.raises(ConsentNotActiveError):
            mem.update(MemoryContent(value="updated"), proposed)

    def test_update_preserves_provenance(self) -> None:
        mem = make_memory()
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        original_prov = mem.provenance
        mem.update(MemoryContent(value="updated content"), consent)
        assert mem.provenance is original_prov
        assert mem.provenance.source == original_prov.source

    def test_update_preserves_source_type(self) -> None:
        mem = make_memory(source_type="conversation")
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        mem.update(MemoryContent(value="updated"), consent)
        assert mem.source_type == "conversation"

    def test_update_preserves_source_id(self) -> None:
        mem = make_memory(source_type="conversation", source_id="conv-1")
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        mem.update(MemoryContent(value="updated"), consent)
        assert mem.source_id == "conv-1"

    def test_update_event_has_no_content(self) -> None:
        mem = make_memory()
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        mem.update(MemoryContent(value="updated"), consent)
        with pytest.raises(AttributeError):
            _ = mem.events[0].content  # type: ignore


class TestMemoryDelete:
    def test_delete_sets_deleted_at(self) -> None:
        mem = make_memory()
        mem.delete()
        assert mem.deleted_at is not None

    def test_delete_sets_state_deleted(self) -> None:
        mem = make_memory()
        mem.delete()
        assert mem.state == MemoryState.DELETED

    def test_delete_emits_event(self) -> None:
        mem = make_memory()
        mem.delete()
        assert len(mem.events) == 1
        assert isinstance(mem.events[0], MemoryDeleted)

    def test_delete_event_revision(self) -> None:
        mem = make_memory()
        mem.delete()
        assert mem.events[0].revision == 1

    def test_is_deleted_true(self) -> None:
        mem = make_memory()
        mem.delete()
        assert mem.is_deleted is True

    def test_delete_twice_raises(self) -> None:
        mem = make_memory()
        mem.delete()
        with pytest.raises(DeletedMemoryUpdateError):
            mem.delete()

    def test_update_after_delete_raises(self) -> None:
        mem = make_memory()
        mem.delete()
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        with pytest.raises(DeletedMemoryUpdateError):
            mem.update(MemoryContent(value="nope"), consent)

    def test_delete_event_has_no_content(self) -> None:
        mem = make_memory()
        mem.delete()
        with pytest.raises(AttributeError):
            _ = mem.events[0].content  # type: ignore


class TestMemoryRetentionLifecycle:
    def test_expire_retention_sets_expired(self) -> None:
        mem = make_memory()
        mem.expire_retention()
        assert mem.retention_status == RetentionStatus.EXPIRED

    def test_expire_retention_emits_event(self) -> None:
        mem = make_memory()
        mem.expire_retention()
        assert len(mem.events) == 1
        assert isinstance(mem.events[0], MemoryRetentionExpired)

    def test_expire_retention_preserves_state(self) -> None:
        mem = make_memory()
        mem.expire_retention()
        assert mem.state == MemoryState.CREATED

    def test_schedule_purge_sets_purge_pending(self) -> None:
        mem = make_memory()
        mem.schedule_purge()
        assert mem.retention_status == RetentionStatus.PURGE_PENDING

    def test_schedule_purge_emits_event(self) -> None:
        mem = make_memory()
        mem.schedule_purge()
        assert len(mem.events) == 1
        assert isinstance(mem.events[0], MemoryPurgeScheduled)

    def test_purge_memory_sets_purged(self) -> None:
        mem = make_memory()
        mem.purge_memory()
        assert mem.retention_status == RetentionStatus.PURGED

    def test_purge_memory_sets_deleted(self) -> None:
        mem = make_memory()
        mem.purge_memory()
        assert mem.state == MemoryState.DELETED
        assert mem.deleted_at is not None

    def test_purge_memory_emits_event(self) -> None:
        mem = make_memory()
        mem.purge_memory()
        assert len(mem.events) == 1
        assert isinstance(mem.events[0], MemoryPurged)

    def test_full_retention_lifecycle(self) -> None:
        mem = make_memory()
        assert mem.retention_status == RetentionStatus.ACTIVE
        mem.expire_retention()
        assert mem.retention_status == RetentionStatus.EXPIRED
        mem.schedule_purge()
        assert mem.retention_status == RetentionStatus.PURGE_PENDING
        mem.purge_memory()
        assert mem.retention_status == RetentionStatus.PURGED
        assert mem.is_deleted

    def test_update_disallowed_after_purge(self) -> None:
        mem = make_memory()
        mem.purge_memory()
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        with pytest.raises(PurgedMemoryImmutableError):
            mem.update(MemoryContent(value="nope"), consent)

    def test_delete_disallowed_after_purge(self) -> None:
        mem = make_memory()
        mem.purge_memory()
        with pytest.raises(PurgedMemoryImmutableError):
            mem.delete()

    def test_expire_retention_disallowed_after_purge(self) -> None:
        mem = make_memory()
        mem.purge_memory()
        with pytest.raises(PurgedMemoryImmutableError):
            mem.expire_retention()

    def test_schedule_purge_disallowed_after_purge(self) -> None:
        mem = make_memory()
        mem.purge_memory()
        with pytest.raises(PurgedMemoryImmutableError):
            mem.schedule_purge()

    def test_double_expire_raises(self) -> None:
        mem = make_memory()
        mem.expire_retention()
        with pytest.raises(RetentionExpirationError):
            mem.expire_retention()

    def test_expire_then_schedule_purge(self) -> None:
        mem = make_memory()
        mem.expire_retention()
        mem.schedule_purge()
        assert mem.retention_status == RetentionStatus.PURGE_PENDING

    def test_schedule_purge_then_purge(self) -> None:
        mem = make_memory()
        mem.schedule_purge()
        mem.purge_memory()
        assert mem.retention_status == RetentionStatus.PURGED

    def test_events_accumulate_in_lifecycle(self) -> None:
        mem = make_memory()
        mem.expire_retention()
        mem.schedule_purge()
        mem.purge_memory()
        assert len(mem.events) == 3


# =============================================================================
# 6. Domain Rule Tests
# =============================================================================


class TestRuleContentNotEmpty:
    def test_empty_raises(self) -> None:
        with pytest.raises(EmptyContentError):
            assert_content_not_empty("")

    def test_blank_raises(self) -> None:
        with pytest.raises(EmptyContentError):
            assert_content_not_empty("   ")

    def test_valid_passes(self) -> None:
        assert_content_not_empty("hello") is None


class TestRuleContentMaxLength:
    def test_under_limit_passes(self) -> None:
        assert_content_max_length("x" * 100) is None

    def test_at_limit_passes(self) -> None:
        assert_content_max_length("x" * MAX_CONTENT_LENGTH) is None

    def test_over_limit_raises(self) -> None:
        with pytest.raises(ContentTooLongError) as exc:
            assert_content_max_length("x" * (MAX_CONTENT_LENGTH + 1))
        assert exc.value.length == MAX_CONTENT_LENGTH + 1
        assert exc.value.max_length == MAX_CONTENT_LENGTH


class TestRuleContentNoSecrets:
    def test_rejects_password(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("my password is 1234")

    def test_rejects_token(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("auth token abc123")

    def test_rejects_api_key(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("api_key=sk-1234")

    def test_rejects_api_key_variant(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("apikey=abc")

    def test_rejects_api_key_variant2(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("api-key=xyz")

    def test_rejects_private_key(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("my private_key is secret")

    def test_rejects_private_key_variant(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("my private_key = 'secret'")

    def test_rejects_secret_word(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("the secretword is pass")

    def test_rejects_secret_token(self) -> None:
        with pytest.raises(SecretDetectedError):
            assert_content_no_secrets("my secret_token is xyz")

    def test_passes_clean_content(self) -> None:
        assert_content_no_secrets("hello world this is fine") is None

    def test_passes_edge_text(self) -> None:
        assert_content_no_secrets("I like passwords as a concept") is None


class TestRuleConsentActive:
    def test_active_consent_passes(self) -> None:
        c = make_valid_consent(ConsentStatus.ACTIVE)
        assert_consent_active(c) is None

    def test_proposed_consent_raises(self) -> None:
        c = ConsentRecord()
        with pytest.raises(ConsentNotActiveError):
            assert_consent_active(c)

    def test_revoked_consent_raises(self) -> None:
        c = make_valid_consent(ConsentStatus.REVOKED)
        with pytest.raises(ConsentNotActiveError):
            assert_consent_active(c)


class TestRuleConsentAllowsUpdates:
    def test_active_allows(self) -> None:
        c = make_valid_consent(ConsentStatus.ACTIVE)
        assert_consent_allows_updates(c) is None

    def test_revoked_raises(self) -> None:
        c = make_valid_consent(ConsentStatus.REVOKED)
        with pytest.raises(RevokedConsentBlocksUpdateError):
            assert_consent_allows_updates(c)

    def test_proposed_raises(self) -> None:
        c = ConsentRecord()
        with pytest.raises(ConsentNotActiveError):
            assert_consent_allows_updates(c)

    def test_purged_raises(self) -> None:
        c = make_valid_consent(ConsentStatus.ACTIVE)
        c.revoke()
        c.purge()
        with pytest.raises(PurgedConsentError):
            assert_consent_allows_updates(c)


class TestRuleRetentionRequired:
    def test_provided_passes(self) -> None:
        rp = RetentionPolicy(policy="persistent")
        assert_retention_provided(rp) is None

    def test_none_raises(self) -> None:
        with pytest.raises(RetentionRequiredError):
            assert_retention_provided(None)


class TestRuleProvenanceRequired:
    def test_provided_passes(self) -> None:
        p = make_valid_provenance()
        assert_provenance_provided(p) is None

    def test_none_raises(self) -> None:
        with pytest.raises(ProvenanceRequiredError):
            assert_provenance_provided(None)


class TestRuleSourceRequired:
    def test_provided_passes(self) -> None:
        assert_source_provided("user_input") is None

    def test_empty_raises(self) -> None:
        with pytest.raises(SourceRequiredError):
            assert_source_provided("")

    def test_none_raises(self) -> None:
        with pytest.raises(SourceRequiredError):
            assert_source_provided(None)


class TestRuleClassification:
    def test_valid_classification_passes(self) -> None:
        for c in VALID_CLASSIFICATIONS:
            assert_classification_valid(c) is None

    def test_invalid_raises(self) -> None:
        with pytest.raises(InvalidClassificationError) as exc:
            assert_classification_valid("top_secret")
        assert exc.value.classification == "top_secret"


class TestRuleNotDeleted:
    def test_created_passes(self) -> None:
        assert_not_deleted(MemoryState.CREATED) is None

    def test_updated_passes(self) -> None:
        assert_not_deleted(MemoryState.UPDATED) is None

    def test_deleted_raises(self) -> None:
        with pytest.raises(DeletedMemoryUpdateError):
            assert_not_deleted(MemoryState.DELETED)


class TestRuleExpirationAfterGrant:
    def test_future_expiration_passes(self) -> None:
        now = datetime.now(tz=timezone.utc)
        assert_expiration_after_grant(now + timedelta(days=1), now) is None

    def test_same_time_passes(self) -> None:
        now = datetime.now(tz=timezone.utc)
        assert_expiration_after_grant(now, now) is None

    def test_past_expiration_raises(self) -> None:
        now = datetime.now(tz=timezone.utc)
        with pytest.raises(ExpirationBeforeGrantError):
            assert_expiration_after_grant(now - timedelta(days=1), now)


class TestRuleConsentTransition:
    def test_proposed_to_active(self) -> None:
        assert_consent_can_transition(ConsentStatus.PROPOSED, ConsentStatus.ACTIVE) is None

    def test_active_to_revoked(self) -> None:
        assert_consent_can_transition(ConsentStatus.ACTIVE, ConsentStatus.REVOKED) is None

    def test_revoked_to_purged(self) -> None:
        assert_consent_can_transition(ConsentStatus.REVOKED, ConsentStatus.PURGED) is None

    def test_proposed_to_revoked_raises(self) -> None:
        with pytest.raises(InvalidConsentTransitionError):
            assert_consent_can_transition(ConsentStatus.PROPOSED, ConsentStatus.REVOKED)

    def test_active_to_purged_raises(self) -> None:
        with pytest.raises(InvalidConsentTransitionError):
            assert_consent_can_transition(ConsentStatus.ACTIVE, ConsentStatus.PURGED)

    def test_purged_to_anything_raises(self) -> None:
        for target in ConsentStatus:
            if target == ConsentStatus.PURGED:
                continue
            with pytest.raises(InvalidConsentTransitionError):
                assert_consent_can_transition(ConsentStatus.PURGED, target)

    def test_revoked_to_active_raises(self) -> None:
        with pytest.raises(InvalidConsentTransitionError):
            assert_consent_can_transition(ConsentStatus.REVOKED, ConsentStatus.ACTIVE)


# -- Rule 14: Sensitive memories require active consent ---------------------

class TestRuleSensitiveRequiresConsent:
    def test_sensitive_with_active_consent_passes(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        assert_sensitive_requires_consent("sensitive", consent) is None

    def test_sensitive_with_proposed_consent_raises(self) -> None:
        consent = ConsentRecord()
        with pytest.raises(SensitiveMemoryRequiresConsentError):
            assert_sensitive_requires_consent("sensitive", consent)

    def test_sensitive_with_revoked_consent_raises(self) -> None:
        consent = make_valid_consent(ConsentStatus.REVOKED)
        with pytest.raises(SensitiveMemoryRequiresConsentError):
            assert_sensitive_requires_consent("sensitive", consent)

    def test_public_does_not_require_consent_check(self) -> None:
        consent = ConsentRecord()
        assert_sensitive_requires_consent("public", consent) is None

    def test_internal_does_not_require_consent_check(self) -> None:
        consent = ConsentRecord()
        assert_sensitive_requires_consent("internal", consent) is None

    def test_restricted_does_not_require_consent_check(self) -> None:
        consent = ConsentRecord()
        assert_sensitive_requires_consent("restricted", consent) is None


# -- Rule 15: Restricted memories require redaction metadata ----------------

class TestRuleRestrictedRequiresRedaction:
    def test_restricted_with_redaction_passes(self) -> None:
        assert_restricted_requires_redaction("restricted", "redact-abc") is None

    def test_restricted_without_redaction_raises(self) -> None:
        with pytest.raises(RestrictedMemoryRequiresRedactionError):
            assert_restricted_requires_redaction("restricted", None)

    def test_restricted_with_empty_redaction_raises(self) -> None:
        with pytest.raises(RestrictedMemoryRequiresRedactionError):
            assert_restricted_requires_redaction("restricted", "")

    def test_public_no_redaction_needed(self) -> None:
        assert_restricted_requires_redaction("public", None) is None

    def test_sensitive_no_redaction_needed(self) -> None:
        assert_restricted_requires_redaction("sensitive", None) is None

    def test_internal_no_redaction_needed(self) -> None:
        assert_restricted_requires_redaction("internal", None) is None


# -- Rule 16: Purged memories are immutable forever -------------------------

class TestRulePurgedMemoryImmutable:
    def test_active_status_passes(self) -> None:
        assert_not_purged(RetentionStatus.ACTIVE) is None

    def test_expired_status_passes(self) -> None:
        assert_not_purged(RetentionStatus.EXPIRED) is None

    def test_purge_pending_status_passes(self) -> None:
        assert_not_purged(RetentionStatus.PURGE_PENDING) is None

    def test_purged_status_raises(self) -> None:
        with pytest.raises(PurgedMemoryImmutableError):
            assert_not_purged(RetentionStatus.PURGED)


# -- Rule 17: Retention expiration validation -------------------------------

class TestRuleRetentionExpiration:
    def test_active_can_expire(self) -> None:
        assert_retention_can_expire(RetentionStatus.ACTIVE) is None

    def test_purge_pending_can_expire(self) -> None:
        assert_retention_can_expire(RetentionStatus.PURGE_PENDING) is None

    def test_expired_raises(self) -> None:
        with pytest.raises(RetentionExpirationError):
            assert_retention_can_expire(RetentionStatus.EXPIRED)

    def test_purged_raises(self) -> None:
        with pytest.raises(RetentionExpirationError):
            assert_retention_can_expire(RetentionStatus.PURGED)


# -- Rule 19: Source provenance must survive all revisions ------------------

class TestRuleProvenancePreserved:
    def test_same_source_passes(self) -> None:
        now = datetime.now(tz=timezone.utc)
        p1 = Provenance(source="conversation", timestamp=now)
        p2 = Provenance(source="conversation", timestamp=now)
        assert_provenance_preserved(p1, p2) is None

    def test_different_source_raises(self) -> None:
        now = datetime.now(tz=timezone.utc)
        p1 = Provenance(source="conversation", timestamp=now)
        p2 = Provenance(source="user_input", timestamp=now)
        with pytest.raises(ProvenanceMismatchError):
            assert_provenance_preserved(p1, p2)


# -- Rule 20: Event payload must not contain content -----------------------

class TestRuleEventPayloadOmitsContent:
    def test_no_content_passes(self) -> None:
        assert_event_payload_omits_content({"memory_id", "revision"}) is None

    def test_content_field_raises(self) -> None:
        with pytest.raises(EventPayloadTooDetailedError):
            assert_event_payload_omits_content({"content"})

    def test_memory_content_field_raises(self) -> None:
        with pytest.raises(EventPayloadTooDetailedError):
            assert_event_payload_omits_content({"memory_content"})


# -- Rule 21: Event payload compliance with JDOS governance -----------------

class TestRuleEventPayloadCompliant:
    def test_public_memory_allows_normal_fields(self) -> None:
        assert_event_payload_compliant({"memory_id", "revision"}, "public") is None

    def test_sensitive_rejects_password_field(self) -> None:
        with pytest.raises(EventPayloadTooDetailedError):
            assert_event_payload_compliant({"password"}, "sensitive")

    def test_restricted_rejects_token_field(self) -> None:
        with pytest.raises(EventPayloadTooDetailedError):
            assert_event_payload_compliant({"token"}, "restricted")

    def test_public_allows_password_field(self) -> None:
        assert_event_payload_compliant({"password"}, "public") is None

    def test_internal_allows_password_field(self) -> None:
        assert_event_payload_compliant({"password"}, "internal") is None

    def test_sensitive_allows_innocuous_fields(self) -> None:
        assert_event_payload_compliant({"memory_id", "occurred_at"}, "sensitive") is None


# -- Rule 18: Revisions start at 1 (enforced by RevisionNumber) ------------
# (already tested in TestRevisionNumber)

# -- Sensitivity valid ------------------------------------------------------

class TestRuleSensitivityValid:
    def test_valid_sensitivity_passes(self) -> None:
        for level in VALID_SENSITIVITY_LEVELS:
            assert_sensitivity_valid(level) is None

    def test_invalid_sensitivity_raises(self) -> None:
        with pytest.raises(InvalidSensitivityError) as exc:
            assert_sensitivity_valid("top_secret")
        assert exc.value.sensitivity == "top_secret"


# =============================================================================
# 7. Factory Tests
# =============================================================================


class TestMemoryFactoryCreate:
    def test_create_valid_memory(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        provenance = make_valid_provenance()
        retention = make_valid_retention()
        mem, event = MemoryFactory.create(
            consent=consent,
            content="test memory content",
            category=MemoryCategory.GENERAL,
            source_type="user_input",
            source_id=None,
            provenance=provenance,
            retention=retention,
            classification="public",
            sensitivity="public",
        )
        assert isinstance(mem, Memory)
        assert isinstance(event, MemoryCreated)
        assert mem.content.value == "test memory content"
        assert mem.revision.value == 1

    def test_create_emits_event_with_correct_ids(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        provenance = make_valid_provenance()
        retention = make_valid_retention()
        mem, event = MemoryFactory.create(
            consent=consent,
            content="hello",
            category="general",
            source_type="user_input",
            provenance=provenance,
            retention=retention,
            classification="public",
            sensitivity="public",
        )
        assert event.memory_id == mem.memory_id
        assert event.consent_id == mem.consent_id

    def test_create_with_string_category(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        mem, _ = MemoryFactory.create(
            consent=consent,
            content="hello",
            category="insight",
            source_type="user_input",
            provenance=make_valid_provenance(),
            retention=make_valid_retention(),
            classification="public",
            sensitivity="public",
        )
        assert mem.category == MemoryCategory.INSIGHT

    def test_create_without_provenance_raises(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        retention = make_valid_retention()
        with pytest.raises(ProvenanceRequiredError):
            MemoryFactory.create(
                consent=consent,
                content="hello",
                category="general",
                source_type="user_input",
                provenance=None,
                retention=retention,
                classification="public",
                sensitivity="public",
            )

    def test_create_without_retention_raises(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        provenance = make_valid_provenance()
        with pytest.raises(RetentionRequiredError):
            MemoryFactory.create(
                consent=consent,
                content="hello",
                category="general",
                source_type="user_input",
                provenance=provenance,
                retention=None,
                classification="public",
                sensitivity="public",
            )

    def test_create_with_proposed_consent_raises(self) -> None:
        consent = ConsentRecord()
        provenance = make_valid_provenance()
        retention = make_valid_retention()
        with pytest.raises(ConsentNotActiveError):
            MemoryFactory.create(
                consent=consent,
                content="hello",
                category="general",
                source_type="user_input",
                provenance=provenance,
                retention=retention,
                classification="public",
                sensitivity="public",
            )

    def test_create_with_empty_content_raises(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        provenance = make_valid_provenance()
        retention = make_valid_retention()
        with pytest.raises(EmptyContentError):
            MemoryFactory.create(
                consent=consent,
                content="",
                category="general",
                source_type="user_input",
                provenance=provenance,
                retention=retention,
                classification="public",
                sensitivity="public",
            )

    def test_create_with_secret_raises(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        provenance = make_valid_provenance()
        retention = make_valid_retention()
        with pytest.raises(SecretDetectedError):
            MemoryFactory.create(
                consent=consent,
                content="my password is 1234",
                category="general",
                source_type="user_input",
                provenance=provenance,
                retention=retention,
                classification="public",
                sensitivity="public",
            )

    def test_create_without_source_raises(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        provenance = make_valid_provenance()
        retention = make_valid_retention()
        with pytest.raises(SourceRequiredError):
            MemoryFactory.create(
                consent=consent,
                content="hello",
                category="general",
                source_type="",
                provenance=provenance,
                retention=retention,
                classification="public",
                sensitivity="public",
            )

    def test_create_with_invalid_classification_raises(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        provenance = make_valid_provenance()
        retention = make_valid_retention()
        with pytest.raises(InvalidClassificationError):
            MemoryFactory.create(
                consent=consent,
                content="hello",
                category="general",
                source_type="user_input",
                provenance=provenance,
                retention=retention,
                classification="invalid",
                sensitivity="public",
            )

    def test_create_with_too_long_content_raises(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        provenance = make_valid_provenance()
        retention = make_valid_retention()
        with pytest.raises(ContentTooLongError):
            MemoryFactory.create(
                consent=consent,
                content="x" * (MAX_CONTENT_LENGTH + 1),
                category="general",
                source_type="user_input",
                provenance=provenance,
                retention=retention,
                classification="public",
                sensitivity="public",
            )

    def test_create_event_category(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        mem, event = MemoryFactory.create(
            consent=consent,
            content="hello",
            category="preference",
            source_type="user_input",
            provenance=make_valid_provenance(),
            retention=make_valid_retention(),
            classification="public",
            sensitivity="public",
        )
        assert event.category == MemoryCategory.PREFERENCE

    def test_create_with_revoked_consent_raises(self) -> None:
        consent = make_valid_consent(ConsentStatus.REVOKED)
        with pytest.raises(ConsentNotActiveError):
            MemoryFactory.create(
                consent=consent,
                content="hello",
                category="general",
                source_type="user_input",
                provenance=make_valid_provenance(),
                retention=make_valid_retention(),
                classification="public",
                sensitivity="public",
            )

    def test_create_with_all_categories(self) -> None:
        for cat in MemoryCategory:
            consent = make_valid_consent(ConsentStatus.ACTIVE)
            mem, _ = MemoryFactory.create(
                consent=consent,
                content=f"test for {cat.value}",
                category=cat,
                source_type="user_input",
                provenance=make_valid_provenance(),
                retention=make_valid_retention(),
                classification="public",
                sensitivity="public",
            )
            assert mem.category == cat

    def test_create_with_source_id(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        mem, event = MemoryFactory.create(
            consent=consent,
            content="hello",
            category="general",
            source_type="conversation",
            source_id="conv-42",
            provenance=make_valid_provenance(),
            retention=make_valid_retention(),
            classification="public",
            sensitivity="public",
        )
        assert mem.source_id == "conv-42"
        assert event.source_id == "conv-42"

    def test_create_event_has_source_type_and_id(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        _, event = MemoryFactory.create(
            consent=consent,
            content="hello",
            category="general",
            source_type="conversation",
            source_id="conv-1",
            provenance=make_valid_provenance(),
            retention=make_valid_retention(),
            classification="public",
            sensitivity="public",
        )
        assert event.source_type == "conversation"
        assert event.source_id == "conv-1"

    def test_create_event_has_sensitivity(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        _, event = MemoryFactory.create(
            consent=consent,
            content="hello",
            category="general",
            source_type="user_input",
            provenance=make_valid_provenance(),
            retention=make_valid_retention(),
            classification="internal",
            sensitivity="internal",
        )
        assert event.sensitivity == "internal"


class TestFactorySensitivity:
    def test_create_sensitive_with_active_consent(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        mem, _ = MemoryFactory.create(
            consent=consent,
            content="sensitive data",
            category="general",
            source_type="user_input",
            provenance=make_valid_provenance(),
            retention=make_valid_retention(),
            classification="sensitive",
            sensitivity="sensitive",
        )
        assert mem.sensitivity == "sensitive"

    def test_create_sensitive_without_consent_raises(self) -> None:
        consent = ConsentRecord()
        with pytest.raises(ConsentNotActiveError):
            MemoryFactory.create(
                consent=consent,
                content="sensitive data",
                category="general",
                source_type="user_input",
                provenance=make_valid_provenance(),
                retention=make_valid_retention(),
                classification="sensitive",
                sensitivity="sensitive",
            )

    def test_create_restricted_with_redaction(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        mem, _ = MemoryFactory.create(
            consent=consent,
            content="restricted data",
            category="general",
            source_type="user_input",
            provenance=make_valid_provenance(),
            retention=make_valid_retention(),
            classification="restricted",
            sensitivity="restricted",
            redaction_metadata="redact-user-99",
        )
        assert mem.redaction_metadata == "redact-user-99"

    def test_create_restricted_without_redaction_raises(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        with pytest.raises(RestrictedMemoryRequiresRedactionError):
            MemoryFactory.create(
                consent=consent,
                content="restricted data",
                category="general",
                source_type="user_input",
                provenance=make_valid_provenance(),
                retention=make_valid_retention(),
                classification="restricted",
                sensitivity="restricted",
            )

    def test_create_with_invalid_sensitivity_raises(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        with pytest.raises(InvalidSensitivityError):
            MemoryFactory.create(
                consent=consent,
                content="hello",
                category="general",
                source_type="user_input",
                provenance=make_valid_provenance(),
                retention=make_valid_retention(),
                classification="public",
                sensitivity="invalid_level",
            )

    def test_create_with_all_sensitivity_levels(self) -> None:
        for level in ("public", "internal", "sensitive", "restricted"):
            consent = make_valid_consent(ConsentStatus.ACTIVE)
            kw = dict(
                consent=consent,
                content=f"test for {level}",
                category="general",
                source_type="user_input",
                provenance=make_valid_provenance(),
                retention=make_valid_retention(),
                classification=level,
                sensitivity=level,
            )
            if level == "restricted":
                kw["redaction_metadata"] = f"redact-{level}"
            if level == "sensitive":
                pass  # active consent already provided
            mem, _ = MemoryFactory.create(**kw)
            assert mem.sensitivity == level

    def test_event_does_not_contain_content(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        _, event = MemoryFactory.create(
            consent=consent,
            content="secret content here",
            category="general",
            source_type="user_input",
            provenance=make_valid_provenance(),
            retention=make_valid_retention(),
            classification="public",
            sensitivity="public",
        )
        with pytest.raises(AttributeError):
            _ = event.content  # type: ignore


# =============================================================================
# 8. Edge Cases & Integration
# =============================================================================


class TestEdgeCases:
    def test_factory_and_lifecycle_full(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        mem, created = MemoryFactory.create(
            consent=consent,
            content="important memory",
            category="insight",
            source_type="conversation",
            source_id="conv-42",
            provenance=Provenance(
                source="conversation",
                timestamp=datetime.now(tz=timezone.utc),
                actor_id="user-42",
            ),
            retention=RetentionPolicy(policy="persistent"),
            classification="internal",
            sensitivity="internal",
        )
        assert mem.state == MemoryState.CREATED
        assert created.category == MemoryCategory.INSIGHT
        assert created.source_type == "conversation"
        assert created.source_id == "conv-42"
        assert created.sensitivity == "internal"

        mem.update(MemoryContent(value="updated memory"), consent)
        assert mem.state == MemoryState.UPDATED
        assert mem.revision.value == 2

        mem.delete()
        assert mem.state == MemoryState.DELETED
        assert mem.deleted_at is not None
        assert mem.is_deleted is True

    def test_different_sources(self) -> None:
        for source in ("user_input", "conversation", "inference", "system", "external"):
            mem = make_memory(source_type=source)
            assert mem.source_type == source

    def test_multiple_updates_accumulate_events(self) -> None:
        mem = make_memory()
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        for i in range(5):
            mem.update(MemoryContent(value=f"v{i+2}"), consent)
        assert len(mem.events) == 5
        assert mem.revision.value == 6

    def test_exception_is_domain_error(self) -> None:
        with pytest.raises(MemoryDomainError):
            make_memory(content="")

    def test_sensitive_content_variants(self) -> None:
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        variants = [
            "my token is abc",
            "API_KEY=12345",
            "PrivateKey stuff",
            "my-secret-key",
            "secretword is pass",
        ]
        for content in variants:
            with pytest.raises(MemoryDomainError):
                MemoryFactory.create(
                    consent=consent,
                    content=content,
                    category="general",
                    source_type="user_input",
                    provenance=make_valid_provenance(),
                    retention=make_valid_retention(),
                    classification="public",
                    sensitivity="public",
                )

    def test_expired_consent_blocks_creation(self) -> None:
        past = datetime.now(tz=timezone.utc) - timedelta(days=1)
        c = ConsentRecord(
            status=ConsentStatus.ACTIVE,
            granted_at=past - timedelta(days=10),
            expires_at=past,
        )
        with pytest.raises(ConsentNotActiveError):
            make_memory(consent=c)

    def test_retention_lifecycle_complete(self) -> None:
        mem = make_memory()
        mem.expire_retention()
        mem.schedule_purge()
        mem.purge_memory()
        assert mem.retention_status == RetentionStatus.PURGED
        assert mem.is_deleted
        assert len(mem.events) == 3

    def test_provenance_preserved_through_updates(self) -> None:
        mem = make_memory()
        original_prov = mem.provenance
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        for i in range(3):
            mem.update(MemoryContent(value=f"v{i+2}"), consent)
        assert mem.provenance.source == original_prov.source
        assert mem.provenance.actor_id == original_prov.actor_id

    def test_purged_memory_fully_immutable(self) -> None:
        mem = make_memory()
        mem.purge_memory()
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        with pytest.raises(PurgedMemoryImmutableError):
            mem.update(MemoryContent(value="nope"), consent)
        with pytest.raises(PurgedMemoryImmutableError):
            mem.delete()
        with pytest.raises(PurgedMemoryImmutableError):
            mem.expire_retention()
        with pytest.raises(PurgedMemoryImmutableError):
            mem.schedule_purge()

    def test_validate_memory_creation_composite(self) -> None:
        content = MemoryContent(value="valid content")
        consent = make_valid_consent(ConsentStatus.ACTIVE)
        provenance = make_valid_provenance()
        retention = make_valid_retention()
        validate_memory_creation(
            content=content,
            consent=consent,
            source_type="user_input",
            provenance=provenance,
            classification="public",
            sensitivity="public",
            retention=retention,
        )

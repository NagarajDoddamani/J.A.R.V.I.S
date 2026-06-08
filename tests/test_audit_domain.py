from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.audit.domain.exceptions import (
    AuditEntryError,
    InvalidActionError,
    InvalidActorRefError,
    InvalidChainNameError,
    InvalidClassificationError,
    InvalidCorrelationIdError,
    InvalidEntryIndexError,
    InvalidLifecycleTransitionError,
    InvalidPolicyDecisionError,
    InvalidResultError,
    RestrictedClassificationRequiresReason,
    SensitiveContentInAuditEntry,
)
from backend.audit.domain.factory import AuditEntryFactory
from backend.audit.domain.hash_chain import ChainLink, compute_entry_hash, verify_chain_link
from backend.audit.domain.model import (
    AuditChainHead,
    AuditEntry,
    AuditEntryId,
    AuditEntryRecorded,
    AuditEntryState,
    EntryHash,
    EntryIndex,
    OccurredAt,
    Result,
    TargetRef,
)
from backend.audit.domain.rules import (
    assert_action_not_empty,
    assert_actor_ref_valid,
    assert_chain_name_not_empty,
    assert_classification_valid,
    assert_content_minimized,
    assert_correlation_id_not_empty,
    assert_entry_index_sequential,
    assert_lifecycle_transition_valid,
    assert_policy_decision_valid,
    assert_restricted_has_reason,
    assert_result_not_empty,
)

# ---------------------------------------------------------------------------
# Value Object Tests
# ---------------------------------------------------------------------------


class TestAuditEntryId:
    def test_uuid_generation(self) -> None:
        entry_id = AuditEntryId()
        assert isinstance(entry_id.value, UUID)
        assert str(entry_id) == str(entry_id.value)

    def test_unique_ids(self) -> None:
        assert AuditEntryId().value != AuditEntryId().value


class TestEntryHash:
    def test_from_hex_roundtrip(self) -> None:
        raw = b"\x00" * 32
        h = EntryHash(value=raw)
        assert h.hex() == "00" * 32
        assert EntryHash.from_hex(h.hex()) == h

    def test_equality(self) -> None:
        raw = b"\x01" * 32
        assert EntryHash(value=raw) == EntryHash(value=raw)
        assert EntryHash(value=raw) != EntryHash(value=b"\x02" * 32)

    def test_hashable(self) -> None:
        s = {EntryHash(value=b"\x01" * 32)}
        s.add(EntryHash(value=b"\x01" * 32))
        assert len(s) == 1


class TestEntryIndex:
    def test_non_negative(self) -> None:
        EntryIndex(value=0)
        EntryIndex(value=1)
        with pytest.raises(ValueError, match=">= 0"):
            EntryIndex(value=-1)

    def test_next(self) -> None:
        assert EntryIndex(value=0).next() == EntryIndex(value=1)
        assert EntryIndex(value=42).next() == EntryIndex(value=43)


class TestOccurredAt:
    def test_utc_default(self) -> None:
        dt = datetime.now(tz=timezone.utc)
        oa = OccurredAt(value=dt)
        assert oa.value.tzinfo is not None

    def test_native_datetime_gets_utc(self) -> None:
        naive = datetime(2026, 6, 8, 12, 0, 0)
        oa = OccurredAt(value=naive)
        assert oa.value.tzinfo is not None
        assert oa.value.tzinfo.utcoffset(oa.value).total_seconds() == 0.0

    def test_now(self) -> None:
        oa = OccurredAt.now()
        assert isinstance(oa.value, datetime)
        assert oa.value.tzinfo is not None


class TestResult:
    def test_value(self) -> None:
        assert Result(value="success").value == "success"


# ---------------------------------------------------------------------------
# Domain Rule Tests
# ---------------------------------------------------------------------------


class TestDomainRulesChainName:
    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidChainNameError):
            assert_chain_name_not_empty("")
        with pytest.raises(InvalidChainNameError):
            assert_chain_name_not_empty("   ")

    def test_non_empty_passes(self) -> None:
        assert_chain_name_not_empty("security")


class TestDomainRulesActorRef:
    def test_valid_types(self) -> None:
        for t in ("user", "service", "agent"):
            assert_actor_ref_valid(t, None)  # no error

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(InvalidActorRefError):
            assert_actor_ref_valid("robot", None)


class TestDomainRulesAction:
    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidActionError):
            assert_action_not_empty("")

    def test_non_empty_passes(self) -> None:
        assert_action_not_empty("memory.create")


class TestDomainRulesPolicyDecision:
    def test_valid_decisions(self) -> None:
        for d in ("grant", "deny", "require_confirmation"):
            assert_policy_decision_valid(d)  # no error

    def test_invalid_raises(self) -> None:
        with pytest.raises(InvalidPolicyDecisionError):
            assert_policy_decision_valid("maybe")


class TestDomainRulesClassification:
    def test_valid_classifications(self) -> None:
        for c in ("public", "internal", "sensitive", "restricted"):
            assert_classification_valid(c)

    def test_invalid_raises(self) -> None:
        with pytest.raises(InvalidClassificationError):
            assert_classification_valid("top_secret")


class TestDomainRulesCorrelationId:
    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidCorrelationIdError):
            assert_correlation_id_not_empty("")

    def test_non_empty_passes(self) -> None:
        assert_correlation_id_not_empty("01975c2f-4aef-7cf1-a940-ae54bf596280")


class TestDomainRulesResult:
    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidResultError):
            assert_result_not_empty("")

    def test_non_empty_passes(self) -> None:
        assert_result_not_empty("success")


class TestDomainRulesEntryIndex:
    def test_sequential_passes(self) -> None:
        assert_entry_index_sequential(5, 5)

    def test_mismatch_raises(self) -> None:
        with pytest.raises(InvalidEntryIndexError):
            assert_entry_index_sequential(5, 6)


class TestDomainRulesLifecycleTransition:
    def test_valid_transition(self) -> None:
        assert_lifecycle_transition_valid(AuditEntryState.PENDING, AuditEntryState.RECORDED)

    def test_invalid_transition(self) -> None:
        with pytest.raises(InvalidLifecycleTransitionError):
            assert_lifecycle_transition_valid(AuditEntryState.RECORDED, AuditEntryState.PENDING)
        with pytest.raises(InvalidLifecycleTransitionError):
            assert_lifecycle_transition_valid(AuditEntryState.RECORDED, AuditEntryState.RECORDED)


class TestDomainRulesContentMinimized:
    def test_clean_content_passes(self) -> None:
        assert_content_minimized(action="memory.create", result="success")

    def test_sensitive_pattern_raises(self) -> None:
        with pytest.raises(SensitiveContentInAuditEntry):
            assert_content_minimized(action="memory.create", redacted_reason="raw_prompt content")

    def test_non_string_field_skipped(self) -> None:
        assert_content_minimized(count=42)


class TestDomainRulesRestrictedReason:
    def test_restricted_with_no_reason_raises(self) -> None:
        with pytest.raises(RestrictedClassificationRequiresReason):
            assert_restricted_has_reason("restricted", None)
        with pytest.raises(RestrictedClassificationRequiresReason):
            assert_restricted_has_reason("restricted", "")

    def test_restricted_with_reason_passes(self) -> None:
        assert_restricted_has_reason("restricted", "Legal hold")

    def test_non_restricted_ignored(self) -> None:
        assert_restricted_has_reason("public", None)
        assert_restricted_has_reason("sensitive", "")


# ---------------------------------------------------------------------------
# Hash Chain Tests
# ---------------------------------------------------------------------------


class TestComputeEntryHash:
    def test_deterministic(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        kwargs = dict(
            chain_name="security",
            actor_type="user",
            actor_id="alice",
            action="memory.create",
            target_type="memory",
            target_ref="mem-001",
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-1",
            causation_id=None,
            result="success",
            redacted_reason=None,
            occurred_at=dt,
            entry_index=0,
        )
        h1 = compute_entry_hash(**kwargs)
        h2 = compute_entry_hash(**kwargs)
        assert h1 == h2
        assert len(h1) == 32  # SHA-256

    def test_different_content_different_hash(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        base = dict(
            chain_name="security",
            actor_type="user",
            actor_id="alice",
            action="memory.create",
            target_type="memory",
            target_ref="mem-001",
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-1",
            causation_id=None,
            result="success",
            redacted_reason=None,
            occurred_at=dt,
            entry_index=0,
        )
        h1 = compute_entry_hash(**base)
        h2 = compute_entry_hash(**{**base, "action": "memory.delete"})
        assert h1 != h2

    def test_entry_index_changes_hash(self) -> None:
        dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
        base = dict(
            chain_name="security",
            actor_type="user",
            actor_id="alice",
            action="memory.create",
            target_type="memory",
            target_ref="mem-001",
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-1",
            causation_id=None,
            result="success",
            redacted_reason=None,
            occurred_at=dt,
            entry_index=0,
        )
        h0 = compute_entry_hash(**base)
        h1 = compute_entry_hash(**{**base, "entry_index": 1})
        assert h0 != h1


class TestVerifyChainLink:
    def test_first_entry_valid(self) -> None:
        assert verify_chain_link(previous_hash=None, previous_entry_hash=None)

    def test_first_entry_invalid(self) -> None:
        assert not verify_chain_link(
            previous_hash=b"\x01" * 32, previous_entry_hash=None
        )
        assert not verify_chain_link(
            previous_hash=None, previous_entry_hash=b"\x01" * 32
        )

    def test_subsequent_entry_valid(self) -> None:
        h = b"\x01" * 32
        assert verify_chain_link(previous_hash=h, previous_entry_hash=h)

    def test_subsequent_entry_invalid(self) -> None:
        assert not verify_chain_link(
            previous_hash=b"\x01" * 32, previous_entry_hash=b"\x02" * 32
        )


# ---------------------------------------------------------------------------
# Factory Integration Tests
# ---------------------------------------------------------------------------


class TestAuditEntryFactory:
    def test_create_first_entry(self) -> None:
        entry, event = AuditEntryFactory.create(
            chain_name="security",
            action="memory.create",
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-001",
            result="success",
            actor_type="user",
            actor_id="alice",
        )
        assert isinstance(entry, AuditEntry)
        assert isinstance(event, AuditEntryRecorded)
        assert entry.chain_name == "security"
        assert entry.action == "memory.create"
        assert entry.policy_decision == "grant"
        assert entry.classification == "internal"
        assert entry.correlation_id == "corr-001"
        assert entry.result == "success"
        assert entry.actor.actor_type == "user"
        assert entry.actor.actor_id == "alice"
        assert entry.entry_index == EntryIndex(value=0)
        assert entry.previous_hash is None
        assert entry.state == AuditEntryState.RECORDED
        assert event.entry_id == entry.entry_id
        assert event.chain_name == "security"

    def test_create_subsequent_entry(self) -> None:
        # Create first entry to establish chain
        entry1, _ = AuditEntryFactory.create(
            chain_name="security",
            action="memory.create",
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-001",
            result="success",
            actor_type="user",
            actor_id="alice",
        )
        entry2, event2 = AuditEntryFactory.create(
            chain_name="security",
            action="consent.revoke",
            policy_decision="grant",
            classification="sensitive",
            correlation_id="corr-002",
            result="success",
            actor_type="agent",
            actor_id="jarvis",
            previous_entry_hash=entry1.entry_hash.value,
            previous_entry_index=entry1.entry_index.value,
        )
        assert entry2.entry_index == EntryIndex(value=1)
        assert entry2.previous_hash == entry1.entry_hash
        assert event2.entry_index == 1

    def test_previous_hash_stored(self) -> None:
        h = b"\xab" * 32
        entry, _ = AuditEntryFactory.create(
            chain_name="security",
            action="memory.create",
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-001",
            result="success",
            actor_type="user",
            actor_id="alice",
            previous_entry_hash=h,
            previous_entry_index=0,
        )
        assert entry.previous_hash is not None
        assert entry.previous_hash.value == h

    def test_restricted_requires_reason(self) -> None:
        with pytest.raises(RestrictedClassificationRequiresReason):
            AuditEntryFactory.create(
                chain_name="security",
                action="memory.read",
                policy_decision="deny",
                classification="restricted",
                correlation_id="corr-003",
                result="denied",
                actor_type="agent",
                actor_id="jarvis",
            )

    def test_restricted_with_reason_passes(self) -> None:
        entry, _ = AuditEntryFactory.create(
            chain_name="security",
            action="memory.read",
            policy_decision="deny",
            classification="restricted",
            correlation_id="corr-003",
            result="denied",
            actor_type="agent",
            actor_id="jarvis",
            redacted_reason="Legal hold on memory data",
        )
        assert entry.classification == "restricted"
        assert entry.redacted_reason == "Legal hold on memory data"

    def test_sensitive_content_rejected(self) -> None:
        with pytest.raises(SensitiveContentInAuditEntry):
            AuditEntryFactory.create(
                chain_name="security",
                action="memory.create",
                policy_decision="grant",
                classification="internal",
                correlation_id="corr-004",
                result="success",
                actor_type="user",
                actor_id="alice",
                redacted_reason="Contains raw_prompt text",
            )

    def test_target_ref_full(self) -> None:
        entry, _ = AuditEntryFactory.create(
            chain_name="consent",
            action="consent.revoke",
            policy_decision="grant",
            classification="sensitive",
            correlation_id="corr-005",
            result="success",
            actor_type="service",
            actor_id="memory-service",
            target_type="consent",
            target_ref="cons-001",
        )
        assert entry.target is not None
        assert entry.target.target_type == "consent"
        assert entry.target.target_ref == "cons-001"

    def test_target_ref_partial(self) -> None:
        entry, _ = AuditEntryFactory.create(
            chain_name="system",
            action="service.start",
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-006",
            result="success",
            actor_type="service",
            actor_id="memory-service",
            target_type="service",
        )
        assert entry.target is not None
        assert entry.target.target_type == "service"
        assert entry.target.target_ref is None

    def test_causation_id_propagated(self) -> None:
        entry, _ = AuditEntryFactory.create(
            chain_name="security",
            action="memory.create",
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-007",
            causation_id="cause-001",
            result="success",
            actor_type="user",
            actor_id="alice",
        )
        assert entry.causation_id == "cause-001"

    def test_explicit_occurred_at(self) -> None:
        dt = datetime(2026, 6, 8, 10, 0, 0, tzinfo=timezone.utc)
        entry, _ = AuditEntryFactory.create(
            chain_name="security",
            action="test.action",
            policy_decision="grant",
            classification="public",
            correlation_id="corr-008",
            result="success",
            actor_type="service",
            actor_id="audit-service",
            occurred_at=dt,
        )
        assert entry.occurred_at.value == dt

    def test_multiple_validation_errors_collected(self) -> None:
        with pytest.raises(AuditEntryError) as exc:
            AuditEntryFactory.create(
                chain_name="",
                action="",
                policy_decision="invalid",
                classification="bad",
                correlation_id="",
                result="",
                actor_type="robot",
                actor_id=None,
            )
        msg = str(exc.value)
        assert "Invalid chain name" in msg
        assert "Invalid action" in msg
        assert "Invalid policy decision" in msg
        assert "Invalid classification" in msg
        assert "Correlation ID must not be empty" in msg
        assert "Invalid result" in msg
        assert "Invalid actor ref" in msg

    def test_domain_event_fields(self) -> None:
        _, event = AuditEntryFactory.create(
            chain_name="admin",
            action="settings.update",
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-009",
            result="success",
            actor_type="user",
            actor_id="admin",
        )
        assert isinstance(event, AuditEntryRecorded)
        assert event.chain_name == "admin"
        assert event.action == "settings.update"
        assert event.actor_type == "user"
        assert event.actor_id == "admin"
        assert event.correlation_id == "corr-009"
        assert event.entry_index == 0
        assert isinstance(event.occurred_at, datetime)


# ---------------------------------------------------------------------------
# AuditEntry Entity Tests
# ---------------------------------------------------------------------------


class TestAuditEntryEntity:
    def test_repr(self) -> None:
        entry, _ = AuditEntryFactory.create(
            chain_name="security",
            action="test.repr",
            policy_decision="grant",
            classification="public",
            correlation_id="corr-repr",
            result="success",
            actor_type="user",
            actor_id="alice",
        )
        r = repr(entry)
        assert "AuditEntry" in r
        assert "security" in r
        assert "test.repr" in r

    def test_readonly_properties(self) -> None:
        entry, _ = AuditEntryFactory.create(
            chain_name="system",
            action="service.start",
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-ro",
            result="success",
            actor_type="service",
            actor_id="audit",
        )
        assert entry.chain_name == "system"
        assert entry.action == "service.start"
        assert entry.policy_decision == "grant"

    def test_lifecycle_transition(self) -> None:
        entry = AuditEntry(
            entry_id=AuditEntryId(),
            chain_name="test",
            actor=__import__("backend.audit.domain.model", fromlist=["ActorRef"]).ActorRef(
                actor_type="user", actor_id="tester"
            ),
            action="test.transition",
            policy_decision="grant",
            classification="public",
            correlation_id="corr-lifecycle",
            result="success",
            entry_hash=EntryHash(value=b"\x00" * 32),
            entry_index=EntryIndex(value=0),
            state=AuditEntryState.PENDING,
        )
        assert entry.state == AuditEntryState.PENDING
        entry.transition_to_recorded()
        assert entry.state == AuditEntryState.RECORDED

        with pytest.raises(ValueError, match="Cannot transition"):
            entry.transition_to_recorded()


# ---------------------------------------------------------------------------
# AuditChainHead Tests
# ---------------------------------------------------------------------------


class TestAuditChainHead:
    def test_empty_chain(self) -> None:
        head = AuditChainHead(chain_name="security", head_hash=None, entries_count=0)
        assert head.chain_name == "security"
        assert head.head_hash is None
        assert head.entries_count == 0

    def test_with_hash(self) -> None:
        h = EntryHash(value=b"\xab" * 32)
        head = AuditChainHead(chain_name="consent", head_hash=h, entries_count=5)
        assert head.head_hash == h
        assert head.entries_count == 5


# ---------------------------------------------------------------------------
# Hash Determinism Verification
# ---------------------------------------------------------------------------


class TestHashDeterminism:
    def test_canonical_json_stable(self) -> None:
        """Prove that the JSON serialization is deterministic."""
        import json

        a = json.dumps({"b": 2, "a": 1}, sort_keys=True)
        b = json.dumps({"a": 1, "b": 2}, sort_keys=True)
        assert a == b

    def test_chain_integrity_three_entries(self) -> None:
        """Build a chain of 3 entries and verify all links."""
        entry0, _ = AuditEntryFactory.create(
            chain_name="chain-test",
            action="entry.0",
            policy_decision="grant",
            classification="public",
            correlation_id="corr-c0",
            result="success",
            actor_type="user",
            actor_id="alice",
        )
        entry1, _ = AuditEntryFactory.create(
            chain_name="chain-test",
            action="entry.1",
            policy_decision="deny",
            classification="sensitive",
            correlation_id="corr-c1",
            result="denied",
            actor_type="agent",
            actor_id="jarvis",
            previous_entry_hash=entry0.entry_hash.value,
            previous_entry_index=entry0.entry_index.value,
        )
        entry2, _ = AuditEntryFactory.create(
            chain_name="chain-test",
            action="entry.2",
            policy_decision="require_confirmation",
            classification="restricted",
            correlation_id="corr-c2",
            result="pending",
            actor_type="service",
            actor_id="audit-svc",
            redacted_reason="Requires user confirmation",
            previous_entry_hash=entry1.entry_hash.value,
            previous_entry_index=entry1.entry_index.value,
        )

        assert entry0.entry_index == EntryIndex(value=0)
        assert entry1.entry_index == EntryIndex(value=1)
        assert entry2.entry_index == EntryIndex(value=2)

        assert entry0.previous_hash is None
        assert entry1.previous_hash == entry0.entry_hash
        assert entry2.previous_hash == entry1.entry_hash

        # Verify manually
        assert verify_chain_link(
            previous_hash=None, previous_entry_hash=None
        )
        assert verify_chain_link(
            previous_hash=entry1.previous_hash.value,
            previous_entry_hash=entry0.entry_hash.value,
        )
        assert verify_chain_link(
            previous_hash=entry2.previous_hash.value,
            previous_entry_hash=entry1.entry_hash.value,
        )


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_string_values_accepted_by_factory(self) -> None:
        """Factory validation catches empties; test that direct
        construction bypasses rules (as expected for domain entities)."""
        entry = AuditEntry(
            entry_id=AuditEntryId(),
            chain_name="",
            actor=__import__("backend.audit.domain.model", fromlist=["ActorRef"]).ActorRef(
                actor_type="",
                actor_id=None,
            ),
            action="",
            policy_decision="",
            classification="",
            correlation_id="",
            result="",
            entry_hash=EntryHash(value=b"\x00" * 32),
            entry_index=EntryIndex(value=0),
        )
        assert entry.chain_name == ""
        assert entry.actor.actor_type == ""

    def test_very_long_target_ref(self) -> None:
        long_ref = "x" * 1000
        entry, _ = AuditEntryFactory.create(
            chain_name="security",
            action="storage.query",
            policy_decision="grant",
            classification="internal",
            correlation_id="corr-long",
            result="success",
            actor_type="user",
            actor_id="alice",
            target_type="documents",
            target_ref=long_ref,
        )
        assert entry.target is not None
        assert len(entry.target.target_ref) == 1000

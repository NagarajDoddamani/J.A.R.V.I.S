from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.audit.domain.exceptions import AuditEntryError
from backend.audit.domain.hash_chain import compute_entry_hash
from backend.audit.domain.model import (
    ActorRef,
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
    assert_policy_decision_valid,
    assert_restricted_has_reason,
    assert_result_not_empty,
)


class AuditEntryFactory:
    """Factory for creating validated AuditEntry aggregate instances.

    The factory enforces all domain rules, computes the entry hash,
    links the chain, and emits an ``AuditEntryRecorded`` domain event.
    """

    @staticmethod
    def create(
        *,
        chain_name: str,
        action: str,
        policy_decision: str,
        classification: str,
        correlation_id: str,
        result: str,
        actor_type: str,
        actor_id: str | None = None,
        causation_id: str | None = None,
        target_type: str | None = None,
        target_ref: str | None = None,
        redacted_reason: str | None = None,
        occurred_at: datetime | None = None,
        previous_entry_hash: bytes | None = None,
        previous_entry_index: int | None = None,
    ) -> tuple[AuditEntry, AuditEntryRecorded]:
        """Create a validated AuditEntry with hash-chain linking.

        Parameters
        ----------
        previous_entry_hash:
            The ``entry_hash`` of the preceding entry in the same
            chain. ``None`` for the first entry.
        previous_entry_index:
            The ``entry_index`` of the preceding entry. ``None``
            for the first entry.

        Returns
        -------
        tuple[AuditEntry, AuditEntryRecorded]
            The validated entry and the emitted domain event.
        """
        AuditEntryFactory._validate_create_params(
            chain_name=chain_name,
            action=action,
            policy_decision=policy_decision,
            classification=classification,
            correlation_id=correlation_id,
            result=result,
            actor_type=actor_type,
            actor_id=actor_id,
            target_type=target_type,
            target_ref=target_ref,
            redacted_reason=redacted_reason,
        )

        entry_id = AuditEntryId()
        actor = ActorRef(actor_type=actor_type, actor_id=actor_id)
        target = (
            TargetRef(target_type=target_type, target_ref=target_ref)
            if target_type or target_ref
            else None
        )
        result_obj = Result(value=result)
        occurred_at_obj = (
            OccurredAt(value=occurred_at) if occurred_at else OccurredAt.now()
        )

        entry_index = (
            EntryIndex(value=previous_entry_index + 1)
            if previous_entry_index is not None
            else EntryIndex(value=0)
        )

        raw_hash = compute_entry_hash(
            chain_name=chain_name,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_ref=target_ref,
            policy_decision=policy_decision,
            classification=classification,
            correlation_id=correlation_id,
            causation_id=causation_id,
            result=result_obj.value,
            redacted_reason=redacted_reason,
            occurred_at=occurred_at_obj.value,
            entry_index=entry_index.value,
        )
        entry_hash_obj = EntryHash(value=raw_hash)

        previous_hash_obj = (
            EntryHash(value=previous_entry_hash) if previous_entry_hash is not None else None
        )

        entry = AuditEntry(
            entry_id=entry_id,
            chain_name=chain_name,
            actor=actor,
            action=action,
            target=target,
            policy_decision=policy_decision,
            classification=classification,
            correlation_id=correlation_id,
            causation_id=causation_id,
            result=result_obj.value,
            redacted_reason=redacted_reason,
            occurred_at=occurred_at_obj,
            previous_hash=previous_hash_obj,
            entry_hash=entry_hash_obj,
            entry_index=entry_index,
            state=AuditEntryState.RECORDED,
        )

        domain_event = AuditEntryRecorded(
            entry_id=entry_id,
            chain_name=chain_name,
            action=action,
            actor_type=actor_type,
            actor_id=actor_id,
            correlation_id=correlation_id,
            entry_index=entry_index.value,
            occurred_at=occurred_at_obj.value,
        )

        return entry, domain_event

    @staticmethod
    def _validate_create_params(
        *,
        chain_name: str,
        action: str,
        policy_decision: str,
        classification: str,
        correlation_id: str,
        result: str,
        actor_type: str,
        actor_id: str | None,
        target_type: str | None,
        target_ref: str | None,
        redacted_reason: str | None,
    ) -> None:
        errors: list[AuditEntryError] = []

        try:
            assert_chain_name_not_empty(chain_name)
        except AuditEntryError as e:
            errors.append(e)

        try:
            assert_actor_ref_valid(actor_type, actor_id)
        except AuditEntryError as e:
            errors.append(e)

        try:
            assert_action_not_empty(action)
        except AuditEntryError as e:
            errors.append(e)

        try:
            assert_policy_decision_valid(policy_decision)
        except AuditEntryError as e:
            errors.append(e)

        try:
            assert_classification_valid(classification)
        except AuditEntryError as e:
            errors.append(e)

        try:
            assert_correlation_id_not_empty(correlation_id)
        except AuditEntryError as e:
            errors.append(e)

        try:
            assert_result_not_empty(result)
        except AuditEntryError as e:
            errors.append(e)

        assert_restricted_has_reason(classification, redacted_reason)

        assert_content_minimized(
            action=action,
            result=result,
            redacted_reason=redacted_reason,
            target_ref=target_ref,
        )

        if errors:
            raise AuditEntryError(
                "; ".join(str(e) for e in errors)
            )

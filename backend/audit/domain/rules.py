from __future__ import annotations

from backend.audit.domain.exceptions import (
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
from backend.audit.domain.model import AuditEntryState

VALID_ACTOR_TYPES: frozenset[str] = frozenset({"user", "service", "agent"})
VALID_CLASSIFICATIONS: frozenset[str] = frozenset(
    {"public", "internal", "sensitive", "restricted"}
)
VALID_POLICY_DECISIONS: frozenset[str] = frozenset(
    {"grant", "deny", "require_confirmation"}
)

SENSITIVE_FIELD_PATTERNS: tuple[str, ...] = (
    "raw_prompt",
    "full_prompt",
    "prompt",
    "transcript",
    "user_content",
    "query_text",
    "document_body",
    "chunk_body",
    "embedding",
    "raw_audio",
    "raw_image",
    "raw_screenshot",
    "memory_text",
    "memory_content",
    "raw_memory",
    "research_content",
    "raw_research",
)


def assert_chain_name_not_empty(chain_name: str) -> None:
    if not chain_name or not chain_name.strip():
        raise InvalidChainNameError(chain_name)


def assert_actor_ref_valid(actor_type: str, actor_id: str | None) -> None:
    if actor_type not in VALID_ACTOR_TYPES:
        raise InvalidActorRefError(actor_type, actor_id)


def assert_action_not_empty(action: str) -> None:
    if not action or not action.strip():
        raise InvalidActionError(action)


def assert_policy_decision_valid(decision: str) -> None:
    if decision not in VALID_POLICY_DECISIONS:
        raise InvalidPolicyDecisionError(decision)


def assert_classification_valid(classification: str) -> None:
    if classification not in VALID_CLASSIFICATIONS:
        raise InvalidClassificationError(classification)


def assert_correlation_id_not_empty(correlation_id: str) -> None:
    if not correlation_id or not correlation_id.strip():
        raise InvalidCorrelationIdError()


def assert_result_not_empty(result: str) -> None:
    if not result or not result.strip():
        raise InvalidResultError(result)


def assert_entry_index_sequential(
    new_index: int, expected_index: int
) -> None:
    if new_index != expected_index:
        raise InvalidEntryIndexError(new_index, expected_index)


def assert_lifecycle_transition_valid(
    current: AuditEntryState, target: AuditEntryState
) -> None:
    """Allow only PENDING -> RECORDED."""
    if current == AuditEntryState.PENDING and target == AuditEntryState.RECORDED:
        return
    raise InvalidLifecycleTransitionError(current.value, target.value)


def assert_content_minimized(**fields: object) -> None:
    """Ensure no sensitive content leaks into audit entry fields."""
    for field_name, value in fields.items():
        if not isinstance(value, str):
            continue
        lower = value.lower()
        for pattern in SENSITIVE_FIELD_PATTERNS:
            if pattern in lower:
                raise SensitiveContentInAuditEntry(field_name, value)


def assert_restricted_has_reason(
    classification: str, redacted_reason: str | None
) -> None:
    """Restricted entries must include a non-empty redacted_reason."""
    if classification == "restricted" and (
        not redacted_reason or not redacted_reason.strip()
    ):
        raise RestrictedClassificationRequiresReason()

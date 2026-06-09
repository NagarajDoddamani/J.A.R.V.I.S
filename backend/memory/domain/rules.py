from __future__ import annotations

import re
from datetime import datetime, timezone

from backend.memory.domain.exceptions import (
    ConsentNotActiveError,
    ContentTooLongError,
    DeletedMemoryUpdateError,
    EmptyContentError,
    EventPayloadTooDetailedError,
    ExpirationBeforeGrantError,
    InvalidClassificationError,
    InvalidConsentTransitionError,
    InvalidSensitivityError,
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
from backend.memory.domain.model import (
    ConsentRecord,
    ConsentStatus,
    MemoryContent,
    MemoryState,
    Provenance,
    RetentionPolicy,
    RetentionStatus,
)

# GLOBAL CONFIGURATION
MAX_CONTENT_LENGTH: int = 10000

VALID_CLASSIFICATIONS: frozenset[str] = frozenset(
    {"public", "internal", "sensitive", "restricted"}
)

VALID_SENSITIVITY_LEVELS: frozenset[str] = frozenset(
    {"public", "internal", "sensitive", "restricted"}
)

SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bpassword\b", re.IGNORECASE),
    re.compile(r"\btoken\b", re.IGNORECASE),
    re.compile(r"api[_\-]?key", re.IGNORECASE),
    re.compile(r"private[_\-]?key", re.IGNORECASE),
    re.compile(r"secret[_\-]?(word|key|token)", re.IGNORECASE),
    re.compile(r"authorization", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9\-._~+/]+", re.IGNORECASE),
)

VALID_CONSENT_TRANSITIONS: dict[ConsentStatus, set[ConsentStatus]] = {
    ConsentStatus.PROPOSED: {ConsentStatus.ACTIVE},
    ConsentStatus.ACTIVE: {ConsentStatus.REVOKED},
    ConsentStatus.REVOKED: {ConsentStatus.PURGED},
    ConsentStatus.PURGED: set(),
}

SENSITIVE_FIELDS: frozenset[str] = frozenset(
    {"password", "token", "api_key", "private_key", "secret"}
)


def assert_content_not_empty(content: str) -> None:
    if not content or not content.strip():
        raise EmptyContentError()


def assert_content_max_length(content: str, max_length: int = MAX_CONTENT_LENGTH) -> None:
    if len(content) > max_length:
        raise ContentTooLongError(len(content), max_length)


def assert_content_no_secrets(content: str) -> None:
    lower = content.lower()
    for pattern in SECRET_PATTERNS:
        if pattern.search(lower) or pattern.search(content):
            match = pattern.search(content)
            matched = match.group(0) if match else ""
            raise SecretDetectedError(matched[:40])


def assert_consent_active(consent: ConsentRecord) -> None:
    if not consent.is_active:
        raise ConsentNotActiveError(consent.status.value)


def assert_consent_allows_updates(consent: ConsentRecord) -> None:
    if consent.status == ConsentStatus.REVOKED:
        raise RevokedConsentBlocksUpdateError()
    if consent.status == ConsentStatus.PURGED:
        raise PurgedConsentError()
    if consent.status != ConsentStatus.ACTIVE:
        raise ConsentNotActiveError(consent.status.value)
    if consent.expires_at is not None and consent.expires_at < datetime.now(tz=timezone.utc):
        raise ConsentNotActiveError(consent.status.value)


def assert_retention_provided(policy: RetentionPolicy | None) -> None:
    if policy is None:
        raise RetentionRequiredError()


def assert_provenance_provided(provenance: Provenance | None) -> None:
    if provenance is None:
        raise ProvenanceRequiredError()


def assert_source_provided(source: str | None) -> None:
    if not source or not source.strip():
        raise SourceRequiredError()


def assert_classification_valid(classification: str) -> None:
    if classification not in VALID_CLASSIFICATIONS:
        raise InvalidClassificationError(classification)


def assert_not_deleted(state: MemoryState) -> None:
    if state == MemoryState.DELETED:
        raise DeletedMemoryUpdateError()


def assert_expiration_after_grant(expires_at: datetime, granted_at: datetime) -> None:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if granted_at.tzinfo is None:
        granted_at = granted_at.replace(tzinfo=timezone.utc)
    if expires_at < granted_at:
        raise ExpirationBeforeGrantError()


def assert_consent_can_transition(
    current: ConsentStatus, target: ConsentStatus
) -> None:
    allowed = VALID_CONSENT_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidConsentTransitionError(current.value, target.value)


# -- Rule 14: Sensitive memories require active consent ---------------------

def assert_sensitive_requires_consent(sensitivity: str, consent: ConsentRecord) -> None:
    if sensitivity == "sensitive" and not consent.is_active:
        raise SensitiveMemoryRequiresConsentError()


# -- Rule 15: Restricted memories require redaction metadata ----------------

def assert_restricted_requires_redaction(
    sensitivity: str, redaction_metadata: str | None
) -> None:
    if sensitivity == "restricted" and not redaction_metadata:
        raise RestrictedMemoryRequiresRedactionError()


# -- Rule 16: Purged memories are immutable forever -------------------------

def assert_not_purged(retention_status: RetentionStatus) -> None:
    if retention_status == RetentionStatus.PURGED:
        raise PurgedMemoryImmutableError()


# -- Rule 17: Retention expiration validation -------------------------------

def assert_retention_can_expire(retention_status: RetentionStatus) -> None:
    if retention_status == RetentionStatus.PURGED:
        raise RetentionExpirationError("Cannot expire a purged memory")
    if retention_status == RetentionStatus.EXPIRED:
        raise RetentionExpirationError("Memory retention is already expired")


# -- Rule 18: Revisions start at 1 (enforced by RevisionNumber VO) ---------

# -- Rule 19: Source provenance must survive all revisions ------------------

def assert_provenance_preserved(original: Provenance, current: Provenance) -> None:
    if original.source != current.source:
        raise ProvenanceMismatchError()


# -- Rule 20: Memory content not stored in domain events --------------------

def assert_event_payload_omits_content(event_fields: set[str]) -> None:
    if "content" in event_fields or "memory_content" in event_fields:
        raise EventPayloadTooDetailedError(
            "Event payload must not contain memory content"
        )


# -- Rule 21: Event payloads must comply with JDOS sensitive-payload --------

def assert_event_payload_compliant(event_fields: set[str], sensitivity: str) -> None:
    if sensitivity in ("sensitive", "restricted"):
        for field in event_fields:
            lower = field.lower()
            for sensitive_field in SENSITIVE_FIELDS:
                if sensitive_field in lower:
                    raise EventPayloadTooDetailedError(
                        f"Event payload must not contain {field!r} for "
                        f"{sensitivity} memories"
                    )


# -- Helper: validate sensitivity -------------------------------------------

def assert_sensitivity_valid(sensitivity: str) -> None:
    if sensitivity not in VALID_SENSITIVITY_LEVELS:
        raise InvalidSensitivityError(sensitivity)


# -- Composite validators ---------------------------------------------------

def validate_memory_creation(
    content: MemoryContent,
    consent: ConsentRecord,
    source_type: str,
    provenance: Provenance | None,
    classification: str,
    sensitivity: str,
    retention: RetentionPolicy | None,
    redaction_metadata: str | None = None,
) -> None:
    assert_content_not_empty(content.value)
    assert_content_max_length(content.value)
    assert_content_no_secrets(content.value)
    assert_consent_active(consent)
    assert_source_provided(source_type)
    assert_provenance_provided(provenance)
    assert_classification_valid(classification)
    assert_sensitivity_valid(sensitivity)
    assert_retention_provided(retention)
    assert_sensitive_requires_consent(sensitivity, consent)
    assert_restricted_requires_redaction(sensitivity, redaction_metadata)

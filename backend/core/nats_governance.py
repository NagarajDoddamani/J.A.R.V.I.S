"""JARVIS NATS Governance (JDOS v1.2, Correction 10).

This module is the single source of truth for NATS topology, payload
boundaries, retry policy, dead-letter routing, and envelope validation
required by the JARVIS Development Operating System v1.2.

It contains **no business logic**. It exposes declarative stream and
consumer configurations, a small set of pure validators, and helpers
for subject derivation. The runtime manager (``backend.core.nats``)
consumes these declarations to bootstrap the broker on startup.

Authoritative references:
    - ``docs/architecture/JDOS_v1.2_Architecture_Corrections_Addendum.md``
    - ``docs/implementation/event_contracts.md``
    - ``docs/architecture/system_architecture.md``
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any, Final

# ---------------------------------------------------------------------------
# Wire-level boundaries
# ---------------------------------------------------------------------------

#: Hard upper bound on the serialized size of any durable command or event.
#: Enforced at the producer boundary; consumers MUST also reject oversize
#: messages to defend against rogue publishers.
NATS_MAX_PAYLOAD_BYTES: Final[int] = 256 * 1024  # 256 KiB

#: Reserved headroom for JetStream protocol overhead. A producer MUST refuse
#: to publish when the serialized payload would exceed this budget even
#: before reaching the broker.
NATS_PAYLOAD_HEADROOM_BYTES: Final[int] = 1024

# ---------------------------------------------------------------------------
# Stream classes (Correction 10, stream table)
# ---------------------------------------------------------------------------

STREAM_COMMANDS: Final[str] = "JARVIS_COMMANDS_V1"
STREAM_EVENTS: Final[str] = "JARVIS_EVENTS_V1"
STREAM_AUDIT_SIGNALS: Final[str] = "JARVIS_AUDIT_SIGNALS_V1"

STREAM_NAMES: Final[tuple[str, ...]] = (
    STREAM_COMMANDS,
    STREAM_EVENTS,
    STREAM_AUDIT_SIGNALS,
)

# ---------------------------------------------------------------------------
# Subject conventions
# ---------------------------------------------------------------------------

#: Allowed command domains, derived from the v1.2 core command registry.
#: Additional domains may be added through a future ADR.
ALLOWED_COMMAND_DOMAINS: Final[frozenset[str]] = frozenset(
    {
        "request",
        "notification",
        "wallpaper",
        "memory",
        "research",
        "automation",
        "settings",
        "knowledge",
        "consent",
        "deletion",
    }
)

#: Stream-level subject filters. Each stream receives a single wildcard
#: root; per-subject authorization is enforced through NATS accounts.
STREAM_COMMANDS_SUBJECTS: Final[tuple[str, ...]] = ("jarvis.command.>",)
STREAM_EVENTS_SUBJECTS: Final[tuple[str, ...]] = ("jarvis.event.>",)
STREAM_AUDIT_SIGNALS_SUBJECTS: Final[tuple[str, ...]] = ("jarvis.audit.signal.>",)

#: Ephemeral NATS Core subjects (no persistence).
EPHEMERAL_SUBJECT_ROOT: Final[str] = "jarvis.ephemeral."

#: Dead-letter subject root. Each domain gets its own DLQ subject.
DLQ_SUBJECT_ROOT: Final[str] = "jarvis.dlq."

# ---------------------------------------------------------------------------
# Subject patterns
# ---------------------------------------------------------------------------

_SUBJECT_RE = re.compile(
    r"^jarvis\.(?P<kind>command|event|ephemeral|dlq|audit)\."
    r"(?P<domain>[a-z][a-z0-9_]*)"
    r"(?:\.(?P<rest>[a-z0-9_\.]+?))?"
    r"\.v(?P<major>[0-9]+)$"
)


# ---------------------------------------------------------------------------
# Retry and backoff policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded exponential backoff with full jitter.

    Delivery is attempted up to ``max_attempts`` times. Each retry waits
    ``base_ms * 2 ** (attempt - 1)`` milliseconds, capped at
    ``max_backoff_ms``, and jittered in the range ``[0, capped]``.
    """

    max_attempts: int = 5
    base_ms: int = 250
    max_backoff_ms: int = 30_000
    jitter: bool = True

    def delay_ms(self, attempt: int) -> int:
        """Return the wait time in milliseconds for ``attempt`` (1-indexed)."""
        if attempt < 1:
            raise ValueError("attempt must be >= 1")
        return min(self.max_backoff_ms, self.base_ms * (2 ** (attempt - 1)))


DEFAULT_RETRY_POLICY: Final[RetryPolicy] = RetryPolicy()


# ---------------------------------------------------------------------------
# Stream retention defaults
# ---------------------------------------------------------------------------

#: 30-day default retention for durable events, expressed in seconds.
EVENTS_RETENTION_SECONDS: Final[int] = 30 * 24 * 60 * 60

#: 7-day delivery buffer for audit signals, expressed in seconds.
AUDIT_SIGNALS_BUFFER_SECONDS: Final[int] = 7 * 24 * 60 * 60

#: Default time window for duplicate suppression at the broker.
DUPLICATE_WINDOW_SECONDS: Final[int] = 120


# ---------------------------------------------------------------------------
# Consumer defaults
# ---------------------------------------------------------------------------

#: Time a consumer has to acknowledge a message before redelivery.
ACK_WAIT_SECONDS: Final[int] = 30

#: Default maximum in-flight messages per consumer.
MAX_ACK_PENDING: Final[int] = 1000

#: Default maximum pull-batch wait.
MAX_PULL_WAIT_SECONDS: Final[int] = 2


# ---------------------------------------------------------------------------
# Envelope field contracts
# ---------------------------------------------------------------------------

COMMAND_ENVELOPE_REQUIRED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "command_id",
        "command_type",
        "command_version",
        "issued_at",
        "expires_at",
        "producer",
        "correlation_id",
        "causation_id",
        "idempotency_key",
        "actor",
        "classification",
        "payload",
    }
)

EVENT_ENVELOPE_REQUIRED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "event_id",
        "event_type",
        "event_version",
        "occurred_at",
        "producer",
        "correlation_id",
        "causation_id",
        "actor",
        "classification",
        "trace_context",
        "payload",
    }
)

#: Valid classification buckets, sourced from the security_privacy doc.
VALID_CLASSIFICATIONS: Final[frozenset[str]] = frozenset(
    {"public", "internal", "sensitive", "restricted"}
)

#: Valid actor types, sourced from the capability model.
VALID_ACTOR_TYPES: Final[frozenset[str]] = frozenset({"user", "service", "agent"})

# ---------------------------------------------------------------------------
# Sensitive payload policy (Correction 5)
# ---------------------------------------------------------------------------

#: Top-level keys that MUST NOT appear in durable NATS payloads.
#: Matching is case-insensitive and recursive.
SENSITIVE_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(
    {
        "raw_memory",
        "memory_content",
        "raw_research",
        "research_content",
        "raw_prompt",
        "full_prompt",
        "prompt",
        "transcript",
        "user_content",
        "query_text",
        "document_body",
        "chunk_body",
        "embedding",
        "embedding_vector",
        "raw_audio",
        "raw_image",
        "raw_screenshot",
        "memory_text",
        "api_key",
        "secret",
        "token",
        "password",
        "private_key",
    }
)


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class GovernanceError(ValueError):
    """Raised when a payload or envelope violates JDOS v1.2 governance."""


# ---------------------------------------------------------------------------
# Stream configuration (declarative)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StreamSpec:
    """Declarative description of a JetStream stream."""

    name: str
    subjects: tuple[str, ...]
    retention: str
    max_age_seconds: int
    max_msg_size: int
    description: str
    storage: str = "file"
    discard: str = "old"
    num_replicas: int = 1
    duplicate_window_seconds: int = DUPLICATE_WINDOW_SECONDS


STREAM_SPECS: Final[tuple[StreamSpec, ...]] = (
    StreamSpec(
        name=STREAM_COMMANDS,
        subjects=STREAM_COMMANDS_SUBJECTS,
        retention="work_queue",
        max_age_seconds=0,
        max_msg_size=NATS_MAX_PAYLOAD_BYTES,
        description=(
            "Durable, work-queue command stream. Single owner per command. "
            "Reference-only payloads; sensitive content forbidden."
        ),
    ),
    StreamSpec(
        name=STREAM_EVENTS,
        subjects=STREAM_EVENTS_SUBJECTS,
        retention="limits",
        max_age_seconds=EVENTS_RETENTION_SECONDS,
        max_msg_size=NATS_MAX_PAYLOAD_BYTES,
        description=(
            "Durable, multi-subscriber event stream. Reference-only payloads; "
            "30-day default retention; consumer is responsible for retention."
        ),
    ),
    StreamSpec(
        name=STREAM_AUDIT_SIGNALS,
        subjects=STREAM_AUDIT_SIGNALS_SUBJECTS,
        retention="limits",
        max_age_seconds=AUDIT_SIGNALS_BUFFER_SECONDS,
        max_msg_size=NATS_MAX_PAYLOAD_BYTES,
        description=(
            "Reference-only audit delivery signals for the Audit Service. "
            "7-day delivery buffer; metadata only."
        ),
    ),
)


def stream_spec(name: str) -> StreamSpec:
    """Return the :class:`StreamSpec` for ``name`` or raise."""
    for spec in STREAM_SPECS:
        if spec.name == name:
            return spec
    raise GovernanceError(f"Unknown stream name: {name!r}")


# ---------------------------------------------------------------------------
# Consumer configuration (declarative)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsumerSpec:
    """Declarative description of a JetStream durable consumer."""

    stream: str
    name: str
    description: str
    filter_subjects: tuple[str, ...]
    ack_policy: str = "explicit"
    ack_wait_seconds: int = ACK_WAIT_SECONDS
    max_deliver: int = DEFAULT_RETRY_POLICY.max_attempts
    max_ack_pending: int = MAX_ACK_PENDING
    deliver_policy: str = "all"


#: The six core v1.2 command consumers. Each is a durable single-owner
#: pull consumer bound to its imperative subject. The owning handler
#: is the only component permitted to attach a competing consumer.
COMMAND_CONSUMER_SPECS: Final[tuple[ConsumerSpec, ...]] = tuple(
    ConsumerSpec(
        stream=STREAM_COMMANDS,
        name=f"consumer-{domain}-v1",
        description=f"Owning consumer for jarvis.command.{domain}.*.v1",
        filter_subjects=(f"jarvis.command.{domain}.>.v1",),
    )
    for domain in (
        "request",
        "notification",
        "wallpaper",
        "memory",
        "research",
        "automation",
        "settings",
        "knowledge",
        "consent",
        "deletion",
    )
)


# ---------------------------------------------------------------------------
# Subject helpers
# ---------------------------------------------------------------------------


def command_subject(domain: str, action: str, major: int = 1) -> str:
    """Build a v1.2 command subject."""
    if domain not in ALLOWED_COMMAND_DOMAINS:
        raise GovernanceError(f"Unknown command domain: {domain!r}")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", action):
        raise GovernanceError(f"Invalid command action: {action!r}")
    if not isinstance(major, int) or major < 1:
        raise GovernanceError(f"Invalid major version: {major!r}")
    return f"jarvis.command.{domain}.{action}.v{major}"


def event_subject(domain: str, fact: str, major: int = 1) -> str:
    """Build a v1.2 event subject using a past-tense fact."""
    if not re.fullmatch(r"[a-z][a-z0-9_]*", domain):
        raise GovernanceError(f"Invalid event domain: {domain!r}")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", fact):
        raise GovernanceError(f"Invalid event fact: {fact!r}")
    if not isinstance(major, int) or major < 1:
        raise GovernanceError(f"Invalid major version: {major!r}")
    return f"jarvis.event.{domain}.{fact}.v{major}"


def dlq_subject(domain: str) -> str:
    """Build the dead-letter subject for ``domain``."""
    if not re.fullmatch(r"[a-z][a-z0-9_]*", domain):
        raise GovernanceError(f"Invalid DLQ domain: {domain!r}")
    return f"{DLQ_SUBJECT_ROOT}{domain}.v1"


def ephemeral_subject(domain: str, state: str, major: int = 1) -> str:
    """Build an ephemeral NATS Core subject (no persistence)."""
    if not re.fullmatch(r"[a-z][a-z0-9_]*", domain):
        raise GovernanceError(f"Invalid ephemeral domain: {domain!r}")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", state):
        raise GovernanceError(f"Invalid ephemeral state: {state!r}")
    return f"{EPHEMERAL_SUBJECT_ROOT}{domain}.{state}.v{major}"


def parse_subject(subject: str) -> dict[str, str]:
    """Parse a JARVIS subject into its components.

    Raises :class:`GovernanceError` if the subject is not a known
    JARVIS subject under the v1.2 conventions.
    """
    match = _SUBJECT_RE.match(subject)
    if not match:
        raise GovernanceError(f"Subject is not a JARVIS v1.2 subject: {subject!r}")
    return match.groupdict()


# ---------------------------------------------------------------------------
# Payload validators
# ---------------------------------------------------------------------------


def is_uuid_v4_or_v7(value: str) -> bool:
    """Return True if ``value`` parses as a UUID (any version)."""
    try:
        parsed = uuid.UUID(str(value))
    except (TypeError, ValueError):
        return False
    return parsed.version in (4, 7)


def validate_correlation_id(value: Any) -> None:
    """Enforce the v1.2 correlation-ID contract."""
    if not isinstance(value, str) or not value:
        raise GovernanceError("correlation_id is required and must be a non-empty string")
    if not is_uuid_v4_or_v7(value):
        raise GovernanceError(f"correlation_id must be a UUID: {value!r}")


def validate_causation_id(value: Any) -> None:
    """Enforce the v1.2 causation-ID contract."""
    if not isinstance(value, str) or not value:
        raise GovernanceError("causation_id is required and must be a non-empty string")
    if not is_uuid_v4_or_v7(value):
        raise GovernanceError(f"causation_id must be a UUID: {value!r}")


def validate_payload_size(serialized: bytes) -> None:
    """Reject payloads that exceed the 256 KiB boundary."""
    if not isinstance(serialized, (bytes, bytearray, memoryview)):
        raise GovernanceError("Payload must be bytes-like")
    if len(serialized) > NATS_MAX_PAYLOAD_BYTES:
        raise GovernanceError(
            f"Payload exceeds {NATS_MAX_PAYLOAD_BYTES} byte limit "
            f"(received {len(serialized)} bytes)"
        )


def validate_sensitive_payload(payload: Any, *, _seen: set[int] | None = None) -> None:
    """Reject any durable payload that contains sensitive keys.

    Matching is recursive and case-insensitive. Cycles are detected via
    object identity and treated as a hard failure to prevent DoS.
    """
    if _seen is None:
        _seen = set()
    if id(payload) in _seen:
        raise GovernanceError("Cyclic payload detected during sensitive-payload scan")
    _seen.add(id(payload))

    if isinstance(payload, dict):
        for key, value in payload.items():
            if not isinstance(key, str):
                raise GovernanceError("Payload keys must be strings")
            if key.lower() in SENSITIVE_PAYLOAD_KEYS:
                raise GovernanceError(
                    f"Payload contains sensitive key: {key!r} (Correction 5)"
                )
            if isinstance(value, (dict, list)):
                validate_sensitive_payload(value, _seen=_seen)
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, (dict, list)):
                validate_sensitive_payload(item, _seen=_seen)


def validate_envelope(envelope: dict[str, Any], *, kind: str) -> None:
    """Validate the structural envelope of a command or event."""
    if not isinstance(envelope, dict):
        raise GovernanceError("Envelope must be a dict")
    required = (
        COMMAND_ENVELOPE_REQUIRED_FIELDS
        if kind == "command"
        else EVENT_ENVELOPE_REQUIRED_FIELDS
    )
    missing = sorted(required - envelope.keys())
    if missing:
        raise GovernanceError(
            f"{kind.capitalize()} envelope missing required fields: {missing}"
        )
    validate_correlation_id(envelope.get("correlation_id"))
    validate_causation_id(envelope.get("causation_id"))
    actor = envelope.get("actor")
    if not isinstance(actor, dict) or actor.get("type") not in VALID_ACTOR_TYPES:
        raise GovernanceError(f"actor.type must be one of {sorted(VALID_ACTOR_TYPES)}")
    classification = envelope.get("classification")
    if classification not in VALID_CLASSIFICATIONS:
        raise GovernanceError(
            f"classification must be one of {sorted(VALID_CLASSIFICATIONS)}"
        )
    payload = envelope.get("payload")
    if payload is None:
        raise GovernanceError("payload is required (use an empty object for no data)")
    validate_sensitive_payload(payload)
    subject = envelope.get("subject") or envelope.get("command_type") or envelope.get("event_type")
    if isinstance(subject, str):
        parse_subject(subject)


__all__ = [
    "ACK_WAIT_SECONDS",
    "ALLOWED_COMMAND_DOMAINS",
    "AUDIT_SIGNALS_BUFFER_SECONDS",
    "COMMAND_CONSUMER_SPECS",
    "COMMAND_ENVELOPE_REQUIRED_FIELDS",
    "DEFAULT_RETRY_POLICY",
    "DLQ_SUBJECT_ROOT",
    "DUPLICATE_WINDOW_SECONDS",
    "EPHEMERAL_SUBJECT_ROOT",
    "EVENTS_RETENTION_SECONDS",
    "EVENT_ENVELOPE_REQUIRED_FIELDS",
    "MAX_ACK_PENDING",
    "MAX_PULL_WAIT_SECONDS",
    "NATS_MAX_PAYLOAD_BYTES",
    "NATS_PAYLOAD_HEADROOM_BYTES",
    "SENSITIVE_PAYLOAD_KEYS",
    "STREAM_AUDIT_SIGNALS",
    "STREAM_AUDIT_SIGNALS_SUBJECTS",
    "STREAM_COMMANDS",
    "STREAM_COMMANDS_SUBJECTS",
    "STREAM_EVENTS",
    "STREAM_EVENTS_SUBJECTS",
    "STREAM_NAMES",
    "STREAM_SPECS",
    "VALID_ACTOR_TYPES",
    "VALID_CLASSIFICATIONS",
    "ConsumerSpec",
    "GovernanceError",
    "RetryPolicy",
    "StreamSpec",
    "command_subject",
    "dlq_subject",
    "ephemeral_subject",
    "event_subject",
    "is_uuid_v4_or_v7",
    "parse_subject",
    "stream_spec",
    "validate_causation_id",
    "validate_correlation_id",
    "validate_envelope",
    "validate_payload_size",
    "validate_sensitive_payload",
]

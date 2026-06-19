from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

COMMAND_ENVELOPE_REQUIRED_FIELDS = frozenset(
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

VALID_CLASSIFICATIONS = frozenset({"public", "internal", "sensitive", "restricted"})

VALID_ACTOR_TYPES = frozenset({"user", "service", "agent"})


@dataclass(frozen=True)
class CommandEnvelope:
    """A validated command envelope.

    Follows the JDOS v1.2 command envelope schema defined in
    ``docs/implementation/event_contracts.md``.
    """

    command_id: str
    command_type: str
    command_version: int
    issued_at: datetime
    expires_at: datetime
    producer: str
    correlation_id: str
    causation_id: str
    idempotency_key: str
    actor: dict[str, str]
    classification: str
    payload: dict[str, Any]

    # Parsed subject components (not in the wire envelope).
    subject_domain: str = ""
    subject_action: str = ""

    def is_expired(self, now: datetime | None = None) -> bool:
        if now is None:
            now = datetime.now(tz=timezone.utc)
        return now > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "command_id": self.command_id,
            "command_type": self.command_type,
            "command_version": self.command_version,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "producer": self.producer,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "idempotency_key": self.idempotency_key,
            "actor": dict(self.actor),
            "classification": self.classification,
            "payload": dict(self.payload),
        }
        if self.subject_domain:
            d["subject_domain"] = self.subject_domain
        if self.subject_action:
            d["subject_action"] = self.subject_action
        return d


def parse_command_envelope(
    data: dict[str, Any],
    *,
    subject_domain: str = "",
    subject_action: str = "",
) -> CommandEnvelope:
    """Parse and validate a raw dict into a ``CommandEnvelope``.

    Raises ``CommandValidationError`` on structural or semantic failure.
    """
    missing = COMMAND_ENVELOPE_REQUIRED_FIELDS - data.keys()
    if missing:
        from backend.runtime.errors import CommandValidationError

        raise CommandValidationError(
            f"Command envelope missing required fields: {sorted(missing)}"
        )

    classification = data["classification"]
    if classification not in VALID_CLASSIFICATIONS:
        from backend.runtime.errors import CommandValidationError

        raise CommandValidationError(
            f"Invalid classification: {classification!r}; "
            f"must be one of {sorted(VALID_CLASSIFICATIONS)}"
        )

    actor = data["actor"]
    if not isinstance(actor, dict) or actor.get("type") not in VALID_ACTOR_TYPES:
        from backend.runtime.errors import CommandValidationError

        raise CommandValidationError(
            f"Invalid actor: {actor!r}; must have type in {sorted(VALID_ACTOR_TYPES)}"
        )

    try:
        issued_at = _parse_datetime(data["issued_at"])
        expires_at = _parse_datetime(data["expires_at"])
    except (ValueError, TypeError) as exc:
        from backend.runtime.errors import CommandValidationError

        raise CommandValidationError(f"Invalid datetime in envelope: {exc}")

    payload = data.get("payload", {})
    if not isinstance(payload, dict):
        from backend.runtime.errors import CommandValidationError

        raise CommandValidationError("payload must be a dict")

    return CommandEnvelope(
        command_id=str(data["command_id"]),
        command_type=str(data["command_type"]),
        command_version=int(data["command_version"]),
        issued_at=issued_at,
        expires_at=expires_at,
        producer=str(data.get("producer", "")),
        correlation_id=str(data["correlation_id"]),
        causation_id=str(data["causation_id"]),
        idempotency_key=str(data["idempotency_key"]),
        actor=actor,
        classification=classification,
        payload=payload,
        subject_domain=subject_domain,
        subject_action=subject_action,
    )


def deserialize_command_envelope(
    wire_bytes: bytes,
    *,
    subject_domain: str = "",
    subject_action: str = "",
) -> CommandEnvelope:
    """Deserialize a JSON byte payload and parse into a ``CommandEnvelope``."""
    try:
        data = json.loads(wire_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        from backend.runtime.errors import CommandValidationError

        raise CommandValidationError(f"Failed to deserialize command envelope: {exc}")
    if not isinstance(data, dict):
        from backend.runtime.errors import CommandValidationError

        raise CommandValidationError("Command envelope must be a JSON object")
    return parse_command_envelope(
        data,
        subject_domain=subject_domain,
        subject_action=subject_action,
    )


def build_command_envelope(
    command_type: str,
    payload: dict[str, Any],
    *,
    command_id: str | None = None,
    producer: str = "runtime",
    correlation_id: str | None = None,
    causation_id: str | None = None,
    idempotency_key: str | None = None,
    actor: dict[str, str] | None = None,
    classification: str = "internal",
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
    command_version: int = 1,
) -> CommandEnvelope:
    """Build a :class:`CommandEnvelope` with sensible defaults.

    Useful for tests and programmatic command creation.
    """
    import uuid

    now = datetime.now(tz=timezone.utc)
    cid = command_id or str(uuid.uuid4())
    return CommandEnvelope(
        command_id=cid,
        command_type=command_type,
        command_version=command_version,
        issued_at=issued_at or now,
        expires_at=expires_at or now.replace(year=now.year + 1),
        producer=producer,
        correlation_id=correlation_id or str(uuid.uuid4()),
        causation_id=causation_id or str(uuid.uuid4()),
        idempotency_key=idempotency_key or cid,
        actor=actor or {"type": "service", "id": producer},
        classification=classification,
        payload=payload,
    )


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    raise TypeError(f"Cannot parse datetime from {type(value).__name__}: {value!r}")


def serialize_command_envelope(envelope: CommandEnvelope) -> bytes:
    """Serialize a ``CommandEnvelope`` to JSON bytes for NATS transport."""
    d = envelope.to_dict()
    d.pop("subject_domain", None)
    d.pop("subject_action", None)
    return json.dumps(d, separators=(",", ":")).encode("utf-8")

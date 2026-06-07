"""Phase 01 governance unit tests.

These tests are pure in-process. They exercise the in-process parts of
the NATS governance module that the manager delegates to. No broker
connection, no database, no models.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.core.nats_governance import (  # noqa: E402
    NATS_MAX_PAYLOAD_BYTES,
    GovernanceError,
    command_subject,
    dlq_subject,
    ephemeral_subject,
    event_subject,
    parse_subject,
    validate_correlation_id,
    validate_envelope,
    validate_payload_size,
    validate_sensitive_payload,
)


# ---------------------------------------------------------------------------
# Subject construction
# ---------------------------------------------------------------------------


def test_command_subject_format() -> None:
    assert command_subject("memory", "create") == "jarvis.command.memory.create.v1"


def test_command_subject_rejects_unknown_domain() -> None:
    with pytest.raises(GovernanceError):
        command_subject("rogue", "create")


def test_command_subject_rejects_invalid_action() -> None:
    with pytest.raises(GovernanceError):
        command_subject("memory", "Create-Now!")


def test_event_subject_format() -> None:
    assert event_subject("memory", "created") == "jarvis.event.memory.created.v1"


def test_dlq_subject_format() -> None:
    assert dlq_subject("memory") == "jarvis.dlq.memory.v1"


def test_ephemeral_subject_format() -> None:
    assert ephemeral_subject("request", "progress") == "jarvis.ephemeral.request.progress.v1"


def test_parse_subject_round_trip() -> None:
    parsed = parse_subject("jarvis.event.memory.created.v1")
    assert parsed["kind"] == "event"
    assert parsed["domain"] == "memory"
    assert parsed["major"] == "1"


def test_parse_subject_rejects_unknown_shape() -> None:
    with pytest.raises(GovernanceError):
        parse_subject("not.a.jarvis.subject")


# ---------------------------------------------------------------------------
# Correlation & causation
# ---------------------------------------------------------------------------


def test_correlation_id_accepts_uuid7() -> None:
    validate_correlation_id("01975c2f-4aef-7cf1-a940-ae54bf596280")


def test_correlation_id_rejects_garbage() -> None:
    with pytest.raises(GovernanceError):
        validate_correlation_id("not-a-uuid")


def test_correlation_id_rejects_empty() -> None:
    with pytest.raises(GovernanceError):
        validate_correlation_id("")


# ---------------------------------------------------------------------------
# Payload size
# ---------------------------------------------------------------------------


def test_payload_size_accepts_under_limit() -> None:
    validate_payload_size(b"x" * (NATS_MAX_PAYLOAD_BYTES - 1))


def test_payload_size_rejects_over_limit() -> None:
    with pytest.raises(GovernanceError):
        validate_payload_size(b"x" * (NATS_MAX_PAYLOAD_BYTES + 1))


def test_payload_size_rejects_non_bytes() -> None:
    with pytest.raises(GovernanceError):
        validate_payload_size("not-bytes")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Sensitive payload scan
# ---------------------------------------------------------------------------


def test_sensitive_payload_detects_top_level_key() -> None:
    with pytest.raises(GovernanceError):
        validate_sensitive_payload({"prompt": "hello"})


def test_sensitive_payload_detects_nested_key() -> None:
    with pytest.raises(GovernanceError):
        validate_sensitive_payload({"meta": {"transcript": "hi"}})


def test_sensitive_payload_detects_list_member() -> None:
    with pytest.raises(GovernanceError):
        validate_sensitive_payload({"items": [{"document_body": "x"}]})


def test_sensitive_payload_case_insensitive() -> None:
    with pytest.raises(GovernanceError):
        validate_sensitive_payload({"API_KEY": "x"})


def test_sensitive_payload_clean_payload_passes() -> None:
    validate_sensitive_payload({"request_id": "01975c2f-4aef-7cf1-a940-ae54bf596280"})


# ---------------------------------------------------------------------------
# Envelope validation
# ---------------------------------------------------------------------------


def _good_envelope() -> dict:
    return {
        "command_id": "01975c2f-51c0-7781-b801-28af3bd9fa24",
        "command_type": "CREATE_MEMORY_COMMAND",
        "command_version": 1,
        "issued_at": "2026-06-07T06:30:00Z",
        "expires_at": "2026-06-07T06:31:00Z",
        "producer": "orchestration-service",
        "correlation_id": "01975c2f-4aef-7cf1-a940-ae54bf596280",
        "causation_id": "01975c2f-1111-7777-8888-123456789abc",
        "idempotency_key": "opaque-key",
        "actor": {"type": "agent", "id": "memory-agent"},
        "classification": "sensitive",
        "capability_grant_id": "01975c2f-2222-7777-8888-123456789abc",
        "payload": {"memory_id": "01975c2f-3333-7777-8888-123456789abc"},
    }


def test_envelope_passes_for_valid_command() -> None:
    validate_envelope(_good_envelope(), kind="command")


def test_envelope_rejects_missing_correlation_id() -> None:
    envelope = _good_envelope()
    envelope.pop("correlation_id")
    with pytest.raises(GovernanceError):
        validate_envelope(envelope, kind="command")


def test_envelope_rejects_missing_causation_id() -> None:
    envelope = _good_envelope()
    envelope.pop("causation_id")
    with pytest.raises(GovernanceError):
        validate_envelope(envelope, kind="command")


def test_envelope_rejects_sensitive_payload() -> None:
    envelope = _good_envelope()
    envelope["payload"] = {"prompt": "leak"}
    with pytest.raises(GovernanceError):
        validate_envelope(envelope, kind="command")


def test_envelope_rejects_bad_classification() -> None:
    envelope = _good_envelope()
    envelope["classification"] = "top-secret"
    with pytest.raises(GovernanceError):
        validate_envelope(envelope, kind="command")


def test_envelope_rejects_bad_actor_type() -> None:
    envelope = _good_envelope()
    envelope["actor"]["type"] = "model"
    with pytest.raises(GovernanceError):
        validate_envelope(envelope, kind="command")

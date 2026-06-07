"""Tests for the durable-NATS payload policy.

These tests exercise the governance module's envelope validator and
sensitive-payload scan. They prove that the producer-side contract
rejects prompts, raw memory, documents, embeddings, and secrets in
durable command and event envelopes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.core.nats_governance import (  # noqa: E402
    GovernanceError,
    NATS_MAX_PAYLOAD_BYTES,
    validate_envelope,
    validate_payload_size,
    validate_sensitive_payload,
)


def _envelope_with_payload(payload: dict) -> dict:
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
        "payload": payload,
    }


@pytest.mark.parametrize(
    "payload,expected_substring",
    [
        ({"prompt": "leak"}, "prompt"),
        ({"transcript": "leak"}, "transcript"),
        ({"raw_memory": "leak"}, "raw_memory"),
        ({"memory_text": "leak"}, "memory_text"),
        ({"document_body": "leak"}, "document_body"),
        ({"chunk_body": "leak"}, "chunk_body"),
        ({"embedding": [0.1, 0.2]}, "embedding"),
        ({"embedding_vector": [0.1, 0.2]}, "embedding_vector"),
        ({"raw_audio": b"x"}, "raw_audio"),
        ({"raw_image": b"x"}, "raw_image"),
        ({"api_key": "x"}, "api_key"),
        ({"password": "x"}, "password"),
        ({"token": "x"}, "token"),
        ({"private_key": "x"}, "private_key"),
    ],
)
def test_validate_sensitive_payload_rejects(payload: dict, expected_substring: str) -> None:
    with pytest.raises(GovernanceError):
        validate_sensitive_payload(payload)


def test_validate_sensitive_payload_rejects_nested_prompt() -> None:
    with pytest.raises(GovernanceError):
        validate_sensitive_payload({"meta": {"prompt": "leak"}})


def test_validate_sensitive_payload_rejects_list_with_document() -> None:
    with pytest.raises(GovernanceError):
        validate_sensitive_payload({"items": [{"document_body": "x"}]})


def test_validate_sensitive_payload_accepts_clean_payload() -> None:
    validate_sensitive_payload({"request_id": "01975c2f-4aef-7cf1-a940-ae54bf596280"})


def test_validate_envelope_rejects_prompt_in_payload() -> None:
    envelope = _envelope_with_payload({"prompt": "leak"})
    with pytest.raises(GovernanceError):
        validate_envelope(envelope, kind="command")


def test_validate_envelope_rejects_raw_memory_in_payload() -> None:
    envelope = _envelope_with_payload({"raw_memory": "leak"})
    with pytest.raises(GovernanceError):
        validate_envelope(envelope, kind="command")


def test_validate_envelope_rejects_document_in_payload() -> None:
    envelope = _envelope_with_payload({"document_body": "leak"})
    with pytest.raises(GovernanceError):
        validate_envelope(envelope, kind="command")


def test_validate_envelope_rejects_embedding_in_payload() -> None:
    envelope = _envelope_with_payload({"embedding": [0.1, 0.2]})
    with pytest.raises(GovernanceError):
        validate_envelope(envelope, kind="command")


def test_validate_envelope_rejects_secret_in_payload() -> None:
    envelope = _envelope_with_payload({"api_key": "leak"})
    with pytest.raises(GovernanceError):
        validate_envelope(envelope, kind="command")


def test_validate_envelope_accepts_clean_payload() -> None:
    envelope = _envelope_with_payload(
        {"memory_id": "01975c2f-3333-7777-8888-123456789abc"}
    )
    validate_envelope(envelope, kind="command")


def test_validate_payload_size_rejects_oversize() -> None:
    big = b"x" * (NATS_MAX_PAYLOAD_BYTES + 1)
    with pytest.raises(GovernanceError):
        validate_payload_size(big)


def test_validate_payload_size_accepts_under_limit() -> None:
    validate_payload_size(b"x" * 1024)


def test_validated_envelope_serializes_under_limit() -> None:
    envelope = _envelope_with_payload({"k": "v"})
    validate_envelope(envelope, kind="command")
    serialized = json.dumps(envelope, separators=(",", ":")).encode("utf-8")
    assert len(serialized) <= NATS_MAX_PAYLOAD_BYTES

"""Phase 02 Step 1 — Contract validation tests against JDOS v1.2 NATS governance.

Every envelope, payload, and DTO in ``shared/schemas/`` must comply with:

* ``backend.core.nats_governance`` envelope validation
* Sensitive-payload policy (Correction 5)
* Correlation/causation requirements
* Idempotency requirements
* Classification requirements
* ``extra="forbid"`` strictness
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.core.nats_governance import (  # noqa: E402
    COMMAND_ENVELOPE_REQUIRED_FIELDS,
    EVENT_ENVELOPE_REQUIRED_FIELDS,
    DEFAULT_RETRY_POLICY,
    VALID_ACTOR_TYPES,
    VALID_CLASSIFICATIONS,
    GovernanceError,
    validate_causation_id,
    validate_correlation_id,
    validate_envelope,
    validate_sensitive_payload,
)

from shared.schemas import (  # noqa: E402
    COMMAND_PAYLOAD_REGISTRY,
    EVENT_PAYLOAD_REGISTRY,
    Actor,
    ActorType,
    Classification,
    CommandEnvelope,
    EventEnvelope,
    RequestId,
)


# ===================================================================
# 1. Envelope structural alignment
# ===================================================================


class TestEnvelopeAlignment:
    """Verify that the shared envelope models produce dicts that match
    the NATS governance required-field sets."""

    def test_command_envelope_has_all_required_fields(self) -> None:
        env = CommandEnvelope(
            command_type="TEST",
            expires_at="2026-06-08T00:00:00Z",  # type: ignore[arg-type]
            producer="test",
            actor=Actor(type=ActorType.SERVICE, id="test"),
            classification=Classification.INTERNAL,
        )
        as_dict = env.model_dump()
        for field in COMMAND_ENVELOPE_REQUIRED_FIELDS:
            assert field in as_dict, f"Missing required command field: {field}"

    def test_command_envelope_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValueError, match="extra_forbidden"):
            CommandEnvelope(
                command_type="TEST",
                expires_at="2026-06-08T00:00:00Z",  # type: ignore[arg-type]
                producer="test",
                actor=Actor(type=ActorType.SERVICE, id="test"),
                classification=Classification.INTERNAL,
                unknown_field="nope",  # type: ignore[call-arg]
            )

    def test_event_envelope_has_all_required_fields(self) -> None:
        env = EventEnvelope(
            event_type="TEST",
            producer="test",
            actor=Actor(type=ActorType.SERVICE, id="test"),
            classification=Classification.INTERNAL,
        )
        as_dict = env.model_dump()
        for field in EVENT_ENVELOPE_REQUIRED_FIELDS:
            assert field in as_dict, f"Missing required event field: {field}"

    def test_event_envelope_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValueError, match="extra_forbidden"):
            EventEnvelope(
                event_type="TEST",
                producer="test",
                actor=Actor(type=ActorType.SERVICE, id="test"),
                classification=Classification.INTERNAL,
                unknown_field="nope",  # type: ignore[call-arg]
            )


# ===================================================================
# 2. NATS governance validate_envelope compatibility
# ===================================================================


class TestGovernanceCompatibility:
    """Prove that shared envelope model_dump() output passes the
    production NATS governance validate_envelope() function."""

    def _make_valid_command_dict(self, **overrides: object) -> dict:
        env = CommandEnvelope(
            command_type="CREATE_MEMORY_COMMAND",
            expires_at="2026-06-08T00:01:00Z",
            producer="test-producer",
            actor=Actor(type=ActorType.AGENT, id="memory-agent"),
            classification=Classification.SENSITIVE,
            payload={"memory_id": "01975c2f-51c0-7781-b801-28af3bd9fa24"},
        )
        d = env.model_dump()
        d["subject"] = "jarvis.command.memory.create.v1"
        d.update(overrides)
        return d

    def _make_valid_event_dict(self, **overrides: object) -> dict:
        env = EventEnvelope(
            event_type="MEMORY_CREATED",
            producer="test-producer",
            actor=Actor(type=ActorType.SERVICE, id="memory-service"),
            classification=Classification.SENSITIVE,
            payload={"memory_id": "01975c2f-51c0-7781-b801-28af3bd9fa24"},
        )
        d = env.model_dump()
        d["subject"] = "jarvis.event.memory.created.v1"
        d.update(overrides)
        return d

    def test_command_envelope_passes_governance(self) -> None:
        d = self._make_valid_command_dict()
        validate_envelope(d, kind="command")

    def test_event_envelope_passes_governance(self) -> None:
        d = self._make_valid_event_dict()
        validate_envelope(d, kind="event")

    def test_missing_command_field_rejected(self) -> None:
        d = self._make_valid_command_dict()
        del d["command_type"]
        with pytest.raises(GovernanceError, match="missing required fields"):
            validate_envelope(d, kind="command")

    def test_missing_event_field_rejected(self) -> None:
        d = self._make_valid_event_dict()
        del d["event_type"]
        with pytest.raises(GovernanceError, match="missing required fields"):
            validate_envelope(d, kind="event")

    def test_invalid_classification_rejected(self) -> None:
        d = self._make_valid_command_dict(classification="ultra")
        with pytest.raises(GovernanceError, match="classification"):
            validate_envelope(d, kind="command")

    def test_all_valid_classifications_accepted(self) -> None:
        for c in VALID_CLASSIFICATIONS:
            d = self._make_valid_command_dict(classification=c)
            validate_envelope(d, kind="command")

    def test_invalid_actor_type_rejected(self) -> None:
        d = self._make_valid_command_dict(actor={"type": "robot", "id": "r2"})
        with pytest.raises(GovernanceError, match="actor.type"):
            validate_envelope(d, kind="command")

    def test_all_valid_actor_types_accepted(self) -> None:
        for t in VALID_ACTOR_TYPES:
            d = self._make_valid_command_dict(actor={"type": t, "id": "tester"})
            validate_envelope(d, kind="command")

    def test_none_payload_rejected(self) -> None:
        d = self._make_valid_command_dict(payload=None)
        with pytest.raises(GovernanceError, match="payload is required"):
            validate_envelope(d, kind="command")

    def test_empty_payload_accepted(self) -> None:
        d = self._make_valid_command_dict(payload={})
        validate_envelope(d, kind="command")


# ===================================================================
# 3. Correlation / causation validation
# ===================================================================


class TestCorrelationAndCausation:
    """Prove that generated correlation/causation IDs satisfy the
    v1.2 UUID contract."""

    def test_command_envelope_has_valid_correlation_id(self) -> None:
        env = CommandEnvelope(
            command_type="TEST",
            expires_at="2026-06-08T00:00:00Z",  # type: ignore[arg-type]
            producer="test",
            actor=Actor(type=ActorType.SERVICE, id="test"),
            classification=Classification.INTERNAL,
        )
        validate_correlation_id(env.correlation_id)

    def test_command_envelope_has_valid_causation_id(self) -> None:
        env = CommandEnvelope(
            command_type="TEST",
            expires_at="2026-06-08T00:00:00Z",  # type: ignore[arg-type]
            producer="test",
            actor=Actor(type=ActorType.SERVICE, id="test"),
            classification=Classification.INTERNAL,
        )
        validate_causation_id(env.causation_id)

    def test_event_envelope_has_valid_correlation_id(self) -> None:
        env = EventEnvelope(
            event_type="TEST",
            producer="test",
            actor=Actor(type=ActorType.SERVICE, id="test"),
            classification=Classification.INTERNAL,
        )
        validate_correlation_id(env.correlation_id)

    def test_event_envelope_has_valid_causation_id(self) -> None:
        env = EventEnvelope(
            event_type="TEST",
            producer="test",
            actor=Actor(type=ActorType.SERVICE, id="test"),
            classification=Classification.INTERNAL,
        )
        validate_causation_id(env.causation_id)


# ===================================================================
# 4. Idempotency
# ===================================================================


class TestIdempotency:
    """Verify that every command envelope carries an idempotency_key."""

    def test_command_envelope_has_idempotency_key(self) -> None:
        env = CommandEnvelope(
            command_type="TEST",
            expires_at="2026-06-08T00:00:00Z",  # type: ignore[arg-type]
            producer="test",
            actor=Actor(type=ActorType.SERVICE, id="test"),
            classification=Classification.INTERNAL,
        )
        assert env.idempotency_key
        assert isinstance(env.idempotency_key, str)

    def test_event_envelope_has_no_idempotency_key(self) -> None:
        """Events are facts; idempotency is via event_id, not a separate key."""
        env = EventEnvelope(
            event_type="TEST",
            producer="test",
            actor=Actor(type=ActorType.SERVICE, id="test"),
            classification=Classification.INTERNAL,
        )
        assert not hasattr(env, "idempotency_key")


# ===================================================================
# 5. Classification
# ===================================================================


class TestClassification:
    """Verify that classification values are one of the four valid buckets."""

    def test_classification_enum_values_match_governance(self) -> None:
        enum_values = {c.value for c in Classification}
        assert enum_values == VALID_CLASSIFICATIONS, (
            f"Classification enum {enum_values} != governance {VALID_CLASSIFICATIONS}"
        )

    def test_command_envelope_requires_classification(self) -> None:
        env = CommandEnvelope(
            command_type="TEST",
            expires_at="2026-06-08T00:00:00Z",  # type: ignore[arg-type]
            producer="test",
            actor=Actor(type=ActorType.SERVICE, id="test"),
            classification=Classification.INTERNAL,
        )
        assert env.classification in VALID_CLASSIFICATIONS

    def test_event_envelope_requires_classification(self) -> None:
        env = EventEnvelope(
            event_type="TEST",
            producer="test",
            actor=Actor(type=ActorType.SERVICE, id="test"),
            classification=Classification.INTERNAL,
        )
        assert env.classification in VALID_CLASSIFICATIONS


# ===================================================================
# 6. Sensitive payload policy (Correction 5)
# ===================================================================


class TestSensitivePayloadPolicy:
    """Prove that payloads containing sensitive keys are rejected by
    validate_sensitive_payload."""

    PROHIBITED_KEYS = [
        "prompt",
        "transcript",
        "query_text",
        "document_body",
        "chunk_body",
        "embedding",
        "raw_audio",
        "raw_image",
        "memory_text",
        "api_key",
        "password",
        "private_key",
    ]

    def test_sensitive_keys_rejected_at_top_level(self) -> None:
        for key in self.PROHIBITED_KEYS:
            with pytest.raises(GovernanceError, match="sensitive key"):
                validate_sensitive_payload({key: "some sensitive content"})

    def test_sensitive_keys_rejected_nested(self) -> None:
        for key in self.PROHIBITED_KEYS:
            with pytest.raises(GovernanceError, match="sensitive key"):
                validate_sensitive_payload({"nested": {key: "secret"}})

    def test_reference_only_payload_accepted(self) -> None:
        payload = {
            "memory_id": "01975c2f-51c0-7781-b801-28af3bd9fa24",
            "consent_id": "01975c2f-4aef-7cf1-a940-ae54bf596280",
        }
        validate_sensitive_payload(payload)

    def test_empty_payload_accepted(self) -> None:
        validate_sensitive_payload({})

    def test_command_envelope_violation_rejected_by_governance(self) -> None:
        d = {
            "subject": "jarvis.command.memory.create.v1",
            "command_id": "01975c2f-51c0-7781-b801-28af3bd9fa24",
            "command_type": "CREATE_MEMORY_COMMAND",
            "command_version": 1,
            "issued_at": "2026-06-08T00:00:00Z",
            "expires_at": "2026-06-08T00:01:00Z",
            "producer": "test",
            "correlation_id": "01975c2f-4aef-7cf1-a940-ae54bf596280",
            "causation_id": "01975c2f-4aef-7cf1-a940-ae54bf596280",
            "idempotency_key": "01975c2f-4aef-7cf1-a940-ae54bf596280",
            "actor": {"type": "agent", "id": "memory-agent"},
            "classification": "sensitive",
            "payload": {"prompt": "Research LangGraph"},
        }
        with pytest.raises(GovernanceError, match="sensitive key"):
            validate_envelope(d, kind="command")


# ===================================================================
# 7. Command and event payload registry completeness
# ===================================================================


class TestPayloadRegistries:
    """Verify that every expected command/event type has a registered
    payload model and that each model can be instantiated."""

    EXPECTED_COMMANDS = frozenset({
        "USER_REQUEST_COMMAND",
        "SHOW_NOTIFICATION_COMMAND",
        "UPDATE_WALLPAPER_COMMAND",
        "CREATE_MEMORY_COMMAND",
        "START_RESEARCH_COMMAND",
        "OPEN_APPLICATION_COMMAND",
        "CANCEL_REQUEST_COMMAND",
        "RECORD_CONSENT_COMMAND",
        "REVOKE_CONSENT_COMMAND",
        "DELETE_MEMORY_COMMAND",
        "UPDATE_MEMORY_COMMAND",
        "UPDATE_SETTINGS_COMMAND",
        "REGISTER_KNOWLEDGE_SOURCE_COMMAND",
        "DELETE_KNOWLEDGE_SOURCE_COMMAND",
        "REINDEX_KNOWLEDGE_SOURCE_COMMAND",
        "ACKNOWLEDGE_NOTIFICATION_COMMAND",
        "DISMISS_NOTIFICATION_COMMAND",
        "INVOKE_NOTIFICATION_ACTION_COMMAND",
        "APPROVE_ACTION_COMMAND",
    })

    EXPECTED_EVENTS = frozenset({
        "USER_REQUEST_RECEIVED",
        "MEMORY_CREATED",
        "MEMORY_UPDATED",
        "MEMORY_DELETED",
        "RESEARCH_STARTED",
        "RESEARCH_COMPLETED",
        "APPLICATION_OPENED",
        "REQUEST_COMPLETED",
        "REQUEST_FAILED",
        "REQUEST_CANCELLED",
        "CONSENT_GRANTED",
        "CONSENT_REVOKED",
        "SETTINGS_UPDATED",
        "KNOWLEDGE_SOURCE_REGISTERED",
        "KNOWLEDGE_SOURCE_DELETED",
        "KNOWLEDGE_INDEXED",
        "NOTIFICATION_SHOWN",
        "NOTIFICATION_ACKNOWLEDGED",
        "NOTIFICATION_DISMISSED",
        "WALLPAPER_UPDATED",
        "POLICY_DECISION_MADE",
        "AGENT_TASK_STARTED",
        "AGENT_TASK_COMPLETED",
        "WAKE_WORD_DETECTED",
    })

    def test_all_expected_commands_registered(self) -> None:
        registered = set(COMMAND_PAYLOAD_REGISTRY.keys())
        missing = self.EXPECTED_COMMANDS - registered
        extra = registered - self.EXPECTED_COMMANDS
        assert not missing, f"Missing command registrations: {missing}"
        assert not extra, f"Unexpected command registrations: {extra}"

    def test_all_expected_events_registered(self) -> None:
        registered = set(EVENT_PAYLOAD_REGISTRY.keys())
        missing = self.EXPECTED_EVENTS - registered
        extra = registered - self.EXPECTED_EVENTS
        assert not missing, f"Missing event registrations: {missing}"
        assert not extra, f"Unexpected event registrations: {extra}"

    def test_every_command_payload_instantiable(self) -> None:
        for name, model in COMMAND_PAYLOAD_REGISTRY.items():
            instance = model.model_construct()
            assert instance is not None, f"Failed to construct {name}"

    def test_every_event_payload_instantiable(self) -> None:
        for name, model in EVENT_PAYLOAD_REGISTRY.items():
            instance = model.model_construct()
            assert instance is not None, f"Failed to construct {name}"

    def test_every_command_payload_has_extra_forbid(self) -> None:
        for name, model in COMMAND_PAYLOAD_REGISTRY.items():
            assert model.model_config.get("extra") == "forbid", (
                f"{name} payload missing extra='forbid'"
            )

    def test_every_event_payload_has_extra_forbid(self) -> None:
        for name, model in EVENT_PAYLOAD_REGISTRY.items():
            assert model.model_config.get("extra") == "forbid", (
                f"{name} payload missing extra='forbid'"
            )


# ===================================================================
# 8. RequestId import fix
# ===================================================================


class TestRequestId:
    """Verify that RequestId is properly defined and importable."""

    def test_request_id_importable(self) -> None:
        rid = RequestId()
        assert rid.value
        assert isinstance(rid.value, str)

    def test_request_id_rejects_extra(self) -> None:
        with pytest.raises(ValueError, match="extra_forbidden"):
            RequestId(value="abc", unknown="nope")  # type: ignore[call-arg]

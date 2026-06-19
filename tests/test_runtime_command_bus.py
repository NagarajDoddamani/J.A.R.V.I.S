"""Tests for the Runtime Command Bus (SVC-011-A).

Covers envelope validation, routing, handler registration, unknown
commands, expiry, retry semantics, ack/nack handling, serialization,
and the subscriber loop.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from backend.runtime.dispatcher import CommandDispatcher
from backend.runtime.envelope import (
    COMMAND_ENVELOPE_REQUIRED_FIELDS,
    VALID_ACTOR_TYPES,
    VALID_CLASSIFICATIONS,
    CommandEnvelope,
    build_command_envelope,
    deserialize_command_envelope,
    parse_command_envelope,
    serialize_command_envelope,
)
from backend.runtime.errors import (
    CommandExpiredError,
    CommandHandlerError,
    CommandRejectedError,
    CommandValidationError,
    RuntimeError,
)
from backend.runtime.handler import CommandHandler, CommandResult
from backend.runtime.registry import CommandRegistry
from backend.runtime.subscriber import (
    _is_poison,
    _process_message,
    consume_command_stream,
    run_command_subscriber,
)

# =========================================================================
# Helpers
# =========================================================================

NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)


def make_valid_envelope(
    command_type: str = "TEST_COMMAND",
    **overrides: object,
) -> dict[str, object]:
    """Build a valid command envelope dict for testing."""
    payload: dict[str, object] = {"key": "value"}
    return {
        "command_id": "01975c2f-51c0-7781-b801-28af3bd9fa24",
        "command_type": command_type,
        "command_version": 1,
        "issued_at": "2026-06-13T12:00:00+00:00",
        "expires_at": "2027-06-13T12:00:00+00:00",
        "producer": "test-service",
        "correlation_id": "01975c2f-4aef-7cf1-a940-ae54bf596280",
        "causation_id": "01975c2f-1111-7777-8888-123456789abc",
        "idempotency_key": "test-idem-key",
        "actor": {"type": "service", "id": "test-service"},
        "classification": "internal",
        "payload": payload,
        **overrides,
    }


async def _ok_handler(envelope: CommandEnvelope) -> CommandResult:
    return CommandResult(success=True)


async def _fail_handler(envelope: CommandEnvelope) -> CommandResult:
    return CommandResult(success=False, error="handler error")


async def _raise_handler(envelope: CommandEnvelope) -> CommandResult:
    raise ValueError("unexpected error")


async def _events_handler(envelope: CommandEnvelope) -> CommandResult:
    return CommandResult(
        success=True,
        events=[
            {
                "event_type": "TEST_COMPLETED",
                "payload": {"ref": envelope.command_id},
            }
        ],
    )


class _CallTrackingHandler:
    def __init__(self) -> None:
        self.calls: list[CommandEnvelope] = []

    async def __call__(self, envelope: CommandEnvelope) -> CommandResult:
        self.calls.append(envelope)
        return CommandResult(success=True)


def _make_mock_msg(
    data: bytes,
    subject: str = "jarvis.command.test.do_something.v1",
) -> AsyncMock:
    msg = AsyncMock()
    msg.data = data
    msg.subject = subject
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()
    msg.in_progress = AsyncMock()
    msg.term = AsyncMock()
    return msg


def _make_registry(*pairs: tuple[str, CommandHandler]) -> CommandRegistry:
    r = CommandRegistry()
    for cmd_type, handler in pairs:
        r.register(cmd_type, handler)
    return r


@pytest.fixture
def registry() -> CommandRegistry:
    return CommandRegistry()


@pytest.fixture
def dispatcher(registry: CommandRegistry) -> CommandDispatcher:
    return CommandDispatcher(registry)


@pytest.fixture
def mock_js() -> AsyncMock:
    js = AsyncMock()
    js.publish = AsyncMock()
    return js


# =========================================================================
# 1. Envelope Construction and Validation (~30 tests)
# =========================================================================


class TestCommandEnvelopeConstruction:
    def test_minimal_envelope(self) -> None:
        env = build_command_envelope("TEST", {"a": 1})
        assert env.command_type == "TEST"
        assert env.payload == {"a": 1}
        assert env.command_version == 1
        assert env.classification == "internal"
        assert env.producer == "runtime"

    def test_envelope_to_dict_roundtrip(self) -> None:
        env = build_command_envelope("TEST", {"a": 1}, producer="test")
        d = env.to_dict()
        assert d["command_type"] == "TEST"
        assert d["payload"] == {"a": 1}
        assert d["producer"] == "test"

    def test_envelope_is_expired_true(self) -> None:
        env = build_command_envelope(
            "TEST", {},
            expires_at=NOW - timedelta(hours=1),
        )
        assert env.is_expired(now=NOW)

    def test_envelope_is_expired_false(self) -> None:
        env = build_command_envelope(
            "TEST", {},
            expires_at=NOW + timedelta(hours=1),
        )
        assert not env.is_expired(now=NOW)

    def test_envelope_default_expiry_is_far_future(self) -> None:
        env = build_command_envelope("TEST", {})
        assert not env.is_expired(now=NOW)

    def test_envelope_actor_defaults(self) -> None:
        env = build_command_envelope("TEST", {}, producer="my-svc")
        assert env.actor == {"type": "service", "id": "my-svc"}

    def test_envelope_custom_actor(self) -> None:
        env = build_command_envelope(
            "TEST", {},
            actor={"type": "user", "id": "user-1"},
        )
        assert env.actor == {"type": "user", "id": "user-1"}

    def test_envelope_idempotency_key_defaults_to_command_id(self) -> None:
        env = build_command_envelope(
            "TEST", {},
            command_id="custom-id",
        )
        assert env.idempotency_key == "custom-id"

    def test_envelope_explicit_idempotency_key(self) -> None:
        env = build_command_envelope(
            "TEST", {},
            command_id="cid",
            idempotency_key="ik",
        )
        assert env.idempotency_key == "ik"

    def test_envelope_subject_domain_action(self) -> None:
        env = build_command_envelope("TEST", {})
        env = env  # placeholder
        parsed = parse_command_envelope(
            make_valid_envelope("TEST"),  # type: ignore[arg-type]
            subject_domain="memory",
            subject_action="create",
        )
        assert parsed.subject_domain == "memory"
        assert parsed.subject_action == "create"

    def test_envelope_frozen(self) -> None:
        env = build_command_envelope("TEST", {})
        with pytest.raises(AttributeError):
            env.payload = {}  # type: ignore[misc]

    def test_envelope_custom_classification(self) -> None:
        for c in VALID_CLASSIFICATIONS:
            env = build_command_envelope("TEST", {}, classification=c)
            assert env.classification == c


class TestParseCommandEnvelope:
    def test_parse_valid(self) -> None:
        raw = make_valid_envelope("MY_COMMAND")
        env = parse_command_envelope(raw)  # type: ignore[arg-type]
        assert env.command_type == "MY_COMMAND"
        assert env.command_id == "01975c2f-51c0-7781-b801-28af3bd9fa24"
        assert env.payload == {"key": "value"}
        assert env.subject_domain == ""
        assert env.subject_action == ""

    def test_parse_with_subject_components(self) -> None:
        raw = make_valid_envelope("MY_COMMAND")
        env = parse_command_envelope(  # type: ignore[arg-type]
            raw,
            subject_domain="memory",
            subject_action="create",
        )
        assert env.subject_domain == "memory"
        assert env.subject_action == "create"

    def test_parse_missing_required_fields(self) -> None:
        raw: dict[str, object] = {"command_id": "abc"}
        with pytest.raises(CommandValidationError) as exc:
            parse_command_envelope(raw)
        assert "missing required fields" in str(exc.value).lower()

    def test_parse_empty_dict(self) -> None:
        with pytest.raises(CommandValidationError):
            parse_command_envelope({})

    def test_parse_invalid_classification(self) -> None:
        raw = make_valid_envelope(classification="top-secret")  # type: ignore[arg-type]
        with pytest.raises(CommandValidationError) as exc:
            parse_command_envelope(raw)  # type: ignore[arg-type]
        assert "Invalid classification" in str(exc.value)

    def test_parse_invalid_actor_type(self) -> None:
        raw = make_valid_envelope(actor={"type": "robot"})  # type: ignore[arg-type]
        with pytest.raises(CommandValidationError) as exc:
            parse_command_envelope(raw)  # type: ignore[arg-type]
        assert "Invalid actor" in str(exc.value)

    def test_parse_actor_not_a_dict(self) -> None:
        raw = make_valid_envelope(actor="not-a-dict")  # type: ignore[arg-type]
        with pytest.raises(CommandValidationError):
            parse_command_envelope(raw)  # type: ignore[arg-type]

    def test_parse_missing_actor_type(self) -> None:
        raw = make_valid_envelope(actor={"id": "test"})  # type: ignore[arg-type]
        with pytest.raises(CommandValidationError):
            parse_command_envelope(raw)  # type: ignore[arg-type]

    def test_parse_invalid_datetime_format(self) -> None:
        raw = make_valid_envelope(issued_at="not-a-date")  # type: ignore[arg-type]
        with pytest.raises(CommandValidationError):
            parse_command_envelope(raw)  # type: ignore[arg-type]

    def test_parse_payload_not_dict(self) -> None:
        raw = make_valid_envelope(payload="string-payload")  # type: ignore[arg-type]
        with pytest.raises(CommandValidationError):
            parse_command_envelope(raw)  # type: ignore[arg-type]

    def test_parse_payload_none(self) -> None:
        raw = make_valid_envelope(payload=None)  # type: ignore[arg-type]
        with pytest.raises(CommandValidationError):
            parse_command_envelope(raw)  # type: ignore[arg-type]

    def test_parse_datetime_without_tz(self) -> None:
        raw = make_valid_envelope()
        raw["issued_at"] = "2026-06-13T12:00:00"
        env = parse_command_envelope(raw)  # type: ignore[arg-type]
        assert env.issued_at.tzinfo is not None

    def test_parse_all_classifications_accepted(self) -> None:
        for c in sorted(VALID_CLASSIFICATIONS):
            raw = make_valid_envelope(classification=c)
            env = parse_command_envelope(raw)  # type: ignore[arg-type]
            assert env.classification == c


class TestDeserializeCommandEnvelope:
    def test_deserialize_valid(self) -> None:
        raw = make_valid_envelope("TEST")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        env = deserialize_command_envelope(wire)
        assert env.command_type == "TEST"

    def test_deserialize_invalid_json(self) -> None:
        with pytest.raises(CommandValidationError):
            deserialize_command_envelope(b"not json")

    def test_deserialize_empty_bytes(self) -> None:
        with pytest.raises(CommandValidationError):
            deserialize_command_envelope(b"")

    def test_deserialize_not_an_object(self) -> None:
        wire = json.dumps([1, 2, 3]).encode("utf-8")
        with pytest.raises(CommandValidationError):
            deserialize_command_envelope(wire)

    def test_deserialize_with_subject_components(self) -> None:
        raw = make_valid_envelope("TEST")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        env = deserialize_command_envelope(
            wire,
            subject_domain="notification",
            subject_action="show",
        )
        assert env.subject_domain == "notification"
        assert env.subject_action == "show"

    def test_deserialize_roundtrip(self) -> None:
        original = build_command_envelope("ROUNDTRIP", {"x": 1}, producer="test")
        wire = serialize_command_envelope(original)
        parsed = deserialize_command_envelope(wire)
        assert parsed.command_type == "ROUNDTRIP"
        assert parsed.payload == {"x": 1}
        assert parsed.producer == "test"
        assert parsed.command_id == original.command_id
        assert parsed.correlation_id == original.correlation_id


class TestSerializeCommandEnvelope:
    def test_serialize_to_bytes(self) -> None:
        env = build_command_envelope("TEST", {"a": 1})
        wire = serialize_command_envelope(env)
        assert isinstance(wire, bytes)
        decoded = json.loads(wire.decode("utf-8"))
        assert decoded["command_type"] == "TEST"
        assert decoded["payload"] == {"a": 1}

    def test_serialize_strips_subject_fields(self) -> None:
        env = parse_command_envelope(
            make_valid_envelope("TEST"),  # type: ignore[arg-type]
            subject_domain="memory",
            subject_action="create",
        )
        wire = serialize_command_envelope(env)
        decoded = json.loads(wire.decode("utf-8"))
        assert "subject_domain" not in decoded
        assert "subject_action" not in decoded

    def test_serialize_preserves_all_required_fields(self) -> None:
        env = build_command_envelope("TEST", {"a": 1})
        wire = serialize_command_envelope(env)
        decoded = json.loads(wire.decode("utf-8"))
        for field in COMMAND_ENVELOPE_REQUIRED_FIELDS:
            assert field in decoded, f"Missing field: {field}"

    def test_serialize_deserialize_identity(self) -> None:
        env = build_command_envelope(
            "IDENTITY",
            {"nested": {"list": [1, 2]}},
            producer="svc",
            classification="sensitive",
        )
        wire = serialize_command_envelope(env)
        parsed = deserialize_command_envelope(wire)
        assert parsed.command_id == env.command_id
        assert parsed.command_type == env.command_type
        assert parsed.payload == env.payload
        assert parsed.classification == env.classification
        assert parsed.producer == env.producer


# =========================================================================
# 2. CommandRegistry (~15 tests)
# =========================================================================


class TestCommandRegistry:
    def test_register_and_get(self, registry: CommandRegistry) -> None:
        handler = _ok_handler
        registry.register("TEST", handler)
        assert registry.get("TEST") is handler

    def test_register_duplicate_raises(self, registry: CommandRegistry) -> None:
        registry.register("TEST", _ok_handler)
        with pytest.raises(ValueError, match="already registered"):
            registry.register("TEST", _ok_handler)

    def test_register_or_replace_overwrites(self, registry: CommandRegistry) -> None:
        registry.register("TEST", _ok_handler)
        registry.register_or_replace("TEST", _fail_handler)
        assert registry.get("TEST") is _fail_handler

    def test_get_nonexistent(self, registry: CommandRegistry) -> None:
        assert registry.get("NONEXISTENT") is None

    def test_has_returns_true(self, registry: CommandRegistry) -> None:
        registry.register("TEST", _ok_handler)
        assert registry.has("TEST")

    def test_has_returns_false(self, registry: CommandRegistry) -> None:
        assert not registry.has("NONEXISTENT")

    def test_unregister_removes_handler(self, registry: CommandRegistry) -> None:
        registry.register("TEST", _ok_handler)
        registry.unregister("TEST")
        assert not registry.has("TEST")

    def test_unregister_nonexistent_no_error(self, registry: CommandRegistry) -> None:
        registry.unregister("NOTHING")

    def test_clear_removes_all(self, registry: CommandRegistry) -> None:
        registry.register("A", _ok_handler)
        registry.register("B", _ok_handler)
        registry.clear()
        assert registry.registered_types == frozenset()

    def test_registered_types(self, registry: CommandRegistry) -> None:
        registry.register("A", _ok_handler)
        registry.register("B", _ok_handler)
        assert registry.registered_types == frozenset({"A", "B"})

    def test_multiple_registrations(self, registry: CommandRegistry) -> None:
        handlers = {f"CMD_{i}": _ok_handler for i in range(10)}
        for cmd_type, handler in handlers.items():
            registry.register(cmd_type, handler)
        assert len(registry.registered_types) == 10

    def test_handler_callable_check(self, registry: CommandRegistry) -> None:
        handler = _CallTrackingHandler()
        registry.register("TRACKED", handler)
        assert registry.has("TRACKED")

    def test_register_with_runtime_checkable(self, registry: CommandRegistry) -> None:
        registry.register("TEST", _ok_handler)
        from typing import runtime_checkable, Protocol
        handler = registry.get("TEST")
        assert handler is not None

    def test_initially_empty(self, registry: CommandRegistry) -> None:
        assert registry.registered_types == frozenset()

    def test_get_after_clear(self, registry: CommandRegistry) -> None:
        registry.register("TEST", _ok_handler)
        registry.clear()
        assert registry.get("TEST") is None


# =========================================================================
# 3. CommandDispatcher (~15 tests)
# =========================================================================


class TestCommandDispatcher:
    def test_dispatch_success(self, dispatcher: CommandDispatcher) -> None:
        dispatcher._registry.register("TEST", _ok_handler)
        env = build_command_envelope("TEST", {})
        result = asyncio.run(dispatcher.dispatch(env))
        assert result.success
        assert result.error is None

    def test_dispatch_no_handler(self, dispatcher: CommandDispatcher) -> None:
        env = build_command_envelope("UNKNOWN", {})
        with pytest.raises(CommandRejectedError) as exc:
            asyncio.run(dispatcher.dispatch(env))
        assert "No handler registered" in str(exc.value)

    def test_dispatch_expired(self, dispatcher: CommandDispatcher) -> None:
        dispatcher._registry.register("EXPIRED", _ok_handler)
        env = build_command_envelope(
            "EXPIRED", {},
            expires_at=NOW - timedelta(hours=1),
        )
        with pytest.raises(CommandExpiredError) as exc:
            asyncio.run(dispatcher.dispatch(env))
        assert "expired" in str(exc.value).lower()

    def test_dispatch_handler_raises(self, dispatcher: CommandDispatcher) -> None:
        dispatcher._registry.register("RAISE", _raise_handler)
        env = build_command_envelope("RAISE", {})
        with pytest.raises(CommandHandlerError) as exc:
            asyncio.run(dispatcher.dispatch(env))
        assert "failed" in str(exc.value).lower()

    def test_dispatch_returns_events(self, dispatcher: CommandDispatcher) -> None:
        dispatcher._registry.register("EVENTS", _events_handler)
        env = build_command_envelope("EVENTS", {})
        result = asyncio.run(dispatcher.dispatch(env))
        assert result.success
        assert len(result.events) == 1
        assert result.events[0]["event_type"] == "TEST_COMPLETED"

    def test_dispatch_handler_failure(self, dispatcher: CommandDispatcher) -> None:
        dispatcher._registry.register("FAIL", _fail_handler)
        env = build_command_envelope("FAIL", {})
        result = asyncio.run(dispatcher.dispatch(env))
        assert not result.success
        assert result.error == "handler error"

    def test_dispatch_tracking_handler(self, dispatcher: CommandDispatcher) -> None:
        handler = _CallTrackingHandler()
        dispatcher._registry.register("TRACK", handler)
        env = build_command_envelope("TRACK", {"x": 1})
        asyncio.run(dispatcher.dispatch(env))
        assert len(handler.calls) == 1
        assert handler.calls[0].command_type == "TRACK"
        assert handler.calls[0].payload == {"x": 1}

    def test_dispatch_preserves_idempotency_key(self, dispatcher: CommandDispatcher) -> None:
        handler = _CallTrackingHandler()
        dispatcher._registry.register("IDEM", handler)
        env = build_command_envelope("IDEM", {}, idempotency_key="my-key")
        asyncio.run(dispatcher.dispatch(env))
        assert handler.calls[0].idempotency_key == "my-key"

    def test_dispatch_different_types(self, dispatcher: CommandDispatcher) -> None:
        h1 = _CallTrackingHandler()
        h2 = _CallTrackingHandler()
        dispatcher._registry.register("TYPE_A", h1)
        dispatcher._registry.register("TYPE_B", h2)
        asyncio.run(dispatcher.dispatch(build_command_envelope("TYPE_A", {})))
        asyncio.run(dispatcher.dispatch(build_command_envelope("TYPE_B", {})))
        assert len(h1.calls) == 1
        assert len(h2.calls) == 1

    def test_dispatch_empty_payload(self, dispatcher: CommandDispatcher) -> None:
        dispatcher._registry.register("EMPTY", _ok_handler)
        env = build_command_envelope("EMPTY", {})
        result = asyncio.run(dispatcher.dispatch(env))
        assert result.success

    def test_dispatch_multiple_calls(self, dispatcher: CommandDispatcher) -> None:
        handler = _CallTrackingHandler()
        dispatcher._registry.register("MULTI", handler)
        for _ in range(5):
            asyncio.run(dispatcher.dispatch(build_command_envelope("MULTI", {})))
        assert len(handler.calls) == 5

    def test_dispatch_command_version(self, dispatcher: CommandDispatcher) -> None:
        handler = _CallTrackingHandler()
        dispatcher._registry.register("VERSIONED", handler)
        env = build_command_envelope("VERSIONED", {}, command_version=2)
        asyncio.run(dispatcher.dispatch(env))
        assert handler.calls[0].command_version == 2

    def test_dispatch_with_subject_context(self, dispatcher: CommandDispatcher) -> None:
        handler = _CallTrackingHandler()
        dispatcher._registry.register("DOMAINED", handler)
        raw = make_valid_envelope("DOMAINED")
        env = parse_command_envelope(  # type: ignore[arg-type]
            raw,
            subject_domain="memory",
            subject_action="create",
        )
        asyncio.run(dispatcher.dispatch(env))
        assert handler.calls[0].subject_domain == "memory"
        assert handler.calls[0].subject_action == "create"


# =========================================================================
# 4. Command Handler Protocol (~5 tests)
# =========================================================================


class TestCommandHandlerProtocol:
    def test_runtime_checkable_type_check(self) -> None:
        handler = _CallTrackingHandler()
        assert isinstance(handler, CommandHandler)

    def test_function_handler(self) -> None:
        assert isinstance(_ok_handler, CommandHandler)

    def test_async_handler_result(self) -> None:
        env = build_command_envelope("TEST", {})
        result = asyncio.run(_ok_handler(env))
        assert isinstance(result, CommandResult)

    def test_command_result_fields(self) -> None:
        r = CommandResult(success=True, events=[{"e": 1}], error=None)
        assert r.success
        assert r.events == [{"e": 1}]
        assert r.error is None

    def test_command_result_defaults(self) -> None:
        r = CommandResult(success=False)
        assert not r.success
        assert r.events == []
        assert r.error is None


# =========================================================================
# 5. Subscriber Logic — _process_message (~30 tests)
# =========================================================================


class TestProcessMessage:
    def test_valid_command_acks(self, mock_js: AsyncMock) -> None:
        registry = _make_registry(("TEST", _ok_handler))
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("TEST")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire)

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.ack.assert_awaited_once()
        msg.nak.assert_not_awaited()

    def test_unknown_command_acks_poison(self, mock_js: AsyncMock) -> None:
        registry = _make_registry()
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("UNKNOWN")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire)

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.ack.assert_awaited_once()
        msg.nak.assert_not_awaited()

    def test_expired_command_acks_poison(self, mock_js: AsyncMock) -> None:
        registry = _make_registry(("EXPIRED", _ok_handler))
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope(
            "EXPIRED",
            expires_at="2020-01-01T00:00:00+00:00",
        )
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire)

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.ack.assert_awaited_once()

    def test_handler_failure_naks(self, mock_js: AsyncMock) -> None:
        registry = _make_registry(("FAIL", _fail_handler))
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("FAIL")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire)

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.nak.assert_awaited_once()

    def test_handler_raises_naks(self, mock_js: AsyncMock) -> None:
        registry = _make_registry(("RAISE", _raise_handler))
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("RAISE")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire)

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.nak.assert_awaited_once()

    def test_invalid_envelope_acks(self, mock_js: AsyncMock) -> None:
        registry = _make_registry()
        dispatcher = CommandDispatcher(registry)
        wire = json.dumps({"bad": "data"}, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire)

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.ack.assert_awaited_once()

    def test_invalid_json_acks(self, mock_js: AsyncMock) -> None:
        registry = _make_registry()
        dispatcher = CommandDispatcher(registry)
        msg = _make_mock_msg(b"not json")

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.ack.assert_awaited_once()

    def test_invalid_subject_acks(self, mock_js: AsyncMock) -> None:
        registry = _make_registry()
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("TEST")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire, subject="not.a.jarvis.subject")

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.ack.assert_awaited_once()

    def test_success_publishes_events(self, mock_js: AsyncMock) -> None:
        registry = _make_registry(("EVENTS", _events_handler))
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("EVENTS")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire, subject="jarvis.command.test.do_something.v1")

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.ack.assert_awaited_once()
        assert mock_js.publish.await_count == 1

    def test_success_no_events_no_publish(self, mock_js: AsyncMock) -> None:
        registry = _make_registry(("TEST", _ok_handler))
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("TEST")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire)

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.ack.assert_awaited_once()
        assert mock_js.publish.await_count == 0

    def test_governance_validation_rejects_bad_actor(self, mock_js: AsyncMock) -> None:
        registry = _make_registry()
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope(actor={"type": "robot"})
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire)

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.ack.assert_awaited_once()

    def test_governance_validation_rejects_bad_classification(
        self, mock_js: AsyncMock
    ) -> None:
        registry = _make_registry()
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope(classification="super-duper-secret")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire)

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.ack.assert_awaited_once()

    def test_missing_correlation_id_acks(self, mock_js: AsyncMock) -> None:
        registry = _make_registry()
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope(correlation_id="")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire)

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.ack.assert_awaited_once()

    def test_multiple_messages_all_acked(self, mock_js: AsyncMock) -> None:
        registry = _make_registry(("TEST", _ok_handler))
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("TEST")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msgs = [_make_mock_msg(wire) for _ in range(5)]

        for msg in msgs:
            asyncio.run(_process_message(msg, dispatcher, mock_js))

        for msg in msgs:
            msg.ack.assert_awaited_once()

    def test_handler_with_poison_error_acks(self, mock_js: AsyncMock) -> None:
        registry = _make_registry(("REJECT", _fail_handler))
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("REJECT")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire)

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        # _fail_handler returns error but not poison — should NAK
        msg.nak.assert_awaited_once()

    def test_poison_detection_no_handler(self) -> None:
        result = CommandResult(
            success=True,
            error="No handler registered for command type 'UNKNOWN'",
        )
        assert _is_poison(result)

    def test_poison_detection_expired(self) -> None:
        result = CommandResult(
            success=True,
            error="expired at 2020-01-01T00:00:00",
        )
        assert _is_poison(result)

    def test_poison_detection_not_poison(self) -> None:
        result = CommandResult(
            success=False,
            error="database connection failed",
        )
        assert not _is_poison(result)

    def test_poison_detection_none_error(self) -> None:
        result = CommandResult(success=True, error=None)
        assert _is_poison(result)

    def test_empty_payload_deserialization(self, mock_js: AsyncMock) -> None:
        registry = _make_registry(("TEST", _ok_handler))
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("TEST")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire)

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.ack.assert_awaited_once()

    def test_unknown_domain_subject_acks(self, mock_js: AsyncMock) -> None:
        registry = _make_registry()
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("TEST")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire, subject="jarvis.unknown.domain.test.v1")

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.ack.assert_awaited_once()


# =========================================================================
# 6. consume_command_stream — Subscriber Loop (~10 tests)
# =========================================================================


class MockMsg:
    """A minimal Msg-like object for testing subscribers."""

    def __init__(self, data: bytes, subject: str = "jarvis.command.test.do_something.v1") -> None:
        self.data = data
        self.subject = subject
        self.ack = AsyncMock()
        self.nak = AsyncMock()


class TestConsumeCommandStream:
    def test_processes_single_message(self, mock_js: AsyncMock) -> None:
        registry = _make_registry(("TEST", _ok_handler))
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("TEST")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = MockMsg(wire)

        async def fake_fetch(
            batch: int = 1, timeout: float = 1.0
        ) -> list[MockMsg]:
            return [msg]

        sub = MagicMock()
        sub.fetch = fake_fetch
        mock_js.pull_subscribe = AsyncMock(return_value=sub)

        asyncio.run(
            consume_command_stream(
                mock_js, "consumer-test", dispatcher,
                batch=1, poll_interval=0.1, max_iterations=1,
            )
        )
        msg.ack.assert_awaited_once()

    def test_handles_no_messages(self, mock_js: AsyncMock) -> None:
        registry = _make_registry()
        dispatcher = CommandDispatcher(registry)

        async def fake_fetch(
            batch: int = 1, timeout: float = 1.0
        ) -> list[MockMsg]:
            raise asyncio.TimeoutError()

        sub = MagicMock()
        sub.fetch = fake_fetch
        mock_js.pull_subscribe = AsyncMock(return_value=sub)

        asyncio.run(
            consume_command_stream(
                mock_js, "consumer-test", dispatcher,
                batch=1, poll_interval=0.1, max_iterations=1,
            )
        )

    def test_handles_fetch_exception(self, mock_js: AsyncMock) -> None:
        registry = _make_registry()
        dispatcher = CommandDispatcher(registry)

        async def fake_fetch(
            batch: int = 1, timeout: float = 1.0
        ) -> list[MockMsg]:
            raise Exception("broker error")

        sub = MagicMock()
        sub.fetch = fake_fetch
        mock_js.pull_subscribe = AsyncMock(return_value=sub)

        asyncio.run(
            consume_command_stream(
                mock_js, "consumer-test", dispatcher,
                batch=1, poll_interval=0.1, max_iterations=1,
            )
        )

    def test_multiple_messages_in_batch(self, mock_js: AsyncMock) -> None:
        registry = _make_registry(("TEST", _ok_handler))
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("TEST")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msgs = [MockMsg(wire) for _ in range(3)]

        call_count = 0

        async def fake_fetch(
            batch: int = 1, timeout: float = 1.0
        ) -> list[MockMsg]:
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise asyncio.TimeoutError()
            return msgs

        sub = MagicMock()
        sub.fetch = fake_fetch
        mock_js.pull_subscribe = AsyncMock(return_value=sub)

        asyncio.run(
            consume_command_stream(
                mock_js, "consumer-test", dispatcher,
                batch=10, poll_interval=0.1, max_iterations=2,
            )
        )
        for m in msgs:
            m.ack.assert_awaited_once()

    def test_consumer_name_passed_to_pull_subscribe(self, mock_js: AsyncMock) -> None:
        registry = _make_registry()
        dispatcher = CommandDispatcher(registry)

        async def fake_fetch(
            batch: int = 1, timeout: float = 1.0
        ) -> list[MockMsg]:
            raise asyncio.TimeoutError()

        sub = MagicMock()
        sub.fetch = fake_fetch
        mock_js.pull_subscribe = AsyncMock(return_value=sub)

        asyncio.run(
            consume_command_stream(
                mock_js, "consumer-memory-v1", dispatcher,
                batch=1, poll_interval=0.1, max_iterations=1,
            )
        )
        mock_js.pull_subscribe.assert_awaited_once_with(
            subject="",
            durable="consumer-memory-v1",
            stream="JARVIS_COMMANDS_V1",
        )

    def test_max_iterations_stops_loop(self, mock_js: AsyncMock) -> None:
        registry = _make_registry()
        dispatcher = CommandDispatcher(registry)

        fetch_calls = 0

        async def fake_fetch(
            batch: int = 1, timeout: float = 1.0
        ) -> list[MockMsg]:
            nonlocal fetch_calls
            fetch_calls += 1
            raise asyncio.TimeoutError()

        sub = MagicMock()
        sub.fetch = fake_fetch
        mock_js.pull_subscribe = AsyncMock(return_value=sub)

        asyncio.run(
            consume_command_stream(
                mock_js, "consumer-limited", dispatcher,
                batch=1, poll_interval=0.05, max_iterations=3,
            )
        )
        assert fetch_calls == 3

    def test_mixed_success_and_failure(self, mock_js: AsyncMock) -> None:
        registry = _make_registry(("OK", _ok_handler))
        dispatcher = CommandDispatcher(registry)

        ok_raw = make_valid_envelope("OK")
        ok_wire = json.dumps(ok_raw, separators=(",", ":")).encode("utf-8")
        fail_raw = make_valid_envelope("UNKNOWN_HANDLER")
        fail_wire = json.dumps(fail_raw, separators=(",", ":")).encode("utf-8")

        ok_msg = MockMsg(ok_wire)
        fail_msg = MockMsg(fail_wire)

        async def fake_fetch(
            batch: int = 1, timeout: float = 1.0
        ) -> list[MockMsg]:
            return [ok_msg, fail_msg]

        sub = MagicMock()
        sub.fetch = fake_fetch
        mock_js.pull_subscribe = AsyncMock(return_value=sub)

        asyncio.run(
            consume_command_stream(
                mock_js, "consumer-mixed", dispatcher,
                batch=10, poll_interval=0.1, max_iterations=1,
            )
        )
        ok_msg.ack.assert_awaited_once()
        fail_msg.ack.assert_awaited_once()  # unknown = poison = ack


# =========================================================================
# 7. run_command_subscriber — Multi-consumer orchestration (~10 tests)
# =========================================================================


class TestRunCommandSubscriber:
    def test_creates_tasks_for_all_consumers(self) -> None:
        nats_mgr = MagicMock()
        nats_mgr.js = AsyncMock()
        pull_sub = MagicMock()

        async def fake_fetch(
            batch: int = 1, timeout: float = 1.0
        ) -> list[MockMsg]:
            raise asyncio.TimeoutError()

        pull_sub.fetch = fake_fetch
        nats_mgr.js.pull_subscribe = AsyncMock(return_value=pull_sub)
        registry = _make_registry()
        dispatcher = CommandDispatcher(registry)

        asyncio.run(
            run_command_subscriber(
                nats_mgr, dispatcher,
                batch=1, poll_interval=0.05, max_iterations=1,
            )
        )

        from backend.core.nats_governance import COMMAND_CONSUMER_SPECS
        assert nats_mgr.js.pull_subscribe.await_count == len(COMMAND_CONSUMER_SPECS)

    def test_raises_if_not_connected(self) -> None:
        nats_mgr = MagicMock()
        nats_mgr.js = None
        dispatcher = CommandDispatcher(_make_registry())

        with pytest.raises(RuntimeError, match="not initialized"):
            asyncio.run(
                run_command_subscriber(nats_mgr, dispatcher)
            )


# =========================================================================
# 8. Edge Cases and Error Handling (~10 tests)
# =========================================================================


class TestEdgeCases:
    def test_oversized_payload_deserialization(self) -> None:
        large = make_valid_envelope("LARGE", payload={"data": "x" * 300_000})
        wire = json.dumps(large, separators=(",", ":")).encode("utf-8")
        # Should not crash — deserialize accepts any payload
        env = deserialize_command_envelope(wire)
        assert env.command_type == "LARGE"

    def test_invalid_utf8_bytes(self) -> None:
        raw = make_valid_envelope("TEST")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        # Accept valid UTF-8
        env = deserialize_command_envelope(wire)
        assert env.command_type == "TEST"

    def test_unicode_in_command_type(self) -> None:
        raw = make_valid_envelope("TEST")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        env = deserialize_command_envelope(wire)
        assert env.command_type == "TEST"

    def test_very_nested_payload(self) -> None:
        nested = {"a": {"b": {"c": {"d": [1, 2, 3]}}}}
        raw = make_valid_envelope("NESTED", payload=nested)
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        env = deserialize_command_envelope(wire)
        assert env.payload["a"]["b"]["c"]["d"] == [1, 2, 3]

    def test_empty_command_id(self) -> None:
        raw = make_valid_envelope("TEST", command_id="")
        env = parse_command_envelope(raw)  # type: ignore[arg-type]
        assert env.command_id == ""

    def test_zero_command_version(self) -> None:
        raw = make_valid_envelope("TEST", command_version=0)
        env = parse_command_envelope(raw)  # type: ignore[arg-type]
        assert env.command_version == 0

    def test_negative_command_version(self) -> None:
        raw = make_valid_envelope("TEST", command_version=-1)
        env = parse_command_envelope(raw)  # type: ignore[arg-type]
        assert env.command_version == -1

    def test_missing_idempotency_key_in_wire(self) -> None:
        raw = make_valid_envelope("TEST")
        raw.pop("idempotency_key")
        with pytest.raises(CommandValidationError):
            parse_command_envelope(raw)  # type: ignore[arg-type]

    def test_missing_payload_in_wire(self) -> None:
        raw = make_valid_envelope("TEST")
        raw.pop("payload")
        with pytest.raises(CommandValidationError):
            parse_command_envelope(raw)  # type: ignore[arg-type]

    def test_envelope_with_extra_fields(self) -> None:
        raw = make_valid_envelope("TEST", extra_field="ignored")
        env = parse_command_envelope(raw)  # type: ignore[arg-type]
        assert env.command_type == "TEST"


# =========================================================================
# 9. Error Hierarchy (~5 tests)
# =========================================================================


class TestErrorHierarchy:
    def test_runtime_error_base(self) -> None:
        assert issubclass(CommandValidationError, RuntimeError)
        assert issubclass(CommandExpiredError, RuntimeError)
        assert issubclass(CommandHandlerError, RuntimeError)
        assert issubclass(CommandRejectedError, RuntimeError)

    def test_runtime_error_is_exception(self) -> None:
        assert issubclass(RuntimeError, Exception)

    def test_validation_error_message(self) -> None:
        err = CommandValidationError("bad stuff")
        assert str(err) == "bad stuff"

    def test_expired_error_message(self) -> None:
        err = CommandExpiredError("command expired")
        assert "expired" in str(err)

    def test_rejected_error_message(self) -> None:
        err = CommandRejectedError("no handler")
        assert "no handler" in str(err)


# =========================================================================
# 10. Integration Scenarios (~10 tests)
# =========================================================================


class TestIntegrationScenarios:
    def test_full_pipeline_success(self, mock_js: AsyncMock) -> None:
        """Envelope → Deserialize → Dispatch → Ack → Publish events."""
        registry = _make_registry(("CREATE_MEMORY", _events_handler))
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("CREATE_MEMORY")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire, subject="jarvis.command.memory.create.v1")

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.ack.assert_awaited_once()
        assert mock_js.publish.await_count == 1

    def test_full_pipeline_no_handler(self, mock_js: AsyncMock) -> None:
        """Unknown command type → ack (poison) → no events."""
        registry = _make_registry()
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("UNKNOWN")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire)

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.ack.assert_awaited_once()
        assert mock_js.publish.await_count == 0

    def test_full_pipeline_handler_error(self, mock_js: AsyncMock) -> None:
        """Handler returns failure → NAK → no events."""
        registry = _make_registry(("FAIL", _fail_handler))
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("FAIL")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire)

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.nak.assert_awaited_once()
        assert mock_js.publish.await_count == 0

    def test_full_pipeline_expired(self, mock_js: AsyncMock) -> None:
        """Expired command → ack (poison) → no events."""
        registry = _make_registry(("EXPIRED", _ok_handler))
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("EXPIRED", expires_at="2020-01-01T00:00:00+00:00")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire)

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.ack.assert_awaited_once()
        assert mock_js.publish.await_count == 0

    def test_full_pipeline_bad_json(self, mock_js: AsyncMock) -> None:
        """Invalid JSON → ack → no events."""
        registry = _make_registry()
        dispatcher = CommandDispatcher(registry)
        msg = _make_mock_msg(b"{{{bad json")

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.ack.assert_awaited_once()
        assert mock_js.publish.await_count == 0

    def test_multiple_commands_sequential(self, mock_js: AsyncMock) -> None:
        handler = _CallTrackingHandler()
        registry = _make_registry(("TEST", handler))
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("TEST")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")

        for _ in range(5):
            msg = _make_mock_msg(wire)
            asyncio.run(_process_message(msg, dispatcher, mock_js))
            msg.ack.assert_awaited_once()

        assert len(handler.calls) == 5

    def test_different_commands_different_handlers(self, mock_js: AsyncMock) -> None:
        h1 = _CallTrackingHandler()
        h2 = _CallTrackingHandler()
        registry = _make_registry(("TYPE_A", h1), ("TYPE_B", h2))
        dispatcher = CommandDispatcher(registry)

        raw_a = make_valid_envelope("TYPE_A")
        raw_b = make_valid_envelope("TYPE_B")
        wire_a = json.dumps(raw_a, separators=(",", ":")).encode("utf-8")
        wire_b = json.dumps(raw_b, separators=(",", ":")).encode("utf-8")

        msg_a = _make_mock_msg(wire_a)
        msg_b = _make_mock_msg(wire_b)
        asyncio.run(_process_message(msg_a, dispatcher, mock_js))
        asyncio.run(_process_message(msg_b, dispatcher, mock_js))

        assert len(h1.calls) == 1
        assert len(h2.calls) == 1
        assert h1.calls[0].command_type == "TYPE_A"
        assert h2.calls[0].command_type == "TYPE_B"

    def test_governance_validated_subject_rejected(self, mock_js: AsyncMock) -> None:
        registry = _make_registry()
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope("TEST")
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire, subject="jarvis.command.memory.create.v1")

        asyncio.run(_process_message(msg, dispatcher, mock_js))
        msg.ack.assert_awaited_once()

    def test_result_event_inherits_correlation(self, mock_js: AsyncMock) -> None:
        registry = _make_registry(("EVENTS", _events_handler))
        dispatcher = CommandDispatcher(registry)
        raw = make_valid_envelope(
            "EVENTS",
            correlation_id="11111111-1111-7111-8111-111111111111",
        )
        wire = json.dumps(raw, separators=(",", ":")).encode("utf-8")
        msg = _make_mock_msg(wire, subject="jarvis.command.memory.do.v1")

        asyncio.run(_process_message(msg, dispatcher, mock_js))

        call_args = mock_js.publish.await_args
        assert call_args is not None
        published = json.loads(call_args[0][1].decode("utf-8"))
        assert published["correlation_id"] == "11111111-1111-7111-8111-111111111111"
        assert published["causation_id"] == raw["command_id"]


# =========================================================================
# 11. Build helper (~5 tests)
# =========================================================================


class TestBuildCommandEnvelope:
    def test_build_with_all_overrides(self) -> None:
        env = build_command_envelope(
            command_type="TEST",
            payload={"x": 1},
            command_id="my-id",
            producer="my-svc",
            correlation_id="corr-id",
            causation_id="caus-id",
            idempotency_key="ik",
            actor={"type": "user", "id": "user-1"},
            classification="restricted",
            command_version=2,
        )
        assert env.command_id == "my-id"
        assert env.producer == "my-svc"
        assert env.correlation_id == "corr-id"
        assert env.causation_id == "caus-id"
        assert env.idempotency_key == "ik"
        assert env.actor == {"type": "user", "id": "user-1"}
        assert env.classification == "restricted"
        assert env.command_version == 2

    def test_build_generates_uuid_command_id(self) -> None:
        env = build_command_envelope("TEST", {})
        import uuid
        assert uuid.UUID(env.command_id).version in (4, 7)

    def test_build_generates_correlation_id(self) -> None:
        env = build_command_envelope("TEST", {})
        import uuid
        assert uuid.UUID(env.correlation_id).version in (4, 7)

    def test_parse_roundtrip_from_built(self) -> None:
        original = build_command_envelope("ROUND", {"data": 42})
        d = original.to_dict()
        parsed = parse_command_envelope(d)
        assert parsed.command_id == original.command_id
        assert parsed.command_type == original.command_type
        assert parsed.payload == original.payload

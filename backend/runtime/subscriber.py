"""NATS command subscriber infrastructure.

Provides the pull-based consumer loop that bridges NATS commands
to the dispatcher. Each domain gets its own durable consumer from
the pre-bootstrapped ``COMMAND_CONSUMER_SPECS`` in the governance
layer.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from nats.aio.msg import Msg
from nats.js import JetStreamContext

from backend.core.logging import logger
from backend.core.nats import NatsManager
from backend.core.nats_governance import (
    STREAM_COMMANDS,
    parse_subject,
    validate_envelope,
)
from backend.runtime.dispatcher import CommandDispatcher
from backend.runtime.envelope import (
    CommandEnvelope,
    deserialize_command_envelope,
)
from backend.runtime.errors import (
    CommandExpiredError,
    CommandRejectedError,
    RuntimeError,
)
from backend.runtime.handler import CommandResult


async def consume_command_stream(
    js: JetStreamContext,
    consumer_name: str,
    dispatcher: CommandDispatcher,
    *,
    batch: int = 1,
    poll_interval: float = 1.0,
    max_iterations: int = 0,
) -> None:
    """Pull-based consumer loop for a single command consumer.

    For each message:
        1. Deserialize envelope from JSON bytes.
        2. Validate envelope structure against governance rules.
        3. Parse subject to extract domain/action.
        4. Dispatch to the registered handler.
        5. On success: ACK the message; publish any resulting events.
        6. On expected failure (expired, no handler): ACK (poison).
        7. On unexpected failure: NAK (retry).

    When *max_iterations* > 0 the loop exits after that many
    iterations (useful for testing).
    """
    sub = await js.pull_subscribe(
        subject="",
        durable=consumer_name,
        stream=STREAM_COMMANDS,
    )
    logger.info(
        "Command subscriber attached",
        consumer=consumer_name,
        stream=STREAM_COMMANDS,
    )

    _iterations = 0
    while True:
        _iterations += 1
        try:
            messages = await sub.fetch(batch=batch, timeout=poll_interval)
        except asyncio.TimeoutError:
            if 0 < max_iterations <= _iterations:
                break
            continue
        except Exception:
            logger.exception("Fetch failed in command subscriber", consumer=consumer_name)
            if 0 < max_iterations <= _iterations:
                break
            await asyncio.sleep(poll_interval)
            continue

        for msg in messages:
            await _process_message(msg, dispatcher, js)

        if 0 < max_iterations <= _iterations:
            break


async def _process_message(msg: Msg, dispatcher: CommandDispatcher, js: JetStreamContext) -> None:
    """Process a single NATS message through the command pipeline."""
    subject = msg.subject
    data = msg.data

    # 1. Extract subject components
    try:
        subject_parts = parse_subject(subject)
    except Exception as exc:
        logger.warning("Unknown subject, ack and skip", subject=subject, error=str(exc))
        await msg.ack()
        return

    domain = subject_parts.get("domain", "")
    action = subject_parts.get("action", "")

    # 2. Deserialize envelope
    try:
        envelope = deserialize_command_envelope(
            data,
            subject_domain=domain,
            subject_action=action,
        )
    except RuntimeError as exc:
        logger.warning("Invalid envelope, ack and skip", subject=subject, error=str(exc))
        await msg.ack()
        return

    # 3. Governance envelope validation
    try:
        validate_envelope(envelope.to_dict(), kind="command")
    except Exception as exc:
        logger.warning("Governance validation failed, ack and skip", error=str(exc))
        await msg.ack()
        return

    # 4. Dispatch to handler
    result = await _dispatch_safe(dispatcher, envelope)

    # 5. Ack/NAK
    if result.success:
        await msg.ack()
        logger.info(
            "Command processed",
            command_id=envelope.command_id,
            command_type=envelope.command_type,
            subject=subject,
        )
        # Publish resulting events
        for event_payload in result.events:
            await _publish_result_event(js, envelope, event_payload)
    else:
        is_poison = _is_poison(result)
        if is_poison:
            await msg.ack()
            logger.warning(
                "Poison command, acked",
                command_id=envelope.command_id,
                command_type=envelope.command_type,
                error=result.error,
            )
        else:
            await msg.nak()
            logger.warning(
                "Command failed, nak",
                command_id=envelope.command_id,
                command_type=envelope.command_type,
                error=result.error,
            )


async def _dispatch_safe(dispatcher: CommandDispatcher, envelope: CommandEnvelope) -> CommandResult:
    """Dispatch and return a safe result, catching expected errors."""
    try:
        return await dispatcher.dispatch(envelope)
    except CommandExpiredError as exc:
        return CommandResult(success=True, error=str(exc))
    except CommandRejectedError as exc:
        return CommandResult(success=True, error=str(exc))
    except RuntimeError as exc:
        return CommandResult(success=False, error=str(exc))
    except Exception as exc:
        return CommandResult(success=False, error=str(exc))


def _is_poison(result: CommandResult) -> bool:
    """Return True if the result represents a poison message.

    Poison messages are those that can never succeed (e.g. unknown
    command type, expired, invalid envelope). They should be ACKed
    to avoid infinite retry.
    """
    if result.error is None:
        return True
    poison_indicators = (
        "No handler registered for command type",
        "expired at",
        "Failed to deserialize",
        "Invalid classification",
        "Missing required fields",
    )
    return any(indicator in result.error for indicator in poison_indicators)


async def _publish_result_event(
    js: JetStreamContext,
    envelope: CommandEnvelope,
    event_payload: dict[str, Any],
) -> None:
    """Publish a resulting event after command execution.

    The event inherits the command's correlation_id and uses the
    command's command_id as its causation_id.
    """
    result_envelope = {
        "event_id": event_payload.get("event_id"),
        "event_type": event_payload.get("event_type", "UNKNOWN"),
        "event_version": 1,
        "occurred_at": event_payload.get(
            "occurred_at", envelope.issued_at.isoformat()
        ),
        "producer": envelope.producer,
        "correlation_id": envelope.correlation_id,
        "causation_id": envelope.command_id,
        "actor": dict(envelope.actor),
        "classification": envelope.classification,
        "trace_context": {},
        "payload": event_payload.get("payload", {}),
    }
    subject = event_payload.get(
        "subject",
        f"jarvis.event.{envelope.subject_domain}.{event_payload.get('event_type', 'unknown').lower()}.v1",
    )
    try:
        serialized = json.dumps(result_envelope, separators=(",", ":")).encode("utf-8")
        await js.publish(subject, serialized)
        logger.info(
            "Result event published",
            subject=subject,
            command_id=envelope.command_id,
        )
    except Exception as exc:
        logger.error("Failed to publish result event", error=str(exc))


async def run_command_subscriber(
    nats_manager: NatsManager,
    dispatcher: CommandDispatcher,
    *,
    batch: int = 1,
    poll_interval: float = 1.0,
    max_iterations: int = 0,
) -> None:
    """Run command subscribers for all pre-bootstrapped consumers.

    Attaches to every durable consumer defined in
    ``COMMAND_CONSUMER_SPECS`` and polls for commands.
    When *max_iterations* > 0 the loop exits after that many
    iterations (useful for testing).
    """
    if nats_manager.js is None:
        raise RuntimeError("NATS JetStream context is not initialized")

    from backend.core.nats_governance import COMMAND_CONSUMER_SPECS

    tasks: list[asyncio.Task[None]] = []
    for spec in COMMAND_CONSUMER_SPECS:
        task = asyncio.create_task(
            consume_command_stream(
                nats_manager.js,
                spec.name,
                dispatcher,
                batch=batch,
                poll_interval=poll_interval,
                max_iterations=max_iterations,
            )
        )
        tasks.append(task)
        logger.info("Command subscriber task created", consumer=spec.name)

    if tasks:
        await asyncio.gather(*tasks)

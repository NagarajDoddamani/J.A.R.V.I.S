"""NATS runtime manager wired to JDOS v1.2 governance.

This module is intentionally thin: it owns the connection, performs the
one-time bootstrap of the three v1.2 streams, exposes publish/subscribe
helpers that enforce the envelope and payload-size contracts, and never
hard-codes a subject or retry budget.

All policy lives in :mod:`backend.core.nats_governance`. The manager
imports those declarations and applies them at the broker boundary.
"""

from __future__ import annotations

import json
import random
from typing import Any

import nats
from nats.aio.client import Client as NatsClient
from nats.errors import TimeoutError as NatsTimeoutError
from nats.js import JetStreamContext
from nats.js.api import (
    AckPolicy,
    ConsumerConfig,
    DeliverPolicy,
    DiscardPolicy,
    RetentionPolicy,
    StorageType,
    StreamConfig,
)

from backend.core.config import settings
from backend.core.logging import logger
from backend.core.nats_governance import (
    COMMAND_CONSUMER_SPECS,
    DEFAULT_RETRY_POLICY,
    STREAM_NAMES,
    STREAM_SPECS,
    ConsumerSpec,
    GovernanceError,
    RetryPolicy,
    StreamSpec,
    validate_envelope,
    validate_payload_size,
)


def _retention_policy(name: str) -> RetentionPolicy:
    return RetentionPolicy.WORK_QUEUE if name == "work_queue" else RetentionPolicy.LIMITS


def _storage_type(name: str) -> StorageType:
    return StorageType.FILE if name == "file" else StorageType.MEMORY


def _discard_policy(name: str) -> DiscardPolicy:
    return DiscardPolicy.OLD if name == "old" else DiscardPolicy.NEW


def _build_stream_config(spec: StreamSpec) -> StreamConfig:
    return StreamConfig(
        name=spec.name,
        subjects=list(spec.subjects),
        retention=_retention_policy(spec.retention),
        max_age=spec.max_age_seconds,
        max_msgs=-1,
        max_bytes=-1,
        max_msg_size=spec.max_msg_size,
        storage=_storage_type(spec.storage),
        discard=_discard_policy(spec.discard),
        num_replicas=spec.num_replicas,
        duplicate_window=spec.duplicate_window_seconds,
        description=spec.description,
    )


def _build_consumer_config(spec: ConsumerSpec) -> ConsumerConfig:
    return ConsumerConfig(
        durable_name=spec.name,
        name=spec.name,
        description=spec.description,
        ack_policy=AckPolicy.EXPLICIT,
        ack_wait=spec.ack_wait_seconds,
        max_deliver=spec.max_deliver,
        max_ack_pending=spec.max_ack_pending,
        filter_subjects=list(spec.filter_subjects),
        deliver_policy=DeliverPolicy.ALL,
    )


class NatsManager:
    """Connection + governance bootstrap for the local NATS cluster."""

    def __init__(self) -> None:
        self.nc: NatsClient | None = None
        self.js: JetStreamContext | None = None
        self._connected = False
        self._bootstrap_complete = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Connect to NATS and bootstrap the v1.2 governance topology."""
        if self._connected:
            return
        try:
            self.nc = await nats.connect(
                settings.NATS_URL,
                connect_timeout=10,
                reconnect_time_wait=2,
                max_reconnect_attempts=60,
                name=f"{settings.PROJECT_NAME}-backend",
            )
            self.js = self.nc.jetstream()
            self._connected = True
            logger.info("NATS connected", url=settings.NATS_URL)
        except Exception as exc:
            logger.error("NATS connection failed", error=str(exc))
            raise

    async def bootstrap_governance(self) -> None:
        """Idempotently create the three v1.2 streams and core consumers.

        Failures are logged but never raised, so that downstream services
        can degrade gracefully while the operator inspects the cause.
        Production deployments should run this from a controlled init
        job and fail-closed on error.
        """
        if not self._connected or self.js is None:
            raise GovernanceError("NATS not connected; call connect() first")
        if self._bootstrap_complete:
            return

        await self._ensure_streams()
        await self._ensure_core_command_consumers()
        self._bootstrap_complete = True
        logger.info("NATS governance bootstrap complete", streams=list(STREAM_NAMES))

    async def _ensure_streams(self) -> None:
        assert self.js is not None
        for spec in STREAM_SPECS:
            try:
                await self.js.add_stream(_build_stream_config(spec))
                logger.info("Stream ready", stream=spec.name, retention=spec.retention)
            except Exception as exc:
                logger.error(
                    "Stream bootstrap failed",
                    stream=spec.name,
                    error=str(exc),
                )
                raise

    async def _ensure_core_command_consumers(self) -> None:
        assert self.js is not None
        for spec in COMMAND_CONSUMER_SPECS:
            try:
                await self.js.add_consumer(stream=spec.stream, config=_build_consumer_config(spec))
                logger.info("Consumer ready", stream=spec.stream, consumer=spec.name)
            except Exception as exc:
                logger.warning(
                    "Consumer bootstrap skipped",
                    stream=spec.stream,
                    consumer=spec.name,
                    error=str(exc),
                )

    async def close(self) -> None:
        if self.nc is not None:
            try:
                await self.nc.close()
            finally:
                self.nc = None
                self.js = None
                self._connected = False
                self._bootstrap_complete = False
                logger.info("NATS connection closed")

    async def is_healthy(self) -> bool:
        if not self._connected or self.nc is None:
            return False
        try:
            return self.nc.is_connected
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Publish path
    # ------------------------------------------------------------------

    async def publish(
        self,
        subject: str,
        envelope: dict[str, Any],
        *,
        kind: str = "event",
    ) -> Any:
        """Validate, serialize, and publish an envelope.

        Performs four checks before opening a connection to the broker:

        1. Structural envelope validation (required fields, actor, classification).
        2. Sensitive-payload scan (Correction 5).
        3. Serialized-size boundary at ``NATS_MAX_PAYLOAD_BYTES``.
        4. Subject parse against the v1.2 conventions.
        """
        if not self._connected or self.js is None:
            raise GovernanceError("NATS not connected; call connect() first")
        validate_envelope(envelope, kind=kind)
        serialized = json.dumps(envelope, separators=(",", ":")).encode("utf-8")
        validate_payload_size(serialized)
        headers = {
            "Nats-Msg-Id": str(envelope.get("correlation_id", "")),
            "X-Correlation-ID": str(envelope.get("correlation_id", "")),
            "X-Causation-ID": str(envelope.get("causation_id", "")),
            "X-Jarvis-Producer": str(envelope.get("producer", "")),
            "X-Jarvis-Msg-Id": str(
                envelope.get("command_id") or envelope.get("event_id", "")
            ),
        }
        ack = await self.js.publish(subject, serialized, headers=headers)
        logger.info(
            "Published",
            subject=subject,
            kind=kind,
            correlation_id=envelope.get("correlation_id"),
            stream=ack.stream if hasattr(ack, "stream") else None,
            seq=ack.seq if hasattr(ack, "seq") else None,
        )
        return ack

    # ------------------------------------------------------------------
    # Subscribe path
    # ------------------------------------------------------------------

    async def pull_subscribe(
        self,
        consumer: str,
        stream: str,
        *,
        batch: int = 1,
        timeout: int = 2,
    ) -> Any:
        """Attach to a previously-bootstrapped durable consumer.

        No ``config`` is passed because the consumer was created with
        its full governance configuration during ``bootstrap_governance``;
        passing an override here would attempt to mutate the existing
        consumer and is not what we want.
        """
        if not self._connected or self.js is None:
            raise GovernanceError("NATS not connected; call connect() first")
        return await self.js.pull_subscribe(
            subject="",
            durable=consumer,
            stream=stream,
        )

    async def fetch_one(self, sub: Any, *, timeout: int = 2) -> Any:
        """Fetch a single message, raising on timeout."""
        try:
            return await sub.fetch(batch=1, timeout=timeout)
        except NatsTimeoutError as exc:
            raise GovernanceError("NATS fetch timeout") from exc


# ---------------------------------------------------------------------------
# Retry helper (used by consumer runtimes in later phases)
# ---------------------------------------------------------------------------


def backoff_ms(attempt: int, policy: RetryPolicy = DEFAULT_RETRY_POLICY) -> int:
    """Return the wait time in milliseconds for ``attempt`` (1-indexed)."""
    capped = policy.delay_ms(attempt)
    if not policy.jitter:
        return capped
    return random.randint(0, capped)


# ---------------------------------------------------------------------------
# Module singleton + dependency-injection helpers
# ---------------------------------------------------------------------------

nats_manager = NatsManager()


async def get_nats_client() -> NatsClient:
    if nats_manager.nc is None:
        raise GovernanceError("NATS client is not initialized")
    return nats_manager.nc


async def get_jetstream_context() -> JetStreamContext:
    if nats_manager.js is None:
        raise GovernanceError("JetStream context is not initialized")
    return nats_manager.js


# Re-export public surface for downstream consumers
__all__ = [
    "backoff_ms",
    "get_jetstream_context",
    "get_nats_client",
    "nats_manager",
]

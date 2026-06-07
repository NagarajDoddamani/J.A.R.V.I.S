# NATS Governance (JDOS v1.2 — Correction 10)

**Status:** Implemented in `backend/core/nats_governance.py` and `backend/core/nats.py`
**Effective date:** 2026-06-07
**Authority:** This document is the operator-facing companion to the
declarative governance module. Both are derived from
`docs/architecture/JDOS_v1.2_Architecture_Corrections_Addendum.md`.

## 1. Topology

Three durable JetStream streams are bootstrapped on backend startup
(when `NATS_AUTO_BOOTSTRAP=true`):

| Stream | Subject filter | Retention | Age | Max payload | Description |
|---|---|---|---|---|---|
| `JARVIS_COMMANDS_V1` | `jarvis.command.>` | work-queue | unlimited | 256 KiB | Single-owner imperative commands. Reference-only payloads. |
| `JARVIS_EVENTS_V1` | `jarvis.event.>` | limits | 30 d (default) | 256 KiB | Multi-subscriber factual events. Reference-only payloads. |
| `JARVIS_AUDIT_SIGNALS_V1` | `jarvis.audit.signal.>` | limits | 7 d | 256 KiB | Reference-only audit delivery signals for the Audit Service. |

Each stream enforces the **256 KiB serialized-message limit** (Correction 10).
The runtime manager rejects oversize payloads at the producer boundary
before opening a connection to the broker.

## 2. Subject Conventions

| Type | Pattern | Example |
|---|---|---|
| Command | `jarvis.command.<domain>.<action>.v<major>` | `jarvis.command.memory.create.v1` |
| Event | `jarvis.event.<domain>.<past-tense-fact>.v<major>` | `jarvis.event.memory.created.v1` |
| Ephemeral | `jarvis.ephemeral.<domain>.<state>.v<major>` | `jarvis.ephemeral.request.progress.v1` |
| Dead letter | `jarvis.dlq.<domain>.v<major>` | `jarvis.dlq.memory.v1` |
| Audit signal | `jarvis.audit.signal.<domain>.v<major>` | `jarvis.audit.signal.consent.v1` |

Breaking changes require a new major version subject. A 256 KiB
envelope headroom is reserved on top of the limit; the runtime adds
`X-Correlation-ID`, `X-Causation-ID`, `X-Jarvis-Producer`, and
`X-Jarvis-Msg-Id` headers to every published message.

## 3. Envelope Validation

The governance module validates four invariants before any publish:

1. **Structural envelope.** Command envelopes require
   `command_id, command_type, command_version, issued_at, expires_at,
   producer, correlation_id, causation_id, idempotency_key, actor,
   classification, payload`.
   Event envelopes require the analogous set with `event_*` and
   `occurred_at`. Unknown fields are rejected (`extra="forbid"`).
2. **Correlation & causation IDs.** Both must be present and parse as
   a UUID (v4 or v7). Causation may be `null` only for the initial
   `USER_REQUEST_COMMAND` of a conversation.
3. **Actor and classification.** `actor.type ∈ {user, service, agent}`;
   `classification ∈ {public, internal, sensitive, restricted}`.
4. **Sensitive payload scan.** Recursive, case-insensitive scan that
   rejects durable messages carrying any of the keys declared in
   `SENSITIVE_PAYLOAD_KEYS` (e.g. `prompt`, `transcript`, `query_text`,
   `document_body`, `embedding`, `api_key`, `password`).

Validation runs both at the producer (`backend.core.nats.NatsManager.publish`)
and at every consumer boundary (defence in depth).

## 4. Retry & Dead Letter

Default retry budget:

| Parameter | Value |
|---|---|
| Max delivery attempts | 5 |
| Backoff base | 250 ms |
| Backoff cap | 30 s |
| Backoff shape | exponential with full jitter |
| Ack-wait | 30 s |
| Max ack-pending | 1000 |
| Duplicate window | 120 s |

Exhausted messages are routed to `jarvis.dlq.<domain>.v1` with a
**metadata-only** payload (no original content). The owning service
owns triage; the Audit Service and Security capability receive
reference-only signals. Replay is always authorized, requires a
reason, propagates the correlation ID, and is recorded in the audit
log.

The `backoff_ms(attempt)` helper in `backend.core.nats` returns the
wait time in milliseconds; consumer runtimes in later phases use it
when sleeping between fetch attempts.

## 5. Consumers

The runtime pre-creates one durable consumer per allowed command
domain (see `COMMAND_CONSUMER_SPECS`). Each consumer is a pull
consumer with explicit ack, `max_deliver=5`, and a single filter
subject `jarvis.command.<domain>.>.v1`.

Adding a new command domain is a two-step operation:

1. Add the domain to `ALLOWED_COMMAND_DOMAINS` in
   `backend/core/nats_governance.py`.
2. Extend `COMMAND_CONSUMER_SPECS` with the matching consumer spec.

Both edits require an ADR.

## 6. Bootstrap

Bootstrap is idempotent and safe to run on every backend startup:

```python
await nats_manager.connect()
await nats_manager.bootstrap_governance()
```

`bootstrap_governance()` is no-op if the manager is already
bootstrapped. Set `NATS_AUTO_BOOTSTRAP=false` in production to opt
out of automatic bootstrap and run the bootstrap from a controlled
init job that fails closed on error.

## 7. Sensitive Payload Scan (Correction 5)

The same sensitive-payload scan is exposed at the API gateway
middleware (see `backend/core/payload_policy.py`) and at the consumer
boundary (defence in depth). Adding a new sensitive key is a code
change in `SENSITIVE_PAYLOAD_KEYS` plus a contract update in
`docs/implementation/event_contracts.md`.

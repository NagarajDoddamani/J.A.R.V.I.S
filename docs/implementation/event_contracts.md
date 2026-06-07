# Command and Event Contracts

**Contract version:** 1.2  
**Encoding:** UTF-8 JSON  
**Transport:** NATS Core or JetStream  
**Governing addendum:** `../architecture/JDOS_v1.2_Architecture_Corrections_Addendum.md`

## Command Architecture

Commands request future actions. Each command has exactly one owning handler,
uses an imperative name, has an expiry, and is processed idempotently.

| Command | Subject | Single owning handler | Durability |
|---|---|---|---|
| `USER_REQUEST_COMMAND` | `jarvis.command.request.submit.v1` | Planner Agent | JetStream |
| `SHOW_NOTIFICATION_COMMAND` | `jarvis.command.notification.show.v1` | Notification Service | JetStream |
| `UPDATE_WALLPAPER_COMMAND` | `jarvis.command.wallpaper.update.v1` | Wallpaper Engine | JetStream |
| `CREATE_MEMORY_COMMAND` | `jarvis.command.memory.create.v1` | Memory Service | JetStream |
| `START_RESEARCH_COMMAND` | `jarvis.command.research.start.v1` | Research Agent | JetStream |
| `OPEN_APPLICATION_COMMAND` | `jarvis.command.automation.open_application.v1` | Automation Agent | JetStream |

The JARVIS Core Agent governs orchestration, policy, approvals, cancellation,
and compensation. Command ownership identifies the sole component authorized to
execute and acknowledge that command.

## Event Architecture

Events describe facts that already happened. They use past-tense names and may
have multiple subscribers.

| Event | Subject | Producer | Durability |
|---|---|---|---|
| `USER_REQUEST_RECEIVED` | `jarvis.event.request.received.v1` | Planner Agent | JetStream |
| `MEMORY_CREATED` | `jarvis.event.memory.created.v1` | Memory Service | JetStream |
| `MEMORY_UPDATED` | `jarvis.event.memory.updated.v1` | Memory Service | JetStream |
| `RESEARCH_STARTED` | `jarvis.event.research.started.v1` | Research Agent | JetStream |
| `RESEARCH_COMPLETED` | `jarvis.event.research.completed.v1` | Research Agent | JetStream |
| `APPLICATION_OPENED` | `jarvis.event.automation.application_opened.v1` | Automation Agent | JetStream |

`NOTIFICATION_SHOW` and `WALLPAPER_UPDATE` are retired as event names. Their
correct contracts are `SHOW_NOTIFICATION_COMMAND` and
`UPDATE_WALLPAPER_COMMAND`. Handlers may later register the factual events
`NOTIFICATION_SHOWN` and `WALLPAPER_UPDATED`.

## Subject Convention

- Commands: `jarvis.command.<domain>.<action>.v<major>`.
- Events: `jarvis.event.<domain>.<past-tense-fact>.v<major>`.
- Ephemeral state: `jarvis.ephemeral.<domain>.<state>.v<major>`.
- Dead letter: `jarvis.dlq.<domain>.v<major>`.

## Command Envelope

```json
{
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
  "payload": {}
}
```

Required fields are command ID/type/version, issue/expiry time, producer,
correlation/causation IDs, idempotency key, actor, classification, capability
grant where applicable, and typed payload.

## Event Envelope

```json
{
  "event_id": "01975c2f-6d72-7f18-9ae2-c63f11c64f10",
  "event_type": "MEMORY_CREATED",
  "event_version": 1,
  "occurred_at": "2026-06-07T06:30:00Z",
  "producer": "memory-service",
  "correlation_id": "01975c2f-4aef-7cf1-a940-ae54bf596280",
  "causation_id": "01975c2f-51c0-7781-b801-28af3bd9fa24",
  "actor": {"type": "service", "id": "memory-service"},
  "classification": "sensitive",
  "trace_context": {"traceparent": "00-..."},
  "payload": {}
}
```

Required fields are event ID/type/version, occurrence time, producer,
correlation/causation IDs, actor, classification, trace context, and payload.

Unknown envelope fields are rejected within a major version. Consumers ignore
unknown optional payload fields for compatible additive changes.

## Sensitive Event Policy

Durable commands and events MUST NOT contain:

- User prompts, voice transcripts, or research queries.
- Personal content, documents, document chunks, or research results.
- Memory text or embedding vectors.
- Raw audio, images, screenshots, credentials, tokens, or secrets.

Durable payloads contain IDs, opaque authorized resource references,
classification, purpose, revisions, counts, status, and safe operational
metadata only. Consumers retrieve content through an authenticated,
purpose-limited service query port after policy and consent evaluation.

Bad:

```json
{"query": "Research LangGraph"}
```

Good:

```json
{"request_id": "01975c2f-4aef-7cf1-a940-ae54bf596280"}
```

## Command Payload Schemas

### USER_REQUEST_COMMAND

```json
{
  "request_id": "uuid",
  "conversation_id": "uuid",
  "request_content_ref": "orchestration-request:uuid",
  "input_mode": "text",
  "language": "en",
  "attachment_refs": [{"resource_id": "uuid", "media_type": "text/plain"}],
  "requested_capability_refs": ["application.open"]
}
```

The Orchestration Command Intake stores content before outbox publication. The
reference is resolvable only by authorized Planner/Orchestration ports.

### SHOW_NOTIFICATION_COMMAND

```json
{
  "notification_id": "uuid",
  "notification_content_ref": "notification:uuid",
  "priority": "normal",
  "sensitive": false,
  "expires_at": "2026-06-07T06:41:00Z"
}
```

The Notification Service retrieves title, body, and actions from its owned
state. Lock-screen and ambient surfaces use redacted content for sensitive
notifications.

### UPDATE_WALLPAPER_COMMAND

```json
{
  "wallpaper_update_id": "uuid",
  "display_scope": "all",
  "scene_id": "local-scene-id",
  "state": "processing",
  "intensity": 0.6,
  "transition": {"type": "crossfade", "duration_ms": 400},
  "expires_at": "2026-06-07T06:37:00Z"
}
```

`scene_id` references installed local assets. Receivers enforce reduced-motion
and resource settings.

### CREATE_MEMORY_COMMAND

```json
{
  "memory_id": "uuid",
  "consent_id": "uuid",
  "memory_content_ref": "memory-proposal:uuid",
  "source": {"type": "explicit_user_input", "resource_id": "uuid"},
  "retention_policy": {"policy": "until_deleted", "expires_at": null},
  "sensitivity": "internal"
}
```

The Memory Service rejects missing, expired, revoked, out-of-scope, or
purpose-mismatched consent.

### START_RESEARCH_COMMAND

```json
{
  "research_id": "uuid",
  "request_id": "uuid",
  "query_ref": "orchestration-request:uuid",
  "source_scopes": ["knowledge:approved"],
  "network_allowed": false
}
```

The baseline requires `network_allowed=false`. A future network adapter requires
explicit current-request authorization and cannot upload user content.

### OPEN_APPLICATION_COMMAND

```json
{
  "action_id": "uuid",
  "application_id": "approved-app-id",
  "launch_mode": "user_approved",
  "capability_grant_id": "uuid"
}
```

No command line, environment block, unrestricted executable path, or sensitive
path is permitted.

## Event Payload Schemas

### USER_REQUEST_RECEIVED

```json
{
  "request_id": "uuid",
  "conversation_id": "uuid",
  "input_mode": "text",
  "request_content_ref": "orchestration-request:uuid",
  "received_at": "2026-06-07T06:30:00Z"
}
```

### MEMORY_CREATED

```json
{
  "memory_id": "uuid",
  "consent_id": "uuid",
  "memory_type": "preference",
  "source_ref": "request:uuid",
  "revision": 1,
  "sensitivity": "internal",
  "retention_policy": {"policy": "until_deleted", "expires_at": null},
  "created_at": "2026-06-07T06:30:04Z"
}
```

### MEMORY_UPDATED

```json
{
  "memory_id": "uuid",
  "consent_id": "uuid",
  "revision": 2,
  "changed_fields": ["content", "retention_policy.expires_at"],
  "sensitivity": "internal",
  "retention_policy": {
    "policy": "expires",
    "expires_at": "2026-12-07T00:00:00Z"
  },
  "updated_at": "2026-06-07T06:35:00Z"
}
```

### RESEARCH_STARTED

```json
{
  "research_id": "uuid",
  "request_id": "uuid",
  "source_scopes": ["knowledge:approved"],
  "network_allowed": false,
  "started_at": "2026-06-07T06:30:01Z"
}
```

### RESEARCH_COMPLETED

```json
{
  "research_id": "uuid",
  "request_id": "uuid",
  "status": "completed",
  "result_ref": "research-result:uuid",
  "citation_refs": [{"source_id": "uuid", "chunk_id": "uuid"}],
  "source_count": 3,
  "completed_at": "2026-06-07T06:30:03Z"
}
```

`status` is `completed`, `partial`, `failed`, or `cancelled`. Failures contain a
safe error code in metadata, never stack traces or content.

### APPLICATION_OPENED

```json
{
  "action_id": "uuid",
  "application_id": "approved-app-id",
  "process_id": 12345,
  "capability_grant_id": "uuid",
  "result": "success",
  "opened_at": "2026-06-07T06:36:00Z"
}
```

`result` is `success`, `already_running`, or `failed`.

## Auxiliary Event

`WAKE_WORD_DETECTED` remains an ephemeral NATS Core fact:

```json
{
  "session_id": "uuid",
  "wake_word_id": "jarvis",
  "confidence": 0.94,
  "device_id": "sha256:opaque-device-reference",
  "detected_at": "2026-06-07T06:30:00Z"
}
```

No audio or raw device label is included.

## NATS Governance

| Stream | Content | Retention |
|---|---|---|
| `JARVIS_COMMANDS_V1` | Durable reference-only commands | Work-queue retention |
| `JARVIS_EVENTS_V1` | Durable reference-only domain events | Limits retention, 30-day default |
| `JARVIS_AUDIT_SIGNALS_V1` | Reference-only audit delivery signals | Limits retention, 7-day buffer |
| NATS Core | Ephemeral progress/UI state | No persistence |

- Maximum serialized message size: 256 KiB.
- Commands have one named durable consumer; events may have multiple named
  durable consumers.
- Delivery is at least once; consumers are idempotent and acknowledge only after
  durable state commits.
- Retry uses bounded exponential backoff with jitter and defaults to five
  delivery attempts.
- Exhausted messages produce a metadata-only record on
  `jarvis.dlq.<domain>.v1`.
- The owning service owns dead-letter triage. Security and Audit receive
  metadata-only signals.
- Replay requires local authorization, reason, correlation ID, and audit record.
- Least-privilege NATS accounts restrict publish and subscribe subjects.
- Stream retention is not authoritative business or audit storage.

## Compatibility and Lifecycle

- Ordering is guaranteed only for a documented aggregate stream.
- Breaking removal, rename, semantic change, or type narrowing requires a new
  subject major version.
- New lifecycle events for request completion/failure/cancellation, memory
  deletion, consent grant/revocation, knowledge indexing/deletion, policy
  decisions, agent task outcomes, notification display/acknowledgement, and
  wallpaper completion MUST be registered before producers ship.

## Consumer Checklist

- Validate envelope and payload.
- Confirm the component owns the command or is registered for the event.
- Enforce classification, capability, consent, and purpose.
- Resolve content references through authorized ports only.
- Deduplicate by command/event ID and idempotency key.
- Commit durable state before acknowledgement.
- Apply bounded retry and metadata-only dead-letter handling.
- Propagate correlation and causation IDs.


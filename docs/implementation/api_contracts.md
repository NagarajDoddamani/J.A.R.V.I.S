# API Contracts

**API version:** v1.2  
**Base URL:** `http://127.0.0.1:<configured-port>/v1`  
**Encoding:** JSON unless a documented streaming/media endpoint applies

## API Principles

- Bind to loopback by default.
- Authenticate the installed Tauri client with an OS-protected per-install credential.
- Use OpenAPI 3.1 as the generated HTTP contract.
- Validate requests and responses.
- Use UUID request IDs and propagate `X-Correlation-ID`.
- Mutations accept `Idempotency-Key`.
- Pagination uses opaque cursors.
- Timestamps use RFC 3339 UTC.
- Sensitive fields are omitted by default and never placed in URLs.
- Mutations enter the owning application through command intake and NATS; the
  Gateway never directly invokes agents.

## Common Error

```json
{
  "error": {
    "code": "MEMORY_NOT_FOUND",
    "message": "The requested memory was not found.",
    "correlation_id": "uuid",
    "details": {},
    "retryable": false
  }
}
```

Status policy: `400` invalid input, `401` unauthenticated, `403` denied, `404` absent, `409` conflict/idempotency mismatch, `422` semantic validation, `429` rate limited, `503` unavailable.

## Public Gateway Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Shallow process liveness |
| `GET` | `/ready` | Required dependency readiness |
| `GET` | `/system/status` | Redacted local service/model/storage state |
| `POST` | `/requests` | Submit a user request |
| `GET` | `/requests/{request_id}` | Inspect request, plan, tasks, and result |
| `POST` | `/requests/{request_id}/cancel` | Cancel queued/running work |
| `GET` | `/requests/{request_id}/events` | SSE state/progress stream |
| `POST` | `/approvals/{approval_id}` | Approve or deny a pending capability |
| `GET/POST` | `/memories` | Search/list or explicitly create memory |
| `GET/PATCH/DELETE` | `/memories/{memory_id}` | Inspect, update, or delete memory |
| `POST` | `/memories/export` | Create local export job |
| `POST` | `/consents` | Record explicit scoped memory consent |
| `GET` | `/consents/{consent_id}` | Inspect consent metadata |
| `POST` | `/consents/{consent_id}/revoke` | Revoke consent and initiate covered purge |
| `GET` | `/deletion-jobs/{job_id}` | Inspect purge state and backup-expiry status |
| `GET/POST` | `/knowledge-sources` | List or register approved local source |
| `GET/DELETE` | `/knowledge-sources/{source_id}` | Inspect or remove source and index |
| `POST` | `/knowledge-sources/{source_id}/reindex` | Rebuild source index |
| `GET` | `/notifications` | List notification state |
| `POST` | `/notifications/{id}/acknowledge` | Mark seen |
| `POST` | `/notifications/{id}/dismiss` | Dismiss |
| `POST` | `/notifications/{id}/actions/{action_id}` | Invoke validated action |
| `GET` | `/audit` | Query redacted local audit records |
| `GET/PATCH` | `/settings` | Read or update validated user settings |

## Core Schemas

### Submit Request

```json
{
  "conversation_id": "uuid-or-null",
  "input": {"mode": "text", "content": "Summarize my selected local notes"},
  "attachments": [{"resource_id": "uuid", "media_type": "text/plain"}],
  "preferences": {"response_mode": "text", "language": "en"}
}
```

Response `202 Accepted`:

```json
{
  "request_id": "uuid",
  "conversation_id": "uuid",
  "status": "received",
  "events_url": "/v1/requests/uuid/events",
  "created_at": "2026-06-07T06:30:00Z"
}
```

Request status is `received|planning|awaiting_approval|running|completed|failed|cancelled`.

The Gateway passes the request to the Orchestration Command Intake port. In one
local transaction, Orchestration stores sensitive content in
`orchestration.request_content` and writes a reference-only
`USER_REQUEST_COMMAND` to its outbox. Neither the command nor resulting durable
events contain the request text.

### Approval Decision

```json
{
  "decision": "approve_once",
  "constraints": {"expires_at": "2026-06-07T06:35:00Z"}
}
```

`decision` is `approve_once|deny`. Persistent grants require a separate settings workflow and stronger confirmation.

### Create Memory

```json
{
  "consent_id": "uuid",
  "content": "I prefer concise spoken responses.",
  "memory_type": "preference",
  "sensitivity": "internal",
  "retention": {"policy": "until_deleted", "expires_at": null},
  "provenance": {"source_type": "explicit_user_input", "source_id": "uuid"}
}
```

The Memory Service validates that consent is active and matches purpose, scope,
source, sensitivity, and retention before accepting the command. Response
`201 Created` contains ID, consent ID, revision, metadata, and timestamps.
Search parameters include `query`, `type`, `sensitivity`, `created_after`,
`limit`, and `cursor`.

### Consent Record

```json
{
  "purpose": "remember_explicit_preference",
  "scope": {
    "memory_types": ["preference"],
    "source_types": ["explicit_user_input"]
  },
  "retention_policy": {"policy": "until_deleted", "expires_at": null},
  "decision": "approve"
}
```

Response `201 Created` contains `consent_id`, status, policy version,
`granted_at`, and optional expiry. Denial does not create active consent.

Revocation response `202 Accepted`:

```json
{
  "consent_id": "uuid",
  "status": "revoked",
  "deletion_job_id": "uuid",
  "revoked_at": "2026-06-07T06:40:00Z"
}
```

Revocation blocks retrieval immediately and purges memories covered only by
that consent.

### Delete Memory

`DELETE /memories/{memory_id}` returns `202 Accepted`:

```json
{
  "memory_id": "uuid",
  "deletion_job_id": "uuid",
  "status": "purge_pending",
  "backup_expiry_at": "2026-09-07T00:00:00Z"
}
```

Deletion jobs report relational, vector, cache, artifact, audit, and
backup-retention stages without exposing deleted content.

### Knowledge Source

```json
{
  "kind": "directory",
  "local_path_token": "opaque-approved-path-token",
  "include_patterns": ["**/*.md", "**/*.pdf"],
  "exclude_patterns": ["**/.git/**"],
  "retention": "reference_source"
}
```

Raw local paths are accepted only by the trusted Tauri boundary and exchanged for scoped tokens before normal API use.

### Settings Patch

```json
{
  "voice": {"wake_word_enabled": true, "retain_audio": false},
  "privacy": {"history_retention_days": 30},
  "ui": {"reduced_motion": false}
}
```

Settings are schema-versioned. Unknown fields fail validation.

## Internal APIs and Service Boundaries

NATS is required for cross-boundary mutation commands and domain events.
Synchronous internal HTTP is allowed only for bounded, side-effect-free queries
or health and requires service authentication. Durable messages contain
references and metadata, never prompts, research queries, documents, memory
text, or raw media.

| Owner | Commands/operations | Must not expose |
|---|---|---|
| Orchestration/Core | create/cancel request, plan/task state, approvals | Direct DB/model/tool access to UI |
| Memory Service | memory lifecycle and retrieval | Raw tables, unrestricted embeddings |
| Knowledge Service | source lifecycle, search, provenance | Arbitrary filesystem access |
| Notification Service | notification lifecycle | OS notification APIs directly to agents |
| Settings Service | settings, feature flags, runtime configuration, preferences | Secrets or policy-floor bypass |
| Audit Service | security, consent, action, policy, and administrative audit | Raw prompts/content or general agent reads |
| Policy capability | evaluate capability request | Mutable policy bypass |
| Model adapter | generate/embed/vision inference, including `nomic-embed-text` | Ollama administration to agents |
| Automation adapter | allowlisted local actions | Generic shell execution |

## Internal Command Pattern

```json
{
  "command_id": "uuid",
  "command_type": "CREATE_MEMORY_COMMAND",
  "command_version": 1,
  "issued_at": "2026-06-07T06:30:00Z",
  "expires_at": "2026-06-07T06:31:00Z",
  "correlation_id": "uuid",
  "actor": {"type": "agent", "id": "memory-agent"},
  "capability_grant_id": "uuid",
  "idempotency_key": "opaque-key",
  "payload": {
    "memory_id": "uuid",
    "consent_id": "uuid",
    "memory_content_ref": "memory-proposal:uuid"
  }
}
```

Commands require identity, expiry, capability grant where applicable, idempotency, and a typed result event.

The authoritative command ownership table and payload schemas are defined in
`event_contracts.md`.

The six commands in the v1.2 core registry are the minimum corrected baseline.
Additional mutations, including request cancellation, consent grant/revocation,
memory deletion, settings updates, knowledge-source changes, and notification
actions, MUST receive a versioned command contract and exactly one owner before
the corresponding endpoint is implemented.

## Streaming

SSE events contain only request-scoped state updates, use monotonically increasing sequence numbers per request, support `Last-Event-ID`, and redact sensitive data. Reconnect obtains durable current state before transient progress resumes.

## Contract Governance

- Generated clients derive from OpenAPI/JSON Schema; hand-written duplicate DTOs are prohibited.
- Provider and consumer contract tests run in CI.
- Additive optional fields are backward compatible.
- Removing/renaming fields, changing meaning, or tightening accepted values requires `/v2` or an agreed deprecation cycle.
- Deprecated fields remain for at least one supported release and produce local diagnostics.

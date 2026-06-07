# Phase 02: Core Services

## Objective

Implement the stable service boundaries and contracts required by orchestration and user experiences.

## Entry Criteria

- Phase 01 exit criteria approved.
- API, event, and database contracts reviewed.
- Service ownership and schema boundaries assigned.

## Deliverables

### API Gateway

- Versioned `/v1` API, local-client authentication, request validation, correlation IDs, and rate limiting.
- Request submission, state query, cancellation, health, readiness, and event streaming.
- Uniform errors and OpenAPI generation.

### Memory Service

- Explicit memory create, retrieve, search, update, archive, and delete workflows.
- Sensitivity classification, consent, provenance, retention, and deletion propagation.
- PostgreSQL source of truth with Qdrant-derived embeddings and transactional outbox.

### Knowledge Service

- User-approved local document ingestion.
- Parsing, chunking, fingerprinting, provenance, indexing, re-indexing, and deletion.
- Protection against embedded prompt injection and unsupported file types.

### Notification Service

- Create, prioritize, deliver, acknowledge, dismiss, expire, and action notifications.
- Core NATS delivery with reconnect recovery from durable state.

### Settings Service

- Own user settings, feature flags, runtime configuration, and personal
  preferences in the `settings` PostgreSQL schema.
- Publish factual settings events without secrets.
- Store only OS credential-manager references for secret-backed settings.

### Audit Service

- Own security, consent, system-action, policy-decision, and administrative
  records in the append-only `audit` schema.
- Enforce content minimization, hash chaining, local access control, and
  retention policy.

## Work Breakdown

| ID | Task | Verification |
|---|---|---|
| SVC-001 | API request lifecycle | Contract tests for submit, inspect, cancel, and errors |
| SVC-002 | Local authentication and policy middleware | Unauthorized and replay cases denied |
| SVC-003 | Memory lifecycle | CRUD, retention, provenance, and delete propagation tests |
| SVC-004 | Semantic retrieval | Deterministic evaluation fixture meets relevance baseline |
| SVC-005 | Knowledge ingestion | Duplicate, malformed, oversized, and delete cases pass |
| SVC-006 | Notification lifecycle | Ordering, expiry, reconnect, and action tests pass |
| SVC-007 | Outbox/inbox reliability | Crash recovery and duplicate delivery tests pass |
| SVC-008 | Service observability | One request trace links API, events, storage, and result |
| SVC-009 | Settings ownership | Schema, API, event, validation, and secret-reference tests pass |
| SVC-010 | Audit ownership | Hash-chain, access, retention, minimization, and fail-closed tests pass |

## Service Constraints

- Services do not read or mutate another service's tables.
- Embeddings are derived data and can be rebuilt.
- Raw file content remains at its approved local source unless copy retention is explicitly enabled.
- Every mutation supports an idempotency key.
- Delete operations are asynchronous only when the API returns a deletion job that can be inspected.

## Exit Criteria

- Public and internal APIs conform to checked schemas.
- Memory and document deletion are verified across relational, vector, cache, event, and backup-retention layers.
- Core services recover from restart without losing acknowledged durable work.
- API and persistence authorization tests pass.
- Offline integration tests pass.
- Service runbooks and ownership are documented.

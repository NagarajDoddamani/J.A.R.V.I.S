# Phase 01: Foundation

## Objective

Create a reproducible monorepo and secure local runtime on which all later phases can depend.

## Entry Criteria

- JDOS v1.0 approved.
- Supported operating systems: Windows 11 (Primary), Ubuntu 24.04 (Secondary).
- Architecture baseline accepted through ADR-0001.

## Deliverables

### Monorepo

- Python 3.12 backend workspace with `uv` for dependency management.
- Node.js 22 LTS, React, TypeScript, and Tailwind frontend workspace with `pnpm` workspaces.
- Shared schema generation package and repository tooling.
- Consistent format, lint, type, test, security, and license commands.
- Environment configuration with validated settings and safe defaults.

### Docker and Local Infrastructure

- Version-pinned Compose services:
  - PostgreSQL 16
  - Redis 7
  - Qdrant (latest stable)
  - NATS with JetStream (latest stable)
  - Ollama (latest stable)
- Loopback/private-network bindings and non-default development credentials.
- Health checks, named volumes, resource limits, and startup ordering.
- One-command start, stop, status, reset, backup, and restore workflows.
- No automatic model download or external network dependency during normal startup.

### Platform Foundations

- Correlation ID and structured logging libraries.
- Health/readiness endpoint conventions.
- Event envelope package and schema validation.
- Separate command and event envelopes, registries, and ownership validation.
- Migration framework and empty service-owned schemas.
- Secret loading through environment in development and OS credential manager abstraction for production.
- CI baseline and architecture fitness tests.

## Work Breakdown

| ID | Task | Verification |
|---|---|---|
| FND-001 | Initialize repository toolchains and lockfiles | Clean checkout installs from documented prerequisites |
| FND-002 | Define local configuration schema | Invalid/missing values fail with actionable errors |
| FND-003 | Add Compose stack | Every dependency reports healthy |
| FND-004 | Configure NATS accounts, subjects, JetStream | Publish/consume and durable replay tests pass |
| FND-005 | Configure database roles and migrations | Least-privilege role tests and migration round trip pass |
| FND-006 | Configure Qdrant and Redis policies | Connectivity, namespacing, TTL, and auth tests pass |
| FND-007 | Configure Ollama adapter boundary | Health and model-unavailable behavior pass offline |
| FND-008 | Add CI and local quality commands | Same commands pass locally and in CI |
| FND-009 | Add backup/restore proof | Restore into clean volumes and validate checksums |
| FND-010 | Produce SBOM and dependency policy | Baseline artifacts generated without upload |
| FND-011 | Verify approved Ollama models | Manifest, digest, offline inference, and startup checks pass |
| FND-012 | Validate sensitive payload policy | Durable message fixtures reject prompts, queries, memory text, documents, and raw media |

## Required Tests

- Compose smoke and dependency health tests.
- Outbound-network-blocked startup test.
- Event delivery, duplicate handling, and dead-letter test.
- Single command-owner and multi-subscriber event tests.
- NATS stream retention, 256 KiB message limit, five-attempt retry, subject
  permissions, metadata-only dead-letter, and authorized replay tests.
- Migration upgrade and clean-database bootstrap test.
- Backup/restore data integrity test.
- Secret and sensitive logging tests.
- Backup exclusion tests for keys, tokens, credentials, `.env`, OS secrets,
  Redis, caches, and temporary media.

## Model Verification Checklist

The following models are locked and MUST be verified:

- Qwen 3 8B.
- Qwen Coder.
- Qwen2.5-VL.
- `nomic-embed-text`.

For each model:

- Verify installation through the approved Ollama model manifest.
- Record model name, version/tag, immutable digest/checksum, source, and license
  metadata.
- Start with outbound network blocked and verify local discovery.
- Run a deterministic smoke inference appropriate to the model type.
- Restart Ollama and verify startup discovery without download.
- Verify missing/corrupt model behavior fails locally with an actionable error
  and never invokes a cloud fallback.

Model artifacts MUST NOT download automatically during normal startup.

## NATS Governance Verification

Phase 01 configures:

- `JARVIS_COMMANDS_V1` with work-queue retention.
- `JARVIS_EVENTS_V1` with limits retention and a 30-day default.
- `JARVIS_AUDIT_SIGNALS_V1` with limits retention and a 7-day buffer.
- NATS Core for non-persistent progress and UI state.
- Least-privilege publish/subscribe subject permissions.
- A 256 KiB serialized-message limit.
- Explicit acknowledgement, bounded exponential backoff, five delivery
  attempts, and metadata-only dead-letter subjects.
- Replay authorization, reason, correlation ID, and Audit Service recording.

## Exit Criteria

- A new developer can start the stack from a clean checkout using documented commands.
- All services are version pinned, healthy, and inaccessible from non-local interfaces by default.
- CI enforces formatting, linting, strict typing, tests, secret scanning, and contract validation.
- NATS event envelope and subject conventions are implemented and tested.
- Command ownership and event producer/consumer registries are implemented and
  contract tested.
- All four approved Ollama models pass checksum, startup, smoke, and offline
  availability verification.
- Durable NATS payload scanning proves that prohibited sensitive content is
  rejected.
- Database migration, backup, and restore procedures are proven.
- No critical/high security findings remain.

## Explicitly Deferred

Business endpoints, memory behavior, agent prompts, voice capture, and product UI beyond a minimal health surface.

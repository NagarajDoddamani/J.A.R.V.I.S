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

The runtime configuration is implemented in
`backend/core/nats_governance.py` (declarative) and `backend/core/nats.py`
(manager). Bootstrap is idempotent and runs from the FastAPI lifespan
when `NATS_AUTO_BOOTSTRAP=true`. See
`docs/implementation/nats_governance.md` for the operator-facing
companion.

## CI/CD and Local Quality Commands

Phase 01 ships a foundation CI workflow at
`.github/workflows/ci.yml` with two jobs:

* **foundation** — installs Python 3.12 via `astral-sh/setup-uv`,
  runs `uv sync`, `uv run ruff check .`, `uv run mypy --strict .`,
  and `uv run pytest ../tests -q --cov --cov-fail-under=70`,
  plus a `gitleaks` secret scan.
* **docker-smoke** — brings up the Compose stack, waits for the
  healthchecks, runs `uv run python -m tools.sbom.generate --out-dir
  build/sbom` to produce the SBOM, and tears down.

`backend/pyproject.toml` is the single source of truth for Ruff
select rules (`E,F,I,B,S,C4,UP,RUF,SIM,T20,RET`), Mypy strict,
pytest, and the `--cov-fail-under=70` gate.

`.github/dependabot.yml` keeps `pip`, `shared`, GitHub Actions, and
Docker images current on a weekly cadence.

`.gitleaks.toml` blocks JARVIS-internal credential patterns and
common AI-provider key patterns; the `allowlist` covers
`.env.example`, docs, and test fixtures.

`tests/test_architecture_fitness.py` is a non-bypassable
architecture-fitness test. It enforces:

* domain purity (no business logic in `shared/` or repo root),
* the 256 KiB payload-boundary consistency between
  `NATS_MAX_PAYLOAD_BYTES` and the gateway middleware,
* the sensitive-key surface overlap between NATS governance and
  the payload policy,
* NATS stream invariants (work-queue `JARVIS_COMMANDS_V1`,
  `max_ack_pending` defaults),
* model manifest coverage for the four locked Ollama models,
* a plaintext-secret regex sweep across tracked files,
* FND-001 lockfile policy, FND-003 Compose hardening,
  FND-006 Redis/Qdrant governance, and FND-007 Ollama
  adapter boundary.

## Lockfiles and Reproducible Installs (FND-001)

* `backend/uv.lock` and `pnpm-lock.yaml` are gitignored and
  regenerated on demand.
* The verifier at `tools/lockfile/verify.py` runs
  `uv lock --check` and `pnpm install --frozen-lockfile`; it
  fails the session when either lockfile is missing or stale.
* The CI workflow and the bootstrap scripts call the verifier
  before lint and tests. See
  `docs/implementation/lockfile_policy.md`.

## Compose Hardening (FND-003)

* Loopback bindings only.
* `depends_on.condition: service_healthy` on every
  application service.
* Resource limits and `stop_grace_period` on every service.
* Restart policies: `unless-stopped` for stateful services.
* `app` profile on the `backend` service so the foundation
  stack can come up without launching the application.
* See `docs/implementation/compose_operations.md` for the
  service topology, the resource matrix, the graceful
  shutdown policy, and the failure-mode matrix.

## Redis and Qdrant Governance (FND-006)

* Redis namespace `jarvis:` with a per-service prefix registry
  (`backend/core/redis_governance.py`).
* Key-class TTL policy: session=1h, rate-limit=1m, lock=30s,
  ephemeral=5m, durable=24h.
* Cache eviction policy `allkeys-lru` (Compose parity enforced
  by the architecture fitness test).
* Max single-key size 8 KiB; larger payloads go to PostgreSQL
  bytea, Qdrant payload, or the filesystem.
* Qdrant collection registry with the locked 768-d cosine
  configuration, retention, and rebuild policy
  (`backend/core/qdrant_governance.py`).
* See `docs/implementation/redis_governance.md` and
  `docs/implementation/qdrant_governance.md`.

## Ollama Adapter Boundary (FND-007)

* `backend/core/ollama.py` is the *only* module in the backend
  that imports `httpx` (architecture fitness enforces this).
* The adapter implements `ModelPort`, `EmbeddingPort`,
  `GenerationPort`, and `VisionPort`.
* Loopback URL guard, manifest reconciliation, bounded retry,
  per-request timeout, and typed errors.
* See `docs/implementation/ollama_adapter.md`.

## Backup / Restore

Phase 01 ships an encrypted backup proof at
`tools/backup/` with three modules:

* `crypto.py` — AES-256-GCM with PBKDF2-HMAC-SHA256 (600 000
  iterations). The header (`HEADER_MAGIC = b"JARVISBAK\x00"`,
  version, KDF iterations, salt, nonce) is bound to the
  ciphertext via AES-GCM's AAD.
* `manifest.py` — `ArtifactEntry`, `BackupManifest`, and
  `EXCLUDED_SOURCES` covering `.env`, secrets, redis, tmp,
  cache, `.aws`, and `.ssh`.
* `backup.py` / `restore.py` — the operator entry points.
  `backup.py` runs `pg_dump`, snapshots the Qdrant storage,
  bundles user settings, encrypts the resulting tar, and
  writes a manifest + ciphertext. `restore.py` decrypts, SHA-256
  verifies each entry, guards against path traversal, and
  re-applies the excluded-source rule.

The recovery passphrase is held by the user
(`JARVIS_BACKUP_PASSPHRASE`); losing it is unrecoverable by
design. See `tools/backup/RESTORE.md` for the operator drill.

## SBOM and Security Policy

Phase 01 ships an SBOM generator at `tools/sbom/generate.py`. It
emits:

* `build/sbom/jarvis-sbom.cdx.json` — CycloneDX 1.5 JSON SBOM.
* `build/sbom/jarvis-inventory.json` — flat dependency inventory.
* `build/sbom/jarvis-licenses.json` — per-license report.

The generator uses `importlib.metadata` and has no third-party
runtime dependency beyond the standard library.

`SECURITY.md` captures the supported-version policy, reporting
procedure, trust boundaries, threat catalog, secret-management
rules, and CI fitness gates.

## Service-Owned Database Schemas

Phase 01 establishes the durable persistence layer. The initial Alembic
migration (`backend/migrations/versions/743a95f81f31_initial_foundation_setup.py`)
creates:

- The `platform` schema (extensions, `uuidv7()` generator, Alembic
  version table).
- Six service-owned schemas: `orchestration`, `memory`, `knowledge`,
  `notification`, `settings`, `audit`.
- An outbox and inbox table inside every service schema.
- The first foundation entities: `memory.memories`,
  `memory.consent_records`, `audit.audit_entries`,
  `audit.audit_chain_heads`, `settings.user_settings`.

Per the JDOS v1.2 architecture corrections, the foundation layer ships
with UUIDv7 primary keys, `timestamptz` columns, optimistic-locking
support, soft-delete support, and least-privilege role grants. See
`docs/implementation/database_schema_foundation.md` for details.

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

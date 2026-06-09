# Development Status

**JDOS version:** 1.2  
**Last updated:** 2026-06-09  
**Updated by:** AI Agent  
**Repository state:** SVC-001 complete. SVC-002 fully complete (A–G).
SVC-003 fully complete (A–G). SVC-004 fully complete (A–G). 2563
total tests pass (45 architecture + 728 memory + 501 settings + 229
audit + 263 foundation + 797 knowledge).
Phase 01 exit gate remains open.

## Current Phase

**Phase 02: Core Services — Step completed: SVC-004-G Knowledge
Integration & Service Closure**

Knowledge Service fully complete across all seven layers (A–G).
116 new tests (84 integration + 32 service closure) verify source
lifecycle, document lifecycle, chunk lifecycle, ingestion lifecycle,
reindex flow, repository roundtrip (DTO→ORM→DB→DTO→Domain for all
5 entities), event flow (all 10 domain events through outbox with
FIFO ordering), REST contract (all 11 routes, status codes, error
bodies, DTO shapes), cross-entity integrity (source→document→chunk
cascade, inactive source blocking, deleted entity protection), and
outbox ordering (FIFO append, partial mark, pending isolation).
Service closure audits: domain enum completeness, architecture
import barriers, layer isolation, provider/route/event/repo/mapper/DTO
inventory, security compliance (classification, empty name/title,
invalid transitions, deleted entity protection), and coverage metrics.
Full suite: 2563 passed, 1 skipped, 52 warnings.
Complete. KNOWLEDGE_SERVICE_COMPLETE.

The Audit Service (SVC-001) has been fully implemented across all six
hexagonal architecture layers:

- **SVC-001-A Domain** (63 tests): `AuditEntry` aggregate, value objects,
  `AuditEntryRecorded` event, `AuditEntryFactory`, 13 domain rules, hash-chain
  computation, `AuditEntryState` lifecycle.
- **SVC-001-B Ports** (30 tests): 5 `typing.Protocol` interfaces for
  repositories, outbox, clock, and ID generation.
- **SVC-001-C Persistence Contracts** (49 tests): Storage DTOs, mapper
  protocols, schema contracts (column/table contracts for 3 tables).
- **SVC-001-D Use Cases** (23 tests): 5 use cases (Record, GetEntry,
  GetChain, GetByCorrelation, GetChainHead) with request/response DTOs.
- **SVC-001-E Adapters** (26 tests): SQLAlchemy ORM models, mapper impls,
  repository impls, `SystemClockAdapter`, `UuidV7GeneratorAdapter`.
  Tests use SQLite in-memory with schema stripped for compatibility.
- **SVC-001-F Service Bootstrap**: FastAPI routes (`POST/GET /audit/entries`,
  `GET /audit/chains/{name}`, `GET /audit/chains/{name}/head`), DI wiring via
  FastAPI `Depends()` in `backend/audit/bootstrap.py`, NATS outbox publisher
  background task in `backend/audit/nats.py`, SQLAlchemy engine/session in
  `backend/core/database.py` (lazy initialization).
- **SVC-001-G Integration & API Contracts** (38 tests): Full-stack round-trips
  (use case→repository→SQLite), outbox persistence (append/fetch/mark FIFO),
  rollback on domain violations, NATS outbox publisher (mock JetStream),
  API contract tests for all 5 routes (201/404/422 status codes, error shapes,
  pagination, correlation filtering, chain head tracking).

## Completed Tasks

- Established repository and documentation structure.
- Defined product vision, scope, outcomes, release criteria, and risks.
- Defined system, data, event, security, privacy, and agent architecture.
- Defined six gated development phases and development workflow.
- Defined API, event, database, coding, testing, logging, and security
  standards.
- Created master context and reusable Codex, Claude Code, and Gemini CLI
  prompts.
- Established ADR process and initial architecture baseline.
- Created ownership boundaries for future repository areas.
- Applied all ten JDOS v1.2 architecture audit corrections.
- Separated command and event architecture and corrected Gateway-to-NATS
  flow.
- Finalized `nomic-embed-text`, memory consent, sensitive payload,
  backup, Settings, Audit, model verification, and NATS governance
  architecture.
- Accepted ADR-0001 with platform (Windows/Ubuntu), toolchain (uv/pnpm),
  and infrastructure (Docker Compose) decisions.
- **FND-001 — Toolchain completion.** `uv.lock` and `pnpm-lock.yaml`
  are produced and verified on demand by
  `tools/lockfile/verify.py`, called from the CI workflow and the
  bootstrap scripts. Lockfiles are gitignored and regenerated
  per-machine. `frontend/package.json` is the pnpm workspace root.
  See `docs/implementation/lockfile_policy.md`.
- **FND-002 — Local configuration schema.** Env-validated with
  `extra="forbid"`; `Settings` derives the PostgreSQL DSN.
- **FND-003 — Compose hardening.** Every service binds to
  loopback, declares `restart: unless-stopped`, has a healthcheck,
  resource limits, and `stop_grace_period`. `backend` uses
  `depends_on.condition: service_healthy`. The Compose file is
  version-named (`name: jarvis-foundation`) and the network is
  named (`jarvis-network`) with masquerading disabled. See
  `docs/implementation/compose_operations.md` and
  `tests/test_compose_hardening.py`.
- **FND-004 — NATS Governance (Correction 10).** Three durable
  streams (`JARVIS_COMMANDS_V1`, `JARVIS_EVENTS_V1`,
  `JARVIS_AUDIT_SIGNALS_V1`) are bootstrapped from
  `backend/core/nats_governance.py` and `backend/core/nats.py`.
  256 KiB payload boundary, retry budget, dead-letter routing,
  envelope validation enforced at the producer boundary.
- **FND-005 — Service-Owned Schemas (Corrections 7 & 8).** Alembic
  migration creates `platform` schema (uuidv7 generator), six
  service-owned schemas, per-service outbox/inbox tables, and
  the first foundation entities. Least-privilege role
  scaffolding in place.
- **FND-006 — Redis and Qdrant governance.**
  `backend/core/redis_governance.py` defines the namespace
  (`jarvis:`), the per-service prefix registry, the key-class
  TTL policy (session/rate-limit/lock/ephemeral/durable), the
  eviction policy (`allkeys-lru`), and the 8 KiB max key size.
  `backend/core/qdrant_governance.py` defines the collection
  registry, the locked 768-d cosine configuration, and the
  retention/rebuild policy. Compose parity is enforced by the
  architecture fitness test. See
  `docs/implementation/redis_governance.md` and
  `docs/implementation/qdrant_governance.md`.
- **FND-007 — Ollama adapter boundary.** `backend/core/ollama.py`
  is the only place in the backend that may import `httpx`
  (architecture fitness enforces this). The adapter implements
  `ModelPort`, `EmbeddingPort`, `GenerationPort`, and
  `VisionPort`. It enforces a loopback URL guard, manifest
  reconciliation, bounded retry (3 attempts, capped at 8 s),
  per-request timeout, and typed errors. See
  `docs/implementation/ollama_adapter.md`.
- **FND-008 — CI/CD and local quality commands.**
  `.github/workflows/ci.yml` runs the foundation job (Ruff, Mypy
  strict, Pytest with coverage, gitleaks) and a docker-smoke
  job. `backend/pyproject.toml` is configured for strict static
  checks and `--cov-fail-under=70`. `.gitleaks.toml` blocks any
  JARVIS-internal credential pattern and common AI-key
  patterns; `.github/dependabot.yml` keeps pip, shared,
  actions, and Docker up to date weekly.
- **FND-009 — Backup / restore proof.** `tools/backup/crypto.py`
  provides AES-256-GCM with PBKDF2-HMAC-SHA256 (600 000
  iterations) and a magic-prefixed header. `manifest.py`
  enumerates `EXCLUDED_SOURCES`. `backup.py` runs `pg_dump`,
  snapshots Qdrant, encrypts the tar, and writes the manifest.
  `restore.py` decrypts, SHA-256 verifies, and guards against
  path traversal. Recovery passphrase is user-held.
- **FND-010 — SBOM, dependency inventory, security policy.**
  `tools/sbom/generate.py` emits CycloneDX 1.5 JSON SBOM plus
  a flat inventory and a per-license report. `SECURITY.md`
  captures the supported-version policy, threat catalog,
  secret-management rules, audit chain, and CI fitness gates.
- **FND-011 — Approved Ollama model verification.**
  `tools/model_verification/manifest.py` declares the four
  locked models with expected digests, smoke prompts, and an
  alias map. `verify_models.py` reconciles the manifest,
  performs digest checks, smoke inference, missing/unsupported
  detection, and writes a JSON report.
  `JARVIS_VERIFY_OFFLINE=1` enables offline-only verification.
- **FND-012 — Sensitive payload policy.** `PayloadPolicyError`
  carries a stable code and dotted path. FastAPI middleware
  (`backend/core/middleware/__init__.py`) is registered in
  `backend/main.py`. Tests cover the five proof points
  (prompt, raw memory, document, embedding, secret) over HTTP
  and over `nats_manager.publish()`, plus cycle-safe
  traversal, the 256 KiB oversize case, and exempt paths.
- **SVC-002-F Settings Bootstrap** — FastAPI routes (5 endpoints:
  `GET /settings`, `GET /settings/{key}`, `PATCH /settings/{key}`,
  `PATCH /settings`, `POST /settings/reset`), DI wiring with
  `DEFAULT_REGISTRY` (20 setting definitions across 6 categories),
  NATS outbox publisher (`publish_settings_outbox_events` with poll–
  publish–mark loop, `max_iterations`, graceful cancellation). Clock
  and ID generator adapters created. Tests: 76 new (bootstrap + API +
  NATS). 937 total tests pass.
- **SVC-002-G Settings Integration & Final Verification** — End-to-end
  lifecycle verification (create→patch→query→reset→publish→mark),
  repository roundtrip (Domain→DTO→ORM→DB→ORM→DTO→Domain) with no data
  loss, event flow validation (SettingUpdated/SettingsReset through
  outbox→NATS payload→published marker, FIFO preservation), REST
  contract verification (all 5 routes, status codes, DTO shapes,
  validation errors, cross-profile isolation), architecture compliance
  (layer isolation, import barriers), and registry audit (20 keys,
  6 categories, type/bounds/allowed-values consistency). Tests: 101 new
  (integration + service closure). 1038 total tests pass. Completion
  report: `docs/status/settings_service_completion_report.md`.
- **SVC-003-A Memory Domain** — Memory Service domain layer completed.
  Value objects: `MemoryId`, `ConsentId`, `RevisionNumber`,
  `MemoryContent`, `Provenance`, `RetentionPolicy`. Enums: `MemoryCategory`
  (6: GENERAL, CONVERSATION, DOCUMENT, INSIGHT, PREFERENCE, EPHEMERAL),
  `MemoryState` (3: CREATED, UPDATED, DELETED), `ConsentStatus` (4:
  PROPOSED, ACTIVE, REVOKED, PURGED), `MemorySource` (5: USER_INPUT,
  CONVERSATION, INFERENCE, SYSTEM, EXTERNAL). Entities: `Memory`
  (aggregate root with update/delete commands), `ConsentRecord` (with
  grant/revoke/purge lifecycle). Domain events: `MemoryCreated`,
  `MemoryUpdated`, `MemoryDeleted`, `ConsentGranted`, `ConsentRevoked`.
  13 domain rules: content not empty, max length (10000 chars), no
  secrets (password, token, api_key, private_key), consent must be
  ACTIVE, retention required, revision monotonicity, deleted memory
  blocks updates, revoked consent blocks updates, provenance required,
  source required, classification valid, purged consent dead,
  expiration after grant. `MemoryFactory.create()` with full validation.
  Tests: 258.
- **SVC-003-B Memory Ports** — 5 `typing.Protocol` interfaces:
  `MemoryRepositoryPort`, `ConsentRepositoryPort`, `MemoryOutboxPort`,
  `MemoryClockPort`, `MemoryIdGeneratorPort`. Tests: 67.
- **SVC-003-C Memory Persistence** — `MemoryStorageDTO`,
  `ConsentStorageDTO`, `MemoryOutboxStorageDTO` with `extra=forbid`;
  schema contracts for `MEMORIES_TABLE`, `CONSENTS_TABLE`,
  `MEMORY_OUTBOX_TABLE` covering column names, types, nullability,
  primary keys, and the `memory` schema qualifier. Tests: 96.
- **SVC-003-D Memory Use Cases** — `CreateMemoryUseCase`,
  `UpdateMemoryUseCase`, `DeleteMemoryUseCase`, `GetMemoryUseCase`,
  `ListMemoriesUseCase` with full domain rule enforcement, outbox event
  emission, consent validation, and request/response DTOs. Tests: 58.
- **SVC-003-E Memory Adapters** — Outbound adapters: `SystemClockAdapter`,
  `UuidGeneratorAdapter`, `MemoryMapperImpl`, `ConsentMapperImpl`,
  `MemoryOutboxMapperImpl` (8 event types with JSON payload), SQLAlchemy
  ORM models (`MemoryModel` — 16 columns, `ConsentModel` — 6 columns,
  `MemoryOutboxModel` — 8 columns), `SqlAlchemyMemoryRepository`,
  `SqlAlchemyConsentRepository`, `SqlAlchemyMemoryOutboxAdapter` (upsert
  semantics, FIFO outbox, `find_deleted` via `deleted_at IS NOT NULL`,
  idempotent `mark_published` via `aggregate_id`). Integration tests
  cover full domain→mapper→DTO→ORM→SQLite roundtrips, consent lifecycle,
  outbox FIFO ordering, and partial mark_published. Tests: 78 new
  (32 unit + 46 integration). 1595 total tests pass.
- **SVC-003-F Memory Bootstrap** — `backend/memory/bootstrap.py`: 8
  dependency providers (`CreateMemoryUseCase`, `UpdateMemoryUseCase`,
  `DeleteMemoryUseCase`, `GetMemoryUseCase`, `SearchMemoriesUseCase`,
  `GrantConsentUseCase`, `RevokeConsentUseCase`, `GetConsentUseCase`)
  wired to SQLAlchemy repos, outbox, clock, and ID generator via
  FastAPI `Depends`. `backend/memory/nats.py`: `publish_memory_outbox_events`
  background publisher with FIFO ordering, configurable batch/interval/
  max_iterations, NATS subjects per event type
  (`jarvis.memory.event.<type>.v1`), and envelope with event_id,
  event_type, aggregate_id, occurred_at, and event-specific payloads.
  `backend/api/endpoints/memory.py`: 8 REST routes at `/api/v1/memory/`
  (`POST /memories`, `PATCH /memories/{id}`, `DELETE /memories/{id}`,
  `GET /memories/{id}`, `GET /memories`, `POST /consents`,
  `POST /consents/{id}/revoke`, `GET /consents/{id}`) with error mapping
  (MemoryNotFoundError→404, ConsentNotActiveError→400, MemoryDomainError→422).
  Registered in `backend/api/router.py` and `backend/main.py` lifespan.
  Tests: 84 new (16 bootstrap + 46 API + 22 NATS). 1679 total tests pass.
- **SVC-003-G Memory Integration & Service Closure** — Full lifecycle
  verification (consent: grant→get→revoke→find_active→find_revoked→count;
  memory: create→update→delete→get→search→get_deleted), outbox audit
  (all 8 event types: MemoryCreated, MemoryUpdated, MemoryDeleted,
  MemoryPurgeScheduled, MemoryPurged, MemoryRetentionExpired,
  ConsentGranted, ConsentRevoked — FIFO ordering, mark_published
  isolation), repository roundtrip (Domain→DTO→ORM→DB→ORM→DTO→Domain)
  with no data loss, REST contract verification (all 8 routes at
  `/api/v1/memory/`, 201/200/400/404/422 status codes, DTO shapes,
  error bodies, search filtering by category/state), cross-service
  scenarios (consent active allows memory create, revoked blocks,
  memory created after consent granted). Service closure audits:
  registry audit (8 providers, 8 routes, 3 ORM models, 8 outbox
  events), architecture compliance (layer isolation, no upward
  imports, allowed adapter paths), coverage metrics (641 memory +
  87 new integration/closure), security compliance (no secrets,
  no PII in outbox payloads). Tests: 87 new (55 integration + 32
  service closure). 1766 total tests pass.
- **SVC-004-A Knowledge Domain** — Knowledge Service domain layer.
  4 entities, 4 enums, 8 value objects, 10 domain events, 22 domain
  rules, `KnowledgeFactory` with 5 creation operations. Tests: 206.
  1972 total tests pass.
- **SVC-004-B Knowledge Ports** — Knowledge Service application
  ports. 4 repository ports (`KnowledgeSourceRepositoryPort` —
  save/find_by_id/find_by_status/find_by_type/count,
  `KnowledgeDocumentRepositoryPort` — save/find_by_id/
  find_by_source_id/find_by_checksum/find_deleted/count,
  `KnowledgeChunkRepositoryPort` — save/find_by_id/
  find_by_document_id/find_by_index_range/count,
  `IngestionJobRepositoryPort` — save/find_by_id/
  find_by_source_id/find_by_status/count), 1 outbox port
  (`KnowledgeOutboxPort` — append/fetch_unpublished/mark_published
  with at-least-once delivery semantics), 1 clock port
  (`KnowledgeClockPort` — UTC-aware now()), 1 ID generator port
  (`KnowledgeIdGeneratorPort` — generate_source_id/generate_document_id/
  generate_chunk_id/generate_job_id). All ports use `typing.Protocol`
  for structural subtyping. Tests: 75 contract tests with stub
  implementations covering save/find semantics, null returns, query
  filtering, FIFO ordering, limit enforcement, mark_published
  idempotence, UUID uniqueness, deterministic test stubs, and method
   signature verification. 2047 total tests pass.
- **SVC-004-C Knowledge Persistence Contracts** — 5 storage DTOs
   (frozen dataclasses with flattened primitives), 5 mapper Protocol
   interfaces (domain_to_dto/dto_to_domain), 5 schema contract tuples
   in `knowledge` schema (KNOWLEDGE_SOURCES_TABLE, KNOWLEDGE_DOCUMENTS_TABLE,
   KNOWLEDGE_CHUNKS_TABLE, INGESTION_JOBS_TABLE, KNOWLEDGE_OUTBOX_TABLE).
   142 persistence contract tests covering DTO construction, mapper
   roundtrips, schema consistency, DTO↔schema alignment, schema↔domain
   alignment, and domain↔DTO parity. 2189 total tests pass.
- **SVC-004-D Knowledge Use Cases** — 12 application use cases
   (RegisterSource, DeleteSource, GetSource, ListSources,
   IngestDocument, GetDocument, CreateChunk, GetChunksByDocument,
   StartIngestion, CompleteIngestion, FailIngestion, GetIngestionJob,
    RequestReindex) with 26 request/response DTOs, 7-exception
    UseCaseError hierarchy, and factory/entity orchestration. 75 tests.
    2264 total tests pass.
- **SVC-004-E Knowledge Adapters** — 5 SQLAlchemy ORM models, 5 mapper
   implementations (lossless Domain→DTO↔ORM roundtrip), 4 repository
   implementations (upsert pattern, all query/count methods),
   SqlAlchemyKnowledgeOutboxAdapter (FIFO append/fetch/mark_published),
   SystemClockAdapter (UTC-aware now), UuidGeneratorAdapter (domain ID
   types). 85 tests (35 unit + 50 integration with SQLite in-memory).
   2349 total tests pass.
- **SVC-004-F Knowledge Bootstrap, API, and NATS** — 13 dependency
   providers with FastAPI `Depends`, 11 REST routes at `/api/v1/knowledge`
   (sources CRUD, document ingest/get, chunk create, chunks-by-document,
   ingestion start/complete/fail/get, reindex), NATS outbox publisher
   (`publish_knowledge_outbox_events`) with 10 event types mapped to
   `jarvis.knowledge.event.<type>.v1` subjects, FIFO ordering, envelope
   with event_id/event_type/kind/producer/aggregate_id/occurred_at/payload.
   `backend/main.py` updated with knowledge outbox publisher task.
   `backend/api/router.py` updated with knowledge routes. 98 tests.
   2447 total tests pass.

## Pending Tasks

1. **SVC-001 outbox publisher hardening** — Governance envelope validation
   (use `nats_manager.publish()`), retry budget, DLQ routing,
   graceful NATS disconnect handling, ACK tracking.
2. Run the Phase 01 Compose stack end-to-end and capture
   evidence for the exit gate (NATS replay, in-VM message
   size, model verification live, backup round-trip, payload
   fixture suite, lockfile parity).
3. Production grant pattern for the per-service roles.
4. Pin exact production image versions.
5. **Next step: SVC-005**
   Phase 03 services.

## Known Issues

- SQLite compatibility requires stripping schema from ORM metadata
  in test fixtures (`_table.schema = None`). Production uses
  PostgreSQL with `audit` schema.
- `UuidV7GeneratorAdapter` uses `uuid4()`; production should switch to
  `platform.uuidv7()` for time-ordered UUID column clustering.
- Outbox publisher uses raw `js.publish()` without governance envelope
  validation — should use `nats_manager.publish()` when NATS is available.

## Architecture Decisions

| ADR | Status | Decision |
|---|---|---|
| ADR-0001 | Accepted | Adopt local/offline event-driven clean architecture baseline |
| ADR-0002 | Accepted | Adopt JDOS v1.2 architecture corrections |

## FND-001 → FND-012 Status (Phase 01)

| ID | Task | Status |
|---|---|---|
| FND-001 | Initialize repository toolchains and lockfiles | Done |
| FND-002 | Define local configuration schema | Done |
| FND-003 | Add Compose stack | Done |
| FND-004 | Configure NATS accounts, subjects, JetStream | Done |
| FND-005 | Configure database roles and migrations | Done |
| FND-006 | Configure Qdrant and Redis policies | Done |
| FND-007 | Configure Ollama adapter boundary | Done |
| FND-008 | Add CI and local quality commands | Done |
| FND-009 | Add backup/restore proof | Done |
| FND-010 | Produce SBOM and dependency policy | Done |
| FND-011 | Verify approved Ollama models | Done |
| FND-012 | Validate sensitive payload policy | Done |

Phase 01 percentage: **12 of 12 implemented**. Exit gate: end-to-end Compose evidence + production hardening ADRs.

## SVC-002 Settings Service Status

| ID | Task | Status | Tests |
|---|---|---|---|
| SVC-002-A | Domain model, value objects, factory, rules, events | Done | 107 |
| SVC-002-B | Port protocols (repository, outbox, clock, id gen) | Done | 43 |
| SVC-002-C | Persistence DTOs, mapper protocols, schema contracts | Done | 65 |
| SVC-002-D | Use cases (get, patch, reset, get-by-key) | Done | 55 |
| SVC-002-E | Adapters (mappers, models, repository, outbox) | Done | 54 |
| SVC-002-F | Bootstrap (FastAPI routes, DI wiring, NATS publisher) | Done | 76 |
| SVC-002-G | Integration & final verification | Done | 101 |
| **Total** | | | **501** |

## SVC-003 Memory Service Status

| ID | Task | Status | Tests |
|---|---|---|---|
| SVC-003-A | Domain model, value objects, enums, entities, events, rules, factory | Done | 258 |
| SVC-003-B | Port protocols (repository, outbox, clock, id gen) | Done | 67 |
| SVC-003-C | Persistence DTOs, mapper protocols, schema contracts | Done | 96 |
| SVC-003-D | Use cases (create, update, delete, get, list) | Done | 58 |
| SVC-003-E | Adapters (mappers, models, repositories, clock, id gen) | Done | 78 |
| SVC-003-F | Bootstrap (DI wiring, NATS publisher, REST API, tests) | Done | 84 |
| SVC-003-G | Integration & service closure | Done | 87 |
| **Total** | | | **728** |

## SVC-004 Knowledge Service Status

| ID | Task | Status | Tests |
|---|---|---|---|
| SVC-004-A | Domain model, value objects, enums, entities, events, rules, factory | Done | 206 |
| SVC-004-B | Application ports (repository, outbox, clock, id gen) | Done | 75 |
| SVC-004-C | Persistence DTOs, mapper protocols, schema contracts | Done | 142 |
| SVC-004-D | Application use cases (12 use cases, request/response DTOs, exceptions) | Done | 75 |
| SVC-004-E | Adapters (mappers, models, repositories, outbox, clock, id gen) | Done | 85 |
| SVC-004-F | Bootstrap, API, NATS (DI wiring, REST routes, outbox publisher) | Done | 98 |
| SVC-004-G | Integration & service closure | Done | 116 |
| **Total** | | | **797** |

## SVC-001 Audit Service Status

| ID | Task | Status | Tests |
|---|---|---|---|
| SVC-001-A | Domain model, value objects, factory, rules, events | Done | 63 |
| SVC-001-B | Port Protocols (repository, outbox, clock, id gen) | Done | 30 |
| SVC-001-C | Persistence DTOs, mapper protocols, schema contracts | Done | 49 |
| SVC-001-D | Application use cases, request/response DTOs | Done | 23 |
| SVC-001-E | SQLAlchemy ORM models, mapper impls, repository impls | Done | 26 |
| SVC-001-F | Service bootstrap (FastAPI routes, NATS, DI wiring) | Done | — |
| SVC-001-G | Integration & API contract tests | Done | 38 |

## Session Handoff

### Objective

Complete SVC-004-G Knowledge Integration & Service Closure: 116
new tests (84 integration + 32 service closure), completion report,
final suite validation.

### Completed

- **`tests/test_knowledge_integration.py`** — 84 tests across 10 areas:
  `TestSourceLifecycle` (8), `TestDocumentLifecycle` (9),
  `TestChunkLifecycle` (9), `TestIngestionLifecycle` (9),
  `TestReindexFlow` (3), `TestRepositoryRoundtrip` (6),
  `TestEventFlow` (10), `TestRESTContract` (15),
  `TestCrossEntityIntegrity` (8), `TestOutboxOrdering` (7).
  Covers source/document/chunk/ingestion lifecycle transitions,
  reindex creates job with outbox event, DTO→ORM→DB→DTO→Domain
  roundtrip for all 5 entities with no data loss, all 10 domain
  events emitted through outbox with correct types and FIFO marking,
  all 11 REST routes with status codes, error bodies, and DTO shapes,
  cross-entity integrity (source→document→chunk cascade, inactive
  source blocking, deleted entity protection), and FIFO ordering
  with partial mark and pending isolation.
- **`tests/test_knowledge_service_closure.py`** — 32 tests across 10
  audit areas: `TestDomainEnumCompleteness` (3 — SourceStatus,
  DocumentStatus, IngestionStatus), `TestArchitectureImports` (4 —
  domain/ports/persistence/use_cases don't import adapters/bootstrap/
  api/nats), `TestLayerIsolation` (5 — no upward imports from any
  knowledge layer), `TestProviderAudit` (1 — 13 providers),
  `TestRouteAudit` (1 — 11 routes), `TestEventAudit` (1 — 10 outbox
  event types), `TestRepositoryAudit` (1 — 4 repos + 1 outbox),
  `TestMapperAudit` (1 — 5 mapper implementations), `TestDTOAudit`
  (1 — 5 storage DTOs), `TestSecurityCompliance` (5 — classification
  enforcement, empty name/title rejected, invalid transition blocked,
  invalid source type rejected, deleted source blocks activation),
  `TestCoverageMetrics` (9 — minimum test counts per layer).
- **`docs/status/knowledge_service_completion_report.md`** — Full
  completion report with layer summary, domain model, architecture,
  test coverage, file inventory, outbox events, known issues, and
  decisions recorded. Status: `KNOWLEDGE_SERVICE_COMPLETE`.

### Files Changed

- **Added:**
  `tests/test_knowledge_integration.py` — 1613 lines, 84 tests
  `tests/test_knowledge_service_closure.py` — 612 lines, 32 tests
  `docs/status/knowledge_service_completion_report.md` — full report
- **Updated:**
  `docs/status/development_status.md` — SVC-004-G completion

### Validation Performed

- 2563 total tests pass (797 knowledge + 728 memory + 501 settings
  + 229 audit + 263 foundation + 45 architecture). 116 new tests.
  0 failures, 1 pre-existing skip, 52 pre-existing warnings.
- All 84 integration tests pass: source/document/chunk/ingestion
  lifecycle transitions, reindex flow with outbox event, repository
  roundtrip for all 5 entities (no data loss), all 10 domain events
  emitted through outbox with correct types and FIFO marking, all 11
  REST routes with correct status codes and DTO shapes, cross-entity
  integrity (cascade, inactive block, deleted protection), outbox
  FIFO ordering with partial mark isolation.
- All 32 service closure tests pass: domain enum completeness,
  architecture import barriers (4 layers don't import adapters),
  layer isolation (no upward imports), provider audit (13/13),
  route audit (11/11), event audit (10/10), repository audit (4+1),
  mapper audit (5/5), DTO audit (5/5), security compliance (5/5),
  coverage metrics (9 thresholds met).
- Full suite: 0 failures, 1 pre-existing skip, 52 pre-existing warnings.

### Known Issues

- 1 pre-existing skip (`test_lockfile` — pnpm not on PATH).
- Route count: 11 distinct routes produce 13 `@router` registrations;
  closure route audit tests for 11 route URLs.
- `KnowledgeSource.activate()`/`disable()` don't emit events (only
  `delete()` emits `KnowledgeSourceDeleted`). Intentional design.

### Decisions Required

- None. Knowledge Service fully complete (A–G). Next step: Phase 03.

### Recommended Next Action

Proceed to Phase 03 services (SVC-005). All core services are now
complete: Audit (SVC-001), Settings (SVC-002), Memory (SVC-003),
Knowledge (SVC-004).

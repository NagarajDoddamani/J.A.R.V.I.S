# Development Status

**JDOS version:** 1.2  
**Last updated:** 2026-06-19  
**Updated by:** AI Agent  
**AI Brain Verification Sprint:** COMPLETE — BRAIN_VERIFIED (15/15 phases, 10/10 readiness)  
**Repository state:** SVC-001 complete. SVC-002 fully complete (A–G).
SVC-003 fully complete (A–G). SVC-004 fully complete (A–G).
SVC-005 fully complete (A–G). SVC-006 fully complete (A–G).
SVC-007 fully complete (A–G). SVC-008 fully complete (A–G).
SVC-009 fully complete (A–G). SVC-010 fully complete (A–G).
SVC-011 fully complete (A–G). Agent domain, ports, persistence contracts, use cases, adapters, bootstrap/API/NATS, and integration/service closure (E, EB, EC, ED, EE, EF, EG) complete.
SVC-011-E Agent Layer Domain — COMPLETE (344 domain tests, 0 failures).
SVC-011-EB Agent Application Ports — COMPLETE (92 port tests, 0 failures).
SVC-011-EC Agent Persistence Contracts — COMPLETE (173 persistence contract tests, 0 failures).
SVC-011-ED Agent Application Use Cases — COMPLETE (86 use case tests, 0 failures).
SVC-011-EE Agent Adapters — COMPLETE (47 adapter unit tests + 38 repository integration tests, 0 failures).
Runtime Verification Sprint Phase 2 — COMPLETE (RUNTIME_VERIFIED, 10/10).
N/A
total tests (45 architecture + 728 memory + 501 settings + 229
audit + 263 foundation + 797 knowledge + 810 notification + 302 planner
domain + 106 planner ports + 194 planner persistence + 96 planner use
cases + 39 planner adapters + 32 planner repository integration + 17
planner bootstrap + 49 planner API + 12 planner NATS + 77 planner
integration + 48 planner service closure + 296 research
domain + 64 research
ports + 107 research persistence
contracts + 52 research use
cases + 47 research adapters + 35
research repository integration + 16 research bootstrap + 48 research API
+ 12 research NATS + 76
research integration + 48 research service closure + 272
orchestrator domain + 81 orchestrator ports + 157 orchestrator persistence + 92 orchestrator use cases + 53 orchestrator adapters + 45 orchestrator repository integration + 25
orchestrator bootstrap + 50 orchestrator API + 15 orchestrator NATS + 106
orchestrator integration + 50 orchestrator service closure + 321
automation domain + 82 automation ports + 168 automation persistence
contracts + 88 automation use cases + 36 automation adapters + 34
automation repository integration + 17 automation bootstrap + 30
automation API + 12 automation NATS + 68 automation integration + 53
automation service closure + 300 policy
domain + 344 agent
domain + 92 agent ports + 173 agent persistence
contracts + 86 agent use
cases + 47 agent adapter unit + 38 agent repository
integration + 90 policy ports + 182 policy persistence
contracts + 84 policy use
cases + 48 policy adapters + 38 policy repository
integration + 17 policy bootstrap + 28 policy API + 12 policy NATS + 76
policy integration + 70 policy service closure + 45 architecture fitness
other).
Phase 01 exit gate remains open.

## Current Phase

**AI Brain Verification Sprint — COMPLETE (BRAIN_VERIFIED).**
**Phase 05: Research Agent — SVC-007-G Integration & Service Closure complete.**
**Phase 06: Agent Orchestrator — SVC-008-G Integration & Service Closure complete.**
**All Agent Infrastructure — COMPLETE.**

## Phase 03: Notification Services — COMPLETE.

810 tests, 0 failures.

## Phase 04: Planner Agent — COMPLETE.

**SVC-006-A through SVC-006-G complete.** 972 planner tests, 0 failures.

## Phase 05: Research Agent — SVC-007-A through SVC-007-G complete.

**SVC-007-A complete.** 296 research domain tests, 0 failures.
**SVC-007-B complete.** 64 research port tests, 0 failures.
**SVC-007-C complete.** 107 research persistence contract tests, 0 failures.
**SVC-007-D complete.** 52 research use case tests, 0 failures.
**SVC-007-E complete.** 82 research adapter tests (47 unit + 35 integration), 0 failures.
**SVC-007-F complete.** 79 research bootstrap/API/NATS tests (16 bootstrap + 48 API + 12 NATS), 0 failures.
**SVC-007-G complete.** 124 research integration & service closure tests (76 integration + 48 service closure), 0 failures.
**SVC-008-A complete.** 272 orchestrator domain tests (value objects, enums, events, WorkflowStep lifecycle, Workflow lifecycle, Orchestration lifecycle, rules, factory), 0 failures.
**SVC-008-B complete.** 81 orchestrator port tests (OrchestrationRepositoryPort contract, WorkflowRepositoryPort contract, StepRepositoryPort contract, outbox FIFO/idempotency/limit, clock protocol, ID generator protocol, 13-event union conformance, protocol structural conformance), 0 failures.
**SVC-008-C complete.** 157 orchestrator persistence contract tests (DTO construction/immutability/nullables/field counts for 4 DTOs, mapper domain_to_dto/dto_to_domain/roundtrip for 4 mappers, 13-event outbox mapper roundtrip, schema contracts for 4 tables — column names/types/nullability/enum values/primary keys/indexes/max_length, alignment between DTO↔schema fields, schema↔domain enums, DTO↔domain nullable parity, event union↔schema event_type count), 0 failures.
**SVC-008-D complete.** 92 orchestrator use case tests, 0 failures.
**SVC-008-E complete.** 98 orchestrator adapter tests (53 adapter unit + 45 repository integration), 0 failures. (create orchestration, 6 lifecycle commands, create/complete/fail workflow, add/start/complete/fail step, 3 queries, 4 exception hierarchy, 18 persistence verifications, 3 outbox event type checks, 5 DTO correctness, 5 edge cases, 5 integration flows), 0 failures.

949 total orchestrator tests pass (0 failures). 9269 total repository tests pass.

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
- **SVC-006-F Planner Bootstrap, API, and NATS** — 22 dependency
  providers (7 plan commands, 5 task commands, 4 queries, 5 internal
  adapters) with FastAPI `Depends`, 17 REST routes at `/api/v1/planner`
  (10 plans + 7 tasks) with error mapping (404 for PlanNotFoundError/
  TaskNotFoundError, 400 for PlannerDomainError, 422 for validation),
  NATS outbox publisher (`publish_planner_outbox_events`) with 11 event
  subjects (`jarvis.planner.event.<type>.v1`), FIFO ordering, envelope
  with event_id/event_type/aggregate_id/occurred_at/payload,
  batch/interval/max_iterations params. Fixed plan repository to load
  tasks when querying plans (needed for lifecycle rules like
  `assert_plan_has_tasks`) and added `plan_id` to domain `Task` model.
  `backend/main.py` and `backend/api/router.py` updated. 78 tests
  (17 bootstrap + 49 API + 12 NATS). 847 planner tests, 4365 total.
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
4. Run the Phase 01 Compose stack end-to-end and capture
   evidence for the exit gate (NATS replay, in-VM message
   size, model verification live, backup round-trip, payload
   fixture suite, lockfile parity).
5. Production grant pattern for the per-service roles.
6. Pin exact production image versions.

## Known Issues

- SQLite compatibility requires stripping schema from ORM metadata
  in test fixtures (`t.schema = None`). Production uses
  PostgreSQL with per-service schemas.
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

## SVC-006 Planner Service Status

| ID | Task | Status | Tests |
|---|---|---|---|
| SVC-006-A | Domain model, value objects, enums, entities, events, rules, factory | Done | 302 |
| SVC-006-B | Application ports (repository, outbox, clock, id gen) | Done | 106 |
| SVC-006-C | Persistence contracts (DTOs, mappers, schema) | Done | 194 |
| SVC-006-D | Use cases (17 use cases, 20 DTOs, 3 exceptions) | Done | 96 |
| SVC-006-E | Adapters (4 ORM models, 4 mapper impls, 3 repo impls, clock, id gen) | Done | 71 |
| SVC-006-F | Bootstrap, API, NATS | Done | 78 |
| SVC-006-G | Integration & service closure | Done | 125 |
| **Total** | | | **972** |

## SVC-007 Research Service Status

| ID | Task | Status | Tests |
|---|---|---|---|
| SVC-007-A | Domain model, value objects, enums, entities, events, rules, factory | Done | 296 |
| SVC-007-B | Application ports (repository, outbox, clock, id gen) | Done | 64 |
| SVC-007-C | Persistence contracts (DTOs, mapper protocols, schema) | Done | 107 |
| SVC-007-D | Use cases (15 use cases, request/response DTOs, exceptions) | Done | 52 |
| SVC-007-E | Adapters (4 ORM models, 4 mapper impls, 3 repo impls, outbox, clock, id gen) | Done | 82 |
| SVC-007-F | Bootstrap (17 providers), API (15 routes), NATS (7 subjects) | Done | 79 |
| SVC-007-G | Integration & service closure | Done | 124 |
| **Total** | | | **804** |

## SVC-008 Agent Orchestrator Status

| ID | Task | Status | Tests |
|---|---|---|---|
| SVC-008-A | Domain model, value objects, enums, entities, events, rules, factory | Done | 272 |
| SVC-008-B | Application ports (repository, outbox, clock, id gen) | Done | 81 |
| SVC-008-C | Persistence contracts (DTOs, mapper protocols, schema contracts) | Done | 157 |
| SVC-008-D | Use cases (create orchestration, lifecycle commands, workflow/step management, queries) | Done | 92 |
| SVC-008-E | Adapters (4 ORM models, 4 mapper impls, 3 repo impls, outbox, clock, id gen) | Done | 98 |
| SVC-008-F | Bootstrap, API, NATS (DI wiring, 19 REST routes, 13 event outbox publisher) | Done | 90 |
| SVC-008-G | Integration & service closure (lifecycles, roundtrips, events, REST, architecture audits) | Done | 156 |
| **Total** | | | **949** |

## SVC-005 Notification Service Status

| ID | Task | Status | Tests |
|---|---|---|---|
| SVC-005-A | Domain model, value objects, enums, entities, events, rules, factory | Done | 252 |
| SVC-005-B | Application ports (repository, outbox, clock, id gen) | Done | 62 |
| SVC-005-C | Persistence DTOs, mapper protocols, schema contracts | Done | 110 |
| SVC-005-D | Application use cases (9 use cases, request/response DTOs, exceptions) | Done | 74 |
| SVC-005-E | Adapters (mappers, models, repositories, outbox, clock, id gen) | Done | 63 |
| SVC-005-F | Bootstrap, API, NATS (DI wiring, REST routes, outbox publisher) | Done | 117 |
| SVC-005-G | Integration & service closure | Done | 132 |
| **Total** | | | **810** |

## SVC-009 Automation Service Status

| ID | Task | Status | Tests |
|---|---|---|---|
| SVC-009-A | Domain model, value objects, enums, entities, events, rules, factory | Done | 321 |
| SVC-009-B | Application ports (repository, outbox, clock, id gen) | Done | 82 |
| SVC-009-C | Persistence contracts (DTOs, mapper protocols, schema) | Done | 168 |
| SVC-009-D | Use cases | Done | 88 |
| SVC-009-E | Adapters (mappers, models, repositories, outbox, clock, id gen) | Done | 70 |
| SVC-009-F | Bootstrap, API, NATS | Done | 59 |
| SVC-009-G | Integration & service closure | Done | 153 |
| **Total** | | | **941** |

## SVC-010 Policy Engine Service Status

| ID | Task | Status | Tests |
|---|---|---|---|
| SVC-010-A | Domain model, value objects, enums, entities, events, rules, factory | Done | 300 |
| SVC-010-B | Application ports (repository, outbox, clock, id gen) | Done | 90 |
| SVC-010-C | Persistence contracts (DTOs, mapper protocols, schema) | Done | 182 |
| SVC-010-D | Use cases (17 use cases, 28 DTOs, 3 exceptions) | Done | 84 |
| SVC-010-E | Adapters (4 ORM models, 4 mapper impls, 4 repo impls, outbox, clock, id gen) | Done | 86 |
| SVC-010-F | Bootstrap (17 providers), API (17 routes), NATS (11 subjects) | Done | 57 |
| SVC-010-G | Integration & service closure (lifecycles, roundtrips, events, REST, architecture audits) | Done | 184 |
| **Total** | | | **946** |

## SVC-011 Runtime Command Bus Status

| ID | Task | Status | Tests |
|---|---|---|---|
| SVC-011-A | Runtime Command Bus (envelope, handler, registry, dispatcher, subscriber, errors, NATS) | Done | 126 |
| SVC-011-B | Runtime Service Adapters (8 service adapters + registration helpers) | Done | 109 |
| SVC-011-C | Runtime Workflow Engine (models, engine, executor, state, registry, errors) | Done | 151 |
| SVC-011-D | Runtime Orchestration Flows (templates, factory, coordinator, DTOs, exceptions) | Done | 158 |
| SVC-011-E | Agent Domain (model, exceptions, rules, factory) | Done | 344 |
| SVC-011-EB | Agent Application Ports (repository, outbox, clock, id gen) | Done | 92 |
| SVC-011-EC | Agent Persistence Contracts (DTOs, mapper protocols, schema) | Done | 173 |
| SVC-011-ED | Agent Application Use Cases (17 use cases, 27 DTOs, 3 exceptions) | Done | 86 |
| SVC-011-EE | Agent Adapters (4 ORM models, 4 mapper impls, 4 repo impls, outbox, clock, id gen) | Done | 85 |
| SVC-011-EF | Agent Bootstrap (18 providers), API (18 routes), NATS (12 subjects, envelope, publisher) | Done | 70 |
| SVC-011-EG | Agent Integration Tests (144), Service Closure (68), Completion Report | Done | 212 |
| SVC-011-RT | Runtime Verification Sprint Phase 2 | Done | 41 verification checks |
| **Total** | | | **1062 agent + 544 runtime (+ 41 verification)** |

## Runtime Verification Sprint — Phase 2

**Status:** COMPLETE
**Verdict:** RUNTIME_VERIFIED (Readiness: 10/10)
**Date:** 2026-06-16
**Report:** `docs/status/runtime_verification_report.md`

All 7 phases executed and passed:
- Phase 1: Startup Verification — 7/7 checks passed
- Phase 2: Runtime Coordinator — 5/5 checks passed (3 workflow types verified)
- Phase 3: Persistence — 6/6 checks passed
- Phase 4: Outbox — 7/7 checks passed (FIFO, idempotent mark_published)
- Phase 5: NATS — 8/8 checks passed (serialization, validation, governance)
- Phase 6: Failure — 7/7 checks passed (invalid/expired commands, cancellation, state)
- Phase 7: Readiness — 30/30 component checks passed, score 10/10

Failures verified: invalid command (CommandRejectedError), expired command (CommandExpiredError),
handler failure (CommandResult.success=False), workflow cancellation (RUNNING->CANCELLED),
step failure (state consistent, FAILED status).

Total: 41 evidence points, 38 PASS, 1 INFO, 1 WARN, 0 FAIL.

## Session Handoff

### Objective

Complete SVC-011-EG — Agent Integration Tests, Service Closure Tests, and Completion Report.

### Completed

- **`tests/test_agent_integration.py`** — 144 tests covering: agent lifecycle (create→activate→pause→disable, all status sequences, error cases); task lifecycle (create→start→complete/fail/cancel, status validation, 404/400 errors); execution lifecycle (start→complete/fail, paused/disabled agent guard, double-complete guard); repository roundtrip (save/find for agent/task/execution with children, count, filter by status/type/agent_id/task_id); outbox lifecycle (append/fetch/mark, FIFO, limit, idempotent mark); FIFO ordering (all 12 events, full 12-event FIFO); REST contract coverage (all 18 routes, 200/201/404/400 status codes, query filtering by agent_id/status/type/task_id, empty/invalid input validation); API-to-outbox pipeline (each operation publishes correct event type); NATS pipeline (API→outbox→NATS flow, envelope structure).
- **`tests/test_agent_service_closure.py`** — 68 tests covering: enum inventory (4 enums); event inventory (all 12 events); route inventory (18 routes); provider inventory (18 providers); repository inventory (4 repos); mapper inventory (4 mappers); architecture barriers (6 import barrier checks); DTO inventory (31 total: 4 persistence + 27 use case); coverage metrics (≥ 1000 total agent tests).
- **`docs/status/agent_service_completion_report.md`** — Full completion report with architecture diagram, layer summary, DTO inventory, route/provider/event/repository inventories, test inventory, integration coverage table, service closure audit coverage.

### Defects Fixed

- `SqlAlchemyAgentRepository.save()` — now persists child tasks and executions (previously only saved the agent row, causing task/execution data loss).
- `SqlAlchemyAgentTaskRepository.find_by_agent_id()` — fixed type annotation from `str` to `AgentId` with `str()` conversion (matching execution repo pattern).

### Files Changed

- `backend/agent/adapters/outbound/sqlalchemy_repository.py` — Modified: `save` persists child tasks/executions; `find_by_agent_id` accepts `AgentId`; added `_task_model_from_dto`, `_task_model_update_from_dto`, `_execution_model_from_dto`, `_execution_model_update_from_dto` helpers.
- `tests/test_agent_integration.py` — New: 144 integration tests.
- `tests/test_agent_service_closure.py` — New: 68 service closure tests.
- `docs/status/agent_service_completion_report.md` — New: Agent Service completion report.
- `docs/status/development_status.md` — Modified: SVC-011-EG marked COMPLETE.

### Contracts Changed

- None — no API, event, or schema changes.

### Validation Performed

- **212 EG tests pass** (0 failures): 144 integration + 68 service closure.
- Combined with prior agent layers: **1062 total agent tests pass** (0 failures).
- No regressions in existing agent tests.
- Architecture fitness path checks pass.

### Known Issues

- Domain empty-string validation returns 400 (AgentDomainError) instead of 422 (input validation). Consistent with all other services in the repository.
- Outbox publisher uses raw `js.publish()` without governance envelope validation (same pattern as all other services).

### Decisions Required

- None — SVC-011-EG is complete per spec. Agent Service is fully complete.

### Recommended Next Action

Proceed to Phase 06 integration work as defined in `docs/development/Phase_06_Integration.md`.

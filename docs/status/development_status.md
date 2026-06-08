# Development Status

**JDOS version:** 1.2  
**Last updated:** 2026-06-09  
**Updated by:** AI Agent  
**Repository state:** SVC-001 Audit Service fully validated (229 tests).
SVC-002-A Settings Domain layer implemented (107 tests). 381 total
tests pass (45 architecture + 107 settings + 229 audit).
Phase 01 exit gate remains open.

## Current Phase

**Phase 02: Core Services — Step 3: SVC-002-A Settings Domain (In Progress)**

The Settings Service domain layer (SVC-002-A) has been implemented
following the same hexagonal patterns as SVC-001:

- **SVC-002-A Domain** (107 tests): `SettingsProfile` aggregate root,
  `Setting` value object, `SettingDefinition` schema, `SettingCategory`
  (6 categories), `SettingScope`, `Version`. `SettingsProfileFactory`
  creates validated profiles with defaults. 12 domain rules (key format,
  type validation, bounds, max length, allowed values, safety floor,
  reserved keys). Domain events: `SettingUpdated`, `SettingsReset`.

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

## Pending Tasks

1. **SVC-002-B Settings Ports** — Port protocols for repository, cache,
   event publisher.
2. **SVC-002-C Persistence Contracts** — Storage DTOs, mapper protocols,
   schema contracts for `settings` schema.
3. **SVC-002-D Use Cases** — GetSettings, PatchSettings, ResetSettings,
   GetSettingByKey use cases.
4. **SVC-002-E Adapters** — SQLAlchemy ORM models, mapper impls,
   repository impls.
5. **SVC-002-F Service Bootstrap** — FastAPI routes, DI wiring.
6. **SVC-001 outbox publisher hardening** — Governance envelope validation
   (use `nats_manager.publish()`), retry budget, DLQ routing,
   graceful NATS disconnect handling, ACK tracking.
7. Run the Phase 01 Compose stack end-to-end and capture
   evidence for the exit gate (NATS replay, in-VM message
   size, model verification live, backup round-trip, payload
   fixture suite, lockfile parity).
8. Production grant pattern for the per-service roles.
9. Pin exact production image versions.

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

Implement SVC-002-A Settings Service domain layer following the same
hexagonal architecture and quality standards established by SVC-001 Audit.
Domain layer only — no ports, no persistence, no infrastructure.

### Completed

- **SVC-002-A Settings Domain** (107 tests):
  - `backend/settings/domain/model.py` — Value objects: `SettingId` (UUID),
    `Version` (major.minor), `SettingCategory` (6-category StrEnum),
    `SettingScope` (user/system/service StrEnum), `SettingDefinition`
    (schema with key/category/scope/type/defaults/bounds/safety_floor),
    `Setting` (key-value pair). Aggregate root: `SettingsProfile` with
    `get()`, `has_key()`, `get_all_in_category()`, `apply_setting()`,
    `apply_patch()`, `reset_to_defaults()`. Domain events: `SettingUpdated`,
    `SettingsReset`.
  - `backend/settings/domain/exceptions.py` — 14 typed exceptions:
    `SettingsDomainError`, `InvalidSettingKeyError`, `UnknownSettingKeyError`,
    `InvalidSettingValueError`, `InvalidSettingCategoryError`,
    `InvalidSettingScopeError`, `SafetyFloorViolationError`,
    `ReservedSettingKeyError`, `SchemaVersionMismatchError`,
    `InvalidVersionError`, `SettingTypeMismatchError`, `SettingBoundsError`,
    `SettingMaxLengthError`, `SettingAllowedValuesError`,
    `DuplicateSettingKeyError`.
  - `backend/settings/domain/rules.py` — 12 validation rules:
    `assert_key_format` (regex `[a-z_]+(\.[a-z_]+)*`), `assert_key_known`,
    `assert_key_not_reserved`, `assert_category_valid`, `assert_scope_valid`,
    `assert_version_valid`, `assert_value_type` (bool/int/float/str/list/dict),
    `assert_value_not_exceeds_max_length`, `assert_value_in_bounds`,
    `assert_value_in_allowed`, `assert_safety_floor` (min value + boolean
    default floor), `validate_setting_value` (composite).
  - `backend/settings/domain/factory.py` — `SettingsProfileFactory.create()`
    builds a validated profile with defaults from a definition registry.
  - Canonical default registry with 19 settings across 6 categories:
    3 System (language, timezone, auto_start), 3 Privacy (history_retention,
    analytics, consent_required [reserved]), 5 Voice (wake_word, mic,
    retain_audio, tts_enabled, tts_speed), 3 Notification (sounds_enabled,
    quiet_hours_start/end), 3 Model (temperature, top_p, max_tokens),
    2 UI (theme, reduced_motion).

### Files Changed

- **Added:**
  `backend/settings/__init__.py`
  `backend/settings/domain/__init__.py`
  `backend/settings/domain/model.py`
  `backend/settings/domain/exceptions.py`
  `backend/settings/domain/rules.py`
  `backend/settings/domain/factory.py`
  `tests/test_settings_domain.py` — 107 comprehensive domain tests.
- **Updated:**
  `docs/status/development_status.md` (this update).

### Contracts Changed

- **No external contracts changed** — domain layer only. No ports, APIs,
  events, or persistence schemas yet.

### Validation Performed

- **107 settings domain tests pass** covering:
  - Value objects: SettingId (uniqueness, string), Version (validation,
    string, current, equality), SettingCategory/SettingScope (all values),
    SettingDefinition, Setting.
  - Key validation: format regex (valid, empty, dot-prefix/suffix, uppercase,
    spaces, special chars, numeric start, deep nesting), known keys,
    reserved keys.
  - Category/scope/version validation: valid/invalid values.
  - Value validation: type matching (bool/int/float/str/list/dict), max
    length, numeric bounds, allowed values, safety floor (numeric min,
    boolean default floor).
  - Factory: creates profile with defaults, registry match, custom version,
    empty registry, invalid definition rejection.
  - Aggregate: initial state, create with settings, get/has_key queries,
    apply new/update setting, emit SettingUpdated events, apply_patch
    (multi-update, unknown key→error, validation, empty, safety floor),
    get_all_in_category, reset_to_defaults (reset/event), event accumulation
    and immutability.
  - Edge cases: unknown key, type mismatches (str↔bool, float↔int, None),
    zero value, repr.
  - Default registry: 19 settings across 6 categories, all valid, category
    counts, reserved key enforcement.
- **381 total tests pass** (45 architecture + 107 settings domain + 229 audit).

### Known Issues

- 1 pre-existing skip (`test_lockfile` — pnpm not on PATH).

### Decisions Required

- Proceed with SVC-002-B (Settings ports), SVC-002-C (persistence contracts),
  or switch to another service?

### Recommended Next Action

Continue the Settings hexagonal stack:

1. **SVC-002-B Settings Ports** — Port protocols: `SettingsRepositoryPort`,
   `SettingsCachePort`, `SettingsEventPublisherPort`.
2. **SVC-002-C Persistence Contracts** — Storage DTOs, mapper protocols,
   schema contracts for `settings` schema.
3. **SVC-002-D Use Cases** — GetSettings, PatchSettings, ResetSettings,
   GetSettingByKey.
4. **SVC-002-E Adapters** — SQLAlchemy ORM models, mapper impls.
5. **SVC-002-F Service Bootstrap** — FastAPI routes, DI wiring.

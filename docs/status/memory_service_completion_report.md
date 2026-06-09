# Memory Service Completion Report

**JDOS v1.2 — SVC-003 Memory Service (A–G)**  
**Date:** 2026-06-09  
**Status:** Complete

---

## Scope

The Memory Service provides domain-driven memory management with consent-based access control, outbox-backed event publishing, and a FastAPI REST interface. It is implemented across all seven hexagonal architecture layers (A–G).

---

## Layer Summary

| Layer | ID | Tests | Key Artifacts |
|---|---|---|---|
| Domain | SVC-003-A | 258 | `Memory`, `ConsentRecord` aggregates, 13 domain rules, 8 domain events, `MemoryFactory` |
| Ports | SVC-003-B | 67 | 5 `typing.Protocol` interfaces (repository, outbox, clock, id gen) |
| Persistence | SVC-003-C | 96 | `MemoryStorageDTO`, `ConsentStorageDTO`, `MemoryOutboxStorageDTO`, schema contracts |
| Use Cases | SVC-003-D | 58 | `CreateMemoryUseCase`, `UpdateMemoryUseCase`, `DeleteMemoryUseCase`, `GetMemoryUseCase`, `SearchMemoriesUseCase`, `GrantConsentUseCase`, `RevokeConsentUseCase`, `GetConsentUseCase` |
| Adapters | SVC-003-E | 78 | 3 ORM models, 3 mapper impls, 3 repository impls, clock, ID gen |
| Bootstrap | SVC-003-F | 84 | 8 DI providers, NATS publisher, 8 REST routes |
| Integration & Closure | SVC-003-G | 87 | Full lifecycle, outbox audit, REST contracts, architecture audits, registry audit, coverage metrics, security compliance |
| **Total** | | **728** | |

---

## Domain Model

### Entities
- **Memory** — Aggregate root with `MemoryId`, `MemoryContent`, `Provenance`, `RetentionPolicy`, `MemoryCategory`, `MemoryState` (CREATED→UPDATED→DELETED), and `RevisionNumber`. Commands: `create()`, `update()`, `delete()`.
- **ConsentRecord** — `ConsentId`, `ConsentStatus` (PROPOSED→ACTIVE→REVOKED→PURGED), `granted_at`, `expires_at`, `revoked_at`, `policy_version`. Commands: `grant()`, `revoke()`, `purge()`.

### Domain Events (8)
| Event | Trigger | Payload |
|---|---|---|
| `MemoryCreated` | Memory created | memory_id, content, category, provenance |
| `MemoryUpdated` | Memory updated | memory_id, content, category, provenance, revision |
| `MemoryDeleted` | Memory deleted | memory_id, reason |
| `MemoryPurgeScheduled` | Retention expired | memory_id, scheduled_at |
| `MemoryPurged` | Memory purged | memory_id |
| `MemoryRetentionExpired` | Retention expired | memory_id, retention_period |
| `ConsentGranted` | Consent granted | consent_id |
| `ConsentRevoked` | Consent revoked | consent_id |

### Domain Rules (13)
1. Content not empty
2. Max length 10 000 characters
3. No secrets in content (password, token, api_key, private_key)
4. Consent must be ACTIVE
5. Retention policy required
6. Revision monotonicity
7. Deleted memory blocks updates
8. Revoked consent blocks updates
9. Provenance required
10. Source required
11. Category must be valid
12. Purged consent is dead
13. Expiration after grant

---

## Architecture

### Hexagonal Layers
```
┌─────────────────────────────────────────┐
│  REST API (FastAPI)                     │
│  /api/v1/memory/memories/  (5 routes)   │
│  /api/v1/memory/consents/  (3 routes)   │
├─────────────────────────────────────────┤
│  Bootstrap (DI wiring)                  │
│  8 × Depends() providers                │
├─────────────────────────────────────────┤
│  Use Cases (8)                          │
│  Create | Update | Delete | Get | Search│
│  GrantConsent | RevokeConsent | GetCons │
├─────────────────────────────────────────┤
│  Ports (5 Protocols)                    │
├─────────────────────────────────────────┤
│  Adapters                               │
│  Repositories | Mappers | ORM | Clock   │
├─────────────────────────────────────────┤
│  Database (SQLite/PostgreSQL)           │
└─────────────────────────────────────────┘
```

### Event Flow
```
Client → API → UseCase → Repository (DB)
                        → Outbox (append event)
                                 ↓
                        NATS Publisher (poll → publish → mark)
                                 ↓
                        NATS JetStream (jarvis.memory.event.*.v1)
```

### REST API
| Method | Route | Status | Error Codes |
|---|---|---|---|
| POST | `/memories/` | 201 | 400, 422 |
| PATCH | `/memories/{id}` | 200 | 400, 404, 422 |
| DELETE | `/memories/{id}` | 200 | 400, 404 |
| GET | `/memories/{id}` | 200 | 404 |
| GET | `/memories/` | 200 | (search params) |
| POST | `/consents/` | 201 | — |
| POST | `/consents/{id}/revoke` | 200 | 400, 404 |
| GET | `/consents/{id}` | 200 | 404 |

---

## Test Coverage

| Category | Tests |
|---|---|
| Domain (SVC-003-A) | 258 |
| Ports (SVC-003-B) | 67 |
| Persistence (SVC-003-C) | 96 |
| Use Cases (SVC-003-D) | 58 |
| Adapters (SVC-003-E) | 78 |
| Bootstrap/API/NATS (SVC-003-F) | 84 |
| Integration (SVC-003-G) | 55 |
| Service Closure (SVC-003-G) | 32 |
| **Total Memory** | **728** |

### Integration Test Groups (55 tests)
- `TestConsentLifecycle` — 7 tests (grant→get→revoke→find→count, event emission)
- `TestMemoryLifecycle` — 8 tests (create→get→update→delete→search→deleted, event emission)
- `TestOutboxEvents` — 9 tests (all 8 event types, FIFO, mark_published)
- `TestRepositoryRoundtrip` — 3 tests (DTO→ORM→DB→DTO→Domain)
- `TestRESTContract` — 12 tests (all 8 routes, status codes, errors, search)
- `TestCrossServiceScenarios` — 3 tests (consent gate logic through API)

### Service Closure Test Groups (32 tests)
- `TestRegistryAudit` — 8 tests (providers, routes, models, events, subjects, errors)
- `TestArchitectureCompliance` — 4 tests (import barriers, allowed paths)
- `TestLayerIsolation` — 5 tests (no upward imports from any layer)
- `TestCoverageMetrics` — 4 tests (minimum counts)
- `TestSecurityCompliance` — 2 tests (no secrets, no PII in outbox)

---

## Files Created/Modified

### Production Code
| File | Purpose |
|---|---|
| `backend/memory/domain/model.py` | Domain entities, value objects, events, rules |
| `backend/memory/domain/ports.py` | Protocol interfaces |
| `backend/memory/application/persistence/dto.py` | Storage DTOs |
| `backend/memory/application/persistence/contracts.py` | Schema contracts |
| `backend/memory/application/use_cases/*.py` | 8 use cases |
| `backend/memory/adapters/outbound/models.py` | 3 ORM models |
| `backend/memory/adapters/outbound/mapper.py` | 3 mapper impls |
| `backend/memory/adapters/outbound/sqlalchemy_repository.py` | 3 repository impls |
| `backend/memory/adapters/outbound/clock.py` | SystemClockAdapter |
| `backend/memory/adapters/outbound/id_generator.py` | UuidGeneratorAdapter |
| `backend/memory/bootstrap.py` | 8 DI providers |
| `backend/memory/nats.py` | NATS outbox publisher |
| `backend/api/endpoints/memory.py` | 8 REST routes |
| `backend/api/router.py` | Router registration |
| `backend/main.py` | Outbox publisher lifespan task |

### Test Code
| File | Tests | Purpose |
|---|---|---|
| `tests/test_memory_domain.py` | 258 | Domain model, rules, events, factory |
| `tests/test_memory_ports.py` | 67 | Protocol conformance |
| `tests/test_memory_persistence.py` | 96 | DTOs, schema, contracts |
| `tests/test_memory_use_cases.py` | 58 | Use case execution |
| `tests/test_memory_adapters.py` | 32 | Mapper unit tests |
| `tests/test_memory_repository_integration.py` | 46 | Repository roundtrip, outbox |
| `tests/test_memory_bootstrap.py` | 16 | DI wiring, API error paths |
| `tests/test_memory_api.py` | 46 | API happy/error paths |
| `tests/test_memory_nats.py` | 22 | NATS publisher |
| `tests/test_memory_integration.py` | 55 | Lifecycle, outbox, REST contracts |
| `tests/test_memory_service_closure.py` | 32 | Registry, architecture, coverage |

---

## Outbox Events (8)

| Event Type | NATS Subject | Payload Fields |
|---|---|---|
| `memory_created` | `jarvis.memory.event.memory_created.v1` | memory_id, content, category, provenance |
| `memory_updated` | `jarvis.memory.event.memory_updated.v1` | memory_id, content, category, provenance, revision |
| `memory_deleted` | `jarvis.memory.event.memory_deleted.v1` | memory_id, reason |
| `memory_purge_scheduled` | `jarvis.memory.event.memory_purge_scheduled.v1` | memory_id, scheduled_at |
| `memory_purged` | `jarvis.memory.event.memory_purged.v1` | memory_id |
| `memory_retention_expired` | `jarvis.memory.event.memory_retention_expired.v1` | memory_id, retention_period |
| `consent_granted` | `jarvis.memory.event.consent_granted.v1` | consent_id |
| `consent_revoked` | `jarvis.memory.event.consent_revoked.v1` | consent_id |

---

## Known Issues

1. **SQLite test compatibility** — All test files strip schema from ORM metadata (`_table.schema = None`) for SQLite compatibility. Production uses PostgreSQL with `memory` schema.
2. **UUID V4 vs V7** — `UuidGeneratorAdapter` uses `uuid4()`. Should switch to `platform.uuidv7()` for time-ordered UUID column clustering in production.
3. **NATS governance envelope** — Outbox publisher uses raw `js.publish()` without governance envelope validation. Should use `nats_manager.publish()` when NATS is available.
4. **SAWarning in existing tests** — `test_memory_api.py` and `test_memory_bootstrap.py` emit `SAWarning: transaction already deassociated from connection` due to SQLite connection-bound session pattern.

---

## Decisions Recorded

- `mark_published` filters by `aggregate_id` (not `event_id`) to match port contract where event_id is the string representation of MemoryId or ConsentId.
- NATS subjects use underscores for event types: `jarvis.memory.event.memory_created.v1`.
- `DeletedMemoryUpdateError` maps to 400 (domain blocks double-deletion).
- Bootstrap and NATS files added to `ALLOWED_ADAPTER_PATHS` in architecture fitness test.

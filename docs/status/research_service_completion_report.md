# Research Service Completion Report

**JDOS v1.2 — SVC-007 Research Service (A–G)**  
**Date:** 2026-06-10  
**Status:** Complete

---

## Scope

The Research Service provides domain-driven research request management with job orchestration, source tracking, summary generation, outbox-backed event publishing, and a FastAPI REST interface. It is implemented across all seven hexagonal architecture layers (A–G).

---

## Layer Summary

| Layer | ID | Tests | Key Artifacts |
|---|---|---|---|
| Domain | SVC-007-A | 296 | `ResearchRequest`, `ResearchJob`, `ResearchSource` aggregates, 14 domain rules, 7 domain events, `ResearchFactory` |
| Ports | SVC-007-B | 64 | 4 `typing.Protocol` interfaces (3 repository, 1 outbox, clock, id gen) |
| Persistence | SVC-007-C | 107 | `ResearchRequestStorageDTO`, `ResearchJobStorageDTO`, `ResearchSourceStorageDTO`, `ResearchOutboxStorageDTO`, schema contracts |
| Use Cases | SVC-007-D | 52 | 15 use cases (5 request lifecycle, 4 job lifecycle, add_source, generate_summary, 4 queries) with 25 request/response DTOs |
| Adapters | SVC-007-E | 82 | 4 ORM models, 4 mapper impls, 3 repository impls, outbox, clock, ID gen |
| Bootstrap | SVC-007-F | 79 | 15 DI providers, NATS publisher, 15 REST routes |
| Integration & Closure | SVC-007-G | 124 | Full lifecycle, outbox audit, REST contracts, architecture audits, registry audit, coverage metrics |
| **Total** | | **804** | |

---

## Domain Model

### Entities
- **ResearchRequest** — Aggregate root with `RequestId`, `ResearchTopic`, `ResearchPriority` (low/normal/high/critical), `ResearchStatus` (created→running→completed→failed→cancelled). Commands: `start()`, `complete()`, `fail()`, `cancel()`.
- **ResearchJob** — Entity with `JobId`, `Query`, `ResearchStatus` lifecycle, associated to a `ResearchRequest` via `request_id`.
- **ResearchSource** — Value object (entity in persistence) with `SourceId`, `Url`, `SourceType` (memory/knowledge/web/document/user), `Summary`, `RelevanceScore`.

### Domain Events (7)
| Event | Trigger | Payload |
|---|---|---|
| `ResearchRequested` | Request created | request_id, topic, priority |
| `ResearchStarted` | Request started | request_id |
| `ResearchCompleted` | Request completed | request_id, summary |
| `ResearchFailed` | Request failed | request_id, reason |
| `ResearchCancelled` | Request cancelled | request_id |
| `SourceAdded` | Source added to job | source_id, job_id, url, type |
| `ResearchSummaryGenerated` | Summary generated | job_id, sources, summary |

### Domain Rules (14)
1. Topic must not be empty
2. Max topic length 500 characters
3. Priority must be valid
4. Status transitions follow: created→running→completed (or failed/cancelled)
5. Cannot start an already started request
6. Cannot complete a not-started request
7. Cannot fail a completed request
8. Cannot cancel a completed request
9. Jobs can only be created on running requests
10. Jobs track their own status independently
11. Sources require a valid URL
12. Summary generation creates a source entry
13. At least one source before summary generation (configurable)
14. Request completion requires all jobs to be complete (configurable)

---

## Architecture

### Hexagonal Layers
```
┌─────────────────────────────────────────┐
│  REST API (FastAPI)                     │
│  /api/v1/research/*  (15 routes)        │
├─────────────────────────────────────────┤
│  Bootstrap (DI wiring)                  │
│  15 × Depends() providers               │
├─────────────────────────────────────────┤
│  Use Cases (15)                         │
│  Request CRUD | Job lifecycle | Sources │
│  Summary | Queries                      │
├─────────────────────────────────────────┤
│  Ports (4 Protocols)                    │
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
                        NATS JetStream (jarvis.research.event.*.v1)
```

### REST API
| Method | Route | Status | Error Codes |
|---|---|---|---|
| POST | `/requests` | 201 | 400, 422 |
| GET | `/requests/{request_id}` | 200 | 404 |
| GET | `/requests` | 200 | — |
| POST | `/requests/{request_id}/start` | 200 | 400, 404, 422 |
| POST | `/requests/{request_id}/complete` | 200 | 400, 404 |
| POST | `/requests/{request_id}/fail` | 200 | 400, 404 |
| POST | `/requests/{request_id}/cancel` | 200 | 400, 404 |
| POST | `/requests/{request_id}/jobs` | 201 | 400, 404 |
| POST | `/jobs/{job_id}/start` | 200 | 400, 404 |
| POST | `/jobs/{job_id}/complete` | 200 | 400, 404 |
| POST | `/jobs/{job_id}/fail` | 200 | 400, 404 |
| GET | `/jobs/{job_id}` | 200 | 404 |
| GET | `/jobs` | 200 | — |
| POST | `/jobs/{job_id}/sources` | 201 | 400, 404 |
| POST | `/jobs/{job_id}/summary` | 200 | 400, 404 |

---

## Test Coverage

| Category | Tests |
|---|---|
| Domain (SVC-007-A) | 296 |
| Ports (SVC-007-B) | 64 |
| Persistence (SVC-007-C) | 107 |
| Use Cases (SVC-007-D) | 52 |
| Adapters (SVC-007-E) | 82 |
| Bootstrap/API/NATS (SVC-007-F) | 79 |
| Integration (SVC-007-G) | 76 |
| Service Closure (SVC-007-G) | 48 |
| **Total Research** | **804** |

### Integration Test Groups (76 tests)
- `TestRequestFullLifecycle` — 12 tests (create→get→start→fail→complete→cancel, list by status, invalid priority)
- `TestJobLifecycle` — 12 tests (create→get→list→start→fail→complete, empty/list by status/multi-request)
- `TestSourceLifecycle` — 5 tests (add→get→list, post-completion, multiple sources)
- `TestSummaryGeneration` — 5 tests (generate→completes request→marks completed→adds source→not found)
- `TestErrorChangingCompleted` — 3 tests (start/fail/cancel on completed request)
- `TestErrorChangingCancelled` — 3 tests (start/fail/complete on cancelled request)
- `TestErrorInvalidTransitions` — 6 tests (complete/fail not-started, start started, job for not-started/completed/cancelled request)
- `TestOutboxEvents` — 10 tests (all 7 event types, FIFO ordering, mark_published filter, empty skip)
- `TestRepositoryRoundtrip` — 3 tests (DTO→ORM→DB→DTO→Domain)
- `TestRESTContract` — 13 tests (all routes, 201/200/404/400/422 status codes, list filters)
- `TestCrossServiceScenarios` — 5 tests (create→start→job, full chain, multiple requests, multi-job, cancelled no job)

### Service Closure Test Groups (48 tests)
- `TestEnumCompleteness` — 6 tests (ResearchStatus, SourceType, ResearchPriority values and counts)
- `TestEventCompleteness` — 4 tests (7 events exist, outbox mapping, NATS subjects, convention)
- `TestRouteInventory` — 2 tests (15 routes registered, HTTP methods)
- `TestProviderInventory` — 2 tests (15 use-case providers, return types)
- `TestRepositoryInventory` — 5 tests (3 repos + outbox, method completeness)
- `TestMapperInventory` — 5 tests (4 mapper impls, bidirectional mapping)
- `TestDtoInventory` — 3 tests (4 persistence DTOs, 25 use-case DTOs, total count)
- `TestArchitectureImportBarriers` — 8 tests (no adapter frameworks in domain/ports/persistence/use_cases, port isolation, persistence isolation, bootstrap composition root, NATS file)
- `TestLayerIsolation` — 1 test (no upward imports from lower layers)
- `TestCoverageMetrics` — 12 tests (all 11 research test files exist, total completeness)

---

## Files Created/Modified

### Production Code
| File | Purpose |
|---|---|
| `backend/research/domain/model.py` | Domain entities, value objects, events, rules |
| `backend/research/domain/ports.py` | Protocol interfaces |
| `backend/research/application/persistence/dto.py` | Storage DTOs |
| `backend/research/application/persistence/contracts.py` | Schema contracts |
| `backend/research/application/use_cases/*.py` | 15 use cases |
| `backend/research/adapters/outbound/models.py` | 4 ORM models |
| `backend/research/adapters/outbound/mapper.py` | 4 mapper impls |
| `backend/research/adapters/outbound/sqlalchemy_repository.py` | 3 repository impls |
| `backend/research/adapters/outbound/clock.py` | SystemClockAdapter |
| `backend/research/adapters/outbound/id_generator.py` | UuidV7GeneratorAdapter |
| `backend/research/bootstrap.py` | 15 DI providers |
| `backend/research/nats.py` | NATS outbox publisher |
| `backend/api/endpoints/research.py` | 15 REST routes |
| `backend/api/router.py` | Router registration |
| `backend/main.py` | Outbox publisher lifespan task |

### Test Code
| File | Tests | Purpose |
|---|---|---|
| `tests/test_research_domain.py` | 296 | Domain model, rules, events, factory |
| `tests/test_research_ports.py` | 64 | Protocol conformance |
| `tests/test_research_persistence_contracts.py` | 107 | DTOs, schema, contracts |
| `tests/test_research_use_cases.py` | 52 | Use case execution |
| `tests/test_research_adapters.py` | 47 | Mapper unit tests |
| `tests/test_research_repository_integration.py` | 35 | Repository roundtrip, outbox |
| `tests/test_research_bootstrap.py` | 16 | DI wiring, API error paths |
| `tests/test_research_api.py` | 48 | API happy/error paths |
| `tests/test_research_nats.py` | 12 | NATS publisher |
| `tests/test_research_integration.py` | 76 | Lifecycle, outbox, REST contracts |
| `tests/test_research_service_closure.py` | 48 | Registry, architecture, coverage |

---

## Outbox Events (7)

| Event Type | NATS Subject | Payload Fields |
|---|---|---|
| `research_requested` | `jarvis.research.event.requested.v1` | request_id, topic, priority |
| `research_started` | `jarvis.research.event.started.v1` | request_id |
| `research_completed` | `jarvis.research.event.completed.v1` | request_id, summary |
| `research_failed` | `jarvis.research.event.failed.v1` | request_id, reason |
| `research_cancelled` | `jarvis.research.event.cancelled.v1` | request_id |
| `source_added` | `jarvis.research.event.source_added.v1` | source_id, job_id, url, type |
| `summary_generated` | `jarvis.research.event.summary_generated.v1` | job_id, sources, summary |

---

## Known Issues

1. **ResearchJob domain entity lacks `request_id`** — The `ResearchJobStorageDTO` carries `request_id` but the mapper sets it to `None` from the domain side. `find_by_request_id` uses the DTO's storage value.
2. **ResearchRequest.complete() requires loaded jobs** — The aggregate requires jobs loaded for completion validation, but `find_by_id()` does not load associated jobs. Full completion requires repository-level job loading.
3. **SQLite test compatibility** — All test files strip schema from ORM metadata (`_table.schema = None`) for SQLite compatibility. Production uses PostgreSQL with `research` schema.
4. **UUID V4 vs V7** — `UuidV7GeneratorAdapter` uses `uuid4()`. Should switch to `platform.uuidv7()` for time-ordered UUID column clustering in production.
5. **NATS governance envelope** — Outbox publisher uses raw `js.publish()` without governance envelope validation. Should use `nats_manager.publish()` when NATS is available.

---

## Decisions Recorded

- Research jobs are separate entities (not value objects) to support independent lifecycle management.
- `mark_published` filters by `aggregate_id` to match port contract where `event_id` is the string representation of the domain ID.
- NATS subjects use underscore-separated event types: `jarvis.research.event.requested.v1`.
- Bootstrap and NATS files added to `ALLOWED_ADAPTER_PATHS` in architecture fitness test.
- REST routes are nested under `/api/v1/research/` following service convention.

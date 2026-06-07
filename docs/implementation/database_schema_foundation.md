# Database Schema Strategy (Foundation, JDOS v1.2)

**Status:** Implemented in `backend/migrations/versions/743a95f81f31_initial_foundation_setup.py`
**Effective date:** 2026-06-07
**Authority:** Companion to
`docs/architecture/JDOS_v1.2_Architecture_Corrections_Addendum.md` and
`docs/implementation/database_strategy.md`.

## 1. Schemas

The foundation migration creates one PostgreSQL schema per bounded
service. Each schema is owned by the schema-owning user
(`jarvis_admin` in development) and is writable only through its
per-service role in production.

| Schema | Owner role (dev) | Application role (prod) | Purpose |
|---|---|---|---|
| `platform` | `jarvis_admin` | n/a | Shared extensions, `uuidv7()` generator, Alembic version table. |
| `orchestration` | `jarvis_admin` | `jarvis_orchestration_app` | Request lifecycle, plans, tasks, capability grants. |
| `memory` | `jarvis_admin` | `jarvis_memory_app` | Memory records, consent, retention, deletion jobs. |
| `knowledge` | `jarvis_admin` | `jarvis_knowledge_app` | Sources, documents, chunks, ingestion jobs. |
| `notification` | `jarvis_admin` | `jarvis_notification_app` | Notification lifecycle and delivery state. |
| `settings` | `jarvis_admin` | `jarvis_settings_app` | User settings, feature flags, runtime configuration. |
| `audit` | `jarvis_admin` | `jarvis_audit_app` | Append-only audit entries and chain heads. |

## 2. Foundation Entities (Phase 01)

| Schema | Table | Purpose |
|---|---|---|
| `memory` | `consent_records` | Explicit active consent for a memory purpose/scope. |
| `memory` | `memories` | Consent-backed memory records (content column intentionally absent in Phase 01). |
| `audit` | `audit_entries` | Append-only, hash-chained, content-minimized audit log. |
| `audit` | `audit_chain_heads` | Per-chain head pointer and entry count. |
| `settings` | `user_settings` | User settings, feature flags, and runtime configuration. |

## 3. Outbox & Inbox

Each service schema owns a pair of tables that together implement
the durable transport surfaces described in
`docs/implementation/event_contracts.md` and
`docs/architecture/system_architecture.md`:

| Table | Purpose | Key columns |
|---|---|---|
| `{schema}.outbox` | Application-side transactional outbox. Rows are inserted in the same local transaction as the domain mutation; a publisher reads unpublished rows, pushes them to NATS, and stamps `published_at`. | `message_id`, `subject`, `payload`, `headers`, `correlation_id`, `causation_id`, `published_at`, `attempts`, `last_error` |
| `{schema}.inbox` | Idempotency log of consumed messages. A unique index on `(message_id, consumer_group)` enforces exactly-once semantics at the consumer boundary. | `message_id`, `consumer_group`, `subject`, `payload`, `headers`, `correlation_id`, `causation_id`, `processed_at` |

The outbox index `ix_<schema>_outbox_unpublished` partial-indexes
unpublished rows for fast dispatcher reads. The inbox unique index
`uq_<schema>_inbox_dedup` is the canonical idempotency key.

## 4. Identifiers, Timestamps, Concurrency

* **Primary keys** are `UUID` columns with a server-side default of
  `platform.uuidv7()`. The generator is implemented in
  `platform.uuidv7()` (PL/pgSQL) and is reproducible in Python via
  the standard `uuid` module when the application side needs to
  pre-allocate identifiers.
* **Timestamps** are `TIMESTAMPTZ` (`sa.DateTime(timezone=True)`)
  throughout. The application layer is expected to use UTC.
* **Optimistic locking** is supported on every mutable foundation
  entity through a `version INTEGER NOT NULL DEFAULT 1` column.
  Application updates must `WHERE version = ?` and increment the
  column in the same statement.
* **Soft delete** is expressed through a nullable
  `deleted_at TIMESTAMPTZ` column on mutable entities. The
  foundation migration applies unique indexes with
  `WHERE deleted_at IS NULL` so a deleted row can be re-created
  with the same natural key.
* **Audit** uses a hash-chained, append-only design with no mutable
  columns; integrity is enforced through `previous_hash` and
  `entry_hash` columns on `audit.audit_entries`.

## 5. Least Privilege

The migration creates the per-service roles (`jarvis_*.app`,
NOLOGIN) and grants `USAGE` on the corresponding schema. The
foundation tables receive CRUD grants scoped to the owning role.
The dev path continues to connect as `POSTGRES_USER`
(`jarvis_admin`) and bypasses the per-service roles.

Production deployment grants each per-service role to the
corresponding application user (e.g. via
`GRANT jarvis_memory_app TO memory_service_user;`). Application
connections then run under least privilege.

## 6. Sensitive Column Classification

The migration follows the addendum's column-classification rule:
columns whose content is highly sensitive (memory text, raw audio,
raw frames) are intentionally **not** created in Phase 01. Memory
content will be introduced in Phase 02 through an explicit
content-store relationship that owns the access policy.

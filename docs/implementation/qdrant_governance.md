# Qdrant Governance (Phase 01, FND-006)

JARVIS Qdrant is a private vector store used for user knowledge,
the research corpus, and memory summaries. The governance module
[`backend/core/qdrant_governance.py`](../../backend/core/qdrant_governance.py)
is the single source of truth for the collection registry, the
canonical vector configuration, and the retention / rebuild
policy.

## Embedding Configuration

The locked embedding model is `nomic-embed-text` (FND-011).
Its vector size is 768 and the canonical distance metric is
cosine. The values are governance constants:

| Field | Value |
|---|---|
| `vector_size` | 768 |
| `distance` | `Cosine` |

## Collection Registry

| Collection | Vector size | Distance | Shards | Replicas | On-disk payload |
|---|---|---|---|---|---|
| `jarvis_user_knowledge` | 768 | Cosine | 1 | 1 | true |
| `jarvis_research_corpus` | 768 | Cosine | 1 | 1 | true |
| `jarvis_memory_summaries` | 768 | Cosine | 1 | 1 | true |

Adding a collection requires an ADR. The
`QdrantCollection` enum is authoritative; `COLLECTION_REGISTRY`
exposes the full config for the runtime.

## Retention and Rebuild Policy

| Field | Value | Rationale |
|---|---|---|
| `retention_days` | 365 | 12 months by default; per-collection override via ADR. |
| `soft_delete_grace_days` | 30 | Soft-deleted points are purged after 30 days. |
| `rebuild_on_missing` | true | A missing collection is rebuilt from the authoritative source. |
| `rebuild_on_corrupt` | true | A corrupt collection snapshot triggers a rebuild. |
| `snapshot_before_rebuild` | true | A snapshot is taken before any destructive rebuild. |

The rebuild path is owned by Phase 02 service code; the policy
in the governance module is the contract.

## Validation

The architecture fitness test pins:

* `COLLECTION_REGISTRY` contains every `QdrantCollection`.
* `EXPECTED_VECTOR_SIZE` is 768.
* `EXPECTED_DISTANCE_METRIC` is `Cosine`.
* The Qdrant Compose service exposes both the REST and gRPC
  ports on loopback.

The unit test suite (`tests/test_qdrant_governance.py`) covers
the dynamic helpers (`is_registered_collection`,
`collection_config`, `vector_size_compatible`).

## Snapshot Layout

The Compose service binds a second named volume
(`qdrant_snapshots`) so the Qdrant snapshot API can write
snapshots without touching the storage path. The
backup/restore tool (`tools/backup/backup.py`) snapshots
`/qdrant/storage` directly and `/qdrant/snapshots` is reserved
for the Qdrant API path.

# Redis Governance (Phase 01, FND-006)

JARVIS Redis is a private in-memory store used for short-lived
state: session markers, distributed locks, rate-limit counters,
ephemeral caches, and durable caches that are cheap to recompute.

The governance module
[`backend/core/redis_governance.py`](../../backend/core/redis_governance.py)
is the single source of truth for the namespace, the per-service
prefix registry, the key-class TTL policy, the eviction policy,
and the maximum key size. The architecture fitness test pins
every value in place.

## Namespace

All keys live under the `jarvis:` namespace. The separator is
`:`. The full key shape is:

```
jarvis:<service-prefix>:<key-class>:<rest>
```

## Per-service Prefix Registry

| Service | Prefix |
|---|---|
| Orchestration | `jarvis:orch:` |
| Memory | `jarvis:mem:` |
| Knowledge | `jarvis:knw:` |
| Notification | `jarvis:ntf:` |
| Settings | `jarvis:set:` |
| Audit | `jarvis:aud:` |
| Gateway | `jarvis:gtw:` |
| Shared (transient) | `jarvis:shd:` |

Adding a service requires an ADR. The
`ServicePrefix` enum is the authoritative source of truth; the
`PREFIX_REGISTRY` exposes the full prefix string for use at the
adapter boundary.

## Key Classes and TTL Policy

| Key class | TTL (seconds) | Use |
|---|---|---|
| `session` | 3 600 | user session marker |
| `ratelimit` | 60 | per-minute rate limit counter |
| `lock` | 30 | distributed lock with explicit unlock |
| `ephemeral` | 300 | one-shot cache (idempotency token, etc.) |
| `durable` | 86 400 | long-lived cache (catalog, computed result) |

The TTL is applied at write time via the `EX` argument. The
adapter (`backend/core/redis.py`) MUST call `ttl_for(key_class)`
before issuing the `SET ... EX <ttl>` command.

## Eviction Policy

`docker-compose.yml` declares `maxmemory-policy allkeys-lru` and
caps the cache at 256 MB. The governance module's
`EXPECTED_EVICTION_POLICY` value must match. The architecture
fitness test enforces this parity.

## Maximum Key Size

A single Redis value must be no larger than **8 KiB** (see
`MAX_REDIS_KEY_BYTES`). Larger payloads must be stored in
PostgreSQL (bytea), Qdrant payload, or the local filesystem.

## Validation

The architecture fitness test pins:

* `PREFIX_REGISTRY` contains every `ServicePrefix`.
* `TTL_SECONDS_BY_CLASS` contains every `KeyClass`.
* The Compose `maxmemory-policy` matches
  `EXPECTED_EVICTION_POLICY`.

The unit test suite (`tests/test_redis_governance.py`) covers
the dynamic helpers (`namespaced_key`, `is_valid_key`, `ttl_for`).

## Out of Scope (Phase 02+)

* Cluster topology and replication (Phase 02+ requires an ADR).
* AOF tuning beyond the Compose default
  (`appendonly yes`, `appendfsync everysec`).
* Custom serializers (Phase 01 uses `decode_responses=True` and
  JSON for transient values).

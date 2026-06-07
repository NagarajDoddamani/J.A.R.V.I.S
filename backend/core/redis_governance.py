"""JARVIS Redis governance (Phase 01, FND-006).

The Redis instance is private infrastructure. The governance
module:

* declares the JARVIS namespace (``jarvis:``) and a per-service
  prefix registry,
* declares a key-class TTL policy (session, rate-limit, lock,
  ephemeral, durable-cache),
* declares the cache eviction policy (LRU on `allkeys`),
* exposes validation helpers that the architecture fitness test
  pins in place.

The runtime path is intentionally separate: the operational
client is in :mod:`backend.core.redis` and uses these constants
through a thin façade so a service cannot accidentally bypass
the prefix registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final


# ---------------------------------------------------------------------------
# Namespace + key-prefix registry
# ---------------------------------------------------------------------------

REDIS_NAMESPACE: Final[str] = "jarvis"
KEY_SEPARATOR: Final[str] = ":"


class ServicePrefix(str, Enum):
    """Authoritative per-service Redis key prefix.

    A service MUST use the prefix assigned to it here. New
    services require an ADR; random per-feature prefixes are not
    permitted.
    """

    ORCHESTRATION = "orch"
    MEMORY = "mem"
    KNOWLEDGE = "knw"
    NOTIFICATION = "ntf"
    SETTINGS = "set"
    AUDIT = "aud"
    GATEWAY = "gtw"
    SHARED = "shd"  # cross-service transient keys only


PREFIX_REGISTRY: Final[dict[ServicePrefix, str]] = {
    prefix: f"{REDIS_NAMESPACE}{KEY_SEPARATOR}{prefix.value}{KEY_SEPARATOR}"
    for prefix in ServicePrefix
}


def namespaced_key(prefix: ServicePrefix, *parts: str) -> str:
    """Build a fully-qualified Redis key.

    >>> namespaced_key(ServicePrefix.MEMORY, "session", "abc")
    'jarvis:mem:session:abc'
    """
    head = PREFIX_REGISTRY[prefix]
    return head + KEY_SEPARATOR.join(parts) if parts else head.rstrip(KEY_SEPARATOR)


# ---------------------------------------------------------------------------
# Key classes and TTL policy
# ---------------------------------------------------------------------------


class KeyClass(str, Enum):
    """Classes of Redis key with distinct lifetime rules."""

    SESSION = "session"           # user session
    RATE_LIMIT = "ratelimit"      # API rate limiter
    LOCK = "lock"                 # short-lived distributed lock
    EPHEMERAL = "ephemeral"       # one-shot cache (idempotency token, etc.)
    DURABLE_CACHE = "durable"     # long-lived cache (catalog, computed result)


@dataclass(frozen=True)
class TtlPolicy:
    """Authoritative TTL windows for each key class.

    The values are governance constants. Overriding them requires
    an ADR; tests pin them in place.
    """

    session_seconds: int = 60 * 60              # 1 hour
    rate_limit_seconds: int = 60                # 1 minute window
    lock_seconds: int = 30                      # 30 seconds
    ephemeral_seconds: int = 5 * 60             # 5 minutes
    durable_cache_seconds: int = 24 * 60 * 60   # 24 hours


TTL_POLICY: Final[TtlPolicy] = TtlPolicy()


# TTL windows per key class, expressed as the `EX` argument.
TTL_SECONDS_BY_CLASS: Final[dict[KeyClass, int]] = {
    KeyClass.SESSION: TTL_POLICY.session_seconds,
    KeyClass.RATE_LIMIT: TTL_POLICY.rate_limit_seconds,
    KeyClass.LOCK: TTL_POLICY.lock_seconds,
    KeyClass.EPHEMERAL: TTL_POLICY.ephemeral_seconds,
    KeyClass.DURABLE_CACHE: TTL_POLICY.durable_cache_seconds,
}


def ttl_for(key_class: KeyClass) -> int:
    """Return the authoritative TTL (seconds) for a key class."""
    return TTL_SECONDS_BY_CLASS[key_class]


# ---------------------------------------------------------------------------
# Eviction policy
# ---------------------------------------------------------------------------


class EvictionPolicy(str, Enum):
    """Cache eviction policy declared in the docker-compose contract.

    The Compose file sets ``maxmemory-policy allkeys-lru``; the
    governance module records the same value so architecture
    fitness can assert parity.
    """

    ALLKEYS_LRU = "allkeys-lru"
    VOLATILE_LRU = "volatile-lru"
    ALLKEYS_LFU = "allkeys-lfu"
    NO_EVICTION = "noeviction"


EXPECTED_EVICTION_POLICY: Final[EvictionPolicy] = EvictionPolicy.ALLKEYS_LRU


def is_eviction_policy_compatible(policy: str) -> bool:
    """Return ``True`` if ``policy`` matches the declared policy.

    Used by the architecture fitness test to enforce parity with
    the Compose contract.
    """
    return policy.strip().lower() == EXPECTED_EVICTION_POLICY.value


# ---------------------------------------------------------------------------
# Key validation
# ---------------------------------------------------------------------------


def is_valid_key(key: str) -> bool:
    """Return ``True`` when ``key`` is a properly namespaced JARVIS key.

    A key is valid when it starts with one of the registered
    prefixes. The function is used by the architecture fitness
    test to gate dynamic key construction.
    """
    for prefix in PREFIX_REGISTRY.values():
        if key.startswith(prefix):
            return True
    return False


# ---------------------------------------------------------------------------
# Cardinality for a single Redis key
# ---------------------------------------------------------------------------

MAX_REDIS_KEY_BYTES: Final[int] = 8 * 1024  # 8 KiB
"""The maximum serialized size of a single Redis value. Larger
values must be stored elsewhere (PostgreSQL bytea, Qdrant payload,
or the local filesystem)."""

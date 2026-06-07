"""Tests for the Redis governance module (Phase 01, FND-006)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.core.redis_governance import (  # noqa: E402
    EXPECTED_EVICTION_POLICY,
    KEY_SEPARATOR,
    MAX_REDIS_KEY_BYTES,
    PREFIX_REGISTRY,
    REDIS_NAMESPACE,
    TTL_POLICY,
    TTL_SECONDS_BY_CLASS,
    EvictionPolicy,
    KeyClass,
    ServicePrefix,
    is_eviction_policy_compatible,
    is_valid_key,
    namespaced_key,
    ttl_for,
)


# ---------------------------------------------------------------------------
# Namespace
# ---------------------------------------------------------------------------


def test_namespace_and_separator() -> None:
    assert REDIS_NAMESPACE == "jarvis"
    assert KEY_SEPARATOR == ":"


def test_prefix_registry_covers_every_service() -> None:
    for prefix in ServicePrefix:
        assert prefix in PREFIX_REGISTRY
        assert PREFIX_REGISTRY[prefix].startswith(REDIS_NAMESPACE + KEY_SEPARATOR)
        assert PREFIX_REGISTRY[prefix].endswith(KEY_SEPARATOR)


def test_namespaced_key_builds_qualified_key() -> None:
    assert namespaced_key(ServicePrefix.MEMORY, "session", "abc") == "jarvis:mem:session:abc"
    assert namespaced_key(ServicePrefix.AUDIT, "chain", "head") == "jarvis:aud:chain:head"


def test_namespaced_key_with_no_parts() -> None:
    assert namespaced_key(ServicePrefix.GATEWAY) == "jarvis:gtw"


# ---------------------------------------------------------------------------
# TTL
# ---------------------------------------------------------------------------


def test_ttl_policy_is_frozen() -> None:
    with pytest.raises((AttributeError, TypeError)):
        TTL_POLICY.session_seconds = 1  # type: ignore[misc]


@pytest.mark.parametrize(
    "key_class,expected",
    [
        (KeyClass.SESSION, 3600),
        (KeyClass.RATE_LIMIT, 60),
        (KeyClass.LOCK, 30),
        (KeyClass.EPHEMERAL, 300),
        (KeyClass.DURABLE_CACHE, 86_400),
    ],
)
def test_ttl_for_key_class(key_class: KeyClass, expected: int) -> None:
    assert ttl_for(key_class) == expected
    assert TTL_SECONDS_BY_CLASS[key_class] == expected


# ---------------------------------------------------------------------------
# Eviction policy
# ---------------------------------------------------------------------------


def test_expected_eviction_policy_is_allkeys_lru() -> None:
    assert EXPECTED_EVICTION_POLICY is EvictionPolicy.ALLKEYS_LRU


def test_is_eviction_policy_compatible() -> None:
    assert is_eviction_policy_compatible("allkeys-lru")
    assert is_eviction_policy_compatible("  ALLKEYS-LRU  ")
    assert not is_eviction_policy_compatible("volatile-lru")
    assert not is_eviction_policy_compatible("noeviction")


# ---------------------------------------------------------------------------
# Key validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key,valid",
    [
        ("jarvis:mem:session:abc", True),
        ("jarvis:aud:chain:head", True),
        ("jarvis:gtw:", True),
        ("jarvis:mem", True),
        ("memory:session:abc", False),
        ("jarvis:unknown:foo:bar", False),
        ("", False),
    ],
)
def test_is_valid_key(key: str, valid: bool) -> None:
    assert is_valid_key(key) is valid


# ---------------------------------------------------------------------------
# Maximum key size
# ---------------------------------------------------------------------------


def test_max_redis_key_bytes_is_8_kib() -> None:
    assert MAX_REDIS_KEY_BYTES == 8 * 1024


# ---------------------------------------------------------------------------
# Compose parity
# ---------------------------------------------------------------------------


def test_compose_maxmemory_policy_matches_governance() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "--maxmemory-policy" in compose
    # Extract the policy value.
    for line in compose.splitlines():
        if "--maxmemory-policy" in line:
            parts = line.split("--maxmemory-policy", 1)[1].strip().split()
            assert parts, "maxmemory-policy value missing"
            policy = parts[0].rstrip(",")
            assert is_eviction_policy_compatible(policy), (
                f"Compose maxmemory-policy {policy!r} does not match governance "
                f"expected {EXPECTED_EVICTION_POLICY.value!r}"
            )
            return
    pytest.fail("--maxmemory-policy not found in docker-compose.yml")

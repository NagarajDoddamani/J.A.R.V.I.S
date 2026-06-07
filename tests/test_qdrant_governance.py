"""Tests for the Qdrant governance module (Phase 01, FND-006)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.core.qdrant_governance import (  # noqa: E402
    COLLECTION_REGISTRY,
    EXPECTED_DISTANCE_METRIC,
    EXPECTED_VECTOR_SIZE,
    NOMIC_EMBED_TEXT_VECTOR_SIZE,
    RETENTION_POLICY,
    CollectionConfig,
    DistanceMetric,
    QdrantCollection,
    collection_config,
    is_registered_collection,
    vector_size_compatible,
)


# ---------------------------------------------------------------------------
# Embedding configuration
# ---------------------------------------------------------------------------


def test_expected_vector_size_matches_nomic_embed_text() -> None:
    assert NOMIC_EMBED_TEXT_VECTOR_SIZE == 768
    assert EXPECTED_VECTOR_SIZE == 768


def test_expected_distance_metric_is_cosine() -> None:
    assert EXPECTED_DISTANCE_METRIC is DistanceMetric.COSINE


# ---------------------------------------------------------------------------
# Collection registry
# ---------------------------------------------------------------------------


def test_collection_registry_covers_every_collection() -> None:
    for collection in QdrantCollection:
        assert collection in COLLECTION_REGISTRY


@pytest.mark.parametrize("collection", list(QdrantCollection))
def test_collection_config_consistent_with_registry(collection: QdrantCollection) -> None:
    cfg = COLLECTION_REGISTRY[collection]
    assert isinstance(cfg, CollectionConfig)
    assert cfg.name == collection.value
    assert cfg.vector_size == EXPECTED_VECTOR_SIZE
    assert cfg.distance is EXPECTED_DISTANCE_METRIC
    assert cfg.shard_number >= 1
    assert cfg.replication_factor >= 1


def test_collection_names_have_jarvis_prefix() -> None:
    for cfg in COLLECTION_REGISTRY.values():
        assert cfg.name.startswith("jarvis_"), (
            f"collection {cfg.name!r} must be prefixed with `jarvis_`"
        )


# ---------------------------------------------------------------------------
# is_registered_collection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("collection", list(QdrantCollection))
def test_is_registered_collection_true_for_canonical(collection: QdrantCollection) -> None:
    assert is_registered_collection(collection.value)


@pytest.mark.parametrize(
    "name",
    [
        "jarvis_unknown",
        "memory_summaries",
        "",
        "JARVIS_USER_KNOWLEDGE",
    ],
)
def test_is_registered_collection_false_for_unknown(name: str) -> None:
    assert not is_registered_collection(name)


# ---------------------------------------------------------------------------
# collection_config
# ---------------------------------------------------------------------------


def test_collection_config_returns_canonical_entry() -> None:
    cfg = collection_config(QdrantCollection.MEMORY_SUMMARIES.value)
    assert cfg.name == QdrantCollection.MEMORY_SUMMARIES.value


def test_collection_config_unknown_raises() -> None:
    with pytest.raises(KeyError):
        collection_config("jarvis_unknown")


# ---------------------------------------------------------------------------
# vector_size_compatible
# ---------------------------------------------------------------------------


def test_vector_size_compatible_true_for_locked() -> None:
    assert vector_size_compatible(EXPECTED_VECTOR_SIZE)


def test_vector_size_compatible_false_for_other_sizes() -> None:
    assert not vector_size_compatible(384)
    assert not vector_size_compatible(1024)
    assert not vector_size_compatible(0)


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------


def test_retention_policy_defaults() -> None:
    assert RETENTION_POLICY.retention_days == 365
    assert RETENTION_POLICY.soft_delete_grace_days == 30
    assert RETENTION_POLICY.rebuild_on_missing is True
    assert RETENTION_POLICY.rebuild_on_corrupt is True
    assert RETENTION_POLICY.snapshot_before_rebuild is True


# ---------------------------------------------------------------------------
# Compose parity (gRPC + REST)
# ---------------------------------------------------------------------------


def test_compose_exposes_qdrant_rest_and_grpc_on_loopback() -> None:
    from tests.test_helpers import service_block
    block = service_block("qdrant")
    assert block
    assert "6333" in block and "6334" in block
    assert "127.0.0.1:" in block

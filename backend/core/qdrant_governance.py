"""JARVIS Qdrant governance (Phase 01, FND-006).

The Qdrant instance is private infrastructure. The governance
module:

* declares the collection registry (one collection per
  knowledge surface),
* records the canonical vector configuration (size, distance,
  shards, replication, on-disk payload),
* declares the retention and rebuild policy,
* exposes validation helpers that the architecture fitness test
  pins in place.

The runtime path is intentionally separate: the operational
client is in :mod:`backend.core.qdrant` and uses these constants
through a thin façade so a service cannot accidentally create
an out-of-policy collection.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final


# ---------------------------------------------------------------------------
# Distance + embedding configuration
# ---------------------------------------------------------------------------


class DistanceMetric(str, Enum):
    COSINE = "Cosine"
    DOT = "Dot"
    EUCLID = "Euclid"


EXPECTED_DISTANCE_METRIC: Final[DistanceMetric] = DistanceMetric.COSINE


# The locked embedding model is ``nomic-embed-text`` (Phase 01,
# FND-011). Its vector size is 768. Future embedding upgrades
# require an ADR.
NOMIC_EMBED_TEXT_VECTOR_SIZE: Final[int] = 768
EXPECTED_VECTOR_SIZE: Final[int] = NOMIC_EMBED_TEXT_VECTOR_SIZE


# ---------------------------------------------------------------------------
# Collection registry
# ---------------------------------------------------------------------------


class QdrantCollection(str, Enum):
    """Authoritative Qdrant collection registry.

    Adding a collection requires an ADR; tests pin the registry
    in place.
    """

    USER_KNOWLEDGE = "jarvis_user_knowledge"
    RESEARCH_CORPUS = "jarvis_research_corpus"
    MEMORY_SUMMARIES = "jarvis_memory_summaries"


@dataclass(frozen=True)
class CollectionConfig:
    name: str
    vector_size: int
    distance: DistanceMetric
    shard_number: int = 1
    replication_factor: int = 1
    on_disk_payload: bool = True
    write_consistency_factor: int = 1


COLLECTION_REGISTRY: Final[dict[QdrantCollection, CollectionConfig]] = {
    QdrantCollection.USER_KNOWLEDGE: CollectionConfig(
        name=QdrantCollection.USER_KNOWLEDGE.value,
        vector_size=EXPECTED_VECTOR_SIZE,
        distance=EXPECTED_DISTANCE_METRIC,
    ),
    QdrantCollection.RESEARCH_CORPUS: CollectionConfig(
        name=QdrantCollection.RESEARCH_CORPUS.value,
        vector_size=EXPECTED_VECTOR_SIZE,
        distance=EXPECTED_DISTANCE_METRIC,
    ),
    QdrantCollection.MEMORY_SUMMARIES: CollectionConfig(
        name=QdrantCollection.MEMORY_SUMMARIES.value,
        vector_size=EXPECTED_VECTOR_SIZE,
        distance=EXPECTED_DISTANCE_METRIC,
    ),
}


# ---------------------------------------------------------------------------
# Retention and rebuild policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetentionPolicy:
    """Retention and rebuild rules.

    The retention window is governance-controlled; the rebuild
    rule describes the rebuild-from-source trigger when the
    collection is missing or corrupt.
    """

    retention_days: int = 365                # 12 months by default
    soft_delete_grace_days: int = 30         # 30 days after soft delete
    rebuild_on_missing: bool = True
    rebuild_on_corrupt: bool = True
    snapshot_before_rebuild: bool = True


RETENTION_POLICY: Final[RetentionPolicy] = RetentionPolicy()


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def is_registered_collection(name: str) -> bool:
    """Return ``True`` when ``name`` is in the authoritative registry."""
    return any(cfg.name == name for cfg in COLLECTION_REGISTRY.values())


def collection_config(name: str) -> CollectionConfig:
    """Return the canonical config for ``name`` or raise ``KeyError``."""
    for cfg in COLLECTION_REGISTRY.values():
        if cfg.name == name:
            return cfg
    raise KeyError(f"collection {name!r} is not in the registry")


def vector_size_compatible(declared: int) -> bool:
    """Return ``True`` when ``declared`` matches the locked size."""
    return declared == EXPECTED_VECTOR_SIZE

"""Canonical Ollama model manifest for JARVIS (JDOS v1.2, Correction 9).

The manifest is the single source of truth for the four locked models.
Every entry records:

* The canonical display name (matches the JDOS lock).
* The Ollama model identifier as it appears in ``ollama list``.
* The expected tag (e.g. ``qwen3:8b``).
* The immutable digest (sha256) that the foundation verifier checks
  against. Digests are environment-dependent; the manifest declares
  them under the ``digest`` key. They are intentionally empty until
  the operator pins them on first install. The verifier rejects the
  mismatch case.
* The minimum expected capability used by the smoke inference.
* License metadata sourced from the model publisher.

The manifest is intentionally declarative. The runtime verifier
(``tools.model_verification.verify_models``) consumes the manifest and
produces a verification report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ModelSpec:
    """A single JARVIS-approved model entry."""

    canonical_name: str
    ollama_name: str
    expected_tag: str
    purpose: str
    minimum_smoke_prompt: str
    smoke_max_tokens: int = 16
    license: str = "unknown"
    digest: Optional[str] = None  # sha256:...; filled by operator on first install
    notes: str = ""


# ---------------------------------------------------------------------------
# The four locked models (JDOS v1.2, Correction 9 + master_context.md)
# ---------------------------------------------------------------------------

CANONICAL_MODELS: tuple[ModelSpec, ...] = (
    ModelSpec(
        canonical_name="Qwen 3 8B",
        ollama_name="qwen3",
        expected_tag="8b",
        purpose="General assistant and reasoning model.",
        minimum_smoke_prompt="Reply with the single word OK.",
        smoke_max_tokens=8,
        license="Apache-2.0",
        notes="Primary general model; locked in master_context.md.",
    ),
    ModelSpec(
        canonical_name="Qwen Coder",
        ollama_name="qwen-coder",
        expected_tag="latest",
        purpose="Coding-focused model for the Coding Agent.",
        minimum_smoke_prompt="def add(a, b):\n    return",
        smoke_max_tokens=16,
        license="Apache-2.0",
        notes="Coding Agent runtime model.",
    ),
    ModelSpec(
        canonical_name="Qwen2.5-VL",
        ollama_name="qwen2.5-vl",
        expected_tag="latest",
        purpose="Vision-language model for the Vision Agent.",
        minimum_smoke_prompt="Describe the provided image in one sentence.",
        smoke_max_tokens=24,
        license="Apache-2.0",
        notes="Vision Agent runtime model.",
    ),
    ModelSpec(
        canonical_name="nomic-embed-text",
        ollama_name="nomic-embed-text",
        expected_tag="latest",
        purpose="Approved local embedding model (Correction 4).",
        minimum_smoke_prompt="",
        smoke_max_tokens=0,
        license="Apache-2.0",
        notes="Used through Ollama. Cloud embeddings and cloud fallback are prohibited.",
    ),
)


# ---------------------------------------------------------------------------
# Alias reconciliation
# ---------------------------------------------------------------------------

#: Some Ollama images register under different names. The verifier
#: accepts any of the aliases below for the corresponding canonical
#: model. The aliases are not authoritative and may be deprecated in
#: future revisions.
MODEL_ALIASES: dict[str, tuple[str, ...]] = {
    "qwen3": ("qwen3", "qwen3:8b", "qwen-3", "qwen-3-8b"),
    "qwen-coder": ("qwen-coder", "qwen2.5-coder", "qwen-coder:latest"),
    "qwen2.5-vl": ("qwen2.5-vl", "qwen2.5-vl:latest", "qwen2-vl"),
    "nomic-embed-text": ("nomic-embed-text", "nomic-embed-text:latest"),
}


def find_spec(installed_name: str) -> Optional[ModelSpec]:
    """Return the canonical spec for an installed Ollama model name.

    The lookup is alias-aware. An unknown installed name returns
    ``None`` and the verifier records it as "unsupported".
    """
    for spec in CANONICAL_MODELS:
        aliases = MODEL_ALIASES.get(spec.ollama_name, (spec.ollama_name,))
        if installed_name in aliases:
            return spec
    return None


def find_spec_by_canonical(canonical: str) -> Optional[ModelSpec]:
    for spec in CANONICAL_MODELS:
        if spec.canonical_name == canonical:
            return spec
    return None


__all__ = [
    "CANONICAL_MODELS",
    "MODEL_ALIASES",
    "ModelSpec",
    "find_spec",
    "find_spec_by_canonical",
]

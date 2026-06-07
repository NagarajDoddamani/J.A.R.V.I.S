"""Backup manifest generation (Phase 01, FND-009).

A manifest is a JSON document that describes one encrypted backup. It
records:

* ``schema_version`` and ``created_at`` (UTC, RFC 3339).
* ``jarvis_version`` (taken from ``backend.__init__`` or
  ``pyproject.toml``).
* Per-artifact entries (PostgreSQL dump, Qdrant snapshot, settings
  snapshot). Each entry records the local path, the SHA-256 of the
  plaintext, the SHA-256 of the ciphertext, the size in bytes, and
  the AES-GCM parameters required to decrypt.
* A list of excluded sources per Correction 6
  (``.env``, OS credential manager contents, Redis data, caches,
  temporary media, raw secrets).

The manifest itself is **not** encrypted. Its only secrets are the
KDF parameters and the per-backup salt and nonce, which the operator
already knows.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Final

from tools.backup.crypto import (
    NONCE_BYTES,
    PBKDF2_ITERATIONS,
    SALT_BYTES,
    manifest_payload_sha256,
)

SCHEMA_VERSION: Final[str] = "1.0.0"

# Sources that MUST be excluded from any backup, sourced from
# ``docs/architecture/JDOS_v1.2_Architecture_Corrections_Addendum.md``
# (Correction 6) and ``docs/implementation/database_strategy.md``.
EXCLUDED_SOURCES: Final[tuple[str, ...]] = (
    ".env",
    ".env.local",
    "**/.env",
    "**/.env.*",
    "**/secrets/**",
    "**/.aws/**",
    "**/.ssh/**",
    "**/redis/dump.rdb",
    "**/tmp/**",
    "**/cache/**",
    "**/__pycache__/**",
    "**/.pytest_cache/**",
)


@dataclass
class ArtifactEntry:
    """One artifact within a backup (PostgreSQL dump, Qdrant snapshot, ...)."""

    name: str
    source: str
    size_bytes: int
    plaintext_sha256: str
    ciphertext_sha256: str
    salt_hex: str
    nonce_hex: str
    iterations: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BackupManifest:
    schema_version: str = SCHEMA_VERSION
    created_at: str = ""
    jarvis_version: str = ""
    encryption: str = "AES-256-GCM"
    kdf: str = "PBKDF2-HMAC-SHA256"
    kdf_iterations: int = PBKDF2_ITERATIONS
    salt_bytes: int = SALT_BYTES
    nonce_bytes: int = NONCE_BYTES
    artifacts: list[ArtifactEntry] = field(default_factory=list)
    excluded_sources: tuple[str, ...] = EXCLUDED_SOURCES
    deletion_tombstones_present: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "jarvis_version": self.jarvis_version,
            "encryption": self.encryption,
            "kdf": self.kdf,
            "kdf_iterations": self.kdf_iterations,
            "salt_bytes": self.salt_bytes,
            "nonce_bytes": self.nonce_bytes,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "excluded_sources": list(self.excluded_sources),
            "deletion_tombstones_present": self.deletion_tombstones_present,
            "notes": self.notes,
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_manifest(
    *,
    artifacts: list[ArtifactEntry],
    jarvis_version: str = "",
    deletion_tombstones_present: bool = False,
    notes: str = "",
) -> BackupManifest:
    return BackupManifest(
        created_at=now_iso(),
        jarvis_version=jarvis_version,
        artifacts=artifacts,
        deletion_tombstones_present=deletion_tombstones_present,
        notes=notes,
    )


__all__ = [
    "ArtifactEntry",
    "BackupManifest",
    "EXCLUDED_SOURCES",
    "SCHEMA_VERSION",
    "build_manifest",
    "manifest_payload_sha256",
    "now_iso",
    "sha256_of_bytes",
]

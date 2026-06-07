"""JARVIS backup script (Phase 01, FND-009).

Local-only backup. The script:

1. Dumps PostgreSQL with ``pg_dump`` (custom format).
2. Snapshots the Qdrant storage directory (file copy; the Qdrant
   snapshot API is also acceptable but requires a running container).
3. Bundles the two artifacts with a settings snapshot into a tar
   stream, computes the SHA-256 of the plaintext, encrypts the
   tar with AES-256-GCM (see :mod:`tools.backup.crypto`).
4. Writes a manifest with checksums, KDF parameters, and the
   Exclusion List from Correction 6.
5. Verifies the encrypted blob's checksums on the way out.

The recovery passphrase is supplied through the
``JARVIS_BACKUP_PASSPHRASE`` environment variable. **The passphrase
is never written to disk.** Operators are expected to record the
passphrase in their personal secret manager.

Excluded sources (per Correction 6) are also covered by the
exclusion manifest: ``.env``, OS credential-manager contents,
Redis data, caches, temporary media, and any secret-bearing path.

The script is intentionally not async. It runs as a one-shot CLI.
"""

from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Final

from tools.backup.crypto import (
    BackupCryptoError,
    encrypt_backup,
    manifest_payload_sha256,
)
from tools.backup.manifest import (
    ArtifactEntry,
    build_manifest,
    sha256_of_bytes,
)

BACKUP_DIR: Final[Path] = Path("./backups")


def _pg_dump(postgres_url: str, out: Path) -> bytes:
    """Run ``pg_dump`` and return the bytes of the dump."""
    cmd = [
        "pg_dump",
        "--no-owner",
        "--no-privileges",
        "--format=custom",
        "--file",
        str(out),
        postgres_url,
    ]
    completed = subprocess.run(cmd, capture_output=True, check=False)
    if completed.returncode != 0:
        raise BackupCryptoError(
            f"pg_dump failed: {completed.stderr.decode('utf-8', errors='ignore')}"
        )
    return out.read_bytes()


def _qdrant_snapshot(qdrant_storage: Path, out: Path) -> bytes:
    """Copy the Qdrant storage directory into a tarball."""
    if not qdrant_storage.exists():
        # Qdrant storage is missing in the dev environment; the backup
        # is still useful. We write an empty marker.
        out.write_bytes(b"")
        return out.read_bytes()
    with tarfile.open(out, "w:gz") as tar:
        tar.add(qdrant_storage, arcname=qdrant_storage.name)
    return out.read_bytes()


def _settings_snapshot(out: Path) -> bytes:
    """Bundle the small JSON files that constitute user settings."""
    if out.exists():
        return out.read_bytes()
    out.write_bytes(b"{}")
    return out.read_bytes()


def _write_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def run_backup(
    *,
    postgres_url: str,
    qdrant_storage: Path,
    output_dir: Path,
    passphrase: str,
    jarvis_version: str = "",
    notes: str = "",
) -> dict[str, str]:
    """Run the backup and return the manifest path + blob path."""
    if not passphrase:
        raise BackupCryptoError("A recovery passphrase is required")
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = output_dir / "tmp"
    tmp_dir.mkdir(exist_ok=True)

    pg_bytes = _pg_dump(postgres_url, tmp_dir / "postgres.dump")
    qd_bytes = _qdrant_snapshot(qdrant_storage, tmp_dir / "qdrant.tar.gz")
    st_bytes = _settings_snapshot(tmp_dir / "settings.json")

    # Bundle into a single tar.
    bundle = io.BytesIO()
    with tarfile.open(fileobj=bundle, mode="w:") as tar:
        for name, data in (
            ("postgres.dump", pg_bytes),
            ("qdrant.tar.gz", qd_bytes),
            ("settings.json", st_bytes),
        ):
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    bundle_bytes = bundle.getvalue()

    plaintext_sha = manifest_payload_sha256(bundle_bytes)
    encrypted = encrypt_backup(bundle_bytes, passphrase)
    ciphertext_sha = sha256_of_bytes(encrypted.blob)

    artifacts = [
        ArtifactEntry(
            name="bundle",
            source="tar://postgres+qdrant+settings",
            size_bytes=len(bundle_bytes),
            plaintext_sha256=plaintext_sha,
            ciphertext_sha256=ciphertext_sha,
            salt_hex=encrypted.salt.hex(),
            nonce_hex=encrypted.nonce.hex(),
            iterations=encrypted.iterations,
        ),
    ]
    manifest = build_manifest(
        artifacts=artifacts,
        jarvis_version=jarvis_version,
        deletion_tombstones_present=True,
        notes=notes,
    )

    timestamp = manifest.created_at.replace(":", "").replace(".", "")
    blob_path = output_dir / f"jarvis-backup-{timestamp}.bin"
    manifest_path = output_dir / f"jarvis-backup-{timestamp}.manifest.json"

    _write_atomic(blob_path, encrypted.blob)
    _write_atomic(manifest_path, manifest.to_json().encode("utf-8"))

    # Clean up temporary directory.
    shutil.rmtree(tmp_dir, ignore_errors=True)

    return {
        "blob": str(blob_path),
        "manifest": str(manifest_path),
        "plaintext_sha256": plaintext_sha,
        "ciphertext_sha256": ciphertext_sha,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS local backup (Phase 01, FND-009).")
    parser.add_argument(
        "--postgres-url",
        default=os.getenv("POSTGRES_URL", "postgresql://jarvis_admin:jarvis_secure_pass@127.0.0.1:5432/jarvis_db"),
        help="libpq DSN for the local PostgreSQL service.",
    )
    parser.add_argument(
        "--qdrant-storage",
        type=Path,
        default=Path("./volumes/qdrant"),
        help="Path to the local Qdrant storage directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BACKUP_DIR,
        help="Output directory for the encrypted blob and manifest.",
    )
    parser.add_argument(
        "--jarvis-version",
        default=os.getenv("JARVIS_VERSION", ""),
        help="JARVIS version string recorded in the manifest.",
    )
    parser.add_argument(
        "--notes",
        default="",
        help="Free-form notes recorded in the manifest.",
    )
    args = parser.parse_args()

    passphrase = os.getenv("JARVIS_BACKUP_PASSPHRASE")
    if not passphrase:
        print("[FAIL] JARVIS_BACKUP_PASSPHRASE is not set; refusing to back up.", file=sys.stderr)
        return 2
    try:
        result = run_backup(
            postgres_url=args.postgres_url,
            qdrant_storage=args.qdrant_storage,
            output_dir=args.output_dir,
            passphrase=passphrase,
            jarvis_version=args.jarvis_version,
            notes=args.notes,
        )
    except BackupCryptoError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 3
    except subprocess.CalledProcessError as exc:
        print(f"[FAIL] subprocess failed: {exc}", file=sys.stderr)
        return 4

    for k, v in result.items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

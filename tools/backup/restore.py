"""JARVIS restore verification script (Phase 01, FND-009).

Restoration is performed in an isolated target directory. The script:

1. Decrypts the backup blob with the supplied passphrase.
2. Recomputes the SHA-256 of the plaintext and compares it to the
   manifest.
3. Extracts the tar into the target directory.
4. Validates that no extracted path matches the exclusion list
   (``.env``, OS credential-manager contents, Redis data, caches,
   temporary media, secrets).
5. Optionally applies a destructive pre-restore hook
   (e.g. dropping and re-creating the local database) in a way that
   is safe to call from CI.

The script is intentionally side-effect-free by default: it only
extracts into a target directory. Pass ``--apply`` to perform the
destructive database restore step.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tarfile
from pathlib import Path
from typing import Final

from tools.backup.crypto import (
    BackupCryptoError,
    decrypt_backup,
    manifest_payload_sha256,
)
from tools.backup.manifest import EXCLUDED_SOURCES, sha256_of_bytes

import fnmatch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_excluded(path: str) -> bool:
    for pattern in EXCLUDED_SOURCES:
        if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path.lstrip("./"), pattern):
            return True
    return False


def _verify_manifest(manifest_path: Path) -> dict:
    if not manifest_path.exists():
        raise BackupCryptoError(f"Manifest not found: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _verify_excluded(target_dir: Path) -> list[str]:
    """Return a list of paths inside ``target_dir`` that match the exclusion list."""
    bad: list[str] = []
    for path in target_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(target_dir))
        if _is_excluded(rel):
            bad.append(rel)
    return bad


def _restore_postgres(plaintext_path: Path, postgres_url: str) -> None:
    """Apply the PostgreSQL dump in ``plaintext_path`` to ``postgres_url``."""
    import subprocess

    cmd = [
        "pg_restore",
        "--no-owner",
        "--no-privileges",
        "--clean",
        "--if-exists",
        "--dbname",
        postgres_url,
        str(plaintext_path),
    ]
    completed = subprocess.run(cmd, capture_output=True, check=False)
    if completed.returncode != 0:
        raise BackupCryptoError(
            f"pg_restore failed: {completed.stderr.decode('utf-8', errors='ignore')}"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def verify_backup(
    *,
    blob_path: Path,
    manifest_path: Path,
    passphrase: str,
    extract_dir: Path,
) -> dict[str, str]:
    """Decrypt, verify checksums, extract, and validate the exclusion list.

    Returns a summary dict. Raises :class:`BackupCryptoError` on any
    verification failure.
    """
    if not passphrase:
        raise BackupCryptoError("A recovery passphrase is required")
    manifest = _verify_manifest(manifest_path)

    blob = blob_path.read_bytes()
    plaintext = decrypt_backup(blob, passphrase)
    actual_sha = manifest_payload_sha256(plaintext)

    artifact = next(
        (a for a in manifest.get("artifacts", []) if a.get("name") == "bundle"),
        None,
    )
    if not artifact:
        raise BackupCryptoError("Manifest has no 'bundle' artifact entry")

    expected_plaintext = artifact["plaintext_sha256"]
    if actual_sha != expected_plaintext:
        raise BackupCryptoError(
            f"Plaintext SHA-256 mismatch: expected {expected_plaintext}, got {actual_sha}"
        )

    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True)
    with tarfile.open(fileobj=__import__("io").BytesIO(plaintext), mode="r:") as tar:
        # Refuse to extract absolute paths or paths that escape the target.
        for member in tar.getmembers():
            if member.name.startswith("/") or ".." in Path(member.name).parts:
                raise BackupCryptoError(f"Unsafe path in archive: {member.name}")
            if _is_excluded(member.name):
                raise BackupCryptoError(f"Excluded source in archive: {member.name}")
        tar.extractall(path=extract_dir)

    # Double-check the on-disk result.
    bad_paths = _verify_excluded(extract_dir)
    if bad_paths:
        raise BackupCryptoError(
            f"Restore contains excluded source(s): {bad_paths[:3]}"
        )

    return {
        "plaintext_sha256": actual_sha,
        "expected_sha256": expected_plaintext,
        "extract_dir": str(extract_dir),
        "manifest_schema": manifest.get("schema_version", "unknown"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS restore verification (Phase 01, FND-009).")
    parser.add_argument("--blob", type=Path, required=True, help="Path to the encrypted backup blob.")
    parser.add_argument("--manifest", type=Path, required=True, help="Path to the backup manifest.")
    parser.add_argument(
        "--extract-dir",
        type=Path,
        default=Path("./build/restore"),
        help="Isolated directory to extract the backup into.",
    )
    parser.add_argument(
        "--apply-postgres",
        action="store_true",
        help="Apply the PostgreSQL dump to the database in POSTGRES_URL.",
    )
    args = parser.parse_args()

    passphrase = os.getenv("JARVIS_BACKUP_PASSPHRASE")
    if not passphrase:
        print("[FAIL] JARVIS_BACKUP_PASSPHRASE is not set", file=sys.stderr)
        return 2

    try:
        result = verify_backup(
            blob_path=args.blob,
            manifest_path=args.manifest,
            passphrase=passphrase,
            extract_dir=args.extract_dir,
        )
    except BackupCryptoError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 3

    for k, v in result.items():
        print(f"{k}: {v}")

    if args.apply_postgres:
        postgres_url = os.getenv("POSTGRES_URL")
        if not postgres_url:
            print("[FAIL] --apply-postgres requires POSTGRES_URL", file=sys.stderr)
            return 4
        pg_dump_path = args.extract_dir / "postgres.dump"
        if not pg_dump_path.exists():
            print(f"[FAIL] PostgreSQL dump not found at {pg_dump_path}", file=sys.stderr)
            return 5
        try:
            _restore_postgres(pg_dump_path, postgres_url)
            print("postgres_restored: ok")
        except BackupCryptoError as exc:
            print(f"[FAIL] {exc}", file=sys.stderr)
            return 6
    return 0


if __name__ == "__main__":
    sys.exit(main())

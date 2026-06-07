"""Tests for the backup crypto, manifest, and restore verification.

These tests run in-process and require no PostgreSQL, Qdrant, or
NATS services. They prove:

* AES-256-GCM encrypt/decrypt round-trips.
* PBKDF2 parameters are honoured.
* Plaintext SHA-256 in the manifest matches the decrypted payload.
* Tampered ciphertext fails decryption.
* Wrong passphrase fails decryption.
* Restore refuses to extract paths matching the exclusion list.
"""

from __future__ import annotations

import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.backup.crypto import (  # noqa: E402
    BackupCryptoError,
    NONCE_BYTES,
    PBKDF2_ITERATIONS,
    SALT_BYTES,
    decrypt_backup,
    derive_key,
    encrypt_backup,
    manifest_payload_sha256,
)
from tools.backup.manifest import (  # noqa: E402
    EXCLUDED_SOURCES,
    SCHEMA_VERSION,
    ArtifactEntry,
    build_manifest,
    sha256_of_bytes,
)
from tools.backup.restore import (  # noqa: E402
    verify_backup,
)


# ---------------------------------------------------------------------------
# Crypto
# ---------------------------------------------------------------------------


def test_key_derivation_is_deterministic() -> None:
    salt = b"\x00" * SALT_BYTES
    a = derive_key("hunter2", salt=salt, iterations=1000)
    b = derive_key("hunter2", salt=salt, iterations=1000)
    assert a == b
    assert len(a) == 32


def test_key_derivation_changes_with_salt() -> None:
    a = derive_key("hunter2", salt=b"\x00" * SALT_BYTES, iterations=1000)
    b = derive_key("hunter2", salt=b"\x01" * SALT_BYTES, iterations=1000)
    assert a != b


def test_key_derivation_rejects_empty_passphrase() -> None:
    with pytest.raises(BackupCryptoError):
        derive_key("", salt=b"\x00" * SALT_BYTES)


def test_encrypt_decrypt_round_trip() -> None:
    plaintext = b"jarvis local backup round-trip payload"
    encrypted = encrypt_backup(plaintext, "correct horse battery staple")
    decrypted = decrypt_backup(encrypted.blob, "correct horse battery staple")
    assert decrypted == plaintext


def test_encrypt_produces_unique_ciphertext_per_run() -> None:
    plaintext = b"deterministic? no thanks"
    a = encrypt_backup(plaintext, "passphrase")
    b = encrypt_backup(plaintext, "passphrase")
    # Different salt + nonce means different ciphertext.
    assert a.blob != b.blob
    # But both decrypt to the same plaintext.
    assert decrypt_backup(a.blob, "passphrase") == plaintext
    assert decrypt_backup(b.blob, "passphrase") == plaintext


def test_decrypt_with_wrong_passphrase_fails() -> None:
    encrypted = encrypt_backup(b"secret", "right-key")
    with pytest.raises(BackupCryptoError):
        decrypt_backup(encrypted.blob, "wrong-key")


def test_decrypt_rejects_tampered_blob() -> None:
    encrypted = encrypt_backup(b"secret", "right-key")
    tampered = bytearray(encrypted.blob)
    tampered[-1] ^= 0x01
    with pytest.raises(BackupCryptoError):
        decrypt_backup(bytes(tampered), "right-key")


def test_decrypt_rejects_truncated_blob() -> None:
    encrypted = encrypt_backup(b"secret", "right-key")
    with pytest.raises(BackupCryptoError):
        decrypt_backup(encrypted.blob[: len(encrypted.blob) - 5], "right-key")


def test_encrypted_blob_has_documented_header() -> None:
    encrypted = encrypt_backup(b"x", "passphrase")
    # HEADER_MAGIC + version byte + 4 byte iteration count + salt + nonce + body
    assert encrypted.blob[9] == 1
    assert encrypted.salt == encrypted.blob[14 : 14 + SALT_BYTES]
    assert encrypted.nonce == encrypted.blob[14 + SALT_BYTES : 14 + SALT_BYTES + NONCE_BYTES]
    assert encrypted.iterations == PBKDF2_ITERATIONS


def test_manifest_payload_sha256_is_stable() -> None:
    assert manifest_payload_sha256(b"x") == "2d711642b726b04401627ca9fbac32f5" "c8530fb1903cc4db02258717921a4881"  # sha256 hex
    # Just a small smoke: a different payload yields a different hash.
    assert manifest_payload_sha256(b"x") != manifest_payload_sha256(b"y")


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def test_manifest_defaults_lock_values() -> None:
    manifest = build_manifest(artifacts=[])
    assert manifest.schema_version == SCHEMA_VERSION
    assert manifest.kdf == "PBKDF2-HMAC-SHA256"
    assert manifest.encryption == "AES-256-GCM"
    assert manifest.kdf_iterations == PBKDF2_ITERATIONS
    assert manifest.salt_bytes == SALT_BYTES
    assert manifest.nonce_bytes == NONCE_BYTES
    assert manifest.excluded_sources == EXCLUDED_SOURCES
    assert manifest.deletion_tombstones_present is False


def test_manifest_serializes_to_json() -> None:
    manifest = build_manifest(
        artifacts=[
            ArtifactEntry(
                name="bundle",
                source="tar://test",
                size_bytes=10,
                plaintext_sha256="a" * 64,
                ciphertext_sha256="b" * 64,
                salt_hex="c" * 32,
                nonce_hex="d" * 24,
                iterations=PBKDF2_ITERATIONS,
            )
        ],
        jarvis_version="1.2.0",
    )
    blob = manifest.to_json()
    data = json.loads(blob)
    assert data["schema_version"] == SCHEMA_VERSION
    assert data["jarvis_version"] == "1.2.0"
    assert data["artifacts"][0]["name"] == "bundle"
    assert data["deletion_tombstones_present"] is False  # build_manifest default
    assert ".env" in data["excluded_sources"]


def test_excluded_sources_cover_secret_bearing_paths() -> None:
    must = [".env", "secrets", "redis", "tmp", "cache", ".aws", ".ssh"]
    flat = " ".join(EXCLUDED_SOURCES)
    for needle in must:
        assert needle in flat, f"Exclusion list must cover {needle!r}"


# ---------------------------------------------------------------------------
# Restore verification
# ---------------------------------------------------------------------------


def _build_tar_bytes(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _write_backup(
    tmp_path: Path, files: dict[str, bytes], passphrase: str = "key"
) -> tuple[Path, Path]:
    plaintext = _build_tar_bytes(files)
    encrypted = encrypt_backup(plaintext, passphrase)
    artifact = ArtifactEntry(
        name="bundle",
        source="tar://test",
        size_bytes=len(plaintext),
        plaintext_sha256=manifest_payload_sha256(plaintext),
        ciphertext_sha256=sha256_of_bytes(encrypted.blob),
        salt_hex=encrypted.salt.hex(),
        nonce_hex=encrypted.nonce.hex(),
        iterations=encrypted.iterations,
    )
    manifest = build_manifest(artifacts=[artifact], deletion_tombstones_present=True)
    blob_path = tmp_path / "test.bin"
    manifest_path = tmp_path / "test.manifest.json"
    blob_path.write_bytes(encrypted.blob)
    manifest_path.write_text(manifest.to_json(), encoding="utf-8")
    return blob_path, manifest_path


def test_restore_round_trip(tmp_path: Path) -> None:
    files = {
        "postgres.dump": b"pg dump placeholder",
        "qdrant.tar.gz": b"qdrant snapshot placeholder",
        "settings.json": b"{}",
    }
    blob_path, manifest_path = _write_backup(tmp_path, files)
    extract_dir = tmp_path / "out"
    result = verify_backup(
        blob_path=blob_path,
        manifest_path=manifest_path,
        passphrase="key",
        extract_dir=extract_dir,
    )
    assert result["expected_sha256"] == result["plaintext_sha256"]
    assert (extract_dir / "postgres.dump").read_bytes() == files["postgres.dump"]


def test_restore_rejects_wrong_passphrase(tmp_path: Path) -> None:
    blob_path, manifest_path = _write_backup(tmp_path, {"a": b"b"})
    with pytest.raises(BackupCryptoError):
        verify_backup(
            blob_path=blob_path,
            manifest_path=manifest_path,
            passphrase="wrong",
            extract_dir=tmp_path / "out",
        )


def test_restore_rejects_missing_manifest(tmp_path: Path) -> None:
    blob_path, _ = _write_backup(tmp_path, {"a": b"b"})
    with pytest.raises(BackupCryptoError):
        verify_backup(
            blob_path=blob_path,
            manifest_path=tmp_path / "missing.json",
            passphrase="key",
            extract_dir=tmp_path / "out",
        )


def test_restore_rejects_excluded_source(tmp_path: Path) -> None:
    # The archive contains a .env file; the verifier must refuse it.
    files = {".env": b"API_KEY=leak", "postgres.dump": b"ok"}
    blob_path, manifest_path = _write_backup(tmp_path, files)
    with pytest.raises(BackupCryptoError) as exc:
        verify_backup(
            blob_path=blob_path,
            manifest_path=manifest_path,
            passphrase="key",
            extract_dir=tmp_path / "out",
        )
    assert "Excluded" in str(exc.value)


def test_restore_rejects_unsafe_path(tmp_path: Path) -> None:
    # Manually craft a tar with an absolute path.
    plaintext_buf = io.BytesIO()
    with tarfile.open(fileobj=plaintext_buf, mode="w") as tar:
        info = tarfile.TarInfo(name="/etc/passwd")
        info.size = 4
        tar.addfile(info, io.BytesIO(b"leak"))
    plaintext = plaintext_buf.getvalue()
    encrypted = encrypt_backup(plaintext, "key")
    artifact = ArtifactEntry(
        name="bundle",
        source="tar://test",
        size_bytes=len(plaintext),
        plaintext_sha256=manifest_payload_sha256(plaintext),
        ciphertext_sha256=sha256_of_bytes(encrypted.blob),
        salt_hex=encrypted.salt.hex(),
        nonce_hex=encrypted.nonce.hex(),
        iterations=encrypted.iterations,
    )
    manifest = build_manifest(artifacts=[artifact])
    blob_path = tmp_path / "t.bin"
    manifest_path = tmp_path / "t.manifest.json"
    blob_path.write_bytes(encrypted.blob)
    manifest_path.write_text(manifest.to_json(), encoding="utf-8")
    with pytest.raises(BackupCryptoError) as exc:
        verify_backup(
            blob_path=blob_path,
            manifest_path=manifest_path,
            passphrase="key",
            extract_dir=tmp_path / "out",
        )
    assert "Unsafe" in str(exc.value) or "Excluded" in str(exc.value)

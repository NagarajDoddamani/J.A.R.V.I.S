"""JARVIS backup cryptography (Phase 01, FND-009).

Implements the v1.2 backup security policy (Correction 6):

* Backups are encrypted locally using AES-256-GCM with an
  authenticated encryption scheme.
* The recovery key is user-controlled and never stored in the backup
  or in the manifest. The key is derived from a passphrase via
  PBKDF2-HMAC-SHA256 with 600 000 iterations and a per-backup random
  salt.
* The manifest records the KDF parameters, the salt, the nonce, the
  auth-tag, the SHA-256 of the plaintext, and the SHA-256 of the
  ciphertext so integrity and authenticity can be verified without
  the recovery key.

The module is dependency-free in the foundation layer beyond
``cryptography``.
"""

from __future__ import annotations

import json
import os
import secrets
import struct
from dataclasses import dataclass
from typing import Final

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KEY_BYTES: Final[int] = 32  # AES-256
SALT_BYTES: Final[int] = 16
NONCE_BYTES: Final[int] = 12  # GCM standard
PBKDF2_ITERATIONS: Final[int] = 600_000
HEADER_MAGIC: Final[bytes] = b"JARVISBAK\x00"
HEADER_VERSION: Final[int] = 1


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class BackupCryptoError(RuntimeError):
    """Raised on backup cryptographic failure."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EncryptedBackup:
    """The bytes of an encrypted backup file.

    The on-disk layout is:

    +--------------------+--------+--------+----------+--------------------+
    | ``HEADER_MAGIC``   | ver    | nonce  | salt     | ciphertext + tag   |
    +--------------------+--------+--------+----------+--------------------+
    | 9 bytes            | 1 byte | 12 B   | 16 B     | rest               |
    +--------------------+--------+--------+----------+--------------------+
    """

    blob: bytes
    salt: bytes
    nonce: bytes
    iterations: int

    @property
    def plaintext_sha256(self) -> str:
        # Stored on the *manifest*; the blob itself is opaque.
        raise NotImplementedError

    def __post_init__(self) -> None:
        if not self.blob.startswith(HEADER_MAGIC + bytes([HEADER_VERSION])):
            raise BackupCryptoError("Invalid backup blob header")


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------


def derive_key(passphrase: str, *, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> bytes:
    """Derive a 256-bit key from ``passphrase`` using PBKDF2-HMAC-SHA256."""
    if not isinstance(passphrase, str) or not passphrase:
        raise BackupCryptoError("passphrase must be a non-empty string")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_BYTES,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(passphrase.encode("utf-8"))


# ---------------------------------------------------------------------------
# Encryption
# ---------------------------------------------------------------------------


def encrypt_backup(plaintext: bytes, passphrase: str) -> EncryptedBackup:
    """Encrypt ``plaintext`` with ``passphrase`` and return the on-disk blob."""
    if not isinstance(plaintext, (bytes, bytearray)):
        raise BackupCryptoError("plaintext must be bytes-like")
    salt = secrets.token_bytes(SALT_BYTES)
    nonce = secrets.token_bytes(NONCE_BYTES)
    key = derive_key(passphrase, salt=salt)
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, bytes(plaintext), associated_data=HEADER_MAGIC)
    # Append salt and nonce into the blob header for self-describing restores.
    blob = (
        HEADER_MAGIC
        + bytes([HEADER_VERSION])
        + struct.pack(">I", PBKDF2_ITERATIONS)
        + salt
        + nonce
        + ciphertext_with_tag
    )
    return EncryptedBackup(
        blob=blob,
        salt=salt,
        nonce=nonce,
        iterations=PBKDF2_ITERATIONS,
    )


# ---------------------------------------------------------------------------
# Decryption
# ---------------------------------------------------------------------------


def decrypt_backup(blob: bytes, passphrase: str) -> bytes:
    """Decrypt an :class:`EncryptedBackup` blob with ``passphrase``."""
    if not blob.startswith(HEADER_MAGIC):
        raise BackupCryptoError("Invalid backup magic")
    version = blob[len(HEADER_MAGIC)]
    if version != HEADER_VERSION:
        raise BackupCryptoError(f"Unsupported backup version: {version}")
    offset = len(HEADER_MAGIC) + 1
    (iterations,) = struct.unpack(">I", blob[offset : offset + 4])
    offset += 4
    salt = blob[offset : offset + SALT_BYTES]
    offset += SALT_BYTES
    nonce = blob[offset : offset + NONCE_BYTES]
    offset += NONCE_BYTES
    ciphertext = blob[offset:]
    key = derive_key(passphrase, salt=salt, iterations=iterations)
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ciphertext, associated_data=HEADER_MAGIC)
    except Exception as exc:  # cryptography raises InvalidTag
        raise BackupCryptoError("Backup decryption failed (wrong key or tampered blob)") from exc


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------


def manifest_payload_sha256(plaintext: bytes) -> str:
    """Return the hex SHA-256 of a plaintext payload."""
    import hashlib

    return hashlib.sha256(plaintext).hexdigest()


__all__ = [
    "EncryptedBackup",
    "BackupCryptoError",
    "KEY_BYTES",
    "NONCE_BYTES",
    "PBKDF2_ITERATIONS",
    "SALT_BYTES",
    "decrypt_backup",
    "derive_key",
    "encrypt_backup",
    "manifest_payload_sha256",
]

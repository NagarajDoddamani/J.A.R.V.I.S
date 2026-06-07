"""JARVIS Payload Policy (JDOS v1.2, Correction 5).

This module is the single source of truth for what may and may not
appear in a durable JARVIS payload. It is consumed by:

* The FastAPI gateway middleware (``backend.core.middleware.payload_enforcement``)
  to reject HTTP request bodies whose JSON contains sensitive keys.
* The NATS runtime manager (``backend.core.nats``) to reject durable
  publishes that violate the policy.
* The test suite (``tests.test_payload_enforcement``) to prove the
  policy rejects prompts, raw memory, documents, embeddings, and
  secrets.

The policy is intentionally narrow and locked. Extending the
SENSITIVE_KEYS set or the size boundary is a contract change and
requires an ADR.
"""

from __future__ import annotations

from typing import Any, Final, Iterable

# ---------------------------------------------------------------------------
# Sensitive keys (Correction 5)
# ---------------------------------------------------------------------------

#: Top-level keys that MUST NOT appear in a durable JARVIS payload.
#: Matching is case-insensitive and recursive. The list is the
#: authoritative baseline; extending it requires an ADR.
SENSITIVE_KEYS: Final[frozenset[str]] = frozenset(
    {
        # Prompts and transcripts
        "raw_memory",
        "memory_content",
        "raw_research",
        "research_content",
        "raw_prompt",
        "full_prompt",
        "prompt",
        "transcript",
        "user_content",
        # Research and knowledge
        "query_text",
        "document_body",
        "chunk_body",
        "document_text",
        "research_result",
        # Memory content and embeddings
        "memory_text",
        "embedding",
        "embedding_vector",
        "vector",
        # Raw media
        "raw_audio",
        "raw_image",
        "raw_screenshot",
        "raw_video",
        "raw_frame",
        # Credentials and secrets
        "api_key",
        "secret",
        "token",
        "password",
        "private_key",
        "session_token",
        "access_token",
        "refresh_token",
    }
)

#: HTTP content types whose bodies are scanned. Streaming and binary
#: content types are excluded by design.
SCANNED_CONTENT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "application/json",
        "application/json+jarvis",
        "application/vnd.api+json",
    }
)

#: Hard upper bound on a JSON body that the gateway will scan. Bodies
#: larger than this short-circuit the scan and are rejected; this
#: protects the process from memory-pressure attacks. The value is
#: aligned with the NATS governance boundary (256 KiB) and acts as a
#: defence-in-depth check.
MAX_SCANNED_BODY_BYTES: Final[int] = 256 * 1024


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class PayloadPolicyError(ValueError):
    """Raised when a payload violates the JARVIS payload policy."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
        }


# ---------------------------------------------------------------------------
# Core scan
# ---------------------------------------------------------------------------


def _walk(value: Any, *, _seen: set[int]) -> Iterable[tuple[Any, str]]:
    """Yield ``(parent, key)`` pairs for every dict key in the payload.

    The pair is used by the caller to report the offending location
    without re-traversing the structure.
    """
    if id(value) in _seen:
        return
    _seen.add(id(value))
    if isinstance(value, dict):
        for key, child in value.items():
            yield value, key
            yield from _walk(child, _seen=_seen)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child, _seen=_seen)


def _find_sensitive_keys(payload: Any) -> list[str]:
    """Return the dotted path of every sensitive key in ``payload``."""
    if not isinstance(payload, (dict, list)):
        return []
    paths: list[str] = []
    # Manual traversal so we can capture the dotted path.
    def _recurse(node: Any, prefix: str, seen: set[int]) -> None:
        if id(node) in seen:
            return
        seen.add(id(node))
        if isinstance(node, dict):
            for key, value in node.items():
                if not isinstance(key, str):
                    raise PayloadPolicyError(
                        "INVALID_KEY_TYPE",
                        "Payload keys must be strings",
                    )
                path = f"{prefix}.{key}" if prefix else key
                if key.lower() in SENSITIVE_KEYS:
                    paths.append(path)
                if isinstance(value, (dict, list)):
                    _recurse(value, path, seen)
        elif isinstance(node, list):
            for index, value in enumerate(node):
                path = f"{prefix}[{index}]"
                if isinstance(value, (dict, list)):
                    _recurse(value, path, seen)

    _recurse(payload, "", set())
    return paths


def scan_dict(payload: Any) -> list[str]:
    """Return the dotted paths of every sensitive key in ``payload``.

    A non-dict / non-list payload returns an empty list (nothing to
    scan). Structural errors raise :class:`PayloadPolicyError`.
    """
    return _find_sensitive_keys(payload)


def assert_clean(payload: Any) -> None:
    """Raise :class:`PayloadPolicyError` if ``payload`` is not clean.

    A clean payload is a ``dict`` or ``list`` whose recursive contents
    do not contain any key in :data:`SENSITIVE_KEYS` (case-insensitive).
    """
    if payload is None:
        return
    if not isinstance(payload, (dict, list)):
        raise PayloadPolicyError(
            "INVALID_PAYLOAD",
            "Payload must be a JSON object or array",
        )
    bad = _find_sensitive_keys(payload)
    if bad:
        # Report the first 5 paths to keep error messages compact.
        sample = ", ".join(bad[:5])
        raise PayloadPolicyError(
            "SENSITIVE_KEY_DETECTED",
            f"Payload contains restricted key(s): {sample}",
        )


def assert_clean_bytes(body: bytes, *, content_type: str | None) -> None:
    """Scan a raw HTTP body. Returns silently on success; raises on violation.

    A non-JSON body short-circuits the scan; the caller is expected to
    pass bodies for the scanned content types only.
    """
    if not body:
        return
    if len(body) > MAX_SCANNED_BODY_BYTES:
        raise PayloadPolicyError(
            "BODY_TOO_LARGE",
            f"Request body exceeds {MAX_SCANNED_BODY_BYTES} byte limit "
            f"(received {len(body)} bytes)",
        )
    if content_type is None:
        return
    base_type = content_type.split(";")[0].strip().lower()
    if base_type not in SCANNED_CONTENT_TYPES:
        return
    import json

    try:
        decoded = json.loads(body)
    except json.JSONDecodeError as exc:
        raise PayloadPolicyError(
            "INVALID_JSON",
            f"Body is not valid JSON: {exc.msg}",
        ) from exc
    assert_clean(decoded)


__all__ = [
    "MAX_SCANNED_BODY_BYTES",
    "PayloadPolicyError",
    "SCANNED_CONTENT_TYPES",
    "SENSITIVE_KEYS",
    "assert_clean",
    "assert_clean_bytes",
    "scan_dict",
]

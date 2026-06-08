from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime


def _canonical_json(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)


def _isoformat(dt: datetime) -> str:
    return dt.isoformat()


def compute_entry_hash(
    *,
    chain_name: str,
    actor_type: str,
    actor_id: str | None,
    action: str,
    target_type: str | None,
    target_ref: str | None,
    policy_decision: str,
    classification: str,
    correlation_id: str,
    causation_id: str | None,
    result: str,
    redacted_reason: str | None,
    occurred_at: datetime,
    entry_index: int,
) -> bytes:
    """Compute the SHA-256 hash of an audit entry's content fields.

    The ``entry_hash`` is computed from all content fields *except*
    ``previous_hash`` and ``entry_hash`` itself, using canonical
    JSON serialization (sorted keys, ASCII-safe). This ensures
    the hash is deterministic regardless of field order.
    """
    content: dict[str, object] = {
        "chain_name": chain_name,
        "actor_type": actor_type,
        "actor_id": actor_id,
        "action": action,
        "target_type": target_type,
        "target_ref": target_ref,
        "policy_decision": policy_decision,
        "classification": classification,
        "correlation_id": correlation_id,
        "causation_id": causation_id,
        "result": result,
        "redacted_reason": redacted_reason,
        "occurred_at": _isoformat(occurred_at),
        "entry_index": entry_index,
    }
    canonical = _canonical_json(content)
    return hashlib.sha256(canonical.encode("utf-8")).digest()


def verify_chain_link(
    *,
    previous_hash: bytes | None,
    previous_entry_hash: bytes | None,
) -> bool:
    """Verify that ``previous_hash`` matches ``previous_entry_hash``.

    For the first entry in a chain (no predecessor), both
    ``previous_hash`` and ``previous_entry_hash`` must be ``None``.
    For subsequent entries, ``previous_hash`` must equal the
    preceding entry's ``entry_hash``.
    """
    if previous_hash is None and previous_entry_hash is None:
        return True
    if previous_hash is None or previous_entry_hash is None:
        return False
    return previous_hash == previous_entry_hash


@dataclass(frozen=True)
class ChainLink:
    """Result of linking a new entry into a chain."""
    is_first: bool
    previous_hash: bytes | None
    entry_hash: bytes
    entry_index: int

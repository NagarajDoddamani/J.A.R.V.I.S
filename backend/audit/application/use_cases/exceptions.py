from __future__ import annotations


class UseCaseError(Exception):
    """Base exception for all use-case-level errors."""


class AuditEntryNotFoundError(UseCaseError):
    def __init__(self, entry_id: str) -> None:
        super().__init__(f"Audit entry not found: {entry_id}")
        self.entry_id = entry_id


class ChainNotFoundError(UseCaseError):
    def __init__(self, chain_name: str) -> None:
        super().__init__(f"Audit chain not found: {chain_name}")
        self.chain_name = chain_name

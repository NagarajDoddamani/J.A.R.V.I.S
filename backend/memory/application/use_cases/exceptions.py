from __future__ import annotations


class UseCaseError(Exception):
    """Base exception for all use-case-level errors."""


class MemoryNotFoundError(UseCaseError):
    def __init__(self, memory_id: str) -> None:
        super().__init__(f"Memory not found: {memory_id}")
        self.memory_id = memory_id


class ConsentNotFoundError(UseCaseError):
    def __init__(self, consent_id: str) -> None:
        super().__init__(f"Consent not found: {consent_id}")
        self.consent_id = consent_id


class ConsentNotActiveError(UseCaseError):
    def __init__(self, consent_id: str) -> None:
        super().__init__(f"Consent is not active: {consent_id}")
        self.consent_id = consent_id


class MemoryDeletedError(UseCaseError):
    def __init__(self, memory_id: str) -> None:
        super().__init__(f"Memory is already deleted: {memory_id}")
        self.memory_id = memory_id

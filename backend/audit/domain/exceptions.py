from __future__ import annotations


class AuditDomainError(Exception):
    """Base exception for all audit domain errors."""


class AuditEntryError(AuditDomainError):
    """Base exception for audit entry validation errors."""


class InvalidChainNameError(AuditEntryError):
    def __init__(self, chain_name: str) -> None:
        super().__init__(f"Invalid chain name: {chain_name!r}")


class InvalidActorRefError(AuditEntryError):
    def __init__(self, actor_type: str, actor_id: str | None) -> None:
        super().__init__(f"Invalid actor ref: type={actor_type!r}, id={actor_id!r}")


class InvalidActionError(AuditEntryError):
    def __init__(self, action: str) -> None:
        super().__init__(f"Invalid action: {action!r}")


class InvalidPolicyDecisionError(AuditEntryError):
    def __init__(self, decision: str) -> None:
        super().__init__(f"Invalid policy decision: {decision!r}")


class InvalidClassificationError(AuditEntryError):
    def __init__(self, classification: str) -> None:
        super().__init__(f"Invalid classification: {classification!r}")


class InvalidCorrelationIdError(AuditEntryError):
    def __init__(self) -> None:
        super().__init__("Correlation ID must not be empty")


class InvalidResultError(AuditEntryError):
    def __init__(self, result: str) -> None:
        super().__init__(f"Invalid result: {result!r}")


class InvalidEntryIndexError(AuditEntryError):
    def __init__(self, index: int, expected: int) -> None:
        super().__init__(f"Entry index {index} does not match expected {expected}")


class InvalidEntryHashError(AuditEntryError):
    def __init__(self) -> None:
        super().__init__("Entry hash does not match computed content hash")


class RestrictedClassificationRequiresReason(AuditEntryError):
    def __init__(self) -> None:
        super().__init__("Restricted classification requires a non-empty redacted_reason")


class SensitiveContentInAuditEntry(AuditEntryError):
    def __init__(self, field: str, value: str) -> None:
        snippet = value[:80] if len(value) > 80 else value
        super().__init__(f"Sensitive content detected in field {field!r}: {snippet!r}")


class InvalidLifecycleTransitionError(AuditDomainError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Cannot transition from {current!r} to {target!r}")

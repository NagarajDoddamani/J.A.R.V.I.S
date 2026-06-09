from __future__ import annotations


class MemoryDomainError(Exception):
    """Base exception for all memory domain errors."""


class EmptyContentError(MemoryDomainError):
    def __init__(self) -> None:
        super().__init__("Memory content must not be empty")


class ContentTooLongError(MemoryDomainError):
    def __init__(self, length: int, max_length: int) -> None:
        super().__init__(
            f"Memory content length {length} exceeds maximum {max_length}"
        )
        self.length = length
        self.max_length = max_length


class SecretDetectedError(MemoryDomainError):
    def __init__(self, field: str) -> None:
        super().__init__(f"Memory content must not contain secrets: {field}")
        self.field = field


class ConsentNotActiveError(MemoryDomainError):
    def __init__(self, status: str) -> None:
        super().__init__(
            f"Consent must be ACTIVE before memory creation, got {status!r}"
        )
        self.status = status


class RetentionRequiredError(MemoryDomainError):
    def __init__(self) -> None:
        super().__init__("Retention policy is required")


class RevisionMonotonicityError(MemoryDomainError):
    def __init__(self, current: int, expected: int) -> None:
        super().__init__(
            f"Revision {current} does not follow expected {expected}"
        )
        self.current = current
        self.expected = expected


class DeletedMemoryUpdateError(MemoryDomainError):
    def __init__(self) -> None:
        super().__init__("Deleted memories cannot be updated")


class RevokedConsentBlocksUpdateError(MemoryDomainError):
    def __init__(self) -> None:
        super().__init__("Revoked consent blocks memory updates")


class ProvenanceRequiredError(MemoryDomainError):
    def __init__(self) -> None:
        super().__init__("Provenance is required")


class SourceRequiredError(MemoryDomainError):
    def __init__(self) -> None:
        super().__init__("Source is required")


class InvalidClassificationError(MemoryDomainError):
    def __init__(self, classification: str) -> None:
        super().__init__(f"Invalid classification: {classification!r}")
        self.classification = classification


class PurgedConsentError(MemoryDomainError):
    def __init__(self) -> None:
        super().__init__("Purged consent cannot be reactivated")


class ExpirationBeforeGrantError(MemoryDomainError):
    def __init__(self) -> None:
        super().__init__("Expiration cannot precede grant date")


class InvalidConsentTransitionError(MemoryDomainError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            f"Invalid consent transition from {current!r} to {target!r}"
        )
        self.current = current
        self.target = target


class InvalidProvenanceError(MemoryDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid provenance: {reason}")


class InvalidRetentionPolicyError(MemoryDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid retention policy: {reason}")


class InvalidSensitivityError(MemoryDomainError):
    def __init__(self, sensitivity: str) -> None:
        super().__init__(f"Invalid sensitivity: {sensitivity!r}")
        self.sensitivity = sensitivity


class SensitiveMemoryRequiresConsentError(MemoryDomainError):
    def __init__(self) -> None:
        super().__init__("Sensitive memories require active consent")


class RestrictedMemoryRequiresRedactionError(MemoryDomainError):
    def __init__(self) -> None:
        super().__init__("Restricted memories require redaction metadata")


class PurgedMemoryImmutableError(MemoryDomainError):
    def __init__(self) -> None:
        super().__init__("Purged memories are immutable forever")


class RetentionExpirationError(MemoryDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Retention expiration error: {reason}")


class ProvenanceMismatchError(MemoryDomainError):
    def __init__(self) -> None:
        super().__init__("Source provenance must survive all revisions")


class EventPayloadTooDetailedError(MemoryDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Event payload violates governance: {reason}")

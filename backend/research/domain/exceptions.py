from __future__ import annotations


class ResearchDomainError(Exception):
    """Base exception for all research domain errors."""


class InvalidQueryError(ResearchDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid query: {reason}")


class InvalidGoalError(ResearchDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid research goal: {reason}")


class InvalidSourceReferenceError(ResearchDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid source reference: {reason}")


class InvalidConfidenceScoreError(ResearchDomainError):
    def __init__(self, score: float) -> None:
        super().__init__(f"Invalid confidence score: {score!r}")
        self.score = score


class InvalidSummaryError(ResearchDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid research summary: {reason}")


class InvalidFailureReasonError(ResearchDomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid failure reason: {reason}")


class ResearchImmutableError(ResearchDomainError):
    def __init__(self, status: str) -> None:
        super().__init__(f"Research is in terminal state {status!r} and cannot be modified")
        self.status = status


class InvalidSourceTypeError(ResearchDomainError):
    def __init__(self, source_type: str) -> None:
        super().__init__(f"Invalid source type: {source_type!r}")
        self.source_type = source_type


class InvalidPriorityError(ResearchDomainError):
    def __init__(self, priority: str) -> None:
        super().__init__(f"Invalid research priority: {priority!r}")
        self.priority = priority


class InvalidTransitionError(ResearchDomainError):
    def __init__(self, entity: str, current: str, target: str) -> None:
        super().__init__(
            f"Invalid {entity} transition from {current!r} to {target!r}"
        )
        self.entity = entity
        self.current = current
        self.target = target


class NoJobsError(ResearchDomainError):
    def __init__(self) -> None:
        super().__init__("Research request must have at least one job before COMPLETED")


class DuplicateSourceReferenceError(ResearchDomainError):
    def __init__(self) -> None:
        super().__init__("Duplicate source references not allowed within a job")


class MissingConfidenceScoreError(ResearchDomainError):
    def __init__(self) -> None:
        super().__init__("Confidence score is required for every source")


class IncompleteJobsError(ResearchDomainError):
    def __init__(self) -> None:
        super().__init__("All jobs must be COMPLETED before research request can complete")


class CancelledJobRestartError(ResearchDomainError):
    def __init__(self) -> None:
        super().__init__("CANCELLED jobs cannot restart")


class QueryTooLongError(ResearchDomainError):
    def __init__(self, length: int, max_length: int) -> None:
        super().__init__(f"Query length {length} exceeds maximum {max_length}")


class SummaryTooLongError(ResearchDomainError):
    def __init__(self, length: int, max_length: int) -> None:
        super().__init__(f"Summary length {length} exceeds maximum {max_length}")

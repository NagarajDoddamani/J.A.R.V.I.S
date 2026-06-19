from __future__ import annotations


class UseCaseError(Exception):
    """Base exception for all use-case-level errors."""


class ResearchRequestNotFoundError(UseCaseError):
    def __init__(self, request_id: str) -> None:
        super().__init__(f"Research request not found: {request_id}")
        self.request_id = request_id


class ResearchJobNotFoundError(UseCaseError):
    def __init__(self, job_id: str) -> None:
        super().__init__(f"Research job not found: {job_id}")
        self.job_id = job_id

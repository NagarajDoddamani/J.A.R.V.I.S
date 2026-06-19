from __future__ import annotations

from typing import Protocol, Union

from backend.research.application.persistence.dto import (
    ResearchJobStorageDTO,
    ResearchOutboxStorageDTO,
    ResearchRequestStorageDTO,
    ResearchSourceStorageDTO,
)
from backend.research.domain.model import (
    ResearchCancelled,
    ResearchCompleted,
    ResearchFailed,
    ResearchJob,
    ResearchRequest,
    ResearchRequested,
    ResearchSource,
    ResearchStarted,
    ResearchSummaryGenerated,
    SourceAdded,
)


ResearchOutboxDomainEvent = Union[
    ResearchRequested,
    ResearchStarted,
    ResearchCompleted,
    ResearchFailed,
    ResearchCancelled,
    SourceAdded,
    ResearchSummaryGenerated,
]


class ResearchRequestMapper(Protocol):
    def domain_to_dto(
        self, request: ResearchRequest
    ) -> ResearchRequestStorageDTO:
        ...

    def dto_to_domain(
        self, dto: ResearchRequestStorageDTO
    ) -> ResearchRequest:
        ...


class ResearchJobMapper(Protocol):
    def domain_to_dto(self, job: ResearchJob) -> ResearchJobStorageDTO:
        ...

    def dto_to_domain(self, dto: ResearchJobStorageDTO) -> ResearchJob:
        ...


class ResearchSourceMapper(Protocol):
    def domain_to_dto(
        self, source: ResearchSource
    ) -> ResearchSourceStorageDTO:
        ...

    def dto_to_domain(
        self, dto: ResearchSourceStorageDTO
    ) -> ResearchSource:
        ...


class ResearchOutboxMapper(Protocol):
    def event_to_dto(
        self, event: ResearchOutboxDomainEvent
    ) -> ResearchOutboxStorageDTO:
        ...

    def dto_to_event(
        self, dto: ResearchOutboxStorageDTO
    ) -> ResearchOutboxDomainEvent:
        ...

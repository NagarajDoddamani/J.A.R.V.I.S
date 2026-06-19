from __future__ import annotations

from typing import Protocol
from uuid import UUID

from backend.research.domain.model import (
    ResearchJob,
    ResearchJobId,
    ResearchPriority,
    ResearchRequest,
    ResearchRequestId,
    ResearchSource,
    ResearchStatus,
    SourceType,
)


class ResearchRequestRepositoryPort(Protocol):
    """Repository port for ``ResearchRequest`` aggregate persistence.

    An implementation persists ``ResearchRequest`` aggregates to a
    concrete store. Requests are queryable by status and priority.
    All methods are synchronous.
    """

    def save(self, request: ResearchRequest) -> None:
        """Persist a new or updated research request.

        Uses upsert semantics — if a request with the same
        ``request_id`` already exists it is replaced; otherwise a
        new record is created.

        Parameters
        ----------
        request:
            The ``ResearchRequest`` aggregate to persist.
        """
        ...

    def find_by_id(self, request_id: ResearchRequestId) -> ResearchRequest | None:
        """Retrieve a single research request by its unique identifier.

        Parameters
        ----------
        request_id:
            The ``ResearchRequestId`` to look up.

        Returns
        -------
        The matching request, or ``None`` if no request exists with
        the given identifier.
        """
        ...

    def find_by_status(self, status: ResearchStatus) -> list[ResearchRequest]:
        """Retrieve all research requests with a given status.

        Parameters
        ----------
        status:
            The ``ResearchStatus`` to filter by.

        Returns
        -------
        A list of ``ResearchRequest`` instances with the given
        status.
        """
        ...

    def find_by_priority(self, priority: ResearchPriority) -> list[ResearchRequest]:
        """Retrieve all research requests with a given priority.

        Parameters
        ----------
        priority:
            The ``ResearchPriority`` to filter by.

        Returns
        -------
        A list of ``ResearchRequest`` instances with the given
        priority.
        """
        ...

    def count(self) -> int:
        """Return the total number of research requests.

        This count includes all statuses.

        Returns
        -------
        Total request count (0 if the store is empty).
        """
        ...


class ResearchJobRepositoryPort(Protocol):
    """Repository port for ``ResearchJob`` persistence.

    An implementation persists ``ResearchJob`` aggregates to a
    concrete store. Jobs are queryable by status and parent request.
    All methods are synchronous.
    """

    def save(self, job: ResearchJob) -> None:
        """Persist a new or updated research job.

        Uses upsert semantics — if a job with the same ``job_id``
        already exists it is replaced; otherwise a new record is
        created.

        Parameters
        ----------
        job:
            The ``ResearchJob`` aggregate to persist.
        """
        ...

    def find_by_id(self, job_id: ResearchJobId) -> ResearchJob | None:
        """Retrieve a single research job by its unique identifier.

        Parameters
        ----------
        job_id:
            The ``ResearchJobId`` to look up.

        Returns
        -------
        The matching job, or ``None`` if no job exists with the
        given identifier.
        """
        ...

    def find_by_status(self, status: ResearchStatus) -> list[ResearchJob]:
        """Retrieve all research jobs with a given status.

        Parameters
        ----------
        status:
            The ``ResearchStatus`` to filter by.

        Returns
        -------
        A list of ``ResearchJob`` instances with the given status.
        """
        ...

    def find_by_request_id(
        self, request_id: ResearchRequestId
    ) -> list[ResearchJob]:
        """Retrieve all research jobs belonging to a request.

        Parameters
        ----------
        request_id:
            The ``ResearchRequestId`` to search for.

        Returns
        -------
        A list of ``ResearchJob`` instances for the given request.
        """
        ...

    def count(self) -> int:
        """Return the total number of research jobs.

        Returns
        -------
        Total job count (0 if the store is empty).
        """
        ...


class ResearchSourceRepositoryPort(Protocol):
    """Repository port for ``ResearchSource`` persistence.

    An implementation persists ``ResearchSource`` value objects to a
    concrete store. Sources are queryable by type and parent job.
    All methods are synchronous.
    """

    def save(self, source: ResearchSource) -> None:
        """Persist a new or updated research source.

        Uses upsert semantics — if a source with the same
        ``source_id`` already exists it is replaced; otherwise a new
        record is created.

        Parameters
        ----------
        source:
            The ``ResearchSource`` to persist.
        """
        ...

    def find_by_id(self, source_id: UUID) -> ResearchSource | None:
        """Retrieve a single research source by its unique identifier.

        Parameters
        ----------
        source_id:
            The ``UUID`` to look up.

        Returns
        -------
        The matching source, or ``None`` if no source exists with
        the given identifier.
        """
        ...

    def find_by_type(self, source_type: SourceType) -> list[ResearchSource]:
        """Retrieve all research sources with a given type.

        Parameters
        ----------
        source_type:
            The ``SourceType`` to filter by.

        Returns
        -------
        A list of ``ResearchSource`` instances with the given type.
        """
        ...

    def find_by_job_id(self, job_id: ResearchJobId) -> list[ResearchSource]:
        """Retrieve all research sources belonging to a job.

        Parameters
        ----------
        job_id:
            The ``ResearchJobId`` to search for.

        Returns
        -------
        A list of ``ResearchSource`` instances for the given job.
        """
        ...

    def count(self) -> int:
        """Return the total number of research sources.

        Returns
        -------
        Total source count (0 if the store is empty).
        """
        ...

from __future__ import annotations

from typing import Protocol

from backend.memory.domain.model import (
    ConsentId,
    ConsentRecord,
    Memory,
    MemoryCategory,
    MemoryId,
)


class MemoryRepositoryPort(Protocol):
    """Repository port for ``Memory`` aggregate persistence.

    An implementation persists ``Memory`` aggregates to a concrete
    store. Soft-deleted memories remain queryable via ``find_deleted``.
    All methods are synchronous; adapters requiring async should use
    ``asyncio.to_thread`` or wrap in an async adapter class.
    """

    def save(self, memory: Memory) -> None:
        """Persist a new or updated memory.

        Implementations should use upsert semantics — if a memory
        with the same ``memory_id`` already exists it is replaced;
        otherwise a new record is created.

        Parameters
        ----------
        memory:
            The ``Memory`` aggregate to persist.
        """
        ...

    def find_by_id(self, memory_id: MemoryId) -> Memory | None:
        """Retrieve a single memory by its unique identifier.

        Parameters
        ----------
        memory_id:
            The ``MemoryId`` to look up.

        Returns
        -------
        The matching memory, or ``None`` if no memory exists
        with the given identifier.
        """
        ...

    def find_by_consent_id(self, consent_id: ConsentId) -> list[Memory]:
        """Retrieve all memories associated with a consent record.

        Parameters
        ----------
        consent_id:
            The ``ConsentId`` to search for.

        Returns
        -------
        A list of ``Memory`` instances sharing the given consent ID.
        """
        ...

    def find_by_category(self, category: MemoryCategory) -> list[Memory]:
        """Retrieve memories filtered by category.

        Parameters
        ----------
        category:
            The ``MemoryCategory`` to filter by.

        Returns
        -------
        A list of ``Memory`` instances in the given category.
        """
        ...

    def find_by_source(
        self, source_type: str, source_id: str | None
    ) -> list[Memory]:
        """Retrieve memories matching a source type and optional source ID.

        When ``source_id`` is ``None``, all memories for the given
        ``source_type`` are returned.

        Parameters
        ----------
        source_type:
            The source type string (e.g. ``"user_input"``).
        source_id:
            The source instance identifier, or ``None`` to match
            all memories for the given source type.

        Returns
        -------
        A list of ``Memory`` instances matching the source criteria.
        """
        ...

    def find_deleted(self) -> list[Memory]:
        """Retrieve all soft-deleted memories.

        Deleted memories are not physically removed from the store
        and remain queryable through this method.

        Returns
        -------
        A list of ``Memory`` instances in the ``DELETED`` state.
        """
        ...

    def count(self) -> int:
        """Return the total number of memories in the store.

        This count includes both active and soft-deleted memories.

        Returns
        -------
        Total memory count (0 if the store is empty).
        """
        ...


class ConsentRepositoryPort(Protocol):
    """Repository port for ``ConsentRecord`` persistence.

    An implementation persists ``ConsentRecord`` aggregates to a
    concrete store. Queries for active, expired, and revoked consents
    filter by ``ConsentStatus`` and ``expires_at`` as appropriate.
    """

    def save(self, consent: ConsentRecord) -> None:
        """Persist a new or updated consent record.

        Parameters
        ----------
        consent:
            The ``ConsentRecord`` aggregate to persist.
        """
        ...

    def find_by_id(self, consent_id: ConsentId) -> ConsentRecord | None:
        """Retrieve a consent record by its unique identifier.

        Parameters
        ----------
        consent_id:
            The ``ConsentId`` to look up.

        Returns
        -------
        The matching consent record, or ``None`` if no record
        exists with the given identifier.
        """
        ...

    def find_active(self) -> list[ConsentRecord]:
        """Retrieve all consent records with ``ACTIVE`` status.

        Returns
        -------
        A list of ``ConsentRecord`` instances whose status is
        ``ConsentStatus.ACTIVE``.
        """
        ...

    def find_expired(self) -> list[ConsentRecord]:
        """Retrieve all consent records that have passed their expiry.

        Expired consents are those whose ``expires_at`` is in the
        past, regardless of their current status.

        Returns
        -------
        A list of ``ConsentRecord`` instances that have expired.
        """
        ...

    def find_revoked(self) -> list[ConsentRecord]:
        """Retrieve all consent records with ``REVOKED`` status.

        Returns
        -------
        A list of ``ConsentRecord`` instances whose status is
        ``ConsentStatus.REVOKED``.
        """
        ...

    def count(self) -> int:
        """Return the total number of consent records.

        Returns
        -------
        Total consent record count (0 if the store is empty).
        """
        ...

from __future__ import annotations

from typing import Protocol

from backend.audit.domain.model import AuditChainHead, AuditEntry, AuditEntryId


class AuditEntryRepositoryPort(Protocol):
    """Repository port for ``AuditEntry`` persistence.

    An implementation persists ``AuditEntry`` aggregates to a
    concrete store. All methods are synchronous; adapters that
    require async should use ``asyncio.to_thread`` or wrap in
    an async adapter class.
    """

    def save(self, entry: AuditEntry) -> None:
        """Persist a new audit entry.

        Entries are append-only. Calling ``save`` with an
        ``entry_id`` that already exists should raise
        ``AuditEntryAlreadyExistsError`` (defined by the
        implementing adapter).

        Parameters
        ----------
        entry:
            The fully-constructed ``AuditEntry`` aggregate
            returned by ``AuditEntryFactory.create()``.
        """
        ...

    def find_by_id(self, entry_id: AuditEntryId) -> AuditEntry | None:
        """Retrieve a single entry by its unique identifier.

        Parameters
        ----------
        entry_id:
            The ``AuditEntryId`` to look up.

        Returns
        -------
        The matching entry, or ``None`` if no entry exists
        with the given identifier.
        """
        ...

    def find_by_chain(
        self,
        chain_name: str,
        *,
        since_index: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        """Retrieve entries from a named chain in index order.

        Results are ordered by ``entry_index`` ascending.

        Parameters
        ----------
        chain_name:
            The chain to query (e.g. ``"security"``).
        since_index:
            If set, only return entries with
            ``entry_index >= since_index``.
        limit:
            Maximum number of entries to return.
        offset:
            Number of entries to skip (for pagination).

        Returns
        -------
        A list of ``AuditEntry`` instances, newest-last.
        """
        ...

    def find_by_correlation_id(
        self, correlation_id: str
    ) -> list[AuditEntry]:
        """Retrieve all entries sharing a correlation ID.

        Parameters
        ----------
        correlation_id:
            The correlation ID to search for.

        Returns
        -------
        A list of ``AuditEntry`` instances, ordered by
        ``occurred_at`` ascending.
        """
        ...

    def count_by_chain(self, chain_name: str) -> int:
        """Return the total number of entries in a chain.

        Parameters
        ----------
        chain_name:
            The chain to count.

        Returns
        -------
        Total entry count for the chain (0 if the chain
        has no entries).
        """
        ...


class AuditChainHeadRepositoryPort(Protocol):
    """Repository port for ``AuditChainHead`` persistence.

    Chain heads track the latest entry hash and total entry
    count per chain. They are updated atomically every time
    a new entry is saved.
    """

    def save(self, head: AuditChainHead) -> None:
        """Persist or update a chain head.

        If a head already exists for ``head.chain_name``,
        the implementation replaces it (upsert semantics).

        Parameters
        ----------
        head:
            The chain-head snapshot to persist.
        """
        ...

    def find_by_chain(self, chain_name: str) -> AuditChainHead | None:
        """Retrieve the head of a named chain.

        Parameters
        ----------
        chain_name:
            The chain to query.

        Returns
        -------
        The chain-head snapshot, or ``None`` if the chain
        has no entries yet.
        """
        ...

    def find_all(self) -> list[AuditChainHead]:
        """List all known chain heads.

        Returns
        -------
        A list of ``AuditChainHead`` instances, one per
        chain that has at least one entry.
        """
        ...

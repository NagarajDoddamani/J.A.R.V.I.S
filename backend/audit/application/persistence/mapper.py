from __future__ import annotations

from typing import Protocol

from backend.audit.application.persistence.dto import (
    AuditChainHeadStorageDTO,
    AuditEntryStorageDTO,
    AuditOutboxStorageDTO,
)
from backend.audit.domain.model import (
    AuditChainHead,
    AuditEntry,
    AuditEntryRecorded,
)


class AuditEntryMapper(Protocol):
    """Bidirectional mapping between ``AuditEntry`` and ``AuditEntryStorageDTO``.

    Implementations flatten nested value objects (``ActorRef``,
    ``TargetRef``, ``EntryHash``, ``EntryIndex``, ``OccurredAt``)
    into the DTO's primitive fields and reconstruct them on the
    reverse path.

    The mapping MUST be lossless — a roundtrip
    ``dto_to_domain(domain_to_dto(entry))`` must produce an
    ``AuditEntry`` equal in all value fields.
    """

    def domain_to_dto(self, entry: AuditEntry) -> AuditEntryStorageDTO:
        """Convert a domain ``AuditEntry`` to its storage DTO.

        Parameters
        ----------
        entry:
            The domain aggregate root.

        Returns
        -------
        A flat ``AuditEntryStorageDTO`` containing every field
        from the entry, with value objects decomposed.
        """
        ...

    def dto_to_domain(self, dto: AuditEntryStorageDTO) -> AuditEntry:
        """Reconstruct a domain ``AuditEntry`` from its storage DTO.

        Parameters
        ----------
        dto:
            The flat storage representation.

        Returns
        -------
        A fully reconstructed ``AuditEntry`` aggregate with
        all value objects rehydrated and ``state == RECORDED``.
        """
        ...


class AuditChainHeadMapper(Protocol):
    """Bidirectional mapping between ``AuditChainHead`` and ``AuditChainHeadStorageDTO``.

    The ``updated_at`` field in the DTO is adapter-managed and
    may be ``None`` on the domain-to-DTO path (the domain entity
    has no timestamp). On the DTO-to-domain path the timestamp
    is discarded.
    """

    def domain_to_dto(
        self, head: AuditChainHead
    ) -> AuditChainHeadStorageDTO:
        """Convert a domain ``AuditChainHead`` to its storage DTO.

        Parameters
        ----------
        head:
            The domain chain-head snapshot.

        Returns
        -------
        A flat ``AuditChainHeadStorageDTO``.
        """
        ...

    def dto_to_domain(
        self, dto: AuditChainHeadStorageDTO
    ) -> AuditChainHead:
        """Reconstruct a domain ``AuditChainHead`` from its storage DTO.

        Parameters
        ----------
        dto:
            The flat storage representation.

        Returns
        -------
        A fully reconstructed ``AuditChainHead``.
        """
        ...


class AuditOutboxMapper(Protocol):
    """Mapping between ``AuditEntryRecorded`` domain events and ``AuditOutboxStorageDTO``.

    Domain events that originate from the audit aggregate are
    stored in the outbox before being published. This mapper
    converts between the domain event shape and the flattened
    outbox DTO.
    """

    def event_to_dto(
        self, event: AuditEntryRecorded
    ) -> AuditOutboxStorageDTO:
        """Convert a domain event to its outbox storage DTO.

        Parameters
        ----------
        event:
            The ``AuditEntryRecorded`` domain event emitted by
            ``AuditEntryFactory.create()``.

        Returns
        -------
        A flat ``AuditOutboxStorageDTO``. The ``published``
        flag is always ``False`` for newly converted events.
        """
        ...

    def dto_to_event(
        self, dto: AuditOutboxStorageDTO
    ) -> AuditEntryRecorded:
        """Reconstruct a domain event from its outbox storage DTO.

        Parameters
        ----------
        dto:
            The flat outbox storage representation.

        Returns
        -------
        A fully reconstructed ``AuditEntryRecorded`` domain event.
        """
        ...

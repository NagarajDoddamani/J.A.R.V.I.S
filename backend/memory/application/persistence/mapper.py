from __future__ import annotations

from typing import Protocol, Union

from backend.memory.application.persistence.dto import (
    ConsentStorageDTO,
    MemoryOutboxStorageDTO,
    MemoryStorageDTO,
)
from backend.memory.domain.model import (
    ConsentGranted,
    ConsentRecord,
    ConsentRevoked,
    Memory,
    MemoryCreated,
    MemoryDeleted,
    MemoryPurgeScheduled,
    MemoryPurged,
    MemoryRetentionExpired,
    MemoryUpdated,
)

MemoryOutboxDomainEvent = Union[
    MemoryCreated,
    MemoryUpdated,
    MemoryDeleted,
    MemoryRetentionExpired,
    MemoryPurgeScheduled,
    MemoryPurged,
    ConsentGranted,
    ConsentRevoked,
]


class MemoryMapper(Protocol):
    """Bidirectional mapping between ``Memory`` and ``MemoryStorageDTO``.

    Implementations flatten nested value objects (``MemoryId``,
    ``ConsentId``, ``MemoryContent``, ``Provenance``,
    ``RevisionNumber``, ``RetentionPolicy``) into the DTO's
    primitive fields and reconstruct them on the reverse path.

    The mapping MUST be lossless — a roundtrip
    ``dto_to_domain(domain_to_dto(memory))`` must produce a
    ``Memory`` equal in all value fields.
    """

    def domain_to_dto(self, memory: Memory) -> MemoryStorageDTO:
        """Convert a domain ``Memory`` to its storage DTO.

        Parameters
        ----------
        memory:
            The domain aggregate root.

        Returns
        -------
        A flat ``MemoryStorageDTO`` containing every field from the
        memory, with value objects decomposed.
        """
        ...

    def dto_to_domain(self, dto: MemoryStorageDTO) -> Memory:
        """Reconstruct a domain ``Memory`` from its storage DTO.

        Parameters
        ----------
        dto:
            The flat storage representation.

        Returns
        -------
        A fully reconstructed ``Memory`` aggregate with all value
        objects rehydrated.
        """
        ...


class ConsentMapper(Protocol):
    """Bidirectional mapping between ``ConsentRecord`` and ``ConsentStorageDTO``.

    Flattens ``ConsentId`` into a string and reconstructs the
    aggregate on the reverse path. The mapping MUST be lossless.
    """

    def domain_to_dto(self, consent: ConsentRecord) -> ConsentStorageDTO:
        """Convert a domain ``ConsentRecord`` to its storage DTO.

        Parameters
        ----------
        consent:
            The domain consent aggregate.

        Returns
        -------
        A flat ``ConsentStorageDTO``.
        """
        ...

    def dto_to_domain(self, dto: ConsentStorageDTO) -> ConsentRecord:
        """Reconstruct a domain ``ConsentRecord`` from its storage DTO.

        Parameters
        ----------
        dto:
            The flat storage representation.

        Returns
        -------
        A fully reconstructed ``ConsentRecord`` aggregate.
        """
        ...


class MemoryOutboxMapper(Protocol):
    """Mapping between memory domain events and ``MemoryOutboxStorageDTO``.

    Domain events that originate from memory or consent aggregates
    are stored in the outbox before being published. This mapper
    converts between the domain event shape and the flattened outbox
    DTO. The ``event_type`` field in the DTO determines which domain
    event class to reconstruct.
    """

    def event_to_dto(self, event: MemoryOutboxDomainEvent) -> MemoryOutboxStorageDTO:
        """Convert a domain event to its outbox storage DTO.

        Parameters
        ----------
        event:
            The domain event emitted by a memory or consent aggregate.

        Returns
        -------
        A flat ``MemoryOutboxStorageDTO``. The ``published`` flag is
        always ``False`` for newly converted events.
        """
        ...

    def dto_to_event(self, dto: MemoryOutboxStorageDTO) -> MemoryOutboxDomainEvent:
        """Reconstruct a domain event from its outbox storage DTO.

        Parameters
        ----------
        dto:
            The flat outbox storage representation.

        Returns
        -------
        A fully reconstructed domain event, as determined by
        ``dto.event_type``.
        """
        ...

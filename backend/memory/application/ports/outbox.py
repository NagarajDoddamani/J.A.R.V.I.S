from __future__ import annotations

from typing import Protocol, Union

from backend.memory.domain.model import (
    ConsentGranted,
    ConsentRevoked,
    MemoryCreated,
    MemoryDeleted,
    MemoryPurgeScheduled,
    MemoryPurged,
    MemoryRetentionExpired,
    MemoryUpdated,
)


MemoryOutboxEvent = Union[
    MemoryCreated,
    MemoryUpdated,
    MemoryDeleted,
    MemoryRetentionExpired,
    MemoryPurgeScheduled,
    MemoryPurged,
    ConsentGranted,
    ConsentRevoked,
]


class MemoryOutboxPort(Protocol):
    """Transactional outbox port for memory domain events.

    When a memory or consent aggregate changes state, the corresponding
    domain event is stored in an outbox so it can be published to NATS
    (or another message broker) reliably. The outbox ensures at-least-
    once delivery semantics.
    """

    def append(self, event: MemoryOutboxEvent) -> None:
        """Store a domain event in the outbox.

        The event is marked as unpublished. An implementation should
        use the same transactional context as the repository port to
        guarantee that the aggregate change and its outbox event are
        committed atomically.

        Parameters
        ----------
        event:
            The domain event to store.
        """
        ...

    def fetch_unpublished(self, limit: int = 100) -> list[MemoryOutboxEvent]:
        """Retrieve unpublished domain events.

        Returns events in the order they were appended (FIFO).
        The caller publishes them and then calls ``mark_published``
        for each successfully delivered event.

        Parameters
        ----------
        limit:
            Maximum number of events to fetch (default 100).

        Returns
        -------
        A list of domain events that have not yet been marked as
        published.
        """
        ...

    def mark_published(self, event_id: str) -> None:
        """Mark an outbox event as successfully published.

        After the event has been delivered to the message broker,
        the caller invokes this method to prevent duplicate delivery.
        This method must be idempotent — calling it multiple times
        for the same ``event_id`` must not raise an error.

        Parameters
        ----------
        event_id:
            The unique identifier of the event to mark (typically
            the string representation of ``MemoryId`` or
            ``ConsentId``).
        """
        ...

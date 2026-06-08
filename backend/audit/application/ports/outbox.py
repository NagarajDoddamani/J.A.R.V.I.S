from __future__ import annotations

from typing import Protocol

from backend.audit.domain.model import AuditEntryId, AuditEntryRecorded


class AuditOutboxPort(Protocol):
    """Transactional outbox port for audit domain events.

    When an ``AuditEntry`` is recorded, the corresponding
    ``AuditEntryRecorded`` domain event must be stored in an
    outbox so it can be published to NATS (or another message
    broker) reliably. The outbox ensures at-least-once delivery
    semantics.
    """

    def append(self, event: AuditEntryRecorded) -> None:
        """Store a domain event in the outbox.

        The event is marked as unpublished. An implementation
        should use the same transactional context as
        ``AuditEntryRepositoryPort.save()`` to guarantee
        that the entry and its outbox event are committed
        atomically.

        Parameters
        ----------
        event:
            The ``AuditEntryRecorded`` domain event to store.
        """
        ...

    def mark_published(self, entry_id: AuditEntryId) -> None:
        """Mark an outbox event as successfully published.

        After the event has been delivered to the message
        broker, the caller invokes this method to prevent
        duplicate delivery.

        Parameters
        ----------
        entry_id:
            The entry ID of the event to mark.
        """
        ...

    def fetch_unpublished(
        self, limit: int = 50
    ) -> list[AuditEntryRecorded]:
        """Retrieve unpublished domain events.

        Returns events in the order they were appended
        (FIFO). The caller publishes them and then calls
        ``mark_published`` for each successfully delivered
        event.

        Parameters
        ----------
        limit:
            Maximum number of events to fetch.

        Returns
        -------
        A list of ``AuditEntryRecorded`` events that have
        not yet been marked as published.
        """
        ...

from __future__ import annotations

from typing import Protocol

from backend.settings.domain.model import (
    SettingsReset,
    SettingUpdated,
)

# A settings domain event is either a single-setting change or a
# full reset. This union will expand as the domain grows.
SettingsDomainEvent = SettingUpdated | SettingsReset


class SettingsOutboxPort(Protocol):
    """Transactional outbox port for settings domain events.

    When a ``SettingUpdated`` or ``SettingsReset`` event is raised,
    it must be stored in an outbox so it can be published to NATS
    (or another message broker) reliably. The outbox ensures
    at-least-once delivery semantics via an idempotent mark.

    An implementation should share a transactional context with
    ``SettingsRepositoryPort.save()`` to guarantee that the profile
    and its events are committed atomically.
    """

    def append(self, event: SettingsDomainEvent) -> None:
        """Store a domain event in the outbox.

        The event is initially marked as unpublished.  After the
        enclosing transaction commits, a background publisher will
        read unpublished events, deliver them, and mark them
        published.

        Parameters
        ----------
        event:
            A ``SettingUpdated`` or ``SettingsReset`` domain event.
        """
        ...

    def fetch_unpublished(
        self, limit: int = 50
    ) -> list[SettingsDomainEvent]:
        """Retrieve unpublished domain events in FIFO order.

        Returns events in the order they were appended.  The caller
        publishes each event to the message broker and then calls
        ``mark_published`` for every successfully delivered event.

        Parameters
        ----------
        limit:
            Maximum number of events to fetch (default 50).

        Returns
        -------
        A list of domain events that have not yet been marked as
        published, ordered by append time ascending.
        """
        ...

    def mark_published(self, event_id: str) -> None:
        """Mark an outbox event as successfully published.

        Idempotent — calling ``mark_published`` more than once for
        the same ``event_id`` is a no-op.

        Parameters
        ----------
        event_id:
            The unique identifier of the event to mark.  This is
            obtained from the event payload (e.g.
            ``str(event.profile_id)``).
        """
        ...

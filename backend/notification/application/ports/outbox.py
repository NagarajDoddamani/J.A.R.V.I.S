from __future__ import annotations

from typing import Protocol, Union

from backend.notification.domain.model import (
    NotificationAcknowledged,
    NotificationActionInvoked,
    NotificationCreated,
    NotificationDismissed,
    NotificationExpired,
    NotificationShown,
)


NotificationOutboxEvent = Union[
    NotificationCreated,
    NotificationShown,
    NotificationAcknowledged,
    NotificationDismissed,
    NotificationExpired,
    NotificationActionInvoked,
]


class NotificationOutboxPort(Protocol):
    """Transactional outbox port for notification domain events.

    When a notification or action aggregate changes state, the
    corresponding domain event is stored in an outbox so it can be
    published to NATS (or another message broker) reliably. The
    outbox ensures at-least-once delivery semantics.
    """

    def append(self, event: NotificationOutboxEvent) -> None:
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

    def fetch_unpublished(
        self, limit: int = 100
    ) -> list[NotificationOutboxEvent]:
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

    def mark_published(self, notification_id: str) -> None:
        """Mark an outbox event as successfully published.

        After the event has been delivered to the message broker,
        the caller invokes this method to prevent duplicate delivery.
        This method must be idempotent — calling it multiple times
        for the same ``notification_id`` must not raise an error.

        Parameters
        ----------
        notification_id:
            The unique identifier of the notification whose event
            should be marked published (typically the string
            representation of ``NotificationId`` or ``ActionId``).
        """
        ...

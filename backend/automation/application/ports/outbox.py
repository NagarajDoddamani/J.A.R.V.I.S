from __future__ import annotations

from typing import Protocol, Union

from backend.automation.domain.model import (
    ActionAdded,
    AutomationActivated,
    AutomationCreated,
    AutomationDisabled,
    AutomationExecutionCompleted,
    AutomationExecutionFailed,
    AutomationExecutionStarted,
    AutomationPaused,
    TriggerAdded,
    TriggerDisabled,
    TriggerEnabled,
)

AutomationOutboxEvent = Union[
    AutomationCreated,
    AutomationActivated,
    AutomationPaused,
    AutomationDisabled,
    AutomationExecutionStarted,
    AutomationExecutionCompleted,
    AutomationExecutionFailed,
    TriggerAdded,
    TriggerEnabled,
    TriggerDisabled,
    ActionAdded,
]


class AutomationOutboxPort(Protocol):
    """Transactional outbox port for automation domain events.

    When an automation, trigger, or execution aggregate changes state,
    the corresponding domain event is stored in an outbox so it can
    be published to NATS (or another message broker) reliably. The
    outbox ensures at-least-once delivery semantics.
    """

    def append(self, event: AutomationOutboxEvent) -> None:
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
    ) -> list[AutomationOutboxEvent]:
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

    def mark_published(self, aggregate_id: str) -> None:
        """Mark an outbox event as successfully published.

        After the event has been delivered to the message broker,
        the caller invokes this method to prevent duplicate delivery.
        This method must be idempotent — calling it multiple times
        for the same ``aggregate_id`` must not raise an error.

        Parameters
        ----------
        aggregate_id:
            The unique identifier of the aggregate whose event
            should be marked published (typically the string
            representation of ``AutomationId``, ``TriggerId``,
            or ``WorkflowExecutionId``).
        """
        ...

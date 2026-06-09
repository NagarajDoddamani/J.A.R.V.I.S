from __future__ import annotations

from typing import Protocol

from backend.notification.domain.model import (
    ActionId,
    Notification,
    NotificationAction,
    NotificationId,
    NotificationPriority,
    NotificationStatus,
)


class NotificationRepositoryPort(Protocol):
    """Repository port for ``Notification`` aggregate persistence.

    An implementation persists ``Notification`` aggregates to a
    concrete store. Notifications are queryable by status, priority,
    and target. All methods are synchronous.
    """

    def save(self, notification: Notification) -> None:
        """Persist a new or updated notification.

        Implementations should use upsert semantics — if a
        notification with the same ``notification_id`` already
        exists it is replaced; otherwise a new record is created.

        Parameters
        ----------
        notification:
            The ``Notification`` aggregate to persist.
        """
        ...

    def find_by_id(
        self, notification_id: NotificationId
    ) -> Notification | None:
        """Retrieve a single notification by its unique identifier.

        Parameters
        ----------
        notification_id:
            The ``NotificationId`` to look up.

        Returns
        -------
        The matching notification, or ``None`` if no notification
        exists with the given identifier.
        """
        ...

    def find_by_status(
        self, status: NotificationStatus
    ) -> list[Notification]:
        """Retrieve all notifications with a given status.

        Parameters
        ----------
        status:
            The ``NotificationStatus`` to filter by.

        Returns
        -------
        A list of ``Notification`` instances with the given status.
        """
        ...

    def find_by_priority(
        self, priority: NotificationPriority
    ) -> list[Notification]:
        """Retrieve all notifications with a given priority.

        Parameters
        ----------
        priority:
            The ``NotificationPriority`` to filter by.

        Returns
        -------
        A list of ``Notification`` instances with the given priority.
        """
        ...

    def find_by_target(
        self, target_type: str, target_id: str
    ) -> list[Notification]:
        """Retrieve all notifications for a specific target.

        Parameters
        ----------
        target_type:
            The target type (e.g. ``"user"``, ``"admin"``).
        target_id:
            The target instance identifier.

        Returns
        -------
        A list of ``Notification`` instances for the given target.
        """
        ...

    def find_expired(self) -> list[Notification]:
        """Retrieve all expired notifications.

        Returns notifications whose status is ``EXPIRED`` or whose
        ``expires_at`` is in the past.

        Returns
        -------
        A list of ``Notification`` instances that have expired.
        """
        ...

    def count(self) -> int:
        """Return the total number of notifications.

        This count includes all statuses.

        Returns
        -------
        Total notification count (0 if the store is empty).
        """
        ...


class NotificationActionRepositoryPort(Protocol):
    """Repository port for ``NotificationAction`` persistence.

    An implementation persists ``NotificationAction`` aggregates to
    a concrete store. Actions are queryable by notification.
    """

    def save(self, action: NotificationAction) -> None:
        """Persist a new action.

        Uses upsert semantics.

        Parameters
        ----------
        action:
            The ``NotificationAction`` aggregate to persist.
        """
        ...

    def find_by_id(self, action_id: ActionId) -> NotificationAction | None:
        """Retrieve an action by its unique identifier.

        Parameters
        ----------
        action_id:
            The ``ActionId`` to look up.

        Returns
        -------
        The matching action, or ``None`` if no action exists with
        the given identifier.
        """
        ...

    def find_by_notification_id(
        self, notification_id: NotificationId
    ) -> list[NotificationAction]:
        """Retrieve all actions for a notification.

        Parameters
        ----------
        notification_id:
            The ``NotificationId`` to search for.

        Returns
        -------
        A list of ``NotificationAction`` instances for the given
        notification.
        """
        ...

    def count(self) -> int:
        """Return the total number of actions.

        Returns
        -------
        Total action count (0 if the store is empty).
        """
        ...

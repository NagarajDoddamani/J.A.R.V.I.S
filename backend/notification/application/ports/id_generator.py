from __future__ import annotations

from typing import Protocol

from backend.notification.domain.model import ActionId, NotificationId


class NotificationIdGeneratorPort(Protocol):
    """Identifier generator for the notification domain.

    Produces unique ``NotificationId`` and ``ActionId`` values.
    Swappable implementations allow UUID-based generation in
    production or deterministic sequences in tests.
    """

    def generate_notification_id(self) -> NotificationId:
        """Generate a unique notification identifier.

        The returned ``NotificationId`` MUST be globally unique and
        suitable for use as an aggregate identifier.

        Returns
        -------
        A unique ``NotificationId`` value.
        """
        ...

    def generate_action_id(self) -> ActionId:
        """Generate a unique action identifier.

        The returned ``ActionId`` MUST be globally unique and
        suitable for use as an aggregate identifier.

        Returns
        -------
        A unique ``ActionId`` value.
        """
        ...

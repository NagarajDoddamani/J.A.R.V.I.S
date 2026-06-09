from __future__ import annotations

from backend.notification.domain.model import ActionId, NotificationId


class UuidGeneratorAdapter:
    """Production ID generator using UUID v4.

    Conforms to ``NotificationIdGeneratorPort`` by providing
    ``generate_notification_id`` and ``generate_action_id`` methods.
    """

    def generate_notification_id(self) -> NotificationId:
        return NotificationId()

    def generate_action_id(self) -> ActionId:
        return ActionId()

from __future__ import annotations

from datetime import datetime

from backend.notification.application.use_cases.create_notification import (
    CreateNotificationUseCase,
)
from backend.notification.application.use_cases.dto import CreateNotificationRequest
from backend.notification.application.use_cases.exceptions import UseCaseError
from backend.runtime.envelope import CommandEnvelope
from backend.runtime.handler import CommandResult
from backend.runtime.registry import CommandRegistry


def _safe_event(event_type: str, **fields: object) -> dict[str, object]:
    return {
        "event_type": event_type,
        "payload": {k: v for k, v in fields.items() if v is not None},
    }


def register_notification_handlers(
    registry: CommandRegistry,
    create_notification_use_case: CreateNotificationUseCase,
) -> None:
    """Register all notification command handlers."""

    async def handle_create_notification(envelope: CommandEnvelope) -> CommandResult:
        try:
            expires_at_raw = envelope.payload.get("expires_at")
            expires_at: datetime | None = None
            if isinstance(expires_at_raw, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at_raw)
                except ValueError:
                    pass

            request = CreateNotificationRequest(
                title=envelope.payload.get("title", ""),
                message=envelope.payload.get("message", ""),
                priority=envelope.payload.get("priority", "normal"),
                channel=envelope.payload.get("channel", "in_app"),
                target_type=envelope.payload.get("target_type", "user"),
                target_id=envelope.payload.get("target_id", ""),
                expires_at=expires_at,
            )
            response = create_notification_use_case.execute(request)
            return CommandResult(
                success=True,
                events=[
                    _safe_event(
                        "notification.created",
                        notification_id=response.notification_id,
                        status=response.status,
                        priority=response.priority,
                        channel=response.channel,
                    )
                ],
            )
        except UseCaseError as exc:
            return CommandResult(success=False, error=str(exc))

    registry.register("notification.create_notification", handle_create_notification)

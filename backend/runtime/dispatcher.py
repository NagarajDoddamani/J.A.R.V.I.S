from __future__ import annotations

from datetime import datetime, timezone

from backend.runtime.envelope import CommandEnvelope
from backend.runtime.errors import CommandExpiredError, CommandHandlerError, CommandRejectedError
from backend.runtime.handler import CommandResult
from backend.runtime.registry import CommandRegistry


class CommandDispatcher:
    """Validates and routes incoming commands to registered handlers.

    The dispatcher enforces envelope-level semantics (expiry, handler
    existence) before delegating to the handler. Handlers are expected
    to return a :class:`CommandResult` rather than raising; unexpected
    exceptions are wrapped in :class:`CommandHandlerError`.
    """

    def __init__(self, registry: CommandRegistry) -> None:
        self._registry = registry

    async def dispatch(self, envelope: CommandEnvelope) -> CommandResult:
        """Validate and execute a command.

        1. Check the command has not expired.
        2. Look up the handler for ``envelope.command_type``.
        3. Execute the handler.
        4. Return the result.

        Raises ``CommandExpiredError`` if the command is past
        ``expires_at``. Raises ``CommandRejectedError`` if no handler
        is registered for the command type. Raises ``CommandHandlerError``
        if the handler raises an unexpected exception.
        """
        if envelope.is_expired(now=datetime.now(tz=timezone.utc)):
            raise CommandExpiredError(
                f"Command {envelope.command_id!r} of type "
                f"{envelope.command_type!r} expired at {envelope.expires_at.isoformat()}"
            )

        handler = self._registry.get(envelope.command_type)
        if handler is None:
            raise CommandRejectedError(
                f"No handler registered for command type {envelope.command_type!r}"
            )

        try:
            result = await handler(envelope)
        except CommandExpiredError:
            raise
        except CommandRejectedError:
            raise
        except Exception as exc:
            raise CommandHandlerError(
                f"Handler for {envelope.command_type!r} failed: {exc}"
            ) from exc

        return result

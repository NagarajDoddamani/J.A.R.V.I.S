from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.runtime.handler import CommandHandler


class CommandRegistry:
    """Maps command types to their owning handlers.

    Each command type (e.g. ``CREATE_MEMORY_COMMAND``) is registered
    to exactly one handler. Duplicate registration raises.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, CommandHandler] = {}

    def register(self, command_type: str, handler: CommandHandler) -> None:
        """Register a handler for a command type.

        Raises ``ValueError`` if the command type is already registered.
        """
        if command_type in self._handlers:
            raise ValueError(
                f"Command type {command_type!r} is already registered "
                f"to {self._handlers[command_type]}"
            )
        self._handlers[command_type] = handler

    def register_or_replace(self, command_type: str, handler: CommandHandler) -> None:
        """Register or replace a handler for a command type."""
        self._handlers[command_type] = handler

    def get(self, command_type: str) -> CommandHandler | None:
        """Return the handler for a command type, or ``None``."""
        return self._handlers.get(command_type)

    def unregister(self, command_type: str) -> None:
        """Remove a registered handler."""
        self._handlers.pop(command_type, None)

    def has(self, command_type: str) -> bool:
        """Return ``True`` if the command type has a registered handler."""
        return command_type in self._handlers

    @property
    def registered_types(self) -> frozenset[str]:
        """Return the set of registered command types."""
        return frozenset(self._handlers)

    def clear(self) -> None:
        """Remove all registered handlers."""
        self._handlers.clear()

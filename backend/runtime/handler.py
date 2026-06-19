from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from backend.runtime.envelope import CommandEnvelope


@dataclass(frozen=True)
class CommandResult:
    """The outcome of a command handler execution.

    On success, ``events`` may contain resulting event payloads that the
    subscriber should publish after acknowledgement.
    """

    success: bool
    events: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


@runtime_checkable
class CommandHandler(Protocol):
    """Protocol for command handlers.

    Implementations receive a validated :class:`CommandEnvelope` and
    return a :class:`CommandResult`. Handlers must be idempotent and
    should not raise exceptions — use ``CommandResult(success=False, error=...)``
    for expected failures and let unexpected exceptions propagate to the
    subscriber's error boundary.
    """

    async def __call__(self, envelope: CommandEnvelope) -> CommandResult:
        """Execute the command handler."""
        ...

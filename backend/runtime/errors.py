class RuntimeError(Exception):
    """Base exception for runtime command bus errors."""


class CommandValidationError(RuntimeError):
    """Raised when a command envelope fails structural or semantic validation."""


class CommandExpiredError(RuntimeError):
    """Raised when a command has exceeded its expiry time."""


class CommandHandlerError(RuntimeError):
    """Raised when a registered handler fails during execution."""


class CommandRejectedError(RuntimeError):
    """Raised when an explicit handler rejection occurs (business rule)."""

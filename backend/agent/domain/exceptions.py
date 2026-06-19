from __future__ import annotations


class AgentDomainError(Exception):
    """Base exception for agent domain errors."""

    def __init__(self, message: str = "") -> None:
        self.message = message
        super().__init__(message)


class InvalidAgentNameError(AgentDomainError):
    pass


class InvalidAgentGoalError(AgentDomainError):
    pass


class InvalidAgentInstructionError(AgentDomainError):
    pass


class InvalidAgentResultError(AgentDomainError):
    pass


class InvalidFailureReasonError(AgentDomainError):
    pass


class InvalidTransitionError(AgentDomainError):
    def __init__(self, entity: str, current: str, target: str) -> None:
        self.entity = entity
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid {entity} transition from {current!r} to {target!r}"
        )


class AgentTerminalError(AgentDomainError):
    def __init__(self, status: str) -> None:
        self.status = status
        super().__init__(f"Agent is in terminal state {status!r}")


class AgentDisabledError(AgentDomainError):
    def __init__(self) -> None:
        super().__init__("Agent is disabled and cannot perform actions")


class AgentPausedError(AgentDomainError):
    def __init__(self) -> None:
        super().__init__("Agent is paused and cannot perform actions")


class AgentTaskNotStartedError(AgentDomainError):
    def __init__(self, action: str) -> None:
        self.action = action
        super().__init__(f"Task must be started before {action}")


class AgentExecutionNotStartedError(AgentDomainError):
    def __init__(self, action: str) -> None:
        self.action = action
        super().__init__(f"Execution must be started before {action}")


class AgentTaskNotFoundError(AgentDomainError):
    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(f"Task not found: {task_id}")


class AgentExecutionNotFoundError(AgentDomainError):
    def __init__(self, execution_id: str) -> None:
        self.execution_id = execution_id
        super().__init__(f"Execution not found: {execution_id}")


class DuplicateAgentTaskIdError(AgentDomainError):
    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(f"Duplicate task ID: {task_id}")


class DuplicateAgentExecutionIdError(AgentDomainError):
    def __init__(self, execution_id: str) -> None:
        self.execution_id = execution_id
        super().__init__(f"Duplicate execution ID: {execution_id}")


class InvalidAgentTypeError(AgentDomainError):
    def __init__(self, agent_type: str) -> None:
        self.agent_type = agent_type
        super().__init__(f"Invalid agent type: {agent_type}")


class ResultRequiredError(AgentDomainError):
    def __init__(self) -> None:
        super().__init__("Result is required")

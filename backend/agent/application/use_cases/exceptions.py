from __future__ import annotations


class UseCaseError(Exception):
    """Base exception for all use-case-level errors."""


class AgentNotFoundError(UseCaseError):
    def __init__(self, agent_id: str) -> None:
        super().__init__(f"Agent not found: {agent_id}")
        self.agent_id = agent_id


class AgentTaskNotFoundError(UseCaseError):
    def __init__(self, task_id: str) -> None:
        super().__init__(f"Agent task not found: {task_id}")
        self.task_id = task_id


class AgentExecutionNotFoundError(UseCaseError):
    def __init__(self, execution_id: str) -> None:
        super().__init__(f"Agent execution not found: {execution_id}")
        self.execution_id = execution_id

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AgentResponse:
    agent_id: str
    agent_type: str = "coordinator"
    name: str | None = None
    status: str = "idle"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    task_count: int = 0
    execution_count: int = 0


@dataclass
class TaskResponse:
    task_id: str
    agent_id: str | None = None
    goal: str | None = None
    instruction: str | None = None
    status: str = "pending"
    result: str | None = None
    failure_reason: str | None = None


@dataclass
class ExecutionResponse:
    execution_id: str
    agent_id: str | None = None
    task_id: str | None = None
    status: str = "pending"
    result: str | None = None
    failure_reason: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class CreateAgentRequest:
    name: str
    agent_type: str = "coordinator"


@dataclass
class CreateAgentResponse:
    agent_id: str
    agent_type: str
    name: str | None
    status: str
    created_at: datetime


@dataclass
class AgentLifecycleRequest:
    agent_id: str


@dataclass
class AgentLifecycleResponse:
    agent_id: str
    status: str
    updated_at: datetime | None = None


@dataclass
class CreateTaskRequest:
    agent_id: str
    goal: str
    instruction: str


@dataclass
class CreateTaskResponse:
    task_id: str
    agent_id: str | None
    goal: str | None
    instruction: str | None
    status: str


@dataclass
class TaskLifecycleRequest:
    agent_id: str
    task_id: str


@dataclass
class TaskLifecycleResponse:
    task_id: str
    agent_id: str | None
    status: str
    result: str | None = None
    failure_reason: str | None = None


@dataclass
class CompleteTaskRequest:
    agent_id: str
    task_id: str
    result: str


@dataclass
class FailTaskRequest:
    agent_id: str
    task_id: str
    failure_reason: str


@dataclass
class StartExecutionRequest:
    agent_id: str
    task_id: str


@dataclass
class StartExecutionResponse:
    execution_id: str
    agent_id: str | None
    task_id: str | None
    status: str
    started_at: datetime | None = None


@dataclass
class CompleteExecutionRequest:
    agent_id: str
    execution_id: str
    result: str


@dataclass
class FailExecutionRequest:
    agent_id: str
    execution_id: str
    failure_reason: str


@dataclass
class ExecutionLifecycleResponse:
    execution_id: str
    agent_id: str | None
    task_id: str | None
    status: str
    result: str | None = None
    failure_reason: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class GetAgentRequest:
    agent_id: str


@dataclass
class ListAgentsRequest:
    status: str | None = None
    agent_type: str | None = None


@dataclass
class ListAgentsResponse:
    agents: list[AgentResponse] = field(default_factory=list)
    total: int = 0


@dataclass
class GetTaskRequest:
    task_id: str


@dataclass
class ListTasksRequest:
    agent_id: str | None = None
    status: str | None = None


@dataclass
class ListTasksResponse:
    tasks: list[TaskResponse] = field(default_factory=list)
    total: int = 0


@dataclass
class GetExecutionRequest:
    execution_id: str


@dataclass
class ListExecutionsRequest:
    agent_id: str | None = None
    task_id: str | None = None
    status: str | None = None


@dataclass
class ListExecutionsResponse:
    executions: list[ExecutionResponse] = field(default_factory=list)
    total: int = 0

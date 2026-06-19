from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from backend.agent.application.ports.outbox import AgentOutboxPort
from backend.agent.application.ports.repository import (
    AgentExecutionRepositoryPort,
    AgentRepositoryPort,
    AgentTaskRepositoryPort,
)
from backend.agent.application.use_cases.activate_agent import (
    ActivateAgentUseCase,
)
from backend.agent.application.use_cases.cancel_task import CancelTaskUseCase
from backend.agent.application.use_cases.complete_execution import (
    CompleteExecutionUseCase,
)
from backend.agent.application.use_cases.complete_task import (
    CompleteTaskUseCase,
)
from backend.agent.application.use_cases.create_agent import (
    CreateAgentUseCase,
)
from backend.agent.application.use_cases.create_task import CreateTaskUseCase
from backend.agent.application.use_cases.disable_agent import (
    DisableAgentUseCase,
)
from backend.agent.application.use_cases.dto import (
    AgentLifecycleRequest,
    AgentLifecycleResponse,
    AgentResponse,
    CompleteExecutionRequest,
    CompleteTaskRequest,
    CreateAgentRequest,
    CreateAgentResponse,
    CreateTaskRequest,
    CreateTaskResponse,
    ExecutionLifecycleResponse,
    ExecutionResponse,
    FailExecutionRequest,
    FailTaskRequest,
    GetAgentRequest,
    GetExecutionRequest,
    GetTaskRequest,
    ListAgentsRequest,
    ListAgentsResponse,
    ListExecutionsRequest,
    ListExecutionsResponse,
    ListTasksRequest,
    ListTasksResponse,
    StartExecutionRequest,
    StartExecutionResponse,
    TaskLifecycleRequest,
    TaskLifecycleResponse,
    TaskResponse,
)
from backend.agent.application.use_cases.exceptions import (
    AgentExecutionNotFoundError,
    AgentNotFoundError,
    AgentTaskNotFoundError,
    UseCaseError,
)
from backend.agent.application.use_cases.fail_execution import (
    FailExecutionUseCase,
)
from backend.agent.application.use_cases.fail_task import FailTaskUseCase
from backend.agent.application.use_cases.get_agent import GetAgentUseCase
from backend.agent.application.use_cases.get_execution import (
    GetExecutionUseCase,
)
from backend.agent.application.use_cases.get_task import GetTaskUseCase
from backend.agent.application.use_cases.list_agents import (
    ListAgentsUseCase,
)
from backend.agent.application.use_cases.list_executions import (
    ListExecutionsUseCase,
)
from backend.agent.application.use_cases.list_tasks import ListTasksUseCase
from backend.agent.application.use_cases.pause_agent import (
    PauseAgentUseCase,
)
from backend.agent.application.use_cases.start_execution import (
    StartExecutionUseCase,
)
from backend.agent.application.use_cases.start_task import StartTaskUseCase
from backend.agent.domain.model import (
    Agent,
    AgentActivated,
    AgentCreated,
    AgentDisabled,
    AgentExecution,
    AgentExecutionCompleted,
    AgentExecutionFailed,
    AgentExecutionId,
    AgentExecutionStarted,
    AgentExecutionStatus,
    AgentGoal,
    AgentId,
    AgentInstruction,
    AgentName,
    AgentPaused,
    AgentResult,
    AgentStatus,
    AgentTask,
    AgentTaskCancelled,
    AgentTaskCompleted,
    AgentTaskCreated,
    AgentTaskFailed,
    AgentTaskId,
    AgentTaskStarted,
    AgentTaskStatus,
    AgentType,
    FailureReason,
)


# ===================================================================
# Fake repositories
# ===================================================================


class FakeAgentRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, Agent] = {}
        self.save_calls: list[Agent] = []

    def save(self, agent: Agent) -> None:
        self._store[agent.agent_id.value] = agent
        self.save_calls.append(agent)

    def find_by_id(self, agent_id: AgentId) -> Agent | None:
        return self._store.get(agent_id.value)

    def find_by_status(self, status: AgentStatus) -> list[Agent]:
        return [a for a in self._store.values() if a.status == status]

    def find_by_type(self, agent_type: AgentType) -> list[Agent]:
        return [a for a in self._store.values() if a.agent_type == agent_type]

    def find_all(self) -> list[Agent]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class FakeTaskRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, AgentTask] = {}
        self.save_calls: list[AgentTask] = []

    def save(self, task: AgentTask) -> None:
        self._store[task.task_id.value] = task
        self.save_calls.append(task)

    def find_by_id(self, task_id: AgentTaskId) -> AgentTask | None:
        return self._store.get(task_id.value)

    def find_by_agent_id(self, agent_id: AgentId) -> list[AgentTask]:
        return [t for t in self._store.values() if t.agent_id == agent_id]

    def find_by_status(self, status: AgentTaskStatus) -> list[AgentTask]:
        return [t for t in self._store.values() if t.status == status]

    def find_all(self) -> list[AgentTask]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class FakeExecutionRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, AgentExecution] = {}
        self.save_calls: list[AgentExecution] = []

    def save(self, execution: AgentExecution) -> None:
        self._store[execution.execution_id.value] = execution
        self.save_calls.append(execution)

    def find_by_id(
        self, execution_id: AgentExecutionId
    ) -> AgentExecution | None:
        return self._store.get(execution_id.value)

    def find_by_agent_id(self, agent_id: AgentId) -> list[AgentExecution]:
        return [e for e in self._store.values() if e.agent_id == agent_id]

    def find_by_task_id(self, task_id: AgentTaskId) -> list[AgentExecution]:
        return [e for e in self._store.values() if e.task_id == task_id]

    def find_by_status(
        self, status: AgentExecutionStatus
    ) -> list[AgentExecution]:
        return [e for e in self._store.values() if e.status == status]

    def find_all(self) -> list[AgentExecution]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class FakeAgentOutbox:
    def __init__(self) -> None:
        self._events: list = []
        self.append_calls: list = []

    def append(self, event: object) -> None:
        self._events.append(event)
        self.append_calls.append(event)

    def fetch_unpublished(self, limit: int = 100) -> list:
        return list(self._events[:limit])

    def mark_published(self, aggregate_id: str) -> None:
        pass


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def agent_repo() -> FakeAgentRepository:
    return FakeAgentRepository()


@pytest.fixture
def task_repo() -> FakeTaskRepository:
    return FakeTaskRepository()


@pytest.fixture
def execution_repo() -> FakeExecutionRepository:
    return FakeExecutionRepository()


@pytest.fixture
def outbox() -> FakeAgentOutbox:
    return FakeAgentOutbox()


def _create_saved_agent(
    repo: FakeAgentRepository,
    name: str = "test-agent",
    agent_type: str = "research",
) -> Agent:
    from backend.agent.domain.factory import AgentFactory

    agent, _ = AgentFactory.create_agent(name=name, agent_type=agent_type)
    repo.save(agent)
    return agent


def _create_agent_with_task(
    repo: FakeAgentRepository,
    task_goal: str = "test goal",
    task_instruction: str = "do something",
) -> tuple[Agent, AgentTask]:
    from backend.agent.domain.factory import AgentFactory

    agent, _ = AgentFactory.create_agent(
        name="test-agent", agent_type="research",
    )
    task, _ = AgentFactory.create_task(
        agent=agent, goal=task_goal, instruction=task_instruction,
    )
    repo.save(agent)
    return agent, task


def _make_agent_active(agent: Agent) -> None:
    from backend.agent.domain.factory import AgentFactory

    AgentFactory.activate_agent(agent)


def _make_task_running(task: AgentTask) -> None:
    task.start()


def _make_execution_started(agent: Agent, task_id: AgentTaskId) -> AgentExecution:
    return agent.start_execution(task_id)


# ===================================================================
# CreateAgentUseCase
# ===================================================================


class TestCreateAgentUseCase:
    def test_happy_path(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        uc = CreateAgentUseCase(agent_repo, outbox)
        request = CreateAgentRequest(name="my-agent", agent_type="research")
        response = uc.execute(request)
        assert isinstance(response, CreateAgentResponse)
        assert response.name == "my-agent"
        assert response.agent_type == "research"
        assert response.status == "idle"
        assert response.created_at is not None

    def test_default_agent_type(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        uc = CreateAgentUseCase(agent_repo, outbox)
        request = CreateAgentRequest(name="default-agent")
        response = uc.execute(request)
        assert response.agent_type == "coordinator"

    def test_saves_agent(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        uc = CreateAgentUseCase(agent_repo, outbox)
        request = CreateAgentRequest(name="saved", agent_type="automation")
        uc.execute(request)
        assert len(agent_repo.save_calls) == 1
        saved = agent_repo.save_calls[0]
        assert saved.name is not None
        assert saved.name.value == "saved"

    def test_appends_event(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        uc = CreateAgentUseCase(agent_repo, outbox)
        request = CreateAgentRequest(name="evt", agent_type="knowledge")
        uc.execute(request)
        assert len(outbox.append_calls) == 1
        event = outbox.append_calls[0]
        assert isinstance(event, AgentCreated)

    def test_agent_id_in_response(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        uc = CreateAgentUseCase(agent_repo, outbox)
        request = CreateAgentRequest(name="id-test", agent_type="research")
        response = uc.execute(request)
        assert isinstance(response.agent_id, str)
        assert len(response.agent_id) > 0


# ===================================================================
# ActivateAgentUseCase
# ===================================================================


class TestActivateAgentUseCase:
    def test_happy_path(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent = _create_saved_agent(agent_repo)
        uc = ActivateAgentUseCase(agent_repo, outbox)
        request = AgentLifecycleRequest(agent_id=str(agent.agent_id))
        response = uc.execute(request)
        assert isinstance(response, AgentLifecycleResponse)
        assert response.status == "active"
        assert response.updated_at is not None

    def test_not_found(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        uc = ActivateAgentUseCase(agent_repo, outbox)
        request = AgentLifecycleRequest(agent_id=str(uuid4()))
        with pytest.raises(AgentNotFoundError):
            uc.execute(request)

    def test_saves_agent(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent = _create_saved_agent(agent_repo)
        uc = ActivateAgentUseCase(agent_repo, outbox)
        before = len(agent_repo.save_calls)
        request = AgentLifecycleRequest(agent_id=str(agent.agent_id))
        uc.execute(request)
        assert len(agent_repo.save_calls) == before + 1

    def test_appends_event(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent = _create_saved_agent(agent_repo)
        uc = ActivateAgentUseCase(agent_repo, outbox)
        request = AgentLifecycleRequest(agent_id=str(agent.agent_id))
        uc.execute(request)
        assert len(outbox.append_calls) == 1
        assert isinstance(outbox.append_calls[0], AgentActivated)

    def test_agent_activated_in_repo(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent = _create_saved_agent(agent_repo)
        uc = ActivateAgentUseCase(agent_repo, outbox)
        request = AgentLifecycleRequest(agent_id=str(agent.agent_id))
        uc.execute(request)
        stored = agent_repo.find_by_id(agent.agent_id)
        assert stored is not None
        assert stored.status == AgentStatus.ACTIVE


# ===================================================================
# PauseAgentUseCase
# ===================================================================


class TestPauseAgentUseCase:
    def test_happy_path(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent = _create_saved_agent(agent_repo)
        _make_agent_active(agent)
        agent_repo.save(agent)
        uc = PauseAgentUseCase(agent_repo, outbox)
        request = AgentLifecycleRequest(agent_id=str(agent.agent_id))
        response = uc.execute(request)
        assert response.status == "paused"

    def test_not_found(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        uc = PauseAgentUseCase(agent_repo, outbox)
        request = AgentLifecycleRequest(agent_id=str(uuid4()))
        with pytest.raises(AgentNotFoundError):
            uc.execute(request)

    def test_appends_event(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent = _create_saved_agent(agent_repo)
        _make_agent_active(agent)
        agent_repo.save(agent)
        uc = PauseAgentUseCase(agent_repo, outbox)
        request = AgentLifecycleRequest(agent_id=str(agent.agent_id))
        uc.execute(request)
        assert isinstance(outbox.append_calls[-1], AgentPaused)

    def test_invalid_transition_idle_to_paused(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent = _create_saved_agent(agent_repo)
        uc = PauseAgentUseCase(agent_repo, outbox)
        request = AgentLifecycleRequest(agent_id=str(agent.agent_id))
        from backend.agent.domain.exceptions import InvalidTransitionError
        with pytest.raises(InvalidTransitionError):
            uc.execute(request)


# ===================================================================
# DisableAgentUseCase
# ===================================================================


class TestDisableAgentUseCase:
    def test_happy_path(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent = _create_saved_agent(agent_repo)
        uc = DisableAgentUseCase(agent_repo, outbox)
        request = AgentLifecycleRequest(agent_id=str(agent.agent_id))
        response = uc.execute(request)
        assert response.status == "disabled"

    def test_not_found(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        uc = DisableAgentUseCase(agent_repo, outbox)
        request = AgentLifecycleRequest(agent_id=str(uuid4()))
        with pytest.raises(AgentNotFoundError):
            uc.execute(request)

    def test_appends_event(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent = _create_saved_agent(agent_repo)
        uc = DisableAgentUseCase(agent_repo, outbox)
        request = AgentLifecycleRequest(agent_id=str(agent.agent_id))
        uc.execute(request)
        assert isinstance(outbox.append_calls[-1], AgentDisabled)

    def test_terminal_state(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent = _create_saved_agent(agent_repo)
        uc = DisableAgentUseCase(agent_repo, outbox)
        request = AgentLifecycleRequest(agent_id=str(agent.agent_id))
        uc.execute(request)
        stored = agent_repo.find_by_id(agent.agent_id)
        assert stored is not None
        assert stored.is_disabled is True


# ===================================================================
# CreateTaskUseCase
# ===================================================================


class TestCreateTaskUseCase:
    def test_happy_path(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent = _create_saved_agent(agent_repo)
        uc = CreateTaskUseCase(agent_repo, outbox)
        request = CreateTaskRequest(
            agent_id=str(agent.agent_id),
            goal="my goal",
            instruction="my instruction",
        )
        response = uc.execute(request)
        assert isinstance(response, CreateTaskResponse)
        assert response.goal == "my goal"
        assert response.instruction == "my instruction"
        assert response.status == "pending"

    def test_not_found(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        uc = CreateTaskUseCase(agent_repo, outbox)
        request = CreateTaskRequest(
            agent_id=str(uuid4()), goal="g", instruction="i",
        )
        with pytest.raises(AgentNotFoundError):
            uc.execute(request)

    def test_saves_agent(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent = _create_saved_agent(agent_repo)
        uc = CreateTaskUseCase(agent_repo, outbox)
        before = len(agent_repo.save_calls)
        request = CreateTaskRequest(
            agent_id=str(agent.agent_id), goal="g", instruction="i",
        )
        uc.execute(request)
        assert len(agent_repo.save_calls) == before + 1

    def test_appends_event(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent = _create_saved_agent(agent_repo)
        uc = CreateTaskUseCase(agent_repo, outbox)
        request = CreateTaskRequest(
            agent_id=str(agent.agent_id), goal="g", instruction="i",
        )
        uc.execute(request)
        assert len(outbox.append_calls) == 1
        assert isinstance(outbox.append_calls[0], AgentTaskCreated)

    def test_task_added_to_agent(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent = _create_saved_agent(agent_repo)
        uc = CreateTaskUseCase(agent_repo, outbox)
        request = CreateTaskRequest(
            agent_id=str(agent.agent_id), goal="g", instruction="i",
        )
        uc.execute(request)
        stored = agent_repo.find_by_id(agent.agent_id)
        assert stored is not None
        assert len(stored.tasks) == 1


# ===================================================================
# StartTaskUseCase
# ===================================================================


class TestStartTaskUseCase:
    def test_happy_path(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent, task = _create_agent_with_task(agent_repo)
        uc = StartTaskUseCase(agent_repo, outbox)
        request = TaskLifecycleRequest(
            agent_id=str(agent.agent_id),
            task_id=str(task.task_id),
        )
        response = uc.execute(request)
        assert isinstance(response, TaskLifecycleResponse)
        assert response.status == "running"

    def test_not_found_agent(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        uc = StartTaskUseCase(agent_repo, outbox)
        request = TaskLifecycleRequest(
            agent_id=str(uuid4()), task_id=str(uuid4()),
        )
        with pytest.raises(AgentNotFoundError):
            uc.execute(request)

    def test_appends_event(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent, task = _create_agent_with_task(agent_repo)
        uc = StartTaskUseCase(agent_repo, outbox)
        request = TaskLifecycleRequest(
            agent_id=str(agent.agent_id),
            task_id=str(task.task_id),
        )
        uc.execute(request)
        assert isinstance(outbox.append_calls[-1], AgentTaskStarted)

    def test_agent_saved(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent, task = _create_agent_with_task(agent_repo)
        uc = StartTaskUseCase(agent_repo, outbox)
        before = len(agent_repo.save_calls)
        request = TaskLifecycleRequest(
            agent_id=str(agent.agent_id),
            task_id=str(task.task_id),
        )
        uc.execute(request)
        assert len(agent_repo.save_calls) == before + 1


# ===================================================================
# CompleteTaskUseCase
# ===================================================================


class TestCompleteTaskUseCase:
    def test_happy_path(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent, task = _create_agent_with_task(agent_repo)
        _make_task_running(task)
        agent_repo.save(agent)
        uc = CompleteTaskUseCase(agent_repo, outbox)
        request = CompleteTaskRequest(
            agent_id=str(agent.agent_id),
            task_id=str(task.task_id),
            result="success",
        )
        response = uc.execute(request)
        assert response.status == "completed"
        assert response.result == "success"

    def test_not_found_agent(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        uc = CompleteTaskUseCase(agent_repo, outbox)
        request = CompleteTaskRequest(
            agent_id=str(uuid4()), task_id=str(uuid4()), result="ok",
        )
        with pytest.raises(AgentNotFoundError):
            uc.execute(request)

    def test_appends_event(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent, task = _create_agent_with_task(agent_repo)
        _make_task_running(task)
        agent_repo.save(agent)
        uc = CompleteTaskUseCase(agent_repo, outbox)
        request = CompleteTaskRequest(
            agent_id=str(agent.agent_id),
            task_id=str(task.task_id),
            result="done",
        )
        uc.execute(request)
        assert isinstance(outbox.append_calls[-1], AgentTaskCompleted)


# ===================================================================
# FailTaskUseCase
# ===================================================================


class TestFailTaskUseCase:
    def test_happy_path(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent, task = _create_agent_with_task(agent_repo)
        _make_task_running(task)
        agent_repo.save(agent)
        uc = FailTaskUseCase(agent_repo, outbox)
        request = FailTaskRequest(
            agent_id=str(agent.agent_id),
            task_id=str(task.task_id),
            failure_reason="something went wrong",
        )
        response = uc.execute(request)
        assert response.status == "failed"
        assert response.failure_reason == "something went wrong"

    def test_not_found_agent(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        uc = FailTaskUseCase(agent_repo, outbox)
        request = FailTaskRequest(
            agent_id=str(uuid4()), task_id=str(uuid4()), failure_reason="err",
        )
        with pytest.raises(AgentNotFoundError):
            uc.execute(request)

    def test_appends_event(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent, task = _create_agent_with_task(agent_repo)
        _make_task_running(task)
        agent_repo.save(agent)
        uc = FailTaskUseCase(agent_repo, outbox)
        request = FailTaskRequest(
            agent_id=str(agent.agent_id),
            task_id=str(task.task_id),
            failure_reason="err",
        )
        uc.execute(request)
        assert isinstance(outbox.append_calls[-1], AgentTaskFailed)


# ===================================================================
# CancelTaskUseCase
# ===================================================================


class TestCancelTaskUseCase:
    def test_happy_path(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent, task = _create_agent_with_task(agent_repo)
        uc = CancelTaskUseCase(agent_repo, outbox)
        request = TaskLifecycleRequest(
            agent_id=str(agent.agent_id),
            task_id=str(task.task_id),
        )
        response = uc.execute(request)
        assert response.status == "cancelled"

    def test_not_found_agent(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        uc = CancelTaskUseCase(agent_repo, outbox)
        request = TaskLifecycleRequest(
            agent_id=str(uuid4()), task_id=str(uuid4()),
        )
        with pytest.raises(AgentNotFoundError):
            uc.execute(request)

    def test_appends_event(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent, task = _create_agent_with_task(agent_repo)
        uc = CancelTaskUseCase(agent_repo, outbox)
        request = TaskLifecycleRequest(
            agent_id=str(agent.agent_id),
            task_id=str(task.task_id),
        )
        uc.execute(request)
        assert isinstance(outbox.append_calls[-1], AgentTaskCancelled)


# ===================================================================
# StartExecutionUseCase
# ===================================================================


class TestStartExecutionUseCase:
    def test_happy_path(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent, task = _create_agent_with_task(agent_repo)
        uc = StartExecutionUseCase(agent_repo, outbox)
        request = StartExecutionRequest(
            agent_id=str(agent.agent_id),
            task_id=str(task.task_id),
        )
        response = uc.execute(request)
        assert isinstance(response, StartExecutionResponse)
        assert response.status == "executing"
        assert response.started_at is not None

    def test_not_found_agent(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        uc = StartExecutionUseCase(agent_repo, outbox)
        request = StartExecutionRequest(
            agent_id=str(uuid4()), task_id=str(uuid4()),
        )
        with pytest.raises(AgentNotFoundError):
            uc.execute(request)

    def test_appends_event(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent, task = _create_agent_with_task(agent_repo)
        uc = StartExecutionUseCase(agent_repo, outbox)
        request = StartExecutionRequest(
            agent_id=str(agent.agent_id),
            task_id=str(task.task_id),
        )
        uc.execute(request)
        assert isinstance(outbox.append_calls[-1], AgentExecutionStarted)

    def test_execution_added_to_agent(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent, task = _create_agent_with_task(agent_repo)
        uc = StartExecutionUseCase(agent_repo, outbox)
        request = StartExecutionRequest(
            agent_id=str(agent.agent_id),
            task_id=str(task.task_id),
        )
        uc.execute(request)
        stored = agent_repo.find_by_id(agent.agent_id)
        assert stored is not None
        assert len(stored.executions) == 1


# ===================================================================
# CompleteExecutionUseCase
# ===================================================================


class TestCompleteExecutionUseCase:
    def test_happy_path(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent, task = _create_agent_with_task(agent_repo)
        execution = _make_execution_started(agent, task.task_id)
        agent_repo.save(agent)
        uc = CompleteExecutionUseCase(agent_repo, outbox)
        request = CompleteExecutionRequest(
            agent_id=str(agent.agent_id),
            execution_id=str(execution.execution_id),
            result="execution done",
        )
        response = uc.execute(request)
        assert isinstance(response, ExecutionLifecycleResponse)
        assert response.status == "completed"
        assert response.result == "execution done"

    def test_not_found_agent(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        uc = CompleteExecutionUseCase(agent_repo, outbox)
        request = CompleteExecutionRequest(
            agent_id=str(uuid4()), execution_id=str(uuid4()), result="ok",
        )
        with pytest.raises(AgentNotFoundError):
            uc.execute(request)

    def test_appends_event(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent, task = _create_agent_with_task(agent_repo)
        execution = _make_execution_started(agent, task.task_id)
        agent_repo.save(agent)
        uc = CompleteExecutionUseCase(agent_repo, outbox)
        request = CompleteExecutionRequest(
            agent_id=str(agent.agent_id),
            execution_id=str(execution.execution_id),
            result="ok",
        )
        uc.execute(request)
        assert isinstance(outbox.append_calls[-1], AgentExecutionCompleted)

    def test_saves_agent(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent, task = _create_agent_with_task(agent_repo)
        execution = _make_execution_started(agent, task.task_id)
        agent_repo.save(agent)
        uc = CompleteExecutionUseCase(agent_repo, outbox)
        before = len(agent_repo.save_calls)
        request = CompleteExecutionRequest(
            agent_id=str(agent.agent_id),
            execution_id=str(execution.execution_id),
            result="ok",
        )
        uc.execute(request)
        assert len(agent_repo.save_calls) == before + 1


# ===================================================================
# FailExecutionUseCase
# ===================================================================


class TestFailExecutionUseCase:
    def test_happy_path(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent, task = _create_agent_with_task(agent_repo)
        execution = _make_execution_started(agent, task.task_id)
        agent_repo.save(agent)
        uc = FailExecutionUseCase(agent_repo, outbox)
        request = FailExecutionRequest(
            agent_id=str(agent.agent_id),
            execution_id=str(execution.execution_id),
            failure_reason="execution failed",
        )
        response = uc.execute(request)
        assert response.status == "failed"
        assert response.failure_reason == "execution failed"

    def test_not_found_agent(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        uc = FailExecutionUseCase(agent_repo, outbox)
        request = FailExecutionRequest(
            agent_id=str(uuid4()), execution_id=str(uuid4()),
            failure_reason="err",
        )
        with pytest.raises(AgentNotFoundError):
            uc.execute(request)

    def test_appends_event(self, agent_repo: FakeAgentRepository, outbox: FakeAgentOutbox) -> None:
        agent, task = _create_agent_with_task(agent_repo)
        execution = _make_execution_started(agent, task.task_id)
        agent_repo.save(agent)
        uc = FailExecutionUseCase(agent_repo, outbox)
        request = FailExecutionRequest(
            agent_id=str(agent.agent_id),
            execution_id=str(execution.execution_id),
            failure_reason="err",
        )
        uc.execute(request)
        assert isinstance(outbox.append_calls[-1], AgentExecutionFailed)


# ===================================================================
# GetAgentUseCase
# ===================================================================


class TestGetAgentUseCase:
    def test_happy_path(self, agent_repo: FakeAgentRepository) -> None:
        agent = _create_saved_agent(agent_repo)
        uc = GetAgentUseCase(agent_repo)
        request = GetAgentRequest(agent_id=str(agent.agent_id))
        response = uc.execute(request)
        assert isinstance(response, AgentResponse)
        assert response.name == "test-agent"
        assert response.agent_type == "research"
        assert response.status == "idle"

    def test_not_found(self, agent_repo: FakeAgentRepository) -> None:
        uc = GetAgentUseCase(agent_repo)
        request = GetAgentRequest(agent_id=str(uuid4()))
        with pytest.raises(AgentNotFoundError):
            uc.execute(request)

    def test_task_and_execution_counts(self, agent_repo: FakeAgentRepository) -> None:
        from backend.agent.domain.factory import AgentFactory

        agent, _ = AgentFactory.create_agent(
            name="multi", agent_type="automation",
        )
        AgentFactory.create_task(agent=agent, goal="g1", instruction="i1")
        AgentFactory.create_task(agent=agent, goal="g2", instruction="i2")
        agent_repo.save(agent)
        uc = GetAgentUseCase(agent_repo)
        request = GetAgentRequest(agent_id=str(agent.agent_id))
        response = uc.execute(request)
        assert response.task_count == 2


# ===================================================================
# ListAgentsUseCase
# ===================================================================


class TestListAgentsUseCase:
    def test_find_all(self, agent_repo: FakeAgentRepository) -> None:
        _create_saved_agent(agent_repo, name="a1")
        _create_saved_agent(agent_repo, name="a2")
        uc = ListAgentsUseCase(agent_repo)
        request = ListAgentsRequest()
        response = uc.execute(request)
        assert isinstance(response, ListAgentsResponse)
        assert len(response.agents) == 2
        assert response.total == 2

    def test_filter_by_status(self, agent_repo: FakeAgentRepository) -> None:
        a1 = _create_saved_agent(agent_repo, name="active-one")
        a2 = _create_saved_agent(agent_repo, name="active-two")
        _make_agent_active(a1)
        _make_agent_active(a2)
        agent_repo.save(a1)
        agent_repo.save(a2)
        uc = ListAgentsUseCase(agent_repo)
        request = ListAgentsRequest(status="active")
        response = uc.execute(request)
        assert len(response.agents) == 2

    def test_filter_by_type(self, agent_repo: FakeAgentRepository) -> None:
        _create_saved_agent(agent_repo, name="r1", agent_type="research")
        _create_saved_agent(agent_repo, name="a1", agent_type="automation")
        uc = ListAgentsUseCase(agent_repo)
        request = ListAgentsRequest(agent_type="research")
        response = uc.execute(request)
        assert len(response.agents) == 1
        assert response.agents[0].agent_type == "research"

    def test_empty(self, agent_repo: FakeAgentRepository) -> None:
        uc = ListAgentsUseCase(agent_repo)
        request = ListAgentsRequest()
        response = uc.execute(request)
        assert len(response.agents) == 0
        assert response.total == 0

    def test_agent_response_fields(self, agent_repo: FakeAgentRepository) -> None:
        _create_saved_agent(agent_repo)
        uc = ListAgentsUseCase(agent_repo)
        response = uc.execute(ListAgentsRequest())
        agent_resp = response.agents[0]
        assert hasattr(agent_resp, "agent_id")
        assert hasattr(agent_resp, "agent_type")
        assert hasattr(agent_resp, "name")
        assert hasattr(agent_resp, "status")
        assert hasattr(agent_resp, "created_at")


# ===================================================================
# GetTaskUseCase
# ===================================================================


class TestGetTaskUseCase:
    def test_happy_path(self, task_repo: FakeTaskRepository) -> None:
        task = AgentTask(
            task_id=AgentTaskId(),
            goal=AgentGoal(value="my goal"),
            instruction=AgentInstruction(value="do it"),
        )
        task_repo.save(task)
        uc = GetTaskUseCase(task_repo)
        request = GetTaskRequest(task_id=str(task.task_id))
        response = uc.execute(request)
        assert isinstance(response, TaskResponse)
        assert response.goal == "my goal"
        assert response.instruction == "do it"

    def test_not_found(self, task_repo: FakeTaskRepository) -> None:
        uc = GetTaskUseCase(task_repo)
        request = GetTaskRequest(task_id=str(uuid4()))
        with pytest.raises(AgentTaskNotFoundError):
            uc.execute(request)

    def test_with_result(self, task_repo: FakeTaskRepository) -> None:
        task = AgentTask(task_id=AgentTaskId())
        task.start()
        task.complete(AgentResult(value="done"))
        task_repo.save(task)
        uc = GetTaskUseCase(task_repo)
        request = GetTaskRequest(task_id=str(task.task_id))
        response = uc.execute(request)
        assert response.status == "completed"
        assert response.result == "done"

    def test_with_failure_reason(self, task_repo: FakeTaskRepository) -> None:
        task = AgentTask(task_id=AgentTaskId())
        task.start()
        task.fail(FailureReason(value="error"))
        task_repo.save(task)
        uc = GetTaskUseCase(task_repo)
        request = GetTaskRequest(task_id=str(task.task_id))
        response = uc.execute(request)
        assert response.status == "failed"
        assert response.failure_reason == "error"


# ===================================================================
# ListTasksUseCase
# ===================================================================


class TestListTasksUseCase:
    def test_find_all(self, task_repo: FakeTaskRepository) -> None:
        task_repo.save(AgentTask(task_id=AgentTaskId()))
        task_repo.save(AgentTask(task_id=AgentTaskId()))
        uc = ListTasksUseCase(task_repo)
        response = uc.execute(ListTasksRequest())
        assert len(response.tasks) == 2

    def test_filter_by_agent(self, task_repo: FakeTaskRepository) -> None:
        agent_id = AgentId()
        t1 = AgentTask(task_id=AgentTaskId())
        object.__setattr__(t1, "_agent_id", agent_id)
        t2 = AgentTask(task_id=AgentTaskId())
        task_repo.save(t1)
        task_repo.save(t2)
        uc = ListTasksUseCase(task_repo)
        request = ListTasksRequest(agent_id=str(agent_id))
        response = uc.execute(request)
        assert len(response.tasks) == 1

    def test_filter_by_status(self, task_repo: FakeTaskRepository) -> None:
        t1 = AgentTask(task_id=AgentTaskId())
        t1.start()
        t2 = AgentTask(task_id=AgentTaskId())
        task_repo.save(t1)
        task_repo.save(t2)
        uc = ListTasksUseCase(task_repo)
        request = ListTasksRequest(status="running")
        response = uc.execute(request)
        assert len(response.tasks) == 1
        assert response.tasks[0].status == "running"

    def test_empty(self, task_repo: FakeTaskRepository) -> None:
        uc = ListTasksUseCase(task_repo)
        response = uc.execute(ListTasksRequest())
        assert len(response.tasks) == 0
        assert response.total == 0

    def test_task_response_fields(self, task_repo: FakeTaskRepository) -> None:
        task_repo.save(AgentTask(task_id=AgentTaskId()))
        uc = ListTasksUseCase(task_repo)
        response = uc.execute(ListTasksRequest())
        t = response.tasks[0]
        assert hasattr(t, "task_id")
        assert hasattr(t, "status")
        assert hasattr(t, "goal")
        assert hasattr(t, "instruction")


# ===================================================================
# GetExecutionUseCase
# ===================================================================


class TestGetExecutionUseCase:
    def test_happy_path(self, execution_repo: FakeExecutionRepository) -> None:
        execution = AgentExecution(execution_id=AgentExecutionId())
        execution_repo.save(execution)
        uc = GetExecutionUseCase(execution_repo)
        request = GetExecutionRequest(execution_id=str(execution.execution_id))
        response = uc.execute(request)
        assert isinstance(response, ExecutionResponse)
        assert response.status == "pending"

    def test_not_found(self, execution_repo: FakeExecutionRepository) -> None:
        uc = GetExecutionUseCase(execution_repo)
        request = GetExecutionRequest(execution_id=str(uuid4()))
        with pytest.raises(AgentExecutionNotFoundError):
            uc.execute(request)

    def test_with_result(self, execution_repo: FakeExecutionRepository) -> None:
        execution = AgentExecution(execution_id=AgentExecutionId())
        execution.start()
        execution.complete(AgentResult(value="done"))
        execution_repo.save(execution)
        uc = GetExecutionUseCase(execution_repo)
        request = GetExecutionRequest(execution_id=str(execution.execution_id))
        response = uc.execute(request)
        assert response.status == "completed"
        assert response.result == "done"


# ===================================================================
# ListExecutionsUseCase
# ===================================================================


class TestListExecutionsUseCase:
    def test_find_all(self, execution_repo: FakeExecutionRepository) -> None:
        execution_repo.save(AgentExecution(execution_id=AgentExecutionId()))
        execution_repo.save(AgentExecution(execution_id=AgentExecutionId()))
        uc = ListExecutionsUseCase(execution_repo)
        response = uc.execute(ListExecutionsRequest())
        assert len(response.executions) == 2

    def test_filter_by_agent(self, execution_repo: FakeExecutionRepository) -> None:
        agent_id = AgentId()
        e1 = AgentExecution(execution_id=AgentExecutionId())
        object.__setattr__(e1, "_agent_id", agent_id)
        e2 = AgentExecution(execution_id=AgentExecutionId())
        execution_repo.save(e1)
        execution_repo.save(e2)
        uc = ListExecutionsUseCase(execution_repo)
        request = ListExecutionsRequest(agent_id=str(agent_id))
        response = uc.execute(request)
        assert len(response.executions) == 1

    def test_filter_by_task(self, execution_repo: FakeExecutionRepository) -> None:
        task_id = AgentTaskId()
        e1 = AgentExecution(execution_id=AgentExecutionId())
        object.__setattr__(e1, "_task_id", task_id)
        e2 = AgentExecution(execution_id=AgentExecutionId())
        execution_repo.save(e1)
        execution_repo.save(e2)
        uc = ListExecutionsUseCase(execution_repo)
        request = ListExecutionsRequest(task_id=str(task_id))
        response = uc.execute(request)
        assert len(response.executions) == 1

    def test_filter_by_status(self, execution_repo: FakeExecutionRepository) -> None:
        e1 = AgentExecution(execution_id=AgentExecutionId())
        e1.start()
        e2 = AgentExecution(execution_id=AgentExecutionId())
        execution_repo.save(e1)
        execution_repo.save(e2)
        uc = ListExecutionsUseCase(execution_repo)
        request = ListExecutionsRequest(status="executing")
        response = uc.execute(request)
        assert len(response.executions) == 1
        assert response.executions[0].status == "executing"

    def test_empty(self, execution_repo: FakeExecutionRepository) -> None:
        uc = ListExecutionsUseCase(execution_repo)
        response = uc.execute(ListExecutionsRequest())
        assert len(response.executions) == 0
        assert response.total == 0

    def test_execution_response_fields(self, execution_repo: FakeExecutionRepository) -> None:
        execution_repo.save(AgentExecution(execution_id=AgentExecutionId()))
        uc = ListExecutionsUseCase(execution_repo)
        response = uc.execute(ListExecutionsRequest())
        e = response.executions[0]
        assert hasattr(e, "execution_id")
        assert hasattr(e, "status")
        assert hasattr(e, "task_id")
        assert hasattr(e, "agent_id")


# ===================================================================
# DTO correctness
# ===================================================================


class TestAgentDTOs:
    def test_agent_response_creation(self) -> None:
        resp = AgentResponse(
            agent_id="a1", agent_type="research", name="test",
        )
        assert resp.agent_id == "a1"
        assert resp.agent_type == "research"
        assert resp.name == "test"
        assert resp.status == "idle"

    def test_task_response_creation(self) -> None:
        resp = TaskResponse(
            task_id="t1", agent_id="a1", status="completed",
            result="done",
        )
        assert resp.task_id == "t1"
        assert resp.result == "done"

    def test_execution_response_creation(self) -> None:
        resp = ExecutionResponse(
            execution_id="e1", agent_id="a1", status="executing",
        )
        assert resp.execution_id == "e1"
        assert resp.status == "executing"

    def test_list_agents_response(self) -> None:
        resp = ListAgentsResponse(
            agents=[AgentResponse(agent_id="a1")], total=1,
        )
        assert len(resp.agents) == 1
        assert resp.total == 1

    def test_list_tasks_response(self) -> None:
        resp = ListTasksResponse(
            tasks=[TaskResponse(task_id="t1")], total=1,
        )
        assert len(resp.tasks) == 1
        assert resp.total == 1

    def test_list_executions_response(self) -> None:
        resp = ListExecutionsResponse(
            executions=[ExecutionResponse(execution_id="e1")], total=1,
        )
        assert len(resp.executions) == 1
        assert resp.total == 1

    def test_create_task_response(self) -> None:
        resp = CreateTaskResponse(
            task_id="t1", agent_id="a1", goal="g", instruction="i",
            status="pending",
        )
        assert resp.task_id == "t1"

    def test_create_agent_response(self) -> None:
        from datetime import datetime, timezone

        resp = CreateAgentResponse(
            agent_id="a1", agent_type="research", name="n",
            status="idle", created_at=datetime.now(tz=timezone.utc),
        )
        assert resp.agent_id == "a1"
        assert resp.status == "idle"


# ===================================================================
# Exception hierarchy
# ===================================================================


class TestUseCaseExceptions:
    def test_use_case_error_base(self) -> None:
        assert issubclass(AgentNotFoundError, UseCaseError)
        assert issubclass(AgentTaskNotFoundError, UseCaseError)
        assert issubclass(AgentExecutionNotFoundError, UseCaseError)

    def test_agent_not_found_error(self) -> None:
        err = AgentNotFoundError("agent-123")
        assert str(err) == "Agent not found: agent-123"
        assert err.agent_id == "agent-123"

    def test_task_not_found_error(self) -> None:
        err = AgentTaskNotFoundError("task-456")
        assert str(err) == "Agent task not found: task-456"
        assert err.task_id == "task-456"

    def test_execution_not_found_error(self) -> None:
        err = AgentExecutionNotFoundError("exec-789")
        assert str(err) == "Agent execution not found: exec-789"
        assert err.execution_id == "exec-789"

    def test_exception_derivation(self) -> None:
        err = AgentNotFoundError("x")
        assert isinstance(err, UseCaseError)
        assert isinstance(err, Exception)

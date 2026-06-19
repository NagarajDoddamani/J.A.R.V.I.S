from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

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
from backend.agent.application.use_cases.dto import (
    AgentLifecycleResponse,
    AgentResponse,
    CreateAgentResponse,
    CreateTaskResponse,
    ExecutionLifecycleResponse,
    ExecutionResponse,
    ListAgentsResponse,
    ListExecutionsResponse,
    ListTasksResponse,
    StartExecutionResponse,
    TaskLifecycleResponse,
    TaskResponse,
)
from backend.agent.application.use_cases.exceptions import (
    AgentExecutionNotFoundError,
    AgentNotFoundError,
    AgentTaskNotFoundError,
)
from backend.agent.bootstrap import (
    get_activate_agent_use_case,
    get_cancel_task_use_case,
    get_complete_execution_use_case,
    get_complete_task_use_case,
    get_create_agent_use_case,
    get_create_task_use_case,
    get_disable_agent_use_case,
    get_execution_use_case,
    get_fail_execution_use_case,
    get_fail_task_use_case,
    get_agent_use_case,
    get_list_agents_use_case,
    get_list_executions_use_case,
    get_list_tasks_use_case,
    get_pause_agent_use_case,
    get_start_execution_use_case,
    get_start_task_use_case,
    get_task_use_case,
)
from backend.agent.domain.exceptions import AgentDomainError
from backend.api.endpoints.agent import router as agent_router

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def app() -> FastAPI:
    return FastAPI()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    app.include_router(agent_router, prefix="/api/v1/agent")
    return TestClient(app)


def _mock_uc(cls):
    m = MagicMock(spec=cls)
    return m


# =====================================================================
# Agent lifecycle
# =====================================================================


class TestCreateAgent:
    def test_201(self, client: TestClient) -> None:
        mock = _mock_uc(CreateAgentUseCase)
        mock.execute.return_value = CreateAgentResponse(
            agent_id="agent-1",
            agent_type="coordinator",
            name="Test",
            status="idle",
            created_at=NOW,
        )
        app = client.app
        app.dependency_overrides[get_create_agent_use_case] = lambda: mock
        resp = client.post("/api/v1/agent/", json={"name": "Test"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["agent_id"] == "agent-1"
        assert data["status"] == "idle"

    def test_400_on_domain_error(self, client: TestClient) -> None:
        mock = _mock_uc(CreateAgentUseCase)
        mock.execute.side_effect = AgentDomainError("bad")
        client.app.dependency_overrides[get_create_agent_use_case] = lambda: mock
        resp = client.post("/api/v1/agent/", json={"name": "Test"})
        assert resp.status_code == 400

    def test_422_on_value_error(self, client: TestClient) -> None:
        mock = _mock_uc(CreateAgentUseCase)
        mock.execute.side_effect = ValueError("invalid")
        client.app.dependency_overrides[get_create_agent_use_case] = lambda: mock
        resp = client.post("/api/v1/agent/", json={"name": "Test"})
        assert resp.status_code == 422


class TestActivateAgent:
    def test_200(self, client: TestClient) -> None:
        mock = _mock_uc(ActivateAgentUseCase)
        mock.execute.return_value = AgentLifecycleResponse(
            agent_id="agent-1", status="active", updated_at=NOW
        )
        client.app.dependency_overrides[get_activate_agent_use_case] = lambda: mock
        resp = client.post("/api/v1/agent/agent-1/activate")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_404(self, client: TestClient) -> None:
        mock = _mock_uc(ActivateAgentUseCase)
        mock.execute.side_effect = AgentNotFoundError("agent-1")
        client.app.dependency_overrides[get_activate_agent_use_case] = lambda: mock
        resp = client.post("/api/v1/agent/agent-1/activate")
        assert resp.status_code == 404

    def test_400(self, client: TestClient) -> None:
        mock = _mock_uc(ActivateAgentUseCase)
        mock.execute.side_effect = AgentDomainError("cannot activate")
        client.app.dependency_overrides[get_activate_agent_use_case] = lambda: mock
        resp = client.post("/api/v1/agent/agent-1/activate")
        assert resp.status_code == 400


class TestPauseAgent:
    def test_200(self, client: TestClient) -> None:
        mock = _mock_uc(PauseAgentUseCase)
        mock.execute.return_value = AgentLifecycleResponse(
            agent_id="agent-1", status="paused"
        )
        client.app.dependency_overrides[get_pause_agent_use_case] = lambda: mock
        resp = client.post("/api/v1/agent/agent-1/pause")
        assert resp.status_code == 200

    def test_404(self, client: TestClient) -> None:
        mock = _mock_uc(PauseAgentUseCase)
        mock.execute.side_effect = AgentNotFoundError("agent-1")
        client.app.dependency_overrides[get_pause_agent_use_case] = lambda: mock
        resp = client.post("/api/v1/agent/agent-1/pause")
        assert resp.status_code == 404


class TestDisableAgent:
    def test_200(self, client: TestClient) -> None:
        mock = _mock_uc(DisableAgentUseCase)
        mock.execute.return_value = AgentLifecycleResponse(
            agent_id="agent-1", status="disabled"
        )
        client.app.dependency_overrides[get_disable_agent_use_case] = lambda: mock
        resp = client.post("/api/v1/agent/agent-1/disable")
        assert resp.status_code == 200

    def test_404(self, client: TestClient) -> None:
        mock = _mock_uc(DisableAgentUseCase)
        mock.execute.side_effect = AgentNotFoundError("agent-1")
        client.app.dependency_overrides[get_disable_agent_use_case] = lambda: mock
        resp = client.post("/api/v1/agent/agent-1/disable")
        assert resp.status_code == 404


# =====================================================================
# Task endpoints
# =====================================================================


class TestCreateTask:
    def test_201(self, client: TestClient) -> None:
        mock = _mock_uc(CreateTaskUseCase)
        mock.execute.return_value = CreateTaskResponse(
            task_id="task-1",
            agent_id="agent-1",
            goal="goal",
            instruction="instr",
            status="pending",
        )
        client.app.dependency_overrides[get_create_task_use_case] = lambda: mock
        resp = client.post(
            "/api/v1/agent/agent-1/tasks",
            json={"agent_id": "agent-1", "goal": "goal", "instruction": "instr"},
        )
        assert resp.status_code == 201

    def test_404(self, client: TestClient) -> None:
        mock = _mock_uc(CreateTaskUseCase)
        mock.execute.side_effect = AgentNotFoundError("agent-1")
        client.app.dependency_overrides[get_create_task_use_case] = lambda: mock
        resp = client.post(
            "/api/v1/agent/agent-1/tasks",
            json={"agent_id": "agent-1", "goal": "goal", "instruction": "instr"},
        )
        assert resp.status_code == 404


class TestStartTask:
    def test_200(self, client: TestClient) -> None:
        mock = _mock_uc(StartTaskUseCase)
        mock.execute.return_value = TaskLifecycleResponse(
            task_id="task-1", agent_id="agent-1", status="running"
        )
        client.app.dependency_overrides[get_start_task_use_case] = lambda: mock
        resp = client.post(
            "/api/v1/agent/tasks/task-1/start?agent_id=agent-1"
        )
        assert resp.status_code == 200

    def test_404_agent(self, client: TestClient) -> None:
        mock = _mock_uc(StartTaskUseCase)
        mock.execute.side_effect = AgentNotFoundError("agent-1")
        client.app.dependency_overrides[get_start_task_use_case] = lambda: mock
        resp = client.post(
            "/api/v1/agent/tasks/task-1/start?agent_id=agent-1"
        )
        assert resp.status_code == 404


class TestCompleteTask:
    def test_200(self, client: TestClient) -> None:
        mock = _mock_uc(CompleteTaskUseCase)
        mock.execute.return_value = TaskLifecycleResponse(
            task_id="task-1", agent_id="agent-1", status="completed",
            result="done"
        )
        client.app.dependency_overrides[get_complete_task_use_case] = lambda: mock
        resp = client.post(
            "/api/v1/agent/tasks/task-1/complete",
            json={"agent_id": "agent-1", "task_id": "task-1", "result": "done"},
        )
        assert resp.status_code == 200

    def test_404_task(self, client: TestClient) -> None:
        mock = _mock_uc(CompleteTaskUseCase)
        mock.execute.side_effect = AgentTaskNotFoundError("task-1")
        client.app.dependency_overrides[get_complete_task_use_case] = lambda: mock
        resp = client.post(
            "/api/v1/agent/tasks/task-1/complete",
            json={"agent_id": "agent-1", "task_id": "task-1", "result": "done"},
        )
        assert resp.status_code == 404


class TestFailTask:
    def test_200(self, client: TestClient) -> None:
        mock = _mock_uc(FailTaskUseCase)
        mock.execute.return_value = TaskLifecycleResponse(
            task_id="task-1", agent_id="agent-1", status="failed",
            failure_reason="err"
        )
        client.app.dependency_overrides[get_fail_task_use_case] = lambda: mock
        resp = client.post(
            "/api/v1/agent/tasks/task-1/fail",
            json={"agent_id": "agent-1", "task_id": "task-1", "failure_reason": "err"},
        )
        assert resp.status_code == 200


class TestCancelTask:
    def test_200(self, client: TestClient) -> None:
        mock = _mock_uc(CancelTaskUseCase)
        mock.execute.return_value = TaskLifecycleResponse(
            task_id="task-1", agent_id="agent-1", status="cancelled"
        )
        client.app.dependency_overrides[get_cancel_task_use_case] = lambda: mock
        resp = client.post(
            "/api/v1/agent/tasks/task-1/cancel?agent_id=agent-1"
        )
        assert resp.status_code == 200

    def test_404(self, client: TestClient) -> None:
        mock = _mock_uc(CancelTaskUseCase)
        mock.execute.side_effect = AgentTaskNotFoundError("task-1")
        client.app.dependency_overrides[get_cancel_task_use_case] = lambda: mock
        resp = client.post(
            "/api/v1/agent/tasks/task-1/cancel?agent_id=agent-1"
        )
        assert resp.status_code == 404


class TestGetTask:
    def test_200(self, client: TestClient) -> None:
        mock = _mock_uc(GetTaskUseCase)
        mock.execute.return_value = TaskResponse(
            task_id="task-1", status="pending"
        )
        client.app.dependency_overrides[get_task_use_case] = lambda: mock
        resp = client.get("/api/v1/agent/tasks/task-1")
        assert resp.status_code == 200

    def test_404(self, client: TestClient) -> None:
        mock = _mock_uc(GetTaskUseCase)
        mock.execute.side_effect = AgentTaskNotFoundError("task-1")
        client.app.dependency_overrides[get_task_use_case] = lambda: mock
        resp = client.get("/api/v1/agent/tasks/task-1")
        assert resp.status_code == 404


class TestListTasks:
    def test_200(self, client: TestClient) -> None:
        mock = _mock_uc(ListTasksUseCase)
        mock.execute.return_value = ListTasksResponse(
            tasks=[], total=0
        )
        client.app.dependency_overrides[get_list_tasks_use_case] = lambda: mock
        resp = client.get("/api/v1/agent/tasks")
        assert resp.status_code == 200

    def test_filter_by_agent_id(self, client: TestClient) -> None:
        mock = _mock_uc(ListTasksUseCase)
        mock.execute.return_value = ListTasksResponse(
            tasks=[TaskResponse(task_id="t1", status="pending")], total=1
        )
        client.app.dependency_overrides[get_list_tasks_use_case] = lambda: mock
        resp = client.get("/api/v1/agent/tasks?agent_id=agent-1")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


# =====================================================================
# Execution endpoints
# =====================================================================


class TestStartExecution:
    def test_201(self, client: TestClient) -> None:
        mock = _mock_uc(StartExecutionUseCase)
        mock.execute.return_value = StartExecutionResponse(
            execution_id="exec-1",
            agent_id="agent-1",
            task_id="task-1",
            status="executing",
        )
        client.app.dependency_overrides[get_start_execution_use_case] = lambda: mock
        resp = client.post(
            "/api/v1/agent/tasks/task-1/executions?agent_id=agent-1"
        )
        assert resp.status_code == 201

    def test_404(self, client: TestClient) -> None:
        mock = _mock_uc(StartExecutionUseCase)
        mock.execute.side_effect = AgentNotFoundError("agent-1")
        client.app.dependency_overrides[get_start_execution_use_case] = lambda: mock
        resp = client.post(
            "/api/v1/agent/tasks/task-1/executions?agent_id=agent-1"
        )
        assert resp.status_code == 404


class TestCompleteExecution:
    def test_200(self, client: TestClient) -> None:
        mock = _mock_uc(CompleteExecutionUseCase)
        mock.execute.return_value = ExecutionLifecycleResponse(
            execution_id="exec-1", agent_id="agent-1", task_id="task-1",
            status="completed", result="done"
        )
        client.app.dependency_overrides[get_complete_execution_use_case] = lambda: mock
        resp = client.post(
            "/api/v1/agent/executions/exec-1/complete",
            json={"agent_id": "agent-1", "execution_id": "exec-1", "result": "done"},
        )
        assert resp.status_code == 200

    def test_404_execution(self, client: TestClient) -> None:
        mock = _mock_uc(CompleteExecutionUseCase)
        mock.execute.side_effect = AgentExecutionNotFoundError("exec-1")
        client.app.dependency_overrides[get_complete_execution_use_case] = lambda: mock
        resp = client.post(
            "/api/v1/agent/executions/exec-1/complete",
            json={"agent_id": "agent-1", "execution_id": "exec-1", "result": "done"},
        )
        assert resp.status_code == 404


class TestFailExecution:
    def test_200(self, client: TestClient) -> None:
        mock = _mock_uc(FailExecutionUseCase)
        mock.execute.return_value = ExecutionLifecycleResponse(
            execution_id="exec-1", agent_id="agent-1", task_id="task-1",
            status="failed", failure_reason="err"
        )
        client.app.dependency_overrides[get_fail_execution_use_case] = lambda: mock
        resp = client.post(
            "/api/v1/agent/executions/exec-1/fail",
            json={"agent_id": "agent-1", "execution_id": "exec-1", "failure_reason": "err"},
        )
        assert resp.status_code == 200


class TestGetExecution:
    def test_200(self, client: TestClient) -> None:
        mock = _mock_uc(GetExecutionUseCase)
        mock.execute.return_value = ExecutionResponse(
            execution_id="exec-1", status="completed"
        )
        client.app.dependency_overrides[get_execution_use_case] = lambda: mock
        resp = client.get("/api/v1/agent/executions/exec-1")
        assert resp.status_code == 200

    def test_404(self, client: TestClient) -> None:
        mock = _mock_uc(GetExecutionUseCase)
        mock.execute.side_effect = AgentExecutionNotFoundError("exec-1")
        client.app.dependency_overrides[get_execution_use_case] = lambda: mock
        resp = client.get("/api/v1/agent/executions/exec-1")
        assert resp.status_code == 404


class TestListExecutions:
    def test_200(self, client: TestClient) -> None:
        mock = _mock_uc(ListExecutionsUseCase)
        mock.execute.return_value = ListExecutionsResponse(
            executions=[], total=0
        )
        client.app.dependency_overrides[get_list_executions_use_case] = lambda: mock
        resp = client.get("/api/v1/agent/executions")
        assert resp.status_code == 200


# =====================================================================
# Agent queries
# =====================================================================


class TestGetAgent:
    def test_200(self, client: TestClient) -> None:
        mock = _mock_uc(GetAgentUseCase)
        mock.execute.return_value = AgentResponse(
            agent_id="agent-1", status="idle"
        )
        client.app.dependency_overrides[get_agent_use_case] = lambda: mock
        resp = client.get("/api/v1/agent/agent-1")
        assert resp.status_code == 200

    def test_404(self, client: TestClient) -> None:
        mock = _mock_uc(GetAgentUseCase)
        mock.execute.side_effect = AgentNotFoundError("agent-1")
        client.app.dependency_overrides[get_agent_use_case] = lambda: mock
        resp = client.get("/api/v1/agent/agent-1")
        assert resp.status_code == 404


class TestListAgents:
    def test_200(self, client: TestClient) -> None:
        mock = _mock_uc(ListAgentsUseCase)
        mock.execute.return_value = ListAgentsResponse(
            agents=[], total=0
        )
        client.app.dependency_overrides[get_list_agents_use_case] = lambda: mock
        resp = client.get("/api/v1/agent/")
        assert resp.status_code == 200

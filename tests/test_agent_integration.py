from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.agent.adapters.outbound.clock import SystemClockAdapter
from backend.agent.adapters.outbound.mapper import (
    AgentOutboxDomainEvent,
)
from backend.agent.adapters.outbound.models import Base
from backend.agent.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyAgentExecutionRepository,
    SqlAlchemyAgentOutboxAdapter,
    SqlAlchemyAgentRepository,
    SqlAlchemyAgentTaskRepository,
)
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
)
from backend.agent.nats import (
    _EVENT_TYPE_MAP,
    _NATS_SUBJECT_MAP,
    publish_agent_outbox_events,
)
from backend.api.endpoints.agent import router as agent_router
from backend.core.database import get_db

for _table in Base.metadata.tables.values():
    _table.schema = None

NOW = datetime(2026, 6, 18, 12, 0, 0, tzinfo=timezone.utc)


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite://", echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    return e


@pytest.fixture
def session(engine):
    conn = engine.connect()
    transaction = conn.begin()
    s = Session(bind=conn)
    yield s
    s.close()
    transaction.rollback()
    conn.close()


@pytest.fixture
def agent_repo(session):
    return SqlAlchemyAgentRepository(session)


@pytest.fixture
def task_repo(session):
    return SqlAlchemyAgentTaskRepository(session)


@pytest.fixture
def execution_repo(session):
    return SqlAlchemyAgentExecutionRepository(session)


@pytest.fixture
def outbox(session):
    return SqlAlchemyAgentOutboxAdapter(session)


@pytest.fixture
def clock():
    return SystemClockAdapter()


@pytest.fixture
def mock_js():
    js = AsyncMock()
    js.publish = AsyncMock()
    return js


@pytest.fixture
def client(session):
    def _override_get_db():
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    app = FastAPI()
    app.include_router(agent_router, prefix="/api/v1/agent")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


# ===================================================================
# Helpers
# ===================================================================


def _create_agent_via_api(client, name="Test Agent", agent_type="coordinator"):
    return client.post(
        "/api/v1/agent/",
        json={"name": name, "agent_type": agent_type},
    )


def _create_agent() -> Agent:
    return Agent(
        agent_id=AgentId(),
        agent_type=AgentType.COORDINATOR,
        name=AgentName(value="Test Agent"),
        status=AgentStatus.IDLE,
        created_at=NOW,
    )


def _make_task(agent: Agent, goal="Test goal", instruction="Test instruction") -> AgentTask:
    goal_vo = AgentGoal(value=goal)
    instruction_vo = AgentInstruction(value=instruction)
    task = AgentTask(
        task_id=AgentTaskId(),
        goal=goal_vo,
        instruction=instruction_vo,
        agent_id=agent.agent_id,
    )
    return task


def _make_execution(agent: Agent, task: AgentTask) -> AgentExecution:
    exec_obj = AgentExecution(
        execution_id=AgentExecutionId(),
        task_id=task.task_id,
        agent_id=agent.agent_id,
    )
    return exec_obj


# ===================================================================
# 1. Agent Lifecycle — Create → Activate → Pause → Disable
# ===================================================================


class TestAgentLifecycle:
    def test_create_agent(self, client) -> None:
        resp = _create_agent_via_api(client)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "idle"

    def test_create_activate(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        resp = client.post(f"/api/v1/agent/{aid}/activate")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_create_activate_pause(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        client.post(f"/api/v1/agent/{aid}/activate")
        resp = client.post(f"/api/v1/agent/{aid}/pause")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    def test_create_activate_pause_disable(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        client.post(f"/api/v1/agent/{aid}/activate")
        client.post(f"/api/v1/agent/{aid}/pause")
        resp = client.post(f"/api/v1/agent/{aid}/disable")
        assert resp.status_code == 200
        assert resp.json()["status"] == "disabled"

    def test_full_lifecycle_status_sequence(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        assert created["status"] == "idle"
        r1 = client.post(f"/api/v1/agent/{aid}/activate")
        assert r1.json()["status"] == "active"
        r2 = client.post(f"/api/v1/agent/{aid}/pause")
        assert r2.json()["status"] == "paused"
        r3 = client.post(f"/api/v1/agent/{aid}/disable")
        assert r3.json()["status"] == "disabled"

    def test_reactivate_after_pause(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        client.post(f"/api/v1/agent/{aid}/activate")
        client.post(f"/api/v1/agent/{aid}/pause")
        resp = client.post(f"/api/v1/agent/{aid}/activate")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_disable_from_idle(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        resp = client.post(f"/api/v1/agent/{aid}/disable")
        assert resp.status_code == 200
        assert resp.json()["status"] == "disabled"

    def test_activate_disabled_returns_400(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        client.post(f"/api/v1/agent/{aid}/disable")
        resp = client.post(f"/api/v1/agent/{aid}/activate")
        assert resp.status_code == 400

    def test_pause_idle_returns_400(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        resp = client.post(f"/api/v1/agent/{aid}/pause")
        assert resp.status_code == 400

    def test_get_agent_after_create(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        resp = client.get(f"/api/v1/agent/{aid}")
        assert resp.status_code == 200
        assert resp.json()["agent_id"] == aid
        assert resp.json()["status"] == "idle"

    def test_list_agents(self, client) -> None:
        _create_agent_via_api(client)
        resp = client.get("/api/v1/agent/")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_get_nonexistent_agent_returns_404(self, client) -> None:
        resp = client.get(f"/api/v1/agent/{uuid4()}")
        assert resp.status_code == 404

    def test_activate_nonexistent_agent_returns_404(self, client) -> None:
        resp = client.post(f"/api/v1/agent/{uuid4()}/activate")
        assert resp.status_code == 404

    def test_pause_nonexistent_agent_returns_404(self, client) -> None:
        resp = client.post(f"/api/v1/agent/{uuid4()}/pause")
        assert resp.status_code == 404

    def test_disable_nonexistent_agent_returns_404(self, client) -> None:
        resp = client.post(f"/api/v1/agent/{uuid4()}/disable")
        assert resp.status_code == 404


# ===================================================================
# 2. Task Lifecycle — Create → Start → Complete / Fail / Cancel
# ===================================================================


class TestTaskLifecycle:
    def test_create_task(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "pending"

    def test_create_then_start(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        resp = client.post(f"/api/v1/agent/tasks/{tid}/start?agent_id={aid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_create_start_complete(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        client.post(f"/api/v1/agent/tasks/{tid}/start?agent_id={aid}")
        resp = client.post(
            f"/api/v1/agent/tasks/{tid}/complete",
            json={"agent_id": aid, "task_id": tid, "result": "done"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_create_start_fail(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        client.post(f"/api/v1/agent/tasks/{tid}/start?agent_id={aid}")
        resp = client.post(
            f"/api/v1/agent/tasks/{tid}/fail",
            json={"agent_id": aid, "task_id": tid, "failure_reason": "err"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_create_cancel_before_start(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        resp = client.post(f"/api/v1/agent/tasks/{tid}/cancel?agent_id={aid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_create_start_cancel(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        client.post(f"/api/v1/agent/tasks/{tid}/start?agent_id={aid}")
        resp = client.post(f"/api/v1/agent/tasks/{tid}/cancel?agent_id={aid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_complete_not_started_returns_400(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        resp = client.post(
            f"/api/v1/agent/tasks/{tid}/complete",
            json={"agent_id": aid, "task_id": tid, "result": "done"},
        )
        assert resp.status_code == 400

    def test_fail_not_started_returns_400(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        resp = client.post(
            f"/api/v1/agent/tasks/{tid}/fail",
            json={"agent_id": aid, "task_id": tid, "failure_reason": "err"},
        )
        assert resp.status_code == 400

    def test_complete_already_completed_returns_400(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        client.post(f"/api/v1/agent/tasks/{tid}/start?agent_id={aid}")
        client.post(
            f"/api/v1/agent/tasks/{tid}/complete",
            json={"agent_id": aid, "task_id": tid, "result": "done"},
        )
        resp = client.post(
            f"/api/v1/agent/tasks/{tid}/complete",
            json={"agent_id": aid, "task_id": tid, "result": "again"},
        )
        assert resp.status_code == 400

    def test_get_task(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        resp = client.get(f"/api/v1/agent/tasks/{tid}")
        assert resp.status_code == 200
        assert resp.json()["task_id"] == tid

    def test_get_nonexistent_task_returns_404(self, client) -> None:
        resp = client.get(f"/api/v1/agent/tasks/{uuid4()}")
        assert resp.status_code == 404

    def test_list_tasks(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        resp = client.get("/api/v1/agent/tasks")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_create_task_nonexistent_agent_returns_404(self, client) -> None:
        resp = client.post(
            f"/api/v1/agent/{uuid4()}/tasks",
            json={"agent_id": str(uuid4()), "goal": "goal", "instruction": "instr"},
        )
        assert resp.status_code == 404

    def test_start_task_nonexistent_agent_returns_404(self, client) -> None:
        resp = client.post(f"/api/v1/agent/tasks/{uuid4()}/start?agent_id={uuid4()}")
        assert resp.status_code == 404

    def test_complete_task_nonexistent_returns_404(self, client) -> None:
        resp = client.post(
            f"/api/v1/agent/tasks/{uuid4()}/complete",
            json={"agent_id": str(uuid4()), "task_id": str(uuid4()), "result": "x"},
        )
        assert resp.status_code == 404

    def test_fail_task_nonexistent_returns_404(self, client) -> None:
        resp = client.post(
            f"/api/v1/agent/tasks/{uuid4()}/fail",
            json={"agent_id": str(uuid4()), "task_id": str(uuid4()), "failure_reason": "x"},
        )
        assert resp.status_code == 404

    def test_cancel_task_nonexistent_returns_404(self, client) -> None:
        resp = client.post(f"/api/v1/agent/tasks/{uuid4()}/cancel?agent_id={uuid4()}")
        assert resp.status_code == 404

    def test_create_task_on_disabled_agent_returns_400(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        client.post(f"/api/v1/agent/{aid}/disable")
        resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        assert resp.status_code == 400


# ===================================================================
# 3. Execution Lifecycle — Start → Complete / Fail
# ===================================================================


class TestExecutionLifecycle:
    def test_start_execution(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        resp = client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        assert resp.status_code == 201
        assert resp.json()["status"] == "executing"

    def test_start_then_complete_execution(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        exec_resp = client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        eid = exec_resp.json()["execution_id"]
        resp = client.post(
            f"/api/v1/agent/executions/{eid}/complete",
            json={"agent_id": aid, "execution_id": eid, "result": "done"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_start_then_fail_execution(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        exec_resp = client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        eid = exec_resp.json()["execution_id"]
        resp = client.post(
            f"/api/v1/agent/executions/{eid}/fail",
            json={"agent_id": aid, "execution_id": eid, "failure_reason": "error"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_get_execution(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        exec_resp = client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        eid = exec_resp.json()["execution_id"]
        resp = client.get(f"/api/v1/agent/executions/{eid}")
        assert resp.status_code == 200
        assert resp.json()["execution_id"] == eid

    def test_get_nonexistent_execution_returns_404(self, client) -> None:
        resp = client.get(f"/api/v1/agent/executions/{uuid4()}")
        assert resp.status_code == 404

    def test_list_executions(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        resp = client.get("/api/v1/agent/executions")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_start_execution_nonexistent_agent_returns_404(self, client) -> None:
        resp = client.post(f"/api/v1/agent/tasks/{uuid4()}/executions?agent_id={uuid4()}")
        assert resp.status_code == 404

    def test_complete_nonexistent_execution_returns_404(self, client) -> None:
        resp = client.post(
            f"/api/v1/agent/executions/{uuid4()}/complete",
            json={"agent_id": str(uuid4()), "execution_id": str(uuid4()), "result": "x"},
        )
        assert resp.status_code == 404

    def test_fail_nonexistent_execution_returns_404(self, client) -> None:
        resp = client.post(
            f"/api/v1/agent/executions/{uuid4()}/fail",
            json={"agent_id": str(uuid4()), "execution_id": str(uuid4()), "failure_reason": "x"},
        )
        assert resp.status_code == 404

    def test_start_execution_on_paused_agent_returns_400(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        client.post(f"/api/v1/agent/{aid}/activate")
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        client.post(f"/api/v1/agent/{aid}/pause")
        resp = client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        assert resp.status_code == 400

    def test_start_execution_on_disabled_agent_returns_400(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        client.post(f"/api/v1/agent/{aid}/activate")
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        client.post(f"/api/v1/agent/{aid}/disable")
        resp = client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        assert resp.status_code == 400

    def test_complete_already_completed_execution_returns_400(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        exec_resp = client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        eid = exec_resp.json()["execution_id"]
        client.post(
            f"/api/v1/agent/executions/{eid}/complete",
            json={"agent_id": aid, "execution_id": eid, "result": "done"},
        )
        resp = client.post(
            f"/api/v1/agent/executions/{eid}/complete",
            json={"agent_id": aid, "execution_id": eid, "result": "again"},
        )
        assert resp.status_code == 400


# ===================================================================
# 4. Repository Roundtrip
# ===================================================================


class TestRepositoryRoundtrip:
    def test_agent_roundtrip(self, agent_repo, session) -> None:
        agent = _create_agent()
        agent_repo.save(agent)
        session.flush()
        loaded = agent_repo.find_by_id(agent.agent_id)
        assert loaded is not None
        assert loaded.agent_id == agent.agent_id
        assert loaded.status == AgentStatus.IDLE

    def test_agent_update_roundtrip(self, agent_repo, session) -> None:
        agent = _create_agent()
        agent_repo.save(agent)
        session.flush()
        agent.activate()
        agent_repo.save(agent)
        session.flush()
        loaded = agent_repo.find_by_id(agent.agent_id)
        assert loaded is not None
        assert loaded.status == AgentStatus.ACTIVE

    def test_agent_with_task_roundtrip(self, agent_repo, session) -> None:
        agent = _create_agent()
        task = _make_task(agent)
        agent._tasks.append(task)
        agent_repo.save(agent)
        session.flush()
        loaded = agent_repo.find_by_id(agent.agent_id)
        assert loaded is not None
        assert len(loaded.tasks) == 1
        assert loaded.tasks[0].task_id == task.task_id

    def test_agent_with_execution_roundtrip(self, agent_repo, session) -> None:
        agent = _create_agent()
        task = _make_task(agent)
        agent._tasks.append(task)
        exec_obj = AgentExecution(
            execution_id=AgentExecutionId(),
            task_id=task.task_id,
            agent_id=agent.agent_id,
            status=AgentExecutionStatus.PENDING,
        )
        agent._executions.append(exec_obj)
        agent_repo.save(agent)
        session.flush()
        loaded = agent_repo.find_by_id(agent.agent_id)
        assert loaded is not None
        assert len(loaded.executions) == 1
        assert loaded.executions[0].execution_id == exec_obj.execution_id

    def test_agent_count(self, agent_repo, session) -> None:
        before = agent_repo.count()
        agent_repo.save(_create_agent())
        session.flush()
        assert agent_repo.count() == before + 1

    def test_find_agent_by_status(self, agent_repo, session) -> None:
        agent = _create_agent()
        agent_repo.save(agent)
        session.flush()
        results = agent_repo.find_by_status(AgentStatus.IDLE)
        assert len(results) >= 1
        assert all(a.status == AgentStatus.IDLE for a in results)

    def test_find_agent_by_type(self, agent_repo, session) -> None:
        agent = _create_agent()
        agent_repo.save(agent)
        session.flush()
        results = agent_repo.find_by_type(AgentType.COORDINATOR)
        assert len(results) >= 1

    def test_find_all_agents(self, agent_repo, session) -> None:
        before = len(agent_repo.find_all())
        agent_repo.save(_create_agent())
        session.flush()
        assert len(agent_repo.find_all()) == before + 1

    def test_task_find_by_id(self, task_repo, session, agent_repo) -> None:
        agent = _create_agent()
        agent_repo.save(agent)
        session.flush()
        task = _make_task(agent)
        task_repo.save(task)
        session.flush()
        loaded = task_repo.find_by_id(task.task_id)
        assert loaded is not None
        assert loaded.task_id == task.task_id

    def test_task_find_by_agent_id(self, task_repo, session, agent_repo) -> None:
        agent = _create_agent()
        agent_repo.save(agent)
        session.flush()
        task = _make_task(agent)
        task_repo.save(task)
        session.flush()
        results = task_repo.find_by_agent_id(agent.agent_id)
        assert len(results) >= 1

    def test_task_find_by_status(self, task_repo, session, agent_repo) -> None:
        agent = _create_agent()
        agent_repo.save(agent)
        session.flush()
        task = _make_task(agent)
        task_repo.save(task)
        session.flush()
        results = task_repo.find_by_status(AgentTaskStatus.PENDING)
        assert len(results) >= 1

    def test_task_count(self, task_repo, session, agent_repo) -> None:
        before = task_repo.count()
        agent = _create_agent()
        agent_repo.save(agent)
        session.flush()
        task = _make_task(agent)
        task_repo.save(task)
        session.flush()
        assert task_repo.count() == before + 1

    def test_execution_find_by_id(self, execution_repo, session) -> None:
        exec_obj = AgentExecution(
            execution_id=AgentExecutionId(),
            task_id=AgentTaskId(),
            agent_id=AgentId(),
        )
        execution_repo.save(exec_obj)
        session.flush()
        loaded = execution_repo.find_by_id(exec_obj.execution_id)
        assert loaded is not None
        assert loaded.execution_id == exec_obj.execution_id

    def test_execution_find_by_agent_id(self, execution_repo, session) -> None:
        aid = AgentId()
        exec_obj = AgentExecution(
            execution_id=AgentExecutionId(), task_id=AgentTaskId(), agent_id=aid,
        )
        execution_repo.save(exec_obj)
        session.flush()
        results = execution_repo.find_by_agent_id(aid)
        assert len(results) >= 1

    def test_execution_find_by_task_id(self, execution_repo, session) -> None:
        tid = AgentTaskId()
        exec_obj = AgentExecution(
            execution_id=AgentExecutionId(), task_id=tid, agent_id=AgentId(),
        )
        execution_repo.save(exec_obj)
        session.flush()
        results = execution_repo.find_by_task_id(tid)
        assert len(results) >= 1

    def test_execution_count(self, execution_repo, session) -> None:
        before = execution_repo.count()
        exec_obj = AgentExecution(
            execution_id=AgentExecutionId(), task_id=AgentTaskId(), agent_id=AgentId(),
        )
        execution_repo.save(exec_obj)
        session.flush()
        assert execution_repo.count() == before + 1

    def test_execution_find_by_status(self, execution_repo, session) -> None:
        exec_obj = AgentExecution(
            execution_id=AgentExecutionId(), task_id=AgentTaskId(), agent_id=AgentId(),
            status=AgentExecutionStatus.PENDING,
        )
        execution_repo.save(exec_obj)
        session.flush()
        results = execution_repo.find_by_status(AgentExecutionStatus.PENDING)
        assert len(results) >= 1


# ===================================================================
# 5. Outbox Lifecycle
# ===================================================================


class TestOutboxLifecycle:
    def test_append_event(self, outbox, session) -> None:
        event = AgentCreated(
            agent_id=AgentId(), agent_type="coordinator", name="test", occurred_at=NOW,
        )
        outbox.append(event)
        session.flush()
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1

    def test_fetch_unpublished_empty_initially(self, outbox) -> None:
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 0

    def test_mark_published(self, outbox, session) -> None:
        event = AgentCreated(
            agent_id=AgentId(), agent_type="coordinator", name="test", occurred_at=NOW,
        )
        outbox.append(event)
        session.flush()
        entries = outbox.fetch_unpublished()
        event_id = str(entries[0].event_id)
        outbox.mark_published(event_id)
        session.flush()
        remaining = outbox.fetch_unpublished()
        assert len(remaining) == 0

    def test_append_multiple_events(self, outbox, session) -> None:
        outbox.append(AgentCreated(
            agent_id=AgentId(), agent_type="coordinator", name="test", occurred_at=NOW,
        ))
        outbox.append(AgentActivated(agent_id=AgentId(), occurred_at=NOW))
        session.flush()
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 2

    def test_partial_mark_published(self, outbox, session) -> None:
        outbox.append(AgentCreated(
            agent_id=AgentId(), agent_type="coordinator", name="test", occurred_at=NOW,
        ))
        outbox.append(AgentActivated(agent_id=AgentId(), occurred_at=NOW))
        session.flush()
        entries = outbox.fetch_unpublished()
        outbox.mark_published(str(entries[0].event_id))
        session.flush()
        remaining = outbox.fetch_unpublished()
        assert len(remaining) == 1

    def test_fetch_respects_limit(self, outbox, session) -> None:
        for _ in range(5):
            outbox.append(AgentCreated(
                agent_id=AgentId(), agent_type="coordinator", name="t", occurred_at=NOW,
            ))
        session.flush()
        entries = outbox.fetch_unpublished(limit=3)
        assert len(entries) == 3

    def test_idempotent_mark_published(self, outbox, session) -> None:
        event = AgentCreated(
            agent_id=AgentId(), agent_type="coordinator", name="test", occurred_at=NOW,
        )
        outbox.append(event)
        session.flush()
        entries = outbox.fetch_unpublished()
        event_id = str(entries[0].event_id)
        outbox.mark_published(event_id)
        outbox.mark_published(event_id)
        session.flush()
        remaining = outbox.fetch_unpublished()
        assert len(remaining) == 0


# ===================================================================
# 6. FIFO Ordering — All 12 Events
# ===================================================================


class TestFIFOOrdering:
    def test_outbox_preserves_insertion_order(self, outbox, session) -> None:
        events = [
            AgentCreated(agent_id=AgentId(), agent_type="coordinator", name="test", occurred_at=NOW),
            AgentActivated(agent_id=AgentId(), occurred_at=NOW),
            AgentPaused(agent_id=AgentId(), occurred_at=NOW),
            AgentDisabled(agent_id=AgentId(), occurred_at=NOW),
        ]
        for e in events:
            outbox.append(e)
        session.flush()
        entries = outbox.fetch_unpublished()
        assert len(entries) == 4
        for i, entry in enumerate(entries):
            assert type(entry) is type(events[i])

    def test_fifo_across_task_events(self, outbox, session) -> None:
        aid = AgentId()
        tid = AgentTaskId()
        events = [
            AgentTaskCreated(task_id=tid, agent_id=aid, goal="g", instruction="i", occurred_at=NOW),
            AgentTaskStarted(task_id=tid, agent_id=aid, occurred_at=NOW),
            AgentTaskCompleted(task_id=tid, agent_id=aid, result="done", occurred_at=NOW),
            AgentTaskFailed(task_id=tid, agent_id=aid, failure_reason="err", occurred_at=NOW),
            AgentTaskCancelled(task_id=tid, agent_id=aid, occurred_at=NOW),
        ]
        for e in events:
            outbox.append(e)
        session.flush()
        entries = outbox.fetch_unpublished()
        assert len(entries) == 5
        for i, entry in enumerate(entries):
            assert type(entry) is type(events[i])

    def test_fifo_across_execution_events(self, outbox, session) -> None:
        aid = AgentId()
        tid = AgentTaskId()
        eid = AgentExecutionId()
        events = [
            AgentExecutionStarted(execution_id=eid, agent_id=aid, task_id=tid, occurred_at=NOW),
            AgentExecutionCompleted(execution_id=eid, agent_id=aid, task_id=tid, result="done", occurred_at=NOW),
            AgentExecutionFailed(execution_id=eid, agent_id=aid, task_id=tid, failure_reason="err", occurred_at=NOW),
        ]
        for e in events:
            outbox.append(e)
        session.flush()
        entries = outbox.fetch_unpublished()
        assert len(entries) == 3
        for i, entry in enumerate(entries):
            assert type(entry) is type(events[i])

    def test_fifo_all_12_events(self, outbox, session) -> None:
        aid = AgentId()
        tid = AgentTaskId()
        eid = AgentExecutionId()
        events: list[AgentOutboxDomainEvent] = [
            AgentCreated(agent_id=aid, agent_type="coordinator", name="test", occurred_at=NOW),
            AgentActivated(agent_id=aid, occurred_at=NOW),
            AgentPaused(agent_id=aid, occurred_at=NOW),
            AgentDisabled(agent_id=aid, occurred_at=NOW),
            AgentTaskCreated(task_id=tid, agent_id=aid, goal="g", instruction="i", occurred_at=NOW),
            AgentTaskStarted(task_id=tid, agent_id=aid, occurred_at=NOW),
            AgentTaskCompleted(task_id=tid, agent_id=aid, result="done", occurred_at=NOW),
            AgentTaskFailed(task_id=tid, agent_id=aid, failure_reason="err", occurred_at=NOW),
            AgentTaskCancelled(task_id=tid, agent_id=aid, occurred_at=NOW),
            AgentExecutionStarted(execution_id=eid, agent_id=aid, task_id=tid, occurred_at=NOW),
            AgentExecutionCompleted(execution_id=eid, agent_id=aid, task_id=tid, result="done", occurred_at=NOW),
            AgentExecutionFailed(execution_id=eid, agent_id=aid, task_id=tid, failure_reason="err", occurred_at=NOW),
        ]
        for e in events:
            outbox.append(e)
        session.flush()
        entries = outbox.fetch_unpublished()
        assert len(entries) == 12
        for i, entry in enumerate(entries):
            assert type(entry) is type(events[i])


# ===================================================================
# 7. REST Contract Coverage — All 18 Routes
# ===================================================================


class TestRESTContractCoverage:
    def test_post_agents_201(self, client) -> None:
        resp = _create_agent_via_api(client)
        assert resp.status_code == 201

    def test_get_agents_200(self, client) -> None:
        resp = client.get("/api/v1/agent/")
        assert resp.status_code == 200

    def test_get_agent_by_id_200(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        resp = client.get(f"/api/v1/agent/{aid}")
        assert resp.status_code == 200
        assert resp.json()["agent_id"] == aid

    def test_get_agent_by_id_404(self, client) -> None:
        resp = client.get(f"/api/v1/agent/{uuid4()}")
        assert resp.status_code == 404

    def test_activate_agent_200(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        resp = client.post(f"/api/v1/agent/{aid}/activate")
        assert resp.status_code == 200

    def test_activate_agent_404(self, client) -> None:
        resp = client.post(f"/api/v1/agent/{uuid4()}/activate")
        assert resp.status_code == 404

    def test_pause_agent_200(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        client.post(f"/api/v1/agent/{aid}/activate")
        resp = client.post(f"/api/v1/agent/{aid}/pause")
        assert resp.status_code == 200

    def test_disable_agent_200(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        resp = client.post(f"/api/v1/agent/{aid}/disable")
        assert resp.status_code == 200

    def test_create_task_201(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        assert resp.status_code == 201

    def test_start_task_200(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        resp = client.post(f"/api/v1/agent/tasks/{tid}/start?agent_id={aid}")
        assert resp.status_code == 200

    def test_complete_task_200(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        client.post(f"/api/v1/agent/tasks/{tid}/start?agent_id={aid}")
        resp = client.post(
            f"/api/v1/agent/tasks/{tid}/complete",
            json={"agent_id": aid, "task_id": tid, "result": "done"},
        )
        assert resp.status_code == 200

    def test_fail_task_200(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        client.post(f"/api/v1/agent/tasks/{tid}/start?agent_id={aid}")
        resp = client.post(
            f"/api/v1/agent/tasks/{tid}/fail",
            json={"agent_id": aid, "task_id": tid, "failure_reason": "err"},
        )
        assert resp.status_code == 200

    def test_cancel_task_200(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        resp = client.post(f"/api/v1/agent/tasks/{tid}/cancel?agent_id={aid}")
        assert resp.status_code == 200

    def test_get_task_200(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        resp = client.get(f"/api/v1/agent/tasks/{tid}")
        assert resp.status_code == 200

    def test_list_tasks_200(self, client) -> None:
        resp = client.get("/api/v1/agent/tasks")
        assert resp.status_code == 200

    def test_start_execution_201(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        resp = client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        assert resp.status_code == 201

    def test_complete_execution_200(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        exec_resp = client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        eid = exec_resp.json()["execution_id"]
        resp = client.post(
            f"/api/v1/agent/executions/{eid}/complete",
            json={"agent_id": aid, "execution_id": eid, "result": "done"},
        )
        assert resp.status_code == 200

    def test_fail_execution_200(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        exec_resp = client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        eid = exec_resp.json()["execution_id"]
        resp = client.post(
            f"/api/v1/agent/executions/{eid}/fail",
            json={"agent_id": aid, "execution_id": eid, "failure_reason": "err"},
        )
        assert resp.status_code == 200

    def test_get_execution_200(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        exec_resp = client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        eid = exec_resp.json()["execution_id"]
        resp = client.get(f"/api/v1/agent/executions/{eid}")
        assert resp.status_code == 200

    def test_list_executions_200(self, client) -> None:
        resp = client.get("/api/v1/agent/executions")
        assert resp.status_code == 200

    def test_create_agent_empty_name_returns_400(self, client) -> None:
        resp = client.post("/api/v1/agent/", json={"name": ""})
        assert resp.status_code == 400

    def test_create_agent_invalid_type_returns_400(self, client) -> None:
        resp = client.post("/api/v1/agent/", json={"name": "Test", "agent_type": "invalid"})
        assert resp.status_code == 400

    def test_create_task_empty_goal_returns_400(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "", "instruction": "instr"},
        )
        assert resp.status_code == 400

    def test_create_task_empty_instruction_returns_400(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": ""},
        )
        assert resp.status_code == 400

    def test_complete_task_empty_result_returns_400(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        client.post(f"/api/v1/agent/tasks/{tid}/start?agent_id={aid}")
        resp = client.post(
            f"/api/v1/agent/tasks/{tid}/complete",
            json={"agent_id": aid, "task_id": tid, "result": ""},
        )
        assert resp.status_code == 400


# ===================================================================
# 8. Query Filtering
# ===================================================================


class TestQueryFiltering:
    def test_filter_agents_by_status(self, client) -> None:
        _create_agent_via_api(client)
        resp = client.get("/api/v1/agent/?status=idle")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_filter_agents_by_type(self, client) -> None:
        _create_agent_via_api(client)
        resp = client.get("/api/v1/agent/?agent_type=coordinator")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_filter_agents_by_invalid_status_returns_422(self, client) -> None:
        resp = client.get("/api/v1/agent/?status=nonexistent")
        assert resp.status_code == 422

    def test_filter_tasks_by_agent_id(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        resp = client.get(f"/api/v1/agent/tasks?agent_id={aid}")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_filter_tasks_by_status(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        resp = client.get("/api/v1/agent/tasks?status=pending")
        assert resp.status_code == 200

    def test_filter_tasks_by_agent_id_and_status(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        resp = client.get(f"/api/v1/agent/tasks?agent_id={aid}&status=pending")
        assert resp.status_code == 200

    def test_filter_executions_by_agent_id(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        resp = client.get(f"/api/v1/agent/executions?agent_id={aid}")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_filter_executions_by_task_id(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        resp = client.get(f"/api/v1/agent/executions?task_id={tid}")
        assert resp.status_code == 200

    def test_filter_executions_by_status(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        resp = client.get("/api/v1/agent/executions?status=executing")
        assert resp.status_code == 200


# ===================================================================
# 9. Event Coverage — All 12 Domain Events
# ===================================================================


class TestEventCoverage:
    def test_agent_created_event_type(self) -> None:
        assert AgentCreated in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[AgentCreated] == "agent_created"

    def test_agent_activated_event_type(self) -> None:
        assert AgentActivated in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[AgentActivated] == "agent_activated"

    def test_agent_paused_event_type(self) -> None:
        assert AgentPaused in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[AgentPaused] == "agent_paused"

    def test_agent_disabled_event_type(self) -> None:
        assert AgentDisabled in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[AgentDisabled] == "agent_disabled"

    def test_task_created_event_type(self) -> None:
        assert AgentTaskCreated in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[AgentTaskCreated] == "agent_task_created"

    def test_task_started_event_type(self) -> None:
        assert AgentTaskStarted in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[AgentTaskStarted] == "agent_task_started"

    def test_task_completed_event_type(self) -> None:
        assert AgentTaskCompleted in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[AgentTaskCompleted] == "agent_task_completed"

    def test_task_failed_event_type(self) -> None:
        assert AgentTaskFailed in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[AgentTaskFailed] == "agent_task_failed"

    def test_task_cancelled_event_type(self) -> None:
        assert AgentTaskCancelled in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[AgentTaskCancelled] == "agent_task_cancelled"

    def test_execution_started_event_type(self) -> None:
        assert AgentExecutionStarted in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[AgentExecutionStarted] == "agent_execution_started"

    def test_execution_completed_event_type(self) -> None:
        assert AgentExecutionCompleted in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[AgentExecutionCompleted] == "agent_execution_completed"

    def test_execution_failed_event_type(self) -> None:
        assert AgentExecutionFailed in _EVENT_TYPE_MAP
        assert _EVENT_TYPE_MAP[AgentExecutionFailed] == "agent_execution_failed"

    def test_all_12_events_have_nats_subject(self) -> None:
        assert len(_NATS_SUBJECT_MAP) == 12

    def test_all_events_have_event_type_in_nats_map(self) -> None:
        assert len(_EVENT_TYPE_MAP) == 12


# ===================================================================
# 10. API-to-Outbox Pipeline
# ===================================================================


class TestApiOutboxPipeline:
    def test_create_agent_publishes_event(self, client, session, outbox) -> None:
        resp = _create_agent_via_api(client)
        assert resp.status_code == 201
        session.flush()
        unpublished = outbox.fetch_unpublished()
        agent_created_events = [e for e in unpublished if isinstance(e, AgentCreated)]
        assert len(agent_created_events) == 1

    def test_activate_publishes_event(self, client, session, outbox) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        session.flush()
        outbox.fetch_unpublished()
        client.post(f"/api/v1/agent/{aid}/activate")
        session.flush()
        unpublished = outbox.fetch_unpublished()
        activated = [e for e in unpublished if isinstance(e, AgentActivated)]
        assert len(activated) == 1

    def test_pause_publishes_event(self, client, session, outbox) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        client.post(f"/api/v1/agent/{aid}/activate")
        session.flush()
        outbox.fetch_unpublished()
        client.post(f"/api/v1/agent/{aid}/pause")
        session.flush()
        unpublished = outbox.fetch_unpublished()
        paused = [e for e in unpublished if isinstance(e, AgentPaused)]
        assert len(paused) == 1

    def test_disable_publishes_event(self, client, session, outbox) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        session.flush()
        outbox.fetch_unpublished()
        client.post(f"/api/v1/agent/{aid}/disable")
        session.flush()
        unpublished = outbox.fetch_unpublished()
        disabled = [e for e in unpublished if isinstance(e, AgentDisabled)]
        assert len(disabled) == 1

    def test_create_task_publishes_event(self, client, session, outbox) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        session.flush()
        outbox.fetch_unpublished()
        client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        session.flush()
        unpublished = outbox.fetch_unpublished()
        task_created = [e for e in unpublished if isinstance(e, AgentTaskCreated)]
        assert len(task_created) == 1

    def test_start_task_publishes_event(self, client, session, outbox) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        session.flush()
        outbox.fetch_unpublished()
        client.post(f"/api/v1/agent/tasks/{tid}/start?agent_id={aid}")
        session.flush()
        unpublished = outbox.fetch_unpublished()
        started = [e for e in unpublished if isinstance(e, AgentTaskStarted)]
        assert len(started) == 1

    def test_complete_task_publishes_event(self, client, session, outbox) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        client.post(f"/api/v1/agent/tasks/{tid}/start?agent_id={aid}")
        session.flush()
        outbox.fetch_unpublished()
        client.post(
            f"/api/v1/agent/tasks/{tid}/complete",
            json={"agent_id": aid, "task_id": tid, "result": "done"},
        )
        session.flush()
        unpublished = outbox.fetch_unpublished()
        completed = [e for e in unpublished if isinstance(e, AgentTaskCompleted)]
        assert len(completed) == 1

    def test_fail_task_publishes_event(self, client, session, outbox) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        client.post(f"/api/v1/agent/tasks/{tid}/start?agent_id={aid}")
        session.flush()
        outbox.fetch_unpublished()
        client.post(
            f"/api/v1/agent/tasks/{tid}/fail",
            json={"agent_id": aid, "task_id": tid, "failure_reason": "err"},
        )
        session.flush()
        unpublished = outbox.fetch_unpublished()
        failed = [e for e in unpublished if isinstance(e, AgentTaskFailed)]
        assert len(failed) == 1

    def test_start_execution_publishes_event(self, client, session, outbox) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        session.flush()
        outbox.fetch_unpublished()
        client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        session.flush()
        unpublished = outbox.fetch_unpublished()
        started = [e for e in unpublished if isinstance(e, AgentExecutionStarted)]
        assert len(started) == 1

    def test_complete_execution_publishes_event(self, client, session, outbox) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        exec_resp = client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        eid = exec_resp.json()["execution_id"]
        session.flush()
        outbox.fetch_unpublished()
        client.post(
            f"/api/v1/agent/executions/{eid}/complete",
            json={"agent_id": aid, "execution_id": eid, "result": "done"},
        )
        session.flush()
        unpublished = outbox.fetch_unpublished()
        completed = [e for e in unpublished if isinstance(e, AgentExecutionCompleted)]
        assert len(completed) == 1

    def test_fail_execution_publishes_event(self, client, session, outbox) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        exec_resp = client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        eid = exec_resp.json()["execution_id"]
        session.flush()
        outbox.fetch_unpublished()
        client.post(
            f"/api/v1/agent/executions/{eid}/fail",
            json={"agent_id": aid, "execution_id": eid, "failure_reason": "err"},
        )
        session.flush()
        unpublished = outbox.fetch_unpublished()
        failed = [e for e in unpublished if isinstance(e, AgentExecutionFailed)]
        assert len(failed) == 1

    def test_full_lifecycle_produces_all_events(self, client, session, outbox) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        client.post(f"/api/v1/agent/{aid}/activate")
        client.post(f"/api/v1/agent/{aid}/pause")
        client.post(f"/api/v1/agent/{aid}/activate")
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        client.post(f"/api/v1/agent/tasks/{tid}/start?agent_id={aid}")
        exec_resp = client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        eid = exec_resp.json()["execution_id"]
        client.post(
            f"/api/v1/agent/executions/{eid}/complete",
            json={"agent_id": aid, "execution_id": eid, "result": "done"},
        )
        client.post(
            f"/api/v1/agent/tasks/{tid}/complete",
            json={"agent_id": aid, "task_id": tid, "result": "done"},
        )
        session.flush()
        unpublished = outbox.fetch_unpublished()
        types_found = {type(e).__name__ for e in unpublished}
        for expected in [
            "AgentCreated", "AgentActivated", "AgentPaused",
            "AgentTaskCreated", "AgentTaskStarted",
            "AgentExecutionStarted", "AgentExecutionCompleted",
            "AgentTaskCompleted",
        ]:
            assert expected in types_found, f"Missing event: {expected}"


# ===================================================================
# 11. Cross-Entity Validation
# ===================================================================


class TestCrossEntityValidation:
    def test_tasks_belong_to_agent(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        assert task_resp.json()["agent_id"] == aid

    def test_executions_belong_to_task(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        exec_resp = client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        assert exec_resp.json()["task_id"] == tid

    def test_tasks_isolation_between_agents(self, client) -> None:
        a1 = _create_agent_via_api(client, name="Agent A").json()
        a2 = _create_agent_via_api(client, name="Agent B").json()
        client.post(
            f"/api/v1/agent/{a1['agent_id']}/tasks",
            json={"agent_id": a1["agent_id"], "goal": "g1", "instruction": "i1"},
        )
        resp_a1 = client.get(f"/api/v1/agent/tasks?agent_id={a1['agent_id']}")
        assert resp_a1.json()["total"] == 1
        resp_a2 = client.get(f"/api/v1/agent/tasks?agent_id={a2['agent_id']}")
        assert resp_a2.json()["total"] == 0

    def test_disabled_agent_immutable(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        client.post(f"/api/v1/agent/{aid}/disable")
        resp = client.post(f"/api/v1/agent/{aid}/activate")
        assert resp.status_code == 400

    def test_nonexistent_agent_returns_404_for_all_routes(self, client) -> None:
        pid = str(uuid4())
        assert client.get(f"/api/v1/agent/{pid}").status_code == 404
        assert client.post(f"/api/v1/agent/{pid}/activate").status_code == 404
        assert client.post(f"/api/v1/agent/{pid}/pause").status_code == 404
        assert client.post(f"/api/v1/agent/{pid}/disable").status_code == 404
        assert client.post(
            f"/api/v1/agent/{pid}/tasks",
            json={"agent_id": pid, "goal": "g", "instruction": "i"},
        ).status_code == 404

    def test_agent_response_shape(self, client) -> None:
        resp = _create_agent_via_api(client)
        data = resp.json()
        assert "agent_id" in data
        assert "agent_type" in data
        assert "name" in data
        assert "status" in data
        assert "created_at" in data

    def test_task_response_shape(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        data = resp.json()
        assert "task_id" in data
        assert "agent_id" in data
        assert "goal" in data
        assert "status" in data

    def test_execution_response_shape(self, client) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        resp = client.post(f"/api/v1/agent/tasks/{tid}/executions?agent_id={aid}")
        data = resp.json()
        assert "execution_id" in data
        assert "agent_id" in data
        assert "task_id" in data
        assert "status" in data


# ===================================================================
# 12. NATS Pipeline Integration
# ===================================================================


class TestNatsPipeline:
    @pytest.mark.asyncio
    async def test_api_outbox_nats_full_pipeline(self, client, session, outbox, mock_js) -> None:
        resp = _create_agent_via_api(client)
        assert resp.status_code == 201
        session.flush()
        await publish_agent_outbox_events(
            mock_js, outbox=outbox, batch=10, interval_seconds=0.01, max_iterations=1,
        )
        assert mock_js.publish.await_count >= 1
        remaining = outbox.fetch_unpublished()
        assert len(remaining) == 0

    @pytest.mark.asyncio
    async def test_lifecycle_produces_nats_events(self, client, session, outbox, mock_js) -> None:
        created = _create_agent_via_api(client).json()
        aid = created["agent_id"]
        client.post(f"/api/v1/agent/{aid}/activate")
        task_resp = client.post(
            f"/api/v1/agent/{aid}/tasks",
            json={"agent_id": aid, "goal": "goal", "instruction": "instr"},
        )
        tid = task_resp.json()["task_id"]
        client.post(f"/api/v1/agent/tasks/{tid}/start?agent_id={aid}")
        session.flush()
        await publish_agent_outbox_events(
            mock_js, outbox=outbox, batch=10, interval_seconds=0.01, max_iterations=1,
        )
        assert mock_js.publish.await_count >= 3

    @pytest.mark.asyncio
    async def test_envelope_structure(self, client, session, outbox, mock_js) -> None:
        _create_agent_via_api(client)
        session.flush()
        await publish_agent_outbox_events(
            mock_js, outbox=outbox, batch=10, interval_seconds=0.01, max_iterations=1,
        )
        assert mock_js.publish.await_count >= 1
        call_args = mock_js.publish.await_args
        assert call_args is not None
        subject = call_args[0][0]
        assert subject.startswith("jarvis.agent.event.")
        assert subject.endswith(".v1")

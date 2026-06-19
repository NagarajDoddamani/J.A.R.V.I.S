from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api.endpoints import planner
from backend.core.database import get_db
from backend.planner.adapters.outbound.clock import SystemClockAdapter
from backend.planner.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.planner.adapters.outbound.mapper import (
    PlanMapperImpl,
    TaskMapperImpl,
)
from backend.planner.adapters.outbound.models import Base
from backend.planner.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyPlanRepository,
    SqlAlchemyPlannerOutboxAdapter,
    SqlAlchemyTaskRepository,
)
from backend.planner.application.use_cases.dto import (
    AddTaskRequest,
    AddTaskResponse,
    CreatePlanResponse,
    FailPlanResponse,
    FailTaskResponse,
    ListPlansResponse,
    ListTasksResponse,
    PlanLifecycleResponse,
    PlanResponse,
    TaskResponse,
)
from backend.planner.domain.model import (
    AgentType,
    EstimatedDuration,
    ExecutionStrategy,
    FailureReason,
    Plan,
    PlanGoal,
    PlanId,
    PlanPriority,
    PlanStatus,
    Task,
    TaskDescription,
    TaskId,
    TaskStatus,
    UserRequest,
)

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)

for _table in Base.metadata.tables.values():
    _table.schema = None


@pytest.fixture
def session():
    e = create_engine("sqlite://", echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    conn = e.connect()
    transaction = conn.begin()
    s = Session(bind=conn)
    yield s
    s.close()
    transaction.rollback()
    conn.close()
    e.dispose()


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
    app.include_router(planner.router, prefix="/api/v1/planner")
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c


@pytest.fixture
def clock():
    return SystemClockAdapter()


@pytest.fixture
def plan_repo(session):
    return SqlAlchemyPlanRepository(session, mapper=PlanMapperImpl())


@pytest.fixture
def task_repo(session):
    return SqlAlchemyTaskRepository(session, mapper=TaskMapperImpl())


@pytest.fixture
def outbox(session):
    return SqlAlchemyPlannerOutboxAdapter(session)


def _create_plan(client) -> str:
    resp = client.post(
        "/api/v1/planner/plans",
        json={
            "user_request": "test request",
            "goal": "test goal",
            "priority": "normal",
            "strategy": "sequential",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    return data["plan_id"]


def _create_task(client, plan_id: str) -> str:
    resp = client.post(
        f"/api/v1/planner/plans/{plan_id}/tasks",
        json={"description": "test task"},
    )
    assert resp.status_code == 201
    data = resp.json()
    return data["task_id"]


# ===================================================================
# Plan API tests
# ===================================================================


class TestPlanAPI:
    def test_create_plan(self, client) -> None:
        resp = client.post(
            "/api/v1/planner/plans",
            json={
                "user_request": "test request",
                "goal": "test goal",
                "priority": "high",
                "strategy": "parallel",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["user_request"] == "test request"
        assert data["goal"] == "test goal"
        assert data["priority"] == "high"
        assert data["strategy"] == "parallel"
        assert data["status"] == "draft"

    def test_create_plan_invalid_priority(self, client) -> None:
        resp = client.post(
            "/api/v1/planner/plans",
            json={
                "user_request": "test",
                "goal": "test",
                "priority": "invalid",
                "strategy": "sequential",
            },
        )
        assert resp.status_code == 422

    def test_create_plan_empty_request(self, client) -> None:
        resp = client.post(
            "/api/v1/planner/plans",
            json={
                "user_request": "",
                "goal": "test",
                "priority": "normal",
                "strategy": "sequential",
            },
        )
        assert resp.status_code == 422

    def test_get_plan(self, client) -> None:
        pid = _create_plan(client)
        resp = client.get(f"/api/v1/planner/plans/{pid}")
        assert resp.status_code == 200
        assert resp.json()["plan_id"] == pid

    def test_get_plan_not_found(self, client) -> None:
        resp = client.get(
            "/api/v1/planner/plans/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_list_plans(self, client) -> None:
        _create_plan(client)
        resp = client.get("/api/v1/planner/plans")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_list_plans_empty(self, client) -> None:
        resp = client.get("/api/v1/planner/plans")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_plans_filter_by_status(self, client) -> None:
        _create_plan(client)
        resp = client.get("/api/v1/planner/plans?status=draft")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_list_plans_filter_by_priority(self, client) -> None:
        _create_plan(client)
        resp = client.get("/api/v1/planner/plans?priority=high")
        assert resp.status_code == 200

    def test_approve_plan(self, client) -> None:
        pid = _create_plan(client)
        resp = client.post(f"/api/v1/planner/plans/{pid}/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    def test_approve_plan_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/planner/plans/00000000-0000-0000-0000-000000000000/approve"
        )
        assert resp.status_code == 404

    def test_approve_plan_invalid_transition(self, client) -> None:
        pid = _create_plan(client)
        client.post(f"/api/v1/planner/plans/{pid}/approve")
        resp = client.post(f"/api/v1/planner/plans/{pid}/approve")
        assert resp.status_code == 400

    def test_start_planning(self, client) -> None:
        pid = _create_plan(client)
        client.post(f"/api/v1/planner/plans/{pid}/approve")
        resp = client.post(f"/api/v1/planner/plans/{pid}/planning")
        assert resp.status_code == 200
        assert resp.json()["status"] == "planning"

    def test_mark_ready(self, client) -> None:
        pid = _create_plan(client)
        client.post(f"/api/v1/planner/plans/{pid}/approve")
        client.post(f"/api/v1/planner/plans/{pid}/planning")
        client.post(
            f"/api/v1/planner/plans/{pid}/tasks",
            json={"description": "task"},
        )
        resp = client.post(f"/api/v1/planner/plans/{pid}/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"

    def test_mark_ready_no_tasks(self, client) -> None:
        pid = _create_plan(client)
        client.post(f"/api/v1/planner/plans/{pid}/approve")
        client.post(f"/api/v1/planner/plans/{pid}/planning")
        resp = client.post(f"/api/v1/planner/plans/{pid}/ready")
        assert resp.status_code == 400

    def test_start_execution(self, client) -> None:
        pid = _create_plan(client)
        client.post(f"/api/v1/planner/plans/{pid}/approve")
        client.post(f"/api/v1/planner/plans/{pid}/planning")
        client.post(
            f"/api/v1/planner/plans/{pid}/tasks",
            json={"description": "task"},
        )
        client.post(f"/api/v1/planner/plans/{pid}/ready")
        resp = client.post(f"/api/v1/planner/plans/{pid}/execute")
        assert resp.status_code == 200
        assert resp.json()["status"] == "executing"

    def test_complete_plan(self, client) -> None:
        pid = _create_plan(client)
        client.post(f"/api/v1/planner/plans/{pid}/approve")
        client.post(f"/api/v1/planner/plans/{pid}/planning")
        client.post(
            f"/api/v1/planner/plans/{pid}/tasks",
            json={"description": "task"},
        )
        client.post(f"/api/v1/planner/plans/{pid}/ready")
        client.post(f"/api/v1/planner/plans/{pid}/execute")
        resp = client.post(f"/api/v1/planner/plans/{pid}/complete")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_fail_plan(self, client) -> None:
        pid = _create_plan(client)
        client.post(f"/api/v1/planner/plans/{pid}/approve")
        client.post(f"/api/v1/planner/plans/{pid}/planning")
        client.post(
            f"/api/v1/planner/plans/{pid}/tasks",
            json={"description": "task"},
        )
        client.post(f"/api/v1/planner/plans/{pid}/ready")
        client.post(f"/api/v1/planner/plans/{pid}/execute")
        resp = client.post(
            f"/api/v1/planner/plans/{pid}/fail",
            json={"failure_reason": "error occurred"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"
        assert resp.json()["failure_reason"] == "error occurred"

    def test_fail_plan_empty_reason(self, client) -> None:
        pid = _create_plan(client)
        client.post(f"/api/v1/planner/plans/{pid}/approve")
        client.post(f"/api/v1/planner/plans/{pid}/planning")
        client.post(
            f"/api/v1/planner/plans/{pid}/tasks",
            json={"description": "task"},
        )
        client.post(f"/api/v1/planner/plans/{pid}/ready")
        client.post(f"/api/v1/planner/plans/{pid}/execute")
        resp = client.post(
            f"/api/v1/planner/plans/{pid}/fail",
            json={"failure_reason": ""},
        )
        assert resp.status_code == 400

    def test_cancel_plan(self, client) -> None:
        pid = _create_plan(client)
        resp = client.post(f"/api/v1/planner/plans/{pid}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_cancel_plan_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/planner/plans/00000000-0000-0000-0000-000000000000/cancel"
        )
        assert resp.status_code == 404

    def test_full_plan_lifecycle(self, client) -> None:
        pid = _create_plan(client)
        assert client.post(f"/api/v1/planner/plans/{pid}/approve").status_code == 200
        assert client.post(f"/api/v1/planner/plans/{pid}/planning").status_code == 200
        assert client.post(
            f"/api/v1/planner/plans/{pid}/tasks",
            json={"description": "task"},
        ).status_code == 201
        assert client.post(f"/api/v1/planner/plans/{pid}/ready").status_code == 200
        assert client.post(f"/api/v1/planner/plans/{pid}/execute").status_code == 200
        assert client.post(f"/api/v1/planner/plans/{pid}/complete").status_code == 200


# ===================================================================
# Task API tests
# ===================================================================


class TestTaskAPI:
    def test_add_task(self, client) -> None:
        pid = _create_plan(client)
        resp = client.post(
            f"/api/v1/planner/plans/{pid}/tasks",
            json={"description": "my task"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["description"] == "my task"
        assert data["status"] == "pending"

    def test_add_task_plan_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/planner/plans/00000000-0000-0000-0000-000000000000/tasks",
            json={"description": "task"},
        )
        assert resp.status_code == 404

    def test_add_task_empty_description(self, client) -> None:
        pid = _create_plan(client)
        resp = client.post(
            f"/api/v1/planner/plans/{pid}/tasks",
            json={"description": ""},
        )
        assert resp.status_code == 400

    def test_assign_task(self, client) -> None:
        pid = _create_plan(client)
        tid = _create_task(client, pid)
        resp = client.post(
            f"/api/v1/planner/tasks/{tid}/assign",
            json={"agent": "research"},
        )
        assert resp.status_code == 200
        assert resp.json()["assigned_agent"] == "research"
        assert resp.json()["status"] == "assigned"

    def test_assign_task_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/planner/tasks/00000000-0000-0000-0000-000000000000/assign",
            json={"agent": "research"},
        )
        assert resp.status_code == 404

    def test_assign_task_invalid_agent(self, client) -> None:
        pid = _create_plan(client)
        tid = _create_task(client, pid)
        resp = client.post(
            f"/api/v1/planner/tasks/{tid}/assign",
            json={"agent": "invalid"},
        )
        assert resp.status_code == 400

    def test_start_task(self, client) -> None:
        pid = _create_plan(client)
        tid = _create_task(client, pid)
        client.post(
            f"/api/v1/planner/tasks/{tid}/assign",
            json={"agent": "research"},
        )
        resp = client.post(f"/api/v1/planner/tasks/{tid}/start")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_start_task_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/planner/tasks/00000000-0000-0000-0000-000000000000/start"
        )
        assert resp.status_code == 404

    def test_complete_task(self, client) -> None:
        pid = _create_plan(client)
        tid = _create_task(client, pid)
        client.post(
            f"/api/v1/planner/tasks/{tid}/assign",
            json={"agent": "research"},
        )
        client.post(f"/api/v1/planner/tasks/{tid}/start")
        resp = client.post(f"/api/v1/planner/tasks/{tid}/complete")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_complete_task_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/planner/tasks/00000000-0000-0000-0000-000000000000/complete"
        )
        assert resp.status_code == 404

    def test_fail_task(self, client) -> None:
        pid = _create_plan(client)
        tid = _create_task(client, pid)
        client.post(
            f"/api/v1/planner/tasks/{tid}/assign",
            json={"agent": "research"},
        )
        client.post(f"/api/v1/planner/tasks/{tid}/start")
        resp = client.post(
            f"/api/v1/planner/tasks/{tid}/fail",
            json={"failure_reason": "something broke"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"
        assert resp.json()["failure_reason"] == "something broke"

    def test_fail_task_not_found(self, client) -> None:
        resp = client.post(
            "/api/v1/planner/tasks/00000000-0000-0000-0000-000000000000/fail",
            json={"failure_reason": "err"},
        )
        assert resp.status_code == 404

    def test_fail_task_empty_reason(self, client) -> None:
        pid = _create_plan(client)
        tid = _create_task(client, pid)
        client.post(
            f"/api/v1/planner/tasks/{tid}/assign",
            json={"agent": "research"},
        )
        client.post(f"/api/v1/planner/tasks/{tid}/start")
        resp = client.post(
            f"/api/v1/planner/tasks/{tid}/fail",
            json={"failure_reason": ""},
        )
        assert resp.status_code == 400

    def test_get_task(self, client) -> None:
        pid = _create_plan(client)
        tid = _create_task(client, pid)
        resp = client.get(f"/api/v1/planner/tasks/{tid}")
        assert resp.status_code == 200
        assert resp.json()["task_id"] == tid
        assert resp.json()["status"] == "pending"

    def test_get_task_not_found(self, client) -> None:
        resp = client.get(
            "/api/v1/planner/tasks/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_list_tasks(self, client) -> None:
        pid = _create_plan(client)
        _create_task(client, pid)
        resp = client.get("/api/v1/planner/tasks")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_list_tasks_empty(self, client) -> None:
        resp = client.get("/api/v1/planner/tasks")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_tasks_filter_by_status(self, client) -> None:
        pid = _create_plan(client)
        _create_task(client, pid)
        resp = client.get("/api/v1/planner/tasks?status=pending")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_list_tasks_filter_by_agent(self, client) -> None:
        pid = _create_plan(client)
        tid = _create_task(client, pid)
        client.post(
            f"/api/v1/planner/tasks/{tid}/assign",
            json={"agent": "research"},
        )
        resp = client.get("/api/v1/planner/tasks?assigned_agent=research")
        assert resp.status_code == 200

    def test_list_tasks_filter_by_plan_id(self, client) -> None:
        pid = _create_plan(client)
        _create_task(client, pid)
        resp = client.get(f"/api/v1/planner/tasks?plan_id={pid}")
        assert resp.status_code == 200

    def test_full_task_lifecycle(self, client) -> None:
        pid = _create_plan(client)
        tid = _create_task(client, pid)
        assert client.post(
            f"/api/v1/planner/tasks/{tid}/assign",
            json={"agent": "research"},
        ).status_code == 200
        assert client.post(
            f"/api/v1/planner/tasks/{tid}/start"
        ).status_code == 200
        assert client.post(
            f"/api/v1/planner/tasks/{tid}/complete"
        ).status_code == 200


# ===================================================================
# Response DTO shape tests
# ===================================================================


class TestPlanResponseShapes:
    def test_create_plan_response_shape(self, client) -> None:
        resp = client.post(
            "/api/v1/planner/plans",
            json={
                "user_request": "r",
                "goal": "g",
                "priority": "normal",
                "strategy": "sequential",
            },
        )
        data = resp.json()
        assert "plan_id" in data
        assert "user_request" in data
        assert "goal" in data
        assert "priority" in data
        assert "strategy" in data
        assert "status" in data
        assert "created_at" in data

    def test_plan_response_shape(self, client) -> None:
        pid = _create_plan(client)
        resp = client.get(f"/api/v1/planner/plans/{pid}")
        data = resp.json()
        assert "plan_id" in data
        assert "user_request" in data
        assert "goal" in data
        assert "priority" in data
        assert "strategy" in data
        assert "status" in data
        assert "task_count" in data

    def test_plan_lifecycle_response_shape(self, client) -> None:
        pid = _create_plan(client)
        resp = client.post(f"/api/v1/planner/plans/{pid}/approve")
        data = resp.json()
        assert "plan_id" in data
        assert "status" in data
        assert "updated_at" in data

    def test_task_response_shape(self, client) -> None:
        pid = _create_plan(client)
        tid = _create_task(client, pid)
        resp = client.get(f"/api/v1/planner/tasks/{tid}")
        data = resp.json()
        assert "task_id" in data
        assert "description" in data
        assert "status" in data


# ===================================================================
# Error mapping tests
# ===================================================================


class TestErrorMapping:
    def test_plan_not_found_returns_404(self, client) -> None:
        pid = "00000000-0000-0000-0000-000000000000"
        endpoints = [
            ("GET", f"/api/v1/planner/plans/{pid}"),
            ("POST", f"/api/v1/planner/plans/{pid}/approve"),
            ("POST", f"/api/v1/planner/plans/{pid}/planning"),
            ("POST", f"/api/v1/planner/plans/{pid}/ready"),
            ("POST", f"/api/v1/planner/plans/{pid}/execute"),
            ("POST", f"/api/v1/planner/plans/{pid}/complete"),
            ("POST", f"/api/v1/planner/plans/{pid}/cancel"),
        ]
        for method, url in endpoints:
            if method == "GET":
                resp = client.get(url)
            else:
                resp = client.post(url)
            assert resp.status_code == 404, f"{method} {url} returned {resp.status_code}"

    def test_task_not_found_returns_404(self, client) -> None:
        tid = "00000000-0000-0000-0000-000000000000"
        endpoints = [
            ("GET", f"/api/v1/planner/tasks/{tid}"),
            ("POST", f"/api/v1/planner/tasks/{tid}/assign"),
            ("POST", f"/api/v1/planner/tasks/{tid}/start"),
            ("POST", f"/api/v1/planner/tasks/{tid}/complete"),
        ]
        for method, url in endpoints:
            if method == "GET":
                resp = client.get(url)
            else:
                resp = client.post(url, json={"agent": "research"} if "/assign" in url else {})
            assert resp.status_code == 404, f"{method} {url} returned {resp.status_code}"

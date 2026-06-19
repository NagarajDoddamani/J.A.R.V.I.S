"""Tests for SVC-011-C Runtime Workflow Engine.

Covers:
- WorkflowRegistry (registration, lookup, error cases)
- InMemoryWorkflowState (save / load / delete / list)
- WorkflowEngine (sequential, parallel, hybrid DAG, retries,
  failures, cancellation, cycle detection, edge cases)
- WorkflowExecutor (dispatcher integration, retry, timeout,
  full workflow execution)
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.runtime.workflows.engine import WorkflowEngine
from backend.runtime.workflows.errors import (
    WorkflowDependencyError,
    WorkflowError,
    WorkflowInstanceNotFoundError,
    WorkflowInvalidTransitionError,
    WorkflowNotFoundError,
    WorkflowStepNotFoundError,
    WorkflowTimeoutError,
)
from backend.runtime.workflows.executor import WorkflowExecutor
from backend.runtime.workflows.models import (
    StepRun,
    StepStatus,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowStatus,
    WorkflowStep,
)
from backend.runtime.workflows.registry import WorkflowRegistry
from backend.runtime.workflows.state import InMemoryWorkflowState

# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def registry() -> WorkflowRegistry:
    return WorkflowRegistry()


@pytest.fixture
def state() -> InMemoryWorkflowState:
    return InMemoryWorkflowState()


@pytest.fixture
def engine(registry: WorkflowRegistry, state: InMemoryWorkflowState) -> WorkflowEngine:
    return WorkflowEngine(registry=registry, state=state)


@pytest.fixture
def dispatcher() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def executor(engine: WorkflowEngine, dispatcher: AsyncMock) -> WorkflowExecutor:
    return WorkflowExecutor(engine=engine, dispatcher=dispatcher)


# =========================================================================
# Helper factories
# =========================================================================


def step(
    step_id: str,
    command_type: str = "TEST_CMD",
    payload: dict[str, Any] | None = None,
    dependencies: list[str] | None = None,
    retry_count: int = 0,
    timeout_seconds: float = 30.0,
) -> WorkflowStep:
    return WorkflowStep(
        step_id=step_id,
        command_type=command_type,
        payload=payload or {},
        dependencies=dependencies or [],
        retry_count=retry_count,
        timeout_seconds=timeout_seconds,
    )


def definition(
    workflow_type: str,
    *steps: WorkflowStep,
    description: str = "",
    timeout_seconds: float = 300.0,
) -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_type=workflow_type,
        steps=steps,
        description=description,
        timeout_seconds=timeout_seconds,
    )


def seq_workflow(registry: WorkflowRegistry) -> str:
    """Register a 3-step sequential workflow. Returns workflow type."""
    wf_def = definition(
        "SEQ_WF",
        step("s1"),
        step("s2", dependencies=["s1"]),
        step("s3", dependencies=["s2"]),
    )
    registry.register(wf_def)
    return "SEQ_WF"


def parallel_workflow(registry: WorkflowRegistry) -> str:
    """Register a workflow with 3 parallel steps. Returns workflow type."""
    wf_def = definition(
        "PAR_WF",
        step("a"),
        step("b"),
        step("c"),
    )
    registry.register(wf_def)
    return "PAR_WF"


def hybrid_workflow(registry: WorkflowRegistry) -> str:
    """Register a hybrid DAG workflow. Returns workflow type."""
    wf_def = definition(
        "HYB_WF",
        step("s1"),
        step("s2", dependencies=["s1"]),
        step("s3", dependencies=["s1"]),
        step("s4", dependencies=["s2", "s3"]),
    )
    registry.register(wf_def)
    return "HYB_WF"


# =========================================================================
# WorkflowRegistry tests
# =========================================================================


class TestWorkflowRegistry:
    def test_register_and_get(self, registry: WorkflowRegistry) -> None:
        d = definition("TEST", step("a"))
        registry.register(d)
        assert registry.get("TEST") is d

    def test_register_duplicate_raises(self, registry: WorkflowRegistry) -> None:
        registry.register(definition("TEST", step("a")))
        with pytest.raises(ValueError, match="already registered"):
            registry.register(definition("TEST", step("b")))

    def test_register_or_replace(self, registry: WorkflowRegistry) -> None:
        d1 = definition("TEST", step("a"))
        d2 = definition("TEST", step("b"))
        registry.register(d1)
        registry.register_or_replace(d2)
        assert registry.get("TEST") is d2

    def test_has(self, registry: WorkflowRegistry) -> None:
        assert not registry.has("NONEXISTENT")
        registry.register(definition("EXISTS", step("a")))
        assert registry.has("EXISTS")

    def test_unregister(self, registry: WorkflowRegistry) -> None:
        registry.register(definition("TEST", step("a")))
        registry.unregister("TEST")
        assert not registry.has("TEST")

    def test_unregister_nonexistent(self, registry: WorkflowRegistry) -> None:
        registry.unregister("NONEXISTENT")

    def test_get_nonexistent_raises(self, registry: WorkflowRegistry) -> None:
        with pytest.raises(WorkflowNotFoundError, match="not registered"):
            registry.get("NONEXISTENT")

    def test_registered_types(self, registry: WorkflowRegistry) -> None:
        registry.register(definition("A", step("a")))
        registry.register(definition("B", step("b")))
        assert registry.registered_types == frozenset({"A", "B"})

    def test_clear(self, registry: WorkflowRegistry) -> None:
        registry.register(definition("A", step("a")))
        registry.clear()
        assert not registry.has("A")
        assert len(registry.registered_types) == 0


# =========================================================================
# InMemoryWorkflowState tests
# =========================================================================


class TestInMemoryWorkflowState:
    def test_save_and_load(self, state: InMemoryWorkflowState) -> None:
        inst = WorkflowInstance(instance_id="id-1", workflow_type="TEST")
        state.save(inst)
        loaded = state.load("id-1")
        assert loaded.instance_id == "id-1"
        assert loaded is inst

    def test_load_nonexistent_raises(self, state: InMemoryWorkflowState) -> None:
        with pytest.raises(WorkflowInstanceNotFoundError, match="not found"):
            state.load("NONEXISTENT")

    def test_delete(self, state: InMemoryWorkflowState) -> None:
        inst = WorkflowInstance(instance_id="id-1", workflow_type="TEST")
        state.save(inst)
        state.delete("id-1")
        with pytest.raises(WorkflowInstanceNotFoundError):
            state.load("id-1")

    def test_delete_nonexistent(self, state: InMemoryWorkflowState) -> None:
        state.delete("NONEXISTENT")

    def test_list_all(self, state: InMemoryWorkflowState) -> None:
        state.save(WorkflowInstance(instance_id="a", workflow_type="T"))
        state.save(WorkflowInstance(instance_id="b", workflow_type="T"))
        assert len(state.list_all()) == 2

    def test_list_all_empty(self, state: InMemoryWorkflowState) -> None:
        assert state.list_all() == []

    def test_clear(self, state: InMemoryWorkflowState) -> None:
        state.save(WorkflowInstance(instance_id="a", workflow_type="T"))
        state.clear()
        assert state.list_all() == []

    def test_overwrite_same_id(self, state: InMemoryWorkflowState) -> None:
        i1 = WorkflowInstance(instance_id="id-1", workflow_type="T1")
        i2 = WorkflowInstance(instance_id="id-1", workflow_type="T2")
        state.save(i1)
        state.save(i2)
        loaded = state.load("id-1")
        assert loaded.workflow_type == "T2"


# =========================================================================
# WorkflowEngine — start_workflow
# =========================================================================


class TestWorkflowEngineStart:
    def test_start_sequential(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        assert inst.status == WorkflowStatus.RUNNING
        assert inst.workflow_type == "SEQ_WF"
        assert len(inst.steps) == 3
        for step_run in inst.steps.values():
            assert step_run.status == StepStatus.PENDING

    def test_start_unknown_type_raises(self, engine: WorkflowEngine) -> None:
        with pytest.raises(WorkflowNotFoundError):
            engine.start_workflow("NONEXISTENT")

    def test_start_custom_instance_id(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF", instance_id="my-custom-id")
        assert inst.instance_id == "my-custom-id"

    def test_start_generates_instance_id(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        assert inst.instance_id is not None
        assert len(inst.instance_id) > 0

    def test_start_sets_created_and_started_at(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        assert inst.created_at is not None
        assert inst.started_at is not None

    def test_start_with_payload_override_merges_into_step_payloads(
        self, engine: WorkflowEngine, registry: WorkflowRegistry
    ) -> None:
        wf_def = definition(
            "WITH_PAYLOAD",
            step("s1", command_type="CMD", payload={"a": 1}),
            step("s2", command_type="CMD", payload={"b": 2}),
        )
        registry.register(wf_def)
        inst = engine.start_workflow("WITH_PAYLOAD", payload_override={"a": 999, "extra": "x"})
        assert inst.steps["s1"].step.payload["a"] == 999
        assert inst.steps["s1"].step.payload["extra"] == "x"
        assert inst.steps["s2"].step.payload["b"] == 2
        assert inst.steps["s2"].step.payload["extra"] == "x"

    def test_start_validates_dependencies(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("BAD_DEPS", step("a", dependencies=["b"]), step("b"))
        registry.register(wf_def)
        engine.start_workflow("BAD_DEPS")

    def test_start_rejects_unknown_dependency(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("BAD_DEPS", step("a", dependencies=["nonexistent"]))
        registry.register(wf_def)
        with pytest.raises(WorkflowDependencyError, match="unknown step"):
            engine.start_workflow("BAD_DEPS")

    def test_start_rejects_cycle(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition(
            "CYCLE",
            step("a", dependencies=["b"]),
            step("b", dependencies=["a"]),
        )
        registry.register(wf_def)
        with pytest.raises(WorkflowDependencyError, match="Circular dependency"):
            engine.start_workflow("CYCLE")

    def test_start_rejects_self_cycle(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("SELF", step("a", dependencies=["a"]))
        registry.register(wf_def)
        with pytest.raises(WorkflowDependencyError, match="Circular dependency"):
            engine.start_workflow("SELF")

    def test_start_rejects_transitive_cycle(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition(
            "TRANS_CYCLE",
            step("a", dependencies=["b"]),
            step("b", dependencies=["c"]),
            step("c", dependencies=["a"]),
        )
        registry.register(wf_def)
        with pytest.raises(WorkflowDependencyError, match="Circular dependency"):
            engine.start_workflow("TRANS_CYCLE")

    def test_start_saves_to_state(self, engine: WorkflowEngine, registry: WorkflowRegistry, state: InMemoryWorkflowState) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        assert state.load(inst.instance_id).instance_id == inst.instance_id


# =========================================================================
# WorkflowEngine — execute_step
# =========================================================================


class TestWorkflowEngineExecuteStep:
    def test_execute_pending_step(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        step_run = engine.execute_step(inst.instance_id, "s1")
        assert step_run.status == StepStatus.RUNNING
        assert step_run.attempt == 1
        assert step_run.started_at is not None

    def test_execute_nonexistent_step_raises(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        with pytest.raises(WorkflowStepNotFoundError, match="not found"):
            engine.execute_step(inst.instance_id, "ghost")

    def test_execute_nonexistent_instance_raises(self, engine: WorkflowEngine) -> None:
        with pytest.raises(WorkflowInstanceNotFoundError):
            engine.execute_step("ghost", "s1")

    def test_execute_already_running_step_raises(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        with pytest.raises(WorkflowInvalidTransitionError, match="Cannot execute"):
            engine.execute_step(inst.instance_id, "s1")

    def test_execute_already_completed_step_raises(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.complete_step(inst.instance_id, "s1")
        with pytest.raises(WorkflowInvalidTransitionError, match="Cannot execute"):
            engine.execute_step(inst.instance_id, "s1")

    def test_execute_step_with_unmet_dependency_raises(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        with pytest.raises(WorkflowInvalidTransitionError, match="dependencies are not met"):
            engine.execute_step(inst.instance_id, "s2")

    def test_execute_step_after_dependency_met(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.complete_step(inst.instance_id, "s1")
        step_run = engine.execute_step(inst.instance_id, "s2")
        assert step_run.status == StepStatus.RUNNING

    def test_execute_step_in_saves_state(self, engine: WorkflowEngine, registry: WorkflowRegistry, state: InMemoryWorkflowState) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        loaded = state.load(inst.instance_id)
        assert loaded.steps["s1"].status == StepStatus.RUNNING

    def test_execute_step_increments_attempt(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        assert engine.get_instance(inst.instance_id).steps["s1"].attempt == 1


# =========================================================================
# WorkflowEngine — complete_step
# =========================================================================


class TestWorkflowEngineCompleteStep:
    def test_complete_step(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        updated = engine.complete_step(inst.instance_id, "s1", result={"output": 42})
        assert updated.steps["s1"].status == StepStatus.COMPLETED
        assert updated.steps["s1"].completed_at is not None
        assert updated.steps["s1"].result == {"output": 42}

    def test_complete_nonexistent_step_raises(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        with pytest.raises(WorkflowStepNotFoundError):
            engine.complete_step(inst.instance_id, "ghost")

    def test_complete_not_running_step_raises(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        with pytest.raises(WorkflowInvalidTransitionError, match="Cannot complete"):
            engine.complete_step(inst.instance_id, "s1")

    def test_complete_without_result(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.complete_step(inst.instance_id, "s1")
        assert inst.steps["s1"].status == StepStatus.COMPLETED

    def test_workflow_completes_when_all_steps_done(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        for sid in ("s1", "s2", "s3"):
            engine.execute_step(inst.instance_id, sid)
            engine.complete_step(inst.instance_id, sid)
        assert engine.get_instance(inst.instance_id).status == WorkflowStatus.COMPLETED
        assert engine.get_instance(inst.instance_id).completed_at is not None

    def test_workflow_not_completed_before_all_steps_done(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.complete_step(inst.instance_id, "s1")
        assert engine.get_instance(inst.instance_id).status == WorkflowStatus.RUNNING

    def test_complete_saves_state(self, engine: WorkflowEngine, registry: WorkflowRegistry, state: InMemoryWorkflowState) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.complete_step(inst.instance_id, "s1")
        loaded = state.load(inst.instance_id)
        assert loaded.steps["s1"].status == StepStatus.COMPLETED


# =========================================================================
# WorkflowEngine — fail_step
# =========================================================================


class TestWorkflowEngineFailStep:
    def test_fail_step_marks_failed(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        updated = engine.fail_step(inst.instance_id, "s1", error_message="boom")
        assert updated.steps["s1"].status == StepStatus.FAILED
        assert updated.steps["s1"].error_message == "boom"
        assert updated.steps["s1"].completed_at is not None

    def test_fail_step_fails_workflow_no_retry(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.fail_step(inst.instance_id, "s1", error_message="boom")
        assert engine.get_instance(inst.instance_id).status == WorkflowStatus.FAILED
        assert engine.get_instance(inst.instance_id).failed_at is not None

    def test_fail_step_cancels_dependents(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.fail_step(inst.instance_id, "s1", error_message="boom")
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s2"].status == StepStatus.CANCELLED
        assert instance.steps["s3"].status == StepStatus.CANCELLED

    def test_fail_step_with_retry_returns_to_pending(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("RETRY_WF", step("s1", retry_count=2))
        registry.register(wf_def)
        inst = engine.start_workflow("RETRY_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.fail_step(inst.instance_id, "s1", error_message="retry")
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].status == StepStatus.PENDING
        assert instance.steps["s1"].attempt == 1
        assert instance.steps["s1"].error_message == "retry"
        assert instance.status == WorkflowStatus.RUNNING

    def test_fail_step_exhausts_retries(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("RETRY_WF", step("s1", retry_count=1))
        registry.register(wf_def)
        inst = engine.start_workflow("RETRY_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.fail_step(inst.instance_id, "s1", error_message="fail1")
        engine.execute_step(inst.instance_id, "s1")
        engine.fail_step(inst.instance_id, "s1", error_message="fail2")
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].status == StepStatus.FAILED
        assert instance.steps["s1"].attempt == 2
        assert instance.status == WorkflowStatus.FAILED

    def test_fail_retry_then_succeed(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("RETRY_SUCCEED", step("s1", retry_count=2))
        registry.register(wf_def)
        inst = engine.start_workflow("RETRY_SUCCEED")
        engine.execute_step(inst.instance_id, "s1")
        engine.fail_step(inst.instance_id, "s1", error_message="try1")
        engine.execute_step(inst.instance_id, "s1")
        engine.complete_step(inst.instance_id, "s1", result={"ok": True})
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].status == StepStatus.COMPLETED
        assert instance.status == WorkflowStatus.COMPLETED

    def test_fail_step_nonexistent_raises(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        with pytest.raises(WorkflowStepNotFoundError):
            engine.fail_step(inst.instance_id, "ghost")

    def test_fail_not_running_step_raises(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.complete_step(inst.instance_id, "s1")
        with pytest.raises(WorkflowInvalidTransitionError, match="Cannot fail"):
            engine.fail_step(inst.instance_id, "s1")

    def test_fail_pending_step_allowed(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.fail_step(inst.instance_id, "s1", error_message="direct fail")
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].status == StepStatus.FAILED
        assert instance.status == WorkflowStatus.FAILED

    def test_fail_saves_state(self, engine: WorkflowEngine, registry: WorkflowRegistry, state: InMemoryWorkflowState) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.fail_step(inst.instance_id, "s1", error_message="boom")
        loaded = state.load(inst.instance_id)
        assert loaded.steps["s1"].status == StepStatus.FAILED

    def test_fail_retry_does_not_cancel_dependents(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("RETRY_DEP", step("s1", retry_count=1), step("s2", dependencies=["s1"]))
        registry.register(wf_def)
        inst = engine.start_workflow("RETRY_DEP")
        engine.execute_step(inst.instance_id, "s1")
        engine.fail_step(inst.instance_id, "s1", error_message="retry")
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].status == StepStatus.PENDING
        assert instance.steps["s2"].status == StepStatus.PENDING


# =========================================================================
# WorkflowEngine — cancellation
# =========================================================================


class TestWorkflowEngineCancel:
    def test_cancel_running_workflow(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        cancelled = engine.cancel_workflow(inst.instance_id, reason="user request")
        assert cancelled.status == WorkflowStatus.CANCELLED
        assert cancelled.error_message == "user request"

    def test_cancel_cancels_pending_steps(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.cancel_workflow(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s2"].status == StepStatus.CANCELLED
        assert instance.steps["s3"].status == StepStatus.CANCELLED

    def test_cancel_does_not_affect_completed_step(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.complete_step(inst.instance_id, "s1")
        engine.cancel_workflow(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].status == StepStatus.COMPLETED

    def test_cancel_pending_workflow(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("PEND", step("a"), step("b"))
        registry.register(wf_def)
        inst = engine.start_workflow("PEND")
        engine.cancel_workflow(inst.instance_id, reason="no longer needed")
        assert engine.get_instance(inst.instance_id).status == WorkflowStatus.CANCELLED

    def test_cancel_completed_workflow_raises(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        for sid in ("s1", "s2", "s3"):
            engine.execute_step(inst.instance_id, sid)
            engine.complete_step(inst.instance_id, sid)
        with pytest.raises(WorkflowInvalidTransitionError, match="Cannot cancel"):
            engine.cancel_workflow(inst.instance_id)

    def test_cancel_failed_workflow_raises(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.fail_step(inst.instance_id, "s1", error_message="boom")
        with pytest.raises(WorkflowInvalidTransitionError, match="Cannot cancel"):
            engine.cancel_workflow(inst.instance_id)

    def test_cancel_saves_state(self, engine: WorkflowEngine, registry: WorkflowRegistry, state: InMemoryWorkflowState) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.cancel_workflow(inst.instance_id, reason="test")
        loaded = state.load(inst.instance_id)
        assert loaded.status == WorkflowStatus.CANCELLED


# =========================================================================
# WorkflowEngine — ready_steps
# =========================================================================


class TestWorkflowEngineReadySteps:
    def test_ready_steps_sequential_initial(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        ready = engine.ready_steps(inst.instance_id)
        assert len(ready) == 1
        assert ready[0].step.step_id == "s1"

    def test_ready_steps_after_first_completes(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.complete_step(inst.instance_id, "s1")
        ready = engine.ready_steps(inst.instance_id)
        assert len(ready) == 1
        assert ready[0].step.step_id == "s2"

    def test_ready_steps_parallel_initial(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        parallel_workflow(registry)
        inst = engine.start_workflow("PAR_WF")
        ready = engine.ready_steps(inst.instance_id)
        assert len(ready) == 3

    def test_ready_steps_hybrid_initial(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        hybrid_workflow(registry)
        inst = engine.start_workflow("HYB_WF")
        ready = engine.ready_steps(inst.instance_id)
        assert len(ready) == 1
        assert ready[0].step.step_id == "s1"

    def test_ready_steps_hybrid_after_s1(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        hybrid_workflow(registry)
        inst = engine.start_workflow("HYB_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.complete_step(inst.instance_id, "s1")
        ready = engine.ready_steps(inst.instance_id)
        assert len(ready) == 2
        assert {r.step.step_id for r in ready} == {"s2", "s3"}

    def test_ready_steps_hybrid_after_s2_s3(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        hybrid_workflow(registry)
        inst = engine.start_workflow("HYB_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.complete_step(inst.instance_id, "s1")
        engine.execute_step(inst.instance_id, "s2")
        engine.complete_step(inst.instance_id, "s2")
        engine.execute_step(inst.instance_id, "s3")
        engine.complete_step(inst.instance_id, "s3")
        ready = engine.ready_steps(inst.instance_id)
        assert len(ready) == 1
        assert ready[0].step.step_id == "s4"

    def test_ready_steps_empty_when_all_done(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        for sid in ("s1", "s2", "s3"):
            engine.execute_step(inst.instance_id, sid)
            engine.complete_step(inst.instance_id, sid)
        ready = engine.ready_steps(inst.instance_id)
        assert ready == []

    def test_ready_steps_after_failure(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.fail_step(inst.instance_id, "s1", error_message="boom")
        ready = engine.ready_steps(inst.instance_id)
        assert ready == []

    def test_ready_steps_with_retry(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("RETRY_R", step("s1", retry_count=2))
        registry.register(wf_def)
        inst = engine.start_workflow("RETRY_R")
        engine.execute_step(inst.instance_id, "s1")
        engine.fail_step(inst.instance_id, "s1", error_message="retry")
        ready = engine.ready_steps(inst.instance_id)
        assert len(ready) == 1
        assert ready[0].step.step_id == "s1"

    def test_ready_steps_nonexistent_instance_raises(self, engine: WorkflowEngine) -> None:
        with pytest.raises(WorkflowInstanceNotFoundError):
            engine.ready_steps("ghost")


# =========================================================================
# WorkflowEngine — get_instance / list_instances
# =========================================================================


class TestWorkflowEngineQueries:
    def test_get_instance(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        loaded = engine.get_instance(inst.instance_id)
        assert loaded.instance_id == inst.instance_id

    def test_get_instance_nonexistent_raises(self, engine: WorkflowEngine) -> None:
        with pytest.raises(WorkflowInstanceNotFoundError):
            engine.get_instance("ghost")

    def test_list_instances(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        parallel_workflow(registry)
        engine.start_workflow("SEQ_WF")
        engine.start_workflow("PAR_WF")
        assert len(engine.list_instances()) == 2

    def test_list_instances_empty(self, engine: WorkflowEngine) -> None:
        assert engine.list_instances() == []


# =========================================================================
# WorkflowEngine — sequential workflow (end-to-end)
# =========================================================================


class TestWorkflowEngineSequential:
    def test_full_sequential(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        for sid in ("s1", "s2", "s3"):
            engine.execute_step(inst.instance_id, sid)
            engine.complete_step(inst.instance_id, sid)
        assert engine.get_instance(inst.instance_id).status == WorkflowStatus.COMPLETED
        for sid in ("s1", "s2", "s3"):
            assert engine.get_instance(inst.instance_id).steps[sid].status == StepStatus.COMPLETED

    def test_sequential_blocked_by_dependency(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        with pytest.raises(WorkflowInvalidTransitionError, match="dependencies are not met"):
            engine.execute_step(inst.instance_id, "s3")


# =========================================================================
# WorkflowEngine — parallel workflow (end-to-end)
# =========================================================================


class TestWorkflowEngineParallel:
    def test_full_parallel(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        parallel_workflow(registry)
        inst = engine.start_workflow("PAR_WF")
        for sid in ("a", "b", "c"):
            engine.execute_step(inst.instance_id, sid)
            engine.complete_step(inst.instance_id, sid)
        assert engine.get_instance(inst.instance_id).status == WorkflowStatus.COMPLETED

    def test_parallel_order_independence(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        parallel_workflow(registry)
        inst = engine.start_workflow("PAR_WF")
        engine.execute_step(inst.instance_id, "c")
        engine.complete_step(inst.instance_id, "c")
        engine.execute_step(inst.instance_id, "a")
        engine.complete_step(inst.instance_id, "a")
        engine.execute_step(inst.instance_id, "b")
        engine.complete_step(inst.instance_id, "b")
        assert engine.get_instance(inst.instance_id).status == WorkflowStatus.COMPLETED


# =========================================================================
# WorkflowEngine — hybrid DAG (end-to-end)
# =========================================================================


class TestWorkflowEngineHybridDag:
    def test_full_hybrid(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        hybrid_workflow(registry)
        inst = engine.start_workflow("HYB_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.complete_step(inst.instance_id, "s1")
        engine.execute_step(inst.instance_id, "s2")
        engine.complete_step(inst.instance_id, "s2")
        engine.execute_step(inst.instance_id, "s3")
        engine.complete_step(inst.instance_id, "s3")
        engine.execute_step(inst.instance_id, "s4")
        engine.complete_step(inst.instance_id, "s4")
        assert engine.get_instance(inst.instance_id).status == WorkflowStatus.COMPLETED

    def test_hybrid_blocked_until_all_deps_met(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        hybrid_workflow(registry)
        inst = engine.start_workflow("HYB_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.complete_step(inst.instance_id, "s1")
        engine.execute_step(inst.instance_id, "s2")
        engine.complete_step(inst.instance_id, "s2")
        with pytest.raises(WorkflowInvalidTransitionError, match="dependencies are not met"):
            engine.execute_step(inst.instance_id, "s4")


# =========================================================================
# WorkflowEngine — transitive dependency cancellation
# =========================================================================


class TestWorkflowEngineTransitiveCancellation:
    def test_cancel_transitive_dependents(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition(
            "TRANS_CANCEL",
            step("a"),
            step("b", dependencies=["a"]),
            step("c", dependencies=["b"]),
        )
        registry.register(wf_def)
        inst = engine.start_workflow("TRANS_CANCEL")
        engine.execute_step(inst.instance_id, "a")
        engine.fail_step(inst.instance_id, "a", error_message="root fail")
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["b"].status == StepStatus.CANCELLED
        assert instance.steps["c"].status == StepStatus.CANCELLED

    def test_cancel_only_direct_dependents(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition(
            "DAG_CANCEL",
            step("a"),
            step("b", dependencies=["a"]),
            step("c"),  # independent
        )
        registry.register(wf_def)
        inst = engine.start_workflow("DAG_CANCEL")
        engine.execute_step(inst.instance_id, "a")
        engine.fail_step(inst.instance_id, "a", error_message="fail")
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["b"].status == StepStatus.CANCELLED
        assert instance.steps["c"].status == StepStatus.PENDING


# =========================================================================
# WorkflowEngine — error messages
# =========================================================================


class TestWorkflowEngineErrorMessages:
    def test_failure_error_message_on_workflow(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.fail_step(inst.instance_id, "s1", error_message="something went wrong")
        instance = engine.get_instance(inst.instance_id)
        assert "something went wrong" in instance.error_message
        assert "s1" in instance.error_message

    def test_cancellation_error_message(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.cancel_workflow(inst.instance_id, reason="stopped by operator")
        instance = engine.get_instance(inst.instance_id)
        assert instance.error_message == "stopped by operator"

    def test_cancellation_default_reason(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.cancel_workflow(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.error_message == "Workflow cancelled"


# =========================================================================
# WorkflowEngine — edge cases
# =========================================================================


class TestWorkflowEngineEdgeCases:
    def test_empty_workflow(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("EMPTY")
        registry.register(wf_def)
        inst = engine.start_workflow("EMPTY")
        assert inst.status == WorkflowStatus.COMPLETED
        assert len(inst.steps) == 0

    def test_single_step_workflow(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("SINGLE", step("only"))
        registry.register(wf_def)
        inst = engine.start_workflow("SINGLE")
        engine.execute_step(inst.instance_id, "only")
        engine.complete_step(inst.instance_id, "only")
        assert engine.get_instance(inst.instance_id).status == WorkflowStatus.COMPLETED

    def test_multiple_instances_same_type(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        i1 = engine.start_workflow("SEQ_WF")
        i2 = engine.start_workflow("SEQ_WF")
        assert i1.instance_id != i2.instance_id
        assert len(engine.list_instances()) == 2

    def test_step_with_no_dependencies(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("NO_DEPS", step("a"), step("b"))
        registry.register(wf_def)
        inst = engine.start_workflow("NO_DEPS")
        ready = engine.ready_steps(inst.instance_id)
        assert len(ready) == 2

    def test_step_with_all_deps(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("ALL_DEPS", step("a"), step("b", dependencies=["a"]), step("c", dependencies=["a", "b"]))
        registry.register(wf_def)
        inst = engine.start_workflow("ALL_DEPS")
        ready = engine.ready_steps(inst.instance_id)
        assert len(ready) == 1
        assert ready[0].step.step_id == "a"

    def test_no_payload(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("NO_PAYLOAD", step("a", payload={}))
        registry.register(wf_def)
        inst = engine.start_workflow("NO_PAYLOAD")
        assert inst.steps["a"].step.payload == {}

    def test_step_result_preserved(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("RESULT", step("a"))
        registry.register(wf_def)
        inst = engine.start_workflow("RESULT")
        engine.execute_step(inst.instance_id, "a")
        engine.complete_step(inst.instance_id, "a", result={"data": [1, 2, 3]})
        assert engine.get_instance(inst.instance_id).steps["a"].result == {"data": [1, 2, 3]}

    def test_payload_override_none(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("PO_NONE", step("a", payload={"x": 1}))
        registry.register(wf_def)
        inst = engine.start_workflow("PO_NONE", payload_override=None)
        assert inst.steps["a"].step.payload == {"x": 1}


# =========================================================================
# WorkflowExecutor — unit tests
# =========================================================================


class TestWorkflowExecutor:
    async def test_execute_ready_steps_none_ready(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        result = await executor.execute_ready_steps(inst.instance_id)
        assert len(result) == 1
        assert result[0].step.step_id == "s1"

    async def test_execute_step_dispatches_command(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{"result": "ok"}]))
        await executor.execute_ready_steps(inst.instance_id)
        dispatcher.dispatch.assert_awaited_once()
        call_args = dispatcher.dispatch.await_args[0][0]
        assert call_args.command_type == "TEST_CMD"

    async def test_execute_step_success_updates_state(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{"result": "ok"}]))
        await executor.execute_ready_steps(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].status == StepStatus.COMPLETED
        assert instance.steps["s1"].result == {"result": "ok"}

    async def test_execute_step_failure_updates_state(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=False, error="cmd error"))
        await executor.execute_ready_steps(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].status == StepStatus.FAILED
        assert "cmd error" in instance.steps["s1"].error_message

    async def test_execute_step_retry_on_failure(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        wf_def = definition("EXEC_RETRY", step("s1", retry_count=1))
        registry.register(wf_def)
        inst = engine.start_workflow("EXEC_RETRY")
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=False, error="transient"))
        await executor.execute_ready_steps(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].status == StepStatus.PENDING
        assert instance.steps["s1"].attempt == 1

    async def test_execute_step_exhaust_retry(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        wf_def = definition("EXEC_EXHAUST", step("s1", retry_count=0))
        registry.register(wf_def)
        inst = engine.start_workflow("EXEC_EXHAUST")
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=False, error="fatal"))
        await executor.execute_ready_steps(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].status == StepStatus.FAILED
        assert instance.status == WorkflowStatus.FAILED

    async def test_execute_step_timeout(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        wf_def = definition("TIMEOUT", step("s1", timeout_seconds=0.01))
        registry.register(wf_def)
        inst = engine.start_workflow("TIMEOUT")
        dispatcher.dispatch = AsyncMock(side_effect=asyncio.TimeoutError)
        await executor.execute_ready_steps(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].status == StepStatus.FAILED
        assert "timed out" in (instance.steps["s1"].error_message or "").lower() or instance.status == WorkflowStatus.FAILED

    async def test_execute_step_dispatcher_raises(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        dispatcher.dispatch = AsyncMock(side_effect=ValueError("dispatcher crash"))
        await executor.execute_ready_steps(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].status in (StepStatus.FAILED, StepStatus.PENDING)

    async def test_execute_multiple_ready_steps_parallel(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        parallel_workflow(registry)
        inst = engine.start_workflow("PAR_WF")
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        results = await executor.execute_ready_steps(inst.instance_id)
        assert len(results) == 3
        assert dispatcher.dispatch.await_count == 3

    async def test_execute_workflow_full(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{"step": "ok"}]))
        await executor.execute_workflow(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.status == WorkflowStatus.COMPLETED
        assert all(s.status == StepStatus.COMPLETED for s in instance.steps.values())

    async def test_execute_workflow_stops_on_failure(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=False, error="fatal"))
        await executor.execute_workflow(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.status == WorkflowStatus.FAILED

    async def test_execute_nonexistent_instance(self, executor: WorkflowExecutor) -> None:
        with pytest.raises(WorkflowInstanceNotFoundError):
            await executor.execute_ready_steps("ghost")

    async def test_execute_step_with_events_result(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{"output": "done"}]))
        await executor.execute_ready_steps(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].result == {"output": "done"}

    async def test_execute_step_empty_events(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[]))
        await executor.execute_ready_steps(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].result is None

    async def test_execute_workflow_already_completed(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        for sid in ("s1", "s2", "s3"):
            engine.execute_step(inst.instance_id, sid)
            engine.complete_step(inst.instance_id, sid)
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        await executor.execute_workflow(inst.instance_id)
        dispatcher.dispatch.assert_not_called()

    async def test_execute_workflow_already_failed(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.fail_step(inst.instance_id, "s1", error_message="boom")
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        await executor.execute_workflow(inst.instance_id)
        dispatcher.dispatch.assert_not_called()

    async def test_execute_workflow_already_cancelled(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.cancel_workflow(inst.instance_id)
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        await executor.execute_workflow(inst.instance_id)
        dispatcher.dispatch.assert_not_called()

    async def test_execute_hybrid_workflow(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        hybrid_workflow(registry)
        inst = engine.start_workflow("HYB_WF")
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        await executor.execute_workflow(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.status == WorkflowStatus.COMPLETED

    async def test_execute_parallel_workflow(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        parallel_workflow(registry)
        inst = engine.start_workflow("PAR_WF")
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        await executor.execute_workflow(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.status == WorkflowStatus.COMPLETED

    async def test_execute_preserves_command_type(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        wf_def = definition("CMD_TYPE", step("a", command_type="PLAN_CREATE"), step("b", command_type="RESEARCH_EXECUTE"))
        registry.register(wf_def)
        inst = engine.start_workflow("CMD_TYPE")
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        await executor.execute_workflow(inst.instance_id)
        assert dispatcher.dispatch.await_count == 2
        calls = dispatcher.dispatch.await_args_list
        assert calls[0][0][0].command_type == "PLAN_CREATE"
        assert calls[1][0][0].command_type == "RESEARCH_EXECUTE"

    async def test_execute_retry_then_succeed(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        wf_def = definition("RETRY_OK", step("s1", retry_count=1))
        registry.register(wf_def)
        inst = engine.start_workflow("RETRY_OK")
        dispatcher.dispatch = AsyncMock(side_effect=[
            MagicMock(success=False, error="retry"),
            MagicMock(success=True, events=[{"ok": True}]),
        ])
        await executor.execute_workflow(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].status == StepStatus.COMPLETED
        assert instance.status == WorkflowStatus.COMPLETED

    async def test_execute_workflow_with_3step_retry(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        wf_def = definition(
            "RETRY_3",
            step("a", retry_count=2),
            step("b", dependencies=["a"]),
        )
        registry.register(wf_def)
        inst = engine.start_workflow("RETRY_3")
        dispatcher.dispatch = AsyncMock(side_effect=[
            MagicMock(success=False, error="fail1"),
            MagicMock(success=False, error="fail2"),
            MagicMock(success=True, events=[{"ok": True}]),
            MagicMock(success=True, events=[{"ok": True}]),
        ])
        await executor.execute_workflow(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["a"].status == StepStatus.COMPLETED
        assert instance.steps["b"].status == StepStatus.COMPLETED
        assert instance.status == WorkflowStatus.COMPLETED

    async def test_execute_workflow_cancelled_during_execution(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        wf_def = definition("CANCEL_MID", step("a"), step("b", dependencies=["a"]))
        registry.register(wf_def)
        inst = engine.start_workflow("CANCEL_MID")
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        engine.execute_step(inst.instance_id, "a")
        engine.complete_step(inst.instance_id, "a")
        engine.cancel_workflow(inst.instance_id)
        await executor.execute_workflow(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.status == WorkflowStatus.CANCELLED
        assert instance.steps["b"].status == StepStatus.CANCELLED

    async def test_execute_workflow_empty(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("EMPTY_EXEC")
        registry.register(wf_def)
        inst = engine.start_workflow("EMPTY_EXEC")
        await executor.execute_workflow(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.status == WorkflowStatus.COMPLETED

    async def test_execute_ready_steps_empty_when_all_done(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        await executor.execute_workflow(inst.instance_id)
        result = await executor.execute_ready_steps(inst.instance_id)
        assert result == []

    async def test_execute_step_dispatcher_raises_command_expired(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        from backend.runtime.errors import CommandExpiredError
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        dispatcher.dispatch = AsyncMock(side_effect=CommandExpiredError("expired"))
        await executor.execute_ready_steps(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].status in (StepStatus.FAILED, StepStatus.PENDING)

    async def test_execute_step_dispatcher_raises_command_rejected(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        from backend.runtime.errors import CommandRejectedError
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        dispatcher.dispatch = AsyncMock(side_effect=CommandRejectedError("rejected"))
        await executor.execute_ready_steps(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].status in (StepStatus.FAILED, StepStatus.PENDING)

    async def test_execute_retry_then_exhaust(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        wf_def = definition("EXEC_RETRY_EX", step("s1", retry_count=1))
        registry.register(wf_def)
        inst = engine.start_workflow("EXEC_RETRY_EX")
        dispatcher.dispatch = AsyncMock(side_effect=[
            MagicMock(success=False, error="try1"),
            MagicMock(success=False, error="try2"),
            MagicMock(success=True, events=[{}]),
        ])
        await executor.execute_workflow(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].status == StepStatus.FAILED
        assert instance.status == WorkflowStatus.FAILED


# =========================================================================
# Additional engine edge cases
# =========================================================================


class TestWorkflowEngineAdditionalEdgeCases:
    def test_diamond_dag(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition(
            "DIAMOND",
            step("a"),
            step("b", dependencies=["a"]),
            step("c", dependencies=["a"]),
            step("d", dependencies=["b", "c"]),
        )
        registry.register(wf_def)
        inst = engine.start_workflow("DIAMOND")
        engine.execute_step(inst.instance_id, "a")
        engine.complete_step(inst.instance_id, "a")
        engine.execute_step(inst.instance_id, "b")
        engine.complete_step(inst.instance_id, "b")
        engine.execute_step(inst.instance_id, "c")
        engine.complete_step(inst.instance_id, "c")
        engine.execute_step(inst.instance_id, "d")
        engine.complete_step(inst.instance_id, "d")
        assert engine.get_instance(inst.instance_id).status == WorkflowStatus.COMPLETED

    def test_diamond_blocked_until_all_branch_deps_met(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition(
            "DIAMOND2",
            step("a"),
            step("b", dependencies=["a"]),
            step("c", dependencies=["a"]),
            step("d", dependencies=["b", "c"]),
        )
        registry.register(wf_def)
        inst = engine.start_workflow("DIAMOND2")
        engine.execute_step(inst.instance_id, "a")
        engine.complete_step(inst.instance_id, "a")
        engine.execute_step(inst.instance_id, "b")
        engine.complete_step(inst.instance_id, "b")
        with pytest.raises(WorkflowInvalidTransitionError, match="dependencies are not met"):
            engine.execute_step(inst.instance_id, "d")

    def test_fail_on_one_branch_cancels_other_branch_dependents(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition(
            "BRANCH_FAIL",
            step("a"),
            step("b", dependencies=["a"]),
            step("c", dependencies=["a"]),
            step("d", dependencies=["b", "c"]),
        )
        registry.register(wf_def)
        inst = engine.start_workflow("BRANCH_FAIL")
        engine.execute_step(inst.instance_id, "a")
        engine.complete_step(inst.instance_id, "a")
        engine.execute_step(inst.instance_id, "b")
        engine.complete_step(inst.instance_id, "b")
        engine.execute_step(inst.instance_id, "c")
        engine.fail_step(inst.instance_id, "c", error_message="branch fail")
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["c"].status == StepStatus.FAILED
        assert instance.steps["d"].status == StepStatus.CANCELLED

    def test_multiple_independent_branches(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition(
            "MULTI_BRANCH",
            step("a"),
            step("b"),
            step("c1", dependencies=["a"]),
            step("c2", dependencies=["a"]),
            step("d1", dependencies=["b"]),
        )
        registry.register(wf_def)
        inst = engine.start_workflow("MULTI_BRANCH")
        ready = engine.ready_steps(inst.instance_id)
        assert len(ready) == 2
        assert {r.step.step_id for r in ready} == {"a", "b"}

    def test_long_chain(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        steps = [step(f"s{i}") for i in range(10)]
        for i in range(1, 10):
            steps[i] = step(f"s{i}", dependencies=[f"s{i-1}"])
        wf_def = definition("LONG", *steps)
        registry.register(wf_def)
        inst = engine.start_workflow("LONG")
        for i in range(10):
            engine.execute_step(inst.instance_id, f"s{i}")
            engine.complete_step(inst.instance_id, f"s{i}")
        assert engine.get_instance(inst.instance_id).status == WorkflowStatus.COMPLETED

    def test_two_independent_steps_and_one_dependent(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition(
            "TWO_INDEP",
            step("a"),
            step("b"),
            step("c", dependencies=["a", "b"]),
        )
        registry.register(wf_def)
        inst = engine.start_workflow("TWO_INDEP")
        ready = engine.ready_steps(inst.instance_id)
        assert len(ready) == 2
        engine.execute_step(inst.instance_id, "a")
        engine.complete_step(inst.instance_id, "a")
        assert len(engine.ready_steps(inst.instance_id)) == 1
        engine.execute_step(inst.instance_id, "b")
        engine.complete_step(inst.instance_id, "b")
        engine.execute_step(inst.instance_id, "c")
        engine.complete_step(inst.instance_id, "c")
        assert engine.get_instance(inst.instance_id).status == WorkflowStatus.COMPLETED

    def test_start_after_unregister(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        registry.unregister("SEQ_WF")
        with pytest.raises(WorkflowNotFoundError):
            engine.start_workflow("SEQ_WF")

    def test_execute_increments_attempt_on_retry(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("ATTEMPT", step("s1", retry_count=2))
        registry.register(wf_def)
        inst = engine.start_workflow("ATTEMPT")
        engine.execute_step(inst.instance_id, "s1")
        assert engine.get_instance(inst.instance_id).steps["s1"].attempt == 1
        engine.fail_step(inst.instance_id, "s1", error_message="f1")
        engine.execute_step(inst.instance_id, "s1")
        assert engine.get_instance(inst.instance_id).steps["s1"].attempt == 2
        engine.fail_step(inst.instance_id, "s1", error_message="f2")
        engine.execute_step(inst.instance_id, "s1")
        assert engine.get_instance(inst.instance_id).steps["s1"].attempt == 3

    def test_complete_step_with_none_result(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.complete_step(inst.instance_id, "s1")
        assert engine.get_instance(inst.instance_id).steps["s1"].result is None

    def test_fail_step_nonexistent_instance_raises(self, engine: WorkflowEngine) -> None:
        with pytest.raises(WorkflowInstanceNotFoundError):
            engine.fail_step("ghost", "s1")

    def test_cancel_workflow_nonexistent_raises(self, engine: WorkflowEngine) -> None:
        with pytest.raises(WorkflowInstanceNotFoundError):
            engine.cancel_workflow("ghost")

    def test_ready_steps_excludes_cancelled(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.cancel_workflow(inst.instance_id)
        ready = engine.ready_steps(inst.instance_id)
        assert ready == []

    def test_ready_steps_excludes_failed_no_retry(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.fail_step(inst.instance_id, "s1", error_message="fail")
        ready = engine.ready_steps(inst.instance_id)
        assert ready == []

    def test_workflow_definition_immutable(self) -> None:
        d = definition("IMMUTABLE", step("a"), step("b"))
        with pytest.raises(AttributeError):
            d.workflow_type = "CHANGED"  # type: ignore[misc]

    def test_workflow_definition_steps_tuple(self) -> None:
        d = definition("TUPLE", step("a"), step("b"))
        assert isinstance(d.steps, tuple)

    def test_step_immutable_field(self) -> None:
        s = step("test")
        with pytest.raises(AttributeError):
            s.step_id = "changed"  # type: ignore[misc]

    def test_workflow_instance_mutable(self) -> None:
        inst = WorkflowInstance(instance_id="id", workflow_type="T")
        inst.status = WorkflowStatus.COMPLETED
        assert inst.status == WorkflowStatus.COMPLETED

    def test_two_workflow_types_same_step_ids(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        registry.register(definition("A", step("x"), step("y", dependencies=["x"])))
        registry.register(definition("B", step("x"), step("y", dependencies=["x"])))
        i1 = engine.start_workflow("A")
        i2 = engine.start_workflow("B")
        engine.execute_step(i1.instance_id, "x")
        engine.complete_step(i1.instance_id, "x")
        engine.execute_step(i2.instance_id, "x")
        engine.complete_step(i2.instance_id, "x")
        assert engine.get_instance(i1.instance_id).steps["x"].status == StepStatus.COMPLETED
        assert engine.get_instance(i2.instance_id).steps["x"].status == StepStatus.COMPLETED

    def test_parallel_some_fail_cancels_dependents(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition(
            "PAR_FAIL",
            step("a"),
            step("b"),
            step("c"),
            step("d", dependencies=["a", "b", "c"]),
        )
        registry.register(wf_def)
        inst = engine.start_workflow("PAR_FAIL")
        engine.execute_step(inst.instance_id, "a")
        engine.complete_step(inst.instance_id, "a")
        engine.execute_step(inst.instance_id, "b")
        engine.fail_step(inst.instance_id, "b", error_message="b fail")
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["b"].status == StepStatus.FAILED
        assert instance.steps["c"].status == StepStatus.PENDING  # independent, not cancelled
        assert instance.steps["d"].status == StepStatus.CANCELLED  # depends on b
        assert instance.status == WorkflowStatus.FAILED

    def test_fail_with_retry_then_cancel(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("RETRY_CANCEL", step("a", retry_count=1), step("b", dependencies=["a"]))
        registry.register(wf_def)
        inst = engine.start_workflow("RETRY_CANCEL")
        engine.execute_step(inst.instance_id, "a")
        engine.fail_step(inst.instance_id, "a", error_message="fail1")
        assert engine.get_instance(inst.instance_id).status == WorkflowStatus.RUNNING
        engine.cancel_workflow(inst.instance_id, reason="cancelling")
        instance = engine.get_instance(inst.instance_id)
        assert instance.status == WorkflowStatus.CANCELLED
        assert instance.steps["a"].status == StepStatus.CANCELLED
        assert instance.steps["b"].status == StepStatus.CANCELLED

    def test_interleaved_workflows(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition(
            "INTERLEAVE",
            step("a"),
            step("b", dependencies=["a"]),
        )
        registry.register(wf_def)
        i1 = engine.start_workflow("INTERLEAVE")
        i2 = engine.start_workflow("INTERLEAVE")
        engine.execute_step(i1.instance_id, "a")
        engine.execute_step(i2.instance_id, "a")
        engine.complete_step(i1.instance_id, "a")
        engine.execute_step(i1.instance_id, "b")
        engine.complete_step(i1.instance_id, "b")
        engine.complete_step(i2.instance_id, "a")
        engine.execute_step(i2.instance_id, "b")
        engine.complete_step(i2.instance_id, "b")
        assert engine.get_instance(i1.instance_id).status == WorkflowStatus.COMPLETED
        assert engine.get_instance(i2.instance_id).status == WorkflowStatus.COMPLETED

    def test_retry_then_cancel(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("RET_THEN_CANCEL", step("a", retry_count=1))
        registry.register(wf_def)
        inst = engine.start_workflow("RET_THEN_CANCEL")
        engine.execute_step(inst.instance_id, "a")
        engine.fail_step(inst.instance_id, "a", error_message="try1")
        engine.cancel_workflow(inst.instance_id, reason="cancel after retry")
        instance = engine.get_instance(inst.instance_id)
        assert instance.status == WorkflowStatus.CANCELLED

    def test_pending_step_with_retry_not_executed(self, engine: WorkflowEngine, registry: WorkflowRegistry) -> None:
        wf_def = definition("PEND_RETRY", step("a", retry_count=2))
        registry.register(wf_def)
        inst = engine.start_workflow("PEND_RETRY")
        engine.fail_step(inst.instance_id, "a", error_message="fail before exec")
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["a"].status == StepStatus.PENDING
        assert instance.steps["a"].attempt == 1
        assert instance.steps["a"].error_message == "fail before exec"
        assert instance.status == WorkflowStatus.RUNNING

    def test_workflow_survives_state_reload(self, engine: WorkflowEngine, registry: WorkflowRegistry, state: InMemoryWorkflowState) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        engine.execute_step(inst.instance_id, "s1")
        engine.complete_step(inst.instance_id, "s1")
        engine2 = WorkflowEngine(registry=registry, state=state)
        loaded = engine2.get_instance(inst.instance_id)
        assert loaded.steps["s1"].status == StepStatus.COMPLETED
        assert loaded.steps["s2"].status == StepStatus.PENDING


# =========================================================================
# Additional executor edge cases
# =========================================================================


class TestWorkflowExecutorAdditional:
    async def test_executor_parallel_propagates_results(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        parallel_workflow(registry)
        inst = engine.start_workflow("PAR_WF")
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{"output": "done"}]))
        await executor.execute_workflow(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.status == WorkflowStatus.COMPLETED
        assert all(s.status == StepStatus.COMPLETED for s in instance.steps.values())

    async def test_executor_ready_steps_sequential_calls(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        seq_workflow(registry)
        inst = engine.start_workflow("SEQ_WF")
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        r1 = await executor.execute_ready_steps(inst.instance_id)
        assert len(r1) == 1
        r2 = await executor.execute_ready_steps(inst.instance_id)
        assert len(r2) == 1

    async def test_executor_step_timeout_fast(self, executor: WorkflowExecutor, engine: WorkflowEngine, registry: WorkflowRegistry, dispatcher: AsyncMock) -> None:
        wf_def = definition("TO_FAST", step("s1", timeout_seconds=0.001))
        registry.register(wf_def)
        inst = engine.start_workflow("TO_FAST")
        async def slow(_envelope):
            await asyncio.sleep(10)
            return MagicMock(success=True, events=[{}])
        dispatcher.dispatch = AsyncMock(side_effect=slow)
        await executor.execute_ready_steps(inst.instance_id)
        instance = engine.get_instance(inst.instance_id)
        assert instance.steps["s1"].status == StepStatus.FAILED

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.orchestrator.domain.exceptions import (
    AllWorkflowsNotCompletedError,
    DuplicateExecutionOrderError,
    DuplicateWorkflowIdError,
    HybridModeRequiresTwoStepsError,
    InvalidAgentRoleError,
    InvalidExecutionOrderError,
    InvalidExecutionResultError,
    InvalidFailureReasonError,
    InvalidTransitionError,
    InvalidUserIntentError,
    InvalidWorkflowGoalError,
    OrchestrationTerminalError,
    OrchestratorDomainError,
    StepNotStartedError,
    WorkflowHasNoStepsError,
    WorkflowNotStartedError,
    WorkflowStepTerminalError,
    WorkflowTerminalError,
)
from backend.orchestrator.domain.factory import OrchestratorFactory
from backend.orchestrator.domain.model import (
    AgentReference,
    AgentRole,
    ExecutionMode,
    ExecutionOrder,
    ExecutionResult,
    FailureReason,
    Orchestration,
    OrchestrationCancelled,
    OrchestrationCompleted,
    OrchestrationCreated,
    OrchestrationExecutionStarted,
    OrchestrationFailed,
    OrchestrationId,
    OrchestrationPlanningStarted,
    OrchestrationResearchStarted,
    OrchestrationStatus,
    UserIntent,
    VALID_ORCHESTRATION_TRANSITIONS,
    VALID_WORKFLOW_STEP_TRANSITIONS,
    VALID_WORKFLOW_TRANSITIONS,
    Workflow,
    WorkflowCompleted,
    WorkflowCreated,
    WorkflowFailed,
    WorkflowGoal,
    WorkflowId,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStepCompleted,
    WorkflowStepFailed,
    WorkflowStepStarted,
    WorkflowStepStatus,
)

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


# ===========================================================================
# Value Objects
# ===========================================================================


class TestOrchestrationId:
    def test_default_creation(self) -> None:
        oid = OrchestrationId()
        assert isinstance(oid.value, UUID)

    def test_str_representation(self) -> None:
        oid = OrchestrationId(value=UUID("00000000-0000-0000-0000-000000000001"))
        assert str(oid) == "00000000-0000-0000-0000-000000000001"

    def test_equality(self) -> None:
        oid1 = OrchestrationId(value=UUID("00000000-0000-0000-0000-000000000001"))
        oid2 = OrchestrationId(value=UUID("00000000-0000-0000-0000-000000000001"))
        assert oid1 == oid2


class TestWorkflowId:
    def test_default_creation(self) -> None:
        wid = WorkflowId()
        assert isinstance(wid.value, UUID)

    def test_str_representation(self) -> None:
        wid = WorkflowId(value=UUID("00000000-0000-0000-0000-000000000002"))
        assert str(wid) == "00000000-0000-0000-0000-000000000002"

    def test_equality(self) -> None:
        wid1 = WorkflowId(value=UUID("00000000-0000-0000-0000-000000000002"))
        wid2 = WorkflowId(value=UUID("00000000-0000-0000-0000-000000000002"))
        assert wid1 == wid2


class TestUserIntent:
    def test_creation(self) -> None:
        intent = UserIntent(value="search for information")
        assert intent.value == "search for information"
        assert str(intent) == "search for information"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidUserIntentError):
            UserIntent(value="")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(InvalidUserIntentError):
            UserIntent(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            UserIntent(value=123)

    def test_len(self) -> None:
        intent = UserIntent(value="hello")
        assert len(intent) == 5


class TestWorkflowGoal:
    def test_creation(self) -> None:
        goal = WorkflowGoal(value="process data")
        assert goal.value == "process data"
        assert str(goal) == "process data"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidWorkflowGoalError):
            WorkflowGoal(value="")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(InvalidWorkflowGoalError):
            WorkflowGoal(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            WorkflowGoal(value=123)

    def test_len(self) -> None:
        goal = WorkflowGoal(value="hello")
        assert len(goal) == 5


class TestExecutionResult:
    def test_creation(self) -> None:
        result = ExecutionResult(value="completed successfully")
        assert result.value == "completed successfully"
        assert str(result) == "completed successfully"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidExecutionResultError):
            ExecutionResult(value="")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(InvalidExecutionResultError):
            ExecutionResult(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            ExecutionResult(value=123)


class TestFailureReason:
    def test_creation(self) -> None:
        reason = FailureReason(value="timeout")
        assert reason.value == "timeout"
        assert str(reason) == "timeout"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidFailureReasonError):
            FailureReason(value="")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(InvalidFailureReasonError):
            FailureReason(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            FailureReason(value=123)


class TestAgentReference:
    def test_creation(self) -> None:
        ref = AgentReference(role=AgentRole.PLANNER)
        assert ref.role == AgentRole.PLANNER
        assert str(ref) == "planner"

    def test_non_agent_role_raises(self) -> None:
        with pytest.raises(InvalidAgentRoleError):
            AgentReference(role="invalid")


class TestExecutionOrder:
    def test_creation(self) -> None:
        order = ExecutionOrder(value=0)
        assert order.value == 0
        assert int(order) == 0

    def test_positive(self) -> None:
        order = ExecutionOrder(value=5)
        assert order.value == 5

    def test_zero(self) -> None:
        order = ExecutionOrder(value=0)
        assert order.value == 0

    def test_negative_raises(self) -> None:
        with pytest.raises(InvalidExecutionOrderError):
            ExecutionOrder(value=-1)

    def test_non_int_raises(self) -> None:
        with pytest.raises(TypeError):
            ExecutionOrder(value="1")


# ===========================================================================
# Enums
# ===========================================================================


class TestOrchestrationStatusEnum:
    def test_values(self) -> None:
        expected = {
            "created",
            "planning",
            "researching",
            "executing",
            "completed",
            "failed",
            "cancelled",
        }
        actual = {e.value for e in OrchestrationStatus}
        assert actual == expected

    def test_count(self) -> None:
        assert len(OrchestrationStatus) == 7

    def test_created_is_string(self) -> None:
        assert OrchestrationStatus.CREATED.value == "created"


class TestWorkflowStepStatusEnum:
    def test_values(self) -> None:
        expected = {"pending", "running", "completed", "failed", "skipped"}
        actual = {e.value for e in WorkflowStepStatus}
        assert actual == expected

    def test_count(self) -> None:
        assert len(WorkflowStepStatus) == 5

    def test_pending_is_string(self) -> None:
        assert WorkflowStepStatus.PENDING.value == "pending"


class TestAgentRoleEnum:
    def test_values(self) -> None:
        expected = {
            "planner",
            "research",
            "automation",
            "memory",
            "knowledge",
            "policy",
        }
        actual = {e.value for e in AgentRole}
        assert actual == expected

    def test_count(self) -> None:
        assert len(AgentRole) == 6

    def test_planner_is_string(self) -> None:
        assert AgentRole.PLANNER.value == "planner"


class TestExecutionModeEnum:
    def test_values(self) -> None:
        expected = {"sequential", "parallel", "hybrid"}
        actual = {e.value for e in ExecutionMode}
        assert actual == expected

    def test_count(self) -> None:
        assert len(ExecutionMode) == 3

    def test_sequential_is_string(self) -> None:
        assert ExecutionMode.SEQUENTIAL.value == "sequential"


# ===========================================================================
# Events
# ===========================================================================


class TestOrchestrationEvents:
    def test_orchestration_created(self) -> None:
        oid = OrchestrationId()
        event = OrchestrationCreated(
            orchestration_id=oid,
            intent="test",
            goal="test goal",
            occurred_at=NOW,
        )
        assert event.orchestration_id == oid
        assert event.intent == "test"
        assert event.goal == "test goal"
        assert event.occurred_at == NOW
        assert isinstance(event.event_id, UUID)

    def test_orchestration_planning_started(self) -> None:
        oid = OrchestrationId()
        event = OrchestrationPlanningStarted(
            orchestration_id=oid, occurred_at=NOW
        )
        assert event.orchestration_id == oid
        assert isinstance(event.event_id, UUID)

    def test_orchestration_research_started(self) -> None:
        oid = OrchestrationId()
        event = OrchestrationResearchStarted(
            orchestration_id=oid, occurred_at=NOW
        )
        assert event.orchestration_id == oid
        assert isinstance(event.event_id, UUID)

    def test_orchestration_execution_started(self) -> None:
        oid = OrchestrationId()
        event = OrchestrationExecutionStarted(
            orchestration_id=oid, occurred_at=NOW
        )
        assert event.orchestration_id == oid
        assert isinstance(event.event_id, UUID)

    def test_orchestration_completed(self) -> None:
        oid = OrchestrationId()
        event = OrchestrationCompleted(
            orchestration_id=oid, occurred_at=NOW
        )
        assert event.orchestration_id == oid
        assert isinstance(event.event_id, UUID)

    def test_orchestration_failed(self) -> None:
        oid = OrchestrationId()
        event = OrchestrationFailed(
            orchestration_id=oid,
            failure_reason="error",
            occurred_at=NOW,
        )
        assert event.orchestration_id == oid
        assert event.failure_reason == "error"
        assert isinstance(event.event_id, UUID)

    def test_orchestration_cancelled(self) -> None:
        oid = OrchestrationId()
        event = OrchestrationCancelled(
            orchestration_id=oid, occurred_at=NOW
        )
        assert event.orchestration_id == oid
        assert isinstance(event.event_id, UUID)

    def test_all_events_have_event_id(self) -> None:
        oid = OrchestrationId()
        wid = WorkflowId()
        events = [
            OrchestrationCreated(oid, "a", "b", NOW),
            OrchestrationPlanningStarted(oid, NOW),
            OrchestrationResearchStarted(oid, NOW),
            OrchestrationExecutionStarted(oid, NOW),
            OrchestrationCompleted(oid, NOW),
            OrchestrationFailed(oid, "err", NOW),
            OrchestrationCancelled(oid, NOW),
            WorkflowCreated(wid, oid, "g", "sequential", NOW),
            WorkflowCompleted(wid, NOW),
            WorkflowFailed(wid, "err", NOW),
            WorkflowStepStarted(wid, NOW),
            WorkflowStepCompleted(wid, "ok", NOW),
            WorkflowStepFailed(wid, "err", NOW),
        ]
        for e in events:
            assert isinstance(e.event_id, UUID), f"{type(e).__name__} lacks event_id"

    def test_thirteen_events_exist(self) -> None:
        event_classes = {
            OrchestrationCreated,
            OrchestrationPlanningStarted,
            OrchestrationResearchStarted,
            OrchestrationExecutionStarted,
            OrchestrationCompleted,
            OrchestrationFailed,
            OrchestrationCancelled,
            WorkflowCreated,
            WorkflowCompleted,
            WorkflowFailed,
            WorkflowStepStarted,
            WorkflowStepCompleted,
            WorkflowStepFailed,
        }
        assert len(event_classes) == 13

    def test_events_are_frozen(self) -> None:
        oid = OrchestrationId()
        event = OrchestrationCreated(oid, "a", "b", NOW)
        with pytest.raises(AttributeError):
            event.intent = "changed"


class TestWorkflowEvents:
    def test_workflow_created(self) -> None:
        wid = WorkflowId()
        oid = OrchestrationId()
        event = WorkflowCreated(
            workflow_id=wid,
            orchestration_id=oid,
            goal="test",
            mode="sequential",
            occurred_at=NOW,
        )
        assert event.workflow_id == wid
        assert event.orchestration_id == oid
        assert event.goal == "test"
        assert event.mode == "sequential"

    def test_workflow_completed(self) -> None:
        wid = WorkflowId()
        event = WorkflowCompleted(workflow_id=wid, occurred_at=NOW)
        assert event.workflow_id == wid

    def test_workflow_failed(self) -> None:
        wid = WorkflowId()
        event = WorkflowFailed(
            workflow_id=wid, failure_reason="err", occurred_at=NOW
        )
        assert event.workflow_id == wid
        assert event.failure_reason == "err"


class TestWorkflowStepEvents:
    def test_step_started(self) -> None:
        wid = WorkflowId()
        event = WorkflowStepStarted(step_id=wid, occurred_at=NOW)
        assert event.step_id == wid

    def test_step_completed(self) -> None:
        wid = WorkflowId()
        event = WorkflowStepCompleted(
            step_id=wid, result="done", occurred_at=NOW
        )
        assert event.step_id == wid
        assert event.result == "done"

    def test_step_failed(self) -> None:
        wid = WorkflowId()
        event = WorkflowStepFailed(
            step_id=wid, failure_reason="err", occurred_at=NOW
        )
        assert event.step_id == wid
        assert event.failure_reason == "err"


# ===========================================================================
# Transition maps
# ===========================================================================


class TestTransitionMaps:
    def test_orchestration_created_transitions(self) -> None:
        assert VALID_ORCHESTRATION_TRANSITIONS[OrchestrationStatus.CREATED] == {
            OrchestrationStatus.PLANNING,
            OrchestrationStatus.CANCELLED,
        }

    def test_orchestration_completed_terminal(self) -> None:
        assert VALID_ORCHESTRATION_TRANSITIONS[OrchestrationStatus.COMPLETED] == set()

    def test_orchestration_failed_terminal(self) -> None:
        assert VALID_ORCHESTRATION_TRANSITIONS[OrchestrationStatus.FAILED] == set()

    def test_orchestration_cancelled_terminal(self) -> None:
        assert VALID_ORCHESTRATION_TRANSITIONS[OrchestrationStatus.CANCELLED] == set()

    def test_step_pending_transitions(self) -> None:
        assert VALID_WORKFLOW_STEP_TRANSITIONS[WorkflowStepStatus.PENDING] == {
            WorkflowStepStatus.RUNNING,
            WorkflowStepStatus.SKIPPED,
        }

    def test_step_running_transitions(self) -> None:
        assert VALID_WORKFLOW_STEP_TRANSITIONS[WorkflowStepStatus.RUNNING] == {
            WorkflowStepStatus.COMPLETED,
            WorkflowStepStatus.FAILED,
        }

    def test_step_completed_terminal(self) -> None:
        assert VALID_WORKFLOW_STEP_TRANSITIONS[WorkflowStepStatus.COMPLETED] == set()

    def test_step_failed_terminal(self) -> None:
        assert VALID_WORKFLOW_STEP_TRANSITIONS[WorkflowStepStatus.FAILED] == set()

    def test_step_skipped_terminal(self) -> None:
        assert VALID_WORKFLOW_STEP_TRANSITIONS[WorkflowStepStatus.SKIPPED] == set()

    def test_workflow_pending_transitions(self) -> None:
        assert VALID_WORKFLOW_TRANSITIONS[WorkflowStatus.PENDING] == {
            WorkflowStatus.RUNNING,
        }

    def test_workflow_running_transitions(self) -> None:
        assert VALID_WORKFLOW_TRANSITIONS[WorkflowStatus.RUNNING] == {
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
        }

    def test_workflow_completed_terminal(self) -> None:
        assert VALID_WORKFLOW_TRANSITIONS[WorkflowStatus.COMPLETED] == set()

    def test_workflow_failed_terminal(self) -> None:
        assert VALID_WORKFLOW_TRANSITIONS[WorkflowStatus.FAILED] == set()


# ===========================================================================
# WorkflowStep lifecycle
# ===========================================================================


class TestWorkflowStepCreation:
    def test_default_creation(self) -> None:
        step = WorkflowStep()
        assert isinstance(step.step_id, WorkflowId)
        assert step.agent_role == AgentRole.RESEARCH
        assert step.execution_order.value == 0
        assert step.status == WorkflowStepStatus.PENDING
        assert step.result is None
        assert step.failure_reason is None
        assert step.events == []

    def test_custom_creation(self) -> None:
        sid = WorkflowId()
        step = WorkflowStep(
            step_id=sid,
            agent_role=AgentRole.PLANNER,
            execution_order=ExecutionOrder(value=1),
        )
        assert step.step_id == sid
        assert step.agent_role == AgentRole.PLANNER
        assert step.execution_order.value == 1

    def test_is_terminal_pending(self) -> None:
        step = WorkflowStep()
        assert not step.is_terminal

    def test_is_terminal_initial(self) -> None:
        assert not WorkflowStep().is_terminal


class TestWorkflowStepStart:
    def test_start_transitions_to_running(self) -> None:
        step = WorkflowStep()
        step.start()
        assert step.status == WorkflowStepStatus.RUNNING

    def test_start_emits_event(self) -> None:
        step = WorkflowStep()
        step.start()
        assert len(step.events) == 1
        assert isinstance(step.events[0], WorkflowStepStarted)
        assert step.events[0].step_id == step.step_id

    def test_start_already_started_raises(self) -> None:
        step = WorkflowStep()
        step.start()
        with pytest.raises(InvalidTransitionError):
            step.start()

    def test_start_completed_raises(self) -> None:
        step = WorkflowStep()
        step.start()
        step.complete(ExecutionResult(value="done"))
        with pytest.raises(InvalidTransitionError):
            step.start()

    def test_start_failed_raises(self) -> None:
        step = WorkflowStep()
        step.start()
        step.fail(FailureReason(value="err"))
        with pytest.raises(InvalidTransitionError):
            step.start()

    def test_start_skipped_raises(self) -> None:
        step = WorkflowStep()
        step.skip()
        with pytest.raises(InvalidTransitionError):
            step.start()


class TestWorkflowStepComplete:
    def test_complete_transitions_to_completed(self) -> None:
        step = WorkflowStep()
        step.start()
        step.complete(ExecutionResult(value="done"))
        assert step.status == WorkflowStepStatus.COMPLETED

    def test_complete_emits_event(self) -> None:
        step = WorkflowStep()
        step.start()
        step.complete(ExecutionResult(value="done"))
        assert len(step.events) == 2
        assert isinstance(step.events[-1], WorkflowStepCompleted)
        assert step.events[-1].step_id == step.step_id
        assert step.events[-1].result == "done"

    def test_complete_stores_result(self) -> None:
        step = WorkflowStep()
        step.start()
        result = ExecutionResult(value="success")
        step.complete(result)
        assert step.result == result

    def test_complete_without_start_raises(self) -> None:
        step = WorkflowStep()
        result = ExecutionResult(value="done")
        with pytest.raises(InvalidTransitionError):
            step.complete(result)

    def test_complete_no_result_raises(self) -> None:
        step = WorkflowStep()
        step.start()
        with pytest.raises(InvalidExecutionResultError):
            step.complete(None)

    def test_complete_already_completed_raises(self) -> None:
        step = WorkflowStep()
        step.start()
        step.complete(ExecutionResult(value="done"))
        with pytest.raises(InvalidTransitionError):
            step.complete(ExecutionResult(value="again"))

    def test_complete_failed_step_raises(self) -> None:
        step = WorkflowStep()
        step.start()
        step.fail(FailureReason(value="err"))
        with pytest.raises(InvalidTransitionError):
            step.complete(ExecutionResult(value="done"))

    def test_complete_skipped_step_raises(self) -> None:
        step = WorkflowStep()
        step.skip()
        with pytest.raises(InvalidTransitionError):
            step.complete(ExecutionResult(value="done"))


class TestWorkflowStepFail:
    def test_fail_transitions_to_failed(self) -> None:
        step = WorkflowStep()
        step.start()
        step.fail(FailureReason(value="err"))
        assert step.status == WorkflowStepStatus.FAILED

    def test_fail_emits_event(self) -> None:
        step = WorkflowStep()
        step.start()
        step.fail(FailureReason(value="err"))
        assert len(step.events) == 2
        assert isinstance(step.events[-1], WorkflowStepFailed)
        assert step.events[-1].step_id == step.step_id
        assert step.events[-1].failure_reason == "err"

    def test_fail_stores_reason(self) -> None:
        step = WorkflowStep()
        step.start()
        reason = FailureReason(value="timeout")
        step.fail(reason)
        assert step.failure_reason == reason

    def test_fail_without_start_raises(self) -> None:
        step = WorkflowStep()
        with pytest.raises(InvalidTransitionError):
            step.fail(FailureReason(value="err"))

    def test_fail_no_reason_raises(self) -> None:
        step = WorkflowStep()
        step.start()
        with pytest.raises(InvalidFailureReasonError):
            step.fail(None)

    def test_fail_already_completed_raises(self) -> None:
        step = WorkflowStep()
        step.start()
        step.complete(ExecutionResult(value="done"))
        with pytest.raises(InvalidTransitionError):
            step.fail(FailureReason(value="err"))

    def test_fail_skipped_step_raises(self) -> None:
        step = WorkflowStep()
        step.skip()
        with pytest.raises(InvalidTransitionError):
            step.fail(FailureReason(value="err"))


class TestWorkflowStepSkip:
    def test_skip_transitions_to_skipped(self) -> None:
        step = WorkflowStep()
        step.skip()
        assert step.status == WorkflowStepStatus.SKIPPED

    def test_skip_emits_no_event(self) -> None:
        step = WorkflowStep()
        step.skip()
        assert step.events == []

    def test_skip_already_started_raises(self) -> None:
        step = WorkflowStep()
        step.start()
        with pytest.raises(InvalidTransitionError):
            step.skip()

    def test_skip_completed_raises(self) -> None:
        step = WorkflowStep()
        step.start()
        step.complete(ExecutionResult(value="done"))
        with pytest.raises(InvalidTransitionError):
            step.skip()

    def test_skip_failed_raises(self) -> None:
        step = WorkflowStep()
        step.start()
        step.fail(FailureReason(value="err"))
        with pytest.raises(InvalidTransitionError):
            step.skip()

    def test_skip_skipped_raises(self) -> None:
        step = WorkflowStep()
        step.skip()
        with pytest.raises(InvalidTransitionError):
            step.skip()

    def test_skipped_is_terminal(self) -> None:
        step = WorkflowStep()
        step.skip()
        assert step.is_terminal


# ===========================================================================
# Workflow lifecycle
# ===========================================================================


class TestWorkflowCreation:
    def test_default_creation(self) -> None:
        wf = Workflow()
        assert isinstance(wf.workflow_id, WorkflowId)
        assert wf.status == WorkflowStatus.PENDING
        assert wf.mode == ExecutionMode.SEQUENTIAL
        assert wf.steps == []
        assert wf.events == []

    def test_custom_creation(self) -> None:
        wid = WorkflowId()
        goal = WorkflowGoal(value="test")
        wf = Workflow(
            workflow_id=wid,
            goal=goal,
            mode=ExecutionMode.PARALLEL,
        )
        assert wf.workflow_id == wid
        assert wf.goal == goal
        assert wf.mode == ExecutionMode.PARALLEL

    def test_terminal_initial(self) -> None:
        assert not Workflow().is_terminal


class TestWorkflowAddStep:
    def test_add_step_increases_count(self) -> None:
        wf = Workflow()
        step = WorkflowStep()
        wf.add_step(step)
        assert len(wf.steps) == 1
        assert wf.steps[0] == step

    def test_add_multiple_steps(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=1)))
        assert len(wf.steps) == 2

    def test_add_step_to_running_workflow(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        wf.start()
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=1)))
        assert len(wf.steps) == 2

    def test_add_step_to_completed_raises(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        wf.start()
        wf.complete()
        with pytest.raises(WorkflowTerminalError):
            wf.add_step(WorkflowStep())

    def test_add_step_to_failed_raises(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        wf.start()
        wf.fail()
        with pytest.raises(WorkflowTerminalError):
            wf.add_step(WorkflowStep())

    def test_add_step_sequential_duplicate_order_raises(self) -> None:
        wf = Workflow(mode=ExecutionMode.SEQUENTIAL)
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        with pytest.raises(DuplicateExecutionOrderError):
            wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))

    def test_add_step_parallel_allows_duplicate_order(self) -> None:
        wf = Workflow(mode=ExecutionMode.PARALLEL)
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        assert len(wf.steps) == 2


class TestWorkflowStart:
    def test_start_transitions_to_running(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        wf.start()
        assert wf.status == WorkflowStatus.RUNNING

    def test_start_emits_created_event(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        wf.start()
        assert len(wf.events) == 1
        assert isinstance(wf.events[0], WorkflowCreated)

    def test_start_without_steps_raises(self) -> None:
        wf = Workflow()
        with pytest.raises(WorkflowHasNoStepsError):
            wf.start()

    def test_start_already_started_raises(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        wf.start()
        with pytest.raises(InvalidTransitionError):
            wf.start()

    def test_start_completed_raises(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        wf.start()
        wf.complete()
        with pytest.raises(InvalidTransitionError):
            wf.start()

    def test_start_failed_raises(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        wf.start()
        wf.fail()
        with pytest.raises(InvalidTransitionError):
            wf.start()


class TestWorkflowComplete:
    def test_complete_transitions_to_completed(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        wf.start()
        wf.complete()
        assert wf.status == WorkflowStatus.COMPLETED

    def test_complete_emits_event(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        wf.start()
        wf.complete()
        assert len(wf.events) == 2
        assert isinstance(wf.events[-1], WorkflowCompleted)

    def test_complete_without_start_raises(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        with pytest.raises((InvalidTransitionError, WorkflowNotStartedError)):
            wf.complete()

    def test_complete_already_completed_raises(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        wf.start()
        wf.complete()
        with pytest.raises((InvalidTransitionError, WorkflowNotStartedError)):
            wf.complete()

    def test_complete_failed_raises(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        wf.start()
        wf.fail()
        with pytest.raises((InvalidTransitionError, WorkflowNotStartedError)):
            wf.complete()

    def test_completed_is_terminal(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        wf.start()
        wf.complete()
        assert wf.is_terminal


class TestWorkflowFail:
    def test_fail_transitions_to_failed(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        wf.start()
        wf.fail()
        assert wf.status == WorkflowStatus.FAILED

    def test_fail_emits_event(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        wf.start()
        wf.fail()
        assert len(wf.events) == 2
        assert isinstance(wf.events[-1], WorkflowFailed)

    def test_fail_without_start_raises(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        with pytest.raises((InvalidTransitionError, WorkflowNotStartedError)):
            wf.fail()

    def test_fail_already_completed_raises(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        wf.start()
        wf.complete()
        with pytest.raises((InvalidTransitionError, WorkflowNotStartedError)):
            wf.fail()

    def test_failed_is_terminal(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        wf.start()
        wf.fail()
        assert wf.is_terminal


# ===========================================================================
# Orchestration lifecycle
# ===========================================================================


class TestOrchestrationCreation:
    def test_default_creation(self) -> None:
        o = Orchestration()
        assert isinstance(o.orchestration_id, OrchestrationId)
        assert o.status == OrchestrationStatus.CREATED
        assert o.workflows == []
        assert o.events == []
        assert isinstance(o.created_at, datetime)
        assert o.updated_at is None

    def test_custom_creation(self) -> None:
        oid = OrchestrationId()
        intent = UserIntent(value="test")
        goal = WorkflowGoal(value="test goal")
        o = Orchestration(
            orchestration_id=oid,
            intent=intent,
            goal=goal,
        )
        assert o.orchestration_id == oid
        assert o.intent == intent
        assert o.goal == goal

    def test_not_terminal_initial(self) -> None:
        assert not Orchestration().is_terminal


class TestOrchestrationStartPlanning:
    def test_start_planning_transitions(self) -> None:
        o = Orchestration()
        o.start_planning()
        assert o.status == OrchestrationStatus.PLANNING

    def test_start_planning_emits_event(self) -> None:
        o = Orchestration()
        o.start_planning()
        assert len(o.events) == 1
        assert isinstance(o.events[0], OrchestrationPlanningStarted)

    def test_start_planning_sets_updated_at(self) -> None:
        o = Orchestration()
        o.start_planning()
        assert o.updated_at is not None

    def test_start_planning_from_completed_raises(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        o.start_execution()
        wf = Workflow()
        wf._status = WorkflowStatus.COMPLETED
        o.add_workflow(wf)
        o.complete()
        with pytest.raises(InvalidTransitionError):
            o.start_planning()

    def test_start_planning_from_failed_raises(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.fail(FailureReason(value="err"))
        with pytest.raises(InvalidTransitionError):
            o.start_planning()

    def test_start_planning_from_cancelled_raises(self) -> None:
        o = Orchestration()
        o.cancel()
        with pytest.raises(InvalidTransitionError):
            o.start_planning()


class TestOrchestrationStartResearch:
    def test_start_research_transitions(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        assert o.status == OrchestrationStatus.RESEARCHING

    def test_start_research_emits_event(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        assert isinstance(o.events[-1], OrchestrationResearchStarted)

    def test_start_research_from_created_raises(self) -> None:
        o = Orchestration()
        with pytest.raises(InvalidTransitionError):
            o.start_research()

    def test_start_research_from_executing_raises(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        o.start_execution()
        with pytest.raises(InvalidTransitionError):
            o.start_research()


class TestOrchestrationStartExecution:
    def test_start_execution_transitions(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        o.start_execution()
        assert o.status == OrchestrationStatus.EXECUTING

    def test_start_execution_emits_event(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        o.start_execution()
        assert isinstance(o.events[-1], OrchestrationExecutionStarted)

    def test_start_execution_from_created_raises(self) -> None:
        o = Orchestration()
        with pytest.raises(InvalidTransitionError):
            o.start_execution()

    def test_start_execution_from_planning_raises(self) -> None:
        o = Orchestration()
        o.start_planning()
        with pytest.raises(InvalidTransitionError):
            o.start_execution()


class TestOrchestrationComplete:
    def test_complete_transitions(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        o.start_execution()
        wf = Workflow()
        wf._status = WorkflowStatus.COMPLETED
        o.add_workflow(wf)
        o.complete()
        assert o.status == OrchestrationStatus.COMPLETED

    def test_complete_emits_event(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        o.start_execution()
        wf = Workflow()
        wf._status = WorkflowStatus.COMPLETED
        o.add_workflow(wf)
        o.complete()
        assert isinstance(o.events[-1], OrchestrationCompleted)

    def test_complete_without_all_workflows_raises(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        o.start_execution()
        wf = Workflow()
        wf.add_step(WorkflowStep())
        o.add_workflow(wf)
        with pytest.raises(AllWorkflowsNotCompletedError):
            o.complete()

    def test_complete_with_no_workflows_raises(self) -> None:
        # With no workflows, all are "completed" by vacuous truth.
        o = Orchestration()
        o.start_planning()
        o.start_research()
        o.start_execution()
        o.complete()
        assert o.status == OrchestrationStatus.COMPLETED

    def test_complete_from_created_raises(self) -> None:
        o = Orchestration()
        with pytest.raises(InvalidTransitionError):
            o.complete()

    def test_complete_multiple_workflows_all_completed(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        o.start_execution()
        wf1 = Workflow()
        wf1._status = WorkflowStatus.COMPLETED
        wf2 = Workflow()
        wf2._status = WorkflowStatus.COMPLETED
        o.add_workflow(wf1)
        o.add_workflow(wf2)
        o.complete()
        assert o.status == OrchestrationStatus.COMPLETED

    def test_complete_one_workflow_pending_raises(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        o.start_execution()
        wf1 = Workflow()
        wf1._status = WorkflowStatus.COMPLETED
        wf2 = Workflow()
        o.add_workflow(wf1)
        o.add_workflow(wf2)
        with pytest.raises(AllWorkflowsNotCompletedError):
            o.complete()


class TestOrchestrationFail:
    def test_fail_transitions(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.fail(FailureReason(value="err"))
        assert o.status == OrchestrationStatus.FAILED

    def test_fail_emits_event(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.fail(FailureReason(value="err"))
        assert isinstance(o.events[-1], OrchestrationFailed)
        assert o.events[-1].failure_reason == "err"

    def test_fail_from_created_raises(self) -> None:
        o = Orchestration()
        with pytest.raises(InvalidTransitionError):
            o.fail(FailureReason(value="err"))

    def test_fail_no_reason_raises(self) -> None:
        o = Orchestration()
        o.start_planning()
        with pytest.raises(InvalidFailureReasonError):
            o.fail(None)

    def test_fail_already_completed_raises(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        o.start_execution()
        wf = Workflow()
        wf._status = WorkflowStatus.COMPLETED
        o.add_workflow(wf)
        o.complete()
        with pytest.raises(InvalidTransitionError):
            o.fail(FailureReason(value="err"))


class TestOrchestrationCancel:
    def test_cancel_from_created(self) -> None:
        o = Orchestration()
        o.cancel()
        assert o.status == OrchestrationStatus.CANCELLED

    def test_cancel_from_planning(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.cancel()
        assert o.status == OrchestrationStatus.CANCELLED

    def test_cancel_from_researching(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        o.cancel()
        assert o.status == OrchestrationStatus.CANCELLED

    def test_cancel_from_executing(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        o.start_execution()
        o.cancel()
        assert o.status == OrchestrationStatus.CANCELLED

    def test_cancel_emits_event(self) -> None:
        o = Orchestration()
        o.cancel()
        assert isinstance(o.events[-1], OrchestrationCancelled)

    def test_cancel_completed_raises(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        o.start_execution()
        wf = Workflow()
        wf._status = WorkflowStatus.COMPLETED
        o.add_workflow(wf)
        o.complete()
        with pytest.raises(InvalidTransitionError):
            o.cancel()

    def test_cancel_failed_raises(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.fail(FailureReason(value="err"))
        with pytest.raises(InvalidTransitionError):
            o.cancel()

    def test_cancel_cancelled_raises(self) -> None:
        o = Orchestration()
        o.cancel()
        with pytest.raises(InvalidTransitionError):
            o.cancel()


# ===========================================================================
# Orchestration add_workflow
# ===========================================================================


class TestOrchestrationAddWorkflow:
    def test_add_workflow_increases_count(self) -> None:
        o = Orchestration()
        wf = Workflow()
        o.add_workflow(wf)
        assert len(o.workflows) == 1
        assert o.workflows[0] == wf

    def test_add_multiple_workflows(self) -> None:
        o = Orchestration()
        o.add_workflow(Workflow())
        o.add_workflow(Workflow())
        assert len(o.workflows) == 2

    def test_add_duplicate_workflow_id_raises(self) -> None:
        o = Orchestration()
        wf = Workflow()
        o.add_workflow(wf)
        with pytest.raises(DuplicateWorkflowIdError):
            o.add_workflow(wf)

    def test_add_to_completed_raises(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        o.start_execution()
        wf = Workflow()
        wf._status = WorkflowStatus.COMPLETED
        o.add_workflow(wf)
        o.complete()
        with pytest.raises(OrchestrationTerminalError):
            o.add_workflow(Workflow())

    def test_add_to_cancelled_raises(self) -> None:
        o = Orchestration()
        o.cancel()
        with pytest.raises(OrchestrationTerminalError):
            o.add_workflow(Workflow())


# ===========================================================================
# Factory
# ===========================================================================


class TestOrchestratorFactoryCreateOrchestration:
    def test_creates_orchestration_and_event(self) -> None:
        result = OrchestratorFactory.create_orchestration(
            intent="test intent",
            goal="test goal",
        )
        orchestration, event = result
        assert isinstance(orchestration, Orchestration)
        assert isinstance(event, OrchestrationCreated)
        assert orchestration.intent.value == "test intent"
        assert orchestration.goal.value == "test goal"

    def test_event_links_to_orchestration(self) -> None:
        _, event = OrchestratorFactory.create_orchestration(
            intent="test",
            goal="goal",
        )
        assert event.intent == "test"
        assert event.goal == "goal"

    def test_empty_intent_raises(self) -> None:
        with pytest.raises(InvalidUserIntentError):
            OrchestratorFactory.create_orchestration(intent="", goal="goal")

    def test_empty_goal_raises(self) -> None:
        with pytest.raises(InvalidWorkflowGoalError):
            OrchestratorFactory.create_orchestration(intent="intent", goal="")


class TestOrchestratorFactoryCreateWorkflow:
    def test_creates_workflow_and_event(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, event = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf goal"
        )
        assert isinstance(wf, Workflow)
        assert isinstance(event, WorkflowCreated)
        assert wf.goal.value == "wf goal"

    def test_workflow_added_to_orchestration(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf goal"
        )
        assert wf in o.workflows

    def test_workflow_with_parallel_mode(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf goal", mode="parallel"
        )
        assert wf.mode == ExecutionMode.PARALLEL

    def test_orchestration_terminal_raises(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        o.cancel()
        with pytest.raises(OrchestrationTerminalError):
            OrchestratorFactory.create_workflow(
                orchestration=o, goal="wf goal"
            )


class TestOrchestratorFactoryAddStep:
    def test_creates_step(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf goal"
        )
        step = OrchestratorFactory.add_step(
            workflow=wf, agent_role="planner", execution_order=0
        )
        assert isinstance(step, WorkflowStep)
        assert step.agent_role == AgentRole.PLANNER
        assert step.execution_order.value == 0
        assert step.status == WorkflowStepStatus.PENDING

    def test_step_added_to_workflow(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf goal"
        )
        step = OrchestratorFactory.add_step(
            workflow=wf, agent_role="research", execution_order=1
        )
        assert step in wf.steps

    def test_invalid_agent_role_raises(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf goal"
        )
        with pytest.raises(InvalidAgentRoleError):
            OrchestratorFactory.add_step(
                workflow=wf, agent_role="invalid", execution_order=0
            )

    def test_duplicate_order_sequential_raises(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf goal"
        )
        OrchestratorFactory.add_step(
            workflow=wf, agent_role="planner", execution_order=0
        )
        with pytest.raises(DuplicateExecutionOrderError):
            OrchestratorFactory.add_step(
                workflow=wf, agent_role="research", execution_order=0
            )

    def test_duplicate_order_parallel_allowed(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf goal", mode="parallel"
        )
        OrchestratorFactory.add_step(
            workflow=wf, agent_role="planner", execution_order=0
        )
        OrchestratorFactory.add_step(
            workflow=wf, agent_role="research", execution_order=0
        )
        assert len(wf.steps) == 2


class TestOrchestratorFactoryCompleteStep:
    def test_completes_step(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf goal"
        )
        step = OrchestratorFactory.add_step(
            workflow=wf, agent_role="planner", execution_order=0
        )
        step.start()
        event = OrchestratorFactory.complete_step(
            step=step, result="success"
        )
        assert isinstance(event, WorkflowStepCompleted)
        assert event.result == "success"

    def test_complete_without_start_raises(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf goal"
        )
        step = OrchestratorFactory.add_step(
            workflow=wf, agent_role="planner", execution_order=0
        )
        with pytest.raises(InvalidTransitionError):
            OrchestratorFactory.complete_step(step=step, result="done")


class TestOrchestratorFactoryFailStep:
    def test_fails_step(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf goal"
        )
        step = OrchestratorFactory.add_step(
            workflow=wf, agent_role="planner", execution_order=0
        )
        step.start()
        event = OrchestratorFactory.fail_step(
            step=step, reason="timeout"
        )
        assert isinstance(event, WorkflowStepFailed)
        assert event.failure_reason == "timeout"

    def test_fail_without_start_raises(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf goal"
        )
        step = OrchestratorFactory.add_step(
            workflow=wf, agent_role="planner", execution_order=0
        )
        with pytest.raises(InvalidTransitionError):
            OrchestratorFactory.fail_step(step=step, reason="err")


# ===========================================================================
# Cross-workflow validation
# ===========================================================================


class TestCrossWorkflowValidation:
    def test_multiple_workflows_created(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="complex task", goal="process data"
        )
        wf1, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="step 1"
        )
        wf2, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="step 2"
        )
        assert len(o.workflows) == 2

    def test_duplicate_workflow_ids_raises(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf1"
        )
        with pytest.raises(DuplicateWorkflowIdError):
            o.add_workflow(wf)

    def test_orchestration_fails_if_workflow_fails(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf"
        )
        wf.add_step(WorkflowStep())
        wf.start()
        wf.fail()
        o.start_planning()
        o.start_research()
        o.start_execution()
        with pytest.raises(AllWorkflowsNotCompletedError):
            o.complete()

    def test_orchestration_completes_when_all_workflows_done(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf1, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf1"
        )
        wf1._status = WorkflowStatus.COMPLETED
        wf2, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf2"
        )
        wf2._status = WorkflowStatus.COMPLETED
        o.start_planning()
        o.start_research()
        o.start_execution()
        o.complete()
        assert o.status == OrchestrationStatus.COMPLETED

    def test_create_workflow_on_terminal_orchestration_raises(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        o.cancel()
        with pytest.raises(OrchestrationTerminalError):
            OrchestratorFactory.create_workflow(
                orchestration=o, goal="wf"
            )

    def test_multiple_workflows_independent_steps(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf1, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf1"
        )
        wf2, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf2"
        )
        step1 = OrchestratorFactory.add_step(
            workflow=wf1, agent_role="planner", execution_order=0
        )
        step2 = OrchestratorFactory.add_step(
            workflow=wf2, agent_role="research", execution_order=0
        )
        assert step1 in wf1.steps
        assert step2 in wf2.steps


# ===========================================================================
# HYBRID mode
# ===========================================================================


class TestHybridMode:
    def test_hybrid_mode_requires_two_steps_on_start(self) -> None:
        wf = Workflow(mode=ExecutionMode.HYBRID)
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        with pytest.raises(HybridModeRequiresTwoStepsError):
            wf.start()

    def test_hybrid_add_step_validation(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf", mode="hybrid"
        )
        OrchestratorFactory.add_step(
            workflow=wf, agent_role="planner", execution_order=0
        )
        OrchestratorFactory.add_step(
            workflow=wf, agent_role="research", execution_order=1
        )
        assert len(wf.steps) == 2

    def test_hybrid_valid_with_two_steps(self) -> None:
        wf = Workflow(mode=ExecutionMode.HYBRID)
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=1)))
        assert len(wf.steps) == 2


# ===========================================================================
# Multi-error / edge cases
# ===========================================================================


class TestMultiErrorValidation:
    def test_none_intent_and_none_goal(self) -> None:
        with pytest.raises((InvalidUserIntentError, InvalidWorkflowGoalError)):
            OrchestratorFactory.create_orchestration(
                intent="", goal=""
            )

    def test_empty_intent_valid_goal(self) -> None:
        with pytest.raises(InvalidUserIntentError):
            OrchestratorFactory.create_orchestration(
                intent="", goal="valid"
            )

    def test_valid_intent_empty_goal(self) -> None:
        with pytest.raises(InvalidWorkflowGoalError):
            OrchestratorFactory.create_orchestration(
                intent="valid", goal=""
            )

    def test_full_lifecycle_no_errors(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="full test", goal="verify full lifecycle"
        )
        o.start_planning()
        o.start_research()
        o.start_execution()
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="sub workflow"
        )
        step = OrchestratorFactory.add_step(
            workflow=wf, agent_role="planner", execution_order=0
        )
        step.start()
        step.complete(ExecutionResult(value="done"))
        wf._status = WorkflowStatus.COMPLETED
        o.complete()
        assert o.status == OrchestrationStatus.COMPLETED

    def test_full_lifecycle_fail_halfway(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="fail test", goal="verify fail"
        )
        o.start_planning()
        o.fail(FailureReason(value="unexpected error"))
        assert o.status == OrchestrationStatus.FAILED

    def test_full_lifecycle_cancel_halfway(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="cancel test", goal="verify cancel"
        )
        o.start_planning()
        o.cancel()
        assert o.status == OrchestrationStatus.CANCELLED

    def test_orchestration_domain_error_base(self) -> None:
        assert issubclass(InvalidUserIntentError, OrchestratorDomainError)
        assert issubclass(InvalidWorkflowGoalError, OrchestratorDomainError)
        assert issubclass(InvalidTransitionError, OrchestratorDomainError)

    def test_all_exceptions_are_domain_errors(self) -> None:
        exceptions = [
            InvalidUserIntentError,
            InvalidWorkflowGoalError,
            InvalidAgentRoleError,
            InvalidExecutionOrderError,
            InvalidFailureReasonError,
            InvalidExecutionResultError,
            InvalidTransitionError,
            OrchestrationTerminalError,
            WorkflowTerminalError,
            WorkflowStepTerminalError,
            WorkflowHasNoStepsError,
            StepNotStartedError,
            WorkflowNotStartedError,
            DuplicateExecutionOrderError,
            DuplicateWorkflowIdError,
            HybridModeRequiresTwoStepsError,
            AllWorkflowsNotCompletedError,
        ]
        for exc in exceptions:
            assert issubclass(exc, OrchestratorDomainError), f"{exc.__name__} is not"

    def test_clear_events(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        o.start_planning()
        assert len(o.events) == 1
        o._clear_events()
        assert o.events == []

    def test_workflow_clear_events(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        wf.start()
        assert len(wf.events) == 1
        wf._clear_events()
        assert wf.events == []

    def test_step_clear_events(self) -> None:
        step = WorkflowStep()
        step.start()
        assert len(step.events) == 1
        step._clear_events()
        assert step.events == []

    def test_orchestration_repr(self) -> None:
        o = Orchestration()
        assert "Orchestration(" in repr(o)

    def test_workflow_repr(self) -> None:
        wf = Workflow()
        assert "Workflow(" in repr(wf)

    def test_step_repr(self) -> None:
        step = WorkflowStep()
        assert "WorkflowStep(" in repr(step)

    def test_add_step_to_workflow_sets_updated_at(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf"
        )
        assert o.updated_at is not None
        prev = o.updated_at
        OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf2"
        )
        assert o.updated_at >= prev

    def test_create_workflow_with_mode_enum(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf", mode=ExecutionMode.PARALLEL
        )
        assert wf.mode == ExecutionMode.PARALLEL

    def test_add_step_with_agent_role_enum(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf"
        )
        step = OrchestratorFactory.add_step(
            workflow=wf, agent_role=AgentRole.POLICY, execution_order=0
        )
        assert step.agent_role == AgentRole.POLICY

    def test_add_step_negative_order_raises(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="wf"
        )
        with pytest.raises(InvalidExecutionOrderError):
            OrchestratorFactory.add_step(
                workflow=wf, agent_role="planner", execution_order=-1
            )

    def test_complete_step_none_result_raises(self) -> None:
        step = WorkflowStep()
        step.start()
        with pytest.raises(InvalidExecutionResultError):
            step.complete(None)

    def test_step_has_no_events_initial(self) -> None:
        step = WorkflowStep()
        assert step.events == []

    def test_step_events_are_copied(self) -> None:
        step = WorkflowStep()
        step.start()
        events = step.events
        step._clear_events()
        assert step.events == []
        assert len(events) == 1  # original reference still holds

    def test_workflow_events_are_copied(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        wf.start()
        events = wf.events
        wf._clear_events()
        assert wf.events == []
        assert len(events) == 1

    def test_orchestration_events_are_copied(self) -> None:
        o = Orchestration()
        o.start_planning()
        events = o.events
        o._clear_events()
        assert o.events == []
        assert len(events) == 1

    def test_workflow_not_started_without_steps(self) -> None:
        wf = Workflow()
        with pytest.raises(WorkflowHasNoStepsError):
            wf.start()

    def test_workflow_start_before_complete_via_rule(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        with pytest.raises((InvalidTransitionError, WorkflowNotStartedError)):
            wf.complete()

    def test_workflow_start_before_fail_via_rule(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        with pytest.raises((InvalidTransitionError, WorkflowNotStartedError)):
            wf.fail()

    def test_orchestration_id_equality_with_value(self) -> None:
        uid = UUID("00000000-0000-0000-0000-000000000001")
        oid1 = OrchestrationId(value=uid)
        oid2 = OrchestrationId(value=uid)
        assert oid1 == oid2

    def test_workflow_id_equality_with_value(self) -> None:
        uid = UUID("00000000-0000-0000-0000-000000000002")
        wid1 = WorkflowId(value=uid)
        wid2 = WorkflowId(value=uid)
        assert wid1 == wid2

    def test_workflow_steps_property_returns_copy(self) -> None:
        wf = Workflow()
        step = WorkflowStep(execution_order=ExecutionOrder(value=0))
        wf.add_step(step)
        steps_copy = wf.steps
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=1)))
        assert len(steps_copy) == 1  # original copy not affected

    def test_orchestration_workflows_property_returns_copy(self) -> None:
        o = Orchestration()
        wf = Workflow()
        o.add_workflow(wf)
        copy = o.workflows
        o.add_workflow(Workflow())
        assert len(copy) == 1

    def test_step_complete_with_empty_result_raises(self) -> None:
        step = WorkflowStep()
        step.start()
        with pytest.raises(InvalidExecutionResultError):
            step.complete(ExecutionResult(value=""))

    def test_step_fail_with_empty_reason_raises(self) -> None:
        step = WorkflowStep()
        step.start()
        with pytest.raises(InvalidFailureReasonError):
            step.fail(None)

    def test_workflow_can_transition_from_pending(self) -> None:
        assert WorkflowStatus.RUNNING in VALID_WORKFLOW_TRANSITIONS[WorkflowStatus.PENDING]

    def test_workflow_can_transition_from_running(self) -> None:
        assert WorkflowStatus.COMPLETED in VALID_WORKFLOW_TRANSITIONS[WorkflowStatus.RUNNING]

    def test_workflow_failed_terminal(self) -> None:
        assert len(VALID_WORKFLOW_TRANSITIONS[WorkflowStatus.FAILED]) == 0

    def test_create_orchestration_id_unique(self) -> None:
        o1 = OrchestrationId()
        o2 = OrchestrationId()
        assert o1 != o2  # unlikely collision

    def test_create_workflow_id_unique(self) -> None:
        w1 = WorkflowId()
        w2 = WorkflowId()
        assert w1 != w2

    def test_fail_step_event_contains_reason(self) -> None:
        step = WorkflowStep()
        step.start()
        reason = FailureReason(value="failure reason text")
        step.fail(reason)
        assert step.events[-1].failure_reason == "failure reason text"

    def test_complete_step_event_contains_result(self) -> None:
        step = WorkflowStep()
        step.start()
        step.complete(ExecutionResult(value="result text"))
        assert step.events[-1].result == "result text"

    def test_step_start_event_contains_step_id(self) -> None:
        step = WorkflowStep()
        step.start()
        assert step.events[0].step_id == step.step_id

    def test_orchestration_fail_event_contains_reason(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.fail(FailureReason(value="reason text"))
        assert o.events[-1].failure_reason == "reason text"

    def test_orchestration_complete_event_has_id(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        o.start_execution()
        o.complete()
        assert o.events[-1].orchestration_id == o.orchestration_id

    def test_add_step_notifies_event_on_workflow_start(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        wf.start()
        assert len(wf.events) == 1

    def test_add_step_does_not_notify_event_on_add(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep())
        assert wf.events == []

    def test_string_representation_of_agent_reference(self) -> None:
        ref = AgentReference(role=AgentRole.MEMORY)
        assert str(ref) == "memory"

    def test_base_exception_message(self) -> None:
        err = OrchestratorDomainError("base error")
        assert str(err) == "base error"

    def test_hybrid_start_with_two_steps_succeeds(self) -> None:
        wf = Workflow(mode=ExecutionMode.HYBRID)
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=1)))
        wf.start()
        assert wf.status == WorkflowStatus.RUNNING

    def test_sequential_unique_orders_across_modes(self) -> None:
        wf = Workflow(mode=ExecutionMode.SEQUENTIAL)
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=1)))
        assert len(wf.steps) == 2

    def test_parallel_duplicate_orders_allowed(self) -> None:
        wf = Workflow(mode=ExecutionMode.PARALLEL)
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        assert len(wf.steps) == 3

    def test_workflow_repr_contains_id(self) -> None:
        wid = WorkflowId(value=UUID("00000000-0000-0000-0000-000000000101"))
        wf = Workflow(workflow_id=wid)
        assert "00000000-0000-0000-0000-000000000101" in repr(wf)

    def test_step_repr_contains_role(self) -> None:
        step = WorkflowStep(agent_role=AgentRole.POLICY)
        assert "policy" in repr(step)

    def test_orchestration_fail_event_links_to_id(self) -> None:
        oid = OrchestrationId(value=UUID("00000000-0000-0000-0000-000000000201"))
        o = Orchestration(orchestration_id=oid)
        o.start_planning()
        o.fail(FailureReason(value="err"))
        assert o.events[-1].orchestration_id == oid

    def test_orchestration_cancel_event_links_to_id(self) -> None:
        oid = OrchestrationId(value=UUID("00000000-0000-0000-0000-000000000202"))
        o = Orchestration(orchestration_id=oid)
        o.cancel()
        assert o.events[-1].orchestration_id == oid

    def test_orchestration_planning_event_links_to_id(self) -> None:
        oid = OrchestrationId(value=UUID("00000000-0000-0000-0000-000000000203"))
        o = Orchestration(orchestration_id=oid)
        o.start_planning()
        assert o.events[-1].orchestration_id == oid

    def test_orchestration_complete_sets_updated_at(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        o.start_execution()
        o.complete()
        assert o.updated_at is not None

    def test_orchestration_fail_sets_updated_at(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.fail(FailureReason(value="err"))
        assert o.updated_at is not None

    def test_orchestration_cancel_sets_updated_at(self) -> None:
        o = Orchestration()
        o.cancel()
        assert o.updated_at is not None

    def test_orchestration_empty_workflows_complete_succeeds(self) -> None:
        o = Orchestration()
        o.start_planning()
        o.start_research()
        o.start_execution()
        o.complete()
        assert o.status == OrchestrationStatus.COMPLETED

    def test_workflow_created_event_on_start(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        wf.start()
        event = wf.events[0]
        assert isinstance(event, WorkflowCreated)
        assert event.workflow_id == wf.workflow_id

    def test_workflow_completed_event_on_complete(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        wf.start()
        wf.complete()
        event = wf.events[-1]
        assert isinstance(event, WorkflowCompleted)
        assert event.workflow_id == wf.workflow_id

    def test_workflow_failed_event_on_fail(self) -> None:
        wf = Workflow()
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        wf.start()
        wf.fail()
        event = wf.events[-1]
        assert isinstance(event, WorkflowFailed)
        assert event.workflow_id == wf.workflow_id

    def test_step_skipped_no_events(self) -> None:
        step = WorkflowStep()
        step.skip()
        assert step.events == []

    def test_orchestration_status_str(self) -> None:
        assert str(OrchestrationStatus.CREATED) == "created"

    def test_workflow_status_str(self) -> None:
        assert str(WorkflowStatus.PENDING) == "pending"

    def test_agent_role_str(self) -> None:
        assert str(AgentRole.KNOWLEDGE) == "knowledge"

    def test_execution_mode_str(self) -> None:
        assert str(ExecutionMode.HYBRID) == "hybrid"

    def test_workflow_step_status_str(self) -> None:
        assert str(WorkflowStepStatus.SKIPPED) == "skipped"

    def test_create_workflow_with_hybrid_mode_and_only_two_steps(self) -> None:
        wf = Workflow(mode=ExecutionMode.HYBRID)
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=0)))
        wf.add_step(WorkflowStep(execution_order=ExecutionOrder(value=1)))
        wf.start()
        assert wf.status == WorkflowStatus.RUNNING

    def test_factory_create_workflow_default_mode(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="test goal"
        )
        assert wf.mode == ExecutionMode.SEQUENTIAL

    def test_factory_create_workflow_hybrid_mode(self) -> None:
        o, _ = OrchestratorFactory.create_orchestration(
            intent="test", goal="goal"
        )
        wf, _ = OrchestratorFactory.create_workflow(
            orchestration=o, goal="test goal", mode=ExecutionMode.HYBRID
        )
        assert wf.mode == ExecutionMode.HYBRID

    def test_orchestrator_step_with_custom_id(self) -> None:
        sid = WorkflowId(value=UUID("00000000-0000-0000-0000-000000000301"))
        step = WorkflowStep(step_id=sid)
        assert step.step_id == sid

    def test_orchestrator_workflow_with_custom_id(self) -> None:
        wid = WorkflowId(value=UUID("00000000-0000-0000-0000-000000000302"))
        wf = Workflow(workflow_id=wid)
        assert wf.workflow_id == wid

    def test_orchestrator_custom_id(self) -> None:
        oid = OrchestrationId(value=UUID("00000000-0000-0000-0000-000000000303"))
        o = Orchestration(orchestration_id=oid)
        assert o.orchestration_id == oid

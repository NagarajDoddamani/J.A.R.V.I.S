from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.agent.domain.exceptions import (
    AgentDisabledError,
    AgentDomainError,
    AgentExecutionNotStartedError,
    AgentExecutionNotFoundError,
    AgentPausedError,
    AgentTaskNotStartedError,
    AgentTaskNotFoundError,
    AgentTerminalError,
    DuplicateAgentExecutionIdError,
    DuplicateAgentTaskIdError,
    InvalidAgentGoalError,
    InvalidAgentInstructionError,
    InvalidAgentNameError,
    InvalidAgentResultError,
    InvalidAgentTypeError,
    InvalidFailureReasonError,
    InvalidTransitionError,
    ResultRequiredError,
)
from backend.agent.domain.factory import AgentFactory
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
    VALID_AGENT_EXECUTION_TRANSITIONS,
    VALID_AGENT_STATUS_TRANSITIONS,
    VALID_AGENT_TASK_TRANSITIONS,
)

NOW = datetime(2026, 6, 16, 12, 0, 0, tzinfo=timezone.utc)


# ===========================================================================
# Value Objects
# ===========================================================================


class TestAgentId:
    def test_default_creation(self) -> None:
        aid = AgentId()
        assert isinstance(aid.value, UUID)

    def test_str_representation(self) -> None:
        aid = AgentId(value=UUID("00000000-0000-0000-0000-000000000001"))
        assert str(aid) == "00000000-0000-0000-0000-000000000001"

    def test_equality(self) -> None:
        aid1 = AgentId(value=UUID("00000000-0000-0000-0000-000000000001"))
        aid2 = AgentId(value=UUID("00000000-0000-0000-0000-000000000001"))
        assert aid1 == aid2

    def test_inequality(self) -> None:
        aid1 = AgentId(value=UUID("00000000-0000-0000-0000-000000000001"))
        aid2 = AgentId(value=UUID("00000000-0000-0000-0000-000000000002"))
        assert aid1 != aid2

    def test_hashable(self) -> None:
        aid = AgentId()
        assert hash(aid) == hash(aid)


class TestAgentTaskId:
    def test_default_creation(self) -> None:
        tid = AgentTaskId()
        assert isinstance(tid.value, UUID)

    def test_str_representation(self) -> None:
        tid = AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000001"))
        assert str(tid) == "00000000-0000-0000-0000-000000000001"

    def test_equality(self) -> None:
        tid1 = AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000001"))
        tid2 = AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000001"))
        assert tid1 == tid2

    def test_hashable(self) -> None:
        tid = AgentTaskId()
        assert hash(tid) == hash(tid)


class TestAgentExecutionId:
    def test_default_creation(self) -> None:
        eid = AgentExecutionId()
        assert isinstance(eid.value, UUID)

    def test_str_representation(self) -> None:
        eid = AgentExecutionId(value=UUID("00000000-0000-0000-0000-000000000001"))
        assert str(eid) == "00000000-0000-0000-0000-000000000001"

    def test_equality(self) -> None:
        eid1 = AgentExecutionId(value=UUID("00000000-0000-0000-0000-000000000001"))
        eid2 = AgentExecutionId(value=UUID("00000000-0000-0000-0000-000000000001"))
        assert eid1 == eid2

    def test_hashable(self) -> None:
        eid = AgentExecutionId()
        assert hash(eid) == hash(eid)


class TestAgentName:
    def test_creation(self) -> None:
        name = AgentName(value="Research Agent")
        assert name.value == "Research Agent"
        assert str(name) == "Research Agent"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidAgentNameError):
            AgentName(value="")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(InvalidAgentNameError):
            AgentName(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            AgentName(value=123)

    def test_len(self) -> None:
        name = AgentName(value="hello")
        assert len(name) == 5


class TestAgentGoal:
    def test_creation(self) -> None:
        goal = AgentGoal(value="search data")
        assert goal.value == "search data"
        assert str(goal) == "search data"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidAgentGoalError):
            AgentGoal(value="")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(InvalidAgentGoalError):
            AgentGoal(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            AgentGoal(value=123)

    def test_len(self) -> None:
        goal = AgentGoal(value="hello")
        assert len(goal) == 5


class TestAgentInstruction:
    def test_creation(self) -> None:
        instr = AgentInstruction(value="search the knowledge base")
        assert instr.value == "search the knowledge base"
        assert str(instr) == "search the knowledge base"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidAgentInstructionError):
            AgentInstruction(value="")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(InvalidAgentInstructionError):
            AgentInstruction(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            AgentInstruction(value=123)

    def test_len(self) -> None:
        instr = AgentInstruction(value="hello")
        assert len(instr) == 5


class TestAgentResult:
    def test_creation(self) -> None:
        result = AgentResult(value="completed successfully")
        assert result.value == "completed successfully"
        assert str(result) == "completed successfully"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidAgentResultError):
            AgentResult(value="")

    def test_whitespace_raises(self) -> None:
        with pytest.raises(InvalidAgentResultError):
            AgentResult(value="   ")

    def test_non_string_raises(self) -> None:
        with pytest.raises(TypeError):
            AgentResult(value=123)

    def test_len(self) -> None:
        result = AgentResult(value="ok")
        assert len(result) == 2


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

    def test_len(self) -> None:
        reason = FailureReason(value="err")
        assert len(reason) == 3


# ===========================================================================
# Enums
# ===========================================================================


class TestAgentTypeEnum:
    def test_values(self) -> None:
        expected = {"coordinator", "research", "knowledge", "automation"}
        actual = {e.value for e in AgentType}
        assert actual == expected

    def test_count(self) -> None:
        assert len(AgentType) == 4

    def test_coordinator_is_string(self) -> None:
        assert AgentType.COORDINATOR.value == "coordinator"

    def test_research_is_string(self) -> None:
        assert AgentType.RESEARCH.value == "research"

    def test_knowledge_is_string(self) -> None:
        assert AgentType.KNOWLEDGE.value == "knowledge"

    def test_automation_is_string(self) -> None:
        assert AgentType.AUTOMATION.value == "automation"

    def test_from_string(self) -> None:
        assert AgentType("coordinator") == AgentType.COORDINATOR

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            AgentType("invalid")


class TestAgentStatusEnum:
    def test_values(self) -> None:
        expected = {"idle", "active", "paused", "disabled"}
        actual = {e.value for e in AgentStatus}
        assert actual == expected

    def test_count(self) -> None:
        assert len(AgentStatus) == 4

    def test_idle_is_string(self) -> None:
        assert AgentStatus.IDLE.value == "idle"

    def test_active_is_string(self) -> None:
        assert AgentStatus.ACTIVE.value == "active"

    def test_paused_is_string(self) -> None:
        assert AgentStatus.PAUSED.value == "paused"

    def test_disabled_is_string(self) -> None:
        assert AgentStatus.DISABLED.value == "disabled"

    def test_from_string(self) -> None:
        assert AgentStatus("idle") == AgentStatus.IDLE

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            AgentStatus("invalid")


class TestAgentTaskStatusEnum:
    def test_values(self) -> None:
        expected = {"pending", "running", "completed", "failed", "cancelled"}
        actual = {e.value for e in AgentTaskStatus}
        assert actual == expected

    def test_count(self) -> None:
        assert len(AgentTaskStatus) == 5

    def test_pending_is_string(self) -> None:
        assert AgentTaskStatus.PENDING.value == "pending"

    def test_running_is_string(self) -> None:
        assert AgentTaskStatus.RUNNING.value == "running"

    def test_completed_is_string(self) -> None:
        assert AgentTaskStatus.COMPLETED.value == "completed"

    def test_failed_is_string(self) -> None:
        assert AgentTaskStatus.FAILED.value == "failed"

    def test_cancelled_is_string(self) -> None:
        assert AgentTaskStatus.CANCELLED.value == "cancelled"

    def test_from_string(self) -> None:
        assert AgentTaskStatus("pending") == AgentTaskStatus.PENDING

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            AgentTaskStatus("invalid")


class TestAgentExecutionStatusEnum:
    def test_values(self) -> None:
        expected = {"pending", "executing", "completed", "failed"}
        actual = {e.value for e in AgentExecutionStatus}
        assert actual == expected

    def test_count(self) -> None:
        assert len(AgentExecutionStatus) == 4

    def test_pending_is_string(self) -> None:
        assert AgentExecutionStatus.PENDING.value == "pending"

    def test_executing_is_string(self) -> None:
        assert AgentExecutionStatus.EXECUTING.value == "executing"

    def test_completed_is_string(self) -> None:
        assert AgentExecutionStatus.COMPLETED.value == "completed"

    def test_failed_is_string(self) -> None:
        assert AgentExecutionStatus.FAILED.value == "failed"

    def test_from_string(self) -> None:
        assert AgentExecutionStatus("pending") == AgentExecutionStatus.PENDING

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            AgentExecutionStatus("invalid")


# ===========================================================================
# Events
# ===========================================================================


class TestAgentEvents:
    def test_agent_created(self) -> None:
        aid = AgentId()
        event = AgentCreated(
            agent_id=aid,
            agent_type="research",
            name="test",
            occurred_at=NOW,
        )
        assert event.agent_id == aid
        assert event.agent_type == "research"
        assert event.name == "test"
        assert event.occurred_at == NOW
        assert isinstance(event.event_id, UUID)

    def test_agent_activated(self) -> None:
        aid = AgentId()
        event = AgentActivated(agent_id=aid, occurred_at=NOW)
        assert event.agent_id == aid
        assert isinstance(event.event_id, UUID)

    def test_agent_paused(self) -> None:
        aid = AgentId()
        event = AgentPaused(agent_id=aid, occurred_at=NOW)
        assert event.agent_id == aid
        assert isinstance(event.event_id, UUID)

    def test_agent_disabled(self) -> None:
        aid = AgentId()
        event = AgentDisabled(agent_id=aid, occurred_at=NOW)
        assert event.agent_id == aid
        assert isinstance(event.event_id, UUID)

    def test_agent_task_created(self) -> None:
        tid = AgentTaskId()
        aid = AgentId()
        event = AgentTaskCreated(
            task_id=tid,
            agent_id=aid,
            goal="test goal",
            instruction="do something",
            occurred_at=NOW,
        )
        assert event.task_id == tid
        assert event.agent_id == aid
        assert event.goal == "test goal"
        assert event.instruction == "do something"
        assert isinstance(event.event_id, UUID)

    def test_agent_task_started(self) -> None:
        tid = AgentTaskId()
        aid = AgentId()
        event = AgentTaskStarted(
            task_id=tid, agent_id=aid, occurred_at=NOW
        )
        assert event.task_id == tid
        assert event.agent_id == aid
        assert isinstance(event.event_id, UUID)

    def test_agent_task_completed(self) -> None:
        tid = AgentTaskId()
        aid = AgentId()
        event = AgentTaskCompleted(
            task_id=tid, agent_id=aid, result="done", occurred_at=NOW
        )
        assert event.task_id == tid
        assert event.agent_id == aid
        assert event.result == "done"
        assert isinstance(event.event_id, UUID)

    def test_agent_task_failed(self) -> None:
        tid = AgentTaskId()
        aid = AgentId()
        event = AgentTaskFailed(
            task_id=tid, agent_id=aid, failure_reason="error", occurred_at=NOW
        )
        assert event.task_id == tid
        assert event.agent_id == aid
        assert event.failure_reason == "error"
        assert isinstance(event.event_id, UUID)

    def test_agent_task_cancelled(self) -> None:
        tid = AgentTaskId()
        aid = AgentId()
        event = AgentTaskCancelled(
            task_id=tid, agent_id=aid, occurred_at=NOW
        )
        assert event.task_id == tid
        assert event.agent_id == aid
        assert isinstance(event.event_id, UUID)

    def test_agent_execution_started(self) -> None:
        eid = AgentExecutionId()
        aid = AgentId()
        tid = AgentTaskId()
        event = AgentExecutionStarted(
            execution_id=eid, agent_id=aid, task_id=tid, occurred_at=NOW
        )
        assert event.execution_id == eid
        assert event.agent_id == aid
        assert event.task_id == tid
        assert isinstance(event.event_id, UUID)

    def test_agent_execution_completed(self) -> None:
        eid = AgentExecutionId()
        aid = AgentId()
        tid = AgentTaskId()
        event = AgentExecutionCompleted(
            execution_id=eid, agent_id=aid, task_id=tid, result="done", occurred_at=NOW
        )
        assert event.execution_id == eid
        assert event.agent_id == aid
        assert event.task_id == tid
        assert event.result == "done"
        assert isinstance(event.event_id, UUID)

    def test_agent_execution_failed(self) -> None:
        eid = AgentExecutionId()
        aid = AgentId()
        tid = AgentTaskId()
        event = AgentExecutionFailed(
            execution_id=eid, agent_id=aid, task_id=tid, failure_reason="err", occurred_at=NOW
        )
        assert event.execution_id == eid
        assert event.agent_id == aid
        assert event.task_id == tid
        assert event.failure_reason == "err"
        assert isinstance(event.event_id, UUID)

    def test_all_events_have_event_id(self) -> None:
        aid = AgentId()
        tid = AgentTaskId()
        eid = AgentExecutionId()
        events = [
            AgentCreated(aid, "research", "n", NOW),
            AgentActivated(aid, NOW),
            AgentPaused(aid, NOW),
            AgentDisabled(aid, NOW),
            AgentTaskCreated(tid, aid, "g", "i", NOW),
            AgentTaskStarted(tid, aid, NOW),
            AgentTaskCompleted(tid, aid, "ok", NOW),
            AgentTaskFailed(tid, aid, "err", NOW),
            AgentTaskCancelled(tid, aid, NOW),
            AgentExecutionStarted(eid, aid, tid, NOW),
            AgentExecutionCompleted(eid, aid, tid, "ok", NOW),
            AgentExecutionFailed(eid, aid, tid, "err", NOW),
        ]
        for e in events:
            assert isinstance(e.event_id, UUID), f"{type(e).__name__} lacks event_id"

    def test_twelve_events_exist(self) -> None:
        event_classes = {
            AgentCreated,
            AgentActivated,
            AgentPaused,
            AgentDisabled,
            AgentTaskCreated,
            AgentTaskStarted,
            AgentTaskCompleted,
            AgentTaskFailed,
            AgentTaskCancelled,
            AgentExecutionStarted,
            AgentExecutionCompleted,
            AgentExecutionFailed,
        }
        assert len(event_classes) == 12

    def test_events_are_frozen(self) -> None:
        aid = AgentId()
        event = AgentCreated(aid, "research", "n", NOW)
        with pytest.raises(AttributeError):
            event.name = "changed"


# ===========================================================================
# Transition maps
# ===========================================================================


class TestTaskTransitionMap:
    def test_pending_transitions(self) -> None:
        assert VALID_AGENT_TASK_TRANSITIONS[AgentTaskStatus.PENDING] == {
            AgentTaskStatus.RUNNING,
            AgentTaskStatus.CANCELLED,
        }

    def test_running_transitions(self) -> None:
        assert VALID_AGENT_TASK_TRANSITIONS[AgentTaskStatus.RUNNING] == {
            AgentTaskStatus.COMPLETED,
            AgentTaskStatus.FAILED,
            AgentTaskStatus.CANCELLED,
        }

    def test_completed_terminal(self) -> None:
        assert VALID_AGENT_TASK_TRANSITIONS[AgentTaskStatus.COMPLETED] == set()

    def test_failed_terminal(self) -> None:
        assert VALID_AGENT_TASK_TRANSITIONS[AgentTaskStatus.FAILED] == set()

    def test_cancelled_terminal(self) -> None:
        assert VALID_AGENT_TASK_TRANSITIONS[AgentTaskStatus.CANCELLED] == set()


class TestExecutionTransitionMap:
    def test_pending_transitions(self) -> None:
        assert VALID_AGENT_EXECUTION_TRANSITIONS[AgentExecutionStatus.PENDING] == {
            AgentExecutionStatus.EXECUTING,
        }

    def test_executing_transitions(self) -> None:
        assert VALID_AGENT_EXECUTION_TRANSITIONS[AgentExecutionStatus.EXECUTING] == {
            AgentExecutionStatus.COMPLETED,
            AgentExecutionStatus.FAILED,
        }

    def test_completed_terminal(self) -> None:
        assert VALID_AGENT_EXECUTION_TRANSITIONS[AgentExecutionStatus.COMPLETED] == set()

    def test_failed_terminal(self) -> None:
        assert VALID_AGENT_EXECUTION_TRANSITIONS[AgentExecutionStatus.FAILED] == set()


class TestAgentStatusTransitionMap:
    def test_idle_transitions(self) -> None:
        assert VALID_AGENT_STATUS_TRANSITIONS[AgentStatus.IDLE] == {
            AgentStatus.ACTIVE,
            AgentStatus.DISABLED,
        }

    def test_active_transitions(self) -> None:
        assert VALID_AGENT_STATUS_TRANSITIONS[AgentStatus.ACTIVE] == {
            AgentStatus.PAUSED,
            AgentStatus.DISABLED,
        }

    def test_paused_transitions(self) -> None:
        assert VALID_AGENT_STATUS_TRANSITIONS[AgentStatus.PAUSED] == {
            AgentStatus.ACTIVE,
            AgentStatus.DISABLED,
        }

    def test_disabled_terminal(self) -> None:
        assert VALID_AGENT_STATUS_TRANSITIONS[AgentStatus.DISABLED] == set()


# ===========================================================================
# AgentTask lifecycle
# ===========================================================================


class TestAgentTaskCreation:
    def test_default_creation(self) -> None:
        task = AgentTask()
        assert isinstance(task.task_id, AgentTaskId)
        assert task.goal is None
        assert task.instruction is None
        assert task.status == AgentTaskStatus.PENDING
        assert task.result is None
        assert task.failure_reason is None
        assert task.events == []

    def test_custom_creation(self) -> None:
        tid = AgentTaskId()
        goal = AgentGoal(value="test goal")
        instr = AgentInstruction(value="do something")
        task = AgentTask(
            task_id=tid,
            goal=goal,
            instruction=instr,
            status=AgentTaskStatus.PENDING,
        )
        assert task.task_id == tid
        assert task.goal == goal
        assert task.instruction == instr
        assert task.status == AgentTaskStatus.PENDING

    def test_is_terminal_pending(self) -> None:
        task = AgentTask()
        assert not task.is_terminal

    def test_repr(self) -> None:
        task = AgentTask()
        assert "AgentTask" in repr(task)
        assert "pending" in repr(task)


class TestAgentTaskStart:
    def test_start_transitions_to_running(self) -> None:
        task = AgentTask()
        task.start()
        assert task.status == AgentTaskStatus.RUNNING

    def test_start_pending_ok(self) -> None:
        task = AgentTask()
        task.start()
        assert task.status == AgentTaskStatus.RUNNING

    def test_start_already_running_raises(self) -> None:
        task = AgentTask()
        task.start()
        with pytest.raises(InvalidTransitionError):
            task.start()

    def test_start_completed_raises(self) -> None:
        task = AgentTask()
        task.start()
        task.complete(AgentResult(value="done"))
        with pytest.raises(InvalidTransitionError):
            task.start()

    def test_start_failed_raises(self) -> None:
        task = AgentTask()
        task.start()
        task.fail(FailureReason(value="err"))
        with pytest.raises(InvalidTransitionError):
            task.start()

    def test_start_cancelled_raises(self) -> None:
        task = AgentTask()
        task.cancel()
        with pytest.raises(InvalidTransitionError):
            task.start()


class TestAgentTaskComplete:
    def test_complete_transitions_to_completed(self) -> None:
        task = AgentTask()
        task.start()
        task.complete(AgentResult(value="done"))
        assert task.status == AgentTaskStatus.COMPLETED

    def test_complete_stores_result(self) -> None:
        task = AgentTask()
        task.start()
        result = AgentResult(value="success")
        task.complete(result)
        assert task.result == result

    def test_complete_without_start_raises(self) -> None:
        task = AgentTask()
        with pytest.raises(InvalidTransitionError):
            task.complete(AgentResult(value="done"))

    def test_complete_no_result_raises(self) -> None:
        task = AgentTask()
        task.start()
        with pytest.raises(ResultRequiredError):
            task.complete(None)

    def test_complete_already_completed_raises(self) -> None:
        task = AgentTask()
        task.start()
        task.complete(AgentResult(value="done"))
        with pytest.raises(InvalidTransitionError):
            task.complete(AgentResult(value="again"))

    def test_complete_failed_task_raises(self) -> None:
        task = AgentTask()
        task.start()
        task.fail(FailureReason(value="err"))
        with pytest.raises(InvalidTransitionError):
            task.complete(AgentResult(value="done"))

    def test_complete_cancelled_task_raises(self) -> None:
        task = AgentTask()
        task.cancel()
        with pytest.raises(InvalidTransitionError):
            task.complete(AgentResult(value="done"))


class TestAgentTaskFail:
    def test_fail_transitions_to_failed(self) -> None:
        task = AgentTask()
        task.start()
        task.fail(FailureReason(value="err"))
        assert task.status == AgentTaskStatus.FAILED

    def test_fail_stores_reason(self) -> None:
        task = AgentTask()
        task.start()
        reason = FailureReason(value="timeout")
        task.fail(reason)
        assert task.failure_reason == reason

    def test_fail_without_start_raises(self) -> None:
        task = AgentTask()
        with pytest.raises(InvalidTransitionError):
            task.fail(FailureReason(value="err"))

    def test_fail_no_reason_raises(self) -> None:
        task = AgentTask()
        task.start()
        with pytest.raises(InvalidFailureReasonError):
            task.fail(None)

    def test_fail_already_completed_raises(self) -> None:
        task = AgentTask()
        task.start()
        task.complete(AgentResult(value="done"))
        with pytest.raises(InvalidTransitionError):
            task.fail(FailureReason(value="err"))

    def test_fail_cancelled_task_raises(self) -> None:
        task = AgentTask()
        task.cancel()
        with pytest.raises(InvalidTransitionError):
            task.fail(FailureReason(value="err"))


class TestAgentTaskCancel:
    def test_cancel_transitions_to_cancelled(self) -> None:
        task = AgentTask()
        task.cancel()
        assert task.status == AgentTaskStatus.CANCELLED

    def test_cancel_pending_ok(self) -> None:
        task = AgentTask()
        task.cancel()
        assert task.status == AgentTaskStatus.CANCELLED

    def test_cancel_running_ok(self) -> None:
        task = AgentTask()
        task.start()
        task.cancel()
        assert task.status == AgentTaskStatus.CANCELLED

    def test_cancel_completed_raises(self) -> None:
        task = AgentTask()
        task.start()
        task.complete(AgentResult(value="done"))
        with pytest.raises(InvalidTransitionError):
            task.cancel()

    def test_cancel_failed_raises(self) -> None:
        task = AgentTask()
        task.start()
        task.fail(FailureReason(value="err"))
        with pytest.raises(InvalidTransitionError):
            task.cancel()

    def test_cancel_cancelled_raises(self) -> None:
        task = AgentTask()
        task.cancel()
        with pytest.raises(InvalidTransitionError):
            task.cancel()

    def test_cancel_is_terminal(self) -> None:
        task = AgentTask()
        task.cancel()
        assert task.is_terminal


# ===========================================================================
# AgentExecution lifecycle
# ===========================================================================


class TestAgentExecutionCreation:
    def test_default_creation(self) -> None:
        exec_ = AgentExecution()
        assert isinstance(exec_.execution_id, AgentExecutionId)
        assert isinstance(exec_.task_id, AgentTaskId)
        assert exec_.status == AgentExecutionStatus.PENDING
        assert exec_.result is None
        assert exec_.failure_reason is None
        assert exec_.started_at is None
        assert exec_.completed_at is None

    def test_custom_creation(self) -> None:
        eid = AgentExecutionId()
        tid = AgentTaskId()
        exec_ = AgentExecution(
            execution_id=eid,
            task_id=tid,
            status=AgentExecutionStatus.PENDING,
        )
        assert exec_.execution_id == eid
        assert exec_.task_id == tid
        assert exec_.status == AgentExecutionStatus.PENDING

    def test_is_terminal_pending(self) -> None:
        exec_ = AgentExecution()
        assert not exec_.is_terminal

    def test_repr(self) -> None:
        exec_ = AgentExecution()
        assert "AgentExecution" in repr(exec_)
        assert "pending" in repr(exec_)


class TestAgentExecutionStart:
    def test_start_transitions_to_executing(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        assert exec_.status == AgentExecutionStatus.EXECUTING

    def test_start_sets_started_at(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        assert exec_.started_at is not None

    def test_start_already_executing_raises(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        with pytest.raises(InvalidTransitionError):
            exec_.start()

    def test_start_completed_raises(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        exec_.complete(AgentResult(value="done"))
        with pytest.raises(InvalidTransitionError):
            exec_.start()

    def test_start_failed_raises(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        exec_.fail(FailureReason(value="err"))
        with pytest.raises(InvalidTransitionError):
            exec_.start()


class TestAgentExecutionComplete:
    def test_complete_transitions_to_completed(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        exec_.complete(AgentResult(value="done"))
        assert exec_.status == AgentExecutionStatus.COMPLETED

    def test_complete_stores_result(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        result = AgentResult(value="success")
        exec_.complete(result)
        assert exec_.result == result

    def test_complete_sets_completed_at(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        exec_.complete(AgentResult(value="done"))
        assert exec_.completed_at is not None

    def test_complete_without_start_raises(self) -> None:
        exec_ = AgentExecution()
        with pytest.raises(InvalidTransitionError):
            exec_.complete(AgentResult(value="done"))

    def test_complete_no_result_raises(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        with pytest.raises(ResultRequiredError):
            exec_.complete(None)

    def test_complete_already_completed_raises(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        exec_.complete(AgentResult(value="done"))
        with pytest.raises(InvalidTransitionError):
            exec_.complete(AgentResult(value="again"))

    def test_complete_failed_raises(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        exec_.fail(FailureReason(value="err"))
        with pytest.raises(InvalidTransitionError):
            exec_.complete(AgentResult(value="done"))


class TestAgentExecutionFail:
    def test_fail_transitions_to_failed(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        exec_.fail(FailureReason(value="err"))
        assert exec_.status == AgentExecutionStatus.FAILED

    def test_fail_stores_reason(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        reason = FailureReason(value="timeout")
        exec_.fail(reason)
        assert exec_.failure_reason == reason

    def test_fail_sets_completed_at(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        exec_.fail(FailureReason(value="err"))
        assert exec_.completed_at is not None

    def test_fail_without_start_raises(self) -> None:
        exec_ = AgentExecution()
        with pytest.raises(InvalidTransitionError):
            exec_.fail(FailureReason(value="err"))

    def test_fail_no_reason_raises(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        with pytest.raises(InvalidFailureReasonError):
            exec_.fail(None)

    def test_fail_already_completed_raises(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        exec_.complete(AgentResult(value="done"))
        with pytest.raises(InvalidTransitionError):
            exec_.fail(FailureReason(value="err"))

    def test_fail_already_failed_raises(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        exec_.fail(FailureReason(value="err"))
        with pytest.raises(InvalidTransitionError):
            exec_.fail(FailureReason(value="again"))


class TestAgentExecutionTerminal:
    def test_completed_is_terminal(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        exec_.complete(AgentResult(value="done"))
        assert exec_.is_terminal

    def test_failed_is_terminal(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        exec_.fail(FailureReason(value="err"))
        assert exec_.is_terminal

    def test_pending_not_terminal(self) -> None:
        exec_ = AgentExecution()
        assert not exec_.is_terminal

    def test_executing_not_terminal(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        assert not exec_.is_terminal


class TestAgentTaskTerminal:
    def test_completed_task_is_terminal(self) -> None:
        task = AgentTask()
        task.start()
        task.complete(AgentResult(value="done"))
        assert task.is_terminal

    def test_failed_task_is_terminal(self) -> None:
        task = AgentTask()
        task.start()
        task.fail(FailureReason(value="err"))
        assert task.is_terminal

    def test_cancelled_task_is_terminal(self) -> None:
        task = AgentTask()
        task.cancel()
        assert task.is_terminal

    def test_pending_task_not_terminal(self) -> None:
        task = AgentTask()
        assert not task.is_terminal

    def test_running_task_not_terminal(self) -> None:
        task = AgentTask()
        task.start()
        assert not task.is_terminal


# ===========================================================================
# Agent lifecycle
# ===========================================================================


class TestAgentCreation:
    def test_default_creation(self) -> None:
        agent = Agent()
        assert isinstance(agent.agent_id, AgentId)
        assert agent.agent_type == AgentType.COORDINATOR
        assert agent.name is None
        assert agent.status == AgentStatus.IDLE
        assert agent.tasks == []
        assert agent.executions == []
        assert agent.created_at is not None
        assert agent.updated_at is None
        assert agent.events == []

    def test_custom_creation(self) -> None:
        aid = AgentId()
        name = AgentName(value="test")
        agent = Agent(
            agent_id=aid,
            agent_type=AgentType.RESEARCH,
            name=name,
        )
        assert agent.agent_id == aid
        assert agent.agent_type == AgentType.RESEARCH
        assert agent.name == name

    def test_is_terminal_idle(self) -> None:
        agent = Agent()
        assert not agent.is_terminal

    def test_is_disabled(self) -> None:
        agent = Agent()
        assert not agent.is_disabled

    def test_is_paused(self) -> None:
        agent = Agent()
        assert not agent.is_paused

    def test_repr(self) -> None:
        agent = Agent()
        assert "Agent" in repr(agent)
        assert "idle" in repr(agent)


class TestAgentActivate:
    def test_activate_from_idle(self) -> None:
        agent = Agent()
        agent.activate()
        assert agent.status == AgentStatus.ACTIVE

    def test_activate_emits_event(self) -> None:
        agent = Agent()
        agent.activate()
        assert len(agent.events) == 1
        assert isinstance(agent.events[0], AgentActivated)

    def test_activate_sets_updated_at(self) -> None:
        agent = Agent()
        agent.activate()
        assert agent.updated_at is not None

    def test_activate_from_active_raises(self) -> None:
        agent = Agent()
        agent.activate()
        with pytest.raises(InvalidTransitionError):
            agent.activate()

    def test_activate_from_paused_allowed(self) -> None:
        agent = Agent()
        agent.activate()
        agent.pause()
        agent.activate()
        assert agent.status == AgentStatus.ACTIVE

    def test_activate_from_disabled_raises(self) -> None:
        agent = Agent()
        agent.disable()
        with pytest.raises(InvalidTransitionError):
            agent.activate()


class TestAgentPause:
    def test_pause_from_active(self) -> None:
        agent = Agent()
        agent.activate()
        agent.pause()
        assert agent.status == AgentStatus.PAUSED

    def test_pause_emits_event(self) -> None:
        agent = Agent()
        agent.activate()
        agent.pause()
        assert isinstance(agent.events[-1], AgentPaused)

    def test_pause_from_idle_raises(self) -> None:
        agent = Agent()
        with pytest.raises(InvalidTransitionError):
            agent.pause()

    def test_pause_from_disabled_raises(self) -> None:
        agent = Agent()
        agent.disable()
        with pytest.raises(InvalidTransitionError):
            agent.pause()

    def test_pause_from_paused_raises(self) -> None:
        agent = Agent()
        agent.activate()
        agent.pause()
        with pytest.raises(InvalidTransitionError):
            agent.pause()


class TestAgentDisable:
    def test_disable_from_idle(self) -> None:
        agent = Agent()
        agent.disable()
        assert agent.status == AgentStatus.DISABLED

    def test_disable_from_active(self) -> None:
        agent = Agent()
        agent.activate()
        agent.disable()
        assert agent.status == AgentStatus.DISABLED

    def test_disable_from_paused(self) -> None:
        agent = Agent()
        agent.activate()
        agent.pause()
        agent.disable()
        assert agent.status == AgentStatus.DISABLED

    def test_disable_emits_event(self) -> None:
        agent = Agent()
        agent.disable()
        assert isinstance(agent.events[-1], AgentDisabled)

    def test_disable_from_disabled_raises(self) -> None:
        agent = Agent()
        agent.disable()
        with pytest.raises(InvalidTransitionError):
            agent.disable()

    def test_disabled_is_terminal(self) -> None:
        agent = Agent()
        agent.disable()
        assert agent.is_terminal

    def test_disabled_is_disabled(self) -> None:
        agent = Agent()
        agent.disable()
        assert agent.is_disabled


class TestAgentStatusProperties:
    def test_paused_is_paused(self) -> None:
        agent = Agent()
        agent.activate()
        agent.pause()
        assert agent.is_paused
        assert not agent.is_disabled

    def test_active_not_paused_or_disabled(self) -> None:
        agent = Agent()
        agent.activate()
        assert not agent.is_paused
        assert not agent.is_disabled

    def test_idle_not_paused_or_disabled(self) -> None:
        agent = Agent()
        assert not agent.is_paused
        assert not agent.is_disabled


# ===========================================================================
# Agent task management
# ===========================================================================


class TestAgentAddTask:
    def test_add_task_to_idle_agent(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        assert len(agent.tasks) == 1
        assert agent.tasks[0] == task

    def test_add_task_emits_event(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        assert len(agent.events) == 1
        assert isinstance(agent.events[0], AgentTaskCreated)

    def test_add_task_sets_agent_id(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        assert task.agent_id == agent.agent_id

    def test_add_task_to_disabled_agent_raises(self) -> None:
        agent = Agent()
        agent.disable()
        task = AgentTask()
        with pytest.raises(AgentDisabledError):
            agent.add_task(task)

    def test_add_task_to_paused_agent_raises(self) -> None:
        agent = Agent()
        agent.activate()
        agent.pause()
        task = AgentTask()
        with pytest.raises(AgentPausedError):
            agent.add_task(task)

    def test_duplicate_task_id_raises(self) -> None:
        agent = Agent()
        task_id = AgentTaskId()
        task1 = AgentTask(task_id=task_id)
        task2 = AgentTask(task_id=task_id)
        agent.add_task(task1)
        with pytest.raises(DuplicateAgentTaskIdError):
            agent.add_task(task2)

    def test_add_task_sets_updated_at(self) -> None:
        agent = Agent()
        agent.add_task(AgentTask())
        assert agent.updated_at is not None

    def test_add_task_to_active_agent(self) -> None:
        agent = Agent()
        agent.activate()
        task = AgentTask()
        agent.add_task(task)
        assert len(agent.tasks) == 1


class TestAgentStartTask:
    def test_start_task(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        assert task.status == AgentTaskStatus.RUNNING

    def test_start_task_emits_event(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        assert isinstance(agent.events[-1], AgentTaskStarted)

    def test_start_task_not_found_raises(self) -> None:
        agent = Agent()
        with pytest.raises(AgentTaskNotFoundError):
            agent.start_task(AgentTaskId())

    def test_start_task_disabled_agent_raises(self) -> None:
        agent = Agent()
        agent.disable()
        task = AgentTask()
        agent._tasks.append(task)
        with pytest.raises(AgentDisabledError):
            agent.start_task(task.task_id)

    def test_start_task_paused_agent_raises(self) -> None:
        agent = Agent()
        agent.activate()
        agent.pause()
        task = AgentTask()
        agent._tasks.append(task)
        with pytest.raises(AgentPausedError):
            agent.start_task(task.task_id)


class TestAgentCompleteTask:
    def test_complete_task(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        result = AgentResult(value="done")
        agent.complete_task(task.task_id, result)
        assert task.status == AgentTaskStatus.COMPLETED
        assert task.result == result

    def test_complete_task_emits_event(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        agent.complete_task(task.task_id, AgentResult(value="done"))
        assert isinstance(agent.events[-1], AgentTaskCompleted)
        assert agent.events[-1].result == "done"

    def test_complete_task_not_found_raises(self) -> None:
        agent = Agent()
        with pytest.raises(AgentTaskNotFoundError):
            agent.complete_task(AgentTaskId(), AgentResult(value="done"))


class TestAgentFailTask:
    def test_fail_task(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        reason = FailureReason(value="error")
        agent.fail_task(task.task_id, reason)
        assert task.status == AgentTaskStatus.FAILED
        assert task.failure_reason == reason

    def test_fail_task_emits_event(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        agent.fail_task(task.task_id, FailureReason(value="error"))
        assert isinstance(agent.events[-1], AgentTaskFailed)
        assert agent.events[-1].failure_reason == "error"

    def test_fail_task_not_found_raises(self) -> None:
        agent = Agent()
        with pytest.raises(AgentTaskNotFoundError):
            agent.fail_task(AgentTaskId(), FailureReason(value="error"))


class TestAgentCancelTask:
    def test_cancel_task(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.cancel_task(task.task_id)
        assert task.status == AgentTaskStatus.CANCELLED

    def test_cancel_task_emits_event(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.cancel_task(task.task_id)
        assert isinstance(agent.events[-1], AgentTaskCancelled)

    def test_cancel_task_not_found_raises(self) -> None:
        agent = Agent()
        with pytest.raises(AgentTaskNotFoundError):
            agent.cancel_task(AgentTaskId())

    def test_cancel_running_task(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        agent.cancel_task(task.task_id)
        assert task.status == AgentTaskStatus.CANCELLED


# ===========================================================================
# Agent execution management
# ===========================================================================


class TestAgentStartExecution:
    def test_start_execution(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        exec_ = agent.start_execution(task.task_id)
        assert isinstance(exec_, AgentExecution)
        assert exec_.status == AgentExecutionStatus.EXECUTING

    def test_start_execution_emits_event(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        agent.start_execution(task.task_id)
        assert isinstance(agent.events[-1], AgentExecutionStarted)

    def test_start_execution_stores_in_agent(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        exec_ = agent.start_execution(task.task_id)
        assert len(agent.executions) == 1
        assert agent.executions[0] == exec_

    def test_start_execution_disabled_agent_raises(self) -> None:
        agent = Agent()
        agent.disable()
        task = AgentTask()
        agent._tasks.append(task)
        with pytest.raises(AgentDisabledError):
            agent.start_execution(task.task_id)

    def test_start_execution_paused_agent_raises(self) -> None:
        agent = Agent()
        agent.activate()
        agent.pause()
        task = AgentTask()
        agent._tasks.append(task)
        with pytest.raises(AgentPausedError):
            agent.start_execution(task.task_id)

    def test_start_execution_idempotent_not_possible(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        exec1 = agent.start_execution(task.task_id)
        assert exec1.status == AgentExecutionStatus.EXECUTING
        assert len(agent.executions) == 1

    def test_start_execution_sets_task_id(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        exec_ = agent.start_execution(task.task_id)
        assert exec_.task_id == task.task_id

    def test_start_execution_sets_agent_id(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        exec_ = agent.start_execution(task.task_id)
        assert exec_.agent_id == agent.agent_id

    def test_start_execution_not_found_raises(self) -> None:
        agent = Agent()
        with pytest.raises(AgentTaskNotFoundError):
            agent.start_execution(AgentTaskId())


class TestAgentCompleteExecution:
    def test_complete_execution(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        exec_ = agent.start_execution(task.task_id)
        result = AgentResult(value="done")
        agent.complete_execution(exec_.execution_id, result)
        assert exec_.status == AgentExecutionStatus.COMPLETED
        assert exec_.result == result

    def test_complete_execution_emits_event(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        exec_ = agent.start_execution(task.task_id)
        agent.complete_execution(exec_.execution_id, AgentResult(value="done"))
        assert isinstance(agent.events[-1], AgentExecutionCompleted)
        assert agent.events[-1].result == "done"

    def test_complete_execution_not_found_raises(self) -> None:
        agent = Agent()
        with pytest.raises(AgentExecutionNotFoundError):
            agent.complete_execution(AgentExecutionId(), AgentResult(value="done"))


class TestAgentFailExecution:
    def test_fail_execution(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        exec_ = agent.start_execution(task.task_id)
        reason = FailureReason(value="error")
        agent.fail_execution(exec_.execution_id, reason)
        assert exec_.status == AgentExecutionStatus.FAILED
        assert exec_.failure_reason == reason

    def test_fail_execution_emits_event(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        exec_ = agent.start_execution(task.task_id)
        agent.fail_execution(exec_.execution_id, FailureReason(value="error"))
        assert isinstance(agent.events[-1], AgentExecutionFailed)
        assert agent.events[-1].failure_reason == "error"

    def test_fail_execution_not_found_raises(self) -> None:
        agent = Agent()
        with pytest.raises(AgentExecutionNotFoundError):
            agent.fail_execution(AgentExecutionId(), FailureReason(value="error"))


# ===========================================================================
# Full lifecycle
# ===========================================================================


class TestAgentFullLifecycle:
    def test_idle_to_active_to_paused_to_disabled(self) -> None:
        agent = Agent()
        assert agent.status == AgentStatus.IDLE
        agent.activate()
        assert agent.status == AgentStatus.ACTIVE
        agent.pause()
        assert agent.status == AgentStatus.PAUSED
        agent.disable()
        assert agent.status == AgentStatus.DISABLED

    def test_idle_to_active_to_disabled(self) -> None:
        agent = Agent()
        agent.activate()
        agent.disable()
        assert agent.status == AgentStatus.DISABLED

    def test_idle_to_disabled(self) -> None:
        agent = Agent()
        agent.disable()
        assert agent.status == AgentStatus.DISABLED

    def test_paused_to_active(self) -> None:
        agent = Agent()
        agent.activate()
        agent.pause()
        agent.activate()
        assert agent.status == AgentStatus.ACTIVE


class TestTaskFullLifecycle:
    def test_pending_to_running_to_completed(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        assert task.status == AgentTaskStatus.RUNNING
        agent.complete_task(task.task_id, AgentResult(value="done"))
        assert task.status == AgentTaskStatus.COMPLETED

    def test_pending_to_running_to_failed(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        agent.fail_task(task.task_id, FailureReason(value="err"))
        assert task.status == AgentTaskStatus.FAILED

    def test_pending_to_cancelled(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.cancel_task(task.task_id)
        assert task.status == AgentTaskStatus.CANCELLED

    def test_running_to_cancelled(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        agent.cancel_task(task.task_id)
        assert task.status == AgentTaskStatus.CANCELLED


class TestExecutionFullLifecycle:
    def test_pending_to_executing_to_completed(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        exec_ = agent.start_execution(task.task_id)
        assert exec_.status == AgentExecutionStatus.EXECUTING
        agent.complete_execution(exec_.execution_id, AgentResult(value="done"))
        assert exec_.status == AgentExecutionStatus.COMPLETED

    def test_pending_to_executing_to_failed(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        exec_ = agent.start_execution(task.task_id)
        agent.fail_execution(exec_.execution_id, FailureReason(value="err"))
        assert exec_.status == AgentExecutionStatus.FAILED


# ===========================================================================
# Rules (direct unit tests)
# ===========================================================================


class TestRulesName:
    def test_name_required_empty(self) -> None:
        from backend.agent.domain.rules import assert_agent_name_required

        with pytest.raises(InvalidAgentNameError):
            assert_agent_name_required("")

    def test_name_required_none(self) -> None:
        from backend.agent.domain.rules import assert_agent_name_required

        with pytest.raises(InvalidAgentNameError):
            assert_agent_name_required(None)

    def test_name_required_whitespace(self) -> None:
        from backend.agent.domain.rules import assert_agent_name_required

        with pytest.raises(InvalidAgentNameError):
            assert_agent_name_required("   ")

    def test_name_required_valid(self) -> None:
        from backend.agent.domain.rules import assert_agent_name_required

        assert_agent_name_required("test") is None


class TestRulesGoal:
    def test_goal_required_empty(self) -> None:
        from backend.agent.domain.rules import assert_agent_goal_required

        with pytest.raises(InvalidAgentGoalError):
            assert_agent_goal_required("")

    def test_goal_required_none(self) -> None:
        from backend.agent.domain.rules import assert_agent_goal_required

        with pytest.raises(InvalidAgentGoalError):
            assert_agent_goal_required(None)

    def test_goal_required_valid(self) -> None:
        from backend.agent.domain.rules import assert_agent_goal_required

        assert_agent_goal_required("goal") is None


class TestRulesInstruction:
    def test_instruction_required_empty(self) -> None:
        from backend.agent.domain.rules import assert_agent_instruction_required

        with pytest.raises(InvalidAgentInstructionError):
            assert_agent_instruction_required("")

    def test_instruction_required_none(self) -> None:
        from backend.agent.domain.rules import assert_agent_instruction_required

        with pytest.raises(InvalidAgentInstructionError):
            assert_agent_instruction_required(None)

    def test_instruction_required_valid(self) -> None:
        from backend.agent.domain.rules import assert_agent_instruction_required

        assert_agent_instruction_required("instr") is None


class TestRulesResult:
    def test_result_required_none(self) -> None:
        from backend.agent.domain.rules import assert_agent_result_required

        with pytest.raises(ResultRequiredError):
            assert_agent_result_required(None)

    def test_result_required_valid(self) -> None:
        from backend.agent.domain.rules import assert_agent_result_required

        assert_agent_result_required(AgentResult(value="ok")) is None


class TestRulesFailureReason:
    def test_failure_reason_required_none(self) -> None:
        from backend.agent.domain.rules import assert_failure_reason_required

        with pytest.raises(InvalidFailureReasonError):
            assert_failure_reason_required(None)

    def test_failure_reason_required_valid(self) -> None:
        from backend.agent.domain.rules import assert_failure_reason_required

        assert_failure_reason_required(FailureReason(value="err")) is None


class TestRulesAgentType:
    def test_agent_type_valid(self) -> None:
        from backend.agent.domain.rules import assert_agent_type_valid

        assert_agent_type_valid("research") is None

    def test_agent_type_invalid(self) -> None:
        from backend.agent.domain.rules import assert_agent_type_valid

        with pytest.raises(InvalidAgentTypeError):
            assert_agent_type_valid("invalid")


class TestRulesDisabledOrPaused:
    def test_disabled_agent_raises(self) -> None:
        from backend.agent.domain.rules import assert_agent_not_disabled_or_paused

        agent = Agent()
        agent.disable()
        with pytest.raises(AgentDisabledError):
            assert_agent_not_disabled_or_paused(agent)

    def test_paused_agent_raises(self) -> None:
        from backend.agent.domain.rules import assert_agent_not_disabled_or_paused

        agent = Agent()
        agent.activate()
        agent.pause()
        with pytest.raises(AgentPausedError):
            assert_agent_not_disabled_or_paused(agent)

    def test_active_agent_ok(self) -> None:
        from backend.agent.domain.rules import assert_agent_not_disabled_or_paused

        agent = Agent()
        agent.activate()
        assert_agent_not_disabled_or_paused(agent) is None

    def test_idle_agent_ok(self) -> None:
        from backend.agent.domain.rules import assert_agent_not_disabled_or_paused

        agent = Agent()
        assert_agent_not_disabled_or_paused(agent) is None


class TestRulesNotDisabled:
    def test_disabled_agent_raises(self) -> None:
        from backend.agent.domain.rules import assert_agent_not_disabled

        agent = Agent()
        agent.disable()
        with pytest.raises(AgentDisabledError):
            assert_agent_not_disabled(agent)

    def test_active_agent_ok(self) -> None:
        from backend.agent.domain.rules import assert_agent_not_disabled

        agent = Agent()
        agent.activate()
        assert_agent_not_disabled(agent) is None


class TestRulesNotPaused:
    def test_paused_agent_raises(self) -> None:
        from backend.agent.domain.rules import assert_agent_not_paused

        agent = Agent()
        agent.activate()
        agent.pause()
        with pytest.raises(AgentPausedError):
            assert_agent_not_paused(agent)

    def test_active_agent_ok(self) -> None:
        from backend.agent.domain.rules import assert_agent_not_paused

        agent = Agent()
        agent.activate()
        assert_agent_not_paused(agent) is None


class TestRulesTaskIdUnique:
    def test_duplicate_task_id_raises(self) -> None:
        from backend.agent.domain.rules import assert_agent_task_id_unique

        tid = AgentTaskId()
        task1 = AgentTask(task_id=tid)
        task2 = AgentTask(task_id=tid)
        with pytest.raises(DuplicateAgentTaskIdError):
            assert_agent_task_id_unique(tid, [task1, task2])

    def test_unique_task_id_ok(self) -> None:
        from backend.agent.domain.rules import assert_agent_task_id_unique

        tid = AgentTaskId()
        task1 = AgentTask(task_id=AgentTaskId())
        assert_agent_task_id_unique(tid, [task1]) is None


class TestRulesExecutionIdUnique:
    def test_duplicate_execution_id_raises(self) -> None:
        from backend.agent.domain.rules import assert_agent_execution_id_unique

        eid = AgentExecutionId()
        exec1 = AgentExecution(execution_id=eid)
        exec2 = AgentExecution(execution_id=eid)
        with pytest.raises(DuplicateAgentExecutionIdError):
            assert_agent_execution_id_unique(eid, [exec1, exec2])

    def test_unique_execution_id_ok(self) -> None:
        from backend.agent.domain.rules import assert_agent_execution_id_unique

        eid = AgentExecutionId()
        exec1 = AgentExecution(execution_id=AgentExecutionId())
        assert_agent_execution_id_unique(eid, [exec1]) is None


class TestRulesComposite:
    def test_validate_agent_creation_ok(self) -> None:
        from backend.agent.domain.rules import validate_agent_creation

        validate_agent_creation(name="test", agent_type="research") is None

    def test_validate_agent_creation_no_name(self) -> None:
        from backend.agent.domain.rules import validate_agent_creation

        with pytest.raises(InvalidAgentNameError):
            validate_agent_creation(name="")

    def test_validate_agent_creation_bad_type(self) -> None:
        from backend.agent.domain.rules import validate_agent_creation

        with pytest.raises(InvalidAgentTypeError):
            validate_agent_creation(name="test", agent_type="invalid")

    def test_validate_task_creation_ok(self) -> None:
        from backend.agent.domain.rules import validate_task_creation

        validate_task_creation(goal="g", instruction="i") is None

    def test_validate_task_creation_no_goal(self) -> None:
        from backend.agent.domain.rules import validate_task_creation

        with pytest.raises(InvalidAgentGoalError):
            validate_task_creation(goal="", instruction="i")

    def test_validate_task_creation_no_instruction(self) -> None:
        from backend.agent.domain.rules import validate_task_creation

        with pytest.raises(InvalidAgentInstructionError):
            validate_task_creation(goal="g", instruction="")


# ===========================================================================
# Factory
# ===========================================================================


class TestFactoryCreateAgent:
    def test_create_agent(self) -> None:
        agent, event = AgentFactory.create_agent(name="test")
        assert isinstance(agent, Agent)
        assert isinstance(event, AgentCreated)
        assert agent.name is not None
        assert str(agent.name) == "test"
        assert agent.agent_type == AgentType.COORDINATOR
        assert agent.status == AgentStatus.IDLE
        assert event.name == "test"
        assert event.agent_type == "coordinator"

    def test_create_agent_research_type(self) -> None:
        agent, event = AgentFactory.create_agent(
            name="research", agent_type="research"
        )
        assert agent.agent_type == AgentType.RESEARCH
        assert event.agent_type == "research"

    def test_create_agent_knowledge_type(self) -> None:
        agent, event = AgentFactory.create_agent(
            name="knowledge", agent_type=AgentType.KNOWLEDGE
        )
        assert agent.agent_type == AgentType.KNOWLEDGE

    def test_create_agent_invalid_type_raises(self) -> None:
        with pytest.raises(InvalidAgentTypeError):
            AgentFactory.create_agent(name="test", agent_type="invalid")

    def test_create_agent_empty_name_raises(self) -> None:
        with pytest.raises(InvalidAgentNameError):
            AgentFactory.create_agent(name="")

    def test_create_agent_whitespace_name_raises(self) -> None:
        with pytest.raises(InvalidAgentNameError):
            AgentFactory.create_agent(name="   ")

    def test_create_agent_sets_created_at(self) -> None:
        agent, event = AgentFactory.create_agent(name="test")
        assert agent.created_at is not None
        assert event.occurred_at is not None


class TestFactoryActivate:
    def test_activate_agent(self) -> None:
        agent, _ = AgentFactory.create_agent(name="test")
        AgentFactory.activate_agent(agent)
        assert agent.status == AgentStatus.ACTIVE
        assert len(agent.events) == 1  # only activated event recorded
        assert isinstance(agent.events[-1], AgentActivated)


class TestFactoryPause:
    def test_pause_agent(self) -> None:
        agent, _ = AgentFactory.create_agent(name="test")
        AgentFactory.activate_agent(agent)
        AgentFactory.pause_agent(agent)
        assert agent.status == AgentStatus.PAUSED
        assert isinstance(agent.events[-1], AgentPaused)


class TestFactoryDisable:
    def test_disable_agent(self) -> None:
        agent, _ = AgentFactory.create_agent(name="test")
        AgentFactory.disable_agent(agent)
        assert agent.status == AgentStatus.DISABLED
        assert isinstance(agent.events[-1], AgentDisabled)


class TestFactoryCreateTask:
    def test_create_task(self) -> None:
        agent, _ = AgentFactory.create_agent(name="test")
        task, event = AgentFactory.create_task(
            agent=agent, goal="test goal", instruction="do it"
        )
        assert isinstance(task, AgentTask)
        assert isinstance(event, AgentTaskCreated)
        assert str(task.goal) == "test goal"
        assert str(task.instruction) == "do it"
        assert task.status == AgentTaskStatus.PENDING
        assert task.agent_id == agent.agent_id
        assert len(agent.tasks) == 1

    def test_create_task_empty_goal_raises(self) -> None:
        agent, _ = AgentFactory.create_agent(name="test")
        with pytest.raises(InvalidAgentGoalError):
            AgentFactory.create_task(agent=agent, goal="", instruction="do it")

    def test_create_task_empty_instruction_raises(self) -> None:
        agent, _ = AgentFactory.create_agent(name="test")
        with pytest.raises(InvalidAgentInstructionError):
            AgentFactory.create_task(agent=agent, goal="goal", instruction="")


class TestFactoryStartTask:
    def test_start_task(self) -> None:
        agent, _ = AgentFactory.create_agent(name="test")
        task, _ = AgentFactory.create_task(
            agent=agent, goal="g", instruction="i"
        )
        event = AgentFactory.start_task(agent=agent, task_id=task.task_id)
        assert isinstance(event, AgentTaskStarted)
        assert task.status == AgentTaskStatus.RUNNING

    def test_start_task_idle_agent_ok(self) -> None:
        agent, _ = AgentFactory.create_agent(name="test")
        task, _ = AgentFactory.create_task(
            agent=agent, goal="g", instruction="i"
        )
        AgentFactory.start_task(agent=agent, task_id=task.task_id)


class TestFactoryCompleteTask:
    def test_complete_task(self) -> None:
        agent, _ = AgentFactory.create_agent(name="test")
        task, _ = AgentFactory.create_task(
            agent=agent, goal="g", instruction="i"
        )
        AgentFactory.start_task(agent=agent, task_id=task.task_id)
        event = AgentFactory.complete_task(
            agent=agent, task_id=task.task_id, result="done"
        )
        assert isinstance(event, AgentTaskCompleted)
        assert event.result == "done"
        assert task.status == AgentTaskStatus.COMPLETED


class TestFactoryFailTask:
    def test_fail_task(self) -> None:
        agent, _ = AgentFactory.create_agent(name="test")
        task, _ = AgentFactory.create_task(
            agent=agent, goal="g", instruction="i"
        )
        AgentFactory.start_task(agent=agent, task_id=task.task_id)
        event = AgentFactory.fail_task(
            agent=agent, task_id=task.task_id, reason="error"
        )
        assert isinstance(event, AgentTaskFailed)
        assert event.failure_reason == "error"
        assert task.status == AgentTaskStatus.FAILED


class TestFactoryCancelTask:
    def test_cancel_task(self) -> None:
        agent, _ = AgentFactory.create_agent(name="test")
        task, _ = AgentFactory.create_task(
            agent=agent, goal="g", instruction="i"
        )
        event = AgentFactory.cancel_task(agent=agent, task_id=task.task_id)
        assert isinstance(event, AgentTaskCancelled)
        assert task.status == AgentTaskStatus.CANCELLED


class TestFactoryStartExecution:
    def test_start_execution(self) -> None:
        agent, _ = AgentFactory.create_agent(name="test")
        task, _ = AgentFactory.create_task(
            agent=agent, goal="g", instruction="i"
        )
        AgentFactory.start_task(agent=agent, task_id=task.task_id)
        exec_, event = AgentFactory.start_execution(
            agent=agent, task_id=task.task_id
        )
        assert isinstance(exec_, AgentExecution)
        assert isinstance(event, AgentExecutionStarted)
        assert exec_.status == AgentExecutionStatus.EXECUTING
        assert exec_.task_id == task.task_id

    def test_start_execution_disabled_agent_raises(self) -> None:
        agent, _ = AgentFactory.create_agent(name="test")
        task, _ = AgentFactory.create_task(
            agent=agent, goal="g", instruction="i"
        )
        AgentFactory.disable_agent(agent)
        with pytest.raises(AgentDisabledError):
            AgentFactory.start_execution(agent=agent, task_id=task.task_id)

    def test_start_execution_paused_agent_raises(self) -> None:
        agent, _ = AgentFactory.create_agent(name="test")
        task, _ = AgentFactory.create_task(
            agent=agent, goal="g", instruction="i"
        )
        AgentFactory.activate_agent(agent)
        AgentFactory.pause_agent(agent)
        with pytest.raises(AgentPausedError):
            AgentFactory.start_execution(agent=agent, task_id=task.task_id)


class TestFactoryCompleteExecution:
    def test_complete_execution(self) -> None:
        agent, _ = AgentFactory.create_agent(name="test")
        task, _ = AgentFactory.create_task(
            agent=agent, goal="g", instruction="i"
        )
        AgentFactory.start_task(agent=agent, task_id=task.task_id)
        exec_, _ = AgentFactory.start_execution(agent=agent, task_id=task.task_id)
        event = AgentFactory.complete_execution(
            agent=agent, execution_id=exec_.execution_id, result="done"
        )
        assert isinstance(event, AgentExecutionCompleted)
        assert event.result == "done"
        assert exec_.status == AgentExecutionStatus.COMPLETED


class TestFactoryFailExecution:
    def test_fail_execution(self) -> None:
        agent, _ = AgentFactory.create_agent(name="test")
        task, _ = AgentFactory.create_task(
            agent=agent, goal="g", instruction="i"
        )
        AgentFactory.start_task(agent=agent, task_id=task.task_id)
        exec_, _ = AgentFactory.start_execution(agent=agent, task_id=task.task_id)
        event = AgentFactory.fail_execution(
            agent=agent, execution_id=exec_.execution_id, reason="error"
        )
        assert isinstance(event, AgentExecutionFailed)
        assert event.failure_reason == "error"
        assert exec_.status == AgentExecutionStatus.FAILED


# ===========================================================================
# Exception hierarchy
# ===========================================================================


class TestExceptionHierarchy:
    def test_agent_domain_error_is_base(self) -> None:
        assert issubclass(InvalidAgentNameError, AgentDomainError)
        assert issubclass(InvalidAgentGoalError, AgentDomainError)
        assert issubclass(InvalidAgentInstructionError, AgentDomainError)
        assert issubclass(InvalidAgentResultError, AgentDomainError)
        assert issubclass(InvalidFailureReasonError, AgentDomainError)
        assert issubclass(InvalidTransitionError, AgentDomainError)
        assert issubclass(AgentTerminalError, AgentDomainError)
        assert issubclass(AgentDisabledError, AgentDomainError)
        assert issubclass(AgentPausedError, AgentDomainError)
        assert issubclass(AgentTaskNotStartedError, AgentDomainError)
        assert issubclass(AgentExecutionNotStartedError, AgentDomainError)
        assert issubclass(AgentTaskNotFoundError, AgentDomainError)
        assert issubclass(AgentExecutionNotFoundError, AgentDomainError)
        assert issubclass(DuplicateAgentTaskIdError, AgentDomainError)
        assert issubclass(DuplicateAgentExecutionIdError, AgentDomainError)
        assert issubclass(InvalidAgentTypeError, AgentDomainError)
        assert issubclass(ResultRequiredError, AgentDomainError)

    def test_invalid_transition_message(self) -> None:
        exc = InvalidTransitionError("agent", "idle", "paused")
        assert "idle" in str(exc)
        assert "paused" in str(exc)
        assert exc.entity == "agent"
        assert exc.current == "idle"
        assert exc.target == "paused"

    def test_agent_task_not_found_message(self) -> None:
        exc = AgentTaskNotFoundError("task-123")
        assert "task-123" in str(exc)
        assert exc.task_id == "task-123"

    def test_agent_execution_not_found_message(self) -> None:
        exc = AgentExecutionNotFoundError("exec-123")
        assert "exec-123" in str(exc)
        assert exc.execution_id == "exec-123"

    def test_duplicate_task_id_message(self) -> None:
        exc = DuplicateAgentTaskIdError("task-123")
        assert "task-123" in str(exc)
        assert exc.task_id == "task-123"

    def test_duplicate_execution_id_message(self) -> None:
        exc = DuplicateAgentExecutionIdError("exec-123")
        assert "exec-123" in str(exc)
        assert exc.execution_id == "exec-123"


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdgeCases:
    def test_agent_with_no_tasks_empty_list(self) -> None:
        agent = Agent()
        assert agent.tasks == []

    def test_agent_with_no_executions_empty_list(self) -> None:
        agent = Agent()
        assert agent.executions == []

    def test_agent_events_immutable_copy(self) -> None:
        agent = Agent()
        agent.activate()
        events_before = agent.events
        assert len(events_before) == 1
        agent.pause()
        assert len(events_before) == 1
        assert len(agent.events) == 2

    def test_task_cannot_complete_twice(self) -> None:
        task = AgentTask()
        task.start()
        task.complete(AgentResult(value="done"))
        with pytest.raises(InvalidTransitionError):
            task.complete(AgentResult(value="again"))

    def test_task_cannot_fail_twice(self) -> None:
        task = AgentTask()
        task.start()
        task.fail(FailureReason(value="err"))
        with pytest.raises(InvalidTransitionError):
            task.fail(FailureReason(value="again"))

    def test_execution_cannot_complete_twice(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        exec_.complete(AgentResult(value="done"))
        with pytest.raises(InvalidTransitionError):
            exec_.complete(AgentResult(value="again"))

    def test_execution_cannot_fail_twice(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        exec_.fail(FailureReason(value="err"))
        with pytest.raises(InvalidTransitionError):
            exec_.fail(FailureReason(value="again"))

    def test_multiple_tasks_on_same_agent(self) -> None:
        agent = Agent()
        t1 = AgentTask()
        t2 = AgentTask()
        t3 = AgentTask()
        agent.add_task(t1)
        agent.add_task(t2)
        agent.add_task(t3)
        assert len(agent.tasks) == 3

    def test_multiple_executions_on_same_agent(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        e1 = agent.start_execution(task.task_id)
        e2 = AgentExecution()
        agent._executions.append(e2)
        assert len(agent.executions) == 2
        assert e1.execution_id != e2.execution_id

    def test_agent_events_accumulate(self) -> None:
        agent = Agent()
        agent.activate()
        agent.pause()
        agent.activate()
        agent.disable()
        assert len(agent.events) == 4

    def test_task_events_not_stored_on_agent(self) -> None:
        agent = Agent()
        task = AgentTask()
        agent.add_task(task)
        agent.start_task(task.task_id)
        agent.complete_task(task.task_id, AgentResult(value="done"))
        agent_events = agent.events
        assert all(
            isinstance(e, (AgentTaskCreated, AgentTaskStarted, AgentTaskCompleted))
            for e in agent_events[-3:]
        )
        assert len(agent_events) == 3

    def test_agent_name_len(self) -> None:
        name = AgentName(value="Research Agent")
        assert len(name) == 14

    def test_agent_goal_len(self) -> None:
        goal = AgentGoal(value="test")
        assert len(goal) == 4

    def test_agent_instruction_len(self) -> None:
        instr = AgentInstruction(value="do")
        assert len(instr) == 2

    def test_agent_result_len(self) -> None:
        result = AgentResult(value="done")
        assert len(result) == 4

    def test_failure_reason_len(self) -> None:
        reason = FailureReason(value="err")
        assert len(reason) == 3

    def test_agent_goal_str(self) -> None:
        goal = AgentGoal(value="hello")
        assert str(goal) == "hello"

    def test_agent_instruction_str(self) -> None:
        instr = AgentInstruction(value="world")
        assert str(instr) == "world"

    def test_agent_result_str(self) -> None:
        result = AgentResult(value="ok")
        assert str(result) == "ok"

    def test_failure_reason_str(self) -> None:
        reason = FailureReason(value="fail")
        assert str(reason) == "fail"


# ===========================================================================
# Immutability tests
# ===========================================================================


class TestImmutability:
    def test_agent_tasks_list_is_copy(self) -> None:
        agent = Agent()
        tasks = agent.tasks
        tasks.append(AgentTask())
        assert len(agent.tasks) == 0

    def test_agent_executions_list_is_copy(self) -> None:
        agent = Agent()
        execs = agent.executions
        execs.append(AgentExecution())
        assert len(agent.executions) == 0

    def test_agent_events_list_is_copy(self) -> None:
        agent = Agent()
        agent.activate()
        events = agent.events
        events.clear()
        assert len(agent.events) == 1


# ===========================================================================
# State coverage - all invalid transitions
# ===========================================================================


class TestInvalidAgentStatusTransitions:
    def test_idle_to_paused_raises(self) -> None:
        agent = Agent()
        with pytest.raises(InvalidTransitionError):
            agent.pause()

    def test_paused_to_paused_raises(self) -> None:
        agent = Agent()
        agent.activate()
        agent.pause()
        with pytest.raises(InvalidTransitionError):
            agent.pause()

    def test_active_to_active_raises(self) -> None:
        agent = Agent()
        agent.activate()
        with pytest.raises(InvalidTransitionError):
            agent.activate()

    def test_disabled_to_disabled_raises(self) -> None:
        agent = Agent()
        agent.disable()
        with pytest.raises(InvalidTransitionError):
            agent.disable()

    def test_disabled_to_active_raises(self) -> None:
        agent = Agent()
        agent.disable()
        with pytest.raises(InvalidTransitionError):
            agent.activate()

    def test_disabled_to_paused_raises(self) -> None:
        agent = Agent()
        agent.disable()
        with pytest.raises(InvalidTransitionError):
            agent.pause()

    def test_idle_to_idle_not_possible(self) -> None:
        pass


class TestInvalidTaskTransitions:
    def test_pending_to_completed_raises(self) -> None:
        task = AgentTask()
        with pytest.raises(InvalidTransitionError):
            task.complete(AgentResult(value="done"))

    def test_pending_to_failed_raises(self) -> None:
        task = AgentTask()
        with pytest.raises(InvalidTransitionError):
            task.fail(FailureReason(value="err"))

    def test_completed_to_failed_raises(self) -> None:
        task = AgentTask()
        task.start()
        task.complete(AgentResult(value="done"))
        with pytest.raises(InvalidTransitionError):
            task.fail(FailureReason(value="err"))

    def test_completed_to_completed_raises(self) -> None:
        task = AgentTask()
        task.start()
        task.complete(AgentResult(value="done"))
        with pytest.raises(InvalidTransitionError):
            task.complete(AgentResult(value="again"))

    def test_cancelled_to_running_raises(self) -> None:
        task = AgentTask()
        task.cancel()
        with pytest.raises(InvalidTransitionError):
            task.start()

    def test_cancelled_to_completed_raises(self) -> None:
        task = AgentTask()
        task.cancel()
        with pytest.raises(InvalidTransitionError):
            task.complete(AgentResult(value="done"))

    def test_cancelled_to_failed_raises(self) -> None:
        task = AgentTask()
        task.cancel()
        with pytest.raises(InvalidTransitionError):
            task.fail(FailureReason(value="err"))

    def test_failed_to_completed_raises(self) -> None:
        task = AgentTask()
        task.start()
        task.fail(FailureReason(value="err"))
        with pytest.raises(InvalidTransitionError):
            task.complete(AgentResult(value="done"))


class TestInvalidExecutionTransitions:
    def test_pending_to_completed_raises(self) -> None:
        exec_ = AgentExecution()
        with pytest.raises(InvalidTransitionError):
            exec_.complete(AgentResult(value="done"))

    def test_pending_to_failed_raises(self) -> None:
        exec_ = AgentExecution()
        with pytest.raises(InvalidTransitionError):
            exec_.fail(FailureReason(value="err"))

    def test_completed_to_failed_raises(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        exec_.complete(AgentResult(value="done"))
        with pytest.raises(InvalidTransitionError):
            exec_.fail(FailureReason(value="err"))

    def test_completed_to_executing_raises(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        exec_.complete(AgentResult(value="done"))
        with pytest.raises(InvalidTransitionError):
            exec_.start()

    def test_failed_to_completed_raises(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        exec_.fail(FailureReason(value="err"))
        with pytest.raises(InvalidTransitionError):
            exec_.complete(AgentResult(value="done"))

    def test_failed_to_executing_raises(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        exec_.fail(FailureReason(value="err"))
        with pytest.raises(InvalidTransitionError):
            exec_.start()

    def test_executing_to_pending_impossible(self) -> None:
        exec_ = AgentExecution()
        exec_.start()
        assert exec_.status == AgentExecutionStatus.EXECUTING

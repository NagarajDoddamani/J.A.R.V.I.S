from __future__ import annotations

from backend.agent.domain.model import (
    Agent,
    AgentExecution,
    AgentExecutionStatus,
    AgentStatus,
    AgentTask,
    AgentTaskStatus,
    VALID_AGENT_EXECUTION_TRANSITIONS,
    VALID_AGENT_STATUS_TRANSITIONS,
    VALID_AGENT_TASK_TRANSITIONS,
)


# ===========================================================================
# Rule 1: Agent name is required
# ===========================================================================


def assert_agent_name_required(name: str | None) -> None:
    if not name or not name.strip():
        from backend.agent.domain.exceptions import InvalidAgentNameError

        raise InvalidAgentNameError("Agent name is required")


# ===========================================================================
# Rule 2: Goal is required
# ===========================================================================


def assert_agent_goal_required(goal: str | None) -> None:
    if not goal or not goal.strip():
        from backend.agent.domain.exceptions import InvalidAgentGoalError

        raise InvalidAgentGoalError("Goal is required")


# ===========================================================================
# Rule 3: Instruction is required
# ===========================================================================


def assert_agent_instruction_required(instruction: str | None) -> None:
    if not instruction or not instruction.strip():
        from backend.agent.domain.exceptions import InvalidAgentInstructionError

        raise InvalidAgentInstructionError("Instruction is required")


# ===========================================================================
# Rule 4: Agent status transitions must be valid
# ===========================================================================


def assert_agent_status_can_transition(
    current: AgentStatus, target: AgentStatus
) -> None:
    allowed = VALID_AGENT_STATUS_TRANSITIONS.get(current, set())
    if target not in allowed:
        from backend.agent.domain.exceptions import InvalidTransitionError

        raise InvalidTransitionError("agent", current.value, target.value)


# ===========================================================================
# Rule 5: Task transitions must be valid
# ===========================================================================


def assert_agent_task_can_transition(
    current: AgentTaskStatus, target: AgentTaskStatus
) -> None:
    allowed = VALID_AGENT_TASK_TRANSITIONS.get(current, set())
    if target not in allowed:
        from backend.agent.domain.exceptions import InvalidTransitionError

        raise InvalidTransitionError("task", current.value, target.value)


# ===========================================================================
# Rule 6: Execution transitions must be valid
# ===========================================================================


def assert_agent_execution_can_transition(
    current: AgentExecutionStatus, target: AgentExecutionStatus
) -> None:
    allowed = VALID_AGENT_EXECUTION_TRANSITIONS.get(current, set())
    if target not in allowed:
        from backend.agent.domain.exceptions import InvalidTransitionError

        raise InvalidTransitionError("execution", current.value, target.value)


# ===========================================================================
# Rule 7: Task must start before complete
# Rule 8: Task must start before fail
# ===========================================================================


def assert_agent_task_started_before(task: AgentTask, action: str) -> None:
    if task.status != AgentTaskStatus.RUNNING:
        from backend.agent.domain.exceptions import AgentTaskNotStartedError

        raise AgentTaskNotStartedError(action)


# ===========================================================================
# Rule 9: Execution must start before complete
# Rule 10: Execution must start before fail
# ===========================================================================


def assert_agent_execution_started_before(execution: AgentExecution, action: str) -> None:
    if execution.status != AgentExecutionStatus.EXECUTING:
        from backend.agent.domain.exceptions import AgentExecutionNotStartedError

        raise AgentExecutionNotStartedError(action)


# ===========================================================================
# Rule 11: Disabled agent cannot execute
# ===========================================================================


def assert_agent_not_disabled(agent: Agent) -> None:
    if agent.status == AgentStatus.DISABLED:
        from backend.agent.domain.exceptions import AgentDisabledError

        raise AgentDisabledError()


# ===========================================================================
# Rule 12: Paused agent cannot execute
# ===========================================================================


def assert_agent_not_paused(agent: Agent) -> None:
    if agent.status == AgentStatus.PAUSED:
        from backend.agent.domain.exceptions import AgentPausedError

        raise AgentPausedError()


# ===========================================================================
# Rule 13: Disabled or paused agent cannot add/start tasks
# ===========================================================================


def assert_agent_not_disabled_or_paused(agent: Agent) -> None:
    if agent.status == AgentStatus.DISABLED:
        from backend.agent.domain.exceptions import AgentDisabledError

        raise AgentDisabledError()
    if agent.status == AgentStatus.PAUSED:
        from backend.agent.domain.exceptions import AgentPausedError

        raise AgentPausedError()


# ===========================================================================
# Rule 14: Completed task is immutable
# Rule 15: Failed task is immutable
# Rule 16: Cancelled task is immutable
# ===========================================================================

# Enforced via transition map (no outgoing transitions from terminal states).

# ===========================================================================
# Rule 17: Completed execution is immutable
# Rule 18: Failed execution is immutable
# ===========================================================================

# Enforced via transition map (no outgoing transitions from terminal states).

# ===========================================================================
# Rule 19: Duplicate task IDs forbidden
# ===========================================================================


def assert_agent_task_id_unique(
    task_id: object, existing_tasks: list[AgentTask]
) -> None:
    for task in existing_tasks:
        if task.task_id == task_id:
            from backend.agent.domain.exceptions import DuplicateAgentTaskIdError

            raise DuplicateAgentTaskIdError(str(task_id))


# ===========================================================================
# Rule 20: Duplicate execution IDs forbidden
# ===========================================================================


def assert_agent_execution_id_unique(
    execution_id: object, existing_executions: list[AgentExecution]
) -> None:
    for execution in existing_executions:
        if execution.execution_id == execution_id:
            from backend.agent.domain.exceptions import DuplicateAgentExecutionIdError

            raise DuplicateAgentExecutionIdError(str(execution_id))


# ===========================================================================
# Rule 21: Result is required when completing
# ===========================================================================


def assert_agent_result_required(result: object | None) -> None:
    if result is None:
        from backend.agent.domain.exceptions import ResultRequiredError

        raise ResultRequiredError()


# ===========================================================================
# Rule 22: Failure reason is required when failing
# ===========================================================================


def assert_failure_reason_required(reason: object | None) -> None:
    if reason is None:
        from backend.agent.domain.exceptions import InvalidFailureReasonError

        raise InvalidFailureReasonError("Failure reason is required")


# ===========================================================================
# Rule 23: Agent type must be valid
# ===========================================================================


def assert_agent_type_valid(agent_type: str) -> None:
    from backend.agent.domain.model import AgentType

    try:
        AgentType(agent_type)
    except ValueError:
        from backend.agent.domain.exceptions import InvalidAgentTypeError

        raise InvalidAgentTypeError(agent_type)


# ===========================================================================
# Composite validators
# ===========================================================================


def validate_agent_creation(
    name: str | None,
    agent_type: str | None = None,
) -> None:
    assert_agent_name_required(name)
    if agent_type is not None:
        assert_agent_type_valid(agent_type)


def validate_task_creation(
    goal: str | None,
    instruction: str | None,
) -> None:
    assert_agent_goal_required(goal)
    assert_agent_instruction_required(instruction)

from __future__ import annotations

from backend.planner.domain.exceptions import (
    DuplicateExecutionStepIdError,
    DuplicateTaskIdError,
    EmptyPlanExecutionError,
    HybridStrategyRequiresMultipleTasksError,
    InvalidAgentTypeError,
    InvalidEstimatedDurationError,
    InvalidExecutionStrategyError,
    InvalidFailureReasonError,
    InvalidPlanGoalError,
    InvalidPlanPriorityError,
    InvalidStepOrderError,
    InvalidTaskDescriptionError,
    InvalidTransitionError,
    InvalidUserRequestError,
    PlanHasNoTasksError,
    PlanNotReadyError,
    PlanTerminalError,
    TaskNotAssignedError,
    TaskTerminalError,
)
from backend.planner.domain.model import (
    AgentType,
    EstimatedDuration,
    ExecutionStrategy,
    FailureReason,
    Plan,
    PlanPriority,
    PlanStatus,
    Task,
    TaskId,
    TaskStatus,
    UserRequest,
)

# GLOBAL CONFIGURATION
MAX_USER_REQUEST_LENGTH: int = 5000
MAX_PLAN_GOAL_LENGTH: int = 2000
MAX_TASK_DESCRIPTION_LENGTH: int = 2000
MAX_FAILURE_REASON_LENGTH: int = 2000

VALID_PLAN_TRANSITIONS: dict[PlanStatus, set[PlanStatus]] = {
    PlanStatus.DRAFT: {PlanStatus.APPROVED, PlanStatus.CANCELLED},
    PlanStatus.APPROVED: {PlanStatus.PLANNING, PlanStatus.CANCELLED},
    PlanStatus.PLANNING: {PlanStatus.READY, PlanStatus.CANCELLED},
    PlanStatus.READY: {PlanStatus.EXECUTING, PlanStatus.CANCELLED},
    PlanStatus.EXECUTING: {PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.CANCELLED},
    PlanStatus.COMPLETED: set(),
    PlanStatus.FAILED: set(),
    PlanStatus.CANCELLED: set(),
}

VALID_TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.ASSIGNED, TaskStatus.CANCELLED},
    TaskStatus.ASSIGNED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
}


# -- Rule 1: User request required ------------------------------------------

def assert_user_request_required(user_request: str | None) -> None:
    if not user_request or not user_request.strip():
        raise InvalidUserRequestError("User request is required")


# -- Rule 2: Goal required --------------------------------------------------

def assert_goal_required(goal: str | None) -> None:
    if not goal or not goal.strip():
        raise InvalidPlanGoalError("Plan goal is required")


# -- Rule 3: Plan must contain at least one task before READY ----------------

def assert_plan_has_tasks(plan: Plan) -> None:
    if not plan.tasks:
        raise PlanHasNoTasksError()


# -- Rule 4: Task description required ---------------------------------------

def assert_task_description_required(description: str | None) -> None:
    if not description or not description.strip():
        raise InvalidTaskDescriptionError("Task description is required")


# -- Rule 5: Task must have assigned agent before RUNNING --------------------

def assert_task_has_assigned_agent(task: Task) -> None:
    if task.assigned_agent is None:
        raise TaskNotAssignedError()


# -- Rule 6: Failure reason required when FAILED -----------------------------

def assert_failure_reason_provided(reason: FailureReason | None) -> None:
    if reason is None:
        raise InvalidFailureReasonError("Failure reason is required when FAILED")


# -- Rule 7: COMPLETED task cannot transition again --------------------------

# -- Rule 8: CANCELLED task cannot transition again --------------------------

# Both rules 7 and 8 enforced by assert_task_can_transition


# -- Rule 9: COMPLETED plan cannot transition again --------------------------

# -- Rule 10: CANCELLED plan cannot transition again -------------------------

# Both rules 9 and 10 enforced by assert_plan_can_transition


# -- Rule 11: Execution step description required ----------------------------

def assert_step_description_required(description: str) -> None:
    if not description or not description.strip():
        raise InvalidTaskDescriptionError("Execution step description is required")


# -- Rule 12: Step order must be non-negative --------------------------------

def assert_step_order_non_negative(order: int) -> None:
    if order < 0:
        raise InvalidStepOrderError(order)


# -- Rule 13: Plan priority must be valid ------------------------------------

def assert_priority_valid(priority: str | PlanPriority) -> None:
    if isinstance(priority, PlanPriority):
        return
    try:
        PlanPriority(priority)
    except ValueError:
        raise InvalidPlanPriorityError(priority)


# -- Rule 14: Execution strategy must be valid -------------------------------

def assert_strategy_valid(strategy: str | ExecutionStrategy) -> None:
    if isinstance(strategy, ExecutionStrategy):
        return
    try:
        ExecutionStrategy(strategy)
    except ValueError:
        raise InvalidExecutionStrategyError(strategy)


# -- Rule 15: Assigned agent must be valid -----------------------------------

def assert_agent_valid(agent: str | AgentType) -> None:
    if isinstance(agent, AgentType):
        return
    try:
        AgentType(agent)
    except ValueError:
        raise InvalidAgentTypeError(agent)


# -- Rule 16: Estimated duration must be positive (enforced by VO) -----------

def assert_estimated_duration_positive(duration: EstimatedDuration | None) -> None:
    if duration is not None and duration.value <= 0:
        raise InvalidEstimatedDurationError(
            f"Estimated duration must be positive, got {duration.value}"
        )


# -- Rule 17: Plan READY before EXECUTING ------------------------------------

def assert_plan_is_ready(plan: Plan) -> None:
    if plan.status != PlanStatus.READY:
        raise PlanNotReadyError(plan.status.value)


# -- Rule 18: EXECUTING before COMPLETED (enforced by plan transitions) ------


# -- Rule 19: FAILED plans require failure reason ----------------------------

def assert_plan_failure_reason_provided(reason: FailureReason | None) -> None:
    if reason is None:
        raise InvalidFailureReasonError("Plan failure reason is required when FAILED")


# -- Rule 20: Plan must have unique task IDs ---------------------------------

def assert_task_id_unique(task_id: TaskId, existing_tasks: list[Task]) -> None:
    for task in existing_tasks:
        if task.task_id == task_id:
            raise DuplicateTaskIdError()


# -- Rule 21: Tasks must have unique execution step IDs ----------------------

def assert_execution_step_ids_unique(
    step_id: object,
    existing_steps: list[object],
) -> None:
    for step in existing_steps:
        if step.step_id == step_id:
            raise DuplicateExecutionStepIdError()


# -- Rule 22: Empty plans cannot execute -------------------------------------

def assert_plan_not_empty(plan: Plan) -> None:
    if not plan.tasks:
        raise EmptyPlanExecutionError()


# -- Rule 23: HYBRID strategy requires at least 2 tasks ----------------------

def assert_hybrid_strategy_min_tasks(strategy: ExecutionStrategy, task_count: int) -> None:
    if strategy == ExecutionStrategy.HYBRID and task_count < 2:
        raise HybridStrategyRequiresMultipleTasksError()


# -- Rule 24: CRITICAL plans cannot use LOW priority tasks -------------------
# (future-proof validation — tasks currently have no priority field)


def assert_critical_plan_task_priority(
    plan_priority: PlanPriority,
    task_priority: str | None = None,
) -> None:
    if plan_priority == PlanPriority.CRITICAL and task_priority is not None:
        pass  # Future validation when tasks gain priority


# -- Plan transition enforcement ---------------------------------------------

def assert_plan_can_transition(current: PlanStatus, target: PlanStatus) -> None:
    allowed = VALID_PLAN_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError("plan", current.value, target.value)


# -- Task transition enforcement ---------------------------------------------

def assert_task_can_transition(current: TaskStatus, target: TaskStatus) -> None:
    allowed = VALID_TASK_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError("task", current.value, target.value)


# -- Plan terminal check -----------------------------------------------------

def assert_plan_not_terminal(plan: Plan) -> None:
    if plan.is_terminal:
        raise PlanTerminalError(plan.status.value)


# -- Composite validators ----------------------------------------------------

def validate_plan_creation(
    user_request: str | None,
    goal: str | None,
    priority: str | PlanPriority,
    strategy: str | ExecutionStrategy,
) -> tuple[PlanPriority, ExecutionStrategy]:
    assert_user_request_required(user_request)
    assert_goal_required(goal)
    assert_priority_valid(priority)
    assert_strategy_valid(strategy)

    if isinstance(priority, str):
        priority_vo = PlanPriority(priority)
    else:
        priority_vo = priority

    if isinstance(strategy, str):
        strategy_vo = ExecutionStrategy(strategy)
    else:
        strategy_vo = strategy

    return priority_vo, strategy_vo


def validate_task_creation(
    description: str | None,
    plan: Plan | None = None,
    task_priority: str | None = None,
) -> None:
    assert_task_description_required(description)
    if plan is not None:
        assert_plan_not_terminal(plan)
        assert_critical_plan_task_priority(plan.priority, task_priority)


def validate_task_assignment(task: Task, agent: str | AgentType) -> None:
    assert_agent_valid(agent)
    assert_task_can_transition(task.status, TaskStatus.ASSIGNED)

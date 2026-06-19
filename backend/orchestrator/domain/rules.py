from __future__ import annotations

from backend.orchestrator.domain.exceptions import (
    AllWorkflowsNotCompletedError,
    DuplicateExecutionOrderError,
    DuplicateWorkflowIdError,
    HybridModeRequiresTwoStepsError,
    InvalidExecutionOrderError,
    InvalidExecutionResultError,
    InvalidFailureReasonError,
    InvalidTransitionError,
    InvalidUserIntentError,
    InvalidWorkflowGoalError,
    OrchestrationTerminalError,
    StepNotStartedError,
    WorkflowHasNoStepsError,
    WorkflowNotStartedError,
    WorkflowStepTerminalError,
    WorkflowTerminalError,
)
from backend.orchestrator.domain.model import (
    ExecutionMode,
    ExecutionOrder,
    ExecutionResult,
    FailureReason,
    Orchestration,
    OrchestrationStatus,
    VALID_ORCHESTRATION_TRANSITIONS,
    VALID_WORKFLOW_STEP_TRANSITIONS,
    VALID_WORKFLOW_TRANSITIONS,
    Workflow,
    WorkflowStep,
    WorkflowStepStatus,
    WorkflowStatus,
)

# ===========================================================================
# Rule 1: Intent required
# ===========================================================================


def assert_intent_required(intent: str | None) -> None:
    if not intent or not intent.strip():
        raise InvalidUserIntentError("User intent is required")


# ===========================================================================
# Rule 2: Goal required
# ===========================================================================


def assert_goal_required(goal: str | None) -> None:
    if not goal or not goal.strip():
        raise InvalidWorkflowGoalError("Workflow goal is required")


# ===========================================================================
# Rule 3: Workflow must contain at least one step before start
# ===========================================================================


def assert_workflow_has_steps(workflow: Workflow) -> None:
    if not workflow.steps:
        raise WorkflowHasNoStepsError()


# ===========================================================================
# Rule 4: Workflow step must have valid agent role
# ===========================================================================

# Enforced by AgentRole enum validation at construction time.

# ===========================================================================
# Rule 5: Execution order must be non-negative
# ===========================================================================

# Enforced by ExecutionOrder value object __post_init__.

# ===========================================================================
# Rule 6: COMPLETED orchestration immutable
# Rule 7: CANCELLED orchestration immutable
# ===========================================================================

# Both enforced by assert_orchestration_can_transition via transition map.


def assert_orchestration_can_transition(
    current: OrchestrationStatus, target: OrchestrationStatus
) -> None:
    allowed = VALID_ORCHESTRATION_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError(
            "orchestration", current.value, target.value
        )


# ===========================================================================
# Rule 8: FAILED orchestration requires failure reason
# ===========================================================================


def assert_failure_reason_required(reason: FailureReason | None) -> None:
    if reason is None:
        raise InvalidFailureReasonError(
            "Failure reason is required when FAILED"
        )


# ===========================================================================
# Rule 9: Workflow must start before complete
# Rule 10: Workflow must start before fail
# ===========================================================================


def assert_workflow_started_before(workflow: Workflow, action: str) -> None:
    if workflow.status != WorkflowStatus.RUNNING:
        raise WorkflowNotStartedError(action)


# ===========================================================================
# Rule 11: Step must start before complete
# Rule 12: Step must start before fail
# ===========================================================================


def assert_step_started_before(step: WorkflowStep, action: str) -> None:
    if step.status != WorkflowStepStatus.RUNNING:
        raise StepNotStartedError(action)


# ===========================================================================
# Step transition enforcement
# ===========================================================================


def assert_step_can_transition(
    current: WorkflowStepStatus, target: WorkflowStepStatus
) -> None:
    allowed = VALID_WORKFLOW_STEP_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError("step", current.value, target.value)


# ===========================================================================
# Workflow transition enforcement
# ===========================================================================


def assert_workflow_can_transition(
    current: WorkflowStatus, target: WorkflowStatus
) -> None:
    allowed = VALID_WORKFLOW_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError("workflow", current.value, target.value)


# ===========================================================================
# Rule 13: Duplicate execution order not allowed within workflow
# ===========================================================================


def assert_step_execution_order_unique(
    order: ExecutionOrder,
    existing_steps: list[WorkflowStep],
    mode: ExecutionMode,
) -> None:
    if mode == ExecutionMode.SEQUENTIAL:
        for step in existing_steps:
            if step.execution_order == order:
                raise DuplicateExecutionOrderError(order.value)


# ===========================================================================
# Rule 14: Duplicate workflow IDs not allowed within orchestration
# ===========================================================================


def assert_workflow_id_unique(
    workflow_id: object, existing_workflows: list[Workflow]
) -> None:
    for wf in existing_workflows:
        if wf.workflow_id == workflow_id:
            raise DuplicateWorkflowIdError()


# ===========================================================================
# Rule 15: SEQUENTIAL mode requires unique execution order
# ===========================================================================

# Enforced by assert_step_execution_order_unique.

# ===========================================================================
# Rule 16: PARALLEL mode allows shared execution order
# ===========================================================================

# Enforced vacuously by assert_step_execution_order_unique (skip in PARALLEL).

# ===========================================================================
# Rule 17: HYBRID mode requires at least two steps
# ===========================================================================


def assert_hybrid_mode_min_steps(mode: ExecutionMode, step_count: int) -> None:
    if mode == ExecutionMode.HYBRID and step_count < 2:
        raise HybridModeRequiresTwoStepsError()


# ===========================================================================
# Rule 18: Execution result required when step completes
# ===========================================================================


def assert_execution_result_required(result: ExecutionResult | None) -> None:
    if result is None:
        raise InvalidExecutionResultError(
            "Execution result is required when step completes"
        )


# ===========================================================================
# Rule 19: Failure reason required when failed
# ===========================================================================

# Already enforced by assert_failure_reason_required above (shared with Rule 8).

# ===========================================================================
# Rule 20: All workflows completed before orchestration complete
# ===========================================================================


def assert_all_workflows_completed(orchestration: Orchestration) -> None:
    for wf in orchestration.workflows:
        if wf.status != WorkflowStatus.COMPLETED:
            raise AllWorkflowsNotCompletedError()


# ===========================================================================
# Terminal checks
# ===========================================================================


def assert_orchestration_not_terminal(
    orchestration: Orchestration,
) -> None:
    if orchestration.is_terminal:
        raise OrchestrationTerminalError(orchestration.status.value)


def assert_workflow_not_terminal(workflow: Workflow) -> None:
    if workflow.is_terminal:
        raise WorkflowTerminalError(workflow.status.value)


def assert_step_not_terminal(step: WorkflowStep) -> None:
    if step.is_terminal:
        raise WorkflowStepTerminalError(step.status.value)


# ===========================================================================
# Composite validators
# ===========================================================================


def validate_orchestration_creation(
    intent: str | None,
    goal: str | None,
) -> None:
    assert_intent_required(intent)
    assert_goal_required(goal)

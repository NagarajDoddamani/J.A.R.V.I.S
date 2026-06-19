from __future__ import annotations

from datetime import datetime, timezone

from backend.orchestrator.domain.model import (
    AgentRole,
    ExecutionMode,
    ExecutionOrder,
    ExecutionResult,
    FailureReason,
    Orchestration,
    OrchestrationCompleted,
    OrchestrationCreated,
    OrchestrationId,
    OrchestrationStatus,
    UserIntent,
    Workflow,
    WorkflowCreated,
    WorkflowGoal,
    WorkflowId,
    WorkflowStep,
    WorkflowStepCompleted,
    WorkflowStepFailed,
    WorkflowStepStatus,
)
from backend.orchestrator.domain.rules import (
    validate_orchestration_creation,
)


class OrchestratorFactory:
    """Factory for creating validated orchestrator domain aggregates."""

    @staticmethod
    def create_orchestration(
        *,
        intent: str,
        goal: str,
    ) -> tuple[Orchestration, OrchestrationCreated]:
        validate_orchestration_creation(intent=intent, goal=goal)

        intent_vo = UserIntent(value=intent)
        goal_vo = WorkflowGoal(value=goal)

        now = datetime.now(tz=timezone.utc)
        orchestration = Orchestration(
            orchestration_id=OrchestrationId(),
            intent=intent_vo,
            goal=goal_vo,
            status=OrchestrationStatus.CREATED,
            created_at=now,
        )

        event = OrchestrationCreated(
            orchestration_id=orchestration.orchestration_id,
            intent=intent,
            goal=goal,
            occurred_at=now,
        )

        return orchestration, event

    @staticmethod
    def create_workflow(
        *,
        orchestration: Orchestration,
        goal: str,
        mode: str | ExecutionMode = ExecutionMode.SEQUENTIAL,
    ) -> tuple[Workflow, WorkflowCreated]:
        if isinstance(mode, str):
            mode = ExecutionMode(mode)

        goal_vo = WorkflowGoal(value=goal)
        now = datetime.now(tz=timezone.utc)

        workflow = Workflow(
            workflow_id=WorkflowId(),
            goal=goal_vo,
            mode=mode,
        )

        orchestration.add_workflow(workflow)

        event = WorkflowCreated(
            workflow_id=workflow.workflow_id,
            orchestration_id=orchestration.orchestration_id,
            goal=goal,
            mode=mode.value,
            occurred_at=now,
        )

        return workflow, event

    @staticmethod
    def add_step(
        *,
        workflow: Workflow,
        agent_role: str | AgentRole,
        execution_order: int = 0,
    ) -> WorkflowStep:
        if isinstance(agent_role, str):
            from backend.orchestrator.domain.exceptions import (
                InvalidAgentRoleError,
            )

            try:
                agent_role = AgentRole(agent_role)
            except ValueError:
                raise InvalidAgentRoleError(agent_role)

        order_vo = ExecutionOrder(value=execution_order)

        step = WorkflowStep(
            step_id=WorkflowId(),
            agent_role=agent_role,
            execution_order=order_vo,
            status=WorkflowStepStatus.PENDING,
        )

        workflow.add_step(step)
        return step

    @staticmethod
    def complete_step(
        *,
        step: WorkflowStep,
        result: str,
    ) -> WorkflowStepCompleted:
        result_vo = ExecutionResult(value=result)
        step.complete(result_vo)
        return step.events[-1]

    @staticmethod
    def fail_step(
        *,
        step: WorkflowStep,
        reason: str,
    ) -> WorkflowStepFailed:
        reason_vo = FailureReason(value=reason)
        step.fail(reason_vo)
        return step.events[-1]

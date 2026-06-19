from __future__ import annotations

from datetime import datetime, timezone

from backend.planner.domain.exceptions import InvalidAgentTypeError, InvalidExecutionStrategyError, InvalidPlanPriorityError
from backend.planner.domain.model import (
    AgentType,
    ExecutionStep,
    ExecutionStepId,
    ExecutionStrategy,
    FailureReason,
    Plan,
    PlanCancelled,
    PlanCompleted,
    PlanCreated,
    PlanFailed,
    PlanGoal,
    PlanId,
    PlanPriority,
    PlanReady,
    PlanStatus,
    Task,
    TaskAssigned,
    TaskCompleted,
    TaskCreated,
    TaskDescription,
    TaskFailed,
    TaskId,
    TaskStatus,
    UserRequest,
)
from backend.planner.domain.rules import (
    assert_failure_reason_provided,
    assert_plan_not_terminal,
    assert_task_id_unique,
    validate_plan_creation,
    validate_task_creation,
)


class PlannerFactory:
    """Factory for creating validated planner domain aggregates."""

    @staticmethod
    def create_plan(
        *,
        user_request: str,
        goal: str,
        priority: str | PlanPriority,
        strategy: str | ExecutionStrategy,
    ) -> tuple[Plan, PlanCreated]:
        priority_vo, strategy_vo = validate_plan_creation(
            user_request=user_request,
            goal=goal,
            priority=priority,
            strategy=strategy,
        )

        user_request_vo = UserRequest(value=user_request)
        goal_vo = PlanGoal(value=goal)

        now = datetime.now(tz=timezone.utc)
        plan = Plan(
            plan_id=PlanId(),
            user_request=user_request_vo,
            goal=goal_vo,
            priority=priority_vo,
            strategy=strategy_vo,
            status=PlanStatus.DRAFT,
            created_at=now,
        )

        event = PlanCreated(
            plan_id=plan.plan_id,
            user_request=user_request,
            goal=goal,
            priority=priority_vo.value,
            strategy=strategy_vo.value,
            occurred_at=now,
        )

        return plan, event

    @staticmethod
    def add_task(
        *,
        plan: Plan,
        description: str,
    ) -> tuple[Task, TaskCreated]:
        validate_task_creation(
            description=description,
            plan=plan,
        )

        task_description = TaskDescription(value=description)
        now = datetime.now(tz=timezone.utc)
        task = Task(
            task_id=TaskId(),
            plan_id=plan.plan_id,
            description=task_description,
            status=TaskStatus.PENDING,
        )

        plan.add_task(task)

        event = TaskCreated(
            task_id=task.task_id,
            description=description,
            occurred_at=now,
        )

        return task, event

    @staticmethod
    def start_task(
        *,
        task: Task,
    ) -> None:
        task.start()

    @staticmethod
    def assign_task(
        *,
        task: Task,
        agent: str | AgentType,
    ) -> TaskAssigned:
        if isinstance(agent, str):
            try:
                agent = AgentType(agent)
            except ValueError:
                raise InvalidAgentTypeError(agent)

        task.assign(agent)
        return task.events[-1]

    @staticmethod
    def complete_task(
        *,
        task: Task,
    ) -> TaskCompleted:
        task.complete()
        return task.events[-1]

    @staticmethod
    def fail_task(
        *,
        task: Task,
        reason: str,
    ) -> TaskFailed:
        reason_vo = FailureReason(value=reason)
        task.fail(reason_vo)
        return task.events[-1]

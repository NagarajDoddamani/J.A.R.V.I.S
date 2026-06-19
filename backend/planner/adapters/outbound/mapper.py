from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID, uuid4

from backend.planner.application.persistence.dto import (
    ExecutionStepStorageDTO,
    PlanStorageDTO,
    PlannerOutboxStorageDTO,
    TaskStorageDTO,
)
from backend.planner.domain.model import (
    AgentType,
    EstimatedDuration,
    ExecutionStep,
    ExecutionStepId,
    ExecutionStrategy,
    FailureReason,
    Plan,
    PlanApproved,
    PlanCancelled,
    PlanCompleted,
    PlanCreated,
    PlanExecutionStarted,
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

PlannerOutboxDomainEvent = (
    PlanCreated
    | PlanApproved
    | PlanReady
    | PlanExecutionStarted
    | PlanCompleted
    | PlanFailed
    | PlanCancelled
    | TaskCreated
    | TaskAssigned
    | TaskCompleted
    | TaskFailed
)

_EVENT_TYPE_MAP: dict[type, str] = {
    PlanCreated: "planner.plan.created",
    PlanApproved: "planner.plan.approved",
    PlanReady: "planner.plan.ready",
    PlanExecutionStarted: "planner.plan.execution_started",
    PlanCompleted: "planner.plan.completed",
    PlanFailed: "planner.plan.failed",
    PlanCancelled: "planner.plan.cancelled",
    TaskCreated: "planner.task.created",
    TaskAssigned: "planner.task.assigned",
    TaskCompleted: "planner.task.completed",
    TaskFailed: "planner.task.failed",
}

_EVENT_TYPE_REVERSE: dict[str, type] = {v: k for k, v in _EVENT_TYPE_MAP.items()}


class PlanMapperImpl:
    def domain_to_dto(self, plan: Plan) -> PlanStorageDTO:
        return PlanStorageDTO(
            plan_id=str(plan.plan_id),
            user_request=str(plan.user_request) if plan.user_request else None,
            goal=str(plan.goal) if plan.goal else None,
            priority=plan.priority.value,
            strategy=plan.strategy.value,
            status=plan.status.value,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            failure_reason=str(plan.failure_reason) if hasattr(plan, 'failure_reason') and plan.failure_reason else None,
        )

    def dto_to_domain(
        self, dto: PlanStorageDTO, tasks: list[Task] | None = None
    ) -> Plan:
        user_request = UserRequest(value=dto.user_request) if dto.user_request else None
        goal = PlanGoal(value=dto.goal) if dto.goal else None
        return Plan(
            plan_id=PlanId(value=UUID(dto.plan_id)),
            user_request=user_request,
            goal=goal,
            priority=PlanPriority(dto.priority),
            strategy=ExecutionStrategy(dto.strategy),
            status=PlanStatus(dto.status),
            tasks=tasks or [],
            created_at=dto.created_at or datetime.now(),
            updated_at=dto.updated_at,
        )


class TaskMapperImpl:
    def domain_to_dto(self, task: Task) -> TaskStorageDTO:
        return TaskStorageDTO(
            task_id=str(task.task_id),
            plan_id=str(task.plan_id) if task.plan_id else None,
            description=str(task.description) if task.description else None,
            assigned_agent=task.assigned_agent.value if task.assigned_agent else None,
            status=task.status.value,
            failure_reason=str(task.failure_reason) if task.failure_reason else None,
            estimated_duration=float(task.estimated_duration) if task.estimated_duration else None,
        )

    def dto_to_domain(self, dto: TaskStorageDTO) -> Task:
        description = TaskDescription(value=dto.description) if dto.description else None
        assigned_agent = AgentType(dto.assigned_agent) if dto.assigned_agent else None
        failure_reason = FailureReason(value=dto.failure_reason) if dto.failure_reason else None
        estimated_duration = EstimatedDuration(value=dto.estimated_duration) if dto.estimated_duration is not None else None
        plan_id = PlanId(value=UUID(dto.plan_id)) if dto.plan_id else None
        return Task(
            task_id=TaskId(value=UUID(dto.task_id)),
            plan_id=plan_id,
            description=description,
            assigned_agent=assigned_agent,
            status=TaskStatus(dto.status),
            failure_reason=failure_reason,
            estimated_duration=estimated_duration,
        )


class ExecutionStepMapperImpl:
    def domain_to_dto(self, step: ExecutionStep) -> ExecutionStepStorageDTO:
        return ExecutionStepStorageDTO(
            step_id=str(step.step_id),
            task_id=str(step.task_id) if step.task_id else None,
            step_order=step.step_order,
            description=step.description,
            status=step.status.value,
        )

    def dto_to_domain(self, dto: ExecutionStepStorageDTO) -> ExecutionStep:
        task_id = TaskId(value=UUID(dto.task_id)) if dto.task_id else None
        return ExecutionStep(
            step_id=ExecutionStepId(value=UUID(dto.step_id)),
            task_id=task_id,
            step_order=dto.step_order,
            description=dto.description,
            status=TaskStatus(dto.status),
        )


class PlannerOutboxMapperImpl:
    def event_to_dto(self, event: PlannerOutboxDomainEvent) -> PlannerOutboxStorageDTO:
        event_type = _EVENT_TYPE_MAP.get(type(event), "unknown")
        aggregate_id = self._get_aggregate_id(event)
        payload = self._build_payload(event)
        return PlannerOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type=event_type,
            aggregate_id=aggregate_id,
            occurred_at=event.occurred_at,
            payload=json.dumps(payload) if payload else None,
            published=False,
        )

    def dto_to_event(self, dto: PlannerOutboxStorageDTO) -> PlannerOutboxDomainEvent:
        event_cls = _EVENT_TYPE_REVERSE.get(dto.event_type)
        if event_cls is None:
            raise ValueError(f"Unknown event_type: {dto.event_type}")
        payload = json.loads(dto.payload) if dto.payload else {}
        aggregate_uuid = UUID(dto.aggregate_id)
        event_uuid = UUID(dto.event_id)

        if event_cls is PlanCreated:
            return PlanCreated(
                event_id=event_uuid,
                plan_id=PlanId(value=aggregate_uuid),
                user_request=payload.get("user_request", ""),
                goal=payload.get("goal", ""),
                priority=payload.get("priority", "normal"),
                strategy=payload.get("strategy", "sequential"),
                occurred_at=dto.occurred_at,
            )
        if event_cls is PlanApproved:
            return PlanApproved(
                event_id=event_uuid,
                plan_id=PlanId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is PlanReady:
            return PlanReady(
                event_id=event_uuid,
                plan_id=PlanId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is PlanExecutionStarted:
            return PlanExecutionStarted(
                event_id=event_uuid,
                plan_id=PlanId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is PlanCompleted:
            return PlanCompleted(
                event_id=event_uuid,
                plan_id=PlanId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is PlanFailed:
            return PlanFailed(
                event_id=event_uuid,
                plan_id=PlanId(value=aggregate_uuid),
                failure_reason=payload.get("failure_reason", ""),
                occurred_at=dto.occurred_at,
            )
        if event_cls is PlanCancelled:
            return PlanCancelled(
                event_id=event_uuid,
                plan_id=PlanId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is TaskCreated:
            return TaskCreated(
                event_id=event_uuid,
                task_id=TaskId(value=aggregate_uuid),
                description=payload.get("description", ""),
                occurred_at=dto.occurred_at,
            )
        if event_cls is TaskAssigned:
            return TaskAssigned(
                event_id=event_uuid,
                task_id=TaskId(value=aggregate_uuid),
                assigned_agent=AgentType(payload.get("assigned_agent", "planner")),
                occurred_at=dto.occurred_at,
            )
        if event_cls is TaskCompleted:
            return TaskCompleted(
                event_id=event_uuid,
                task_id=TaskId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is TaskFailed:
            return TaskFailed(
                event_id=event_uuid,
                task_id=TaskId(value=aggregate_uuid),
                failure_reason=payload.get("failure_reason", ""),
                occurred_at=dto.occurred_at,
            )

        raise ValueError(f"Unsupported event type: {event_cls}")

    @staticmethod
    def _get_aggregate_id(event: PlannerOutboxDomainEvent) -> str:
        if isinstance(event, (PlanCreated, PlanApproved, PlanReady,
                              PlanExecutionStarted, PlanCompleted,
                              PlanFailed, PlanCancelled)):
            return str(event.plan_id)
        return str(event.task_id)

    @staticmethod
    def _build_payload(event: PlannerOutboxDomainEvent) -> dict | None:
        if isinstance(event, PlanCreated):
            return {
                "user_request": event.user_request,
                "goal": event.goal,
                "priority": event.priority,
                "strategy": event.strategy,
            }
        if isinstance(event, PlanFailed):
            return {"failure_reason": event.failure_reason}
        if isinstance(event, TaskCreated):
            return {"description": event.description}
        if isinstance(event, TaskAssigned):
            return {"assigned_agent": event.assigned_agent.value}
        if isinstance(event, TaskFailed):
            return {"failure_reason": event.failure_reason}
        return None

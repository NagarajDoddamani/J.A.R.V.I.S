from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from backend.planner.application.persistence.dto import (
    ExecutionStepStorageDTO,
    PlanStorageDTO,
    PlannerOutboxStorageDTO,
    TaskStorageDTO,
)
from backend.planner.application.persistence.mapper import (
    ExecutionStepMapper,
    PlanMapper,
    PlannerOutboxDomainEvent,
    PlannerOutboxMapper,
    TaskMapper,
)
from backend.planner.application.persistence.schema import (
    EXECUTION_STEPS_TABLE,
    PLANNER_OUTBOX_TABLE,
    PLANS_TABLE,
    TASKS_TABLE,
    ColumnContract,
    TableContract,
)
from backend.planner.domain.model import (
    AgentType,
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
from backend.planner.domain.rules import (
    MAX_FAILURE_REASON_LENGTH,
    MAX_PLAN_GOAL_LENGTH,
    MAX_TASK_DESCRIPTION_LENGTH,
    MAX_USER_REQUEST_LENGTH,
)
from backend.planner.application.ports.outbox import PlannerOutboxEvent

# ===================================================================
# Constants
# ===================================================================

_NOW = datetime(2026, 6, 9, 14, 0, 0, tzinfo=timezone.utc)
_NOW2 = datetime(2026, 6, 9, 15, 0, 0, tzinfo=timezone.utc)

# ===================================================================
# Stub mapper implementations (conform to mapper protocols)
# ===================================================================


class StubPlanMapper:
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
        )

    def dto_to_domain(self, dto: PlanStorageDTO) -> Plan:
        return Plan(
            plan_id=PlanId(value=UUID(dto.plan_id)),
            user_request=UserRequest(value=dto.user_request) if dto.user_request else None,
            goal=PlanGoal(value=dto.goal) if dto.goal else None,
            priority=PlanPriority(dto.priority),
            strategy=ExecutionStrategy(dto.strategy),
            status=PlanStatus(dto.status),
            created_at=dto.created_at or _NOW,
            updated_at=dto.updated_at,
        )


class StubTaskMapper:
    def domain_to_dto(self, task: Task) -> TaskStorageDTO:
        return TaskStorageDTO(
            task_id=str(task.task_id),
            description=str(task.description) if task.description else None,
            assigned_agent=task.assigned_agent.value if task.assigned_agent else None,
            status=task.status.value,
            failure_reason=str(task.failure_reason) if task.failure_reason else None,
            estimated_duration=float(task.estimated_duration) if task.estimated_duration else None,
        )

    def dto_to_domain(self, dto: TaskStorageDTO) -> Task:
        agent = AgentType(dto.assigned_agent) if dto.assigned_agent else None
        reason = FailureReason(value=dto.failure_reason) if dto.failure_reason else None
        duration = None
        if dto.estimated_duration is not None:
            from backend.planner.domain.model import EstimatedDuration
            duration = EstimatedDuration(value=dto.estimated_duration)
        return Task(
            task_id=TaskId(value=UUID(dto.task_id)),
            description=TaskDescription(value=dto.description) if dto.description else None,
            assigned_agent=agent,
            status=TaskStatus(dto.status),
            failure_reason=reason,
            estimated_duration=duration,
        )


class StubExecutionStepMapper:
    def domain_to_dto(self, step: ExecutionStep) -> ExecutionStepStorageDTO:
        return ExecutionStepStorageDTO(
            step_id=str(step.step_id),
            task_id=str(step.task_id) if step.task_id else None,
            step_order=step.step_order,
            description=step.description,
            status=step.status.value,
        )

    def dto_to_domain(self, dto: ExecutionStepStorageDTO) -> ExecutionStep:
        return ExecutionStep(
            step_id=ExecutionStepId(value=UUID(dto.step_id)),
            task_id=TaskId(value=UUID(dto.task_id)) if dto.task_id else None,
            step_order=dto.step_order,
            description=dto.description,
            status=TaskStatus(dto.status),
        )


class StubPlannerOutboxMapper:
    def event_to_dto(
        self, event: PlannerOutboxDomainEvent
    ) -> PlannerOutboxStorageDTO:
        if isinstance(event, (PlanCreated, PlanApproved, PlanReady, PlanExecutionStarted, PlanCompleted, PlanFailed, PlanCancelled)):
            aggregate_id = str(event.plan_id)
        else:
            aggregate_id = str(event.task_id)

        if isinstance(event, PlanCreated):
            event_type = "plan.created"
        elif isinstance(event, PlanApproved):
            event_type = "plan.approved"
        elif isinstance(event, PlanReady):
            event_type = "plan.ready"
        elif isinstance(event, PlanExecutionStarted):
            event_type = "plan.execution_started"
        elif isinstance(event, PlanCompleted):
            event_type = "plan.completed"
        elif isinstance(event, PlanFailed):
            event_type = "plan.failed"
        elif isinstance(event, PlanCancelled):
            event_type = "plan.cancelled"
        elif isinstance(event, TaskCreated):
            event_type = "task.created"
        elif isinstance(event, TaskAssigned):
            event_type = "task.assigned"
        elif isinstance(event, TaskCompleted):
            event_type = "task.completed"
        elif isinstance(event, TaskFailed):
            event_type = "task.failed"
        else:
            event_type = "unknown"

        return PlannerOutboxStorageDTO(
            event_id=str(getattr(event, "event_id", aggregate_id)),
            event_type=event_type,
            aggregate_id=aggregate_id,
            occurred_at=event.occurred_at,
            published=False,
        )

    def dto_to_event(
        self, dto: PlannerOutboxStorageDTO
    ) -> PlannerOutboxDomainEvent:
        try:
            plan_id = PlanId(value=UUID(dto.aggregate_id))
        except (ValueError, AttributeError):
            plan_id = PlanId()

        try:
            task_id = TaskId(value=UUID(dto.aggregate_id))
        except (ValueError, AttributeError):
            task_id = TaskId()

        if dto.event_type == "plan.created":
            return PlanCreated(
                plan_id=plan_id, user_request="", goal="",
                priority="normal", strategy="sequential",
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "plan.approved":
            return PlanApproved(plan_id=plan_id, occurred_at=dto.occurred_at)
        elif dto.event_type == "plan.ready":
            return PlanReady(plan_id=plan_id, occurred_at=dto.occurred_at)
        elif dto.event_type == "plan.execution_started":
            return PlanExecutionStarted(plan_id=plan_id, occurred_at=dto.occurred_at)
        elif dto.event_type == "plan.completed":
            return PlanCompleted(plan_id=plan_id, occurred_at=dto.occurred_at)
        elif dto.event_type == "plan.failed":
            return PlanFailed(
                plan_id=plan_id, failure_reason="error",
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "plan.cancelled":
            return PlanCancelled(plan_id=plan_id, occurred_at=dto.occurred_at)
        elif dto.event_type == "task.created":
            return TaskCreated(
                task_id=task_id, description="",
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "task.assigned":
            return TaskAssigned(
                task_id=task_id, assigned_agent=AgentType.RESEARCH,
                occurred_at=dto.occurred_at,
            )
        elif dto.event_type == "task.completed":
            return TaskCompleted(task_id=task_id, occurred_at=dto.occurred_at)
        elif dto.event_type == "task.failed":
            return TaskFailed(
                task_id=task_id, failure_reason="err",
                occurred_at=dto.occurred_at,
            )
        else:
            raise ValueError(f"Unknown event_type: {dto.event_type}")


# ===================================================================
# DTO construction tests
# ===================================================================


class TestPlanStorageDTO:
    def test_all_fields_present(self) -> None:
        dto = PlanStorageDTO(
            plan_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            user_request="test request",
            goal="test goal",
            priority="high",
            strategy="sequential",
            status="approved",
            created_at=_NOW,
            updated_at=_NOW2,
            failure_reason=None,
        )
        assert dto.plan_id == "01975c2f-4aef-7cf1-a940-ae54bf596280"
        assert dto.user_request == "test request"
        assert dto.goal == "test goal"
        assert dto.priority == "high"
        assert dto.strategy == "sequential"
        assert dto.status == "approved"
        assert dto.created_at == _NOW
        assert dto.updated_at == _NOW2
        assert dto.failure_reason is None

    def test_optional_fields_defaults(self) -> None:
        dto = PlanStorageDTO(plan_id="id-1")
        assert dto.user_request is None
        assert dto.goal is None
        assert dto.priority == "normal"
        assert dto.strategy == "sequential"
        assert dto.status == "draft"
        assert dto.created_at is None
        assert dto.updated_at is None
        assert dto.failure_reason is None

    def test_nullable_fields(self) -> None:
        dto = PlanStorageDTO(
            plan_id="id-1", user_request=None, goal=None,
            created_at=_NOW, updated_at=None, failure_reason=None,
        )
        assert dto.user_request is None
        assert dto.goal is None
        assert dto.updated_at is None
        assert dto.failure_reason is None
        assert dto.created_at == _NOW

    def test_frozen(self) -> None:
        dto = PlanStorageDTO(plan_id="id-1")
        with pytest.raises(AttributeError):
            dto.plan_id = "changed"  # type: ignore

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(PlanStorageDTO)
        assert len(fields) == 9

    def test_all_fields_have_types(self) -> None:
        import dataclasses
        for f in dataclasses.fields(PlanStorageDTO):
            assert f.type is not None, f"Field {f.name} has no type annotation"

    def test_explicit_priority_values(self) -> None:
        for priority in ("low", "normal", "high", "critical"):
            dto = PlanStorageDTO(plan_id="id-1", priority=priority)
            assert dto.priority == priority

    def test_explicit_strategy_values(self) -> None:
        for strategy in ("sequential", "parallel", "hybrid"):
            dto = PlanStorageDTO(plan_id="id-1", strategy=strategy)
            assert dto.strategy == strategy

    def test_explicit_status_values(self) -> None:
        for status in ("draft", "approved", "planning", "ready",
                       "executing", "completed", "failed", "cancelled"):
            dto = PlanStorageDTO(plan_id="id-1", status=status)
            assert dto.status == status

    def test_full_failure_reason(self) -> None:
        dto = PlanStorageDTO(
            plan_id="id-1", failure_reason="Something went wrong",
        )
        assert dto.failure_reason == "Something went wrong"


class TestTaskStorageDTO:
    def test_all_fields_present(self) -> None:
        dto = TaskStorageDTO(
            task_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            plan_id="01975c2f-4aef-7cf1-a940-ae54bf596281",
            description="Do something",
            assigned_agent="research",
            status="assigned",
            failure_reason=None,
            estimated_duration=120.0,
        )
        assert dto.task_id == "01975c2f-4aef-7cf1-a940-ae54bf596280"
        assert dto.plan_id == "01975c2f-4aef-7cf1-a940-ae54bf596281"
        assert dto.description == "Do something"
        assert dto.assigned_agent == "research"
        assert dto.status == "assigned"
        assert dto.failure_reason is None
        assert dto.estimated_duration == 120.0

    def test_optional_fields_defaults(self) -> None:
        dto = TaskStorageDTO(task_id="id-1")
        assert dto.plan_id is None
        assert dto.description is None
        assert dto.assigned_agent is None
        assert dto.status == "pending"
        assert dto.failure_reason is None
        assert dto.estimated_duration is None

    def test_nullable_fields(self) -> None:
        dto = TaskStorageDTO(
            task_id="id-1", plan_id=None, description=None,
            assigned_agent=None, failure_reason=None, estimated_duration=None,
        )
        assert dto.plan_id is None
        assert dto.description is None
        assert dto.assigned_agent is None
        assert dto.failure_reason is None
        assert dto.estimated_duration is None

    def test_frozen(self) -> None:
        dto = TaskStorageDTO(task_id="id-1")
        with pytest.raises(AttributeError):
            dto.task_id = "changed"  # type: ignore

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(TaskStorageDTO)
        assert len(fields) == 7

    def test_all_fields_have_types(self) -> None:
        import dataclasses
        for f in dataclasses.fields(TaskStorageDTO):
            assert f.type is not None, f"Field {f.name} has no type annotation"

    def test_explicit_status_values(self) -> None:
        for status in ("pending", "assigned", "running",
                       "completed", "failed", "cancelled"):
            dto = TaskStorageDTO(task_id="id-1", status=status)
            assert dto.status == status

    def test_explicit_agent_values(self) -> None:
        for agent in ("planner", "research", "automation",
                      "memory", "knowledge", "notification", "policy"):
            dto = TaskStorageDTO(task_id="id-1", assigned_agent=agent)
            assert dto.assigned_agent == agent

    def test_failure_reason_present(self) -> None:
        dto = TaskStorageDTO(task_id="id-1", failure_reason="failed")
        assert dto.failure_reason == "failed"

    def test_estimated_duration_float(self) -> None:
        dto = TaskStorageDTO(task_id="id-1", estimated_duration=30.5)
        assert dto.estimated_duration == 30.5


class TestExecutionStepStorageDTO:
    def test_all_fields_present(self) -> None:
        dto = ExecutionStepStorageDTO(
            step_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            task_id="01975c2f-4aef-7cf1-a940-ae54bf596281",
            step_order=1,
            description="Execute step",
            status="running",
        )
        assert dto.step_id == "01975c2f-4aef-7cf1-a940-ae54bf596280"
        assert dto.task_id == "01975c2f-4aef-7cf1-a940-ae54bf596281"
        assert dto.step_order == 1
        assert dto.description == "Execute step"
        assert dto.status == "running"

    def test_default_values(self) -> None:
        dto = ExecutionStepStorageDTO(step_id="id-1")
        assert dto.task_id is None
        assert dto.step_order == 0
        assert dto.description == ""
        assert dto.status == "pending"

    def test_frozen(self) -> None:
        dto = ExecutionStepStorageDTO(step_id="id-1")
        with pytest.raises(AttributeError):
            dto.step_id = "changed"  # type: ignore

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(ExecutionStepStorageDTO)
        assert len(fields) == 5

    def test_all_fields_have_types(self) -> None:
        import dataclasses
        for f in dataclasses.fields(ExecutionStepStorageDTO):
            assert f.type is not None, f"Field {f.name} has no type annotation"

    def test_step_order_non_negative(self) -> None:
        dto = ExecutionStepStorageDTO(step_id="id-1", step_order=0)
        assert dto.step_order == 0
        dto2 = ExecutionStepStorageDTO(step_id="id-2", step_order=10)
        assert dto2.step_order == 10

    def test_explicit_status_values(self) -> None:
        for status in ("pending", "assigned", "running",
                       "completed", "failed", "cancelled"):
            dto = ExecutionStepStorageDTO(step_id="id-1", status=status)
            assert dto.status == status

    def test_nullable_task_id(self) -> None:
        dto = ExecutionStepStorageDTO(step_id="id-1", task_id=None)
        assert dto.task_id is None


class TestPlannerOutboxStorageDTO:
    def test_all_fields_present(self) -> None:
        dto = PlannerOutboxStorageDTO(
            event_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            event_type="plan.created",
            aggregate_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            occurred_at=_NOW,
            payload='{"goal": "test"}',
        )
        assert dto.event_id == "01975c2f-4aef-7cf1-a940-ae54bf596280"
        assert dto.event_type == "plan.created"
        assert dto.aggregate_id == "01975c2f-4aef-7cf1-a940-ae54bf596280"
        assert dto.occurred_at == _NOW
        assert dto.payload == '{"goal": "test"}'

    def test_default_published_false(self) -> None:
        dto = PlannerOutboxStorageDTO(
            event_id="id-1", event_type="plan.created",
            aggregate_id="agg-1", occurred_at=_NOW,
        )
        assert dto.published is False

    def test_explicit_published_true(self) -> None:
        dto = PlannerOutboxStorageDTO(
            event_id="id-1", event_type="plan.created",
            aggregate_id="agg-1", occurred_at=_NOW,
            published=True,
        )
        assert dto.published is True

    def test_nullable_payload(self) -> None:
        dto = PlannerOutboxStorageDTO(
            event_id="id-1", event_type="plan.created",
            aggregate_id="agg-1", occurred_at=_NOW,
        )
        assert dto.payload is None

    def test_frozen(self) -> None:
        dto = PlannerOutboxStorageDTO(
            event_id="id-1", event_type="plan.created",
            aggregate_id="agg-1", occurred_at=_NOW,
        )
        with pytest.raises(AttributeError):
            dto.event_id = "changed"  # type: ignore

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(PlannerOutboxStorageDTO)
        assert len(fields) == 6

    def test_all_fields_have_types(self) -> None:
        import dataclasses
        for f in dataclasses.fields(PlannerOutboxStorageDTO):
            assert f.type is not None, f"Field {f.name} has no type annotation"

    def test_all_event_types(self) -> None:
        for event_type in (
            "plan.created", "plan.approved", "plan.ready",
            "plan.execution_started", "plan.completed",
            "plan.failed", "plan.cancelled",
            "task.created", "task.assigned",
            "task.completed", "task.failed",
        ):
            dto = PlannerOutboxStorageDTO(
                event_id="id-1", event_type=event_type,
                aggregate_id="agg-1", occurred_at=_NOW,
            )
            assert dto.event_type == event_type


# ===================================================================
# Mapper protocol conformance tests
# ===================================================================


class TestPlanMapper:
    @pytest.fixture
    def mapper(self) -> StubPlanMapper:
        return StubPlanMapper()

    def test_protocol_conformance(self) -> None:
        mapper: PlanMapper = StubPlanMapper()
        assert isinstance(mapper, StubPlanMapper)

    def test_domain_to_dto(self, mapper: StubPlanMapper) -> None:
        plan = Plan(
            plan_id=PlanId(),
            user_request=UserRequest(value="test request"),
            goal=PlanGoal(value="test goal"),
            priority=PlanPriority.HIGH,
            strategy=ExecutionStrategy.SEQUENTIAL,
            status=PlanStatus.APPROVED,
            created_at=_NOW,
            updated_at=_NOW2,
        )
        dto = mapper.domain_to_dto(plan)
        assert dto.plan_id == str(plan.plan_id)
        assert dto.user_request == "test request"
        assert dto.goal == "test goal"
        assert dto.priority == "high"
        assert dto.strategy == "sequential"
        assert dto.status == "approved"
        assert dto.created_at == _NOW
        assert dto.updated_at == _NOW2

    def test_dto_to_domain(self, mapper: StubPlanMapper) -> None:
        dto = PlanStorageDTO(
            plan_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            user_request="restored request",
            goal="restored goal",
            priority="critical",
            strategy="parallel",
            status="ready",
            created_at=_NOW,
            updated_at=_NOW2,
        )
        plan = mapper.dto_to_domain(dto)
        assert str(plan.plan_id) == dto.plan_id
        assert plan.user_request is not None
        assert plan.user_request.value == "restored request"
        assert plan.goal is not None
        assert plan.goal.value == "restored goal"
        assert plan.priority == PlanPriority.CRITICAL
        assert plan.strategy == ExecutionStrategy.PARALLEL
        assert plan.status == PlanStatus.READY
        assert plan.created_at == _NOW
        assert plan.updated_at == _NOW2

    def test_roundtrip(self, mapper: StubPlanMapper) -> None:
        original = Plan(
            plan_id=PlanId(),
            user_request=UserRequest(value="roundtrip"),
            goal=PlanGoal(value="roundtrip goal"),
            priority=PlanPriority.LOW,
            strategy=ExecutionStrategy.HYBRID,
            status=PlanStatus.EXECUTING,
            created_at=_NOW,
            updated_at=_NOW,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert str(reconstructed.plan_id) == str(original.plan_id)
        assert reconstructed.user_request is not None
        assert reconstructed.user_request.value == original.user_request.value
        assert reconstructed.goal is not None
        assert reconstructed.goal.value == original.goal.value
        assert reconstructed.priority == original.priority
        assert reconstructed.strategy == original.strategy
        assert reconstructed.status == original.status
        assert reconstructed.created_at == original.created_at
        assert reconstructed.updated_at == original.updated_at

    def test_null_fields_roundtrip(self, mapper: StubPlanMapper) -> None:
        original = Plan(
            plan_id=PlanId(),
            user_request=None,
            goal=None,
            priority=PlanPriority.NORMAL,
            strategy=ExecutionStrategy.SEQUENTIAL,
            status=PlanStatus.DRAFT,
            created_at=_NOW,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.user_request is None
        assert reconstructed.goal is None
        assert reconstructed.updated_at is None

    def test_dto_to_domain_missing_user_request(
        self, mapper: StubPlanMapper
    ) -> None:
        dto = PlanStorageDTO(
            plan_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
        )
        plan = mapper.dto_to_domain(dto)
        assert plan.user_request is None
        assert plan.goal is None

    def test_mapper_has_required_methods(self) -> None:
        mapper: PlanMapper = StubPlanMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


class TestTaskMapper:
    @pytest.fixture
    def mapper(self) -> StubTaskMapper:
        return StubTaskMapper()

    def test_protocol_conformance(self) -> None:
        mapper: TaskMapper = StubTaskMapper()
        assert isinstance(mapper, StubTaskMapper)

    def test_domain_to_dto(self, mapper: StubTaskMapper) -> None:
        task = Task(
            task_id=TaskId(),
            description=TaskDescription(value="Do the thing"),
            assigned_agent=AgentType.RESEARCH,
            status=TaskStatus.ASSIGNED,
            estimated_duration=None,
        )
        dto = mapper.domain_to_dto(task)
        assert dto.task_id == str(task.task_id)
        assert dto.description == "Do the thing"
        assert dto.assigned_agent == "research"
        assert dto.status == "assigned"
        assert dto.failure_reason is None
        assert dto.estimated_duration is None

    def test_domain_to_dto_with_duration(self, mapper: StubTaskMapper) -> None:
        from backend.planner.domain.model import EstimatedDuration
        task = Task(
            task_id=TaskId(),
            description=TaskDescription(value="timed"),
            assigned_agent=AgentType.AUTOMATION,
            status=TaskStatus.RUNNING,
            estimated_duration=EstimatedDuration(value=60.0),
        )
        dto = mapper.domain_to_dto(task)
        assert dto.estimated_duration == 60.0

    def test_dto_to_domain(self, mapper: StubTaskMapper) -> None:
        dto = TaskStorageDTO(
            task_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            description="Restored task",
            assigned_agent="memory",
            status="running",
            failure_reason=None,
            estimated_duration=30.0,
        )
        task = mapper.dto_to_domain(dto)
        assert str(task.task_id) == dto.task_id
        assert task.description is not None
        assert task.description.value == "Restored task"
        assert task.assigned_agent == AgentType.MEMORY
        assert task.status == TaskStatus.RUNNING
        assert task.failure_reason is None
        assert task.estimated_duration is not None
        assert float(task.estimated_duration) == 30.0

    def test_roundtrip(self, mapper: StubTaskMapper) -> None:
        from backend.planner.domain.model import EstimatedDuration
        original = Task(
            task_id=TaskId(),
            description=TaskDescription(value="roundtrip task"),
            assigned_agent=AgentType.NOTIFICATION,
            status=TaskStatus.COMPLETED,
            estimated_duration=EstimatedDuration(value=45.0),
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert str(reconstructed.task_id) == str(original.task_id)
        assert reconstructed.description is not None
        assert reconstructed.description.value == original.description.value
        assert reconstructed.assigned_agent == original.assigned_agent
        assert reconstructed.status == original.status

    def test_null_fields_roundtrip(self, mapper: StubTaskMapper) -> None:
        original = Task(
            task_id=TaskId(),
            description=None,
            assigned_agent=None,
            status=TaskStatus.PENDING,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.description is None
        assert reconstructed.assigned_agent is None
        assert reconstructed.failure_reason is None

    def test_failure_reason_roundtrip(self, mapper: StubTaskMapper) -> None:
        original = Task(
            task_id=TaskId(),
            description=TaskDescription(value="fail task"),
            status=TaskStatus.FAILED,
            failure_reason=FailureReason(value="something broke"),
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.failure_reason is not None
        assert reconstructed.failure_reason.value == "something broke"

    def test_mapper_has_required_methods(self) -> None:
        mapper: TaskMapper = StubTaskMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


class TestExecutionStepMapper:
    @pytest.fixture
    def mapper(self) -> StubExecutionStepMapper:
        return StubExecutionStepMapper()

    def test_protocol_conformance(self) -> None:
        mapper: ExecutionStepMapper = StubExecutionStepMapper()
        assert isinstance(mapper, StubExecutionStepMapper)

    def test_domain_to_dto(self, mapper: StubExecutionStepMapper) -> None:
        step = ExecutionStep(
            step_id=ExecutionStepId(),
            task_id=TaskId(),
            step_order=2,
            description="Verify result",
            status=TaskStatus.COMPLETED,
        )
        dto = mapper.domain_to_dto(step)
        assert dto.step_id == str(step.step_id)
        assert dto.task_id == str(step.task_id)
        assert dto.step_order == 2
        assert dto.description == "Verify result"
        assert dto.status == "completed"

    def test_dto_to_domain(self, mapper: StubExecutionStepMapper) -> None:
        dto = ExecutionStepStorageDTO(
            step_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            task_id="01975c2f-4aef-7cf1-a940-ae54bf596281",
            step_order=0,
            description="Initial step",
            status="pending",
        )
        step = mapper.dto_to_domain(dto)
        assert str(step.step_id) == dto.step_id
        assert str(step.task_id) == dto.task_id
        assert step.step_order == 0
        assert step.description == "Initial step"
        assert step.status == TaskStatus.PENDING

    def test_roundtrip(self, mapper: StubExecutionStepMapper) -> None:
        original = ExecutionStep(
            step_id=ExecutionStepId(),
            task_id=TaskId(),
            step_order=3,
            description="Finalize",
            status=TaskStatus.RUNNING,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert str(reconstructed.step_id) == str(original.step_id)
        assert str(reconstructed.task_id) == str(original.task_id)
        assert reconstructed.step_order == original.step_order
        assert reconstructed.description == original.description
        assert reconstructed.status == original.status

    def test_no_task_id_roundtrip(self, mapper: StubExecutionStepMapper) -> None:
        original = ExecutionStep(
            step_id=ExecutionStepId(),
            step_order=1,
            description="Orphan step",
            status=TaskStatus.PENDING,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.task_id is None

    def test_mapper_has_required_methods(self) -> None:
        mapper: ExecutionStepMapper = StubExecutionStepMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


class TestPlannerOutboxMapper:
    @pytest.fixture
    def mapper(self) -> StubPlannerOutboxMapper:
        return StubPlannerOutboxMapper()

    def test_protocol_conformance(self) -> None:
        mapper: PlannerOutboxMapper = StubPlannerOutboxMapper()
        assert isinstance(mapper, StubPlannerOutboxMapper)

    def test_plan_created_event_to_dto(self, mapper: StubPlannerOutboxMapper) -> None:
        event = PlanCreated(
            plan_id=PlanId(), user_request="r", goal="g",
            priority="n", strategy="s", occurred_at=_NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "plan.created"
        assert dto.aggregate_id == str(event.plan_id)
        assert dto.occurred_at == _NOW
        assert dto.published is False

    def test_plan_approved_event_to_dto(self, mapper: StubPlannerOutboxMapper) -> None:
        event = PlanApproved(plan_id=PlanId(), occurred_at=_NOW)
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "plan.approved"

    def test_plan_ready_event_to_dto(self, mapper: StubPlannerOutboxMapper) -> None:
        event = PlanReady(plan_id=PlanId(), occurred_at=_NOW)
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "plan.ready"

    def test_plan_execution_started_event_to_dto(
        self, mapper: StubPlannerOutboxMapper
    ) -> None:
        event = PlanExecutionStarted(plan_id=PlanId(), occurred_at=_NOW)
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "plan.execution_started"

    def test_plan_completed_event_to_dto(self, mapper: StubPlannerOutboxMapper) -> None:
        event = PlanCompleted(plan_id=PlanId(), occurred_at=_NOW)
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "plan.completed"

    def test_plan_failed_event_to_dto(self, mapper: StubPlannerOutboxMapper) -> None:
        event = PlanFailed(
            plan_id=PlanId(), failure_reason="error", occurred_at=_NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "plan.failed"

    def test_plan_cancelled_event_to_dto(self, mapper: StubPlannerOutboxMapper) -> None:
        event = PlanCancelled(plan_id=PlanId(), occurred_at=_NOW)
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "plan.cancelled"

    def test_task_created_event_to_dto(self, mapper: StubPlannerOutboxMapper) -> None:
        event = TaskCreated(task_id=TaskId(), description="do", occurred_at=_NOW)
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "task.created"
        assert dto.aggregate_id == str(event.task_id)

    def test_task_assigned_event_to_dto(self, mapper: StubPlannerOutboxMapper) -> None:
        event = TaskAssigned(
            task_id=TaskId(), assigned_agent=AgentType.PLANNER,
            occurred_at=_NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "task.assigned"

    def test_task_completed_event_to_dto(self, mapper: StubPlannerOutboxMapper) -> None:
        event = TaskCompleted(task_id=TaskId(), occurred_at=_NOW)
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "task.completed"

    def test_task_failed_event_to_dto(self, mapper: StubPlannerOutboxMapper) -> None:
        event = TaskFailed(
            task_id=TaskId(), failure_reason="err", occurred_at=_NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "task.failed"

    def test_all_events_have_dto_mapping(
        self, mapper: StubPlannerOutboxMapper
    ) -> None:
        pid = PlanId()
        tid = TaskId()
        events: list[PlannerOutboxDomainEvent] = [
            PlanCreated(pid, "r", "g", "n", "s", _NOW),
            PlanApproved(pid, _NOW),
            PlanReady(pid, _NOW),
            PlanExecutionStarted(pid, _NOW),
            PlanCompleted(pid, _NOW),
            PlanFailed(pid, "err", _NOW),
            PlanCancelled(pid, _NOW),
            TaskCreated(tid, "d", _NOW),
            TaskAssigned(tid, AgentType.RESEARCH, _NOW),
            TaskCompleted(tid, _NOW),
            TaskFailed(tid, "err", _NOW),
        ]
        for event in events:
            dto = mapper.event_to_dto(event)
            assert dto.event_id is not None
            assert dto.event_type is not None
            assert dto.aggregate_id is not None

    def test_event_to_dto_published_default(
        self, mapper: StubPlannerOutboxMapper
    ) -> None:
        event = PlanCreated(
            PlanId(), "r", "g", "n", "s", _NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.published is False

    def test_dto_to_event_plan_created(self, mapper: StubPlannerOutboxMapper) -> None:
        pid = PlanId()
        dto = PlannerOutboxStorageDTO(
            event_id=str(pid), event_type="plan.created",
            aggregate_id=str(pid), occurred_at=_NOW,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, PlanCreated)
        assert str(event.plan_id) == dto.aggregate_id

    def test_dto_to_event_plan_approved(self, mapper: StubPlannerOutboxMapper) -> None:
        pid = PlanId()
        dto = PlannerOutboxStorageDTO(
            event_id=str(pid), event_type="plan.approved",
            aggregate_id=str(pid), occurred_at=_NOW,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, PlanApproved)

    def test_dto_to_event_plan_ready(self, mapper: StubPlannerOutboxMapper) -> None:
        pid = PlanId()
        dto = PlannerOutboxStorageDTO(
            event_id=str(pid), event_type="plan.ready",
            aggregate_id=str(pid), occurred_at=_NOW,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, PlanReady)

    def test_dto_to_event_plan_execution_started(
        self, mapper: StubPlannerOutboxMapper
    ) -> None:
        pid = PlanId()
        dto = PlannerOutboxStorageDTO(
            event_id=str(pid), event_type="plan.execution_started",
            aggregate_id=str(pid), occurred_at=_NOW,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, PlanExecutionStarted)

    def test_dto_to_event_plan_completed(
        self, mapper: StubPlannerOutboxMapper
    ) -> None:
        pid = PlanId()
        dto = PlannerOutboxStorageDTO(
            event_id=str(pid), event_type="plan.completed",
            aggregate_id=str(pid), occurred_at=_NOW,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, PlanCompleted)

    def test_dto_to_event_plan_failed(self, mapper: StubPlannerOutboxMapper) -> None:
        pid = PlanId()
        dto = PlannerOutboxStorageDTO(
            event_id=str(pid), event_type="plan.failed",
            aggregate_id=str(pid), occurred_at=_NOW,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, PlanFailed)

    def test_dto_to_event_plan_cancelled(
        self, mapper: StubPlannerOutboxMapper
    ) -> None:
        pid = PlanId()
        dto = PlannerOutboxStorageDTO(
            event_id=str(pid), event_type="plan.cancelled",
            aggregate_id=str(pid), occurred_at=_NOW,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, PlanCancelled)

    def test_dto_to_event_task_created(self, mapper: StubPlannerOutboxMapper) -> None:
        tid = TaskId()
        dto = PlannerOutboxStorageDTO(
            event_id=str(tid), event_type="task.created",
            aggregate_id=str(tid), occurred_at=_NOW,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, TaskCreated)

    def test_dto_to_event_task_assigned(self, mapper: StubPlannerOutboxMapper) -> None:
        tid = TaskId()
        dto = PlannerOutboxStorageDTO(
            event_id=str(tid), event_type="task.assigned",
            aggregate_id=str(tid), occurred_at=_NOW,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, TaskAssigned)

    def test_dto_to_event_task_completed(self, mapper: StubPlannerOutboxMapper) -> None:
        tid = TaskId()
        dto = PlannerOutboxStorageDTO(
            event_id=str(tid), event_type="task.completed",
            aggregate_id=str(tid), occurred_at=_NOW,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, TaskCompleted)

    def test_dto_to_event_task_failed(self, mapper: StubPlannerOutboxMapper) -> None:
        tid = TaskId()
        dto = PlannerOutboxStorageDTO(
            event_id=str(tid), event_type="task.failed",
            aggregate_id=str(tid), occurred_at=_NOW,
        )
        event = mapper.dto_to_event(dto)
        assert isinstance(event, TaskFailed)

    def test_unknown_event_type_raises(
        self, mapper: StubPlannerOutboxMapper
    ) -> None:
        dto = PlannerOutboxStorageDTO(
            event_id="id-1", event_type="unknown.type",
            aggregate_id="agg-1", occurred_at=_NOW,
        )
        with pytest.raises(ValueError, match="unknown"):
            mapper.dto_to_event(dto)

    def test_roundtrip_plan_created(self, mapper: StubPlannerOutboxMapper) -> None:
        original = PlanCreated(
            PlanId(), "r", "g", "n", "s", _NOW,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert type(reconstructed) is type(original)
        assert str(reconstructed.plan_id) == str(original.plan_id)

    def test_roundtrip_plan_failed(self, mapper: StubPlannerOutboxMapper) -> None:
        original = PlanFailed(PlanId(), "error", _NOW)
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, PlanFailed)

    def test_roundtrip_task_created(self, mapper: StubPlannerOutboxMapper) -> None:
        original = TaskCreated(TaskId(), "desc", _NOW)
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, TaskCreated)
        assert str(reconstructed.task_id) == str(original.task_id)

    def test_roundtrip_task_assigned(self, mapper: StubPlannerOutboxMapper) -> None:
        original = TaskAssigned(TaskId(), AgentType.KNOWLEDGE, _NOW)
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, TaskAssigned)

    def test_roundtrip_task_completed(self, mapper: StubPlannerOutboxMapper) -> None:
        original = TaskCompleted(TaskId(), _NOW)
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, TaskCompleted)

    def test_roundtrip_task_failed(self, mapper: StubPlannerOutboxMapper) -> None:
        original = TaskFailed(TaskId(), "err", _NOW)
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, TaskFailed)

    def test_mapper_has_required_methods(self) -> None:
        mapper: PlannerOutboxMapper = StubPlannerOutboxMapper()
        assert hasattr(mapper, "event_to_dto")
        assert hasattr(mapper, "dto_to_event")


# ===================================================================
# Schema contract consistency tests
# ===================================================================


class TestPlansTableSchema:
    def test_column_count(self) -> None:
        assert len(PLANS_TABLE.columns) == 9

    def test_schema_name(self) -> None:
        assert PLANS_TABLE.schema == "planner"
        assert PLANS_TABLE.name == "plans"

    def test_primary_key(self) -> None:
        assert PLANS_TABLE.primary_key == "plan_id"

    def test_indexes(self) -> None:
        expected = {"ix_plans_status", "ix_plans_priority"}
        assert set(PLANS_TABLE.indexes) == expected

    def test_not_nullable_columns(self) -> None:
        non_nullable = {c.name for c in PLANS_TABLE.columns if not c.nullable}
        assert "plan_id" in non_nullable
        assert "priority" in non_nullable
        assert "strategy" in non_nullable
        assert "status" in non_nullable
        assert "created_at" in non_nullable

    def test_nullable_columns(self) -> None:
        nullable = {c.name for c in PLANS_TABLE.columns if c.nullable}
        assert "user_request" in nullable
        assert "goal" in nullable
        assert "updated_at" in nullable
        assert "failure_reason" in nullable

    def test_priority_enum_values(self) -> None:
        col = next(c for c in PLANS_TABLE.columns if c.name == "priority")
        assert col.enum_values == ("low", "normal", "high", "critical")

    def test_strategy_enum_values(self) -> None:
        col = next(c for c in PLANS_TABLE.columns if c.name == "strategy")
        assert col.enum_values == ("sequential", "parallel", "hybrid")

    def test_status_enum_values(self) -> None:
        col = next(c for c in PLANS_TABLE.columns if c.name == "status")
        assert col.enum_values == (
            "draft", "approved", "planning", "ready",
            "executing", "completed", "failed", "cancelled",
        )


class TestTasksTableSchema:
    def test_column_count(self) -> None:
        assert len(TASKS_TABLE.columns) == 7

    def test_schema_name(self) -> None:
        assert TASKS_TABLE.schema == "planner"
        assert TASKS_TABLE.name == "tasks"

    def test_primary_key(self) -> None:
        assert TASKS_TABLE.primary_key == "task_id"

    def test_indexes(self) -> None:
        expected = {"ix_tasks_plan_id", "ix_tasks_status", "ix_tasks_assigned_agent"}
        assert set(TASKS_TABLE.indexes) == expected

    def test_not_nullable_columns(self) -> None:
        non_nullable = {c.name for c in TASKS_TABLE.columns if not c.nullable}
        assert "task_id" in non_nullable
        assert "status" in non_nullable

    def test_nullable_columns(self) -> None:
        nullable = {c.name for c in TASKS_TABLE.columns if c.nullable}
        assert "plan_id" in nullable
        assert "description" in nullable
        assert "assigned_agent" in nullable
        assert "failure_reason" in nullable
        assert "estimated_duration" in nullable

    def test_status_enum_values(self) -> None:
        col = next(c for c in TASKS_TABLE.columns if c.name == "status")
        assert col.enum_values == (
            "pending", "assigned", "running",
            "completed", "failed", "cancelled",
        )

    def test_assigned_agent_enum_values(self) -> None:
        col = next(c for c in TASKS_TABLE.columns if c.name == "assigned_agent")
        assert col.enum_values == (
            "planner", "research", "automation",
            "memory", "knowledge", "notification", "policy",
        )

    def test_assigned_agent_nullable(self) -> None:
        col = next(c for c in TASKS_TABLE.columns if c.name == "assigned_agent")
        assert col.nullable is True


class TestExecutionStepsTableSchema:
    def test_column_count(self) -> None:
        assert len(EXECUTION_STEPS_TABLE.columns) == 5

    def test_schema_name(self) -> None:
        assert EXECUTION_STEPS_TABLE.schema == "planner"
        assert EXECUTION_STEPS_TABLE.name == "execution_steps"

    def test_primary_key(self) -> None:
        assert EXECUTION_STEPS_TABLE.primary_key == "step_id"

    def test_indexes(self) -> None:
        expected = {"ix_execution_steps_task_id", "ix_execution_steps_step_order"}
        assert set(EXECUTION_STEPS_TABLE.indexes) == expected

    def test_not_nullable_columns(self) -> None:
        non_nullable = {c.name for c in EXECUTION_STEPS_TABLE.columns if not c.nullable}
        assert "step_id" in non_nullable
        assert "step_order" in non_nullable
        assert "description" in non_nullable
        assert "status" in non_nullable

    def test_nullable_columns(self) -> None:
        nullable = {c.name for c in EXECUTION_STEPS_TABLE.columns if c.nullable}
        assert "task_id" in nullable

    def test_status_enum_values(self) -> None:
        col = next(c for c in EXECUTION_STEPS_TABLE.columns if c.name == "status")
        assert col.enum_values == (
            "pending", "assigned", "running",
            "completed", "failed", "cancelled",
        )


class TestPlannerOutboxTableSchema:
    def test_column_count(self) -> None:
        assert len(PLANNER_OUTBOX_TABLE.columns) == 6

    def test_schema_name(self) -> None:
        assert PLANNER_OUTBOX_TABLE.schema == "planner"
        assert PLANNER_OUTBOX_TABLE.name == "outbox"

    def test_primary_key(self) -> None:
        assert PLANNER_OUTBOX_TABLE.primary_key == "event_id"

    def test_indexes(self) -> None:
        expected = {
            "ix_planner_outbox_unpublished",
            "ix_planner_outbox_aggregate",
        }
        assert set(PLANNER_OUTBOX_TABLE.indexes) == expected

    def test_not_nullable_columns(self) -> None:
        non_nullable = {c.name for c in PLANNER_OUTBOX_TABLE.columns if not c.nullable}
        assert "event_id" in non_nullable
        assert "event_type" in non_nullable
        assert "aggregate_id" in non_nullable
        assert "occurred_at" in non_nullable
        assert "published" in non_nullable

    def test_nullable_payload(self) -> None:
        col = next(c for c in PLANNER_OUTBOX_TABLE.columns if c.name == "payload")
        assert col.nullable is True

    def test_event_type_enum_values(self) -> None:
        col = next(
            c for c in PLANNER_OUTBOX_TABLE.columns if c.name == "event_type"
        )
        assert col.enum_values == (
            "plan.created", "plan.approved", "plan.ready",
            "plan.execution_started", "plan.completed",
            "plan.failed", "plan.cancelled",
            "task.created", "task.assigned", "task.completed",
            "task.failed",
        )

    def test_event_type_max_length(self) -> None:
        col = next(
            c for c in PLANNER_OUTBOX_TABLE.columns if c.name == "event_type"
        )
        assert col.max_length == 32

    def test_event_type_has_eleven_events(self) -> None:
        col = next(
            c for c in PLANNER_OUTBOX_TABLE.columns if c.name == "event_type"
        )
        assert len(col.enum_values) == 11


# ===================================================================
# Alignment tests (DTO ↔ schema, DTO ↔ domain, schema ↔ enum)
# ===================================================================


class TestDTOAlignmentWithSchema:
    def test_plan_dto_field_count_matches_schema(self) -> None:
        import dataclasses
        dto_fields = len(dataclasses.fields(PlanStorageDTO))
        schema_cols = len(PLANS_TABLE.columns)
        assert dto_fields == schema_cols, (
            f"DTO has {dto_fields} fields but schema has {schema_cols} columns"
        )

    def test_plan_dto_types_match_schema_enums(self) -> None:
        import dataclasses
        for col in PLANS_TABLE.columns:
            if col.enum_values:
                field = next(
                    (f for f in dataclasses.fields(PlanStorageDTO) if f.name == col.name),
                    None,
                )
                assert field is not None, f"No DTO field for column {col.name}"

    def test_task_dto_field_count_matches_schema(self) -> None:
        import dataclasses
        dto_fields = len(dataclasses.fields(TaskStorageDTO))
        schema_cols = len(TASKS_TABLE.columns)
        assert dto_fields == schema_cols

    def test_step_dto_field_count_matches_schema(self) -> None:
        import dataclasses
        dto_fields = len(dataclasses.fields(ExecutionStepStorageDTO))
        schema_cols = len(EXECUTION_STEPS_TABLE.columns)
        assert dto_fields == schema_cols

    def test_outbox_dto_field_count_matches_schema(self) -> None:
        import dataclasses
        dto_fields = len(dataclasses.fields(PlannerOutboxStorageDTO))
        schema_cols = len(PLANNER_OUTBOX_TABLE.columns)
        assert dto_fields == schema_cols


class TestDTOAlignmentWithDomain:
    def test_plan_dto_has_plan_id(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(PlanStorageDTO)}
        assert "plan_id" in field_names

    def test_plan_dto_has_priority(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(PlanStorageDTO)}
        assert "priority" in field_names

    def test_plan_dto_has_status(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(PlanStorageDTO)}
        assert "status" in field_names

    def test_task_dto_has_task_id(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(TaskStorageDTO)}
        assert "task_id" in field_names

    def test_task_dto_has_plan_id(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(TaskStorageDTO)}
        assert "plan_id" in field_names

    def test_task_dto_has_status(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(TaskStorageDTO)}
        assert "status" in field_names

    def test_step_dto_has_step_id(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(ExecutionStepStorageDTO)}
        assert "step_id" in field_names

    def test_step_dto_has_task_id(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(ExecutionStepStorageDTO)}
        assert "task_id" in field_names

    def test_step_dto_has_step_order(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(ExecutionStepStorageDTO)}
        assert "step_order" in field_names

    def test_outbox_dto_has_event_id(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(PlannerOutboxStorageDTO)}
        assert "event_id" in field_names

    def test_outbox_dto_has_event_type(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(PlannerOutboxStorageDTO)}
        assert "event_type" in field_names

    def test_outbox_dto_has_aggregate_id(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(PlannerOutboxStorageDTO)}
        assert "aggregate_id" in field_names

    def test_outbox_dto_has_published(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(PlannerOutboxStorageDTO)}
        assert "published" in field_names

    def test_outbox_dto_has_payload(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(PlannerOutboxStorageDTO)}
        assert "payload" in field_names


class TestSchemaEnumAlignment:
    def test_priority_enum_values_match_domain(self) -> None:
        col = next(c for c in PLANS_TABLE.columns if c.name == "priority")
        domain_values = tuple(p.value for p in PlanPriority)
        assert col.enum_values == domain_values

    def test_strategy_enum_values_match_domain(self) -> None:
        col = next(c for c in PLANS_TABLE.columns if c.name == "strategy")
        domain_values = tuple(s.value for s in ExecutionStrategy)
        assert col.enum_values == domain_values

    def test_plan_status_enum_values_match_domain(self) -> None:
        col = next(c for c in PLANS_TABLE.columns if c.name == "status")
        domain_values = tuple(s.value for s in PlanStatus)
        assert col.enum_values == domain_values

    def test_task_status_enum_values_match_domain(self) -> None:
        col = next(c for c in TASKS_TABLE.columns if c.name == "status")
        domain_values = tuple(s.value for s in TaskStatus)
        assert col.enum_values == domain_values

    def test_assigned_agent_enum_values_match_domain(self) -> None:
        col = next(c for c in TASKS_TABLE.columns if c.name == "assigned_agent")
        domain_values = tuple(a.value for a in AgentType)
        assert col.enum_values == domain_values

    def test_step_status_enum_values_match_domain(self) -> None:
        col = next(c for c in EXECUTION_STEPS_TABLE.columns if c.name == "status")
        domain_values = tuple(s.value for s in TaskStatus)
        assert col.enum_values == domain_values

    def test_plan_id_string_type(self) -> None:
        pk_col = next(
            c for c in PLANS_TABLE.columns
            if c.name == PLANS_TABLE.primary_key
        )
        assert pk_col.py_type is str

    def test_task_id_string_type(self) -> None:
        pk_col = next(
            c for c in TASKS_TABLE.columns
            if c.name == TASKS_TABLE.primary_key
        )
        assert pk_col.py_type is str

    def test_step_id_string_type(self) -> None:
        pk_col = next(
            c for c in EXECUTION_STEPS_TABLE.columns
            if c.name == EXECUTION_STEPS_TABLE.primary_key
        )
        assert pk_col.py_type is str

    def test_event_id_string_type(self) -> None:
        pk_col = next(
            c for c in PLANNER_OUTBOX_TABLE.columns
            if c.name == PLANNER_OUTBOX_TABLE.primary_key
        )
        assert pk_col.py_type is str


class TestSchemaRuleAlignment:
    def test_plan_id_not_nullable(self) -> None:
        col = next(c for c in PLANS_TABLE.columns if c.name == "plan_id")
        assert col.nullable is False

    def test_status_not_nullable(self) -> None:
        col = next(c for c in PLANS_TABLE.columns if c.name == "status")
        assert col.nullable is False

    def test_priority_not_nullable(self) -> None:
        col = next(c for c in PLANS_TABLE.columns if c.name == "priority")
        assert col.nullable is False

    def test_task_id_not_nullable(self) -> None:
        col = next(c for c in TASKS_TABLE.columns if c.name == "task_id")
        assert col.nullable is False

    def test_step_id_not_nullable(self) -> None:
        col = next(c for c in EXECUTION_STEPS_TABLE.columns if c.name == "step_id")
        assert col.nullable is False

    def test_plans_table_uses_planner_schema(self) -> None:
        assert PLANS_TABLE.schema == "planner"

    def test_tasks_table_uses_planner_schema(self) -> None:
        assert TASKS_TABLE.schema == "planner"

    def test_steps_table_uses_planner_schema(self) -> None:
        assert EXECUTION_STEPS_TABLE.schema == "planner"

    def test_outbox_table_uses_planner_schema(self) -> None:
        assert PLANNER_OUTBOX_TABLE.schema == "planner"

    def test_outbox_event_type_has_eleven_values(self) -> None:
        col = next(
            c for c in PLANNER_OUTBOX_TABLE.columns if c.name == "event_type"
        )
        assert len(col.enum_values) == 11


class TestDomainValueConsistency:
    def test_priority_enum_values(self) -> None:
        assert PlanPriority.LOW.value == "low"
        assert PlanPriority.NORMAL.value == "normal"
        assert PlanPriority.HIGH.value == "high"
        assert PlanPriority.CRITICAL.value == "critical"

    def test_strategy_enum_values(self) -> None:
        assert ExecutionStrategy.SEQUENTIAL.value == "sequential"
        assert ExecutionStrategy.PARALLEL.value == "parallel"
        assert ExecutionStrategy.HYBRID.value == "hybrid"

    def test_plan_status_enum_values(self) -> None:
        assert PlanStatus.DRAFT.value == "draft"
        assert PlanStatus.APPROVED.value == "approved"
        assert PlanStatus.PLANNING.value == "planning"
        assert PlanStatus.READY.value == "ready"
        assert PlanStatus.EXECUTING.value == "executing"
        assert PlanStatus.COMPLETED.value == "completed"
        assert PlanStatus.FAILED.value == "failed"
        assert PlanStatus.CANCELLED.value == "cancelled"

    def test_task_status_enum_values(self) -> None:
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.ASSIGNED.value == "assigned"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_agent_type_enum_values(self) -> None:
        assert AgentType.PLANNER.value == "planner"
        assert AgentType.RESEARCH.value == "research"
        assert AgentType.AUTOMATION.value == "automation"
        assert AgentType.MEMORY.value == "memory"
        assert AgentType.KNOWLEDGE.value == "knowledge"
        assert AgentType.NOTIFICATION.value == "notification"
        assert AgentType.POLICY.value == "policy"

    def test_max_user_request_length(self) -> None:
        assert MAX_USER_REQUEST_LENGTH == 5000

    def test_max_plan_goal_length(self) -> None:
        assert MAX_PLAN_GOAL_LENGTH == 2000

    def test_max_task_description_length(self) -> None:
        assert MAX_TASK_DESCRIPTION_LENGTH == 2000

    def test_max_failure_reason_length(self) -> None:
        assert MAX_FAILURE_REASON_LENGTH == 2000


class TestColumnTypeConsistency:
    def test_plan_id_column_type(self) -> None:
        col = next(c for c in PLANS_TABLE.columns if c.name == "plan_id")
        assert col.py_type is str

    def test_created_at_column_type(self) -> None:
        col = next(c for c in PLANS_TABLE.columns if c.name == "created_at")
        assert col.py_type is datetime

    def test_updated_at_column_type(self) -> None:
        col = next(c for c in PLANS_TABLE.columns if c.name == "updated_at")
        assert col.py_type is datetime

    def test_task_id_column_type(self) -> None:
        col = next(c for c in TASKS_TABLE.columns if c.name == "task_id")
        assert col.py_type is str

    def test_plan_id_in_tasks_column_type(self) -> None:
        col = next(c for c in TASKS_TABLE.columns if c.name == "plan_id")
        assert col.py_type is str

    def test_step_id_column_type(self) -> None:
        col = next(c for c in EXECUTION_STEPS_TABLE.columns if c.name == "step_id")
        assert col.py_type is str

    def test_step_order_column_type(self) -> None:
        col = next(c for c in EXECUTION_STEPS_TABLE.columns if c.name == "step_order")
        assert col.py_type is int

    def test_event_id_column_type(self) -> None:
        col = next(c for c in PLANNER_OUTBOX_TABLE.columns if c.name == "event_id")
        assert col.py_type is str

    def test_published_column_type(self) -> None:
        col = next(c for c in PLANNER_OUTBOX_TABLE.columns if c.name == "published")
        assert col.py_type is bool

    def test_aggregate_id_column_type(self) -> None:
        col = next(c for c in PLANNER_OUTBOX_TABLE.columns if c.name == "aggregate_id")
        assert col.py_type is str

    def test_estimated_duration_column_type(self) -> None:
        col = next(c for c in TASKS_TABLE.columns if c.name == "estimated_duration")
        assert col.py_type is float


# ===================================================================
# Cross-port type alignment: PlannerOutboxEvent == PlannerOutboxDomainEvent
# ===================================================================


class TestOutboxEventTypeAlignment:
    def test_planner_outbox_event_includes_plan_created(self) -> None:
        event: PlannerOutboxEvent = PlanCreated(
            PlanId(), "r", "g", "n", "s", _NOW,
        )
        assert isinstance(event, PlanCreated)
        domain: PlannerOutboxDomainEvent = event
        assert isinstance(domain, PlanCreated)

    def test_planner_outbox_event_includes_plan_approved(self) -> None:
        event: PlannerOutboxEvent = PlanApproved(PlanId(), _NOW)
        domain: PlannerOutboxDomainEvent = event
        assert isinstance(domain, PlanApproved)

    def test_planner_outbox_event_includes_plan_ready(self) -> None:
        event: PlannerOutboxEvent = PlanReady(PlanId(), _NOW)
        domain: PlannerOutboxDomainEvent = event
        assert isinstance(domain, PlanReady)

    def test_planner_outbox_event_includes_execution_started(self) -> None:
        event: PlannerOutboxEvent = PlanExecutionStarted(PlanId(), _NOW)
        domain: PlannerOutboxDomainEvent = event
        assert isinstance(domain, PlanExecutionStarted)

    def test_planner_outbox_event_includes_plan_completed(self) -> None:
        event: PlannerOutboxEvent = PlanCompleted(PlanId(), _NOW)
        domain: PlannerOutboxDomainEvent = event
        assert isinstance(domain, PlanCompleted)

    def test_planner_outbox_event_includes_plan_failed(self) -> None:
        event: PlannerOutboxEvent = PlanFailed(PlanId(), "e", _NOW)
        domain: PlannerOutboxDomainEvent = event
        assert isinstance(domain, PlanFailed)

    def test_planner_outbox_event_includes_plan_cancelled(self) -> None:
        event: PlannerOutboxEvent = PlanCancelled(PlanId(), _NOW)
        domain: PlannerOutboxDomainEvent = event
        assert isinstance(domain, PlanCancelled)

    def test_planner_outbox_event_includes_task_created(self) -> None:
        event: PlannerOutboxEvent = TaskCreated(TaskId(), "d", _NOW)
        domain: PlannerOutboxDomainEvent = event
        assert isinstance(domain, TaskCreated)

    def test_planner_outbox_event_includes_task_assigned(self) -> None:
        event: PlannerOutboxEvent = TaskAssigned(
            TaskId(), AgentType.PLANNER, _NOW,
        )
        domain: PlannerOutboxDomainEvent = event
        assert isinstance(domain, TaskAssigned)

    def test_planner_outbox_event_includes_task_completed(self) -> None:
        event: PlannerOutboxEvent = TaskCompleted(TaskId(), _NOW)
        domain: PlannerOutboxDomainEvent = event
        assert isinstance(domain, TaskCompleted)

    def test_planner_outbox_event_includes_task_failed(self) -> None:
        event: PlannerOutboxEvent = TaskFailed(TaskId(), "e", _NOW)
        domain: PlannerOutboxDomainEvent = event
        assert isinstance(domain, TaskFailed)

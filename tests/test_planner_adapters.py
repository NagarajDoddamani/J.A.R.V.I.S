from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.planner.adapters.outbound.clock import SystemClockAdapter
from backend.planner.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.planner.adapters.outbound.mapper import (
    ExecutionStepMapperImpl,
    PlanMapperImpl,
    PlannerOutboxMapperImpl,
    TaskMapperImpl,
)
from backend.planner.application.persistence.mapper import (
    ExecutionStepMapper,
    PlanMapper,
    PlannerOutboxMapper,
    TaskMapper,
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

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


def _make_plan(
    priority: PlanPriority = PlanPriority.NORMAL,
    strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL,
    status: PlanStatus = PlanStatus.DRAFT,
) -> Plan:
    return Plan(
        plan_id=PlanId(value=UUID("00000000-0000-0000-0000-000000000001")),
        user_request=UserRequest(value="test request"),
        goal=PlanGoal(value="test goal"),
        priority=priority,
        strategy=strategy,
        status=status,
        created_at=NOW,
        updated_at=NOW,
    )


def _make_task(
    status: TaskStatus = TaskStatus.PENDING,
) -> Task:
    return Task(
        task_id=TaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
        description=TaskDescription(value="test task"),
        status=status,
    )


# ===================================================================
# Clock adapter tests
# ===================================================================


class TestSystemClockAdapter:
    def test_now_returns_utc(self) -> None:
        clock = SystemClockAdapter()
        result = clock.now()
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result).total_seconds() == 0.0

    def test_now_returns_datetime(self) -> None:
        clock = SystemClockAdapter()
        assert isinstance(clock.now(), datetime)


# ===================================================================
# ID generator adapter tests
# ===================================================================


class TestUuidGeneratorAdapter:
    def test_generate_plan_id(self) -> None:
        gen = UuidGeneratorAdapter()
        pid = gen.generate_plan_id()
        assert isinstance(pid, str)
        assert UUID(pid)

    def test_generate_task_id(self) -> None:
        gen = UuidGeneratorAdapter()
        tid = gen.generate_task_id()
        assert isinstance(tid, str)
        assert UUID(tid)

    def test_generate_step_id(self) -> None:
        gen = UuidGeneratorAdapter()
        sid = gen.generate_step_id()
        assert isinstance(sid, str)
        assert UUID(sid)

    def test_unique_ids(self) -> None:
        gen = UuidGeneratorAdapter()
        plan_ids = {gen.generate_plan_id() for _ in range(50)}
        task_ids = {gen.generate_task_id() for _ in range(50)}
        step_ids = {gen.generate_step_id() for _ in range(50)}
        assert len(plan_ids) == 50
        assert len(task_ids) == 50
        assert len(step_ids) == 50


# ===================================================================
# PlanMapperImpl tests
# ===================================================================


class TestPlanMapperImpl:
    @pytest.fixture
    def mapper(self) -> PlanMapperImpl:
        return PlanMapperImpl()

    def test_protocol_conformance(self) -> None:
        mapper: PlanMapper = PlanMapperImpl()
        assert isinstance(mapper, PlanMapperImpl)

    def test_domain_to_dto(self, mapper: PlanMapperImpl) -> None:
        plan = _make_plan()
        dto = mapper.domain_to_dto(plan)
        assert dto.plan_id == "00000000-0000-0000-0000-000000000001"
        assert dto.user_request == "test request"
        assert dto.goal == "test goal"
        assert dto.priority == "normal"
        assert dto.strategy == "sequential"
        assert dto.status == "draft"

    def test_dto_to_domain(self, mapper: PlanMapperImpl) -> None:
        plan = _make_plan()
        dto = mapper.domain_to_dto(plan)
        result = mapper.dto_to_domain(dto)
        assert str(result.plan_id) == "00000000-0000-0000-0000-000000000001"
        assert str(result.user_request) == "test request"
        assert result.priority == PlanPriority.NORMAL
        assert result.strategy == ExecutionStrategy.SEQUENTIAL

    def test_roundtrip(self, mapper: PlanMapperImpl) -> None:
        original = _make_plan(
            priority=PlanPriority.HIGH,
            strategy=ExecutionStrategy.PARALLEL,
            status=PlanStatus.APPROVED,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.priority == original.priority
        assert reconstructed.strategy == original.strategy
        assert reconstructed.status == original.status

    def test_null_user_request_and_goal(self, mapper: PlanMapperImpl) -> None:
        plan = Plan(
            plan_id=PlanId(),
            priority=PlanPriority.NORMAL,
            strategy=ExecutionStrategy.SEQUENTIAL,
            status=PlanStatus.DRAFT,
            created_at=NOW,
        )
        dto = mapper.domain_to_dto(plan)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.user_request is None
        assert reconstructed.goal is None


# ===================================================================
# TaskMapperImpl tests
# ===================================================================


class TestTaskMapperImpl:
    @pytest.fixture
    def mapper(self) -> TaskMapperImpl:
        return TaskMapperImpl()

    def test_protocol_conformance(self) -> None:
        mapper: TaskMapper = TaskMapperImpl()
        assert isinstance(mapper, TaskMapperImpl)

    def test_domain_to_dto(self, mapper: TaskMapperImpl) -> None:
        task = _make_task()
        dto = mapper.domain_to_dto(task)
        assert dto.description == "test task"
        assert dto.status == "pending"
        assert dto.assigned_agent is None
        assert dto.failure_reason is None
        assert dto.estimated_duration is None

    def test_dto_to_domain(self, mapper: TaskMapperImpl) -> None:
        task = _make_task(status=TaskStatus.ASSIGNED)
        dto = mapper.domain_to_dto(task)
        result = mapper.dto_to_domain(dto)
        assert result.status == TaskStatus.ASSIGNED
        assert result.assigned_agent is None

    def test_roundtrip(self, mapper: TaskMapperImpl) -> None:
        original = Task(
            task_id=TaskId(),
            description=TaskDescription(value="full task"),
            assigned_agent=AgentType.RESEARCH,
            status=TaskStatus.RUNNING,
            estimated_duration=EstimatedDuration(value=30.0),
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.status == original.status
        assert reconstructed.assigned_agent == original.assigned_agent
        assert reconstructed.estimated_duration == original.estimated_duration

    def test_null_fields(self, mapper: TaskMapperImpl) -> None:
        original = Task(
            task_id=TaskId(),
            status=TaskStatus.PENDING,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.description is None
        assert reconstructed.assigned_agent is None
        assert reconstructed.failure_reason is None
        assert reconstructed.estimated_duration is None

    def test_failure_reason(self, mapper: TaskMapperImpl) -> None:
        original = Task(
            task_id=TaskId(),
            status=TaskStatus.FAILED,
            failure_reason=FailureReason(value="error occurred"),
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.status == TaskStatus.FAILED
        assert str(reconstructed.failure_reason) == "error occurred"


# ===================================================================
# ExecutionStepMapperImpl tests
# ===================================================================


class TestExecutionStepMapperImpl:
    @pytest.fixture
    def mapper(self) -> ExecutionStepMapperImpl:
        return ExecutionStepMapperImpl()

    def test_protocol_conformance(self) -> None:
        mapper: ExecutionStepMapper = ExecutionStepMapperImpl()
        assert isinstance(mapper, ExecutionStepMapperImpl)

    def test_domain_to_dto(self, mapper: ExecutionStepMapperImpl) -> None:
        step = ExecutionStep(
            step_id=ExecutionStepId(value=UUID("00000000-0000-0000-0000-000000000020")),
            task_id=TaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            step_order=1,
            description="step one",
            status=TaskStatus.PENDING,
        )
        dto = mapper.domain_to_dto(step)
        assert dto.step_id == "00000000-0000-0000-0000-000000000020"
        assert dto.step_order == 1
        assert dto.description == "step one"
        assert dto.status == "pending"

    def test_dto_to_domain(self, mapper: ExecutionStepMapperImpl) -> None:
        step = ExecutionStep(
            step_id=ExecutionStepId(),
            step_order=2,
            description="step two",
            status=TaskStatus.RUNNING,
        )
        dto = mapper.domain_to_dto(step)
        result = mapper.dto_to_domain(dto)
        assert result.step_order == 2
        assert result.status == TaskStatus.RUNNING

    def test_roundtrip(self, mapper: ExecutionStepMapperImpl) -> None:
        original = ExecutionStep(
            step_id=ExecutionStepId(),
            task_id=TaskId(),
            step_order=3,
            description="roundtrip",
            status=TaskStatus.COMPLETED,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.step_order == original.step_order
        assert reconstructed.description == original.description
        assert reconstructed.status == original.status

    def test_null_task_id(self, mapper: ExecutionStepMapperImpl) -> None:
        original = ExecutionStep(
            step_id=ExecutionStepId(),
            step_order=0,
            description="no task",
            status=TaskStatus.PENDING,
        )
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.task_id is None


# ===================================================================
# PlannerOutboxMapperImpl tests
# ===================================================================


class TestPlannerOutboxMapperImpl:
    @pytest.fixture
    def mapper(self) -> PlannerOutboxMapperImpl:
        return PlannerOutboxMapperImpl()

    def test_protocol_conformance(self) -> None:
        mapper: PlannerOutboxMapper = PlannerOutboxMapperImpl()
        assert isinstance(mapper, PlannerOutboxMapperImpl)

    def test_plan_created_event(self, mapper: PlannerOutboxMapperImpl) -> None:
        event = PlanCreated(
            plan_id=PlanId(),
            user_request="request",
            goal="goal",
            priority="high",
            strategy="parallel",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "planner.plan.created"
        assert dto.aggregate_id == str(event.plan_id)
        assert dto.payload is not None

    def test_plan_approved_event(self, mapper: PlannerOutboxMapperImpl) -> None:
        event = PlanApproved(plan_id=PlanId(), occurred_at=NOW)
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "planner.plan.approved"
        assert dto.payload is None

    def test_plan_ready_event(self, mapper: PlannerOutboxMapperImpl) -> None:
        event = PlanReady(plan_id=PlanId(), occurred_at=NOW)
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "planner.plan.ready"

    def test_plan_execution_started_event(self, mapper: PlannerOutboxMapperImpl) -> None:
        event = PlanExecutionStarted(plan_id=PlanId(), occurred_at=NOW)
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "planner.plan.execution_started"

    def test_plan_completed_event(self, mapper: PlannerOutboxMapperImpl) -> None:
        event = PlanCompleted(plan_id=PlanId(), occurred_at=NOW)
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "planner.plan.completed"

    def test_plan_failed_event(self, mapper: PlannerOutboxMapperImpl) -> None:
        event = PlanFailed(
            plan_id=PlanId(), failure_reason="error", occurred_at=NOW
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "planner.plan.failed"
        assert dto.payload is not None

    def test_plan_cancelled_event(self, mapper: PlannerOutboxMapperImpl) -> None:
        event = PlanCancelled(plan_id=PlanId(), occurred_at=NOW)
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "planner.plan.cancelled"

    def test_task_created_event(self, mapper: PlannerOutboxMapperImpl) -> None:
        event = TaskCreated(
            task_id=TaskId(), description="task desc", occurred_at=NOW
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "planner.task.created"
        assert dto.payload is not None

    def test_task_assigned_event(self, mapper: PlannerOutboxMapperImpl) -> None:
        event = TaskAssigned(
            task_id=TaskId(),
            assigned_agent=AgentType.RESEARCH,
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "planner.task.assigned"
        assert dto.payload is not None

    def test_task_completed_event(self, mapper: PlannerOutboxMapperImpl) -> None:
        event = TaskCompleted(task_id=TaskId(), occurred_at=NOW)
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "planner.task.completed"

    def test_task_failed_event(self, mapper: PlannerOutboxMapperImpl) -> None:
        event = TaskFailed(
            task_id=TaskId(), failure_reason="err", occurred_at=NOW
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "planner.task.failed"
        assert dto.payload is not None

    def test_all_events_have_mapping(
        self, mapper: PlannerOutboxMapperImpl
    ) -> None:
        events: list = [
            PlanCreated(PlanId(), "R", "G", "normal", "sequential", NOW),
            PlanApproved(PlanId(), NOW),
            PlanReady(PlanId(), NOW),
            PlanExecutionStarted(PlanId(), NOW),
            PlanCompleted(PlanId(), NOW),
            PlanFailed(PlanId(), "err", NOW),
            PlanCancelled(PlanId(), NOW),
            TaskCreated(TaskId(), "desc", NOW),
            TaskAssigned(TaskId(), AgentType.PLANNER, NOW),
            TaskCompleted(TaskId(), NOW),
            TaskFailed(TaskId(), "err", NOW),
        ]
        for event in events:
            dto = mapper.event_to_dto(event)
            reconstructed = mapper.dto_to_event(dto)
            assert type(reconstructed) is type(event)

    def test_roundtrip_plan_created(
        self, mapper: PlannerOutboxMapperImpl
    ) -> None:
        original = PlanCreated(
            plan_id=PlanId(),
            user_request="req",
            goal="g",
            priority="critical",
            strategy="hybrid",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, PlanCreated)
        assert str(reconstructed.plan_id) == str(original.plan_id)
        assert reconstructed.user_request == "req"

    def test_roundtrip_task_failed(
        self, mapper: PlannerOutboxMapperImpl
    ) -> None:
        original = TaskFailed(
            task_id=TaskId(), failure_reason="timeout", occurred_at=NOW
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, TaskFailed)
        assert reconstructed.failure_reason == "timeout"

    def test_roundtrip_task_assigned(
        self, mapper: PlannerOutboxMapperImpl
    ) -> None:
        original = TaskAssigned(
            task_id=TaskId(),
            assigned_agent=AgentType.AUTOMATION,
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, TaskAssigned)
        assert reconstructed.assigned_agent == AgentType.AUTOMATION

    def test_dto_to_event_unknown_type(
        self, mapper: PlannerOutboxMapperImpl
    ) -> None:
        from backend.planner.application.persistence.dto import (
            PlannerOutboxStorageDTO,
        )

        dto = PlannerOutboxStorageDTO(
            event_id="id-1",
            event_type="unknown.type",
            aggregate_id="id-1",
            occurred_at=NOW,
        )
        with pytest.raises(ValueError, match="unknown.type"):
            mapper.dto_to_event(dto)

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, Union
from uuid import UUID, uuid4

import pytest

from backend.orchestrator.application.persistence.dto import (
    OrchestrationStorageDTO,
    OrchestratorOutboxStorageDTO,
    WorkflowStepStorageDTO,
    WorkflowStorageDTO,
)
from backend.orchestrator.application.persistence.mapper import (
    OrchestrationMapper,
    OrchestratorOutboxDomainEvent,
    OrchestratorOutboxMapper,
    WorkflowMapper,
    WorkflowStepMapper,
)
from backend.orchestrator.application.persistence.schema import (
    ORCHESTRATIONS_TABLE,
    ORCHESTRATOR_OUTBOX_TABLE,
    WORKFLOWS_TABLE,
    WORKFLOW_STEPS_TABLE,
    ColumnContract,
    TableContract,
)
from backend.orchestrator.domain.model import (
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

# ===================================================================
# Constants
# ===================================================================

_NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)
_NOW2 = datetime(2026, 6, 10, 13, 0, 0, tzinfo=timezone.utc)

# ===================================================================
# Stub mapper implementations
# ===================================================================


class StubOrchestrationMapper:
    def domain_to_dto(
        self, orchestration: Orchestration
    ) -> OrchestrationStorageDTO:
        return OrchestrationStorageDTO(
            orchestration_id=str(orchestration.orchestration_id),
            intent=str(orchestration.intent) if orchestration.intent else None,
            goal=str(orchestration.goal) if orchestration.goal else None,
            status=orchestration.status.value,
            created_at=orchestration.created_at,
            updated_at=orchestration.updated_at,
        )

    def dto_to_domain(
        self, dto: OrchestrationStorageDTO
    ) -> Orchestration:
        orchestration = Orchestration(
            orchestration_id=OrchestrationId(value=UUID(dto.orchestration_id)),
            intent=UserIntent(value=dto.intent) if dto.intent else None,
            goal=WorkflowGoal(value=dto.goal) if dto.goal else None,
            created_at=dto.created_at or _NOW,
            updated_at=dto.updated_at,
        )
        object.__setattr__(orchestration, "_status", OrchestrationStatus(dto.status))
        return orchestration


class StubWorkflowMapper:
    def domain_to_dto(self, workflow: Workflow) -> WorkflowStorageDTO:
        return WorkflowStorageDTO(
            workflow_id=str(workflow.workflow_id),
            goal=str(workflow.goal) if workflow.goal else None,
            mode=workflow.mode.value,
            status=workflow.status.value,
        )

    def dto_to_domain(self, dto: WorkflowStorageDTO) -> Workflow:
        workflow = Workflow(
            workflow_id=WorkflowId(value=UUID(dto.workflow_id)),
            goal=WorkflowGoal(value=dto.goal) if dto.goal else None,
            mode=ExecutionMode(dto.mode),
        )
        object.__setattr__(workflow, "_status", WorkflowStatus(dto.status))
        return workflow


class StubWorkflowStepMapper:
    def domain_to_dto(self, step: WorkflowStep) -> WorkflowStepStorageDTO:
        return WorkflowStepStorageDTO(
            step_id=str(step.step_id),
            agent_role=step.agent_role.value,
            execution_order=int(step.execution_order),
            status=step.status.value,
            result=str(step.result) if step.result else None,
            failure_reason=str(step.failure_reason) if step.failure_reason else None,
        )

    def dto_to_domain(self, dto: WorkflowStepStorageDTO) -> WorkflowStep:
        step = WorkflowStep(
            step_id=WorkflowId(value=UUID(dto.step_id)),
            agent_role=AgentRole(dto.agent_role),
            execution_order=ExecutionOrder(value=dto.execution_order),
        )
        object.__setattr__(step, "_status", WorkflowStepStatus(dto.status))
        if dto.result:
            object.__setattr__(step, "_result", ExecutionResult(value=dto.result))
        if dto.failure_reason:
            object.__setattr__(
                step, "_failure_reason", FailureReason(value=dto.failure_reason)
            )
        return step


class StubOrchestratorOutboxMapper:
    def event_to_dto(
        self, event: OrchestratorOutboxDomainEvent
    ) -> OrchestratorOutboxStorageDTO:
        event_type = _get_event_type(event)
        aggregate_id = _get_aggregate_id(event)
        return OrchestratorOutboxStorageDTO(
            event_id=str(event.event_id),
            event_type=event_type,
            aggregate_id=aggregate_id,
            occurred_at=event.occurred_at,
            payload="",
        )

    def dto_to_event(
        self, dto: OrchestratorOutboxStorageDTO
    ) -> OrchestratorOutboxDomainEvent:
        if dto.event_type == "orchestration.created":
            return OrchestrationCreated(
                orchestration_id=OrchestrationId(value=UUID(dto.aggregate_id)),
                intent="i", goal="g", occurred_at=dto.occurred_at,
            )
        if dto.event_type == "orchestration.planning_started":
            return OrchestrationPlanningStarted(
                orchestration_id=OrchestrationId(value=UUID(dto.aggregate_id)),
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "orchestration.research_started":
            return OrchestrationResearchStarted(
                orchestration_id=OrchestrationId(value=UUID(dto.aggregate_id)),
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "orchestration.execution_started":
            return OrchestrationExecutionStarted(
                orchestration_id=OrchestrationId(value=UUID(dto.aggregate_id)),
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "orchestration.completed":
            return OrchestrationCompleted(
                orchestration_id=OrchestrationId(value=UUID(dto.aggregate_id)),
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "orchestration.failed":
            return OrchestrationFailed(
                orchestration_id=OrchestrationId(value=UUID(dto.aggregate_id)),
                failure_reason="err", occurred_at=dto.occurred_at,
            )
        if dto.event_type == "orchestration.cancelled":
            return OrchestrationCancelled(
                orchestration_id=OrchestrationId(value=UUID(dto.aggregate_id)),
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "workflow.created":
            return WorkflowCreated(
                workflow_id=WorkflowId(value=UUID(dto.aggregate_id)),
                orchestration_id=OrchestrationId(), goal="g", mode="seq",
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "workflow.completed":
            return WorkflowCompleted(
                workflow_id=WorkflowId(value=UUID(dto.aggregate_id)),
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "workflow.failed":
            return WorkflowFailed(
                workflow_id=WorkflowId(value=UUID(dto.aggregate_id)),
                failure_reason="err", occurred_at=dto.occurred_at,
            )
        if dto.event_type == "workflow.step_started":
            return WorkflowStepStarted(
                step_id=WorkflowId(value=UUID(dto.aggregate_id)),
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "workflow.step_completed":
            return WorkflowStepCompleted(
                step_id=WorkflowId(value=UUID(dto.aggregate_id)),
                result="ok", occurred_at=dto.occurred_at,
            )
        if dto.event_type == "workflow.step_failed":
            return WorkflowStepFailed(
                step_id=WorkflowId(value=UUID(dto.aggregate_id)),
                failure_reason="err", occurred_at=dto.occurred_at,
            )
        msg = f"Unknown event type: {dto.event_type}"
        raise ValueError(msg)


def _get_event_type(event: OrchestratorOutboxDomainEvent) -> str:
    mapping = {
        OrchestrationCreated: "orchestration.created",
        OrchestrationPlanningStarted: "orchestration.planning_started",
        OrchestrationResearchStarted: "orchestration.research_started",
        OrchestrationExecutionStarted: "orchestration.execution_started",
        OrchestrationCompleted: "orchestration.completed",
        OrchestrationFailed: "orchestration.failed",
        OrchestrationCancelled: "orchestration.cancelled",
        WorkflowCreated: "workflow.created",
        WorkflowCompleted: "workflow.completed",
        WorkflowFailed: "workflow.failed",
        WorkflowStepStarted: "workflow.step_started",
        WorkflowStepCompleted: "workflow.step_completed",
        WorkflowStepFailed: "workflow.step_failed",
    }
    for cls, name in mapping.items():
        if isinstance(event, cls):
            return name
    msg = f"Unknown event type: {type(event).__name__}"
    raise ValueError(msg)


def _get_aggregate_id(event: OrchestratorOutboxDomainEvent) -> str:
    if isinstance(event, (OrchestrationCreated, OrchestrationPlanningStarted,
                          OrchestrationResearchStarted, OrchestrationExecutionStarted,
                          OrchestrationCompleted, OrchestrationFailed,
                          OrchestrationCancelled)):
        return str(event.orchestration_id)
    if isinstance(event, (WorkflowCreated, WorkflowCompleted, WorkflowFailed)):
        return str(event.workflow_id)
    if isinstance(event, (WorkflowStepStarted, WorkflowStepCompleted, WorkflowStepFailed)):
        return str(event.step_id)
    msg = f"Unknown event type: {type(event).__name__}"
    raise ValueError(msg)


# ===================================================================
# DTO: OrchestrationStorageDTO
# ===================================================================


class TestOrchestrationStorageDTO:
    def test_creation_with_all_fields(self) -> None:
        dto = OrchestrationStorageDTO(
            orchestration_id="orch-1",
            intent="test intent",
            goal="test goal",
            status="planning",
            created_at=_NOW,
            updated_at=_NOW2,
        )
        assert dto.orchestration_id == "orch-1"
        assert dto.intent == "test intent"
        assert dto.goal == "test goal"
        assert dto.status == "planning"
        assert dto.created_at == _NOW
        assert dto.updated_at == _NOW2

    def test_creation_with_defaults(self) -> None:
        dto = OrchestrationStorageDTO(orchestration_id="orch-1")
        assert dto.status == "created"
        assert dto.intent is None
        assert dto.goal is None
        assert dto.created_at is None
        assert dto.updated_at is None

    def test_immutability(self) -> None:
        dto = OrchestrationStorageDTO(orchestration_id="orch-1")
        with pytest.raises(AttributeError):
            dto.orchestration_id = "changed"  # type: ignore[misc]

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(OrchestrationStorageDTO)
        assert len(fields) == 6

    def test_nullable_fields(self) -> None:
        dto = OrchestrationStorageDTO(orchestration_id="orch-1")
        nullable = {"intent", "goal", "created_at", "updated_at"}
        for field_name in nullable:
            assert getattr(dto, field_name) is None

    def test_non_nullable_fields(self) -> None:
        dto = OrchestrationStorageDTO(orchestration_id="orch-1")
        assert dto.orchestration_id == "orch-1"
        assert dto.status == "created"

    def test_orchestration_id_type(self) -> None:
        dto = OrchestrationStorageDTO(orchestration_id="orch-1")
        assert isinstance(dto.orchestration_id, str)

    def test_status_type(self) -> None:
        dto = OrchestrationStorageDTO(orchestration_id="orch-1")
        assert isinstance(dto.status, str)


# ===================================================================
# DTO: WorkflowStorageDTO
# ===================================================================


class TestWorkflowStorageDTO:
    def test_creation_with_all_fields(self) -> None:
        dto = WorkflowStorageDTO(
            workflow_id="wf-1",
            orchestration_id="orch-1",
            goal="sub goal",
            mode="parallel",
            status="running",
        )
        assert dto.workflow_id == "wf-1"
        assert dto.orchestration_id == "orch-1"
        assert dto.goal == "sub goal"
        assert dto.mode == "parallel"
        assert dto.status == "running"

    def test_creation_with_defaults(self) -> None:
        dto = WorkflowStorageDTO(workflow_id="wf-1")
        assert dto.mode == "sequential"
        assert dto.status == "pending"
        assert dto.orchestration_id is None
        assert dto.goal is None

    def test_immutability(self) -> None:
        dto = WorkflowStorageDTO(workflow_id="wf-1")
        with pytest.raises(AttributeError):
            dto.workflow_id = "changed"  # type: ignore[misc]

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(WorkflowStorageDTO)
        assert len(fields) == 5

    def test_nullable_fields(self) -> None:
        dto = WorkflowStorageDTO(workflow_id="wf-1")
        nullable = {"orchestration_id", "goal"}
        for field_name in nullable:
            assert getattr(dto, field_name) is None

    def test_non_nullable_fields(self) -> None:
        dto = WorkflowStorageDTO(workflow_id="wf-1")
        assert dto.workflow_id == "wf-1"
        assert dto.mode == "sequential"
        assert dto.status == "pending"

    def test_workflow_id_type(self) -> None:
        dto = WorkflowStorageDTO(workflow_id="wf-1")
        assert isinstance(dto.workflow_id, str)

    def test_mode_type(self) -> None:
        dto = WorkflowStorageDTO(workflow_id="wf-1")
        assert isinstance(dto.mode, str)


# ===================================================================
# DTO: WorkflowStepStorageDTO
# ===================================================================


class TestWorkflowStepStorageDTO:
    def test_creation_with_all_fields(self) -> None:
        dto = WorkflowStepStorageDTO(
            step_id="step-1",
            workflow_id="wf-1",
            agent_role="memory",
            execution_order=2,
            status="completed",
            result="done",
            failure_reason=None,
        )
        assert dto.step_id == "step-1"
        assert dto.workflow_id == "wf-1"
        assert dto.agent_role == "memory"
        assert dto.execution_order == 2
        assert dto.status == "completed"
        assert dto.result == "done"
        assert dto.failure_reason is None

    def test_creation_with_defaults(self) -> None:
        dto = WorkflowStepStorageDTO(step_id="step-1")
        assert dto.agent_role == "research"
        assert dto.execution_order == 0
        assert dto.status == "pending"
        assert dto.workflow_id is None
        assert dto.result is None
        assert dto.failure_reason is None

    def test_immutability(self) -> None:
        dto = WorkflowStepStorageDTO(step_id="step-1")
        with pytest.raises(AttributeError):
            dto.step_id = "changed"  # type: ignore[misc]

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(WorkflowStepStorageDTO)
        assert len(fields) == 7

    def test_nullable_fields(self) -> None:
        dto = WorkflowStepStorageDTO(step_id="step-1")
        nullable = {"workflow_id", "result", "failure_reason"}
        for field_name in nullable:
            assert getattr(dto, field_name) is None

    def test_non_nullable_fields(self) -> None:
        dto = WorkflowStepStorageDTO(step_id="step-1")
        assert dto.step_id == "step-1"
        assert dto.agent_role == "research"
        assert dto.execution_order == 0
        assert dto.status == "pending"

    def test_step_id_type(self) -> None:
        dto = WorkflowStepStorageDTO(step_id="step-1")
        assert isinstance(dto.step_id, str)

    def test_execution_order_type(self) -> None:
        dto = WorkflowStepStorageDTO(step_id="step-1")
        assert isinstance(dto.execution_order, int)

    def test_result_stores_string(self) -> None:
        dto = WorkflowStepStorageDTO(
            step_id="step-1", result="completed successfully"
        )
        assert dto.result == "completed successfully"

    def test_failure_reason_stores_string(self) -> None:
        dto = WorkflowStepStorageDTO(
            step_id="step-1", failure_reason="something failed"
        )
        assert dto.failure_reason == "something failed"


# ===================================================================
# DTO: OrchestratorOutboxStorageDTO
# ===================================================================


class TestOrchestratorOutboxStorageDTO:
    def test_creation_with_all_fields(self) -> None:
        dto = OrchestratorOutboxStorageDTO(
            event_id="evt-1",
            event_type="orchestration.completed",
            aggregate_id="orch-1",
            occurred_at=_NOW,
            payload='{"key": "val"}',
            published=True,
        )
        assert dto.event_id == "evt-1"
        assert dto.event_type == "orchestration.completed"
        assert dto.aggregate_id == "orch-1"
        assert dto.occurred_at == _NOW
        assert dto.payload == '{"key": "val"}'
        assert dto.published is True

    def test_creation_with_defaults(self) -> None:
        dto = OrchestratorOutboxStorageDTO(
            event_id="evt-1",
            event_type="orchestration.created",
            aggregate_id="orch-1",
            occurred_at=_NOW,
        )
        assert dto.payload is None
        assert dto.published is False

    def test_immutability(self) -> None:
        dto = OrchestratorOutboxStorageDTO(
            event_id="evt-1",
            event_type="t",
            aggregate_id="a",
            occurred_at=_NOW,
        )
        with pytest.raises(AttributeError):
            dto.event_id = "changed"  # type: ignore[misc]

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(OrchestratorOutboxStorageDTO)
        assert len(fields) == 6

    def test_nullable_fields(self) -> None:
        dto = OrchestratorOutboxStorageDTO(
            event_id="evt-1",
            event_type="t",
            aggregate_id="a",
            occurred_at=_NOW,
        )
        assert dto.payload is None

    def test_non_nullable_fields(self) -> None:
        dto = OrchestratorOutboxStorageDTO(
            event_id="evt-1",
            event_type="t",
            aggregate_id="a",
            occurred_at=_NOW,
        )
        assert dto.event_id == "evt-1"
        assert dto.event_type == "t"
        assert dto.aggregate_id == "a"
        assert dto.occurred_at == _NOW
        assert dto.published is False

    def test_event_id_type(self) -> None:
        dto = OrchestratorOutboxStorageDTO(
            event_id="evt-1", event_type="t", aggregate_id="a",
            occurred_at=_NOW,
        )
        assert isinstance(dto.event_id, str)

    def test_published_type(self) -> None:
        dto = OrchestratorOutboxStorageDTO(
            event_id="evt-1", event_type="t", aggregate_id="a",
            occurred_at=_NOW, published=True,
        )
        assert isinstance(dto.published, bool)


# ===================================================================
# Mapper: OrchestrationMapper
# ===================================================================


class TestOrchestrationMapper:
    def test_domain_to_dto(self) -> None:
        orch = Orchestration(
            orchestration_id=OrchestrationId(),
            intent=UserIntent(value="test"),
            goal=WorkflowGoal(value="goal"),
            created_at=_NOW,
            updated_at=_NOW2,
        )
        mapper = StubOrchestrationMapper()
        dto = mapper.domain_to_dto(orch)
        assert dto.orchestration_id == str(orch.orchestration_id)
        assert dto.intent == "test"
        assert dto.goal == "goal"
        assert dto.status == "created"
        assert dto.created_at == _NOW
        assert dto.updated_at == _NOW2

    def test_domain_to_dto_with_nulls(self) -> None:
        orch = Orchestration(orchestration_id=OrchestrationId())
        mapper = StubOrchestrationMapper()
        dto = mapper.domain_to_dto(orch)
        assert dto.intent is None
        assert dto.goal is None
        assert dto.updated_at is None

    def test_dto_to_domain(self) -> None:
        dto = OrchestrationStorageDTO(
            orchestration_id=str(UUID(int=42)),
            intent="q",
            goal="g",
            status="researching",
            created_at=_NOW,
            updated_at=_NOW2,
        )
        mapper = StubOrchestrationMapper()
        orch = mapper.dto_to_domain(dto)
        assert str(orch.orchestration_id) == dto.orchestration_id
        assert orch.intent is not None
        assert orch.intent.value == "q"
        assert orch.goal is not None
        assert orch.goal.value == "g"
        assert orch.status == OrchestrationStatus.RESEARCHING
        assert orch.created_at == _NOW
        assert orch.updated_at == _NOW2

    def test_dto_to_domain_with_nulls(self) -> None:
        dto = OrchestrationStorageDTO(
            orchestration_id=str(UUID(int=1)),
        )
        mapper = StubOrchestrationMapper()
        orch = mapper.dto_to_domain(dto)
        assert orch.intent is None
        assert orch.goal is None
        assert orch.updated_at is None

    def test_roundtrip(self) -> None:
        original = Orchestration(
            orchestration_id=OrchestrationId(),
            intent=UserIntent(value="test"),
            goal=WorkflowGoal(value="goal"),
            created_at=_NOW,
            updated_at=_NOW2,
        )
        mapper = StubOrchestrationMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert str(restored.orchestration_id) == str(original.orchestration_id)
        assert restored.intent is not None
        assert restored.intent.value == original.intent.value
        assert restored.goal is not None
        assert restored.goal.value == original.goal.value

    def test_roundtrip_with_nulls(self) -> None:
        original = Orchestration(orchestration_id=OrchestrationId())
        mapper = StubOrchestrationMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert str(restored.orchestration_id) == str(original.orchestration_id)
        assert restored.intent is None
        assert restored.goal is None

    def test_roundtrip_preserves_status(self) -> None:
        original = Orchestration(orchestration_id=OrchestrationId())
        object.__setattr__(original, "_status", OrchestrationStatus.FAILED)
        mapper = StubOrchestrationMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert restored.status == OrchestrationStatus.FAILED

    def test_mapper_has_required_methods(self) -> None:
        mapper = StubOrchestrationMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


# ===================================================================
# Mapper: WorkflowMapper
# ===================================================================


class TestWorkflowMapper:
    def test_domain_to_dto(self) -> None:
        wf = Workflow(
            workflow_id=WorkflowId(),
            goal=WorkflowGoal(value="sub"),
            mode=ExecutionMode.PARALLEL,
        )
        object.__setattr__(wf, "_status", WorkflowStatus.RUNNING)
        mapper = StubWorkflowMapper()
        dto = mapper.domain_to_dto(wf)
        assert dto.workflow_id == str(wf.workflow_id)
        assert dto.goal == "sub"
        assert dto.mode == "parallel"
        assert dto.status == "running"

    def test_domain_to_dto_with_nulls(self) -> None:
        wf = Workflow(workflow_id=WorkflowId())
        mapper = StubWorkflowMapper()
        dto = mapper.domain_to_dto(wf)
        assert dto.goal is None
        assert dto.orchestration_id is None

    def test_dto_to_domain(self) -> None:
        dto = WorkflowStorageDTO(
            workflow_id=str(UUID(int=42)),
            orchestration_id=str(UUID(int=1)),
            goal="g",
            mode="hybrid",
            status="completed",
        )
        mapper = StubWorkflowMapper()
        wf = mapper.dto_to_domain(dto)
        assert str(wf.workflow_id) == dto.workflow_id
        assert wf.goal is not None
        assert wf.goal.value == "g"
        assert wf.mode == ExecutionMode.HYBRID
        assert wf.status == WorkflowStatus.COMPLETED

    def test_dto_to_domain_with_nulls(self) -> None:
        dto = WorkflowStorageDTO(workflow_id=str(UUID(int=1)))
        mapper = StubWorkflowMapper()
        wf = mapper.dto_to_domain(dto)
        assert wf.goal is None

    def test_roundtrip(self) -> None:
        original = Workflow(
            workflow_id=WorkflowId(),
            goal=WorkflowGoal(value="roundtrip"),
            mode=ExecutionMode.HYBRID,
        )
        mapper = StubWorkflowMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert str(restored.workflow_id) == str(original.workflow_id)
        assert restored.goal is not None
        assert restored.goal.value == original.goal.value
        assert restored.mode == original.mode

    def test_roundtrip_with_nulls(self) -> None:
        original = Workflow(workflow_id=WorkflowId())
        mapper = StubWorkflowMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert str(restored.workflow_id) == str(original.workflow_id)
        assert restored.goal is None

    def test_roundtrip_preserves_status(self) -> None:
        original = Workflow(workflow_id=WorkflowId())
        object.__setattr__(original, "_status", WorkflowStatus.FAILED)
        mapper = StubWorkflowMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert restored.status == WorkflowStatus.FAILED

    def test_mapper_has_required_methods(self) -> None:
        mapper = StubWorkflowMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


# ===================================================================
# Mapper: WorkflowStepMapper
# ===================================================================


class TestWorkflowStepMapper:
    def test_domain_to_dto(self) -> None:
        step = WorkflowStep(
            step_id=WorkflowId(),
            agent_role=AgentRole.AUTOMATION,
            execution_order=ExecutionOrder(value=3),
        )
        object.__setattr__(step, "_status", WorkflowStepStatus.COMPLETED)
        object.__setattr__(step, "_result", ExecutionResult(value="done"))
        mapper = StubWorkflowStepMapper()
        dto = mapper.domain_to_dto(step)
        assert dto.step_id == str(step.step_id)
        assert dto.agent_role == "automation"
        assert dto.execution_order == 3
        assert dto.status == "completed"
        assert dto.result == "done"
        assert dto.failure_reason is None

    def test_domain_to_dto_with_nulls(self) -> None:
        step = WorkflowStep(step_id=WorkflowId())
        mapper = StubWorkflowStepMapper()
        dto = mapper.domain_to_dto(step)
        assert dto.result is None
        assert dto.failure_reason is None
        assert dto.workflow_id is None

    def test_domain_to_dto_failed_step(self) -> None:
        step = WorkflowStep(step_id=WorkflowId())
        object.__setattr__(step, "_status", WorkflowStepStatus.FAILED)
        object.__setattr__(step, "_failure_reason", FailureReason(value="err"))
        mapper = StubWorkflowStepMapper()
        dto = mapper.domain_to_dto(step)
        assert dto.status == "failed"
        assert dto.failure_reason == "err"

    def test_dto_to_domain(self) -> None:
        dto = WorkflowStepStorageDTO(
            step_id=str(UUID(int=42)),
            workflow_id=str(UUID(int=1)),
            agent_role="planner",
            execution_order=5,
            status="running",
            result="in progress",
        )
        mapper = StubWorkflowStepMapper()
        step = mapper.dto_to_domain(dto)
        assert str(step.step_id) == dto.step_id
        assert step.agent_role == AgentRole.PLANNER
        assert int(step.execution_order) == 5
        assert step.status == WorkflowStepStatus.RUNNING
        assert step.result is not None
        assert step.result.value == "in progress"

    def test_dto_to_domain_failed(self) -> None:
        dto = WorkflowStepStorageDTO(
            step_id=str(UUID(int=42)),
            agent_role="research",
            execution_order=1,
            status="failed",
            failure_reason="error occurred",
        )
        mapper = StubWorkflowStepMapper()
        step = mapper.dto_to_domain(dto)
        assert step.status == WorkflowStepStatus.FAILED
        assert step.failure_reason is not None
        assert step.failure_reason.value == "error occurred"

    def test_dto_to_domain_with_nulls(self) -> None:
        dto = WorkflowStepStorageDTO(
            step_id=str(UUID(int=1)),
        )
        mapper = StubWorkflowStepMapper()
        step = mapper.dto_to_domain(dto)
        assert step.result is None
        assert step.failure_reason is None

    def test_roundtrip(self) -> None:
        original = WorkflowStep(
            step_id=WorkflowId(),
            agent_role=AgentRole.KNOWLEDGE,
            execution_order=ExecutionOrder(value=2),
        )
        object.__setattr__(original, "_status", WorkflowStepStatus.COMPLETED)
        object.__setattr__(original, "_result", ExecutionResult(value="ok"))
        mapper = StubWorkflowStepMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert str(restored.step_id) == str(original.step_id)
        assert restored.agent_role == original.agent_role
        assert int(restored.execution_order) == int(original.execution_order)
        assert restored.status == original.status
        assert restored.result is not None
        assert restored.result.value == original.result.value

    def test_roundtrip_with_nulls(self) -> None:
        original = WorkflowStep(step_id=WorkflowId())
        mapper = StubWorkflowStepMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert str(restored.step_id) == str(original.step_id)
        assert restored.result is None
        assert restored.failure_reason is None

    def test_roundtrip_preserves_status(self) -> None:
        original = WorkflowStep(step_id=WorkflowId())
        object.__setattr__(original, "_status", WorkflowStepStatus.SKIPPED)
        mapper = StubWorkflowStepMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert restored.status == WorkflowStepStatus.SKIPPED

    def test_mapper_has_required_methods(self) -> None:
        mapper = StubWorkflowStepMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


# ===================================================================
# Mapper: OrchestratorOutboxMapper
# ===================================================================


class TestOrchestratorOutboxMapper:
    def test_event_to_dto_created(self) -> None:
        event = OrchestrationCreated(
            orchestration_id=OrchestrationId(),
            intent="i", goal="g", occurred_at=_NOW,
        )
        mapper = StubOrchestratorOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "orchestration.created"
        assert dto.aggregate_id == str(event.orchestration_id)
        assert dto.occurred_at == _NOW

    def test_event_to_dto_planning_started(self) -> None:
        event = OrchestrationPlanningStarted(
            orchestration_id=OrchestrationId(), occurred_at=_NOW,
        )
        mapper = StubOrchestratorOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "orchestration.planning_started"

    def test_event_to_dto_research_started(self) -> None:
        event = OrchestrationResearchStarted(
            orchestration_id=OrchestrationId(), occurred_at=_NOW,
        )
        mapper = StubOrchestratorOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "orchestration.research_started"

    def test_event_to_dto_execution_started(self) -> None:
        event = OrchestrationExecutionStarted(
            orchestration_id=OrchestrationId(), occurred_at=_NOW,
        )
        mapper = StubOrchestratorOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "orchestration.execution_started"

    def test_event_to_dto_completed(self) -> None:
        event = OrchestrationCompleted(
            orchestration_id=OrchestrationId(), occurred_at=_NOW,
        )
        mapper = StubOrchestratorOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "orchestration.completed"

    def test_event_to_dto_failed(self) -> None:
        event = OrchestrationFailed(
            orchestration_id=OrchestrationId(), failure_reason="err",
            occurred_at=_NOW,
        )
        mapper = StubOrchestratorOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "orchestration.failed"

    def test_event_to_dto_cancelled(self) -> None:
        event = OrchestrationCancelled(
            orchestration_id=OrchestrationId(), occurred_at=_NOW,
        )
        mapper = StubOrchestratorOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "orchestration.cancelled"

    def test_event_to_dto_workflow_created(self) -> None:
        event = WorkflowCreated(
            workflow_id=WorkflowId(), orchestration_id=OrchestrationId(),
            goal="g", mode="seq", occurred_at=_NOW,
        )
        mapper = StubOrchestratorOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "workflow.created"
        assert dto.aggregate_id == str(event.workflow_id)

    def test_event_to_dto_workflow_completed(self) -> None:
        event = WorkflowCompleted(
            workflow_id=WorkflowId(), occurred_at=_NOW,
        )
        mapper = StubOrchestratorOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "workflow.completed"

    def test_event_to_dto_workflow_failed(self) -> None:
        event = WorkflowFailed(
            workflow_id=WorkflowId(), failure_reason="err",
            occurred_at=_NOW,
        )
        mapper = StubOrchestratorOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "workflow.failed"

    def test_event_to_dto_step_started(self) -> None:
        event = WorkflowStepStarted(
            step_id=WorkflowId(), occurred_at=_NOW,
        )
        mapper = StubOrchestratorOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "workflow.step_started"
        assert dto.aggregate_id == str(event.step_id)

    def test_event_to_dto_step_completed(self) -> None:
        event = WorkflowStepCompleted(
            step_id=WorkflowId(), result="ok", occurred_at=_NOW,
        )
        mapper = StubOrchestratorOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "workflow.step_completed"

    def test_event_to_dto_step_failed(self) -> None:
        event = WorkflowStepFailed(
            step_id=WorkflowId(), failure_reason="err",
            occurred_at=_NOW,
        )
        mapper = StubOrchestratorOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "workflow.step_failed"

    def test_dto_to_event_roundtrip_all_types(self) -> None:
        mapper = StubOrchestratorOutboxMapper()
        events: list[OrchestratorOutboxDomainEvent] = [
            OrchestrationCreated(
                orchestration_id=OrchestrationId(), intent="i", goal="g",
                occurred_at=_NOW,
            ),
            OrchestrationPlanningStarted(
                orchestration_id=OrchestrationId(), occurred_at=_NOW,
            ),
            OrchestrationResearchStarted(
                orchestration_id=OrchestrationId(), occurred_at=_NOW,
            ),
            OrchestrationExecutionStarted(
                orchestration_id=OrchestrationId(), occurred_at=_NOW,
            ),
            OrchestrationCompleted(
                orchestration_id=OrchestrationId(), occurred_at=_NOW,
            ),
            OrchestrationFailed(
                orchestration_id=OrchestrationId(), failure_reason="err",
                occurred_at=_NOW,
            ),
            OrchestrationCancelled(
                orchestration_id=OrchestrationId(), occurred_at=_NOW,
            ),
            WorkflowCreated(
                workflow_id=WorkflowId(), orchestration_id=OrchestrationId(),
                goal="g", mode="seq", occurred_at=_NOW,
            ),
            WorkflowCompleted(
                workflow_id=WorkflowId(), occurred_at=_NOW,
            ),
            WorkflowFailed(
                workflow_id=WorkflowId(), failure_reason="err",
                occurred_at=_NOW,
            ),
            WorkflowStepStarted(
                step_id=WorkflowId(), occurred_at=_NOW,
            ),
            WorkflowStepCompleted(
                step_id=WorkflowId(), result="ok", occurred_at=_NOW,
            ),
            WorkflowStepFailed(
                step_id=WorkflowId(), failure_reason="err",
                occurred_at=_NOW,
            ),
        ]
        for event in events:
            dto = mapper.event_to_dto(event)
            restored = mapper.dto_to_event(dto)
            assert type(restored) == type(event)

    def test_mapper_has_required_methods(self) -> None:
        mapper = StubOrchestratorOutboxMapper()
        assert hasattr(mapper, "event_to_dto")
        assert hasattr(mapper, "dto_to_event")


# ===================================================================
# Schema: ORCHESTRATIONS_TABLE
# ===================================================================


class TestOrchestrationsTable:
    def test_name(self) -> None:
        assert ORCHESTRATIONS_TABLE.name == "orchestrations"

    def test_schema(self) -> None:
        assert ORCHESTRATIONS_TABLE.schema == "orchestrator"

    def test_primary_key(self) -> None:
        assert ORCHESTRATIONS_TABLE.primary_key == "orchestration_id"

    def test_column_count(self) -> None:
        assert len(ORCHESTRATIONS_TABLE.columns) == 6

    def test_column_names(self) -> None:
        names = [c.name for c in ORCHESTRATIONS_TABLE.columns]
        assert names == [
            "orchestration_id", "intent", "goal", "status",
            "created_at", "updated_at",
        ]

    def test_status_enum_values(self) -> None:
        col = _find_column(ORCHESTRATIONS_TABLE, "status")
        assert col is not None
        assert col.enum_values == (
            "created", "planning", "researching", "executing",
            "completed", "failed", "cancelled",
        )

    def test_orchestration_id_not_nullable(self) -> None:
        col = _find_column(ORCHESTRATIONS_TABLE, "orchestration_id")
        assert col is not None
        assert col.nullable is False

    def test_status_not_nullable(self) -> None:
        col = _find_column(ORCHESTRATIONS_TABLE, "status")
        assert col is not None
        assert col.nullable is False

    def test_created_at_not_nullable(self) -> None:
        col = _find_column(ORCHESTRATIONS_TABLE, "created_at")
        assert col is not None
        assert col.nullable is False

    def test_nullable_columns(self) -> None:
        nullable = {"intent", "goal", "updated_at"}
        for name in nullable:
            col = _find_column(ORCHESTRATIONS_TABLE, name)
            assert col is not None
            assert col.nullable is True

    def test_indexes(self) -> None:
        assert "ix_orchestrations_status" in ORCHESTRATIONS_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(ORCHESTRATIONS_TABLE.indexes) == 1

    def test_status_max_length(self) -> None:
        col = _find_column(ORCHESTRATIONS_TABLE, "status")
        assert col is not None
        assert col.max_length == 16

    def test_orchestration_id_type(self) -> None:
        col = _find_column(ORCHESTRATIONS_TABLE, "orchestration_id")
        assert col is not None
        assert col.py_type == str

    def test_created_at_type(self) -> None:
        col = _find_column(ORCHESTRATIONS_TABLE, "created_at")
        assert col is not None
        assert col.py_type == datetime

    def test_updated_at_type(self) -> None:
        col = _find_column(ORCHESTRATIONS_TABLE, "updated_at")
        assert col is not None
        assert col.py_type == datetime

    def test_intent_type(self) -> None:
        col = _find_column(ORCHESTRATIONS_TABLE, "intent")
        assert col is not None
        assert col.py_type == str

    def test_goal_type(self) -> None:
        col = _find_column(ORCHESTRATIONS_TABLE, "goal")
        assert col is not None
        assert col.py_type == str


# ===================================================================
# Schema: WORKFLOWS_TABLE
# ===================================================================


class TestWorkflowsTable:
    def test_name(self) -> None:
        assert WORKFLOWS_TABLE.name == "workflows"

    def test_schema(self) -> None:
        assert WORKFLOWS_TABLE.schema == "orchestrator"

    def test_primary_key(self) -> None:
        assert WORKFLOWS_TABLE.primary_key == "workflow_id"

    def test_column_count(self) -> None:
        assert len(WORKFLOWS_TABLE.columns) == 5

    def test_column_names(self) -> None:
        names = [c.name for c in WORKFLOWS_TABLE.columns]
        assert names == [
            "workflow_id", "orchestration_id", "goal", "mode", "status",
        ]

    def test_status_enum_values(self) -> None:
        col = _find_column(WORKFLOWS_TABLE, "status")
        assert col is not None
        assert col.enum_values == (
            "pending", "running", "completed", "failed",
        )

    def test_mode_enum_values(self) -> None:
        col = _find_column(WORKFLOWS_TABLE, "mode")
        assert col is not None
        assert col.enum_values == (
            "sequential", "parallel", "hybrid",
        )

    def test_workflow_id_not_nullable(self) -> None:
        col = _find_column(WORKFLOWS_TABLE, "workflow_id")
        assert col is not None
        assert col.nullable is False

    def test_mode_not_nullable(self) -> None:
        col = _find_column(WORKFLOWS_TABLE, "mode")
        assert col is not None
        assert col.nullable is False

    def test_status_not_nullable(self) -> None:
        col = _find_column(WORKFLOWS_TABLE, "status")
        assert col is not None
        assert col.nullable is False

    def test_nullable_columns(self) -> None:
        nullable = {"orchestration_id", "goal"}
        for name in nullable:
            col = _find_column(WORKFLOWS_TABLE, name)
            assert col is not None
            assert col.nullable is True

    def test_indexes(self) -> None:
        assert "ix_workflows_orchestration_id" in WORKFLOWS_TABLE.indexes
        assert "ix_workflows_status" in WORKFLOWS_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(WORKFLOWS_TABLE.indexes) == 2

    def test_status_max_length(self) -> None:
        col = _find_column(WORKFLOWS_TABLE, "status")
        assert col is not None
        assert col.max_length == 16

    def test_mode_max_length(self) -> None:
        col = _find_column(WORKFLOWS_TABLE, "mode")
        assert col is not None
        assert col.max_length == 16

    def test_workflow_id_type(self) -> None:
        col = _find_column(WORKFLOWS_TABLE, "workflow_id")
        assert col is not None
        assert col.py_type == str

    def test_goal_type(self) -> None:
        col = _find_column(WORKFLOWS_TABLE, "goal")
        assert col is not None
        assert col.py_type == str


# ===================================================================
# Schema: WORKFLOW_STEPS_TABLE
# ===================================================================


class TestWorkflowStepsTable:
    def test_name(self) -> None:
        assert WORKFLOW_STEPS_TABLE.name == "workflow_steps"

    def test_schema(self) -> None:
        assert WORKFLOW_STEPS_TABLE.schema == "orchestrator"

    def test_primary_key(self) -> None:
        assert WORKFLOW_STEPS_TABLE.primary_key == "step_id"

    def test_column_count(self) -> None:
        assert len(WORKFLOW_STEPS_TABLE.columns) == 7

    def test_column_names(self) -> None:
        names = [c.name for c in WORKFLOW_STEPS_TABLE.columns]
        assert names == [
            "step_id", "workflow_id", "agent_role", "execution_order",
            "status", "result", "failure_reason",
        ]

    def test_status_enum_values(self) -> None:
        col = _find_column(WORKFLOW_STEPS_TABLE, "status")
        assert col is not None
        assert col.enum_values == (
            "pending", "running", "completed", "failed", "skipped",
        )

    def test_agent_role_enum_values(self) -> None:
        col = _find_column(WORKFLOW_STEPS_TABLE, "agent_role")
        assert col is not None
        assert col.enum_values == (
            "planner", "research", "automation", "memory",
            "knowledge", "policy",
        )

    def test_step_id_not_nullable(self) -> None:
        col = _find_column(WORKFLOW_STEPS_TABLE, "step_id")
        assert col is not None
        assert col.nullable is False

    def test_agent_role_not_nullable(self) -> None:
        col = _find_column(WORKFLOW_STEPS_TABLE, "agent_role")
        assert col is not None
        assert col.nullable is False

    def test_execution_order_not_nullable(self) -> None:
        col = _find_column(WORKFLOW_STEPS_TABLE, "execution_order")
        assert col is not None
        assert col.nullable is False

    def test_status_not_nullable(self) -> None:
        col = _find_column(WORKFLOW_STEPS_TABLE, "status")
        assert col is not None
        assert col.nullable is False

    def test_nullable_columns(self) -> None:
        nullable = {"workflow_id", "result", "failure_reason"}
        for name in nullable:
            col = _find_column(WORKFLOW_STEPS_TABLE, name)
            assert col is not None
            assert col.nullable is True

    def test_indexes(self) -> None:
        assert "ix_workflow_steps_workflow_id" in WORKFLOW_STEPS_TABLE.indexes
        assert "ix_workflow_steps_status" in WORKFLOW_STEPS_TABLE.indexes
        assert "ix_workflow_steps_agent_role" in WORKFLOW_STEPS_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(WORKFLOW_STEPS_TABLE.indexes) == 3

    def test_status_max_length(self) -> None:
        col = _find_column(WORKFLOW_STEPS_TABLE, "status")
        assert col is not None
        assert col.max_length == 16

    def test_agent_role_max_length(self) -> None:
        col = _find_column(WORKFLOW_STEPS_TABLE, "agent_role")
        assert col is not None
        assert col.max_length == 16

    def test_step_id_type(self) -> None:
        col = _find_column(WORKFLOW_STEPS_TABLE, "step_id")
        assert col is not None
        assert col.py_type == str

    def test_execution_order_type(self) -> None:
        col = _find_column(WORKFLOW_STEPS_TABLE, "execution_order")
        assert col is not None
        assert col.py_type == int

    def test_result_type(self) -> None:
        col = _find_column(WORKFLOW_STEPS_TABLE, "result")
        assert col is not None
        assert col.py_type == str

    def test_failure_reason_type(self) -> None:
        col = _find_column(WORKFLOW_STEPS_TABLE, "failure_reason")
        assert col is not None
        assert col.py_type == str


# ===================================================================
# Schema: ORCHESTRATOR_OUTBOX_TABLE
# ===================================================================


class TestOrchestratorOutboxTable:
    def test_name(self) -> None:
        assert ORCHESTRATOR_OUTBOX_TABLE.name == "outbox"

    def test_schema(self) -> None:
        assert ORCHESTRATOR_OUTBOX_TABLE.schema == "orchestrator"

    def test_primary_key(self) -> None:
        assert ORCHESTRATOR_OUTBOX_TABLE.primary_key == "event_id"

    def test_column_count(self) -> None:
        assert len(ORCHESTRATOR_OUTBOX_TABLE.columns) == 6

    def test_column_names(self) -> None:
        names = [c.name for c in ORCHESTRATOR_OUTBOX_TABLE.columns]
        assert names == [
            "event_id", "event_type", "aggregate_id", "occurred_at",
            "payload", "published",
        ]

    def test_event_type_enum_values(self) -> None:
        col = _find_column(ORCHESTRATOR_OUTBOX_TABLE, "event_type")
        assert col is not None
        assert col.enum_values == (
            "orchestration.created", "orchestration.planning_started",
            "orchestration.research_started", "orchestration.execution_started",
            "orchestration.completed", "orchestration.failed",
            "orchestration.cancelled", "workflow.created",
            "workflow.completed", "workflow.failed",
            "workflow.step_started", "workflow.step_completed",
            "workflow.step_failed",
        )

    def test_event_type_count(self) -> None:
        col = _find_column(ORCHESTRATOR_OUTBOX_TABLE, "event_type")
        assert col is not None
        assert len(col.enum_values) == 13

    def test_not_nullable_columns(self) -> None:
        for name in ("event_id", "event_type", "aggregate_id", "occurred_at", "published"):
            col = _find_column(ORCHESTRATOR_OUTBOX_TABLE, name)
            assert col is not None
            assert col.nullable is False

    def test_payload_nullable(self) -> None:
        col = _find_column(ORCHESTRATOR_OUTBOX_TABLE, "payload")
        assert col is not None
        assert col.nullable is True

    def test_indexes(self) -> None:
        assert "ix_orchestrator_outbox_unpublished" in ORCHESTRATOR_OUTBOX_TABLE.indexes
        assert "ix_orchestrator_outbox_aggregate" in ORCHESTRATOR_OUTBOX_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(ORCHESTRATOR_OUTBOX_TABLE.indexes) == 2

    def test_event_type_max_length(self) -> None:
        col = _find_column(ORCHESTRATOR_OUTBOX_TABLE, "event_type")
        assert col is not None
        assert col.max_length == 32

    def test_event_id_type(self) -> None:
        col = _find_column(ORCHESTRATOR_OUTBOX_TABLE, "event_id")
        assert col is not None
        assert col.py_type == str

    def test_published_type(self) -> None:
        col = _find_column(ORCHESTRATOR_OUTBOX_TABLE, "published")
        assert col is not None
        assert col.py_type == bool


# ===================================================================
# Alignment: DTO ↔ Schema
# ===================================================================


class TestDTOAlignment:
    def test_orchestration_dto_aligns_with_schema(self) -> None:
        dto_fields = _dto_field_names(OrchestrationStorageDTO)
        schema_fields = [c.name for c in ORCHESTRATIONS_TABLE.columns]
        assert dto_fields == schema_fields

    def test_workflow_dto_aligns_with_schema(self) -> None:
        dto_fields = _dto_field_names(WorkflowStorageDTO)
        schema_fields = [c.name for c in WORKFLOWS_TABLE.columns]
        assert dto_fields == schema_fields

    def test_step_dto_aligns_with_schema(self) -> None:
        dto_fields = _dto_field_names(WorkflowStepStorageDTO)
        schema_fields = [c.name for c in WORKFLOW_STEPS_TABLE.columns]
        assert dto_fields == schema_fields

    def test_outbox_dto_aligns_with_schema(self) -> None:
        dto_fields = _dto_field_names(OrchestratorOutboxStorageDTO)
        schema_fields = [c.name for c in ORCHESTRATOR_OUTBOX_TABLE.columns]
        assert dto_fields == schema_fields


# ===================================================================
# Alignment: Schema ↔ Domain Enums
# ===================================================================


class TestSchemaEnumAlignment:
    def test_status_enum_matches_orchestration_status(self) -> None:
        col = _find_column(ORCHESTRATIONS_TABLE, "status")
        assert col is not None
        expected = tuple(m.value for m in OrchestrationStatus)
        assert col.enum_values == expected

    def test_workflow_status_enum_matches_workflow_status(self) -> None:
        col = _find_column(WORKFLOWS_TABLE, "status")
        assert col is not None
        expected = tuple(m.value for m in WorkflowStatus)
        assert col.enum_values == expected

    def test_mode_enum_matches_execution_mode(self) -> None:
        col = _find_column(WORKFLOWS_TABLE, "mode")
        assert col is not None
        expected = tuple(m.value for m in ExecutionMode)
        assert col.enum_values == expected

    def test_step_status_enum_matches_workflow_step_status(self) -> None:
        col = _find_column(WORKFLOW_STEPS_TABLE, "status")
        assert col is not None
        expected = tuple(m.value for m in WorkflowStepStatus)
        assert col.enum_values == expected

    def test_agent_role_enum_matches_agent_role(self) -> None:
        col = _find_column(WORKFLOW_STEPS_TABLE, "agent_role")
        assert col is not None
        expected = tuple(m.value for m in AgentRole)
        assert col.enum_values == expected


# ===================================================================
# Alignment: Event type count
# ===================================================================


class TestEventTypeAlignment:
    def test_event_type_count_matches_domain_events(self) -> None:
        from backend.orchestrator.application.ports.outbox import (
            OrchestratorOutboxEvent,
        )
        import typing
        args = typing.get_args(OrchestratorOutboxEvent)
        col = _find_column(ORCHESTRATOR_OUTBOX_TABLE, "event_type")
        assert col is not None
        assert len(col.enum_values) == len(args)

    def test_event_type_values_cover_all_events(self) -> None:
        col = _find_column(ORCHESTRATOR_OUTBOX_TABLE, "event_type")
        assert col is not None
        assert "orchestration.created" in col.enum_values
        assert "orchestration.planning_started" in col.enum_values
        assert "orchestration.research_started" in col.enum_values
        assert "orchestration.execution_started" in col.enum_values
        assert "orchestration.completed" in col.enum_values
        assert "orchestration.failed" in col.enum_values
        assert "orchestration.cancelled" in col.enum_values
        assert "workflow.created" in col.enum_values
        assert "workflow.completed" in col.enum_values
        assert "workflow.failed" in col.enum_values
        assert "workflow.step_started" in col.enum_values
        assert "workflow.step_completed" in col.enum_values
        assert "workflow.step_failed" in col.enum_values


# ===================================================================
# Alignment: DTO ↔ Domain nullable parity
# ===================================================================


class TestDomainAlignment:
    def test_orchestration_dto_nullable_matches_domain_optionals(self) -> None:
        """DTO nullable fields correspond to domain optional constructor params."""
        dto = OrchestrationStorageDTO(orchestration_id="x")
        assert dto.intent is None
        assert dto.goal is None
        assert dto.updated_at is None
        orch = Orchestration(orchestration_id=OrchestrationId())
        assert orch.intent is None
        assert orch.goal is None
        assert orch.updated_at is None

    def test_workflow_dto_nullable_matches_domain_optionals(self) -> None:
        dto = WorkflowStorageDTO(workflow_id="x")
        assert dto.goal is None
        wf = Workflow(workflow_id=WorkflowId())
        assert wf.goal is None


# ===================================================================
# Helpers
# ===================================================================


def _find_column(
    table: TableContract, name: str
) -> ColumnContract | None:
    for col in table.columns:
        if col.name == name:
            return col
    return None


def _dto_field_names(dto_class: type) -> list[str]:
    import dataclasses
    return [f.name for f in dataclasses.fields(dto_class)]

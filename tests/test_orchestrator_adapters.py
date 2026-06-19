from __future__ import annotations

from datetime import datetime, timezone
from typing import Union
from uuid import UUID

import pytest

from backend.orchestrator.adapters.outbound.clock import SystemClockAdapter
from backend.orchestrator.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.orchestrator.adapters.outbound.mapper import (
    OrchestrationMapperImpl,
    OrchestratorOutboxMapperImpl,
    WorkflowMapperImpl,
    WorkflowStepMapperImpl,
)
from backend.orchestrator.application.persistence.mapper import (
    OrchestrationMapper,
    OrchestratorOutboxMapper,
    WorkflowMapper,
    WorkflowStepMapper,
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
    WorkflowStep,
    WorkflowStepCompleted,
    WorkflowStepFailed,
    WorkflowStepStarted,
    WorkflowStepStatus,
    WorkflowStatus,
)

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


def _make_orchestration(
    status: OrchestrationStatus = OrchestrationStatus.CREATED,
) -> Orchestration:
    return Orchestration(
        orchestration_id=OrchestrationId(
            value=UUID("00000000-0000-0000-0000-000000000001")
        ),
        intent=UserIntent(value="test intent"),
        goal=WorkflowGoal(value="test goal"),
        status=status,
        created_at=NOW,
        updated_at=NOW,
    )


def _make_workflow(
    status: WorkflowStatus = WorkflowStatus.PENDING,
) -> Workflow:
    w = Workflow(
        workflow_id=WorkflowId(
            value=UUID("00000000-0000-0000-0000-000000000010")
        ),
        goal=WorkflowGoal(value="test workflow goal"),
        mode=ExecutionMode.SEQUENTIAL,
    )
    object.__setattr__(w, "_status", status)
    return w


def _make_step(
    status: WorkflowStepStatus = WorkflowStepStatus.PENDING,
) -> WorkflowStep:
    return WorkflowStep(
        step_id=WorkflowId(
            value=UUID("00000000-0000-0000-0000-000000000020")
        ),
        agent_role=AgentRole.RESEARCH,
        execution_order=ExecutionOrder(value=1),
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
    def test_generate_orchestration_id(self) -> None:
        gen = UuidGeneratorAdapter()
        oid = gen.generate_orchestration_id()
        assert isinstance(oid, str)
        assert UUID(oid)

    def test_generate_workflow_id(self) -> None:
        gen = UuidGeneratorAdapter()
        wid = gen.generate_workflow_id()
        assert isinstance(wid, str)
        assert UUID(wid)

    def test_generate_step_id(self) -> None:
        gen = UuidGeneratorAdapter()
        sid = gen.generate_step_id()
        assert isinstance(sid, str)
        assert UUID(sid)

    def test_unique_ids(self) -> None:
        gen = UuidGeneratorAdapter()
        oids = {gen.generate_orchestration_id() for _ in range(50)}
        wids = {gen.generate_workflow_id() for _ in range(50)}
        sids = {gen.generate_step_id() for _ in range(50)}
        assert len(oids) == 50
        assert len(wids) == 50
        assert len(sids) == 50


# ===================================================================
# OrchestrationMapperImpl tests
# ===================================================================


class TestOrchestrationMapperImpl:
    @pytest.fixture
    def mapper(self) -> OrchestrationMapperImpl:
        return OrchestrationMapperImpl()

    def test_protocol_conformance(self) -> None:
        mapper: OrchestrationMapper = OrchestrationMapperImpl()
        assert isinstance(mapper, OrchestrationMapperImpl)

    def test_domain_to_dto(self, mapper: OrchestrationMapperImpl) -> None:
        orch = _make_orchestration()
        dto = mapper.domain_to_dto(orch)
        assert dto.orchestration_id == "00000000-0000-0000-0000-000000000001"
        assert dto.intent == "test intent"
        assert dto.goal == "test goal"
        assert dto.status == "created"

    def test_dto_to_domain(self, mapper: OrchestrationMapperImpl) -> None:
        orch = _make_orchestration()
        dto = mapper.domain_to_dto(orch)
        result = mapper.dto_to_domain(dto)
        assert str(result.orchestration_id) == "00000000-0000-0000-0000-000000000001"
        assert str(result.intent) == "test intent"
        assert result.status == OrchestrationStatus.CREATED

    def test_roundtrip(self, mapper: OrchestrationMapperImpl) -> None:
        original = _make_orchestration(status=OrchestrationStatus.PLANNING)
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.status == original.status

    def test_null_fields(self, mapper: OrchestrationMapperImpl) -> None:
        orch = Orchestration(
            orchestration_id=OrchestrationId(),
            created_at=NOW,
        )
        dto = mapper.domain_to_dto(orch)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.intent is None
        assert reconstructed.goal is None
        assert reconstructed.updated_at is None

    def test_failure_lifecycle(self, mapper: OrchestrationMapperImpl) -> None:
        original = _make_orchestration()
        original.start_planning()
        original.fail(FailureReason(value="test failure"))
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.status == OrchestrationStatus.FAILED
        assert reconstructed.intent is not None

    def test_dto_to_domain_with_all_fields(
        self, mapper: OrchestrationMapperImpl
    ) -> None:
        from backend.orchestrator.application.persistence.dto import (
            OrchestrationStorageDTO,
        )

        dto = OrchestrationStorageDTO(
            orchestration_id="00000000-0000-0000-0000-000000000001",
            intent="custom intent",
            goal="custom goal",
            status="completed",
            created_at=NOW,
            updated_at=NOW,
        )
        result = mapper.dto_to_domain(dto)
        assert str(result.intent) == "custom intent"
        assert result.status == OrchestrationStatus.COMPLETED

    def test_status_mapping_all_values(
        self, mapper: OrchestrationMapperImpl
    ) -> None:
        for status in OrchestrationStatus:
            original = _make_orchestration(status=status)
            dto = mapper.domain_to_dto(original)
            reconstructed = mapper.dto_to_domain(dto)
            assert reconstructed.status == status


# ===================================================================
# WorkflowMapperImpl tests
# ===================================================================


class TestWorkflowMapperImpl:
    @pytest.fixture
    def mapper(self) -> WorkflowMapperImpl:
        return WorkflowMapperImpl()

    def test_protocol_conformance(self) -> None:
        mapper: WorkflowMapper = WorkflowMapperImpl()
        assert isinstance(mapper, WorkflowMapperImpl)

    def test_domain_to_dto(self, mapper: WorkflowMapperImpl) -> None:
        wf = _make_workflow()
        dto = mapper.domain_to_dto(wf)
        assert dto.workflow_id == "00000000-0000-0000-0000-000000000010"
        assert dto.goal == "test workflow goal"
        assert dto.status == "pending"

    def test_dto_to_domain(self, mapper: WorkflowMapperImpl) -> None:
        wf = _make_workflow()
        dto = mapper.domain_to_dto(wf)
        result = mapper.dto_to_domain(dto)
        assert str(result.workflow_id) == "00000000-0000-0000-0000-000000000010"
        assert result.status == WorkflowStatus.PENDING

    def test_roundtrip(self, mapper: WorkflowMapperImpl) -> None:
        original = _make_workflow(status=WorkflowStatus.RUNNING)
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.status == original.status

    def test_null_goal(self, mapper: WorkflowMapperImpl) -> None:
        wf = Workflow(
            workflow_id=WorkflowId(),
        )
        dto = mapper.domain_to_dto(wf)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.goal is None

    def test_all_modes(self, mapper: WorkflowMapperImpl) -> None:
        for mode in ExecutionMode:
            wf = Workflow(
                workflow_id=WorkflowId(),
                goal=WorkflowGoal(value="test"),
                mode=mode,
            )
            dto = mapper.domain_to_dto(wf)
            reconstructed = mapper.dto_to_domain(dto)
            assert reconstructed.mode == mode

    def test_status_mapping_all_values(
        self, mapper: WorkflowMapperImpl
    ) -> None:
        for status in WorkflowStatus:
            original = _make_workflow(status=status)
            dto = mapper.domain_to_dto(original)
            reconstructed = mapper.dto_to_domain(dto)
            assert reconstructed.status == status


# ===================================================================
# WorkflowStepMapperImpl tests
# ===================================================================


class TestWorkflowStepMapperImpl:
    @pytest.fixture
    def mapper(self) -> WorkflowStepMapperImpl:
        return WorkflowStepMapperImpl()

    def test_protocol_conformance(self) -> None:
        mapper: WorkflowStepMapper = WorkflowStepMapperImpl()
        assert isinstance(mapper, WorkflowStepMapperImpl)

    def test_domain_to_dto(self, mapper: WorkflowStepMapperImpl) -> None:
        step = _make_step()
        dto = mapper.domain_to_dto(step)
        assert dto.step_id == "00000000-0000-0000-0000-000000000020"
        assert dto.agent_role == "research"
        assert dto.execution_order == 1
        assert dto.status == "pending"

    def test_dto_to_domain(self, mapper: WorkflowStepMapperImpl) -> None:
        step = _make_step()
        dto = mapper.domain_to_dto(step)
        result = mapper.dto_to_domain(dto)
        assert str(result.step_id) == "00000000-0000-0000-0000-000000000020"
        assert result.agent_role == AgentRole.RESEARCH
        assert int(result.execution_order) == 1
        assert result.status == WorkflowStepStatus.PENDING

    def test_roundtrip(self, mapper: WorkflowStepMapperImpl) -> None:
        original = _make_step(status=WorkflowStepStatus.RUNNING)
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.status == original.status

    def test_completed_step(self, mapper: WorkflowStepMapperImpl) -> None:
        original = _make_step()
        original.start()
        result = ExecutionResult(value="step completed")
        original.complete(result)
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.status == WorkflowStepStatus.COMPLETED
        assert str(reconstructed.result) == "step completed"

    def test_failed_step(self, mapper: WorkflowStepMapperImpl) -> None:
        original = _make_step()
        original.start()
        original.fail(FailureReason(value="step error"))
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.status == WorkflowStepStatus.FAILED
        assert str(reconstructed.failure_reason) == "step error"

    def test_null_fields(self, mapper: WorkflowStepMapperImpl) -> None:
        step = WorkflowStep(
            step_id=WorkflowId(),
        )
        dto = mapper.domain_to_dto(step)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.result is None
        assert reconstructed.failure_reason is None

    def test_all_agent_roles(self, mapper: WorkflowStepMapperImpl) -> None:
        for role in AgentRole:
            step = WorkflowStep(
                step_id=WorkflowId(),
                agent_role=role,
                execution_order=ExecutionOrder(value=0),
            )
            dto = mapper.domain_to_dto(step)
            reconstructed = mapper.dto_to_domain(dto)
            assert reconstructed.agent_role == role

    def test_all_statuses(self, mapper: WorkflowStepMapperImpl) -> None:
        for status in WorkflowStepStatus:
            step = _make_step(status=status)
            dto = mapper.domain_to_dto(step)
            reconstructed = mapper.dto_to_domain(dto)
            assert reconstructed.status == status

    def test_skipped_step(self, mapper: WorkflowStepMapperImpl) -> None:
        original = _make_step()
        original.skip()
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.status == WorkflowStepStatus.SKIPPED

    def test_dto_to_domain_with_all_fields(
        self, mapper: WorkflowStepMapperImpl
    ) -> None:
        from backend.orchestrator.application.persistence.dto import (
            WorkflowStepStorageDTO,
        )

        dto = WorkflowStepStorageDTO(
            step_id="00000000-0000-0000-0000-000000000030",
            workflow_id="wf-1",
            agent_role="automation",
            execution_order=5,
            status="completed",
            result="done",
            failure_reason=None,
        )
        result = mapper.dto_to_domain(dto)
        assert result.agent_role == AgentRole.AUTOMATION
        assert int(result.execution_order) == 5
        assert result.status == WorkflowStepStatus.COMPLETED
        assert str(result.result) == "done"


# ===================================================================
# OrchestratorOutboxMapperImpl tests
# ===================================================================


class TestOrchestratorOutboxMapperImpl:
    @pytest.fixture
    def mapper(self) -> OrchestratorOutboxMapperImpl:
        return OrchestratorOutboxMapperImpl()

    def test_protocol_conformance(self) -> None:
        mapper: OrchestratorOutboxMapper = OrchestratorOutboxMapperImpl()
        assert isinstance(mapper, OrchestratorOutboxMapperImpl)

    def test_orchestration_created_event(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        event = OrchestrationCreated(
            orchestration_id=OrchestrationId(),
            intent="test intent",
            goal="test goal",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "orchestration.created"
        assert dto.aggregate_id == str(event.orchestration_id)
        assert dto.payload is not None

    def test_orchestration_planning_started(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        event = OrchestrationPlanningStarted(
            orchestration_id=OrchestrationId(), occurred_at=NOW
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "orchestration.planning_started"
        assert dto.payload is None

    def test_orchestration_research_started(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        event = OrchestrationResearchStarted(
            orchestration_id=OrchestrationId(), occurred_at=NOW
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "orchestration.research_started"

    def test_orchestration_execution_started(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        event = OrchestrationExecutionStarted(
            orchestration_id=OrchestrationId(), occurred_at=NOW
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "orchestration.execution_started"

    def test_orchestration_completed(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        event = OrchestrationCompleted(
            orchestration_id=OrchestrationId(), occurred_at=NOW
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "orchestration.completed"

    def test_orchestration_failed(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        event = OrchestrationFailed(
            orchestration_id=OrchestrationId(),
            failure_reason="orchestration error",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "orchestration.failed"
        assert dto.payload is not None

    def test_orchestration_cancelled(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        event = OrchestrationCancelled(
            orchestration_id=OrchestrationId(), occurred_at=NOW
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "orchestration.cancelled"

    def test_workflow_created(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        event = WorkflowCreated(
            workflow_id=WorkflowId(),
            orchestration_id=OrchestrationId(),
            goal="test goal",
            mode="sequential",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "workflow.created"
        assert dto.payload is not None

    def test_workflow_completed(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        event = WorkflowCompleted(
            workflow_id=WorkflowId(), occurred_at=NOW
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "workflow.completed"

    def test_workflow_failed(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        event = WorkflowFailed(
            workflow_id=WorkflowId(),
            failure_reason="workflow error",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "workflow.failed"
        assert dto.payload is not None

    def test_workflow_step_started(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        event = WorkflowStepStarted(
            step_id=WorkflowId(), occurred_at=NOW
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "workflow.step_started"

    def test_workflow_step_completed(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        event = WorkflowStepCompleted(
            step_id=WorkflowId(), result="done", occurred_at=NOW
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "workflow.step_completed"
        assert dto.payload is not None

    def test_workflow_step_failed(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        event = WorkflowStepFailed(
            step_id=WorkflowId(),
            failure_reason="step error",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "workflow.step_failed"
        assert dto.payload is not None

    def test_all_events_have_mapping(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        oid = OrchestrationId()
        wid = WorkflowId()
        sid = WorkflowId()
        events: list = [
            OrchestrationCreated(oid, "intent", "goal", NOW),
            OrchestrationPlanningStarted(oid, NOW),
            OrchestrationResearchStarted(oid, NOW),
            OrchestrationExecutionStarted(oid, NOW),
            OrchestrationCompleted(oid, NOW),
            OrchestrationFailed(oid, "err", NOW),
            OrchestrationCancelled(oid, NOW),
            WorkflowCreated(wid, oid, "goal", "sequential", NOW),
            WorkflowCompleted(wid, NOW),
            WorkflowFailed(wid, "err", NOW),
            WorkflowStepStarted(sid, NOW),
            WorkflowStepCompleted(sid, "result", NOW),
            WorkflowStepFailed(sid, "err", NOW),
        ]
        for event in events:
            dto = mapper.event_to_dto(event)
            reconstructed = mapper.dto_to_event(dto)
            assert type(reconstructed) is type(event)

    def test_roundtrip_orchestration_created(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        original = OrchestrationCreated(
            orchestration_id=OrchestrationId(),
            intent="custom intent",
            goal="custom goal",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, OrchestrationCreated)
        assert str(reconstructed.orchestration_id) == str(
            original.orchestration_id
        )
        assert reconstructed.intent == "custom intent"
        assert reconstructed.goal == "custom goal"

    def test_roundtrip_orchestration_failed(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        original = OrchestrationFailed(
            orchestration_id=OrchestrationId(),
            failure_reason="critical error",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, OrchestrationFailed)
        assert reconstructed.failure_reason == "critical error"

    def test_roundtrip_workflow_created(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        original = WorkflowCreated(
            workflow_id=WorkflowId(),
            orchestration_id=OrchestrationId(),
            goal="wf goal",
            mode="parallel",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, WorkflowCreated)
        assert reconstructed.goal == "wf goal"
        assert reconstructed.mode == "parallel"

    def test_roundtrip_workflow_step_completed(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        original = WorkflowStepCompleted(
            step_id=WorkflowId(), result="task done", occurred_at=NOW
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, WorkflowStepCompleted)
        assert reconstructed.result == "task done"

    def test_roundtrip_workflow_step_failed(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        original = WorkflowStepFailed(
            step_id=WorkflowId(),
            failure_reason="step failure",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, WorkflowStepFailed)
        assert reconstructed.failure_reason == "step failure"

    def test_dto_to_event_unknown_type(
        self, mapper: OrchestratorOutboxMapperImpl
    ) -> None:
        from backend.orchestrator.application.persistence.dto import (
            OrchestratorOutboxStorageDTO,
        )

        dto = OrchestratorOutboxStorageDTO(
            event_id="id-1",
            event_type="unknown.type",
            aggregate_id="id-1",
            occurred_at=NOW,
        )
        with pytest.raises(ValueError, match="unknown.type"):
            mapper.dto_to_event(dto)

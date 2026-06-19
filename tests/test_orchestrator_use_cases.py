from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.orchestrator.application.use_cases.add_step import AddStepUseCase
from backend.orchestrator.application.use_cases.cancel_orchestration import (
    CancelOrchestrationUseCase,
)
from backend.orchestrator.application.use_cases.complete_orchestration import (
    CompleteOrchestrationUseCase,
)
from backend.orchestrator.application.use_cases.complete_step import CompleteStepUseCase
from backend.orchestrator.application.use_cases.complete_workflow import (
    CompleteWorkflowUseCase,
)
from backend.orchestrator.application.use_cases.create_orchestration import (
    CreateOrchestrationUseCase,
)
from backend.orchestrator.application.use_cases.create_workflow import (
    CreateWorkflowUseCase,
)
from backend.orchestrator.application.use_cases.dto import (
    AddStepRequest,
    CompleteStepRequest,
    CreateOrchestrationRequest,
    CreateWorkflowRequest,
    FailOrchestrationRequest,
    FailStepRequest,
    FailWorkflowRequest,
    GetOrchestrationRequest,
    GetStepRequest,
    GetWorkflowRequest,
    ListOrchestrationsRequest,
    ListWorkflowsRequest,
    OrchestrationLifecycleRequest,
    StepLifecycleRequest,
    WorkflowLifecycleRequest,
)
from backend.orchestrator.application.use_cases.exceptions import (
    OrchestrationNotFoundError,
    UseCaseError,
    WorkflowNotFoundError,
    WorkflowStepNotFoundError,
)
from backend.orchestrator.application.use_cases.fail_orchestration import (
    FailOrchestrationUseCase,
)
from backend.orchestrator.application.use_cases.fail_step import FailStepUseCase
from backend.orchestrator.application.use_cases.fail_workflow import (
    FailWorkflowUseCase,
)
from backend.orchestrator.application.use_cases.get_orchestration import (
    GetOrchestrationUseCase,
)
from backend.orchestrator.application.use_cases.get_step import GetStepUseCase
from backend.orchestrator.application.use_cases.get_workflow import GetWorkflowUseCase
from backend.orchestrator.application.use_cases.list_orchestrations import (
    ListOrchestrationsUseCase,
)
from backend.orchestrator.application.use_cases.list_workflows import (
    ListWorkflowsUseCase,
)
from backend.orchestrator.application.use_cases.start_execution import (
    StartExecutionUseCase,
)
from backend.orchestrator.application.use_cases.start_planning import (
    StartPlanningUseCase,
)
from backend.orchestrator.application.use_cases.start_research import (
    StartResearchUseCase,
)
from backend.orchestrator.application.use_cases.start_step import StartStepUseCase
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

# =========================================================================
# Stub repositories & ports
# =========================================================================


class StubOrchRepo:
    def __init__(self) -> None:
        self._store: dict[str, Orchestration] = {}

    def save(self, orch: Orchestration) -> None:
        self._store[str(orch.orchestration_id)] = orch

    def find_by_id(self, oid: OrchestrationId) -> Orchestration | None:
        return self._store.get(str(oid))

    def find_by_status(self, status: OrchestrationStatus) -> list[Orchestration]:
        return [o for o in self._store.values() if o.status == status]

    def find_all(self) -> list[Orchestration]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class StubWorkflowRepo:
    def __init__(self) -> None:
        self._store: dict[str, Workflow] = {}

    def save(self, wf: Workflow) -> None:
        self._store[str(wf.workflow_id)] = wf

    def find_by_id(self, wid: WorkflowId) -> Workflow | None:
        return self._store.get(str(wid))

    def find_by_status(self, status: WorkflowStatus) -> list[Workflow]:
        return [w for w in self._store.values() if w.status == status]

    def find_by_orchestration_id(
        self, oid: OrchestrationId
    ) -> list[Workflow]:
        return list(self._store.values())

    def find_all(self) -> list[Workflow]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class StubStepRepo:
    def __init__(self) -> None:
        self._store: dict[str, WorkflowStep] = {}

    def save(self, step: WorkflowStep) -> None:
        self._store[str(step.step_id)] = step

    def find_by_id(self, sid: WorkflowId) -> WorkflowStep | None:
        return self._store.get(str(sid))

    def find_by_status(self, status: WorkflowStepStatus) -> list[WorkflowStep]:
        return [s for s in self._store.values() if s.status == status]

    def find_by_workflow_id(self, wid: WorkflowId) -> list[WorkflowStep]:
        return list(self._store.values())

    def find_by_agent_role(self, role: AgentRole) -> list[WorkflowStep]:
        return [s for s in self._store.values() if s.agent_role == role]

    def count(self) -> int:
        return len(self._store)


class StubOutbox:
    def __init__(self) -> None:
        self.events: list[object] = []

    def append(self, event: object) -> None:
        self.events.append(event)

    def fetch_unpublished(self, limit: int = 100) -> list[object]:
        return list(self.events[:limit])

    def mark_published(self, aggregate_id: str) -> None:
        pass


# =========================================================================
# Fixtures
# =========================================================================

_NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def orch_repo() -> StubOrchRepo:
    return StubOrchRepo()


@pytest.fixture
def wf_repo() -> StubWorkflowRepo:
    return StubWorkflowRepo()


@pytest.fixture
def step_repo() -> StubStepRepo:
    return StubStepRepo()


@pytest.fixture
def outbox() -> StubOutbox:
    return StubOutbox()


# =========================================================================
# Helpers
# =========================================================================


def create_orch_entity(
    oid_str: str = "00000000-0000-0000-0000-000000000001",
    status: OrchestrationStatus = OrchestrationStatus.CREATED,
) -> Orchestration:
    from backend.orchestrator.domain.factory import OrchestratorFactory

    o, _ = OrchestratorFactory.create_orchestration(
        intent="test intent", goal="test goal",
    )
    object.__setattr__(o, "_orchestration_id", OrchestrationId(value=UUID(oid_str)))
    if status != OrchestrationStatus.CREATED:
        object.__setattr__(o, "_status", status)
    return o


def create_wf_entity(
    wf_id_str: str = "00000000-0000-0000-0000-000000000002",
) -> Workflow:
    wf = Workflow(
        workflow_id=WorkflowId(value=UUID(wf_id_str)),
        goal=WorkflowGoal(value="test workflow"),
        mode=ExecutionMode.SEQUENTIAL,
    )
    return wf


def create_step_entity(
    step_id: str = "00000000-0000-0000-0000-000000000003",
    status: WorkflowStepStatus = WorkflowStepStatus.PENDING,
) -> WorkflowStep:
    step = WorkflowStep(
        step_id=WorkflowId(value=UUID(step_id)),
        agent_role=AgentRole.RESEARCH,
        execution_order=ExecutionOrder(value=0),
        status=status,
    )
    return step


def create_startable_wf(
    wf_id_str: str = "00000000-0000-0000-0000-000000000002",
) -> Workflow:
    wf = Workflow(
        workflow_id=WorkflowId(value=UUID(wf_id_str)),
        goal=WorkflowGoal(value="test workflow"),
        mode=ExecutionMode.SEQUENTIAL,
    )
    step = WorkflowStep(
        agent_role=AgentRole.RESEARCH,
        execution_order=ExecutionOrder(value=0),
    )
    wf.add_step(step)
    return wf


# =========================================================================
# CreateOrchestrationUseCase
# =========================================================================


class TestCreateOrchestrationUseCase:
    def test_create(self, orch_repo: StubOrchRepo, outbox: StubOutbox) -> None:
        uc = CreateOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        req = CreateOrchestrationRequest(intent="Research AI", goal="Explore AI")
        resp = uc.execute(req)

        assert resp.intent == "Research AI"
        assert resp.goal == "Explore AI"
        assert resp.status == "created"
        assert resp.orchestration_id is not None
        assert resp.created_at is not None
        assert orch_repo.count() == 1

    def test_emits_orchestration_created(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        uc = CreateOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        uc.execute(CreateOrchestrationRequest(intent="i", goal="g"))

        assert len(outbox.events) == 1
        assert isinstance(outbox.events[0], OrchestrationCreated)

    def test_persists(self, orch_repo: StubOrchRepo, outbox: StubOutbox) -> None:
        uc = CreateOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        resp = uc.execute(CreateOrchestrationRequest(intent="i", goal="g"))

        found = orch_repo.find_by_id(
            OrchestrationId(value=UUID(resp.orchestration_id))
        )
        assert found is not None
        assert found.intent is not None
        assert found.intent.value == "i"


# =========================================================================
# StartPlanningUseCase
# =========================================================================


class TestStartPlanningUseCase:
    def test_start_planning(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity()
        orch_repo.save(entity)

        uc = StartPlanningUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        resp = uc.execute(
            OrchestrationLifecycleRequest(orchestration_id=str(entity.orchestration_id))
        )

        assert resp.status == "planning"

    def test_raises_if_not_found(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        uc = StartPlanningUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        with pytest.raises(OrchestrationNotFoundError):
            uc.execute(
                OrchestrationLifecycleRequest(
                    orchestration_id="00000000-0000-0000-0000-000000009999"
                )
            )

    def test_emits_planning_started(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity()
        orch_repo.save(entity)

        uc = StartPlanningUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        uc.execute(
            OrchestrationLifecycleRequest(orchestration_id=str(entity.orchestration_id))
        )

        assert any(isinstance(e, OrchestrationPlanningStarted) for e in outbox.events)


# =========================================================================
# StartResearchUseCase
# =========================================================================


class TestStartResearchUseCase:
    def test_start_research(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity(status=OrchestrationStatus.PLANNING)
        orch_repo.save(entity)

        uc = StartResearchUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        resp = uc.execute(
            OrchestrationLifecycleRequest(orchestration_id=str(entity.orchestration_id))
        )

        assert resp.status == "researching"

    def test_raises_if_not_found(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        uc = StartResearchUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        with pytest.raises(OrchestrationNotFoundError):
            uc.execute(
                OrchestrationLifecycleRequest(
                    orchestration_id="00000000-0000-0000-0000-000000009999"
                )
            )

    def test_emits_research_started(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity(status=OrchestrationStatus.PLANNING)
        orch_repo.save(entity)

        uc = StartResearchUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        uc.execute(
            OrchestrationLifecycleRequest(orchestration_id=str(entity.orchestration_id))
        )

        assert any(isinstance(e, OrchestrationResearchStarted) for e in outbox.events)


# =========================================================================
# StartExecutionUseCase
# =========================================================================


class TestStartExecutionUseCase:
    def test_start_execution(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity(status=OrchestrationStatus.RESEARCHING)
        orch_repo.save(entity)

        uc = StartExecutionUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        resp = uc.execute(
            OrchestrationLifecycleRequest(orchestration_id=str(entity.orchestration_id))
        )

        assert resp.status == "executing"

    def test_raises_if_not_found(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        uc = StartExecutionUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        with pytest.raises(OrchestrationNotFoundError):
            uc.execute(
                OrchestrationLifecycleRequest(
                    orchestration_id="00000000-0000-0000-0000-000000009999"
                )
            )

    def test_emits_execution_started(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity(status=OrchestrationStatus.RESEARCHING)
        orch_repo.save(entity)

        uc = StartExecutionUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        uc.execute(
            OrchestrationLifecycleRequest(orchestration_id=str(entity.orchestration_id))
        )

        assert any(isinstance(e, OrchestrationExecutionStarted) for e in outbox.events)


# =========================================================================
# CompleteOrchestrationUseCase
# =========================================================================


class TestCompleteOrchestrationUseCase:
    def test_complete(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity(status=OrchestrationStatus.EXECUTING)
        orch_repo.save(entity)

        uc = CompleteOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        resp = uc.execute(
            OrchestrationLifecycleRequest(orchestration_id=str(entity.orchestration_id))
        )

        assert resp.status == "completed"

    def test_raises_if_not_found(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        uc = CompleteOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        with pytest.raises(OrchestrationNotFoundError):
            uc.execute(
                OrchestrationLifecycleRequest(
                    orchestration_id="00000000-0000-0000-0000-000000009999"
                )
            )

    def test_emits_completed(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity(status=OrchestrationStatus.EXECUTING)
        orch_repo.save(entity)

        uc = CompleteOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        uc.execute(
            OrchestrationLifecycleRequest(orchestration_id=str(entity.orchestration_id))
        )

        assert any(isinstance(e, OrchestrationCompleted) for e in outbox.events)


# =========================================================================
# FailOrchestrationUseCase
# =========================================================================


class TestFailOrchestrationUseCase:
    def test_fail(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity(status=OrchestrationStatus.EXECUTING)
        orch_repo.save(entity)

        uc = FailOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        resp = uc.execute(
            FailOrchestrationRequest(
                orchestration_id=str(entity.orchestration_id),
                failure_reason="Error occurred",
            )
        )

        assert resp.status == "failed"
        assert resp.failure_reason == "Error occurred"

    def test_raises_if_not_found(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        uc = FailOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        with pytest.raises(OrchestrationNotFoundError):
            uc.execute(
                FailOrchestrationRequest(
                    orchestration_id="00000000-0000-0000-0000-000000009999",
                    failure_reason="err",
                )
            )

    def test_emits_failed(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity(status=OrchestrationStatus.EXECUTING)
        orch_repo.save(entity)

        uc = FailOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        uc.execute(
            FailOrchestrationRequest(
                orchestration_id=str(entity.orchestration_id),
                failure_reason="err",
            )
        )

        assert any(isinstance(e, OrchestrationFailed) for e in outbox.events)


# =========================================================================
# CancelOrchestrationUseCase
# =========================================================================


class TestCancelOrchestrationUseCase:
    def test_cancel(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity()
        orch_repo.save(entity)

        uc = CancelOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        resp = uc.execute(
            OrchestrationLifecycleRequest(orchestration_id=str(entity.orchestration_id))
        )

        assert resp.status == "cancelled"

    def test_raises_if_not_found(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        uc = CancelOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        with pytest.raises(OrchestrationNotFoundError):
            uc.execute(
                OrchestrationLifecycleRequest(
                    orchestration_id="00000000-0000-0000-0000-000000009999"
                )
            )

    def test_emits_cancelled(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity()
        orch_repo.save(entity)

        uc = CancelOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        uc.execute(
            OrchestrationLifecycleRequest(orchestration_id=str(entity.orchestration_id))
        )

        assert any(isinstance(e, OrchestrationCancelled) for e in outbox.events)


# =========================================================================
# CreateWorkflowUseCase
# =========================================================================


class TestCreateWorkflowUseCase:
    def test_create(
        self, orch_repo: StubOrchRepo, wf_repo: StubWorkflowRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity()
        orch_repo.save(entity)

        uc = CreateWorkflowUseCase(
            orchestration_repo=orch_repo,
            workflow_repo=wf_repo,
            outbox=outbox,
        )
        resp = uc.execute(
            CreateWorkflowRequest(
                orchestration_id=str(entity.orchestration_id),
                goal="sub goal",
                mode="parallel",
            )
        )

        assert resp.workflow_id is not None
        assert resp.goal == "sub goal"
        assert resp.mode == "parallel"
        assert resp.status == "pending"
        assert wf_repo.count() == 1

    def test_raises_if_orch_not_found(
        self, orch_repo: StubOrchRepo, wf_repo: StubWorkflowRepo, outbox: StubOutbox
    ) -> None:
        uc = CreateWorkflowUseCase(
            orchestration_repo=orch_repo,
            workflow_repo=wf_repo,
            outbox=outbox,
        )
        with pytest.raises(OrchestrationNotFoundError):
            uc.execute(
                CreateWorkflowRequest(
                    orchestration_id="00000000-0000-0000-0000-000000009999",
                    goal="g",
                )
            )

    def test_workflow_added_to_orch(
        self, orch_repo: StubOrchRepo, wf_repo: StubWorkflowRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity()
        orch_repo.save(entity)

        uc = CreateWorkflowUseCase(
            orchestration_repo=orch_repo,
            workflow_repo=wf_repo,
            outbox=outbox,
        )
        uc.execute(
            CreateWorkflowRequest(
                orchestration_id=str(entity.orchestration_id),
                goal="g",
            )
        )

        found = orch_repo.find_by_id(entity.orchestration_id)
        assert found is not None
        assert len(found.workflows) == 1

    def test_emits_workflow_created(
        self, orch_repo: StubOrchRepo, wf_repo: StubWorkflowRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity()
        orch_repo.save(entity)

        uc = CreateWorkflowUseCase(
            orchestration_repo=orch_repo,
            workflow_repo=wf_repo,
            outbox=outbox,
        )
        uc.execute(
            CreateWorkflowRequest(
                orchestration_id=str(entity.orchestration_id),
                goal="g",
            )
        )

        assert any(isinstance(e, WorkflowCreated) for e in outbox.events)


# =========================================================================
# CompleteWorkflowUseCase
# =========================================================================


class TestCompleteWorkflowUseCase:
    def test_complete(
        self, wf_repo: StubWorkflowRepo, outbox: StubOutbox
    ) -> None:
        entity = create_startable_wf()
        entity.start()
        wf_repo.save(entity)

        uc = CompleteWorkflowUseCase(workflow_repo=wf_repo, outbox=outbox)
        resp = uc.execute(
            WorkflowLifecycleRequest(workflow_id=str(entity.workflow_id))
        )

        assert resp.status == "completed"

    def test_raises_if_not_found(
        self, wf_repo: StubWorkflowRepo, outbox: StubOutbox
    ) -> None:
        uc = CompleteWorkflowUseCase(workflow_repo=wf_repo, outbox=outbox)
        with pytest.raises(WorkflowNotFoundError):
            uc.execute(
                WorkflowLifecycleRequest(
                    workflow_id="00000000-0000-0000-0000-000000009999"
                )
            )

    def test_emits_workflow_completed(
        self, wf_repo: StubWorkflowRepo, outbox: StubOutbox
    ) -> None:
        entity = create_startable_wf()
        entity.start()
        wf_repo.save(entity)

        uc = CompleteWorkflowUseCase(workflow_repo=wf_repo, outbox=outbox)
        uc.execute(
            WorkflowLifecycleRequest(workflow_id=str(entity.workflow_id))
        )

        assert any(isinstance(e, WorkflowCompleted) for e in outbox.events)


# =========================================================================
# FailWorkflowUseCase
# =========================================================================


class TestFailWorkflowUseCase:
    def test_fail(
        self, wf_repo: StubWorkflowRepo, outbox: StubOutbox
    ) -> None:
        entity = create_startable_wf()
        entity.start()
        wf_repo.save(entity)

        uc = FailWorkflowUseCase(workflow_repo=wf_repo, outbox=outbox)
        resp = uc.execute(
            FailWorkflowRequest(
                workflow_id=str(entity.workflow_id),
                failure_reason="Timeout",
            )
        )

        assert resp.status == "failed"
        assert resp.failure_reason == "Timeout"

    def test_raises_if_not_found(
        self, wf_repo: StubWorkflowRepo, outbox: StubOutbox
    ) -> None:
        uc = FailWorkflowUseCase(workflow_repo=wf_repo, outbox=outbox)
        with pytest.raises(WorkflowNotFoundError):
            uc.execute(
                FailWorkflowRequest(
                    workflow_id="00000000-0000-0000-0000-000000009999",
                    failure_reason="err",
                )
            )

    def test_emits_workflow_failed(
        self, wf_repo: StubWorkflowRepo, outbox: StubOutbox
    ) -> None:
        entity = create_startable_wf()
        entity.start()
        wf_repo.save(entity)

        uc = FailWorkflowUseCase(workflow_repo=wf_repo, outbox=outbox)
        uc.execute(
            FailWorkflowRequest(
                workflow_id=str(entity.workflow_id),
                failure_reason="err",
            )
        )

        assert any(isinstance(e, WorkflowFailed) for e in outbox.events)


# =========================================================================
# AddStepUseCase
# =========================================================================


class TestAddStepUseCase:
    def test_add_step(
        self, wf_repo: StubWorkflowRepo, step_repo: StubStepRepo
    ) -> None:
        wf_entity = create_wf_entity()
        wf_repo.save(wf_entity)

        uc = AddStepUseCase(workflow_repo=wf_repo, step_repo=step_repo)
        resp = uc.execute(
            AddStepRequest(
                workflow_id=str(wf_entity.workflow_id),
                agent_role="memory",
                execution_order=1,
            )
        )

        assert resp.step_id is not None
        assert resp.agent_role == "memory"
        assert resp.execution_order == 1
        assert resp.status == "pending"
        assert step_repo.count() == 1

    def test_raises_if_workflow_not_found(
        self, wf_repo: StubWorkflowRepo, step_repo: StubStepRepo
    ) -> None:
        uc = AddStepUseCase(workflow_repo=wf_repo, step_repo=step_repo)
        with pytest.raises(WorkflowNotFoundError):
            uc.execute(
                AddStepRequest(
                    workflow_id="00000000-0000-0000-0000-000000009999",
                )
            )

    def test_step_added_to_workflow(
        self, wf_repo: StubWorkflowRepo, step_repo: StubStepRepo
    ) -> None:
        wf_entity = create_wf_entity()
        wf_repo.save(wf_entity)

        uc = AddStepUseCase(workflow_repo=wf_repo, step_repo=step_repo)
        uc.execute(
            AddStepRequest(
                workflow_id=str(wf_entity.workflow_id),
                agent_role="research",
            )
        )

        found = wf_repo.find_by_id(wf_entity.workflow_id)
        assert found is not None
        assert len(found.steps) == 1


# =========================================================================
# StartStepUseCase
# =========================================================================


class TestStartStepUseCase:
    def test_start(
        self, step_repo: StubStepRepo, outbox: StubOutbox
    ) -> None:
        entity = create_step_entity()
        step_repo.save(entity)

        uc = StartStepUseCase(step_repo=step_repo, outbox=outbox)
        resp = uc.execute(
            StepLifecycleRequest(step_id=str(entity.step_id))
        )

        assert resp.status == "running"

    def test_raises_if_not_found(
        self, step_repo: StubStepRepo, outbox: StubOutbox
    ) -> None:
        uc = StartStepUseCase(step_repo=step_repo, outbox=outbox)
        with pytest.raises(WorkflowStepNotFoundError):
            uc.execute(
                StepLifecycleRequest(
                    step_id="00000000-0000-0000-0000-000000009999"
                )
            )

    def test_emits_step_started(
        self, step_repo: StubStepRepo, outbox: StubOutbox
    ) -> None:
        entity = create_step_entity()
        step_repo.save(entity)

        uc = StartStepUseCase(step_repo=step_repo, outbox=outbox)
        uc.execute(
            StepLifecycleRequest(step_id=str(entity.step_id))
        )

        assert any(isinstance(e, WorkflowStepStarted) for e in outbox.events)


# =========================================================================
# CompleteStepUseCase
# =========================================================================


class TestCompleteStepUseCase:
    def test_complete(
        self, step_repo: StubStepRepo, outbox: StubOutbox
    ) -> None:
        entity = create_step_entity(status=WorkflowStepStatus.RUNNING)
        step_repo.save(entity)

        uc = CompleteStepUseCase(step_repo=step_repo, outbox=outbox)
        resp = uc.execute(
            CompleteStepRequest(step_id=str(entity.step_id), result="Done")
        )

        assert resp.status == "completed"
        assert resp.result == "Done"

    def test_raises_if_not_found(
        self, step_repo: StubStepRepo, outbox: StubOutbox
    ) -> None:
        uc = CompleteStepUseCase(step_repo=step_repo, outbox=outbox)
        with pytest.raises(WorkflowStepNotFoundError):
            uc.execute(
                CompleteStepRequest(
                    step_id="00000000-0000-0000-0000-000000009999",
                    result="ok",
                )
            )

    def test_emits_step_completed(
        self, step_repo: StubStepRepo, outbox: StubOutbox
    ) -> None:
        entity = create_step_entity(status=WorkflowStepStatus.RUNNING)
        step_repo.save(entity)

        uc = CompleteStepUseCase(step_repo=step_repo, outbox=outbox)
        uc.execute(
            CompleteStepRequest(step_id=str(entity.step_id), result="ok")
        )

        assert any(isinstance(e, WorkflowStepCompleted) for e in outbox.events)


# =========================================================================
# FailStepUseCase
# =========================================================================


class TestFailStepUseCase:
    def test_fail(
        self, step_repo: StubStepRepo, outbox: StubOutbox
    ) -> None:
        entity = create_step_entity(status=WorkflowStepStatus.RUNNING)
        step_repo.save(entity)

        uc = FailStepUseCase(step_repo=step_repo, outbox=outbox)
        resp = uc.execute(
            FailStepRequest(step_id=str(entity.step_id), failure_reason="Error")
        )

        assert resp.status == "failed"
        assert resp.failure_reason == "Error"

    def test_raises_if_not_found(
        self, step_repo: StubStepRepo, outbox: StubOutbox
    ) -> None:
        uc = FailStepUseCase(step_repo=step_repo, outbox=outbox)
        with pytest.raises(WorkflowStepNotFoundError):
            uc.execute(
                FailStepRequest(
                    step_id="00000000-0000-0000-0000-000000009999",
                    failure_reason="err",
                )
            )

    def test_emits_step_failed(
        self, step_repo: StubStepRepo, outbox: StubOutbox
    ) -> None:
        entity = create_step_entity(status=WorkflowStepStatus.RUNNING)
        step_repo.save(entity)

        uc = FailStepUseCase(step_repo=step_repo, outbox=outbox)
        uc.execute(
            FailStepRequest(step_id=str(entity.step_id), failure_reason="err")
        )

        assert any(isinstance(e, WorkflowStepFailed) for e in outbox.events)


# =========================================================================
# GetOrchestrationUseCase
# =========================================================================


class TestGetOrchestrationUseCase:
    def test_get(
        self, orch_repo: StubOrchRepo
    ) -> None:
        entity = create_orch_entity()
        orch_repo.save(entity)

        uc = GetOrchestrationUseCase(orchestration_repo=orch_repo)
        resp = uc.execute(
            GetOrchestrationRequest(orchestration_id=str(entity.orchestration_id))
        )

        assert resp.orchestration_id == str(entity.orchestration_id)
        assert resp.intent == "test intent"
        assert resp.goal == "test goal"
        assert resp.status == "created"

    def test_raises_if_not_found(
        self, orch_repo: StubOrchRepo
    ) -> None:
        uc = GetOrchestrationUseCase(orchestration_repo=orch_repo)
        with pytest.raises(OrchestrationNotFoundError):
            uc.execute(
                GetOrchestrationRequest(
                    orchestration_id="00000000-0000-0000-0000-000000009999"
                )
            )

    def test_returns_workflow_count(
        self, orch_repo: StubOrchRepo
    ) -> None:
        entity = create_orch_entity()
        wf = create_wf_entity()
        entity.add_workflow(wf)
        orch_repo.save(entity)

        uc = GetOrchestrationUseCase(orchestration_repo=orch_repo)
        resp = uc.execute(
            GetOrchestrationRequest(orchestration_id=str(entity.orchestration_id))
        )

        assert resp.workflow_count == 1


# =========================================================================
# ListOrchestrationsUseCase
# =========================================================================


class TestListOrchestrationsUseCase:
    def test_list_by_status(
        self, orch_repo: StubOrchRepo
    ) -> None:
        o1 = create_orch_entity("00000000-0000-0000-0000-000000000001")
        o2 = create_orch_entity(
            "00000000-0000-0000-0000-000000000002",
            status=OrchestrationStatus.PLANNING,
        )
        orch_repo.save(o1)
        orch_repo.save(o2)

        uc = ListOrchestrationsUseCase(orchestration_repo=orch_repo)
        resp = uc.execute(ListOrchestrationsRequest(status="created"))

        assert resp.total == 1
        assert resp.orchestrations[0].orchestration_id == str(o1.orchestration_id)

    def test_returns_all_when_no_filter(
        self, orch_repo: StubOrchRepo
    ) -> None:
        o1 = create_orch_entity(oid_str="00000000-0000-0000-0000-000000000001")
        o2 = create_orch_entity(oid_str="00000000-0000-0000-0000-000000000002")
        orch_repo.save(o1)
        orch_repo.save(o2)

        uc = ListOrchestrationsUseCase(orchestration_repo=orch_repo)
        resp = uc.execute(ListOrchestrationsRequest())

        assert resp.total == 2

    def test_empty_when_no_match(
        self, orch_repo: StubOrchRepo
    ) -> None:
        o = create_orch_entity()
        orch_repo.save(o)

        uc = ListOrchestrationsUseCase(orchestration_repo=orch_repo)
        resp = uc.execute(ListOrchestrationsRequest(status="failed"))

        assert resp.total == 0


# =========================================================================
# GetWorkflowUseCase
# =========================================================================


class TestGetWorkflowUseCase:
    def test_get(
        self, wf_repo: StubWorkflowRepo
    ) -> None:
        entity = create_wf_entity()
        wf_repo.save(entity)

        uc = GetWorkflowUseCase(workflow_repo=wf_repo)
        resp = uc.execute(
            GetWorkflowRequest(workflow_id=str(entity.workflow_id))
        )

        assert resp.workflow_id == str(entity.workflow_id)
        assert resp.goal == "test workflow"
        assert resp.status == "pending"

    def test_raises_if_not_found(
        self, wf_repo: StubWorkflowRepo
    ) -> None:
        uc = GetWorkflowUseCase(workflow_repo=wf_repo)
        with pytest.raises(WorkflowNotFoundError):
            uc.execute(
                GetWorkflowRequest(
                    workflow_id="00000000-0000-0000-0000-000000009999"
                )
            )

    def test_returns_step_count(
        self, wf_repo: StubWorkflowRepo
    ) -> None:
        entity = create_wf_entity()
        step = create_step_entity()
        entity.add_step(step)
        wf_repo.save(entity)

        uc = GetWorkflowUseCase(workflow_repo=wf_repo)
        resp = uc.execute(
            GetWorkflowRequest(workflow_id=str(entity.workflow_id))
        )

        assert resp.step_count == 1


# =========================================================================
# ListWorkflowsUseCase
# =========================================================================


class TestListWorkflowsUseCase:
    def test_list_by_status(
        self, wf_repo: StubWorkflowRepo
    ) -> None:
        w1 = create_wf_entity("00000000-0000-0000-0000-000000000001")
        w2 = create_startable_wf("00000000-0000-0000-0000-000000000002")
        w2.start()
        wf_repo.save(w1)
        wf_repo.save(w2)

        uc = ListWorkflowsUseCase(workflow_repo=wf_repo)
        resp = uc.execute(ListWorkflowsRequest(status="pending"))

        assert resp.total == 1
        assert resp.workflows[0].workflow_id == str(w1.workflow_id)

    def test_list_by_orchestration_id(
        self, wf_repo: StubWorkflowRepo
    ) -> None:
        w1 = create_wf_entity("00000000-0000-0000-0000-000000000001")
        wf_repo.save(w1)

        uc = ListWorkflowsUseCase(workflow_repo=wf_repo)
        resp = uc.execute(
            ListWorkflowsRequest(
                orchestration_id="00000000-0000-0000-0000-000000000099"
            )
        )

        assert resp.total == 1

    def test_returns_all_when_no_filter(
        self, wf_repo: StubWorkflowRepo
    ) -> None:
        w1 = create_wf_entity(wf_id_str="00000000-0000-0000-0000-000000000002")
        w2 = create_wf_entity(wf_id_str="00000000-0000-0000-0000-000000000003")
        wf_repo.save(w1)
        wf_repo.save(w2)

        uc = ListWorkflowsUseCase(workflow_repo=wf_repo)
        resp = uc.execute(ListWorkflowsRequest())

        assert resp.total == 2

    def test_empty_when_no_match(
        self, wf_repo: StubWorkflowRepo
    ) -> None:
        w = create_wf_entity()
        wf_repo.save(w)

        uc = ListWorkflowsUseCase(workflow_repo=wf_repo)
        resp = uc.execute(ListWorkflowsRequest(status="failed"))

        assert resp.total == 0


# =========================================================================
# GetStepUseCase
# =========================================================================


class TestGetStepUseCase:
    def test_get(
        self, step_repo: StubStepRepo
    ) -> None:
        entity = create_step_entity(status=WorkflowStepStatus.RUNNING)
        step_repo.save(entity)

        uc = GetStepUseCase(step_repo=step_repo)
        resp = uc.execute(
            GetStepRequest(step_id=str(entity.step_id))
        )

        assert resp.step_id == str(entity.step_id)
        assert resp.agent_role == "research"
        assert resp.status == "running"

    def test_raises_if_not_found(
        self, step_repo: StubStepRepo
    ) -> None:
        uc = GetStepUseCase(step_repo=step_repo)
        with pytest.raises(WorkflowStepNotFoundError):
            uc.execute(
                GetStepRequest(
                    step_id="00000000-0000-0000-0000-000000009999"
                )
            )

    def test_returns_result_and_failure(
        self, step_repo: StubStepRepo
    ) -> None:
        entity = create_step_entity(
            status=WorkflowStepStatus.COMPLETED,
        )
        object.__setattr__(entity, "_result", ExecutionResult(value="done"))
        step_repo.save(entity)

        uc = GetStepUseCase(step_repo=step_repo)
        resp = uc.execute(
            GetStepRequest(step_id=str(entity.step_id))
        )

        assert resp.result == "done"
        assert resp.failure_reason is None


# =========================================================================
# Exception Hierarchy
# =========================================================================


class TestExceptionHierarchy:
    def test_orchestration_not_found_is_use_case_error(self) -> None:
        assert issubclass(OrchestrationNotFoundError, UseCaseError)

    def test_workflow_not_found_is_use_case_error(self) -> None:
        assert issubclass(WorkflowNotFoundError, UseCaseError)

    def test_step_not_found_is_use_case_error(self) -> None:
        assert issubclass(WorkflowStepNotFoundError, UseCaseError)


# =========================================================================
# Persistence verification
# =========================================================================


class TestOrchestrationPersistence:
    def test_start_planning_persists(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity()
        orch_repo.save(entity)

        uc = StartPlanningUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        uc.execute(
            OrchestrationLifecycleRequest(orchestration_id=str(entity.orchestration_id))
        )

        found = orch_repo.find_by_id(entity.orchestration_id)
        assert found is not None
        assert found.status == OrchestrationStatus.PLANNING

    def test_start_research_persists(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity(status=OrchestrationStatus.PLANNING)
        orch_repo.save(entity)

        uc = StartResearchUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        uc.execute(
            OrchestrationLifecycleRequest(orchestration_id=str(entity.orchestration_id))
        )

        found = orch_repo.find_by_id(entity.orchestration_id)
        assert found is not None
        assert found.status == OrchestrationStatus.RESEARCHING

    def test_start_execution_persists(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity(status=OrchestrationStatus.RESEARCHING)
        orch_repo.save(entity)

        uc = StartExecutionUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        uc.execute(
            OrchestrationLifecycleRequest(orchestration_id=str(entity.orchestration_id))
        )

        found = orch_repo.find_by_id(entity.orchestration_id)
        assert found is not None
        assert found.status == OrchestrationStatus.EXECUTING

    def test_complete_persists(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity(status=OrchestrationStatus.EXECUTING)
        orch_repo.save(entity)

        uc = CompleteOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        uc.execute(
            OrchestrationLifecycleRequest(orchestration_id=str(entity.orchestration_id))
        )

        found = orch_repo.find_by_id(entity.orchestration_id)
        assert found is not None
        assert found.status == OrchestrationStatus.COMPLETED

    def test_fail_persists(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity(status=OrchestrationStatus.EXECUTING)
        orch_repo.save(entity)

        uc = FailOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        uc.execute(
            FailOrchestrationRequest(
                orchestration_id=str(entity.orchestration_id),
                failure_reason="err",
            )
        )

        found = orch_repo.find_by_id(entity.orchestration_id)
        assert found is not None
        assert found.status == OrchestrationStatus.FAILED

    def test_cancel_persists(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity()
        orch_repo.save(entity)

        uc = CancelOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        uc.execute(
            OrchestrationLifecycleRequest(orchestration_id=str(entity.orchestration_id))
        )

        found = orch_repo.find_by_id(entity.orchestration_id)
        assert found is not None
        assert found.status == OrchestrationStatus.CANCELLED

    def test_create_workflow_persists_workflow(
        self, orch_repo: StubOrchRepo, wf_repo: StubWorkflowRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity()
        orch_repo.save(entity)

        uc = CreateWorkflowUseCase(
            orchestration_repo=orch_repo, workflow_repo=wf_repo, outbox=outbox,
        )
        resp = uc.execute(
            CreateWorkflowRequest(
                orchestration_id=str(entity.orchestration_id), goal="g",
            )
        )

        found = wf_repo.find_by_id(
            WorkflowId(value=UUID(resp.workflow_id))
        )
        assert found is not None
        assert found.goal is not None
        assert found.goal.value == "g"

    def test_complete_workflow_persists(
        self, wf_repo: StubWorkflowRepo, outbox: StubOutbox
    ) -> None:
        entity = create_startable_wf()
        entity.start()
        wf_repo.save(entity)

        uc = CompleteWorkflowUseCase(workflow_repo=wf_repo, outbox=outbox)
        uc.execute(
            WorkflowLifecycleRequest(workflow_id=str(entity.workflow_id))
        )

        found = wf_repo.find_by_id(entity.workflow_id)
        assert found is not None
        assert found.status == WorkflowStatus.COMPLETED

    def test_fail_workflow_persists(
        self, wf_repo: StubWorkflowRepo, outbox: StubOutbox
    ) -> None:
        entity = create_startable_wf()
        entity.start()
        wf_repo.save(entity)

        uc = FailWorkflowUseCase(workflow_repo=wf_repo, outbox=outbox)
        uc.execute(
            FailWorkflowRequest(
                workflow_id=str(entity.workflow_id), failure_reason="err",
            )
        )

        found = wf_repo.find_by_id(entity.workflow_id)
        assert found is not None
        assert found.status == WorkflowStatus.FAILED

    def test_start_step_persists(
        self, step_repo: StubStepRepo, outbox: StubOutbox
    ) -> None:
        entity = create_step_entity()
        step_repo.save(entity)

        uc = StartStepUseCase(step_repo=step_repo, outbox=outbox)
        uc.execute(
            StepLifecycleRequest(step_id=str(entity.step_id))
        )

        found = step_repo.find_by_id(entity.step_id)
        assert found is not None
        assert found.status == WorkflowStepStatus.RUNNING

    def test_complete_step_persists(
        self, step_repo: StubStepRepo, outbox: StubOutbox
    ) -> None:
        entity = create_step_entity(status=WorkflowStepStatus.RUNNING)
        step_repo.save(entity)

        uc = CompleteStepUseCase(step_repo=step_repo, outbox=outbox)
        uc.execute(
            CompleteStepRequest(step_id=str(entity.step_id), result="ok")
        )

        found = step_repo.find_by_id(entity.step_id)
        assert found is not None
        assert found.status == WorkflowStepStatus.COMPLETED

    def test_fail_step_persists(
        self, step_repo: StubStepRepo, outbox: StubOutbox
    ) -> None:
        entity = create_step_entity(status=WorkflowStepStatus.RUNNING)
        step_repo.save(entity)

        uc = FailStepUseCase(step_repo=step_repo, outbox=outbox)
        uc.execute(
            FailStepRequest(step_id=str(entity.step_id), failure_reason="err")
        )

        found = step_repo.find_by_id(entity.step_id)
        assert found is not None
        assert found.status == WorkflowStepStatus.FAILED


# =========================================================================
# Outbox event type verification
# =========================================================================


class TestOutboxEventTypes:
    def test_create_orchestration_event_type(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        uc = CreateOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        uc.execute(CreateOrchestrationRequest(intent="i", goal="g"))
        assert len(outbox.events) == 1
        assert type(outbox.events[0]).__name__ == "OrchestrationCreated"

    def test_start_planning_event_type(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity()
        orch_repo.save(entity)
        uc = StartPlanningUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        uc.execute(
            OrchestrationLifecycleRequest(orchestration_id=str(entity.orchestration_id))
        )
        assert type(outbox.events[0]).__name__ == "OrchestrationPlanningStarted"

    def test_cancel_event_type(
        self, orch_repo: StubOrchRepo, outbox: StubOutbox
    ) -> None:
        entity = create_orch_entity()
        orch_repo.save(entity)
        uc = CancelOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        uc.execute(
            OrchestrationLifecycleRequest(orchestration_id=str(entity.orchestration_id))
        )
        assert type(outbox.events[0]).__name__ == "OrchestrationCancelled"


# =========================================================================
# DTO correctness
# =========================================================================


class TestDTOCorrectness:
    def test_create_orchestration_response_fields(self) -> None:
        from backend.orchestrator.application.use_cases.dto import (
            CreateOrchestrationResponse,
        )
        resp = CreateOrchestrationResponse(
            orchestration_id="id", intent="i", goal="g",
            status="created", created_at=_NOW,
        )
        assert resp.orchestration_id == "id"
        assert resp.intent == "i"
        assert resp.goal == "g"
        assert resp.status == "created"
        assert resp.created_at == _NOW

    def test_fail_orchestration_response_fields(self) -> None:
        from backend.orchestrator.application.use_cases.dto import (
            FailOrchestrationResponse,
        )
        resp = FailOrchestrationResponse(
            orchestration_id="id", status="failed",
            failure_reason="err", updated_at=_NOW,
        )
        assert resp.failure_reason == "err"

    def test_complete_step_response_fields(self) -> None:
        from backend.orchestrator.application.use_cases.dto import (
            CompleteStepResponse,
        )
        resp = CompleteStepResponse(
            step_id="id", status="completed", result="done",
        )
        assert resp.result == "done"

    def test_list_orchestrations_response_defaults(self) -> None:
        from backend.orchestrator.application.use_cases.dto import (
            ListOrchestrationsResponse,
        )
        resp = ListOrchestrationsResponse()
        assert resp.orchestrations == []
        assert resp.total == 0

    def test_list_workflows_response_defaults(self) -> None:
        from backend.orchestrator.application.use_cases.dto import (
            ListWorkflowsResponse,
        )
        resp = ListWorkflowsResponse()
        assert resp.workflows == []
        assert resp.total == 0


# =========================================================================
# Edge cases
# =========================================================================


class TestEdgeCases:
    def test_list_orchestrations_empty_repo(
        self, orch_repo: StubOrchRepo
    ) -> None:
        uc = ListOrchestrationsUseCase(orchestration_repo=orch_repo)
        resp = uc.execute(ListOrchestrationsRequest(status="created"))
        assert resp.total == 0

    def test_list_workflows_empty_repo(
        self, wf_repo: StubWorkflowRepo
    ) -> None:
        uc = ListWorkflowsUseCase(workflow_repo=wf_repo)
        resp = uc.execute(ListWorkflowsRequest(status="running"))
        assert resp.total == 0

    def test_get_orchestration_response_includes_updated_at(
        self, orch_repo: StubOrchRepo
    ) -> None:
        entity = create_orch_entity()
        orch_repo.save(entity)
        uc = GetOrchestrationUseCase(orchestration_repo=orch_repo)
        resp = uc.execute(
            GetOrchestrationRequest(orchestration_id=str(entity.orchestration_id))
        )
        assert resp.updated_at is None

    def test_get_step_response_includes_failure_reason(
        self, step_repo: StubStepRepo
    ) -> None:
        entity = create_step_entity(status=WorkflowStepStatus.FAILED)
        object.__setattr__(
            entity, "_failure_reason", FailureReason(value="error")
        )
        step_repo.save(entity)
        uc = GetStepUseCase(step_repo=step_repo)
        resp = uc.execute(
            GetStepRequest(step_id=str(entity.step_id))
        )
        assert resp.failure_reason == "error"

    def test_workflow_step_response_result_and_failure(
        self, step_repo: StubStepRepo
    ) -> None:
        entity = create_step_entity(status=WorkflowStepStatus.COMPLETED)
        object.__setattr__(entity, "_result", ExecutionResult(value="done"))
        step_repo.save(entity)
        uc = GetStepUseCase(step_repo=step_repo)
        resp = uc.execute(
            GetStepRequest(step_id=str(entity.step_id))
        )
        assert resp.result == "done"
        assert resp.failure_reason is None


# =========================================================================
# Integration flows
# =========================================================================


class TestIntegrationFlows:
    def test_full_orchestration_lifecycle(
        self,
        orch_repo: StubOrchRepo,
        wf_repo: StubWorkflowRepo,
        step_repo: StubStepRepo,
        outbox: StubOutbox,
    ) -> None:
        create_uc = CreateOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        create_resp = create_uc.execute(
            CreateOrchestrationRequest(intent="Build AI", goal="Create agent")
        )

        start_p = StartPlanningUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        start_p.execute(
            OrchestrationLifecycleRequest(orchestration_id=create_resp.orchestration_id)
        )

        start_r = StartResearchUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        start_r.execute(
            OrchestrationLifecycleRequest(orchestration_id=create_resp.orchestration_id)
        )

        start_e = StartExecutionUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        start_e.execute(
            OrchestrationLifecycleRequest(orchestration_id=create_resp.orchestration_id)
        )

        complete = CompleteOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        complete_resp = complete.execute(
            OrchestrationLifecycleRequest(orchestration_id=create_resp.orchestration_id)
        )

        assert complete_resp.status == "completed"
        assert len(outbox.events) == 5

    def test_orchestration_with_workflow_and_step(
        self,
        orch_repo: StubOrchRepo,
        wf_repo: StubWorkflowRepo,
        step_repo: StubStepRepo,
        outbox: StubOutbox,
    ) -> None:
        create_uc = CreateOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        create_resp = create_uc.execute(
            CreateOrchestrationRequest(intent="Test", goal="Test flow")
        )

        create_wf = CreateWorkflowUseCase(
            orchestration_repo=orch_repo,
            workflow_repo=wf_repo,
            outbox=outbox,
        )
        wf_resp = create_wf.execute(
            CreateWorkflowRequest(
                orchestration_id=create_resp.orchestration_id,
                goal="sub task",
            )
        )

        add_step_uc = AddStepUseCase(
            workflow_repo=wf_repo, step_repo=step_repo,
        )
        step_resp = add_step_uc.execute(
            AddStepRequest(
                workflow_id=wf_resp.workflow_id,
                agent_role="research",
                execution_order=0,
            )
        )

        start_step = StartStepUseCase(step_repo=step_repo, outbox=outbox)
        start_step.execute(
            StepLifecycleRequest(step_id=step_resp.step_id)
        )

        complete_step = CompleteStepUseCase(step_repo=step_repo, outbox=outbox)
        complete_step.execute(
            CompleteStepRequest(step_id=step_resp.step_id, result="Done")
        )

        assert step_repo.count() == 1
        assert len(outbox.events) >= 3

    def test_orchestration_failure_lifecycle(
        self,
        orch_repo: StubOrchRepo,
        outbox: StubOutbox,
    ) -> None:
        create_uc = CreateOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        create_resp = create_uc.execute(
            CreateOrchestrationRequest(intent="Fail test", goal="Test failure")
        )

        start_p = StartPlanningUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        start_p.execute(
            OrchestrationLifecycleRequest(orchestration_id=create_resp.orchestration_id)
        )

        fail_uc = FailOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        fail_resp = fail_uc.execute(
            FailOrchestrationRequest(
                orchestration_id=create_resp.orchestration_id,
                failure_reason="Something broke",
            )
        )

        assert fail_resp.status == "failed"
        assert fail_resp.failure_reason == "Something broke"

    def test_orchestration_cancellation(
        self,
        orch_repo: StubOrchRepo,
        outbox: StubOutbox,
    ) -> None:
        create_uc = CreateOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        create_resp = create_uc.execute(
            CreateOrchestrationRequest(intent="Cancel test", goal="Test cancel")
        )

        cancel_uc = CancelOrchestrationUseCase(
            orchestration_repo=orch_repo, outbox=outbox,
        )
        cancel_resp = cancel_uc.execute(
            OrchestrationLifecycleRequest(
                orchestration_id=create_resp.orchestration_id
            )
        )

        assert cancel_resp.status == "cancelled"
        assert any(isinstance(e, OrchestrationCancelled) for e in outbox.events)

    def test_step_lifecycle(
        self,
        wf_repo: StubWorkflowRepo,
        step_repo: StubStepRepo,
        outbox: StubOutbox,
    ) -> None:
        wf_entity = create_wf_entity()
        wf_repo.save(wf_entity)

        add_step_uc = AddStepUseCase(
            workflow_repo=wf_repo, step_repo=step_repo,
        )
        step_resp = add_step_uc.execute(
            AddStepRequest(
                workflow_id=str(wf_entity.workflow_id),
                agent_role="automation",
                execution_order=0,
            )
        )

        start_step = StartStepUseCase(step_repo=step_repo, outbox=outbox)
        start_step.execute(
            StepLifecycleRequest(step_id=step_resp.step_id)
        )

        fail_step = FailStepUseCase(step_repo=step_repo, outbox=outbox)
        fail_resp = fail_step.execute(
            FailStepRequest(step_id=step_resp.step_id, failure_reason="Error")
        )

        assert fail_resp.status == "failed"
        assert any(isinstance(e, WorkflowStepFailed) for e in outbox.events)

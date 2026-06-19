from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator
from uuid import UUID

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.orchestrator.adapters.outbound.clock import SystemClockAdapter
from backend.orchestrator.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.orchestrator.adapters.outbound.mapper import (
    OrchestrationMapperImpl,
    OrchestratorOutboxMapperImpl,
    WorkflowMapperImpl,
    WorkflowStepMapperImpl,
)
from backend.orchestrator.adapters.outbound.models import Base
from backend.orchestrator.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyOrchestrationRepository,
    SqlAlchemyOrchestratorOutboxAdapter,
    SqlAlchemyWorkflowRepository,
    SqlAlchemyWorkflowStepRepository,
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


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def engine() -> Iterator[Engine]:
    e = create_engine("sqlite://", echo=False)
    for t in Base.metadata.tables.values():
        t.schema = None
    Base.metadata.create_all(bind=e)
    yield e
    e.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    S = sessionmaker(bind=engine)
    s = S()
    yield s
    s.close()


@pytest.fixture
def orch_mapper() -> OrchestrationMapperImpl:
    return OrchestrationMapperImpl()


@pytest.fixture
def wf_mapper() -> WorkflowMapperImpl:
    return WorkflowMapperImpl()


@pytest.fixture
def step_mapper() -> WorkflowStepMapperImpl:
    return WorkflowStepMapperImpl()


@pytest.fixture
def outbox_mapper() -> OrchestratorOutboxMapperImpl:
    return OrchestratorOutboxMapperImpl()


@pytest.fixture
def clock() -> SystemClockAdapter:
    return SystemClockAdapter()


@pytest.fixture
def id_gen() -> UuidGeneratorAdapter:
    return UuidGeneratorAdapter()


@pytest.fixture
def orch_repo(
    session: Session,
    orch_mapper: OrchestrationMapperImpl,
) -> SqlAlchemyOrchestrationRepository:
    return SqlAlchemyOrchestrationRepository(
        session=session, mapper=orch_mapper
    )


@pytest.fixture
def wf_repo(
    session: Session,
    wf_mapper: WorkflowMapperImpl,
) -> SqlAlchemyWorkflowRepository:
    return SqlAlchemyWorkflowRepository(
        session=session, mapper=wf_mapper
    )


@pytest.fixture
def step_repo(
    session: Session,
    step_mapper: WorkflowStepMapperImpl,
) -> SqlAlchemyWorkflowStepRepository:
    return SqlAlchemyWorkflowStepRepository(
        session=session, mapper=step_mapper
    )


@pytest.fixture
def outbox_adapter(
    session: Session,
    outbox_mapper: OrchestratorOutboxMapperImpl,
) -> SqlAlchemyOrchestratorOutboxAdapter:
    return SqlAlchemyOrchestratorOutboxAdapter(
        session=session, mapper=outbox_mapper
    )


@pytest.fixture
def an_orch(clock: SystemClockAdapter) -> Orchestration:
    return Orchestration(
        orchestration_id=OrchestrationId(),
        intent=UserIntent(value="integration intent"),
        goal=WorkflowGoal(value="integration goal"),
        status=OrchestrationStatus.CREATED,
        created_at=clock.now(),
    )


@pytest.fixture
def a_workflow(clock: SystemClockAdapter) -> Workflow:
    w = Workflow(
        workflow_id=WorkflowId(),
        goal=WorkflowGoal(value="integration workflow goal"),
        mode=ExecutionMode.SEQUENTIAL,
    )
    object.__setattr__(w, "_status", WorkflowStatus.PENDING)
    return w


@pytest.fixture
def a_step() -> WorkflowStep:
    return WorkflowStep(
        step_id=WorkflowId(
            value=UUID("00000000-0000-0000-0000-000000000001")
        ),
        agent_role=AgentRole.RESEARCH,
        execution_order=ExecutionOrder(value=0),
        status=WorkflowStepStatus.PENDING,
    )


# ===================================================================
# Orchestration repository integration tests
# ===================================================================


class TestOrchestrationRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        orch_repo: SqlAlchemyOrchestrationRepository,
        an_orch: Orchestration,
    ) -> None:
        orch_repo.save(an_orch)
        found = orch_repo.find_by_id(an_orch.orchestration_id)
        assert found is not None
        assert str(found.orchestration_id) == str(an_orch.orchestration_id)

    def test_save_updates_existing(
        self,
        orch_repo: SqlAlchemyOrchestrationRepository,
        an_orch: Orchestration,
    ) -> None:
        orch_repo.save(an_orch)
        an_orch.start_planning()
        orch_repo.save(an_orch)
        found = orch_repo.find_by_id(an_orch.orchestration_id)
        assert found is not None
        assert found.status == OrchestrationStatus.PLANNING

    def test_find_by_id_missing(
        self,
        orch_repo: SqlAlchemyOrchestrationRepository,
    ) -> None:
        found = orch_repo.find_by_id(OrchestrationId())
        assert found is None

    def test_find_by_status(
        self,
        orch_repo: SqlAlchemyOrchestrationRepository,
        an_orch: Orchestration,
    ) -> None:
        orch_repo.save(an_orch)
        results = orch_repo.find_by_status(OrchestrationStatus.CREATED)
        assert len(results) >= 1
        assert results[0].orchestration_id == an_orch.orchestration_id

    def test_find_by_status_empty(
        self,
        orch_repo: SqlAlchemyOrchestrationRepository,
    ) -> None:
        results = orch_repo.find_by_status(OrchestrationStatus.COMPLETED)
        assert len(results) == 0

    def test_count(
        self,
        orch_repo: SqlAlchemyOrchestrationRepository,
        an_orch: Orchestration,
    ) -> None:
        assert orch_repo.count() == 0
        orch_repo.save(an_orch)
        assert orch_repo.count() == 1

    def test_lifecycle_persistence(
        self,
        orch_repo: SqlAlchemyOrchestrationRepository,
        an_orch: Orchestration,
    ) -> None:
        orch_repo.save(an_orch)
        an_orch.start_planning()
        orch_repo.save(an_orch)
        found = orch_repo.find_by_id(an_orch.orchestration_id)
        assert found is not None
        assert found.status == OrchestrationStatus.PLANNING
        an_orch.start_research()
        orch_repo.save(an_orch)
        found = orch_repo.find_by_id(an_orch.orchestration_id)
        assert found is not None
        assert found.status == OrchestrationStatus.RESEARCHING

    def test_failure_reason_persisted(
        self,
        orch_repo: SqlAlchemyOrchestrationRepository,
        an_orch: Orchestration,
    ) -> None:
        orch_repo.save(an_orch)
        an_orch.start_planning()
        an_orch.fail(FailureReason(value="integration failure"))
        orch_repo.save(an_orch)
        found = orch_repo.find_by_id(an_orch.orchestration_id)
        assert found is not None
        assert found.status == OrchestrationStatus.FAILED

    def test_multiple_orchestrations(
        self,
        orch_repo: SqlAlchemyOrchestrationRepository,
    ) -> None:
        o1 = Orchestration(
            orchestration_id=OrchestrationId(),
            intent=UserIntent(value="intent 1"),
            goal=WorkflowGoal(value="goal 1"),
            created_at=NOW,
        )
        o2 = Orchestration(
            orchestration_id=OrchestrationId(),
            intent=UserIntent(value="intent 2"),
            goal=WorkflowGoal(value="goal 2"),
            created_at=NOW,
        )
        orch_repo.save(o1)
        orch_repo.save(o2)
        assert orch_repo.count() == 2

    def test_full_lifecycle_all_statuses(
        self,
        orch_repo: SqlAlchemyOrchestrationRepository,
        an_orch: Orchestration,
    ) -> None:
        orch_repo.save(an_orch)
        for method, status in [
            ("start_planning", OrchestrationStatus.PLANNING),
            ("start_research", OrchestrationStatus.RESEARCHING),
            ("start_execution", OrchestrationStatus.EXECUTING),
        ]:
            getattr(an_orch, method)()
            orch_repo.save(an_orch)
            found = orch_repo.find_by_id(an_orch.orchestration_id)
            assert found is not None
            assert found.status == status


# ===================================================================
# Workflow repository integration tests
# ===================================================================


class TestWorkflowRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        wf_repo: SqlAlchemyWorkflowRepository,
        a_workflow: Workflow,
    ) -> None:
        wf_repo.save(a_workflow)
        found = wf_repo.find_by_id(a_workflow.workflow_id)
        assert found is not None
        assert str(found.workflow_id) == str(a_workflow.workflow_id)

    def test_save_updates_existing(
        self,
        wf_repo: SqlAlchemyWorkflowRepository,
        a_workflow: Workflow,
    ) -> None:
        a_workflow.add_step(WorkflowStep(
            step_id=WorkflowId(),
            agent_role=AgentRole.RESEARCH,
            execution_order=ExecutionOrder(value=0),
        ))
        wf_repo.save(a_workflow)
        a_workflow.start()
        wf_repo.save(a_workflow)
        found = wf_repo.find_by_id(a_workflow.workflow_id)
        assert found is not None
        assert found.status == WorkflowStatus.RUNNING

    def test_find_by_id_missing(
        self,
        wf_repo: SqlAlchemyWorkflowRepository,
    ) -> None:
        found = wf_repo.find_by_id(WorkflowId())
        assert found is None

    def test_find_by_status(
        self,
        wf_repo: SqlAlchemyWorkflowRepository,
        a_workflow: Workflow,
    ) -> None:
        wf_repo.save(a_workflow)
        results = wf_repo.find_by_status(WorkflowStatus.PENDING)
        assert len(results) >= 1
        assert results[0].workflow_id == a_workflow.workflow_id

    def test_find_by_status_empty(
        self,
        wf_repo: SqlAlchemyWorkflowRepository,
    ) -> None:
        results = wf_repo.find_by_status(WorkflowStatus.COMPLETED)
        assert len(results) == 0

    def test_find_by_orchestration_id(
        self,
        wf_repo: SqlAlchemyWorkflowRepository,
        a_workflow: Workflow,
    ) -> None:
        wf_repo.save(a_workflow)
        results = wf_repo.find_by_orchestration_id(OrchestrationId())
        assert isinstance(results, list)

    def test_count(
        self,
        wf_repo: SqlAlchemyWorkflowRepository,
        a_workflow: Workflow,
    ) -> None:
        assert wf_repo.count() == 0
        wf_repo.save(a_workflow)
        assert wf_repo.count() == 1

    def test_workflow_lifecycle(
        self,
        wf_repo: SqlAlchemyWorkflowRepository,
    ) -> None:
        wf = Workflow(
            workflow_id=WorkflowId(),
            goal=WorkflowGoal(value="lifecycle workflow"),
            mode=ExecutionMode.SEQUENTIAL,
        )
        wf.add_step(WorkflowStep(
            step_id=WorkflowId(),
            agent_role=AgentRole.RESEARCH,
            execution_order=ExecutionOrder(value=0),
        ))
        wf_repo.save(wf)
        wf.start()
        wf_repo.save(wf)
        found = wf_repo.find_by_id(wf.workflow_id)
        assert found is not None
        assert found.status == WorkflowStatus.RUNNING
        wf.complete()
        wf_repo.save(wf)
        found = wf_repo.find_by_id(wf.workflow_id)
        assert found is not None
        assert found.status == WorkflowStatus.COMPLETED

    def test_multiple_workflows(
        self,
        wf_repo: SqlAlchemyWorkflowRepository,
    ) -> None:
        w1 = Workflow(
            workflow_id=WorkflowId(),
            goal=WorkflowGoal(value="workflow A"),
        )
        w2 = Workflow(
            workflow_id=WorkflowId(),
            goal=WorkflowGoal(value="workflow B"),
        )
        wf_repo.save(w1)
        wf_repo.save(w2)
        assert wf_repo.count() == 2


# ===================================================================
# WorkflowStep repository integration tests
# ===================================================================


class TestWorkflowStepRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        step_repo: SqlAlchemyWorkflowStepRepository,
        a_step: WorkflowStep,
    ) -> None:
        step_repo.save(a_step)
        found = step_repo.find_by_id(a_step.step_id)
        assert found is not None
        assert found.step_id == a_step.step_id

    def test_save_updates_existing(
        self,
        step_repo: SqlAlchemyWorkflowStepRepository,
        a_step: WorkflowStep,
    ) -> None:
        step_repo.save(a_step)
        a_step.start()
        step_repo.save(a_step)
        found = step_repo.find_by_id(a_step.step_id)
        assert found is not None
        assert found.status == WorkflowStepStatus.RUNNING

    def test_find_by_id_missing(
        self,
        step_repo: SqlAlchemyWorkflowStepRepository,
    ) -> None:
        found = step_repo.find_by_id(WorkflowId())
        assert found is None

    def test_find_by_status(
        self,
        step_repo: SqlAlchemyWorkflowStepRepository,
        a_step: WorkflowStep,
    ) -> None:
        step_repo.save(a_step)
        results = step_repo.find_by_status(WorkflowStepStatus.PENDING)
        assert len(results) >= 1
        assert results[0].step_id == a_step.step_id

    def test_find_by_status_empty(
        self,
        step_repo: SqlAlchemyWorkflowStepRepository,
    ) -> None:
        results = step_repo.find_by_status(WorkflowStepStatus.COMPLETED)
        assert len(results) == 0

    def test_find_by_workflow_id(
        self,
        step_repo: SqlAlchemyWorkflowStepRepository,
        a_step: WorkflowStep,
    ) -> None:
        step_repo.save(a_step)
        results = step_repo.find_by_workflow_id(WorkflowId())
        assert isinstance(results, list)

    def test_find_by_agent_role(
        self,
        step_repo: SqlAlchemyWorkflowStepRepository,
        a_step: WorkflowStep,
    ) -> None:
        step_repo.save(a_step)
        results = step_repo.find_by_agent_role(AgentRole.RESEARCH)
        assert len(results) >= 1

    def test_find_by_agent_role_empty(
        self,
        step_repo: SqlAlchemyWorkflowStepRepository,
    ) -> None:
        results = step_repo.find_by_agent_role(AgentRole.PLANNER)
        assert len(results) == 0

    def test_count(
        self,
        step_repo: SqlAlchemyWorkflowStepRepository,
        a_step: WorkflowStep,
    ) -> None:
        assert step_repo.count() == 0
        step_repo.save(a_step)
        assert step_repo.count() == 1

    def test_step_lifecycle(
        self,
        step_repo: SqlAlchemyWorkflowStepRepository,
    ) -> None:
        step = WorkflowStep(
            step_id=WorkflowId(),
            agent_role=AgentRole.AUTOMATION,
            execution_order=ExecutionOrder(value=0),
        )
        step_repo.save(step)
        step.start()
        step_repo.save(step)
        found = step_repo.find_by_id(step.step_id)
        assert found is not None
        assert found.status == WorkflowStepStatus.RUNNING
        step.complete(ExecutionResult(value="done"))
        step_repo.save(step)
        found = step_repo.find_by_id(step.step_id)
        assert found is not None
        assert found.status == WorkflowStepStatus.COMPLETED
        assert str(found.result) == "done"

    def test_step_failure(
        self,
        step_repo: SqlAlchemyWorkflowStepRepository,
    ) -> None:
        step = WorkflowStep(
            step_id=WorkflowId(),
            agent_role=AgentRole.MEMORY,
            execution_order=ExecutionOrder(value=1),
        )
        step_repo.save(step)
        step.start()
        step.fail(FailureReason(value="step integration error"))
        step_repo.save(step)
        found = step_repo.find_by_id(step.step_id)
        assert found is not None
        assert found.status == WorkflowStepStatus.FAILED
        assert str(found.failure_reason) == "step integration error"

    def test_skipped_step(
        self,
        step_repo: SqlAlchemyWorkflowStepRepository,
        a_step: WorkflowStep,
    ) -> None:
        step_repo.save(a_step)
        a_step.skip()
        step_repo.save(a_step)
        found = step_repo.find_by_id(a_step.step_id)
        assert found is not None
        assert found.status == WorkflowStepStatus.SKIPPED

    def test_multiple_steps(
        self,
        step_repo: SqlAlchemyWorkflowStepRepository,
    ) -> None:
        s1 = WorkflowStep(
            step_id=WorkflowId(),
            agent_role=AgentRole.RESEARCH,
            execution_order=ExecutionOrder(value=0),
        )
        s2 = WorkflowStep(
            step_id=WorkflowId(),
            agent_role=AgentRole.PLANNER,
            execution_order=ExecutionOrder(value=1),
        )
        step_repo.save(s1)
        step_repo.save(s2)
        assert step_repo.count() == 2


# ===================================================================
# Outbox adapter integration tests
# ===================================================================


class TestOrchestratorOutboxAdapterIntegration:
    def test_append_and_fetch(
        self,
        outbox_adapter: SqlAlchemyOrchestratorOutboxAdapter,
    ) -> None:
        event = OrchestrationCreated(
            orchestration_id=OrchestrationId(),
            intent="test intent",
            goal="test goal",
            occurred_at=NOW,
        )
        outbox_adapter.append(event)
        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], OrchestrationCreated)

    def test_fifo_ordering(
        self,
        outbox_adapter: SqlAlchemyOrchestratorOutboxAdapter,
    ) -> None:
        t1 = OrchestrationCreated(
            OrchestrationId(), "intent1", "goal1", NOW
        )
        t2 = OrchestrationCreated(
            OrchestrationId(), "intent2", "goal2", NOW
        )
        outbox_adapter.append(t1)
        outbox_adapter.append(t2)
        unpublished = outbox_adapter.fetch_unpublished(limit=10)
        assert len(unpublished) == 2

    def test_mark_published(
        self,
        outbox_adapter: SqlAlchemyOrchestratorOutboxAdapter,
        session: Session,
    ) -> None:
        event = OrchestrationCreated(
            OrchestrationId(), "intent", "goal", NOW
        )
        outbox_adapter.append(event)
        unpublished_before = outbox_adapter.fetch_unpublished()
        assert len(unpublished_before) == 1

        unpublished_before = outbox_adapter.fetch_unpublished()
        outbox_adapter.mark_published(str(unpublished_before[0].event_id))
        session.flush()
        unpublished_after = outbox_adapter.fetch_unpublished()
        assert len(unpublished_after) == 0

    def test_mark_published_idempotent(
        self,
        outbox_adapter: SqlAlchemyOrchestratorOutboxAdapter,
    ) -> None:
        event = OrchestrationCreated(
            OrchestrationId(), "intent", "goal", NOW
        )
        outbox_adapter.append(event)
        fetched = outbox_adapter.fetch_unpublished()
        outbox_adapter.mark_published(str(fetched[0].event_id))
        outbox_adapter.mark_published(str(fetched[0].event_id))

    def test_fetch_limit(
        self,
        outbox_adapter: SqlAlchemyOrchestratorOutboxAdapter,
    ) -> None:
        for i in range(5):
            event = OrchestrationCreated(
                OrchestrationId(), f"intent-{i}", "goal", NOW
            )
            outbox_adapter.append(event)
        results = outbox_adapter.fetch_unpublished(limit=3)
        assert len(results) == 3

    def test_empty_outbox(
        self,
        outbox_adapter: SqlAlchemyOrchestratorOutboxAdapter,
    ) -> None:
        results = outbox_adapter.fetch_unpublished()
        assert len(results) == 0

    def test_multiple_event_types(
        self,
        outbox_adapter: SqlAlchemyOrchestratorOutboxAdapter,
    ) -> None:
        oid = OrchestrationId()
        events = [
            OrchestrationCreated(oid, "intent", "goal", NOW),
            OrchestrationPlanningStarted(oid, NOW),
            OrchestrationCompleted(oid, NOW),
        ]
        for e in events:
            outbox_adapter.append(e)
        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 3


# ===================================================================
# Multi-entity integration tests
# ===================================================================


class TestMultiEntityIntegration:
    def test_independent_storage(
        self,
        orch_repo: SqlAlchemyOrchestrationRepository,
        wf_repo: SqlAlchemyWorkflowRepository,
        step_repo: SqlAlchemyWorkflowStepRepository,
        an_orch: Orchestration,
        a_workflow: Workflow,
        a_step: WorkflowStep,
    ) -> None:
        orch_repo.save(an_orch)
        wf_repo.save(a_workflow)
        step_repo.save(a_step)
        found_orch = orch_repo.find_by_id(an_orch.orchestration_id)
        found_wf = wf_repo.find_by_id(a_workflow.workflow_id)
        found_step = step_repo.find_by_id(a_step.step_id)
        assert found_orch is not None
        assert found_wf is not None
        assert found_step is not None

    def test_sqlite_roundtrip(
        self,
        session: Session,
        orch_repo: SqlAlchemyOrchestrationRepository,
        an_orch: Orchestration,
    ) -> None:
        orch_repo.save(an_orch)
        session.commit()
        session.expire_all()
        found = orch_repo.find_by_id(an_orch.orchestration_id)
        assert found is not None
        assert str(found.orchestration_id) == str(an_orch.orchestration_id)
        assert str(found.intent) == "integration intent"
        assert found.status == OrchestrationStatus.CREATED

    def test_outbox_with_orch_persistence(
        self,
        session: Session,
        orch_repo: SqlAlchemyOrchestrationRepository,
        outbox_adapter: SqlAlchemyOrchestratorOutboxAdapter,
        an_orch: Orchestration,
    ) -> None:
        orch_repo.save(an_orch)
        event = OrchestrationCreated(
            orchestration_id=an_orch.orchestration_id,
            intent=str(an_orch.intent),
            goal=str(an_orch.goal),
            occurred_at=NOW,
        )
        outbox_adapter.append(event)
        session.flush()
        found_orch = orch_repo.find_by_id(an_orch.orchestration_id)
        unpublished = outbox_adapter.fetch_unpublished()
        assert found_orch is not None
        assert len(unpublished) == 1

    def test_orch_status_transitions(
        self,
        orch_repo: SqlAlchemyOrchestrationRepository,
        an_orch: Orchestration,
    ) -> None:
        orch_repo.save(an_orch)
        an_orch.start_planning()
        orch_repo.save(an_orch)
        found = orch_repo.find_by_id(an_orch.orchestration_id)
        assert found is not None and found.status == OrchestrationStatus.PLANNING
        an_orch.start_research()
        orch_repo.save(an_orch)
        found = orch_repo.find_by_id(an_orch.orchestration_id)
        assert found is not None and found.status == OrchestrationStatus.RESEARCHING
        an_orch.start_execution()
        orch_repo.save(an_orch)
        found = orch_repo.find_by_id(an_orch.orchestration_id)
        assert found is not None and found.status == OrchestrationStatus.EXECUTING

    def test_all_outbox_event_types(
        self,
        outbox_adapter: SqlAlchemyOrchestratorOutboxAdapter,
    ) -> None:
        oid = OrchestrationId()
        wid = WorkflowId()
        sid = WorkflowId()
        events = [
            OrchestrationCreated(oid, "i", "g", NOW),
            OrchestrationPlanningStarted(oid, NOW),
            OrchestrationResearchStarted(oid, NOW),
            OrchestrationExecutionStarted(oid, NOW),
            OrchestrationCompleted(oid, NOW),
            OrchestrationFailed(oid, "err", NOW),
            OrchestrationCancelled(oid, NOW),
            WorkflowCreated(wid, oid, "g", "sequential", NOW),
            WorkflowCompleted(wid, NOW),
            WorkflowFailed(wid, "err", NOW),
            WorkflowStepStarted(sid, NOW),
            WorkflowStepCompleted(sid, "r", NOW),
            WorkflowStepFailed(sid, "err", NOW),
        ]
        for e in events:
            outbox_adapter.append(e)
        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 13

    def test_step_workflow_orch_combined(
        self,
        session: Session,
        orch_repo: SqlAlchemyOrchestrationRepository,
        wf_repo: SqlAlchemyWorkflowRepository,
        step_repo: SqlAlchemyWorkflowStepRepository,
        outbox_adapter: SqlAlchemyOrchestratorOutboxAdapter,
        an_orch: Orchestration,
    ) -> None:
        orch_repo.save(an_orch)
        wf = Workflow(
            workflow_id=WorkflowId(),
            goal=WorkflowGoal(value="combined wf"),
            mode=ExecutionMode.SEQUENTIAL,
        )
        wf.add_step(WorkflowStep(
            step_id=WorkflowId(),
            agent_role=AgentRole.RESEARCH,
            execution_order=ExecutionOrder(value=0),
        ))
        an_orch.add_workflow(wf)

        wf_repo.save(wf)
        orch_repo.save(an_orch)

        step = WorkflowStep(
            step_id=WorkflowId(),
            agent_role=AgentRole.AUTOMATION,
            execution_order=ExecutionOrder(value=0),
        )
        step_repo.save(step)

        outbox_adapter.append(OrchestrationCreated(
            an_orch.orchestration_id, "intent", "goal", NOW
        ))

        session.flush()

        found_orch = orch_repo.find_by_id(an_orch.orchestration_id)
        found_wf = wf_repo.find_by_id(wf.workflow_id)
        found_step = step_repo.find_by_id(step.step_id)
        assert found_orch is not None
        assert found_wf is not None
        assert found_step is not None
        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) >= 1

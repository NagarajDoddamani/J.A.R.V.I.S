from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.orchestrator.adapters.outbound.clock import SystemClockAdapter
from backend.orchestrator.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.orchestrator.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyOrchestrationRepository,
    SqlAlchemyOrchestratorOutboxAdapter,
    SqlAlchemyWorkflowRepository,
    SqlAlchemyWorkflowStepRepository,
)
from backend.orchestrator.application.use_cases.add_step import AddStepUseCase
from backend.orchestrator.application.use_cases.cancel_orchestration import CancelOrchestrationUseCase
from backend.orchestrator.application.use_cases.complete_orchestration import CompleteOrchestrationUseCase
from backend.orchestrator.application.use_cases.complete_step import CompleteStepUseCase
from backend.orchestrator.application.use_cases.complete_workflow import CompleteWorkflowUseCase
from backend.orchestrator.application.use_cases.create_orchestration import CreateOrchestrationUseCase
from backend.orchestrator.application.use_cases.create_workflow import CreateWorkflowUseCase
from backend.orchestrator.application.use_cases.fail_orchestration import FailOrchestrationUseCase
from backend.orchestrator.application.use_cases.fail_step import FailStepUseCase
from backend.orchestrator.application.use_cases.fail_workflow import FailWorkflowUseCase
from backend.orchestrator.application.use_cases.get_orchestration import GetOrchestrationUseCase
from backend.orchestrator.application.use_cases.get_step import GetStepUseCase
from backend.orchestrator.application.use_cases.get_workflow import GetWorkflowUseCase
from backend.orchestrator.application.use_cases.list_orchestrations import ListOrchestrationsUseCase
from backend.orchestrator.application.use_cases.list_workflows import ListWorkflowsUseCase
from backend.orchestrator.application.use_cases.start_execution import StartExecutionUseCase
from backend.orchestrator.application.use_cases.start_planning import StartPlanningUseCase
from backend.orchestrator.application.use_cases.start_research import StartResearchUseCase
from backend.orchestrator.application.use_cases.start_step import StartStepUseCase


# -- Internal providers ------------------------------------------------


def _orchestration_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyOrchestrationRepository:
    return SqlAlchemyOrchestrationRepository(db)


def _workflow_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyWorkflowRepository:
    return SqlAlchemyWorkflowRepository(db)


def _step_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyWorkflowStepRepository:
    return SqlAlchemyWorkflowStepRepository(db)


def _outbox(
    db: Session = Depends(get_db),
) -> SqlAlchemyOrchestratorOutboxAdapter:
    return SqlAlchemyOrchestratorOutboxAdapter(db)


def _clock() -> SystemClockAdapter:
    return SystemClockAdapter()


def _id_generator() -> UuidGeneratorAdapter:
    return UuidGeneratorAdapter()


# -- Orchestration use-case providers ----------------------------------


def create_orchestration_use_case(
    orchestration_repo: SqlAlchemyOrchestrationRepository = Depends(_orchestration_repo),
    outbox: SqlAlchemyOrchestratorOutboxAdapter = Depends(_outbox),
) -> CreateOrchestrationUseCase:
    return CreateOrchestrationUseCase(
        orchestration_repo=orchestration_repo, outbox=outbox
    )


def start_planning_use_case(
    orchestration_repo: SqlAlchemyOrchestrationRepository = Depends(_orchestration_repo),
    outbox: SqlAlchemyOrchestratorOutboxAdapter = Depends(_outbox),
) -> StartPlanningUseCase:
    return StartPlanningUseCase(
        orchestration_repo=orchestration_repo, outbox=outbox
    )


def start_research_use_case(
    orchestration_repo: SqlAlchemyOrchestrationRepository = Depends(_orchestration_repo),
    outbox: SqlAlchemyOrchestratorOutboxAdapter = Depends(_outbox),
) -> StartResearchUseCase:
    return StartResearchUseCase(
        orchestration_repo=orchestration_repo, outbox=outbox
    )


def start_execution_use_case(
    orchestration_repo: SqlAlchemyOrchestrationRepository = Depends(_orchestration_repo),
    outbox: SqlAlchemyOrchestratorOutboxAdapter = Depends(_outbox),
) -> StartExecutionUseCase:
    return StartExecutionUseCase(
        orchestration_repo=orchestration_repo, outbox=outbox
    )


def complete_orchestration_use_case(
    orchestration_repo: SqlAlchemyOrchestrationRepository = Depends(_orchestration_repo),
    outbox: SqlAlchemyOrchestratorOutboxAdapter = Depends(_outbox),
) -> CompleteOrchestrationUseCase:
    return CompleteOrchestrationUseCase(
        orchestration_repo=orchestration_repo, outbox=outbox
    )


def fail_orchestration_use_case(
    orchestration_repo: SqlAlchemyOrchestrationRepository = Depends(_orchestration_repo),
    outbox: SqlAlchemyOrchestratorOutboxAdapter = Depends(_outbox),
) -> FailOrchestrationUseCase:
    return FailOrchestrationUseCase(
        orchestration_repo=orchestration_repo, outbox=outbox
    )


def cancel_orchestration_use_case(
    orchestration_repo: SqlAlchemyOrchestrationRepository = Depends(_orchestration_repo),
    outbox: SqlAlchemyOrchestratorOutboxAdapter = Depends(_outbox),
) -> CancelOrchestrationUseCase:
    return CancelOrchestrationUseCase(
        orchestration_repo=orchestration_repo, outbox=outbox
    )


# -- Workflow use-case providers ---------------------------------------


def create_workflow_use_case(
    orchestration_repo: SqlAlchemyOrchestrationRepository = Depends(_orchestration_repo),
    workflow_repo: SqlAlchemyWorkflowRepository = Depends(_workflow_repo),
    outbox: SqlAlchemyOrchestratorOutboxAdapter = Depends(_outbox),
) -> CreateWorkflowUseCase:
    return CreateWorkflowUseCase(
        orchestration_repo=orchestration_repo,
        workflow_repo=workflow_repo,
        outbox=outbox,
    )


def complete_workflow_use_case(
    workflow_repo: SqlAlchemyWorkflowRepository = Depends(_workflow_repo),
    outbox: SqlAlchemyOrchestratorOutboxAdapter = Depends(_outbox),
) -> CompleteWorkflowUseCase:
    return CompleteWorkflowUseCase(
        workflow_repo=workflow_repo, outbox=outbox
    )


def fail_workflow_use_case(
    workflow_repo: SqlAlchemyWorkflowRepository = Depends(_workflow_repo),
    outbox: SqlAlchemyOrchestratorOutboxAdapter = Depends(_outbox),
) -> FailWorkflowUseCase:
    return FailWorkflowUseCase(
        workflow_repo=workflow_repo, outbox=outbox
    )


# -- Step use-case providers -------------------------------------------


def add_step_use_case(
    workflow_repo: SqlAlchemyWorkflowRepository = Depends(_workflow_repo),
    step_repo: SqlAlchemyWorkflowStepRepository = Depends(_step_repo),
) -> AddStepUseCase:
    return AddStepUseCase(workflow_repo=workflow_repo, step_repo=step_repo)


def start_step_use_case(
    step_repo: SqlAlchemyWorkflowStepRepository = Depends(_step_repo),
    outbox: SqlAlchemyOrchestratorOutboxAdapter = Depends(_outbox),
) -> StartStepUseCase:
    return StartStepUseCase(step_repo=step_repo, outbox=outbox)


def complete_step_use_case(
    step_repo: SqlAlchemyWorkflowStepRepository = Depends(_step_repo),
    outbox: SqlAlchemyOrchestratorOutboxAdapter = Depends(_outbox),
) -> CompleteStepUseCase:
    return CompleteStepUseCase(step_repo=step_repo, outbox=outbox)


def fail_step_use_case(
    step_repo: SqlAlchemyWorkflowStepRepository = Depends(_step_repo),
    outbox: SqlAlchemyOrchestratorOutboxAdapter = Depends(_outbox),
) -> FailStepUseCase:
    return FailStepUseCase(step_repo=step_repo, outbox=outbox)


# -- Query use-case providers ------------------------------------------


def get_orchestration_use_case(
    orchestration_repo: SqlAlchemyOrchestrationRepository = Depends(_orchestration_repo),
) -> GetOrchestrationUseCase:
    return GetOrchestrationUseCase(orchestration_repo=orchestration_repo)


def list_orchestrations_use_case(
    orchestration_repo: SqlAlchemyOrchestrationRepository = Depends(_orchestration_repo),
) -> ListOrchestrationsUseCase:
    return ListOrchestrationsUseCase(orchestration_repo=orchestration_repo)


def get_workflow_use_case(
    workflow_repo: SqlAlchemyWorkflowRepository = Depends(_workflow_repo),
) -> GetWorkflowUseCase:
    return GetWorkflowUseCase(workflow_repo=workflow_repo)


def list_workflows_use_case(
    workflow_repo: SqlAlchemyWorkflowRepository = Depends(_workflow_repo),
) -> ListWorkflowsUseCase:
    return ListWorkflowsUseCase(workflow_repo=workflow_repo)


def get_step_use_case(
    step_repo: SqlAlchemyWorkflowStepRepository = Depends(_step_repo),
) -> GetStepUseCase:
    return GetStepUseCase(step_repo=step_repo)

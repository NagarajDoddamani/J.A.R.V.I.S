from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.orchestrator.adapters.outbound.clock import SystemClockAdapter
from backend.orchestrator.adapters.outbound.id_generator import UuidGeneratorAdapter
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
from backend.orchestrator.bootstrap import (
    _clock,
    _id_generator,
    _orchestration_repo,
    _outbox,
    _step_repo,
    _workflow_repo,
    add_step_use_case,
    cancel_orchestration_use_case,
    complete_orchestration_use_case,
    complete_step_use_case,
    complete_workflow_use_case,
    create_orchestration_use_case,
    create_workflow_use_case,
    fail_orchestration_use_case,
    fail_step_use_case,
    fail_workflow_use_case,
    get_orchestration_use_case,
    get_step_use_case,
    get_workflow_use_case,
    list_orchestrations_use_case,
    list_workflows_use_case,
    start_execution_use_case,
    start_planning_use_case,
    start_research_use_case,
    start_step_use_case,
)


# ===================================================================
# Internal provider tests
# ===================================================================


def test_orchestration_repo_provider() -> None:
    with patch("backend.orchestrator.bootstrap.get_db") as mock_db:
        mock_db.return_value = MagicMock()
        repo = _orchestration_repo()
        from backend.orchestrator.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyOrchestrationRepository,
        )
        assert isinstance(repo, SqlAlchemyOrchestrationRepository)


def test_workflow_repo_provider() -> None:
    with patch("backend.orchestrator.bootstrap.get_db") as mock_db:
        mock_db.return_value = MagicMock()
        repo = _workflow_repo()
        from backend.orchestrator.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyWorkflowRepository,
        )
        assert isinstance(repo, SqlAlchemyWorkflowRepository)


def test_step_repo_provider() -> None:
    with patch("backend.orchestrator.bootstrap.get_db") as mock_db:
        mock_db.return_value = MagicMock()
        repo = _step_repo()
        from backend.orchestrator.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyWorkflowStepRepository,
        )
        assert isinstance(repo, SqlAlchemyWorkflowStepRepository)


def test_outbox_provider() -> None:
    with patch("backend.orchestrator.bootstrap.get_db") as mock_db:
        mock_db.return_value = MagicMock()
        ob = _outbox()
        from backend.orchestrator.adapters.outbound.sqlalchemy_repository import (
            SqlAlchemyOrchestratorOutboxAdapter,
        )
        assert isinstance(ob, SqlAlchemyOrchestratorOutboxAdapter)


def test_clock_provider() -> None:
    clock = _clock()
    assert isinstance(clock, SystemClockAdapter)


def test_id_generator_provider() -> None:
    gen = _id_generator()
    assert isinstance(gen, UuidGeneratorAdapter)


# ===================================================================
# Use case provider tests — Orchestration
# ===================================================================


def test_create_orchestration_use_case_provider() -> None:
    uc = create_orchestration_use_case(
        orchestration_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(uc, CreateOrchestrationUseCase)


def test_start_planning_use_case_provider() -> None:
    uc = start_planning_use_case(
        orchestration_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(uc, StartPlanningUseCase)


def test_start_research_use_case_provider() -> None:
    uc = start_research_use_case(
        orchestration_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(uc, StartResearchUseCase)


def test_start_execution_use_case_provider() -> None:
    uc = start_execution_use_case(
        orchestration_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(uc, StartExecutionUseCase)


def test_complete_orchestration_use_case_provider() -> None:
    uc = complete_orchestration_use_case(
        orchestration_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(uc, CompleteOrchestrationUseCase)


def test_fail_orchestration_use_case_provider() -> None:
    uc = fail_orchestration_use_case(
        orchestration_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(uc, FailOrchestrationUseCase)


def test_cancel_orchestration_use_case_provider() -> None:
    uc = cancel_orchestration_use_case(
        orchestration_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(uc, CancelOrchestrationUseCase)


# ===================================================================
# Use case provider tests — Workflow
# ===================================================================


def test_create_workflow_use_case_provider() -> None:
    uc = create_workflow_use_case(
        orchestration_repo=MagicMock(),
        workflow_repo=MagicMock(),
        outbox=MagicMock(),
    )
    assert isinstance(uc, CreateWorkflowUseCase)


def test_complete_workflow_use_case_provider() -> None:
    uc = complete_workflow_use_case(
        workflow_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(uc, CompleteWorkflowUseCase)


def test_fail_workflow_use_case_provider() -> None:
    uc = fail_workflow_use_case(
        workflow_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(uc, FailWorkflowUseCase)


# ===================================================================
# Use case provider tests — Steps
# ===================================================================


def test_add_step_use_case_provider() -> None:
    uc = add_step_use_case(
        workflow_repo=MagicMock(), step_repo=MagicMock()
    )
    assert isinstance(uc, AddStepUseCase)


def test_start_step_use_case_provider() -> None:
    uc = start_step_use_case(
        step_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(uc, StartStepUseCase)


def test_complete_step_use_case_provider() -> None:
    uc = complete_step_use_case(
        step_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(uc, CompleteStepUseCase)


def test_fail_step_use_case_provider() -> None:
    uc = fail_step_use_case(
        step_repo=MagicMock(), outbox=MagicMock()
    )
    assert isinstance(uc, FailStepUseCase)


# ===================================================================
# Use case provider tests — Queries
# ===================================================================


def test_get_orchestration_use_case_provider() -> None:
    uc = get_orchestration_use_case(orchestration_repo=MagicMock())
    assert isinstance(uc, GetOrchestrationUseCase)


def test_list_orchestrations_use_case_provider() -> None:
    uc = list_orchestrations_use_case(orchestration_repo=MagicMock())
    assert isinstance(uc, ListOrchestrationsUseCase)


def test_get_workflow_use_case_provider() -> None:
    uc = get_workflow_use_case(workflow_repo=MagicMock())
    assert isinstance(uc, GetWorkflowUseCase)


def test_list_workflows_use_case_provider() -> None:
    uc = list_workflows_use_case(workflow_repo=MagicMock())
    assert isinstance(uc, ListWorkflowsUseCase)


def test_get_step_use_case_provider() -> None:
    uc = get_step_use_case(step_repo=MagicMock())
    assert isinstance(uc, GetStepUseCase)

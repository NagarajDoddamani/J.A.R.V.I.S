from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.automation.adapters.outbound.clock import SystemClockAdapter
from backend.automation.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.automation.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyAutomationExecutionRepository,
    SqlAlchemyAutomationOutboxAdapter,
    SqlAlchemyAutomationRepository,
    SqlAlchemyTriggerRepository,
)
from backend.automation.application.use_cases.activate_automation import (
    ActivateAutomationUseCase,
)
from backend.automation.application.use_cases.add_action import AddActionUseCase
from backend.automation.application.use_cases.add_trigger import AddTriggerUseCase
from backend.automation.application.use_cases.complete_execution import (
    CompleteExecutionUseCase,
)
from backend.automation.application.use_cases.create_automation import (
    CreateAutomationUseCase,
)
from backend.automation.application.use_cases.disable_automation import (
    DisableAutomationUseCase,
)
from backend.automation.application.use_cases.disable_trigger import (
    DisableTriggerUseCase,
)
from backend.automation.application.use_cases.enable_trigger import (
    EnableTriggerUseCase,
)
from backend.automation.application.use_cases.fail_execution import (
    FailExecutionUseCase,
)
from backend.automation.application.use_cases.get_automation import (
    GetAutomationUseCase,
)
from backend.automation.application.use_cases.get_execution import (
    GetExecutionUseCase,
)
from backend.automation.application.use_cases.get_trigger import (
    GetTriggerUseCase,
)
from backend.automation.application.use_cases.list_automations import (
    ListAutomationsUseCase,
)
from backend.automation.application.use_cases.list_executions import (
    ListExecutionsUseCase,
)
from backend.automation.application.use_cases.list_triggers import (
    ListTriggersUseCase,
)
from backend.automation.application.use_cases.pause_automation import (
    PauseAutomationUseCase,
)
from backend.automation.application.use_cases.start_execution import (
    StartExecutionUseCase,
)


def _automation_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyAutomationRepository:
    return SqlAlchemyAutomationRepository(db)


def _trigger_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyTriggerRepository:
    return SqlAlchemyTriggerRepository(db)


def _execution_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyAutomationExecutionRepository:
    return SqlAlchemyAutomationExecutionRepository(db)


def _outbox(
    db: Session = Depends(get_db),
) -> SqlAlchemyAutomationOutboxAdapter:
    return SqlAlchemyAutomationOutboxAdapter(db)


def _clock() -> SystemClockAdapter:
    return SystemClockAdapter()


def _id_generator() -> UuidGeneratorAdapter:
    return UuidGeneratorAdapter()


# -- Automation commands -------------------------------------------------


def create_automation_use_case(
    automation_repo: SqlAlchemyAutomationRepository = Depends(_automation_repo),
    outbox: SqlAlchemyAutomationOutboxAdapter = Depends(_outbox),
) -> CreateAutomationUseCase:
    return CreateAutomationUseCase(automation_repo=automation_repo, outbox=outbox)


def activate_automation_use_case(
    automation_repo: SqlAlchemyAutomationRepository = Depends(_automation_repo),
    outbox: SqlAlchemyAutomationOutboxAdapter = Depends(_outbox),
) -> ActivateAutomationUseCase:
    return ActivateAutomationUseCase(automation_repo=automation_repo, outbox=outbox)


def pause_automation_use_case(
    automation_repo: SqlAlchemyAutomationRepository = Depends(_automation_repo),
    outbox: SqlAlchemyAutomationOutboxAdapter = Depends(_outbox),
) -> PauseAutomationUseCase:
    return PauseAutomationUseCase(automation_repo=automation_repo, outbox=outbox)


def disable_automation_use_case(
    automation_repo: SqlAlchemyAutomationRepository = Depends(_automation_repo),
    outbox: SqlAlchemyAutomationOutboxAdapter = Depends(_outbox),
) -> DisableAutomationUseCase:
    return DisableAutomationUseCase(automation_repo=automation_repo, outbox=outbox)


# -- Trigger commands ----------------------------------------------------


def add_trigger_use_case(
    automation_repo: SqlAlchemyAutomationRepository = Depends(_automation_repo),
    trigger_repo: SqlAlchemyTriggerRepository = Depends(_trigger_repo),
    outbox: SqlAlchemyAutomationOutboxAdapter = Depends(_outbox),
) -> AddTriggerUseCase:
    return AddTriggerUseCase(
        automation_repo=automation_repo,
        trigger_repo=trigger_repo,
        outbox=outbox,
    )


def enable_trigger_use_case(
    trigger_repo: SqlAlchemyTriggerRepository = Depends(_trigger_repo),
    automation_repo: SqlAlchemyAutomationRepository = Depends(_automation_repo),
    outbox: SqlAlchemyAutomationOutboxAdapter = Depends(_outbox),
) -> EnableTriggerUseCase:
    return EnableTriggerUseCase(
        trigger_repo=trigger_repo,
        automation_repo=automation_repo,
        outbox=outbox,
    )


def disable_trigger_use_case(
    trigger_repo: SqlAlchemyTriggerRepository = Depends(_trigger_repo),
    automation_repo: SqlAlchemyAutomationRepository = Depends(_automation_repo),
    outbox: SqlAlchemyAutomationOutboxAdapter = Depends(_outbox),
) -> DisableTriggerUseCase:
    return DisableTriggerUseCase(
        trigger_repo=trigger_repo,
        automation_repo=automation_repo,
        outbox=outbox,
    )


# -- Action commands ----------------------------------------------------


def add_action_use_case(
    automation_repo: SqlAlchemyAutomationRepository = Depends(_automation_repo),
    outbox: SqlAlchemyAutomationOutboxAdapter = Depends(_outbox),
) -> AddActionUseCase:
    return AddActionUseCase(automation_repo=automation_repo, outbox=outbox)


# -- Execution commands -------------------------------------------------


def start_execution_use_case(
    automation_repo: SqlAlchemyAutomationRepository = Depends(_automation_repo),
    execution_repo: SqlAlchemyAutomationExecutionRepository = Depends(_execution_repo),
    outbox: SqlAlchemyAutomationOutboxAdapter = Depends(_outbox),
) -> StartExecutionUseCase:
    return StartExecutionUseCase(
        automation_repo=automation_repo,
        execution_repo=execution_repo,
        outbox=outbox,
    )


def complete_execution_use_case(
    automation_repo: SqlAlchemyAutomationRepository = Depends(_automation_repo),
    execution_repo: SqlAlchemyAutomationExecutionRepository = Depends(_execution_repo),
    outbox: SqlAlchemyAutomationOutboxAdapter = Depends(_outbox),
) -> CompleteExecutionUseCase:
    return CompleteExecutionUseCase(
        automation_repo=automation_repo,
        execution_repo=execution_repo,
        outbox=outbox,
    )


def fail_execution_use_case(
    automation_repo: SqlAlchemyAutomationRepository = Depends(_automation_repo),
    execution_repo: SqlAlchemyAutomationExecutionRepository = Depends(_execution_repo),
    outbox: SqlAlchemyAutomationOutboxAdapter = Depends(_outbox),
) -> FailExecutionUseCase:
    return FailExecutionUseCase(
        automation_repo=automation_repo,
        execution_repo=execution_repo,
        outbox=outbox,
    )


# -- Queries -------------------------------------------------------------


def get_automation_use_case(
    automation_repo: SqlAlchemyAutomationRepository = Depends(_automation_repo),
) -> GetAutomationUseCase:
    return GetAutomationUseCase(automation_repo=automation_repo)


def list_automations_use_case(
    automation_repo: SqlAlchemyAutomationRepository = Depends(_automation_repo),
) -> ListAutomationsUseCase:
    return ListAutomationsUseCase(automation_repo=automation_repo)


def get_trigger_use_case(
    trigger_repo: SqlAlchemyTriggerRepository = Depends(_trigger_repo),
) -> GetTriggerUseCase:
    return GetTriggerUseCase(trigger_repo=trigger_repo)


def list_triggers_use_case(
    trigger_repo: SqlAlchemyTriggerRepository = Depends(_trigger_repo),
) -> ListTriggersUseCase:
    return ListTriggersUseCase(trigger_repo=trigger_repo)


def get_execution_use_case(
    execution_repo: SqlAlchemyAutomationExecutionRepository = Depends(_execution_repo),
) -> GetExecutionUseCase:
    return GetExecutionUseCase(execution_repo=execution_repo)


def list_executions_use_case(
    execution_repo: SqlAlchemyAutomationExecutionRepository = Depends(_execution_repo),
) -> ListExecutionsUseCase:
    return ListExecutionsUseCase(execution_repo=execution_repo)

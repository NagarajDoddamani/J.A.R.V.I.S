from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.agent.adapters.outbound.clock import SystemClockAdapter
from backend.agent.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.agent.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyAgentExecutionRepository,
    SqlAlchemyAgentOutboxAdapter,
    SqlAlchemyAgentRepository,
    SqlAlchemyAgentTaskRepository,
)
from backend.agent.application.use_cases.activate_agent import (
    ActivateAgentUseCase,
)
from backend.agent.application.use_cases.cancel_task import CancelTaskUseCase
from backend.agent.application.use_cases.complete_execution import (
    CompleteExecutionUseCase,
)
from backend.agent.application.use_cases.complete_task import (
    CompleteTaskUseCase,
)
from backend.agent.application.use_cases.create_agent import (
    CreateAgentUseCase,
)
from backend.agent.application.use_cases.create_task import CreateTaskUseCase
from backend.agent.application.use_cases.disable_agent import (
    DisableAgentUseCase,
)
from backend.agent.application.use_cases.fail_execution import (
    FailExecutionUseCase,
)
from backend.agent.application.use_cases.fail_task import FailTaskUseCase
from backend.agent.application.use_cases.get_agent import GetAgentUseCase
from backend.agent.application.use_cases.get_execution import (
    GetExecutionUseCase,
)
from backend.agent.application.use_cases.get_task import GetTaskUseCase
from backend.agent.application.use_cases.list_agents import (
    ListAgentsUseCase,
)
from backend.agent.application.use_cases.list_executions import (
    ListExecutionsUseCase,
)
from backend.agent.application.use_cases.list_tasks import ListTasksUseCase
from backend.agent.application.use_cases.pause_agent import (
    PauseAgentUseCase,
)
from backend.agent.application.use_cases.start_execution import (
    StartExecutionUseCase,
)
from backend.agent.application.use_cases.start_task import StartTaskUseCase
from backend.core.database import get_db


def _agent_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyAgentRepository:
    return SqlAlchemyAgentRepository(db)


def _task_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyAgentTaskRepository:
    return SqlAlchemyAgentTaskRepository(db)


def _execution_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyAgentExecutionRepository:
    return SqlAlchemyAgentExecutionRepository(db)


def _outbox(
    db: Session = Depends(get_db),
) -> SqlAlchemyAgentOutboxAdapter:
    return SqlAlchemyAgentOutboxAdapter(db)


def _clock() -> SystemClockAdapter:
    return SystemClockAdapter()


def _id_generator() -> UuidGeneratorAdapter:
    return UuidGeneratorAdapter()


# -- Agent lifecycle commands -------------------------------------------


def get_create_agent_use_case(
    agent_repo: SqlAlchemyAgentRepository = Depends(_agent_repo),
    outbox: SqlAlchemyAgentOutboxAdapter = Depends(_outbox),
) -> CreateAgentUseCase:
    return CreateAgentUseCase(agent_repo=agent_repo, outbox=outbox)


def get_activate_agent_use_case(
    agent_repo: SqlAlchemyAgentRepository = Depends(_agent_repo),
    outbox: SqlAlchemyAgentOutboxAdapter = Depends(_outbox),
) -> ActivateAgentUseCase:
    return ActivateAgentUseCase(agent_repo=agent_repo, outbox=outbox)


def get_pause_agent_use_case(
    agent_repo: SqlAlchemyAgentRepository = Depends(_agent_repo),
    outbox: SqlAlchemyAgentOutboxAdapter = Depends(_outbox),
) -> PauseAgentUseCase:
    return PauseAgentUseCase(agent_repo=agent_repo, outbox=outbox)


def get_disable_agent_use_case(
    agent_repo: SqlAlchemyAgentRepository = Depends(_agent_repo),
    outbox: SqlAlchemyAgentOutboxAdapter = Depends(_outbox),
) -> DisableAgentUseCase:
    return DisableAgentUseCase(agent_repo=agent_repo, outbox=outbox)


# -- Task lifecycle commands --------------------------------------------


def get_create_task_use_case(
    agent_repo: SqlAlchemyAgentRepository = Depends(_agent_repo),
    outbox: SqlAlchemyAgentOutboxAdapter = Depends(_outbox),
) -> CreateTaskUseCase:
    return CreateTaskUseCase(agent_repo=agent_repo, outbox=outbox)


def get_start_task_use_case(
    agent_repo: SqlAlchemyAgentRepository = Depends(_agent_repo),
    outbox: SqlAlchemyAgentOutboxAdapter = Depends(_outbox),
) -> StartTaskUseCase:
    return StartTaskUseCase(agent_repo=agent_repo, outbox=outbox)


def get_complete_task_use_case(
    agent_repo: SqlAlchemyAgentRepository = Depends(_agent_repo),
    outbox: SqlAlchemyAgentOutboxAdapter = Depends(_outbox),
) -> CompleteTaskUseCase:
    return CompleteTaskUseCase(agent_repo=agent_repo, outbox=outbox)


def get_fail_task_use_case(
    agent_repo: SqlAlchemyAgentRepository = Depends(_agent_repo),
    outbox: SqlAlchemyAgentOutboxAdapter = Depends(_outbox),
) -> FailTaskUseCase:
    return FailTaskUseCase(agent_repo=agent_repo, outbox=outbox)


def get_cancel_task_use_case(
    agent_repo: SqlAlchemyAgentRepository = Depends(_agent_repo),
    outbox: SqlAlchemyAgentOutboxAdapter = Depends(_outbox),
) -> CancelTaskUseCase:
    return CancelTaskUseCase(agent_repo=agent_repo, outbox=outbox)


# -- Execution lifecycle commands ---------------------------------------


def get_start_execution_use_case(
    agent_repo: SqlAlchemyAgentRepository = Depends(_agent_repo),
    outbox: SqlAlchemyAgentOutboxAdapter = Depends(_outbox),
) -> StartExecutionUseCase:
    return StartExecutionUseCase(agent_repo=agent_repo, outbox=outbox)


def get_complete_execution_use_case(
    agent_repo: SqlAlchemyAgentRepository = Depends(_agent_repo),
    outbox: SqlAlchemyAgentOutboxAdapter = Depends(_outbox),
) -> CompleteExecutionUseCase:
    return CompleteExecutionUseCase(agent_repo=agent_repo, outbox=outbox)


def get_fail_execution_use_case(
    agent_repo: SqlAlchemyAgentRepository = Depends(_agent_repo),
    outbox: SqlAlchemyAgentOutboxAdapter = Depends(_outbox),
) -> FailExecutionUseCase:
    return FailExecutionUseCase(agent_repo=agent_repo, outbox=outbox)


# -- Queries ------------------------------------------------------------


def get_agent_use_case(
    agent_repo: SqlAlchemyAgentRepository = Depends(_agent_repo),
) -> GetAgentUseCase:
    return GetAgentUseCase(agent_repo=agent_repo)


def get_list_agents_use_case(
    agent_repo: SqlAlchemyAgentRepository = Depends(_agent_repo),
) -> ListAgentsUseCase:
    return ListAgentsUseCase(agent_repo=agent_repo)


def get_task_use_case(
    task_repo: SqlAlchemyAgentTaskRepository = Depends(_task_repo),
) -> GetTaskUseCase:
    return GetTaskUseCase(task_repo=task_repo)


def get_list_tasks_use_case(
    task_repo: SqlAlchemyAgentTaskRepository = Depends(_task_repo),
) -> ListTasksUseCase:
    return ListTasksUseCase(task_repo=task_repo)


def get_execution_use_case(
    execution_repo: SqlAlchemyAgentExecutionRepository = Depends(
        _execution_repo
    ),
) -> GetExecutionUseCase:
    return GetExecutionUseCase(execution_repo=execution_repo)


def get_list_executions_use_case(
    execution_repo: SqlAlchemyAgentExecutionRepository = Depends(
        _execution_repo
    ),
) -> ListExecutionsUseCase:
    return ListExecutionsUseCase(execution_repo=execution_repo)

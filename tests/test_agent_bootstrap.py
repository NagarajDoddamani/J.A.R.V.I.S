from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import Depends
from sqlalchemy.orm import Session

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
from backend.agent.bootstrap import (
    get_activate_agent_use_case,
    get_cancel_task_use_case,
    get_complete_execution_use_case,
    get_complete_task_use_case,
    get_create_agent_use_case,
    get_create_task_use_case,
    get_disable_agent_use_case,
    get_execution_use_case,
    get_fail_execution_use_case,
    get_fail_task_use_case,
    get_agent_use_case,
    get_list_agents_use_case,
    get_list_executions_use_case,
    get_list_tasks_use_case,
    get_pause_agent_use_case,
    get_start_execution_use_case,
    get_start_task_use_case,
    get_task_use_case,
)


def _mock_db() -> Session:
    return MagicMock(spec=Session)


class TestBootstrapProviders:
    def test_create_agent_use_case(self) -> None:
        use_case = get_create_agent_use_case(
            agent_repo=MagicMock(spec=SqlAlchemyAgentRepository),
            outbox=MagicMock(spec=SqlAlchemyAgentOutboxAdapter),
        )
        assert isinstance(use_case, CreateAgentUseCase)

    def test_activate_agent_use_case(self) -> None:
        use_case = get_activate_agent_use_case(
            agent_repo=MagicMock(spec=SqlAlchemyAgentRepository),
            outbox=MagicMock(spec=SqlAlchemyAgentOutboxAdapter),
        )
        assert isinstance(use_case, ActivateAgentUseCase)

    def test_pause_agent_use_case(self) -> None:
        use_case = get_pause_agent_use_case(
            agent_repo=MagicMock(spec=SqlAlchemyAgentRepository),
            outbox=MagicMock(spec=SqlAlchemyAgentOutboxAdapter),
        )
        assert isinstance(use_case, PauseAgentUseCase)

    def test_disable_agent_use_case(self) -> None:
        use_case = get_disable_agent_use_case(
            agent_repo=MagicMock(spec=SqlAlchemyAgentRepository),
            outbox=MagicMock(spec=SqlAlchemyAgentOutboxAdapter),
        )
        assert isinstance(use_case, DisableAgentUseCase)

    def test_create_task_use_case(self) -> None:
        use_case = get_create_task_use_case(
            agent_repo=MagicMock(spec=SqlAlchemyAgentRepository),
            outbox=MagicMock(spec=SqlAlchemyAgentOutboxAdapter),
        )
        assert isinstance(use_case, CreateTaskUseCase)

    def test_start_task_use_case(self) -> None:
        use_case = get_start_task_use_case(
            agent_repo=MagicMock(spec=SqlAlchemyAgentRepository),
            outbox=MagicMock(spec=SqlAlchemyAgentOutboxAdapter),
        )
        assert isinstance(use_case, StartTaskUseCase)

    def test_complete_task_use_case(self) -> None:
        use_case = get_complete_task_use_case(
            agent_repo=MagicMock(spec=SqlAlchemyAgentRepository),
            outbox=MagicMock(spec=SqlAlchemyAgentOutboxAdapter),
        )
        assert isinstance(use_case, CompleteTaskUseCase)

    def test_fail_task_use_case(self) -> None:
        use_case = get_fail_task_use_case(
            agent_repo=MagicMock(spec=SqlAlchemyAgentRepository),
            outbox=MagicMock(spec=SqlAlchemyAgentOutboxAdapter),
        )
        assert isinstance(use_case, FailTaskUseCase)

    def test_cancel_task_use_case(self) -> None:
        use_case = get_cancel_task_use_case(
            agent_repo=MagicMock(spec=SqlAlchemyAgentRepository),
            outbox=MagicMock(spec=SqlAlchemyAgentOutboxAdapter),
        )
        assert isinstance(use_case, CancelTaskUseCase)

    def test_start_execution_use_case(self) -> None:
        use_case = get_start_execution_use_case(
            agent_repo=MagicMock(spec=SqlAlchemyAgentRepository),
            outbox=MagicMock(spec=SqlAlchemyAgentOutboxAdapter),
        )
        assert isinstance(use_case, StartExecutionUseCase)

    def test_complete_execution_use_case(self) -> None:
        use_case = get_complete_execution_use_case(
            agent_repo=MagicMock(spec=SqlAlchemyAgentRepository),
            outbox=MagicMock(SqlAlchemyAgentOutboxAdapter),
        )
        assert isinstance(use_case, CompleteExecutionUseCase)

    def test_fail_execution_use_case(self) -> None:
        use_case = get_fail_execution_use_case(
            agent_repo=MagicMock(spec=SqlAlchemyAgentRepository),
            outbox=MagicMock(spec=SqlAlchemyAgentOutboxAdapter),
        )
        assert isinstance(use_case, FailExecutionUseCase)

    def test_get_agent_use_case(self) -> None:
        use_case = get_agent_use_case(
            agent_repo=MagicMock(spec=SqlAlchemyAgentRepository),
        )
        assert isinstance(use_case, GetAgentUseCase)

    def test_list_agents_use_case(self) -> None:
        use_case = get_list_agents_use_case(
            agent_repo=MagicMock(spec=SqlAlchemyAgentRepository),
        )
        assert isinstance(use_case, ListAgentsUseCase)

    def test_get_task_use_case(self) -> None:
        use_case = get_task_use_case(
            task_repo=MagicMock(spec=SqlAlchemyAgentTaskRepository),
        )
        assert isinstance(use_case, GetTaskUseCase)

    def test_list_tasks_use_case(self) -> None:
        use_case = get_list_tasks_use_case(
            task_repo=MagicMock(spec=SqlAlchemyAgentTaskRepository),
        )
        assert isinstance(use_case, ListTasksUseCase)

    def test_get_execution_use_case(self) -> None:
        use_case = get_execution_use_case(
            execution_repo=MagicMock(
                spec=SqlAlchemyAgentExecutionRepository
            ),
        )
        assert isinstance(use_case, GetExecutionUseCase)

    def test_list_executions_use_case(self) -> None:
        use_case = get_list_executions_use_case(
            execution_repo=MagicMock(
                spec=SqlAlchemyAgentExecutionRepository
            ),
        )
        assert isinstance(use_case, ListExecutionsUseCase)

    def test_all_agent_providers_count(self) -> None:
        providers = [
            get_create_agent_use_case,
            get_activate_agent_use_case,
            get_pause_agent_use_case,
            get_disable_agent_use_case,
            get_create_task_use_case,
            get_start_task_use_case,
            get_complete_task_use_case,
            get_fail_task_use_case,
            get_cancel_task_use_case,
            get_start_execution_use_case,
            get_complete_execution_use_case,
            get_fail_execution_use_case,
            get_agent_use_case,
            get_list_agents_use_case,
            get_task_use_case,
            get_list_tasks_use_case,
            get_execution_use_case,
            get_list_executions_use_case,
        ]
        assert len(providers) == 18

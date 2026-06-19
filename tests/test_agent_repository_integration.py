from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator
from uuid import UUID

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.agent.adapters.outbound.clock import SystemClockAdapter
from backend.agent.adapters.outbound.id_generator import (
    UuidGeneratorAdapter,
)
from backend.agent.adapters.outbound.mapper import (
    AgentExecutionMapperImpl,
    AgentMapperImpl,
    AgentOutboxMapperImpl,
    AgentTaskMapperImpl,
)
from backend.agent.adapters.outbound.models import (
    AgentOutboxModel,
    Base,
)
from backend.agent.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyAgentExecutionRepository,
    SqlAlchemyAgentOutboxAdapter,
    SqlAlchemyAgentRepository,
    SqlAlchemyAgentTaskRepository,
)
from backend.agent.domain.model import (
    Agent,
    AgentExecution,
    AgentExecutionId,
    AgentExecutionStatus,
    AgentGoal,
    AgentId,
    AgentInstruction,
    AgentName,
    AgentResult,
    AgentStatus,
    AgentTask,
    AgentTaskId,
    AgentTaskStatus,
    AgentType,
    FailureReason,
)

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


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
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture
def agent_mapper() -> AgentMapperImpl:
    return AgentMapperImpl()


@pytest.fixture
def task_mapper() -> AgentTaskMapperImpl:
    return AgentTaskMapperImpl()


@pytest.fixture
def execution_mapper() -> AgentExecutionMapperImpl:
    return AgentExecutionMapperImpl()


@pytest.fixture
def outbox_mapper() -> AgentOutboxMapperImpl:
    return AgentOutboxMapperImpl()


@pytest.fixture
def clock() -> SystemClockAdapter:
    return SystemClockAdapter()


@pytest.fixture
def id_gen() -> UuidGeneratorAdapter:
    return UuidGeneratorAdapter()


@pytest.fixture
def agent_repo(
    session: Session,
    agent_mapper: AgentMapperImpl,
    task_mapper: AgentTaskMapperImpl,
) -> SqlAlchemyAgentRepository:
    return SqlAlchemyAgentRepository(
        session=session,
        mapper=agent_mapper,
        task_mapper=task_mapper,
    )


@pytest.fixture
def task_repo(
    session: Session,
    task_mapper: AgentTaskMapperImpl,
) -> SqlAlchemyAgentTaskRepository:
    return SqlAlchemyAgentTaskRepository(
        session=session, mapper=task_mapper
    )


@pytest.fixture
def execution_repo(
    session: Session,
    execution_mapper: AgentExecutionMapperImpl,
) -> SqlAlchemyAgentExecutionRepository:
    return SqlAlchemyAgentExecutionRepository(
        session=session, mapper=execution_mapper
    )


@pytest.fixture
def outbox_adapter(
    session: Session,
    outbox_mapper: AgentOutboxMapperImpl,
) -> SqlAlchemyAgentOutboxAdapter:
    return SqlAlchemyAgentOutboxAdapter(
        session=session, mapper=outbox_mapper
    )


@pytest.fixture
def an_agent() -> Agent:
    return Agent(
        agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
        agent_type=AgentType.COORDINATOR,
        name=AgentName(value="Test Agent"),
        status=AgentStatus.IDLE,
        created_at=NOW,
    )


@pytest.fixture
def a_task() -> AgentTask:
    return AgentTask(
        task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
        agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
        goal=AgentGoal(value="Test Goal"),
        instruction=AgentInstruction(value="Test Instruction"),
        status=AgentTaskStatus.PENDING,
    )


# ===================================================================
# Agent Repository Integration Tests
# ===================================================================


class TestAgentRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        agent_repo: SqlAlchemyAgentRepository,
        an_agent: Agent,
    ) -> None:
        agent_repo.save(an_agent)
        stored = agent_repo.find_by_id(an_agent.agent_id)
        assert stored is not None
        assert stored.agent_id == an_agent.agent_id
        assert str(stored.name) == "Test Agent"
        assert stored.status == AgentStatus.IDLE

    def test_save_updates_existing(
        self,
        agent_repo: SqlAlchemyAgentRepository,
        an_agent: Agent,
    ) -> None:
        agent_repo.save(an_agent)
        an_agent._status = AgentStatus.ACTIVE
        an_agent._updated_at = NOW
        agent_repo.save(an_agent)
        stored = agent_repo.find_by_id(an_agent.agent_id)
        assert stored is not None
        assert stored.status == AgentStatus.ACTIVE

    def test_find_by_id_returns_none_for_missing(
        self,
        agent_repo: SqlAlchemyAgentRepository,
    ) -> None:
        result = agent_repo.find_by_id(
            AgentId(value=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"))
        )
        assert result is None

    def test_find_by_status(
        self,
        agent_repo: SqlAlchemyAgentRepository,
        an_agent: Agent,
    ) -> None:
        agent_repo.save(an_agent)
        results = agent_repo.find_by_status(AgentStatus.IDLE)
        assert len(results) == 1
        results = agent_repo.find_by_status(AgentStatus.ACTIVE)
        assert len(results) == 0

    def test_find_by_type(
        self,
        agent_repo: SqlAlchemyAgentRepository,
        an_agent: Agent,
    ) -> None:
        agent_repo.save(an_agent)
        results = agent_repo.find_by_type(AgentType.COORDINATOR)
        assert len(results) == 1
        results = agent_repo.find_by_type(AgentType.RESEARCH)
        assert len(results) == 0

    def test_find_all(
        self,
        agent_repo: SqlAlchemyAgentRepository,
        an_agent: Agent,
    ) -> None:
        agent_repo.save(an_agent)
        results = agent_repo.find_all()
        assert len(results) == 1

    def test_count(
        self,
        agent_repo: SqlAlchemyAgentRepository,
        an_agent: Agent,
    ) -> None:
        assert agent_repo.count() == 0
        agent_repo.save(an_agent)
        assert agent_repo.count() == 1

    def test_multiple_agents(
        self,
        agent_repo: SqlAlchemyAgentRepository,
        an_agent: Agent,
    ) -> None:
        agent_repo.save(an_agent)
        second = Agent(
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000002")),
            agent_type=AgentType.RESEARCH,
            name=AgentName(value="Second"),
            status=AgentStatus.ACTIVE,
            created_at=NOW,
        )
        agent_repo.save(second)
        assert agent_repo.count() == 2
        assert len(agent_repo.find_all()) == 2


# ===================================================================
# Task Repository Integration Tests
# ===================================================================


class TestTaskRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        task_repo: SqlAlchemyAgentTaskRepository,
        a_task: AgentTask,
    ) -> None:
        task_repo.save(a_task)
        stored = task_repo.find_by_id(a_task.task_id)
        assert stored is not None
        assert stored.task_id == a_task.task_id
        assert stored.status == AgentTaskStatus.PENDING

    def test_find_by_id_returns_none_for_missing(
        self,
        task_repo: SqlAlchemyAgentTaskRepository,
    ) -> None:
        result = task_repo.find_by_id(
            AgentTaskId(value=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"))
        )
        assert result is None

    def test_find_by_status(
        self,
        task_repo: SqlAlchemyAgentTaskRepository,
        a_task: AgentTask,
    ) -> None:
        task_repo.save(a_task)
        results = task_repo.find_by_status(AgentTaskStatus.PENDING)
        assert len(results) == 1
        results = task_repo.find_by_status(AgentTaskStatus.RUNNING)
        assert len(results) == 0

    def test_find_by_agent_id(
        self,
        task_repo: SqlAlchemyAgentTaskRepository,
        a_task: AgentTask,
    ) -> None:
        task_repo.save(a_task)
        results = task_repo.find_by_agent_id(
            str(UUID("00000000-0000-0000-0000-000000000001"))
        )
        assert len(results) == 1

    def test_save_updates_existing(
        self,
        task_repo: SqlAlchemyAgentTaskRepository,
        a_task: AgentTask,
    ) -> None:
        task_repo.save(a_task)
        a_task._status = AgentTaskStatus.RUNNING
        task_repo.save(a_task)
        stored = task_repo.find_by_id(a_task.task_id)
        assert stored is not None
        assert stored.status == AgentTaskStatus.RUNNING

    def test_find_all(
        self,
        task_repo: SqlAlchemyAgentTaskRepository,
        a_task: AgentTask,
    ) -> None:
        task_repo.save(a_task)
        assert len(task_repo.find_all()) == 1

    def test_count(
        self,
        task_repo: SqlAlchemyAgentTaskRepository,
        a_task: AgentTask,
    ) -> None:
        assert task_repo.count() == 0
        task_repo.save(a_task)
        assert task_repo.count() == 1

    def test_multiple_tasks(
        self,
        task_repo: SqlAlchemyAgentTaskRepository,
        a_task: AgentTask,
    ) -> None:
        task_repo.save(a_task)
        second = AgentTask(
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000011")),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            goal=AgentGoal(value="Second Goal"),
            instruction=AgentInstruction(value="Second Instr"),
        )
        task_repo.save(second)
        assert task_repo.count() == 2


# ===================================================================
# Execution Repository Integration Tests
# ===================================================================


class TestExecutionRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        execution_repo: SqlAlchemyAgentExecutionRepository,
    ) -> None:
        execution = AgentExecution(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
        )
        execution_repo.save(execution)
        stored = execution_repo.find_by_id(execution.execution_id)
        assert stored is not None
        assert stored.status == AgentExecutionStatus.PENDING

    def test_find_by_id_returns_none_for_missing(
        self,
        execution_repo: SqlAlchemyAgentExecutionRepository,
    ) -> None:
        result = execution_repo.find_by_id(
            AgentExecutionId(
                value=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
            )
        )
        assert result is None

    def test_find_by_status(
        self,
        execution_repo: SqlAlchemyAgentExecutionRepository,
    ) -> None:
        execution = AgentExecution(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
        )
        execution_repo.save(execution)
        results = execution_repo.find_by_status(AgentExecutionStatus.PENDING)
        assert len(results) == 1
        results = execution_repo.find_by_status(AgentExecutionStatus.EXECUTING)
        assert len(results) == 0

    def test_find_by_agent_id(
        self,
        execution_repo: SqlAlchemyAgentExecutionRepository,
    ) -> None:
        aid = AgentId(value=UUID("00000000-0000-0000-0000-000000000001"))
        execution = AgentExecution(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=aid,
        )
        execution_repo.save(execution)
        results = execution_repo.find_by_agent_id(aid)
        assert len(results) == 1

    def test_find_by_task_id(
        self,
        execution_repo: SqlAlchemyAgentExecutionRepository,
    ) -> None:
        tid = AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010"))
        execution = AgentExecution(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            task_id=tid,
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
        )
        execution_repo.save(execution)
        results = execution_repo.find_by_task_id(tid)
        assert len(results) == 1

    def test_save_updates_existing(
        self,
        execution_repo: SqlAlchemyAgentExecutionRepository,
    ) -> None:
        execution = AgentExecution(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
        )
        execution_repo.save(execution)
        execution._status = AgentExecutionStatus.EXECUTING
        execution_repo.save(execution)
        stored = execution_repo.find_by_id(execution.execution_id)
        assert stored is not None
        assert stored.status == AgentExecutionStatus.EXECUTING

    def test_find_all(
        self,
        execution_repo: SqlAlchemyAgentExecutionRepository,
    ) -> None:
        execution = AgentExecution(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
        )
        execution_repo.save(execution)
        assert len(execution_repo.find_all()) == 1

    def test_count(
        self,
        execution_repo: SqlAlchemyAgentExecutionRepository,
    ) -> None:
        assert execution_repo.count() == 0
        execution = AgentExecution(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
        )
        execution_repo.save(execution)
        assert execution_repo.count() == 1

    def test_completed_execution_fields(
        self,
        execution_repo: SqlAlchemyAgentExecutionRepository,
    ) -> None:
        execution = AgentExecution(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            status=AgentExecutionStatus.COMPLETED,
            result=AgentResult(value="Done"),
        )
        execution_repo.save(execution)
        stored = execution_repo.find_by_id(execution.execution_id)
        assert stored is not None
        assert stored.status == AgentExecutionStatus.COMPLETED
        assert str(stored.result) == "Done"

    def test_failed_execution_fields(
        self,
        execution_repo: SqlAlchemyAgentExecutionRepository,
    ) -> None:
        execution = AgentExecution(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            status=AgentExecutionStatus.FAILED,
            failure_reason=FailureReason(value="Error"),
        )
        execution_repo.save(execution)
        stored = execution_repo.find_by_id(execution.execution_id)
        assert stored is not None
        assert stored.status == AgentExecutionStatus.FAILED
        assert str(stored.failure_reason) == "Error"


# ===================================================================
# Outbox Adapter Integration Tests
# ===================================================================


class TestOutboxAdapterIntegration:
    def test_append_and_fetch_unpublished(
        self,
        session: Session,
        outbox_adapter: SqlAlchemyAgentOutboxAdapter,
    ) -> None:
        from backend.agent.domain.model import AgentCreated

        event = AgentCreated(
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            agent_type="coordinator",
            name="Test",
            occurred_at=NOW,
        )
        outbox_adapter.append(event)
        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], AgentCreated)

    def test_mark_published(
        self,
        outbox_adapter: SqlAlchemyAgentOutboxAdapter,
    ) -> None:
        from backend.agent.domain.model import AgentCreated

        event = AgentCreated(
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            agent_type="coordinator",
            name="Test",
            occurred_at=NOW,
        )
        outbox_adapter.append(event)
        fetched = outbox_adapter.fetch_unpublished()
        outbox_adapter.mark_published(str(fetched[0].event_id))
        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 0

    def test_fifo_ordering(
        self,
        outbox_adapter: SqlAlchemyAgentOutboxAdapter,
    ) -> None:
        from datetime import timedelta
        from backend.agent.domain.model import (
            AgentActivated,
            AgentCreated,
        )

        event1 = AgentCreated(
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            agent_type="coordinator",
            name="Test",
            occurred_at=NOW,
        )
        event2 = AgentActivated(
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            occurred_at=NOW + timedelta(seconds=1),
        )
        outbox_adapter.append(event1)
        outbox_adapter.append(event2)
        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 2
        assert isinstance(unpublished[0], AgentCreated)
        assert isinstance(unpublished[1], AgentActivated)

    def test_fetch_unpublished_limit(
        self,
        outbox_adapter: SqlAlchemyAgentOutboxAdapter,
    ) -> None:
        from backend.agent.domain.model import AgentCreated

        for i in range(5):
            event = AgentCreated(
                agent_id=AgentId(),
                agent_type="coordinator",
                name=f"Test {i}",
                occurred_at=NOW,
            )
            outbox_adapter.append(event)
        assert len(outbox_adapter.fetch_unpublished(limit=3)) == 3
        assert len(outbox_adapter.fetch_unpublished()) == 5

    def test_mark_published_idempotent(
        self,
        outbox_adapter: SqlAlchemyAgentOutboxAdapter,
    ) -> None:
        from backend.agent.domain.model import AgentCreated

        event = AgentCreated(
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            agent_type="coordinator",
            name="Test",
            occurred_at=NOW,
        )
        outbox_adapter.append(event)
        fetched = outbox_adapter.fetch_unpublished()
        outbox_adapter.mark_published(str(fetched[0].event_id))
        outbox_adapter.mark_published(str(fetched[0].event_id))
        assert len(outbox_adapter.fetch_unpublished()) == 0

    def test_outbox_model_defaults(
        self,
        session: Session,
    ) -> None:
        from uuid import uuid4

        model = AgentOutboxModel(
            message_id=str(uuid4()),
            subject="agent.created",
            aggregate_id="agg",
            created_at=NOW,
            payload={},
        )
        session.add(model)
        session.flush()
        persisted = session.get(AgentOutboxModel, model.message_id)
        assert persisted is not None
        assert persisted.published_at is None


# ===================================================================
# Relationship Integrity Tests
# ===================================================================


class TestRelationshipIntegrity:
    def test_agent_with_tasks_loaded(
        self,
        session: Session,
        agent_repo: SqlAlchemyAgentRepository,
        task_repo: SqlAlchemyAgentTaskRepository,
        an_agent: Agent,
    ) -> None:
        agent_repo.save(an_agent)
        task = AgentTask(
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=an_agent.agent_id,
            goal=AgentGoal(value="Goal"),
            instruction=AgentInstruction(value="Instr"),
        )
        task_repo.save(task)
        stored = agent_repo.find_by_id(an_agent.agent_id)
        assert stored is not None
        assert len(stored.tasks) == 1

    def test_agent_with_executions_loaded(
        self,
        session: Session,
        agent_repo: SqlAlchemyAgentRepository,
        execution_repo: SqlAlchemyAgentExecutionRepository,
        an_agent: Agent,
    ) -> None:
        agent_repo.save(an_agent)
        execution = AgentExecution(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=an_agent.agent_id,
        )
        execution_repo.save(execution)
        stored = agent_repo.find_by_id(an_agent.agent_id)
        assert stored is not None
        assert len(stored.executions) == 1

    def test_execution_belongs_to_agent(
        self,
        session: Session,
        agent_repo: SqlAlchemyAgentRepository,
        execution_repo: SqlAlchemyAgentExecutionRepository,
        an_agent: Agent,
    ) -> None:
        agent_repo.save(an_agent)
        execution = AgentExecution(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=an_agent.agent_id,
        )
        execution_repo.save(execution)
        executions = execution_repo.find_by_agent_id(an_agent.agent_id)
        assert len(executions) == 1

    def test_complete_sqlite_roundtrip(
        self,
        session: Session,
        agent_repo: SqlAlchemyAgentRepository,
        task_repo: SqlAlchemyAgentTaskRepository,
        execution_repo: SqlAlchemyAgentExecutionRepository,
        outbox_adapter: SqlAlchemyAgentOutboxAdapter,
    ) -> None:
        from backend.agent.domain.model import AgentCreated

        agent = Agent(
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            agent_type=AgentType.COORDINATOR,
            name=AgentName(value="Full"),
            status=AgentStatus.IDLE,
            created_at=NOW,
        )
        agent_repo.save(agent)

        task = AgentTask(
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=agent.agent_id,
            goal=AgentGoal(value="Goal"),
            instruction=AgentInstruction(value="Instr"),
        )
        task_repo.save(task)

        execution = AgentExecution(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            task_id=task.task_id,
            agent_id=agent.agent_id,
        )
        execution_repo.save(execution)

        event = AgentCreated(
            agent_id=agent.agent_id,
            agent_type="coordinator",
            name="Full",
            occurred_at=NOW,
        )
        outbox_adapter.append(event)

        assert agent_repo.count() == 1
        assert task_repo.count() == 1
        assert execution_repo.count() == 1
        assert len(outbox_adapter.fetch_unpublished()) == 1

        stored_agent = agent_repo.find_by_id(agent.agent_id)
        assert stored_agent is not None

        stored_task = task_repo.find_by_id(task.task_id)
        assert stored_task is not None

        stored_exec = execution_repo.find_by_id(execution.execution_id)
        assert stored_exec is not None

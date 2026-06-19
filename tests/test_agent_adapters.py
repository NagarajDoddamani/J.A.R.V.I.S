from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

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
from backend.agent.application.persistence.mapper import (
    AgentExecutionMapper,
    AgentMapper,
    AgentOutboxMapper,
    AgentTaskMapper,
)
from backend.agent.domain.model import (
    Agent,
    AgentActivated,
    AgentCreated,
    AgentDisabled,
    AgentExecution,
    AgentExecutionCompleted,
    AgentExecutionFailed,
    AgentExecutionId,
    AgentExecutionStarted,
    AgentGoal,
    AgentId,
    AgentInstruction,
    AgentName,
    AgentPaused,
    AgentResult,
    AgentStatus,
    AgentTask,
    AgentTaskCancelled,
    AgentTaskCompleted,
    AgentTaskCreated,
    AgentTaskFailed,
    AgentTaskId,
    AgentTaskStarted,
    AgentType,
    AgentExecutionStatus,
    AgentTaskStatus,
    FailureReason,
)

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


def _make_agent(
    status: AgentStatus = AgentStatus.IDLE,
    agent_type: AgentType = AgentType.COORDINATOR,
) -> Agent:
    return Agent(
        agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
        agent_type=agent_type,
        name=AgentName(value="Test Agent"),
        status=status,
        created_at=NOW,
    )


def _make_task(
    status: AgentTaskStatus = AgentTaskStatus.PENDING,
) -> AgentTask:
    return AgentTask(
        task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
        goal=AgentGoal(value="Test Goal"),
        instruction=AgentInstruction(value="Test Instruction"),
        status=status,
        agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
    )


def _make_execution(
    status: AgentExecutionStatus = AgentExecutionStatus.PENDING,
) -> AgentExecution:
    return AgentExecution(
        execution_id=AgentExecutionId(
            value=UUID("00000000-0000-0000-0000-000000000020")
        ),
        task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
        agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
        status=status,
    )


class TestSystemClockAdapter:
    def test_now_returns_utc(self) -> None:
        clock = SystemClockAdapter()
        result = clock.now()
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result) == timezone.utc.utcoffset(result)

    def test_now_returns_datetime(self) -> None:
        clock = SystemClockAdapter()
        result = clock.now()
        assert isinstance(result, datetime)


class TestUuidGeneratorAdapter:
    def test_generate_agent_id_returns_str(self) -> None:
        gen = UuidGeneratorAdapter()
        result = gen.generate_agent_id()
        assert isinstance(result, str)
        assert UUID(result)

    def test_generate_task_id_returns_str(self) -> None:
        gen = UuidGeneratorAdapter()
        result = gen.generate_task_id()
        assert isinstance(result, str)
        assert UUID(result)

    def test_generate_execution_id_returns_str(self) -> None:
        gen = UuidGeneratorAdapter()
        result = gen.generate_execution_id()
        assert isinstance(result, str)
        assert UUID(result)

    def test_unique_ids(self) -> None:
        gen = UuidGeneratorAdapter()
        ids = {
            gen.generate_agent_id(),
            gen.generate_task_id(),
            gen.generate_execution_id(),
        }
        assert len(ids) == 3


class TestAgentMapperImpl:
    def test_protocol_conformance(self) -> None:
        mapper: AgentMapper = AgentMapperImpl()
        assert isinstance(mapper, AgentMapperImpl)

    def test_domain_to_dto(self) -> None:
        mapper = AgentMapperImpl()
        agent = _make_agent()
        dto = mapper.domain_to_dto(agent)
        assert dto.agent_id == str(agent.agent_id)
        assert dto.name == "Test Agent"
        assert dto.agent_type == "coordinator"
        assert dto.status == "idle"
        assert dto.created_at == NOW

    def test_dto_to_domain(self) -> None:
        mapper = AgentMapperImpl()
        agent = _make_agent()
        dto = mapper.domain_to_dto(agent)
        result = mapper.dto_to_domain(dto)
        assert result.agent_id == agent.agent_id
        assert str(result.name) == "Test Agent"
        assert result.status == AgentStatus.IDLE
        assert result.agent_type == AgentType.COORDINATOR

    def test_roundtrip(self) -> None:
        mapper = AgentMapperImpl()
        original = _make_agent(
            status=AgentStatus.ACTIVE,
            agent_type=AgentType.RESEARCH,
        )
        dto = mapper.domain_to_dto(original)
        result = mapper.dto_to_domain(dto)
        assert result.agent_id == original.agent_id
        assert str(result.name) == str(original.name)
        assert result.status == AgentStatus.ACTIVE
        assert result.agent_type == AgentType.RESEARCH

    def test_nullable_fields(self) -> None:
        mapper = AgentMapperImpl()
        agent = Agent(
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            agent_type=AgentType.COORDINATOR,
            status=AgentStatus.IDLE,
            created_at=NOW,
        )
        dto = mapper.domain_to_dto(agent)
        assert dto.name is None
        result = mapper.dto_to_domain(dto)
        assert result.name is None

    def test_dto_with_tasks_and_executions(self) -> None:
        mapper = AgentMapperImpl()
        agent = _make_agent()
        dto = mapper.domain_to_dto(agent)
        task = _make_task()
        execution = _make_execution()
        result = mapper.dto_to_domain(dto, tasks=[task], executions=[execution])
        assert len(result.tasks) == 1
        assert len(result.executions) == 1
        assert result.tasks[0].task_id == task.task_id
        assert result.executions[0].execution_id == execution.execution_id


class TestAgentTaskMapperImpl:
    def test_protocol_conformance(self) -> None:
        mapper: AgentTaskMapper = AgentTaskMapperImpl()
        assert isinstance(mapper, AgentTaskMapperImpl)

    def test_domain_to_dto(self) -> None:
        mapper = AgentTaskMapperImpl()
        task = _make_task()
        dto = mapper.domain_to_dto(task)
        assert dto.task_id == str(task.task_id)
        assert dto.goal == "Test Goal"
        assert dto.instruction == "Test Instruction"
        assert dto.status == "pending"
        assert dto.agent_id == str(task.agent_id)

    def test_dto_to_domain(self) -> None:
        mapper = AgentTaskMapperImpl()
        task = _make_task()
        dto = mapper.domain_to_dto(task)
        result = mapper.dto_to_domain(dto)
        assert result.task_id == task.task_id
        assert str(result.goal) == "Test Goal"
        assert result.status == AgentTaskStatus.PENDING

    def test_roundtrip(self) -> None:
        mapper = AgentTaskMapperImpl()
        original = _make_task(status=AgentTaskStatus.RUNNING)
        dto = mapper.domain_to_dto(original)
        result = mapper.dto_to_domain(dto)
        assert result.task_id == original.task_id
        assert result.status == AgentTaskStatus.RUNNING
        assert str(result.goal) == "Test Goal"

    def test_completed_task_roundtrip(self) -> None:
        mapper = AgentTaskMapperImpl()
        original = AgentTask(
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            goal=AgentGoal(value="Goal"),
            instruction=AgentInstruction(value="Instr"),
            status=AgentTaskStatus.COMPLETED,
            result=AgentResult(value="Done"),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
        )
        dto = mapper.domain_to_dto(original)
        result = mapper.dto_to_domain(dto)
        assert result.status == AgentTaskStatus.COMPLETED
        assert str(result.result) == "Done"

    def test_failed_task_roundtrip(self) -> None:
        mapper = AgentTaskMapperImpl()
        original = AgentTask(
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            goal=AgentGoal(value="Goal"),
            instruction=AgentInstruction(value="Instr"),
            status=AgentTaskStatus.FAILED,
            failure_reason=FailureReason(value="Error"),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
        )
        dto = mapper.domain_to_dto(original)
        result = mapper.dto_to_domain(dto)
        assert result.status == AgentTaskStatus.FAILED
        assert str(result.failure_reason) == "Error"

    def test_nullable_fields(self) -> None:
        mapper = AgentTaskMapperImpl()
        task = AgentTask(
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
        )
        dto = mapper.domain_to_dto(task)
        assert dto.goal is None
        assert dto.instruction is None
        assert dto.result is None
        assert dto.failure_reason is None
        result = mapper.dto_to_domain(dto)
        assert result.goal is None
        assert result.instruction is None


class TestAgentExecutionMapperImpl:
    def test_protocol_conformance(self) -> None:
        mapper: AgentExecutionMapper = AgentExecutionMapperImpl()
        assert isinstance(mapper, AgentExecutionMapperImpl)

    def test_domain_to_dto(self) -> None:
        mapper = AgentExecutionMapperImpl()
        execution = _make_execution()
        dto = mapper.domain_to_dto(execution)
        assert dto.execution_id == str(execution.execution_id)
        assert dto.status == "pending"
        assert dto.result is None
        assert dto.failure_reason is None

    def test_dto_to_domain(self) -> None:
        mapper = AgentExecutionMapperImpl()
        execution = _make_execution()
        dto = mapper.domain_to_dto(execution)
        result = mapper.dto_to_domain(dto)
        assert result.execution_id == execution.execution_id
        assert result.status == AgentExecutionStatus.PENDING

    def test_roundtrip(self) -> None:
        mapper = AgentExecutionMapperImpl()
        original = AgentExecution(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            status=AgentExecutionStatus.COMPLETED,
            result=AgentResult(value="Success"),
        )
        dto = mapper.domain_to_dto(original)
        result = mapper.dto_to_domain(dto)
        assert result.execution_id == original.execution_id
        assert result.status == AgentExecutionStatus.COMPLETED
        assert str(result.result) == "Success"

    def test_failed_execution(self) -> None:
        mapper = AgentExecutionMapperImpl()
        original = AgentExecution(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            status=AgentExecutionStatus.FAILED,
            failure_reason=FailureReason(value="Error occurred"),
        )
        dto = mapper.domain_to_dto(original)
        result = mapper.dto_to_domain(dto)
        assert result.status == AgentExecutionStatus.FAILED
        assert str(result.failure_reason) == "Error occurred"

    def test_executing_roundtrip(self) -> None:
        mapper = AgentExecutionMapperImpl()
        original = AgentExecution(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            status=AgentExecutionStatus.EXECUTING,
        )
        dto = mapper.domain_to_dto(original)
        result = mapper.dto_to_domain(dto)
        assert result.status == AgentExecutionStatus.EXECUTING

    def test_nullable_fields(self) -> None:
        mapper = AgentExecutionMapperImpl()
        execution = AgentExecution(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
        )
        dto = mapper.domain_to_dto(execution)
        assert dto.result is None
        assert dto.failure_reason is None
        assert dto.agent_id is None


class TestAgentOutboxMapperImpl:
    def test_protocol_conformance(self) -> None:
        mapper: AgentOutboxMapper = AgentOutboxMapperImpl()
        assert isinstance(mapper, AgentOutboxMapperImpl)

    def test_agent_created_event(self) -> None:
        mapper = AgentOutboxMapperImpl()
        event = AgentCreated(
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            agent_type="coordinator",
            name="Test Agent",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "agent.created"
        assert dto.aggregate_id == str(event.agent_id)
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AgentCreated)
        assert result.name == "Test Agent"
        assert result.agent_type == "coordinator"

    def test_agent_activated_event(self) -> None:
        mapper = AgentOutboxMapperImpl()
        event = AgentActivated(
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "agent.activated"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AgentActivated)

    def test_agent_paused_event(self) -> None:
        mapper = AgentOutboxMapperImpl()
        event = AgentPaused(
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "agent.paused"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AgentPaused)

    def test_agent_disabled_event(self) -> None:
        mapper = AgentOutboxMapperImpl()
        event = AgentDisabled(
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "agent.disabled"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AgentDisabled)

    def test_task_created_event(self) -> None:
        mapper = AgentOutboxMapperImpl()
        event = AgentTaskCreated(
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            goal="Test Goal",
            instruction="Test Instruction",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "agent.task_created"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AgentTaskCreated)
        assert result.goal == "Test Goal"
        assert result.instruction == "Test Instruction"

    def test_task_started_event(self) -> None:
        mapper = AgentOutboxMapperImpl()
        event = AgentTaskStarted(
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "agent.task_started"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AgentTaskStarted)

    def test_task_completed_event(self) -> None:
        mapper = AgentOutboxMapperImpl()
        event = AgentTaskCompleted(
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            result="Done",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "agent.task_completed"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AgentTaskCompleted)
        assert result.result == "Done"

    def test_task_failed_event(self) -> None:
        mapper = AgentOutboxMapperImpl()
        event = AgentTaskFailed(
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            failure_reason="Error",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "agent.task_failed"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AgentTaskFailed)
        assert result.failure_reason == "Error"

    def test_task_cancelled_event(self) -> None:
        mapper = AgentOutboxMapperImpl()
        event = AgentTaskCancelled(
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "agent.task_cancelled"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AgentTaskCancelled)

    def test_execution_started_event(self) -> None:
        mapper = AgentOutboxMapperImpl()
        event = AgentExecutionStarted(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "agent.execution_started"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AgentExecutionStarted)

    def test_execution_completed_event(self) -> None:
        mapper = AgentOutboxMapperImpl()
        event = AgentExecutionCompleted(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            result="Success",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "agent.execution_completed"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AgentExecutionCompleted)
        assert result.result == "Success"

    def test_execution_failed_event(self) -> None:
        mapper = AgentOutboxMapperImpl()
        event = AgentExecutionFailed(
            execution_id=AgentExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            task_id=AgentTaskId(value=UUID("00000000-0000-0000-0000-000000000010")),
            failure_reason="Error",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "agent.execution_failed"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AgentExecutionFailed)
        assert result.failure_reason == "Error"

    def test_all_events_have_unique_types(self) -> None:
        mapper = AgentOutboxMapperImpl()
        events: list = [
            AgentCreated(
                agent_id=AgentId(), agent_type="coordinator", name="n",
                occurred_at=NOW,
            ),
            AgentActivated(
                agent_id=AgentId(), occurred_at=NOW,
            ),
            AgentPaused(
                agent_id=AgentId(), occurred_at=NOW,
            ),
            AgentDisabled(
                agent_id=AgentId(), occurred_at=NOW,
            ),
            AgentTaskCreated(
                task_id=AgentTaskId(), agent_id=AgentId(),
                goal="g", instruction="i", occurred_at=NOW,
            ),
            AgentTaskStarted(
                task_id=AgentTaskId(), agent_id=AgentId(), occurred_at=NOW,
            ),
            AgentTaskCompleted(
                task_id=AgentTaskId(), agent_id=AgentId(),
                result="r", occurred_at=NOW,
            ),
            AgentTaskFailed(
                task_id=AgentTaskId(), agent_id=AgentId(),
                failure_reason="f", occurred_at=NOW,
            ),
            AgentTaskCancelled(
                task_id=AgentTaskId(), agent_id=AgentId(), occurred_at=NOW,
            ),
            AgentExecutionStarted(
                execution_id=AgentExecutionId(), agent_id=AgentId(),
                task_id=AgentTaskId(), occurred_at=NOW,
            ),
            AgentExecutionCompleted(
                execution_id=AgentExecutionId(), agent_id=AgentId(),
                task_id=AgentTaskId(), result="r", occurred_at=NOW,
            ),
            AgentExecutionFailed(
                execution_id=AgentExecutionId(), agent_id=AgentId(),
                task_id=AgentTaskId(), failure_reason="f", occurred_at=NOW,
            ),
        ]
        type_strings = {
            mapper.event_to_dto(e).event_type for e in events
        }
        assert len(type_strings) == 12

    def test_unknown_event_type_raises_error(self) -> None:
        from backend.agent.application.persistence.dto import (
            AgentOutboxStorageDTO,
        )

        mapper = AgentOutboxMapperImpl()
        dto = AgentOutboxStorageDTO(
            event_id="id",
            event_type="unknown.type",
            aggregate_id="agg",
            occurred_at=NOW,
            payload=None,
            published=False,
        )
        with pytest.raises(ValueError, match="Unknown event_type"):
            mapper.dto_to_event(dto)

    def test_lifecycle_event_no_payload(self) -> None:
        mapper = AgentOutboxMapperImpl()
        event = AgentActivated(
            agent_id=AgentId(value=UUID("00000000-0000-0000-0000-000000000001")),
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.payload is None
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AgentActivated)

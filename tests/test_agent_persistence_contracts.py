from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, Union
from uuid import UUID, uuid4

import pytest

from backend.agent.application.persistence.dto import (
    AgentExecutionStorageDTO,
    AgentOutboxStorageDTO,
    AgentStorageDTO,
    AgentTaskStorageDTO,
)
from backend.agent.application.persistence.mapper import (
    AgentExecutionMapper,
    AgentMapper,
    AgentOutboxDomainEvent,
    AgentOutboxMapper,
    AgentTaskMapper,
)
from backend.agent.application.persistence.schema import (
    AGENT_EXECUTIONS_TABLE,
    AGENT_OUTBOX_TABLE,
    AGENT_TASKS_TABLE,
    AGENTS_TABLE,
    ColumnContract,
    TableContract,
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
    AgentExecutionStatus,
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
    AgentTaskStatus,
    AgentType,
    FailureReason,
)

# ===================================================================
# Constants
# ===================================================================

_NOW = datetime(2026, 6, 16, 12, 0, 0, tzinfo=timezone.utc)
_NOW2 = datetime(2026, 6, 16, 13, 0, 0, tzinfo=timezone.utc)

# ===================================================================
# Stub mapper implementations
# ===================================================================


class StubAgentMapper:
    def domain_to_dto(self, agent: Agent) -> AgentStorageDTO:
        return AgentStorageDTO(
            agent_id=str(agent.agent_id),
            agent_type=agent.agent_type.value,
            name=str(agent.name) if agent.name else None,
            status=agent.status.value,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )

    def dto_to_domain(self, dto: AgentStorageDTO) -> Agent:
        agent = Agent(
            agent_id=AgentId(value=UUID(dto.agent_id)),
            agent_type=AgentType(dto.agent_type),
            name=AgentName(value=dto.name) if dto.name else None,
            created_at=dto.created_at or _NOW,
            updated_at=dto.updated_at,
        )
        object.__setattr__(agent, "_status", AgentStatus(dto.status))
        return agent


class StubAgentTaskMapper:
    def domain_to_dto(self, task: AgentTask) -> AgentTaskStorageDTO:
        return AgentTaskStorageDTO(
            task_id=str(task.task_id),
            agent_id=str(task.agent_id) if task.agent_id else None,
            goal=str(task.goal) if task.goal else None,
            instruction=str(task.instruction) if task.instruction else None,
            status=task.status.value,
            result=str(task.result) if task.result else None,
            failure_reason=str(task.failure_reason) if task.failure_reason else None,
        )

    def dto_to_domain(self, dto: AgentTaskStorageDTO) -> AgentTask:
        task = AgentTask(
            task_id=AgentTaskId(value=UUID(dto.task_id)),
            goal=AgentGoal(value=dto.goal) if dto.goal else None,
            instruction=AgentInstruction(value=dto.instruction) if dto.instruction else None,
        )
        object.__setattr__(task, "_status", AgentTaskStatus(dto.status))
        if dto.agent_id:
            object.__setattr__(task, "_agent_id", AgentId(value=UUID(dto.agent_id)))
        if dto.result:
            object.__setattr__(task, "_result", AgentResult(value=dto.result))
        if dto.failure_reason:
            object.__setattr__(task, "_failure_reason", FailureReason(value=dto.failure_reason))
        return task


class StubAgentExecutionMapper:
    def domain_to_dto(self, execution: AgentExecution) -> AgentExecutionStorageDTO:
        return AgentExecutionStorageDTO(
            execution_id=str(execution.execution_id),
            agent_id=str(execution.agent_id) if execution.agent_id else None,
            task_id=str(execution.task_id) if execution.task_id else None,
            status=execution.status.value,
            result=str(execution.result) if execution.result else None,
            failure_reason=str(execution.failure_reason) if execution.failure_reason else None,
        )

    def dto_to_domain(self, dto: AgentExecutionStorageDTO) -> AgentExecution:
        execution = AgentExecution(
            execution_id=AgentExecutionId(value=UUID(dto.execution_id)),
            status=AgentExecutionStatus(dto.status),
        )
        if dto.agent_id:
            object.__setattr__(execution, "_agent_id", AgentId(value=UUID(dto.agent_id)))
        if dto.task_id:
            object.__setattr__(execution, "_task_id", AgentTaskId(value=UUID(dto.task_id)))
        if dto.result:
            object.__setattr__(execution, "_result", AgentResult(value=dto.result))
        if dto.failure_reason:
            object.__setattr__(execution, "_failure_reason", FailureReason(value=dto.failure_reason))
        return execution


class StubAgentOutboxMapper:
    def event_to_dto(
        self, event: AgentOutboxDomainEvent
    ) -> AgentOutboxStorageDTO:
        event_type = _get_event_type(event)
        aggregate_id = _get_aggregate_id(event)
        return AgentOutboxStorageDTO(
            event_id=str(event.event_id),
            event_type=event_type,
            aggregate_id=aggregate_id,
            occurred_at=event.occurred_at,
            payload="",
        )

    def dto_to_event(
        self, dto: AgentOutboxStorageDTO
    ) -> AgentOutboxDomainEvent:
        if dto.event_type == "agent.created":
            return AgentCreated(
                agent_id=AgentId(value=UUID(dto.aggregate_id)),
                agent_type="research", name="n", occurred_at=dto.occurred_at,
            )
        if dto.event_type == "agent.activated":
            return AgentActivated(
                agent_id=AgentId(value=UUID(dto.aggregate_id)),
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "agent.paused":
            return AgentPaused(
                agent_id=AgentId(value=UUID(dto.aggregate_id)),
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "agent.disabled":
            return AgentDisabled(
                agent_id=AgentId(value=UUID(dto.aggregate_id)),
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "agent.task_created":
            return AgentTaskCreated(
                task_id=AgentTaskId(), agent_id=AgentId(value=UUID(dto.aggregate_id)),
                goal="g", instruction="i", occurred_at=dto.occurred_at,
            )
        if dto.event_type == "agent.task_started":
            return AgentTaskStarted(
                task_id=AgentTaskId(), agent_id=AgentId(value=UUID(dto.aggregate_id)),
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "agent.task_completed":
            return AgentTaskCompleted(
                task_id=AgentTaskId(), agent_id=AgentId(value=UUID(dto.aggregate_id)),
                result="ok", occurred_at=dto.occurred_at,
            )
        if dto.event_type == "agent.task_failed":
            return AgentTaskFailed(
                task_id=AgentTaskId(), agent_id=AgentId(value=UUID(dto.aggregate_id)),
                failure_reason="err", occurred_at=dto.occurred_at,
            )
        if dto.event_type == "agent.task_cancelled":
            return AgentTaskCancelled(
                task_id=AgentTaskId(), agent_id=AgentId(value=UUID(dto.aggregate_id)),
                occurred_at=dto.occurred_at,
            )
        if dto.event_type == "agent.execution_started":
            return AgentExecutionStarted(
                execution_id=AgentExecutionId(), agent_id=AgentId(value=UUID(dto.aggregate_id)),
                task_id=AgentTaskId(), occurred_at=dto.occurred_at,
            )
        if dto.event_type == "agent.execution_completed":
            return AgentExecutionCompleted(
                execution_id=AgentExecutionId(), agent_id=AgentId(value=UUID(dto.aggregate_id)),
                task_id=AgentTaskId(), result="ok", occurred_at=dto.occurred_at,
            )
        if dto.event_type == "agent.execution_failed":
            return AgentExecutionFailed(
                execution_id=AgentExecutionId(), agent_id=AgentId(value=UUID(dto.aggregate_id)),
                task_id=AgentTaskId(), failure_reason="err", occurred_at=dto.occurred_at,
            )
        msg = f"Unknown event type: {dto.event_type}"
        raise ValueError(msg)


def _get_event_type(event: AgentOutboxDomainEvent) -> str:
    mapping = {
        AgentCreated: "agent.created",
        AgentActivated: "agent.activated",
        AgentPaused: "agent.paused",
        AgentDisabled: "agent.disabled",
        AgentTaskCreated: "agent.task_created",
        AgentTaskStarted: "agent.task_started",
        AgentTaskCompleted: "agent.task_completed",
        AgentTaskFailed: "agent.task_failed",
        AgentTaskCancelled: "agent.task_cancelled",
        AgentExecutionStarted: "agent.execution_started",
        AgentExecutionCompleted: "agent.execution_completed",
        AgentExecutionFailed: "agent.execution_failed",
    }
    for cls, name in mapping.items():
        if isinstance(event, cls):
            return name
    msg = f"Unknown event type: {type(event).__name__}"
    raise ValueError(msg)


def _get_aggregate_id(event: AgentOutboxDomainEvent) -> str:
    if isinstance(event, (AgentCreated, AgentActivated, AgentPaused, AgentDisabled)):
        return str(event.agent_id)
    if isinstance(event, (AgentTaskCreated, AgentTaskStarted, AgentTaskCompleted,
                          AgentTaskFailed, AgentTaskCancelled)):
        return str(event.agent_id)
    if isinstance(event, (AgentExecutionStarted, AgentExecutionCompleted, AgentExecutionFailed)):
        return str(event.agent_id)
    msg = f"Unknown event type: {type(event).__name__}"
    raise ValueError(msg)


# ===================================================================
# DTO: AgentStorageDTO
# ===================================================================


class TestAgentStorageDTO:
    def test_creation_with_all_fields(self) -> None:
        dto = AgentStorageDTO(
            agent_id="agent-1",
            agent_type="research",
            name="test-agent",
            status="active",
            created_at=_NOW,
            updated_at=_NOW2,
        )
        assert dto.agent_id == "agent-1"
        assert dto.agent_type == "research"
        assert dto.name == "test-agent"
        assert dto.status == "active"
        assert dto.created_at == _NOW
        assert dto.updated_at == _NOW2

    def test_creation_with_defaults(self) -> None:
        dto = AgentStorageDTO(agent_id="agent-1")
        assert dto.agent_type == "coordinator"
        assert dto.status == "idle"
        assert dto.name is None
        assert dto.created_at is None
        assert dto.updated_at is None

    def test_immutability(self) -> None:
        dto = AgentStorageDTO(agent_id="agent-1")
        with pytest.raises(AttributeError):
            dto.agent_id = "changed"  # type: ignore[misc]

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(AgentStorageDTO)
        assert len(fields) == 6

    def test_nullable_fields(self) -> None:
        dto = AgentStorageDTO(agent_id="agent-1")
        nullable = {"name", "created_at", "updated_at"}
        for field_name in nullable:
            assert getattr(dto, field_name) is None

    def test_non_nullable_fields(self) -> None:
        dto = AgentStorageDTO(agent_id="agent-1")
        assert dto.agent_id == "agent-1"
        assert dto.agent_type == "coordinator"
        assert dto.status == "idle"

    def test_agent_id_type(self) -> None:
        dto = AgentStorageDTO(agent_id="agent-1")
        assert isinstance(dto.agent_id, str)

    def test_agent_type_type(self) -> None:
        dto = AgentStorageDTO(agent_id="agent-1")
        assert isinstance(dto.agent_type, str)

    def test_status_type(self) -> None:
        dto = AgentStorageDTO(agent_id="agent-1")
        assert isinstance(dto.status, str)

    def test_name_none_by_default(self) -> None:
        dto = AgentStorageDTO(agent_id="agent-1")
        assert dto.name is None

    def test_name_with_value(self) -> None:
        dto = AgentStorageDTO(agent_id="agent-1", name="custom")
        assert dto.name == "custom"

    def test_agent_type_custom(self) -> None:
        dto = AgentStorageDTO(agent_id="agent-1", agent_type="automation")
        assert dto.agent_type == "automation"

    def test_status_custom(self) -> None:
        dto = AgentStorageDTO(agent_id="agent-1", status="disabled")
        assert dto.status == "disabled"

    def test_created_at_none_by_default(self) -> None:
        dto = AgentStorageDTO(agent_id="agent-1")
        assert dto.created_at is None

    def test_updated_at_none_by_default(self) -> None:
        dto = AgentStorageDTO(agent_id="agent-1")
        assert dto.updated_at is None


# ===================================================================
# DTO: AgentTaskStorageDTO
# ===================================================================


class TestAgentTaskStorageDTO:
    def test_creation_with_all_fields(self) -> None:
        dto = AgentTaskStorageDTO(
            task_id="task-1",
            agent_id="agent-1",
            goal="test goal",
            instruction="do something",
            status="running",
            result="done",
            failure_reason=None,
        )
        assert dto.task_id == "task-1"
        assert dto.agent_id == "agent-1"
        assert dto.goal == "test goal"
        assert dto.instruction == "do something"
        assert dto.status == "running"
        assert dto.result == "done"
        assert dto.failure_reason is None

    def test_creation_with_defaults(self) -> None:
        dto = AgentTaskStorageDTO(task_id="task-1")
        assert dto.status == "pending"
        assert dto.agent_id is None
        assert dto.goal is None
        assert dto.instruction is None
        assert dto.result is None
        assert dto.failure_reason is None

    def test_immutability(self) -> None:
        dto = AgentTaskStorageDTO(task_id="task-1")
        with pytest.raises(AttributeError):
            dto.task_id = "changed"  # type: ignore[misc]

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(AgentTaskStorageDTO)
        assert len(fields) == 7

    def test_nullable_fields(self) -> None:
        dto = AgentTaskStorageDTO(task_id="task-1")
        nullable = {"agent_id", "goal", "instruction", "result", "failure_reason"}
        for field_name in nullable:
            assert getattr(dto, field_name) is None

    def test_non_nullable_fields(self) -> None:
        dto = AgentTaskStorageDTO(task_id="task-1")
        assert dto.task_id == "task-1"
        assert dto.status == "pending"

    def test_task_id_type(self) -> None:
        dto = AgentTaskStorageDTO(task_id="task-1")
        assert isinstance(dto.task_id, str)

    def test_status_type(self) -> None:
        dto = AgentTaskStorageDTO(task_id="task-1")
        assert isinstance(dto.status, str)

    def test_goal_stores_string(self) -> None:
        dto = AgentTaskStorageDTO(task_id="task-1", goal="my goal")
        assert dto.goal == "my goal"

    def test_instruction_stores_string(self) -> None:
        dto = AgentTaskStorageDTO(task_id="task-1", instruction="my instruction")
        assert dto.instruction == "my instruction"

    def test_result_stores_string(self) -> None:
        dto = AgentTaskStorageDTO(task_id="task-1", result="completed successfully")
        assert dto.result == "completed successfully"

    def test_failure_reason_stores_string(self) -> None:
        dto = AgentTaskStorageDTO(task_id="task-1", failure_reason="something failed")
        assert dto.failure_reason == "something failed"

    def test_agent_id_stores_string(self) -> None:
        dto = AgentTaskStorageDTO(task_id="task-1", agent_id="agent-42")
        assert dto.agent_id == "agent-42"

    def test_status_custom(self) -> None:
        dto = AgentTaskStorageDTO(task_id="task-1", status="completed")
        assert dto.status == "completed"


# ===================================================================
# DTO: AgentExecutionStorageDTO
# ===================================================================


class TestAgentExecutionStorageDTO:
    def test_creation_with_all_fields(self) -> None:
        dto = AgentExecutionStorageDTO(
            execution_id="exec-1",
            agent_id="agent-1",
            task_id="task-1",
            status="executing",
            result="done",
            failure_reason=None,
        )
        assert dto.execution_id == "exec-1"
        assert dto.agent_id == "agent-1"
        assert dto.task_id == "task-1"
        assert dto.status == "executing"
        assert dto.result == "done"
        assert dto.failure_reason is None

    def test_creation_with_defaults(self) -> None:
        dto = AgentExecutionStorageDTO(execution_id="exec-1")
        assert dto.status == "pending"
        assert dto.agent_id is None
        assert dto.task_id is None
        assert dto.result is None
        assert dto.failure_reason is None

    def test_immutability(self) -> None:
        dto = AgentExecutionStorageDTO(execution_id="exec-1")
        with pytest.raises(AttributeError):
            dto.execution_id = "changed"  # type: ignore[misc]

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(AgentExecutionStorageDTO)
        assert len(fields) == 6

    def test_nullable_fields(self) -> None:
        dto = AgentExecutionStorageDTO(execution_id="exec-1")
        nullable = {"agent_id", "task_id", "result", "failure_reason"}
        for field_name in nullable:
            assert getattr(dto, field_name) is None

    def test_non_nullable_fields(self) -> None:
        dto = AgentExecutionStorageDTO(execution_id="exec-1")
        assert dto.execution_id == "exec-1"
        assert dto.status == "pending"

    def test_execution_id_type(self) -> None:
        dto = AgentExecutionStorageDTO(execution_id="exec-1")
        assert isinstance(dto.execution_id, str)

    def test_status_type(self) -> None:
        dto = AgentExecutionStorageDTO(execution_id="exec-1")
        assert isinstance(dto.status, str)

    def test_result_stores_string(self) -> None:
        dto = AgentExecutionStorageDTO(execution_id="exec-1", result="done")
        assert dto.result == "done"

    def test_failure_reason_stores_string(self) -> None:
        dto = AgentExecutionStorageDTO(execution_id="exec-1", failure_reason="err")
        assert dto.failure_reason == "err"

    def test_status_custom(self) -> None:
        dto = AgentExecutionStorageDTO(execution_id="exec-1", status="completed")
        assert dto.status == "completed"


# ===================================================================
# DTO: AgentOutboxStorageDTO
# ===================================================================


class TestAgentOutboxStorageDTO:
    def test_creation_with_all_fields(self) -> None:
        dto = AgentOutboxStorageDTO(
            event_id="evt-1",
            event_type="agent.created",
            aggregate_id="agent-1",
            occurred_at=_NOW,
            payload='{"key": "val"}',
            published=True,
        )
        assert dto.event_id == "evt-1"
        assert dto.event_type == "agent.created"
        assert dto.aggregate_id == "agent-1"
        assert dto.occurred_at == _NOW
        assert dto.payload == '{"key": "val"}'
        assert dto.published is True

    def test_creation_with_defaults(self) -> None:
        dto = AgentOutboxStorageDTO(
            event_id="evt-1",
            event_type="agent.created",
            aggregate_id="agent-1",
            occurred_at=_NOW,
        )
        assert dto.payload is None
        assert dto.published is False

    def test_immutability(self) -> None:
        dto = AgentOutboxStorageDTO(
            event_id="evt-1",
            event_type="t",
            aggregate_id="a",
            occurred_at=_NOW,
        )
        with pytest.raises(AttributeError):
            dto.event_id = "changed"  # type: ignore[misc]

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(AgentOutboxStorageDTO)
        assert len(fields) == 6

    def test_nullable_fields(self) -> None:
        dto = AgentOutboxStorageDTO(
            event_id="evt-1",
            event_type="t",
            aggregate_id="a",
            occurred_at=_NOW,
        )
        assert dto.payload is None

    def test_non_nullable_fields(self) -> None:
        dto = AgentOutboxStorageDTO(
            event_id="evt-1",
            event_type="t",
            aggregate_id="a",
            occurred_at=_NOW,
        )
        assert dto.event_id == "evt-1"
        assert dto.event_type == "t"
        assert dto.aggregate_id == "a"
        assert dto.occurred_at == _NOW
        assert dto.published is False

    def test_event_id_type(self) -> None:
        dto = AgentOutboxStorageDTO(
            event_id="evt-1", event_type="t", aggregate_id="a",
            occurred_at=_NOW,
        )
        assert isinstance(dto.event_id, str)

    def test_published_type(self) -> None:
        dto = AgentOutboxStorageDTO(
            event_id="evt-1", event_type="t", aggregate_id="a",
            occurred_at=_NOW, published=True,
        )
        assert isinstance(dto.published, bool)

    def test_event_type_type(self) -> None:
        dto = AgentOutboxStorageDTO(
            event_id="evt-1", event_type="t", aggregate_id="a",
            occurred_at=_NOW,
        )
        assert isinstance(dto.event_type, str)

    def test_aggregate_id_type(self) -> None:
        dto = AgentOutboxStorageDTO(
            event_id="evt-1", event_type="t", aggregate_id="a",
            occurred_at=_NOW,
        )
        assert isinstance(dto.aggregate_id, str)

    def test_occurred_at_type(self) -> None:
        dto = AgentOutboxStorageDTO(
            event_id="evt-1", event_type="t", aggregate_id="a",
            occurred_at=_NOW,
        )
        assert isinstance(dto.occurred_at, datetime)


# ===================================================================
# Mapper: AgentMapper
# ===================================================================


class TestAgentMapper:
    def test_domain_to_dto(self) -> None:
        agent = Agent(
            agent_id=AgentId(),
            agent_type=AgentType.RESEARCH,
            name=AgentName(value="test"),
            created_at=_NOW,
            updated_at=_NOW2,
        )
        mapper = StubAgentMapper()
        dto = mapper.domain_to_dto(agent)
        assert dto.agent_id == str(agent.agent_id)
        assert dto.agent_type == "research"
        assert dto.name == "test"
        assert dto.status == "idle"
        assert dto.created_at == _NOW
        assert dto.updated_at == _NOW2

    def test_domain_to_dto_with_nulls(self) -> None:
        agent = Agent(agent_id=AgentId())
        mapper = StubAgentMapper()
        dto = mapper.domain_to_dto(agent)
        assert dto.name is None
        assert dto.updated_at is None

    def test_dto_to_domain(self) -> None:
        dto = AgentStorageDTO(
            agent_id=str(UUID(int=42)),
            agent_type="research",
            name="test-agent",
            status="active",
            created_at=_NOW,
            updated_at=_NOW2,
        )
        mapper = StubAgentMapper()
        agent = mapper.dto_to_domain(dto)
        assert str(agent.agent_id) == dto.agent_id
        assert agent.agent_type == AgentType.RESEARCH
        assert agent.name is not None
        assert agent.name.value == "test-agent"
        assert agent.status == AgentStatus.ACTIVE
        assert agent.created_at == _NOW
        assert agent.updated_at == _NOW2

    def test_dto_to_domain_with_nulls(self) -> None:
        dto = AgentStorageDTO(agent_id=str(UUID(int=1)))
        mapper = StubAgentMapper()
        agent = mapper.dto_to_domain(dto)
        assert agent.name is None
        assert agent.updated_at is None

    def test_roundtrip(self) -> None:
        original = Agent(
            agent_id=AgentId(),
            agent_type=AgentType.RESEARCH,
            name=AgentName(value="test"),
            created_at=_NOW,
            updated_at=_NOW2,
        )
        mapper = StubAgentMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert str(restored.agent_id) == str(original.agent_id)
        assert restored.agent_type == original.agent_type
        assert restored.name is not None and original.name is not None
        assert restored.name.value == original.name.value
        assert restored.created_at == original.created_at
        assert restored.updated_at == original.updated_at

    def test_roundtrip_with_different_status(self) -> None:
        original = Agent(agent_id=AgentId())
        original.activate()
        mapper = StubAgentMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert restored.status == AgentStatus.ACTIVE

    def test_mapper_has_required_methods(self) -> None:
        mapper = StubAgentMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


# ===================================================================
# Mapper: AgentTaskMapper
# ===================================================================


class TestAgentTaskMapper:
    def test_domain_to_dto(self) -> None:
        task = AgentTask(
            task_id=AgentTaskId(),
            goal=AgentGoal(value="my goal"),
            instruction=AgentInstruction(value="my instruction"),
        )
        mapper = StubAgentTaskMapper()
        dto = mapper.domain_to_dto(task)
        assert dto.task_id == str(task.task_id)
        assert dto.goal == "my goal"
        assert dto.instruction == "my instruction"
        assert dto.status == "pending"
        assert dto.result is None
        assert dto.failure_reason is None

    def test_domain_to_dto_with_nulls(self) -> None:
        task = AgentTask(task_id=AgentTaskId())
        mapper = StubAgentTaskMapper()
        dto = mapper.domain_to_dto(task)
        assert dto.goal is None
        assert dto.instruction is None
        assert dto.agent_id is None

    def test_dto_to_domain(self) -> None:
        dto = AgentTaskStorageDTO(
            task_id=str(UUID(int=42)),
            agent_id=str(UUID(int=1)),
            goal="goal",
            instruction="instr",
            status="running",
        )
        mapper = StubAgentTaskMapper()
        task = mapper.dto_to_domain(dto)
        assert str(task.task_id) == dto.task_id
        assert task.goal is not None
        assert task.goal.value == "goal"
        assert task.instruction is not None
        assert task.instruction.value == "instr"
        assert task.status == AgentTaskStatus.RUNNING

    def test_dto_to_domain_with_nulls(self) -> None:
        dto = AgentTaskStorageDTO(task_id=str(UUID(int=1)))
        mapper = StubAgentTaskMapper()
        task = mapper.dto_to_domain(dto)
        assert task.goal is None
        assert task.instruction is None

    def test_roundtrip(self) -> None:
        original = AgentTask(
            task_id=AgentTaskId(),
            goal=AgentGoal(value="goal"),
            instruction=AgentInstruction(value="instr"),
        )
        mapper = StubAgentTaskMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert str(restored.task_id) == str(original.task_id)
        assert restored.goal is not None and original.goal is not None
        assert restored.goal.value == original.goal.value
        assert restored.instruction is not None and original.instruction is not None
        assert restored.instruction.value == original.instruction.value

    def test_roundtrip_with_completed_status(self) -> None:
        original = AgentTask(task_id=AgentTaskId())
        original.start()
        original.complete(AgentResult(value="done"))
        mapper = StubAgentTaskMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert restored.status == AgentTaskStatus.COMPLETED
        assert restored.result is not None
        assert restored.result.value == "done"

    def test_mapper_has_required_methods(self) -> None:
        mapper = StubAgentTaskMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


# ===================================================================
# Mapper: AgentExecutionMapper
# ===================================================================


class TestAgentExecutionMapper:
    def test_domain_to_dto(self) -> None:
        execution = AgentExecution(
            execution_id=AgentExecutionId(),
            agent_id=AgentId(),
            task_id=AgentTaskId(),
        )
        mapper = StubAgentExecutionMapper()
        dto = mapper.domain_to_dto(execution)
        assert dto.execution_id == str(execution.execution_id)
        assert dto.agent_id == str(execution.agent_id)
        assert dto.task_id == str(execution.task_id)
        assert dto.status == "pending"
        assert dto.result is None
        assert dto.failure_reason is None

    def test_domain_to_dto_with_nulls(self) -> None:
        execution = AgentExecution(execution_id=AgentExecutionId())
        mapper = StubAgentExecutionMapper()
        dto = mapper.domain_to_dto(execution)
        assert dto.agent_id is None
        assert dto.result is None

    def test_dto_to_domain(self) -> None:
        dto = AgentExecutionStorageDTO(
            execution_id=str(UUID(int=42)),
            agent_id=str(UUID(int=1)),
            task_id=str(UUID(int=2)),
            status="executing",
        )
        mapper = StubAgentExecutionMapper()
        execution = mapper.dto_to_domain(dto)
        assert str(execution.execution_id) == dto.execution_id
        assert str(execution.agent_id) == dto.agent_id
        assert str(execution.task_id) == dto.task_id
        assert execution.status == AgentExecutionStatus.EXECUTING

    def test_dto_to_domain_with_nulls(self) -> None:
        dto = AgentExecutionStorageDTO(execution_id=str(UUID(int=1)))
        mapper = StubAgentExecutionMapper()
        execution = mapper.dto_to_domain(dto)
        assert execution.agent_id is None

    def test_roundtrip(self) -> None:
        original = AgentExecution(
            execution_id=AgentExecutionId(),
            agent_id=AgentId(),
            task_id=AgentTaskId(),
        )
        mapper = StubAgentExecutionMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert str(restored.execution_id) == str(original.execution_id)
        assert str(restored.agent_id) == str(original.agent_id)
        assert str(restored.task_id) == str(original.task_id)

    def test_roundtrip_with_completed_status(self) -> None:
        original = AgentExecution(execution_id=AgentExecutionId())
        original.start()
        original.complete(AgentResult(value="done"))
        mapper = StubAgentExecutionMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert restored.status == AgentExecutionStatus.COMPLETED
        assert restored.result is not None
        assert restored.result.value == "done"

    def test_mapper_has_required_methods(self) -> None:
        mapper = StubAgentExecutionMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


# ===================================================================
# Mapper: AgentOutboxMapper
# ===================================================================


class TestAgentOutboxMapper:
    def test_event_to_dto(self) -> None:
        event = AgentCreated(
            agent_id=AgentId(),
            agent_type="research",
            name="test",
            occurred_at=_NOW,
        )
        mapper = StubAgentOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_id == str(event.event_id)
        assert dto.event_type == "agent.created"
        assert dto.occurred_at == _NOW

    def test_dto_to_event(self) -> None:
        dto = AgentOutboxStorageDTO(
            event_id=str(UUID(int=1)),
            event_type="agent.activated",
            aggregate_id=str(UUID(int=42)),
            occurred_at=_NOW,
        )
        mapper = StubAgentOutboxMapper()
        event = mapper.dto_to_event(dto)
        assert isinstance(event, AgentActivated)
        assert str(event.agent_id) == dto.aggregate_id
        assert event.occurred_at == _NOW

    def test_roundtrip_agent_created(self) -> None:
        event: AgentOutboxDomainEvent = AgentCreated(
            agent_id=AgentId(), agent_type="research", name="n",
            occurred_at=_NOW,
        )
        mapper = StubAgentOutboxMapper()
        dto = mapper.event_to_dto(event)
        restored = mapper.dto_to_event(dto)
        assert type(restored) == type(event)

    def test_roundtrip_agent_activated(self) -> None:
        event: AgentOutboxDomainEvent = AgentActivated(
            agent_id=AgentId(), occurred_at=_NOW,
        )
        mapper = StubAgentOutboxMapper()
        dto = mapper.event_to_dto(event)
        restored = mapper.dto_to_event(dto)
        assert type(restored) == type(event)

    def test_roundtrip_agent_paused(self) -> None:
        event: AgentOutboxDomainEvent = AgentPaused(
            agent_id=AgentId(), occurred_at=_NOW,
        )
        mapper = StubAgentOutboxMapper()
        dto = mapper.event_to_dto(event)
        restored = mapper.dto_to_event(dto)
        assert type(restored) == type(event)

    def test_roundtrip_agent_disabled(self) -> None:
        event: AgentOutboxDomainEvent = AgentDisabled(
            agent_id=AgentId(), occurred_at=_NOW,
        )
        mapper = StubAgentOutboxMapper()
        dto = mapper.event_to_dto(event)
        restored = mapper.dto_to_event(dto)
        assert type(restored) == type(event)

    def test_roundtrip_agent_task_created(self) -> None:
        event: AgentOutboxDomainEvent = AgentTaskCreated(
            task_id=AgentTaskId(), agent_id=AgentId(), goal="g",
            instruction="i", occurred_at=_NOW,
        )
        mapper = StubAgentOutboxMapper()
        dto = mapper.event_to_dto(event)
        restored = mapper.dto_to_event(dto)
        assert type(restored) == type(event)

    def test_roundtrip_all_event_types(self) -> None:
        mapper = StubAgentOutboxMapper()
        agent_id = AgentId()
        events: list[AgentOutboxDomainEvent] = [
            AgentCreated(agent_id=AgentId(), agent_type="research", name="n",
                         occurred_at=_NOW),
            AgentActivated(agent_id=AgentId(), occurred_at=_NOW),
            AgentPaused(agent_id=AgentId(), occurred_at=_NOW),
            AgentDisabled(agent_id=AgentId(), occurred_at=_NOW),
            AgentTaskCreated(task_id=AgentTaskId(), agent_id=AgentId(), goal="g",
                             instruction="i", occurred_at=_NOW),
            AgentTaskStarted(task_id=AgentTaskId(), agent_id=AgentId(),
                             occurred_at=_NOW),
            AgentTaskCompleted(task_id=AgentTaskId(), agent_id=AgentId(),
                               result="ok", occurred_at=_NOW),
            AgentTaskFailed(task_id=AgentTaskId(), agent_id=AgentId(),
                            failure_reason="err", occurred_at=_NOW),
            AgentTaskCancelled(task_id=AgentTaskId(), agent_id=AgentId(),
                               occurred_at=_NOW),
            AgentExecutionStarted(execution_id=AgentExecutionId(), agent_id=AgentId(),
                                  task_id=AgentTaskId(), occurred_at=_NOW),
            AgentExecutionCompleted(execution_id=AgentExecutionId(), agent_id=AgentId(),
                                    task_id=AgentTaskId(), result="ok",
                                    occurred_at=_NOW),
            AgentExecutionFailed(execution_id=AgentExecutionId(), agent_id=AgentId(),
                                  task_id=AgentTaskId(), failure_reason="err",
                                  occurred_at=_NOW),
        ]
        for event in events:
            dto = mapper.event_to_dto(event)
            restored = mapper.dto_to_event(dto)
            assert type(restored) == type(event)

    def test_mapper_has_required_methods(self) -> None:
        mapper = StubAgentOutboxMapper()
        assert hasattr(mapper, "event_to_dto")
        assert hasattr(mapper, "dto_to_event")


# ===================================================================
# Schema: AGENTS_TABLE
# ===================================================================


class TestAgentsTable:
    def test_name(self) -> None:
        assert AGENTS_TABLE.name == "agents"

    def test_schema(self) -> None:
        assert AGENTS_TABLE.schema == "agent"

    def test_primary_key(self) -> None:
        assert AGENTS_TABLE.primary_key == "agent_id"

    def test_column_count(self) -> None:
        assert len(AGENTS_TABLE.columns) == 6

    def test_column_names(self) -> None:
        names = [c.name for c in AGENTS_TABLE.columns]
        assert names == [
            "agent_id", "agent_type", "name", "status",
            "created_at", "updated_at",
        ]

    def test_agent_type_enum_values(self) -> None:
        col = _find_column(AGENTS_TABLE, "agent_type")
        assert col is not None
        assert col.enum_values == (
            "coordinator", "research", "knowledge", "automation",
        )

    def test_status_enum_values(self) -> None:
        col = _find_column(AGENTS_TABLE, "status")
        assert col is not None
        assert col.enum_values == (
            "idle", "active", "paused", "disabled",
        )

    def test_agent_id_not_nullable(self) -> None:
        col = _find_column(AGENTS_TABLE, "agent_id")
        assert col is not None
        assert col.nullable is False

    def test_agent_type_not_nullable(self) -> None:
        col = _find_column(AGENTS_TABLE, "agent_type")
        assert col is not None
        assert col.nullable is False

    def test_status_not_nullable(self) -> None:
        col = _find_column(AGENTS_TABLE, "status")
        assert col is not None
        assert col.nullable is False

    def test_created_at_not_nullable(self) -> None:
        col = _find_column(AGENTS_TABLE, "created_at")
        assert col is not None
        assert col.nullable is False

    def test_nullable_columns(self) -> None:
        nullable = {"name", "updated_at"}
        for name in nullable:
            col = _find_column(AGENTS_TABLE, name)
            assert col is not None
            assert col.nullable is True

    def test_indexes(self) -> None:
        assert "ix_agents_status" in AGENTS_TABLE.indexes
        assert "ix_agents_agent_type" in AGENTS_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(AGENTS_TABLE.indexes) == 2

    def test_status_max_length(self) -> None:
        col = _find_column(AGENTS_TABLE, "status")
        assert col is not None
        assert col.max_length == 16

    def test_agent_type_max_length(self) -> None:
        col = _find_column(AGENTS_TABLE, "agent_type")
        assert col is not None
        assert col.max_length == 16

    def test_agent_id_type(self) -> None:
        col = _find_column(AGENTS_TABLE, "agent_id")
        assert col is not None
        assert col.py_type == str

    def test_created_at_type(self) -> None:
        col = _find_column(AGENTS_TABLE, "created_at")
        assert col is not None
        assert col.py_type == datetime

    def test_updated_at_type(self) -> None:
        col = _find_column(AGENTS_TABLE, "updated_at")
        assert col is not None
        assert col.py_type == datetime

    def test_name_type(self) -> None:
        col = _find_column(AGENTS_TABLE, "name")
        assert col is not None
        assert col.py_type == str

    def test_agent_type_type(self) -> None:
        col = _find_column(AGENTS_TABLE, "agent_type")
        assert col is not None
        assert col.py_type == str


# ===================================================================
# Schema: AGENT_TASKS_TABLE
# ===================================================================


class TestAgentTasksTable:
    def test_name(self) -> None:
        assert AGENT_TASKS_TABLE.name == "agent_tasks"

    def test_schema(self) -> None:
        assert AGENT_TASKS_TABLE.schema == "agent"

    def test_primary_key(self) -> None:
        assert AGENT_TASKS_TABLE.primary_key == "task_id"

    def test_column_count(self) -> None:
        assert len(AGENT_TASKS_TABLE.columns) == 7

    def test_column_names(self) -> None:
        names = [c.name for c in AGENT_TASKS_TABLE.columns]
        assert names == [
            "task_id", "agent_id", "goal", "instruction", "status",
            "result", "failure_reason",
        ]

    def test_status_enum_values(self) -> None:
        col = _find_column(AGENT_TASKS_TABLE, "status")
        assert col is not None
        assert col.enum_values == (
            "pending", "running", "completed", "failed", "cancelled",
        )

    def test_task_id_not_nullable(self) -> None:
        col = _find_column(AGENT_TASKS_TABLE, "task_id")
        assert col is not None
        assert col.nullable is False

    def test_status_not_nullable(self) -> None:
        col = _find_column(AGENT_TASKS_TABLE, "status")
        assert col is not None
        assert col.nullable is False

    def test_nullable_columns(self) -> None:
        nullable = {"agent_id", "goal", "instruction", "result", "failure_reason"}
        for name in nullable:
            col = _find_column(AGENT_TASKS_TABLE, name)
            assert col is not None
            assert col.nullable is True

    def test_indexes(self) -> None:
        assert "ix_agent_tasks_agent_id" in AGENT_TASKS_TABLE.indexes
        assert "ix_agent_tasks_status" in AGENT_TASKS_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(AGENT_TASKS_TABLE.indexes) == 2

    def test_status_max_length(self) -> None:
        col = _find_column(AGENT_TASKS_TABLE, "status")
        assert col is not None
        assert col.max_length == 16

    def test_task_id_type(self) -> None:
        col = _find_column(AGENT_TASKS_TABLE, "task_id")
        assert col is not None
        assert col.py_type == str

    def test_agent_id_type(self) -> None:
        col = _find_column(AGENT_TASKS_TABLE, "agent_id")
        assert col is not None
        assert col.py_type == str

    def test_goal_type(self) -> None:
        col = _find_column(AGENT_TASKS_TABLE, "goal")
        assert col is not None
        assert col.py_type == str

    def test_instruction_type(self) -> None:
        col = _find_column(AGENT_TASKS_TABLE, "instruction")
        assert col is not None
        assert col.py_type == str

    def test_result_type(self) -> None:
        col = _find_column(AGENT_TASKS_TABLE, "result")
        assert col is not None
        assert col.py_type == str

    def test_failure_reason_type(self) -> None:
        col = _find_column(AGENT_TASKS_TABLE, "failure_reason")
        assert col is not None
        assert col.py_type == str


# ===================================================================
# Schema: AGENT_EXECUTIONS_TABLE
# ===================================================================


class TestAgentExecutionsTable:
    def test_name(self) -> None:
        assert AGENT_EXECUTIONS_TABLE.name == "agent_executions"

    def test_schema(self) -> None:
        assert AGENT_EXECUTIONS_TABLE.schema == "agent"

    def test_primary_key(self) -> None:
        assert AGENT_EXECUTIONS_TABLE.primary_key == "execution_id"

    def test_column_count(self) -> None:
        assert len(AGENT_EXECUTIONS_TABLE.columns) == 6

    def test_column_names(self) -> None:
        names = [c.name for c in AGENT_EXECUTIONS_TABLE.columns]
        assert names == [
            "execution_id", "agent_id", "task_id", "status",
            "result", "failure_reason",
        ]

    def test_status_enum_values(self) -> None:
        col = _find_column(AGENT_EXECUTIONS_TABLE, "status")
        assert col is not None
        assert col.enum_values == (
            "pending", "executing", "completed", "failed",
        )

    def test_execution_id_not_nullable(self) -> None:
        col = _find_column(AGENT_EXECUTIONS_TABLE, "execution_id")
        assert col is not None
        assert col.nullable is False

    def test_status_not_nullable(self) -> None:
        col = _find_column(AGENT_EXECUTIONS_TABLE, "status")
        assert col is not None
        assert col.nullable is False

    def test_nullable_columns(self) -> None:
        nullable = {"agent_id", "task_id", "result", "failure_reason"}
        for name in nullable:
            col = _find_column(AGENT_EXECUTIONS_TABLE, name)
            assert col is not None
            assert col.nullable is True

    def test_indexes(self) -> None:
        assert "ix_agent_executions_agent_id" in AGENT_EXECUTIONS_TABLE.indexes
        assert "ix_agent_executions_task_id" in AGENT_EXECUTIONS_TABLE.indexes
        assert "ix_agent_executions_status" in AGENT_EXECUTIONS_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(AGENT_EXECUTIONS_TABLE.indexes) == 3

    def test_status_max_length(self) -> None:
        col = _find_column(AGENT_EXECUTIONS_TABLE, "status")
        assert col is not None
        assert col.max_length == 16

    def test_execution_id_type(self) -> None:
        col = _find_column(AGENT_EXECUTIONS_TABLE, "execution_id")
        assert col is not None
        assert col.py_type == str

    def test_agent_id_type(self) -> None:
        col = _find_column(AGENT_EXECUTIONS_TABLE, "agent_id")
        assert col is not None
        assert col.py_type == str

    def test_task_id_type(self) -> None:
        col = _find_column(AGENT_EXECUTIONS_TABLE, "task_id")
        assert col is not None
        assert col.py_type == str

    def test_result_type(self) -> None:
        col = _find_column(AGENT_EXECUTIONS_TABLE, "result")
        assert col is not None
        assert col.py_type == str

    def test_failure_reason_type(self) -> None:
        col = _find_column(AGENT_EXECUTIONS_TABLE, "failure_reason")
        assert col is not None
        assert col.py_type == str


# ===================================================================
# Schema: AGENT_OUTBOX_TABLE
# ===================================================================


class TestAgentOutboxTable:
    def test_name(self) -> None:
        assert AGENT_OUTBOX_TABLE.name == "agent_outbox"

    def test_schema(self) -> None:
        assert AGENT_OUTBOX_TABLE.schema == "agent"

    def test_primary_key(self) -> None:
        assert AGENT_OUTBOX_TABLE.primary_key == "event_id"

    def test_column_count(self) -> None:
        assert len(AGENT_OUTBOX_TABLE.columns) == 6

    def test_column_names(self) -> None:
        names = [c.name for c in AGENT_OUTBOX_TABLE.columns]
        assert names == [
            "event_id", "event_type", "aggregate_id", "occurred_at",
            "payload", "published",
        ]

    def test_event_type_enum_values(self) -> None:
        col = _find_column(AGENT_OUTBOX_TABLE, "event_type")
        assert col is not None
        assert col.enum_values == (
            "agent.created", "agent.activated", "agent.paused",
            "agent.disabled", "agent.task_created", "agent.task_started",
            "agent.task_completed", "agent.task_failed",
            "agent.task_cancelled", "agent.execution_started",
            "agent.execution_completed", "agent.execution_failed",
        )

    def test_event_type_count(self) -> None:
        col = _find_column(AGENT_OUTBOX_TABLE, "event_type")
        assert col is not None
        assert len(col.enum_values) == 12

    def test_not_nullable_columns(self) -> None:
        for name in ("event_id", "event_type", "aggregate_id", "occurred_at", "published"):
            col = _find_column(AGENT_OUTBOX_TABLE, name)
            assert col is not None
            assert col.nullable is False

    def test_payload_nullable(self) -> None:
        col = _find_column(AGENT_OUTBOX_TABLE, "payload")
        assert col is not None
        assert col.nullable is True

    def test_indexes(self) -> None:
        assert "ix_agent_outbox_unpublished" in AGENT_OUTBOX_TABLE.indexes
        assert "ix_agent_outbox_aggregate" in AGENT_OUTBOX_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(AGENT_OUTBOX_TABLE.indexes) == 2

    def test_event_type_max_length(self) -> None:
        col = _find_column(AGENT_OUTBOX_TABLE, "event_type")
        assert col is not None
        assert col.max_length == 32

    def test_event_id_type(self) -> None:
        col = _find_column(AGENT_OUTBOX_TABLE, "event_id")
        assert col is not None
        assert col.py_type == str

    def test_published_type(self) -> None:
        col = _find_column(AGENT_OUTBOX_TABLE, "published")
        assert col is not None
        assert col.py_type == bool

    def test_aggregate_id_type(self) -> None:
        col = _find_column(AGENT_OUTBOX_TABLE, "aggregate_id")
        assert col is not None
        assert col.py_type == str

    def test_occurred_at_type(self) -> None:
        col = _find_column(AGENT_OUTBOX_TABLE, "occurred_at")
        assert col is not None
        assert col.py_type == datetime

    def test_payload_type(self) -> None:
        col = _find_column(AGENT_OUTBOX_TABLE, "payload")
        assert col is not None
        assert col.py_type == str


# ===================================================================
# Alignment: DTO fields ↔ Schema columns
# ===================================================================


class TestDTOAlignment:
    def test_agent_dto_aligns_with_schema(self) -> None:
        dto_fields = _dto_field_names(AgentStorageDTO)
        schema_fields = [c.name for c in AGENTS_TABLE.columns]
        assert dto_fields == schema_fields

    def test_task_dto_aligns_with_schema(self) -> None:
        dto_fields = _dto_field_names(AgentTaskStorageDTO)
        schema_fields = [c.name for c in AGENT_TASKS_TABLE.columns]
        assert dto_fields == schema_fields

    def test_execution_dto_aligns_with_schema(self) -> None:
        dto_fields = _dto_field_names(AgentExecutionStorageDTO)
        schema_fields = [c.name for c in AGENT_EXECUTIONS_TABLE.columns]
        assert dto_fields == schema_fields

    def test_outbox_dto_aligns_with_schema(self) -> None:
        dto_fields = _dto_field_names(AgentOutboxStorageDTO)
        schema_fields = [c.name for c in AGENT_OUTBOX_TABLE.columns]
        assert dto_fields == schema_fields


# ===================================================================
# Alignment: Schema ↔ Domain Enums
# ===================================================================


class TestSchemaEnumAlignment:
    def test_agent_type_enum_matches_domain(self) -> None:
        col = _find_column(AGENTS_TABLE, "agent_type")
        assert col is not None
        expected = tuple(m.value for m in AgentType)
        assert col.enum_values == expected

    def test_agent_status_enum_matches_domain(self) -> None:
        col = _find_column(AGENTS_TABLE, "status")
        assert col is not None
        expected = tuple(m.value for m in AgentStatus)
        assert col.enum_values == expected

    def test_task_status_enum_matches_domain(self) -> None:
        col = _find_column(AGENT_TASKS_TABLE, "status")
        assert col is not None
        expected = tuple(m.value for m in AgentTaskStatus)
        assert col.enum_values == expected

    def test_execution_status_enum_matches_domain(self) -> None:
        col = _find_column(AGENT_EXECUTIONS_TABLE, "status")
        assert col is not None
        expected = tuple(m.value for m in AgentExecutionStatus)
        assert col.enum_values == expected


# ===================================================================
# Alignment: Event type count
# ===================================================================


class TestEventTypeAlignment:
    def test_event_type_count_matches_domain_events(self) -> None:
        from backend.agent.application.ports.outbox import AgentOutboxEvent
        import typing
        args = typing.get_args(AgentOutboxEvent)
        col = _find_column(AGENT_OUTBOX_TABLE, "event_type")
        assert col is not None
        assert len(col.enum_values) == len(args)

    def test_event_type_values_cover_all_events(self) -> None:
        col = _find_column(AGENT_OUTBOX_TABLE, "event_type")
        assert col is not None
        assert "agent.created" in col.enum_values
        assert "agent.activated" in col.enum_values
        assert "agent.paused" in col.enum_values
        assert "agent.disabled" in col.enum_values
        assert "agent.task_created" in col.enum_values
        assert "agent.task_started" in col.enum_values
        assert "agent.task_completed" in col.enum_values
        assert "agent.task_failed" in col.enum_values
        assert "agent.task_cancelled" in col.enum_values
        assert "agent.execution_started" in col.enum_values
        assert "agent.execution_completed" in col.enum_values
        assert "agent.execution_failed" in col.enum_values


# ===================================================================
# Alignment: DTO ↔ Domain nullable parity
# ===================================================================


class TestDomainAlignment:
    def test_agent_dto_nullable_matches_domain_optionals(self) -> None:
        dto = AgentStorageDTO(agent_id="x")
        assert dto.name is None
        assert dto.updated_at is None
        agent = Agent(agent_id=AgentId())
        assert agent.name is None
        assert agent.updated_at is None

    def test_task_dto_nullable_matches_domain_optionals(self) -> None:
        dto = AgentTaskStorageDTO(task_id="x")
        assert dto.goal is None
        assert dto.instruction is None
        task = AgentTask(task_id=AgentTaskId())
        assert task.goal is None
        assert task.instruction is None

    def test_execution_dto_nullable_matches_domain_optionals(self) -> None:
        dto = AgentExecutionStorageDTO(execution_id="x")
        assert dto.result is None
        assert dto.failure_reason is None
        execution = AgentExecution(execution_id=AgentExecutionId())
        assert execution.result is None
        assert execution.failure_reason is None

    def test_agent_dto_not_nullable_matches_domain_required(self) -> None:
        dto = AgentStorageDTO(agent_id="x")
        assert dto.agent_id == "x"
        assert dto.agent_type == "coordinator"
        assert dto.status == "idle"

    def test_task_dto_task_id_not_nullable(self) -> None:
        dto = AgentTaskStorageDTO(task_id="x")
        assert dto.task_id == "x"
        assert dto.status == "pending"

    def test_execution_dto_execution_id_not_nullable(self) -> None:
        dto = AgentExecutionStorageDTO(execution_id="x")
        assert dto.execution_id == "x"
        assert dto.status == "pending"


# ===================================================================
# Alignment: DTO field types match domain value object types
# ===================================================================


class TestDTOTypeAlignment:
    def test_agent_dto_id_is_str(self) -> None:
        dto = AgentStorageDTO(agent_id="x")
        assert isinstance(dto.agent_id, str)
        assert isinstance(AgentId(value=UUID(int=1)).value, UUID)

    def test_task_dto_id_is_str(self) -> None:
        dto = AgentTaskStorageDTO(task_id="x")
        assert isinstance(dto.task_id, str)
        assert isinstance(AgentTaskId(value=UUID(int=1)).value, UUID)

    def test_execution_dto_id_is_str(self) -> None:
        dto = AgentExecutionStorageDTO(execution_id="x")
        assert isinstance(dto.execution_id, str)
        assert isinstance(AgentExecutionId(value=UUID(int=1)).value, UUID)


# ===================================================================
# Helpers
# ===================================================================


def _find_column(
    table: TableContract, name: str
) -> ColumnContract | None:
    for col in table.columns:
        if col.name == name:
            return col
    return None


def _dto_field_names(dto_class: type) -> list[str]:
    import dataclasses
    return [f.name for f in dataclasses.fields(dto_class)]

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from backend.agent.application.persistence.dto import (
    AgentExecutionStorageDTO,
    AgentOutboxStorageDTO,
    AgentStorageDTO,
    AgentTaskStorageDTO,
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

AgentOutboxDomainEvent = (
    AgentCreated
    | AgentActivated
    | AgentPaused
    | AgentDisabled
    | AgentTaskCreated
    | AgentTaskStarted
    | AgentTaskCompleted
    | AgentTaskFailed
    | AgentTaskCancelled
    | AgentExecutionStarted
    | AgentExecutionCompleted
    | AgentExecutionFailed
)

_EVENT_TYPE_MAP: dict[type, str] = {
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

_EVENT_TYPE_REVERSE: dict[str, type] = {v: k for k, v in _EVENT_TYPE_MAP.items()}


class AgentMapperImpl:
    def domain_to_dto(self, agent: Agent) -> AgentStorageDTO:
        return AgentStorageDTO(
            agent_id=str(agent.agent_id),
            agent_type=agent.agent_type.value,
            name=str(agent.name) if agent.name else None,
            status=agent.status.value,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )

    def dto_to_domain(
        self,
        dto: AgentStorageDTO,
        tasks: list[AgentTask] | None = None,
        executions: list[AgentExecution] | None = None,
    ) -> Agent:
        name_vo = AgentName(value=dto.name) if dto.name else None
        return Agent(
            agent_id=AgentId(value=UUID(dto.agent_id)),
            agent_type=AgentType(dto.agent_type),
            name=name_vo,
            status=AgentStatus(dto.status),
            tasks=tasks or [],
            executions=executions or [],
            created_at=dto.created_at or datetime.now(),
            updated_at=dto.updated_at,
        )


class AgentTaskMapperImpl:
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
        goal_vo = AgentGoal(value=dto.goal) if dto.goal else None
        instruction_vo = AgentInstruction(value=dto.instruction) if dto.instruction else None
        result_vo = AgentResult(value=dto.result) if dto.result else None
        failure_vo = FailureReason(value=dto.failure_reason) if dto.failure_reason else None
        agent_id_vo = AgentId(value=UUID(dto.agent_id)) if dto.agent_id else None
        return AgentTask(
            task_id=AgentTaskId(value=UUID(dto.task_id)),
            goal=goal_vo,
            instruction=instruction_vo,
            status=AgentTaskStatus(dto.status),
            result=result_vo,
            failure_reason=failure_vo,
            agent_id=agent_id_vo,
        )


class AgentExecutionMapperImpl:
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
        result_vo = AgentResult(value=dto.result) if dto.result else None
        failure_vo = FailureReason(value=dto.failure_reason) if dto.failure_reason else None
        agent_id_vo = AgentId(value=UUID(dto.agent_id)) if dto.agent_id else None
        task_id_vo = AgentTaskId(value=UUID(dto.task_id)) if dto.task_id else None
        return AgentExecution(
            execution_id=AgentExecutionId(value=UUID(dto.execution_id)),
            task_id=task_id_vo,
            agent_id=agent_id_vo,
            status=AgentExecutionStatus(dto.status),
            result=result_vo,
            failure_reason=failure_vo,
        )


class AgentOutboxMapperImpl:
    def event_to_dto(
        self, event: AgentOutboxDomainEvent
    ) -> AgentOutboxStorageDTO:
        event_type = _EVENT_TYPE_MAP.get(type(event), "unknown")
        aggregate_id = self._get_aggregate_id(event)
        payload = self._build_payload(event)
        return AgentOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type=event_type,
            aggregate_id=aggregate_id,
            occurred_at=event.occurred_at,
            payload=json.dumps(payload) if payload else None,
            published=False,
        )

    def dto_to_event(
        self, dto: AgentOutboxStorageDTO
    ) -> AgentOutboxDomainEvent:
        event_cls = _EVENT_TYPE_REVERSE.get(dto.event_type)
        if event_cls is None:
            raise ValueError(f"Unknown event_type: {dto.event_type}")
        if isinstance(dto.payload, dict):
            payload = dto.payload
        else:
            payload = json.loads(dto.payload) if dto.payload else {}
        aggregate_uuid = UUID(dto.aggregate_id)
        event_uuid = UUID(dto.event_id)

        if event_cls is AgentCreated:
            return AgentCreated(
                event_id=event_uuid,
                agent_id=AgentId(value=aggregate_uuid),
                agent_type=payload.get("agent_type", ""),
                name=payload.get("name", ""),
                occurred_at=dto.occurred_at,
            )
        if event_cls is AgentActivated:
            return AgentActivated(
                event_id=event_uuid,
                agent_id=AgentId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is AgentPaused:
            return AgentPaused(
                event_id=event_uuid,
                agent_id=AgentId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is AgentDisabled:
            return AgentDisabled(
                event_id=event_uuid,
                agent_id=AgentId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is AgentTaskCreated:
            task_uuid = UUID(payload.get("task_id", ""))
            return AgentTaskCreated(
                event_id=event_uuid,
                task_id=AgentTaskId(value=task_uuid),
                agent_id=AgentId(value=aggregate_uuid),
                goal=payload.get("goal", ""),
                instruction=payload.get("instruction", ""),
                occurred_at=dto.occurred_at,
            )
        if event_cls is AgentTaskStarted:
            task_uuid = UUID(payload.get("task_id", ""))
            return AgentTaskStarted(
                event_id=event_uuid,
                task_id=AgentTaskId(value=task_uuid),
                agent_id=AgentId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is AgentTaskCompleted:
            task_uuid = UUID(payload.get("task_id", ""))
            return AgentTaskCompleted(
                event_id=event_uuid,
                task_id=AgentTaskId(value=task_uuid),
                agent_id=AgentId(value=aggregate_uuid),
                result=payload.get("result", ""),
                occurred_at=dto.occurred_at,
            )
        if event_cls is AgentTaskFailed:
            task_uuid = UUID(payload.get("task_id", ""))
            return AgentTaskFailed(
                event_id=event_uuid,
                task_id=AgentTaskId(value=task_uuid),
                agent_id=AgentId(value=aggregate_uuid),
                failure_reason=payload.get("failure_reason", ""),
                occurred_at=dto.occurred_at,
            )
        if event_cls is AgentTaskCancelled:
            task_uuid = UUID(payload.get("task_id", ""))
            return AgentTaskCancelled(
                event_id=event_uuid,
                task_id=AgentTaskId(value=task_uuid),
                agent_id=AgentId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is AgentExecutionStarted:
            exec_uuid = UUID(payload.get("execution_id", ""))
            task_uuid = UUID(payload.get("task_id", ""))
            return AgentExecutionStarted(
                event_id=event_uuid,
                execution_id=AgentExecutionId(value=exec_uuid),
                agent_id=AgentId(value=aggregate_uuid),
                task_id=AgentTaskId(value=task_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is AgentExecutionCompleted:
            exec_uuid = UUID(payload.get("execution_id", ""))
            task_uuid = UUID(payload.get("task_id", ""))
            return AgentExecutionCompleted(
                event_id=event_uuid,
                execution_id=AgentExecutionId(value=exec_uuid),
                agent_id=AgentId(value=aggregate_uuid),
                task_id=AgentTaskId(value=task_uuid),
                result=payload.get("result", ""),
                occurred_at=dto.occurred_at,
            )
        if event_cls is AgentExecutionFailed:
            exec_uuid = UUID(payload.get("execution_id", ""))
            task_uuid = UUID(payload.get("task_id", ""))
            return AgentExecutionFailed(
                event_id=event_uuid,
                execution_id=AgentExecutionId(value=exec_uuid),
                agent_id=AgentId(value=aggregate_uuid),
                task_id=AgentTaskId(value=task_uuid),
                failure_reason=payload.get("failure_reason", ""),
                occurred_at=dto.occurred_at,
            )

        raise ValueError(f"Unsupported event type: {event_cls}")

    @staticmethod
    def _get_aggregate_id(event: AgentOutboxDomainEvent) -> str:
        if isinstance(event, (AgentCreated, AgentActivated, AgentPaused, AgentDisabled)):
            return str(event.agent_id)
        if isinstance(event, (AgentTaskCreated, AgentTaskStarted, AgentTaskCompleted, AgentTaskFailed, AgentTaskCancelled)):
            return str(event.agent_id)
        if isinstance(event, (AgentExecutionStarted, AgentExecutionCompleted, AgentExecutionFailed)):
            return str(event.agent_id)
        return ""

    @staticmethod
    def _build_payload(event: AgentOutboxDomainEvent) -> dict | None:
        if isinstance(event, AgentCreated):
            return {
                "agent_type": event.agent_type,
                "name": event.name,
            }
        if isinstance(event, AgentTaskCreated):
            return {
                "task_id": str(event.task_id),
                "goal": event.goal,
                "instruction": event.instruction,
            }
        if isinstance(event, AgentTaskStarted):
            return {"task_id": str(event.task_id)}
        if isinstance(event, AgentTaskCompleted):
            return {
                "task_id": str(event.task_id),
                "result": event.result,
            }
        if isinstance(event, AgentTaskFailed):
            return {
                "task_id": str(event.task_id),
                "failure_reason": event.failure_reason,
            }
        if isinstance(event, AgentTaskCancelled):
            return {"task_id": str(event.task_id)}
        if isinstance(event, AgentExecutionStarted):
            return {
                "execution_id": str(event.execution_id),
                "task_id": str(event.task_id),
            }
        if isinstance(event, AgentExecutionCompleted):
            return {
                "execution_id": str(event.execution_id),
                "task_id": str(event.task_id),
                "result": event.result,
            }
        if isinstance(event, AgentExecutionFailed):
            return {
                "execution_id": str(event.execution_id),
                "task_id": str(event.task_id),
                "failure_reason": event.failure_reason,
            }
        return None

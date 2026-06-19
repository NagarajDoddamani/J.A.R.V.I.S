from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from backend.automation.application.persistence.dto import (
    AutomationExecutionStorageDTO,
    AutomationOutboxStorageDTO,
    AutomationStorageDTO,
    TriggerStorageDTO,
)
from backend.automation.domain.model import (
    ActionAdded,
    ActionType,
    Automation,
    AutomationActivated,
    AutomationCreated,
    AutomationDescription,
    AutomationDisabled,
    AutomationExecution,
    AutomationExecutionCompleted,
    AutomationExecutionFailed,
    AutomationExecutionStarted,
    AutomationId,
    AutomationName,
    AutomationPaused,
    AutomationStatus,
    ExecutionMode,
    ExecutionResult,
    ExecutionStatus,
    FailureReason,
    Trigger,
    TriggerAdded,
    TriggerDisabled,
    TriggerEnabled,
    TriggerExpression,
    TriggerId,
    TriggerType,
    WorkflowExecutionId,
)

AutomationOutboxDomainEvent = (
    AutomationCreated
    | AutomationActivated
    | AutomationPaused
    | AutomationDisabled
    | AutomationExecutionStarted
    | AutomationExecutionCompleted
    | AutomationExecutionFailed
    | TriggerAdded
    | TriggerEnabled
    | TriggerDisabled
    | ActionAdded
)

_EVENT_TYPE_MAP: dict[type, str] = {
    AutomationCreated: "automation.created",
    AutomationActivated: "automation.activated",
    AutomationPaused: "automation.paused",
    AutomationDisabled: "automation.disabled",
    AutomationExecutionStarted: "automation.execution_started",
    AutomationExecutionCompleted: "automation.execution_completed",
    AutomationExecutionFailed: "automation.execution_failed",
    TriggerAdded: "automation.trigger_added",
    TriggerEnabled: "automation.trigger_enabled",
    TriggerDisabled: "automation.trigger_disabled",
    ActionAdded: "automation.action_added",
}

_EVENT_TYPE_REVERSE: dict[str, type] = {v: k for k, v in _EVENT_TYPE_MAP.items()}


class AutomationMapperImpl:
    def domain_to_dto(self, automation: Automation) -> AutomationStorageDTO:
        actions_json = json.dumps([a.value for a in automation.actions]) if automation.actions else None
        return AutomationStorageDTO(
            automation_id=str(automation.automation_id),
            name=str(automation.name) if automation.name else None,
            description=str(automation.description) if automation.description else None,
            status=automation.status.value,
            execution_mode=automation.execution_mode.value,
            actions=actions_json,
            created_at=automation.created_at,
            updated_at=automation.updated_at,
        )

    def dto_to_domain(
        self,
        dto: AutomationStorageDTO,
        triggers: list[Trigger] | None = None,
        executions: list[AutomationExecution] | None = None,
        actions: list[str] | None = None,
    ) -> Automation:
        name_vo = AutomationName(value=dto.name) if dto.name else None
        desc_vo = AutomationDescription(value=dto.description) if dto.description else None
        if actions is not None:
            action_list = [ActionType(a) for a in actions]
        elif dto.actions:
            action_list = [ActionType(a) for a in json.loads(dto.actions)]
        else:
            action_list = []
        return Automation(
            automation_id=AutomationId(value=UUID(dto.automation_id)),
            name=name_vo,
            description=desc_vo,
            status=AutomationStatus(dto.status),
            execution_mode=ExecutionMode(dto.execution_mode),
            triggers=triggers or [],
            actions=action_list,
            executions=executions or [],
            created_at=dto.created_at or datetime.now(),
            updated_at=dto.updated_at,
        )


class TriggerMapperImpl:
    def domain_to_dto(
        self, trigger: Trigger, automation_id: str | None = None
    ) -> TriggerStorageDTO:
        return TriggerStorageDTO(
            trigger_id=str(trigger.trigger_id),
            automation_id=automation_id,
            trigger_type=trigger.trigger_type.value,
            expression=str(trigger.expression) if trigger.expression else None,
            enabled=trigger.enabled,
        )

    def dto_to_domain(self, dto: TriggerStorageDTO) -> Trigger:
        expression_vo = (
            TriggerExpression(value=dto.expression) if dto.expression else None
        )
        automation_id = (
            AutomationId(value=UUID(dto.automation_id)) if dto.automation_id else None
        )
        return Trigger(
            trigger_id=TriggerId(value=UUID(dto.trigger_id)),
            trigger_type=TriggerType(dto.trigger_type),
            expression=expression_vo,
            enabled=dto.enabled,
            automation_id=automation_id,
        )


class AutomationExecutionMapperImpl:
    def domain_to_dto(
        self, execution: AutomationExecution
    ) -> AutomationExecutionStorageDTO:
        return AutomationExecutionStorageDTO(
            execution_id=str(execution.execution_id),
            automation_id=str(execution.automation_id),
            status=execution.status.value,
            result=str(execution.result) if execution.result else None,
            failure_reason=str(execution.failure_reason)
            if execution.failure_reason
            else None,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
        )

    def dto_to_domain(
        self, dto: AutomationExecutionStorageDTO
    ) -> AutomationExecution:
        result_vo = ExecutionResult(value=dto.result) if dto.result else None
        failure_vo = (
            FailureReason(value=dto.failure_reason) if dto.failure_reason else None
        )
        return AutomationExecution(
            execution_id=WorkflowExecutionId(value=UUID(dto.execution_id)),
            automation_id=AutomationId(value=UUID(dto.automation_id))
            if dto.automation_id
            else None,
            status=ExecutionStatus(dto.status),
            result=result_vo,
            failure_reason=failure_vo,
            started_at=dto.started_at,
            completed_at=dto.completed_at,
        )


class AutomationOutboxMapperImpl:
    def event_to_dto(
        self, event: AutomationOutboxDomainEvent
    ) -> AutomationOutboxStorageDTO:
        event_type = _EVENT_TYPE_MAP.get(type(event), "unknown")
        aggregate_id = self._get_aggregate_id(event)
        payload = self._build_payload(event)
        return AutomationOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type=event_type,
            aggregate_id=aggregate_id,
            occurred_at=event.occurred_at,
            payload=json.dumps(payload) if payload else None,
            published=False,
        )

    def dto_to_event(
        self, dto: AutomationOutboxStorageDTO
    ) -> AutomationOutboxDomainEvent:
        event_cls = _EVENT_TYPE_REVERSE.get(dto.event_type)
        if event_cls is None:
            raise ValueError(f"Unknown event_type: {dto.event_type}")
        if isinstance(dto.payload, dict):
            payload = dto.payload
        else:
            payload = json.loads(dto.payload) if dto.payload else {}
        aggregate_uuid = UUID(dto.aggregate_id)
        event_uuid = UUID(dto.event_id)

        if event_cls is AutomationCreated:
            return AutomationCreated(
                event_id=event_uuid,
                automation_id=AutomationId(value=aggregate_uuid),
                name=payload.get("name", ""),
                description=payload.get("description", ""),
                execution_mode=payload.get("execution_mode", "once"),
                occurred_at=dto.occurred_at,
            )
        if event_cls is AutomationActivated:
            return AutomationActivated(
                event_id=event_uuid,
                automation_id=AutomationId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is AutomationPaused:
            return AutomationPaused(
                event_id=event_uuid,
                automation_id=AutomationId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is AutomationDisabled:
            return AutomationDisabled(
                event_id=event_uuid,
                automation_id=AutomationId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is AutomationExecutionStarted:
            exec_id = UUID(payload.get("execution_id", ""))
            return AutomationExecutionStarted(
                event_id=event_uuid,
                automation_id=AutomationId(value=aggregate_uuid),
                execution_id=WorkflowExecutionId(value=exec_id),
                occurred_at=dto.occurred_at,
            )
        if event_cls is AutomationExecutionCompleted:
            exec_id = UUID(payload.get("execution_id", ""))
            return AutomationExecutionCompleted(
                event_id=event_uuid,
                automation_id=AutomationId(value=aggregate_uuid),
                execution_id=WorkflowExecutionId(value=exec_id),
                result=payload.get("result", ""),
                occurred_at=dto.occurred_at,
            )
        if event_cls is AutomationExecutionFailed:
            exec_id = UUID(payload.get("execution_id", ""))
            return AutomationExecutionFailed(
                event_id=event_uuid,
                automation_id=AutomationId(value=aggregate_uuid),
                execution_id=WorkflowExecutionId(value=exec_id),
                failure_reason=payload.get("failure_reason", ""),
                occurred_at=dto.occurred_at,
            )
        if event_cls is TriggerAdded:
            trigger_uuid = UUID(payload.get("trigger_id", ""))
            return TriggerAdded(
                event_id=event_uuid,
                trigger_id=TriggerId(value=trigger_uuid),
                automation_id=AutomationId(value=aggregate_uuid),
                trigger_type=payload.get("trigger_type", "manual"),
                expression=payload.get("expression", ""),
                occurred_at=dto.occurred_at,
            )
        if event_cls is TriggerEnabled:
            return TriggerEnabled(
                event_id=event_uuid,
                trigger_id=TriggerId(value=aggregate_uuid),
                automation_id=AutomationId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is TriggerDisabled:
            return TriggerDisabled(
                event_id=event_uuid,
                trigger_id=TriggerId(value=aggregate_uuid),
                automation_id=AutomationId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is ActionAdded:
            return ActionAdded(
                event_id=event_uuid,
                automation_id=AutomationId(value=aggregate_uuid),
                action_type=payload.get("action_type", ""),
                occurred_at=dto.occurred_at,
            )

        raise ValueError(f"Unsupported event type: {event_cls}")

    @staticmethod
    def _get_aggregate_id(event: AutomationOutboxDomainEvent) -> str:
        if isinstance(
            event,
            (
                AutomationCreated,
                AutomationActivated,
                AutomationPaused,
                AutomationDisabled,
            ),
        ):
            return str(event.automation_id)
        if isinstance(
            event,
            (
                AutomationExecutionStarted,
                AutomationExecutionCompleted,
                AutomationExecutionFailed,
            ),
        ):
            return str(event.automation_id)
        if isinstance(event, (TriggerAdded, TriggerEnabled, TriggerDisabled)):
            return str(event.automation_id)
        if isinstance(event, ActionAdded):
            return str(event.automation_id)
        return ""

    @staticmethod
    def _build_payload(event: AutomationOutboxDomainEvent) -> dict | None:
        if isinstance(event, AutomationCreated):
            return {
                "name": event.name,
                "description": event.description,
                "execution_mode": event.execution_mode,
            }
        if isinstance(event, AutomationExecutionStarted):
            return {"execution_id": str(event.execution_id)}
        if isinstance(event, AutomationExecutionCompleted):
            return {
                "execution_id": str(event.execution_id),
                "result": event.result,
            }
        if isinstance(event, AutomationExecutionFailed):
            return {
                "execution_id": str(event.execution_id),
                "failure_reason": event.failure_reason,
            }
        if isinstance(event, TriggerAdded):
            return {
                "trigger_id": str(event.trigger_id),
                "trigger_type": event.trigger_type,
                "expression": event.expression,
            }
        if isinstance(event, ActionAdded):
            return {"action_type": event.action_type}
        return None

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID, uuid4

from backend.orchestrator.application.persistence.dto import (
    OrchestrationStorageDTO,
    OrchestratorOutboxStorageDTO,
    WorkflowStepStorageDTO,
    WorkflowStorageDTO,
)
from backend.orchestrator.application.persistence.mapper import (
    OrchestratorOutboxDomainEvent,
)
from backend.orchestrator.domain.model import (
    AgentRole,
    ExecutionMode,
    ExecutionOrder,
    ExecutionResult,
    FailureReason,
    Orchestration,
    OrchestrationCancelled,
    OrchestrationCompleted,
    OrchestrationCreated,
    OrchestrationExecutionStarted,
    OrchestrationFailed,
    OrchestrationId,
    OrchestrationPlanningStarted,
    OrchestrationResearchStarted,
    OrchestrationStatus,
    UserIntent,
    Workflow,
    WorkflowCompleted,
    WorkflowCreated,
    WorkflowFailed,
    WorkflowGoal,
    WorkflowId,
    WorkflowStep,
    WorkflowStepCompleted,
    WorkflowStepFailed,
    WorkflowStepStarted,
    WorkflowStepStatus,
    WorkflowStatus,
)

_EVENT_TYPE_MAP: dict[type, str] = {
    OrchestrationCreated: "orchestration.created",
    OrchestrationPlanningStarted: "orchestration.planning_started",
    OrchestrationResearchStarted: "orchestration.research_started",
    OrchestrationExecutionStarted: "orchestration.execution_started",
    OrchestrationCompleted: "orchestration.completed",
    OrchestrationFailed: "orchestration.failed",
    OrchestrationCancelled: "orchestration.cancelled",
    WorkflowCreated: "workflow.created",
    WorkflowCompleted: "workflow.completed",
    WorkflowFailed: "workflow.failed",
    WorkflowStepStarted: "workflow.step_started",
    WorkflowStepCompleted: "workflow.step_completed",
    WorkflowStepFailed: "workflow.step_failed",
}

_EVENT_TYPE_REVERSE: dict[str, type] = {v: k for k, v in _EVENT_TYPE_MAP.items()}


class OrchestrationMapperImpl:
    def domain_to_dto(
        self, orchestration: Orchestration
    ) -> OrchestrationStorageDTO:
        return OrchestrationStorageDTO(
            orchestration_id=str(orchestration.orchestration_id),
            intent=str(orchestration.intent) if orchestration.intent else None,
            goal=str(orchestration.goal) if orchestration.goal else None,
            status=orchestration.status.value,
            created_at=orchestration.created_at,
            updated_at=orchestration.updated_at,
        )

    def dto_to_domain(
        self, dto: OrchestrationStorageDTO
    ) -> Orchestration:
        return Orchestration(
            orchestration_id=OrchestrationId(value=UUID(dto.orchestration_id)),
            intent=UserIntent(value=dto.intent) if dto.intent else None,
            goal=WorkflowGoal(value=dto.goal) if dto.goal else None,
            status=OrchestrationStatus(dto.status),
            created_at=dto.created_at or datetime.now(),
            updated_at=dto.updated_at,
        )


class WorkflowMapperImpl:
    def domain_to_dto(self, workflow: Workflow) -> WorkflowStorageDTO:
        return WorkflowStorageDTO(
            workflow_id=str(workflow.workflow_id),
            orchestration_id=None,
            goal=str(workflow.goal) if workflow.goal else None,
            mode=workflow.mode.value,
            status=workflow.status.value,
        )

    def dto_to_domain(self, dto: WorkflowStorageDTO) -> Workflow:
        workflow = Workflow(
            workflow_id=WorkflowId(value=UUID(dto.workflow_id)),
            goal=WorkflowGoal(value=dto.goal) if dto.goal else None,
            mode=ExecutionMode(dto.mode),
        )
        object.__setattr__(workflow, "_status", WorkflowStatus(dto.status))
        return workflow


class WorkflowStepMapperImpl:
    def domain_to_dto(self, step: WorkflowStep) -> WorkflowStepStorageDTO:
        return WorkflowStepStorageDTO(
            step_id=str(step.step_id),
            workflow_id=None,
            agent_role=step.agent_role.value,
            execution_order=int(step.execution_order),
            status=step.status.value,
            result=str(step.result) if step.result else None,
            failure_reason=str(step.failure_reason)
            if step.failure_reason else None,
        )

    def dto_to_domain(self, dto: WorkflowStepStorageDTO) -> WorkflowStep:
        return WorkflowStep(
            step_id=WorkflowId(value=UUID(dto.step_id)),
            agent_role=AgentRole(dto.agent_role),
            execution_order=ExecutionOrder(value=dto.execution_order),
            status=WorkflowStepStatus(dto.status),
            result=ExecutionResult(value=dto.result)
            if dto.result else None,
            failure_reason=FailureReason(value=dto.failure_reason)
            if dto.failure_reason else None,
        )


class OrchestratorOutboxMapperImpl:
    def event_to_dto(
        self, event: OrchestratorOutboxDomainEvent
    ) -> OrchestratorOutboxStorageDTO:
        event_type = _EVENT_TYPE_MAP.get(type(event), "unknown")
        aggregate_id = self._get_aggregate_id(event)
        payload = self._build_payload(event)
        return OrchestratorOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type=event_type,
            aggregate_id=aggregate_id,
            occurred_at=event.occurred_at,
            payload=json.dumps(payload) if payload else None,
            published=False,
        )

    def dto_to_event(
        self, dto: OrchestratorOutboxStorageDTO
    ) -> OrchestratorOutboxDomainEvent:
        event_cls = _EVENT_TYPE_REVERSE.get(dto.event_type)
        if event_cls is None:
            raise ValueError(f"Unknown event_type: {dto.event_type}")
        if isinstance(dto.payload, dict):
            payload = dto.payload
        else:
            payload = json.loads(dto.payload) if dto.payload else {}
        aggregate_uuid = UUID(dto.aggregate_id)
        event_uuid = UUID(dto.event_id)

        if event_cls is OrchestrationCreated:
            return OrchestrationCreated(
                event_id=event_uuid,
                orchestration_id=OrchestrationId(value=aggregate_uuid),
                intent=payload.get("intent", ""),
                goal=payload.get("goal", ""),
                occurred_at=dto.occurred_at,
            )
        if event_cls is OrchestrationPlanningStarted:
            return OrchestrationPlanningStarted(
                event_id=event_uuid,
                orchestration_id=OrchestrationId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is OrchestrationResearchStarted:
            return OrchestrationResearchStarted(
                event_id=event_uuid,
                orchestration_id=OrchestrationId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is OrchestrationExecutionStarted:
            return OrchestrationExecutionStarted(
                event_id=event_uuid,
                orchestration_id=OrchestrationId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is OrchestrationCompleted:
            return OrchestrationCompleted(
                event_id=event_uuid,
                orchestration_id=OrchestrationId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is OrchestrationFailed:
            return OrchestrationFailed(
                event_id=event_uuid,
                orchestration_id=OrchestrationId(value=aggregate_uuid),
                failure_reason=payload.get("failure_reason", ""),
                occurred_at=dto.occurred_at,
            )
        if event_cls is OrchestrationCancelled:
            return OrchestrationCancelled(
                event_id=event_uuid,
                orchestration_id=OrchestrationId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is WorkflowCreated:
            return WorkflowCreated(
                event_id=event_uuid,
                workflow_id=WorkflowId(value=aggregate_uuid),
                orchestration_id=OrchestrationId(
                    value=UUID(payload.get("orchestration_id", dto.aggregate_id))
                ),
                goal=payload.get("goal", ""),
                mode=payload.get("mode", "sequential"),
                occurred_at=dto.occurred_at,
            )
        if event_cls is WorkflowCompleted:
            return WorkflowCompleted(
                event_id=event_uuid,
                workflow_id=WorkflowId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is WorkflowFailed:
            return WorkflowFailed(
                event_id=event_uuid,
                workflow_id=WorkflowId(value=aggregate_uuid),
                failure_reason=payload.get("failure_reason", ""),
                occurred_at=dto.occurred_at,
            )
        if event_cls is WorkflowStepStarted:
            return WorkflowStepStarted(
                event_id=event_uuid,
                step_id=WorkflowId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is WorkflowStepCompleted:
            return WorkflowStepCompleted(
                event_id=event_uuid,
                step_id=WorkflowId(value=aggregate_uuid),
                result=payload.get("result", ""),
                occurred_at=dto.occurred_at,
            )
        if event_cls is WorkflowStepFailed:
            return WorkflowStepFailed(
                event_id=event_uuid,
                step_id=WorkflowId(value=aggregate_uuid),
                failure_reason=payload.get("failure_reason", ""),
                occurred_at=dto.occurred_at,
            )

        raise ValueError(f"Unsupported event type: {event_cls}")

    @staticmethod
    def _get_aggregate_id(event: OrchestratorOutboxDomainEvent) -> str:
        if isinstance(event, (OrchestrationCreated, OrchestrationPlanningStarted,
                              OrchestrationResearchStarted, OrchestrationExecutionStarted,
                              OrchestrationCompleted, OrchestrationFailed, OrchestrationCancelled)):
            return str(event.orchestration_id)
        if isinstance(event, (WorkflowCreated, WorkflowCompleted, WorkflowFailed)):
            return str(event.workflow_id)
        if isinstance(event, (WorkflowStepStarted, WorkflowStepCompleted, WorkflowStepFailed)):
            return str(event.step_id)
        return ""

    @staticmethod
    def _build_payload(
        event: OrchestratorOutboxDomainEvent
    ) -> dict | None:
        if isinstance(event, OrchestrationCreated):
            return {"intent": event.intent, "goal": event.goal}
        if isinstance(event, OrchestrationFailed):
            return {"failure_reason": event.failure_reason}
        if isinstance(event, WorkflowCreated):
            return {
                "orchestration_id": str(event.orchestration_id),
                "goal": event.goal,
                "mode": event.mode,
            }
        if isinstance(event, WorkflowFailed):
            return {"failure_reason": event.failure_reason}
        if isinstance(event, WorkflowStepCompleted):
            return {"result": event.result}
        if isinstance(event, WorkflowStepFailed):
            return {"failure_reason": event.failure_reason}
        return None




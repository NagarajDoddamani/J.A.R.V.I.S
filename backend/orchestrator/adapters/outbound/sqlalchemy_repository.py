from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.orchestrator.adapters.outbound.mapper import (
    OrchestrationMapperImpl,
    OrchestratorOutboxMapperImpl,
    WorkflowMapperImpl,
    WorkflowStepMapperImpl,
)
from backend.orchestrator.adapters.outbound.models import (
    OrchestrationModel,
    OrchestratorOutboxModel,
    WorkflowModel,
    WorkflowStepModel,
)
from backend.orchestrator.application.persistence.dto import (
    OrchestrationStorageDTO,
    OrchestratorOutboxStorageDTO,
    WorkflowStepStorageDTO,
    WorkflowStorageDTO,
)
from backend.orchestrator.domain.model import (
    AgentRole,
    Orchestration,
    OrchestrationId,
    OrchestrationStatus,
    Workflow,
    WorkflowId,
    WorkflowStep,
    WorkflowStepStatus,
    WorkflowStatus,
)
from backend.orchestrator.application.persistence.mapper import (
    OrchestratorOutboxDomainEvent,
)


class SqlAlchemyOrchestrationRepository:
    def __init__(
        self,
        session: Session,
        mapper: OrchestrationMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or OrchestrationMapperImpl()

    def save(self, orchestration: Orchestration) -> None:
        dto = self._mapper.domain_to_dto(orchestration)
        existing = self._session.get(
            OrchestrationModel, dto.orchestration_id
        )
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(
        self, orchestration_id: OrchestrationId
    ) -> Orchestration | None:
        model = self._session.get(
            OrchestrationModel, str(orchestration_id)
        )
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_status(
        self, status: OrchestrationStatus
    ) -> list[Orchestration]:
        stmt = select(OrchestrationModel).where(
            OrchestrationModel.status == status.value
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def find_all(self) -> list[Orchestration]:
        stmt = select(OrchestrationModel)
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def count(self) -> int:
        stmt = select(OrchestrationModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(
        dto: OrchestrationStorageDTO
    ) -> OrchestrationModel:
        return OrchestrationModel(
            orchestration_id=dto.orchestration_id,
            intent=dto.intent,
            goal=dto.goal,
            status=dto.status,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )

    @staticmethod
    def _model_to_dto(
        model: OrchestrationModel
    ) -> OrchestrationStorageDTO:
        return OrchestrationStorageDTO(
            orchestration_id=model.orchestration_id,
            intent=model.intent,
            goal=model.goal,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _model_update_from_dto(
        model: OrchestrationModel, dto: OrchestrationStorageDTO
    ) -> None:
        model.intent = dto.intent
        model.goal = dto.goal
        model.status = dto.status
        model.created_at = dto.created_at
        model.updated_at = dto.updated_at


class SqlAlchemyWorkflowRepository:
    def __init__(
        self,
        session: Session,
        mapper: WorkflowMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or WorkflowMapperImpl()

    def save(self, workflow: Workflow) -> None:
        dto = self._mapper.domain_to_dto(workflow)
        existing = self._session.get(WorkflowModel, dto.workflow_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(self, workflow_id: WorkflowId) -> Workflow | None:
        model = self._session.get(WorkflowModel, str(workflow_id))
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_status(
        self, status: WorkflowStatus
    ) -> list[Workflow]:
        stmt = select(WorkflowModel).where(
            WorkflowModel.status == status.value
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def find_by_orchestration_id(
        self, orchestration_id: OrchestrationId
    ) -> list[Workflow]:
        stmt = select(WorkflowModel).where(
            WorkflowModel.orchestration_id == str(orchestration_id)
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def find_all(self) -> list[Workflow]:
        stmt = select(WorkflowModel)
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def count(self) -> int:
        stmt = select(WorkflowModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(dto: WorkflowStorageDTO) -> WorkflowModel:
        return WorkflowModel(
            workflow_id=dto.workflow_id,
            orchestration_id=dto.orchestration_id,
            goal=dto.goal,
            mode=dto.mode,
            status=dto.status,
        )

    @staticmethod
    def _model_to_dto(model: WorkflowModel) -> WorkflowStorageDTO:
        return WorkflowStorageDTO(
            workflow_id=model.workflow_id,
            orchestration_id=model.orchestration_id,
            goal=model.goal,
            mode=model.mode,
            status=model.status,
        )

    @staticmethod
    def _model_update_from_dto(
        model: WorkflowModel, dto: WorkflowStorageDTO
    ) -> None:
        model.orchestration_id = dto.orchestration_id
        model.goal = dto.goal
        model.mode = dto.mode
        model.status = dto.status


class SqlAlchemyWorkflowStepRepository:
    def __init__(
        self,
        session: Session,
        mapper: WorkflowStepMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or WorkflowStepMapperImpl()

    def save(self, step: WorkflowStep) -> None:
        dto = self._mapper.domain_to_dto(step)
        existing = self._session.get(WorkflowStepModel, dto.step_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(self, step_id: WorkflowId) -> WorkflowStep | None:
        model = self._session.get(WorkflowStepModel, str(step_id))
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_status(
        self, status: WorkflowStepStatus
    ) -> list[WorkflowStep]:
        stmt = select(WorkflowStepModel).where(
            WorkflowStepModel.status == status.value
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def find_by_workflow_id(
        self, workflow_id: WorkflowId
    ) -> list[WorkflowStep]:
        stmt = select(WorkflowStepModel).where(
            WorkflowStepModel.workflow_id == str(workflow_id)
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def find_by_agent_role(
        self, agent_role: AgentRole
    ) -> list[WorkflowStep]:
        stmt = select(WorkflowStepModel).where(
            WorkflowStepModel.agent_role == agent_role.value
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m))
            for m in models
        ]

    def count(self) -> int:
        stmt = select(WorkflowStepModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(dto: WorkflowStepStorageDTO) -> WorkflowStepModel:
        return WorkflowStepModel(
            step_id=dto.step_id,
            workflow_id=dto.workflow_id,
            agent_role=dto.agent_role,
            execution_order=dto.execution_order,
            status=dto.status,
            result=dto.result,
            failure_reason=dto.failure_reason,
        )

    @staticmethod
    def _model_to_dto(model: WorkflowStepModel) -> WorkflowStepStorageDTO:
        return WorkflowStepStorageDTO(
            step_id=model.step_id,
            workflow_id=model.workflow_id,
            agent_role=model.agent_role,
            execution_order=model.execution_order,
            status=model.status,
            result=model.result,
            failure_reason=model.failure_reason,
        )

    @staticmethod
    def _model_update_from_dto(
        model: WorkflowStepModel, dto: WorkflowStepStorageDTO
    ) -> None:
        model.workflow_id = dto.workflow_id
        model.agent_role = dto.agent_role
        model.execution_order = dto.execution_order
        model.status = dto.status
        model.result = dto.result
        model.failure_reason = dto.failure_reason


class SqlAlchemyOrchestratorOutboxAdapter:
    def __init__(
        self,
        session: Session,
        mapper: OrchestratorOutboxMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or OrchestratorOutboxMapperImpl()

    def append(self, event: OrchestratorOutboxDomainEvent) -> None:
        dto = self._mapper.event_to_dto(event)
        model = OrchestratorOutboxModel(
            message_id=dto.event_id,
            subject=dto.event_type,
            aggregate_id=dto.aggregate_id,
            created_at=dto.occurred_at,
            payload=dto.payload,
            published_at=None,
            correlation_id=dto.event_id,
        )
        self._session.add(model)
        self._session.flush()

    def fetch_unpublished(
        self, limit: int = 100
    ) -> list[OrchestratorOutboxDomainEvent]:
        stmt = (
            select(OrchestratorOutboxModel)
            .where(OrchestratorOutboxModel.published_at.is_(None))
            .order_by(OrchestratorOutboxModel.created_at.asc())
            .limit(limit)
        )
        models = list(self._session.scalars(stmt))
        return [self._model_to_event(m) for m in models]

    def mark_published(self, event_id: str) -> None:
        stmt = (
            update(OrchestratorOutboxModel)
            .where(OrchestratorOutboxModel.message_id == event_id)
            .values(published_at=datetime.now(timezone.utc))
        )
        self._session.execute(stmt)
        self._session.flush()

    def _model_to_event(
        self, model: OrchestratorOutboxModel
    ) -> OrchestratorOutboxDomainEvent:
        dto = OrchestratorOutboxStorageDTO(
            event_id=model.message_id,
            event_type=model.subject,
            aggregate_id=model.aggregate_id,
            occurred_at=model.created_at,
            payload=model.payload,
            published=model.published_at is not None,
        )
        return self._mapper.dto_to_event(dto)

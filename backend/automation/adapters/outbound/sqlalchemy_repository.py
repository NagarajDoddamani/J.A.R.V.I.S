from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.automation.adapters.outbound.mapper import (
    AutomationExecutionMapperImpl,
    AutomationMapperImpl,
    AutomationOutboxDomainEvent,
    AutomationOutboxMapperImpl,
    TriggerMapperImpl,
)
from backend.automation.adapters.outbound.models import (
    AutomationExecutionModel,
    AutomationModel,
    AutomationOutboxModel,
    TriggerModel,
)
from backend.automation.application.persistence.dto import (
    AutomationExecutionStorageDTO,
    AutomationStorageDTO,
    TriggerStorageDTO,
)
from backend.automation.domain.model import (
    Automation,
    AutomationExecution,
    AutomationId,
    AutomationStatus,
    ExecutionMode,
    ExecutionStatus,
    Trigger,
    TriggerId,
    TriggerType,
    WorkflowExecutionId,
)


class SqlAlchemyAutomationRepository:
    def __init__(
        self,
        session: Session,
        mapper: AutomationMapperImpl | None = None,
        trigger_mapper: TriggerMapperImpl | None = None,
        execution_mapper: AutomationExecutionMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or AutomationMapperImpl()
        self._trigger_mapper = trigger_mapper or TriggerMapperImpl()
        self._execution_mapper = execution_mapper or AutomationExecutionMapperImpl()

    def save(self, automation: Automation) -> None:
        dto = self._mapper.domain_to_dto(automation)
        existing = self._session.get(AutomationModel, dto.automation_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(self, automation_id: AutomationId) -> Automation | None:
        model = self._session.get(AutomationModel, str(automation_id))
        if model is None:
            return None
        triggers = self._load_triggers(str(automation_id))
        executions = self._load_executions(str(automation_id))
        return self._mapper.dto_to_domain(
            self._model_to_dto(model),
            triggers=triggers,
            executions=executions,
        )

    def find_by_status(self, status: AutomationStatus) -> list[Automation]:
        stmt = select(AutomationModel).where(
            AutomationModel.status == status.value
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(
                self._model_to_dto(m),
                triggers=self._load_triggers(m.automation_id),
                executions=self._load_executions(m.automation_id),
            )
            for m in models
        ]

    def find_by_execution_mode(
        self, mode: ExecutionMode
    ) -> list[Automation]:
        stmt = select(AutomationModel).where(
            AutomationModel.execution_mode == mode.value
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(
                self._model_to_dto(m),
                triggers=self._load_triggers(m.automation_id),
                executions=self._load_executions(m.automation_id),
            )
            for m in models
        ]

    def find_all(self) -> list[Automation]:
        stmt = select(AutomationModel)
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(
                self._model_to_dto(m),
                triggers=self._load_triggers(m.automation_id),
                executions=self._load_executions(m.automation_id),
            )
            for m in models
        ]

    def count(self) -> int:
        stmt = select(AutomationModel)
        return len(list(self._session.scalars(stmt)))

    def _load_triggers(self, automation_id: str) -> list[Trigger]:
        stmt = select(TriggerModel).where(
            TriggerModel.automation_id == automation_id
        )
        models = list(self._session.scalars(stmt))
        return [
            self._trigger_mapper.dto_to_domain(self._trigger_model_to_dto(m))
            for m in models
        ]

    def _load_executions(self, automation_id: str) -> list[AutomationExecution]:
        stmt = select(AutomationExecutionModel).where(
            AutomationExecutionModel.automation_id == automation_id
        )
        models = list(self._session.scalars(stmt))
        return [
            self._execution_mapper.dto_to_domain(
                self._execution_model_to_dto(m)
            )
            for m in models
        ]

    @staticmethod
    def _dto_to_model(dto: AutomationStorageDTO) -> AutomationModel:
        return AutomationModel(
            automation_id=dto.automation_id,
            name=dto.name,
            description=dto.description,
            status=dto.status,
            execution_mode=dto.execution_mode,
            actions=dto.actions,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )

    @staticmethod
    def _model_to_dto(model: AutomationModel) -> AutomationStorageDTO:
        return AutomationStorageDTO(
            automation_id=model.automation_id,
            name=model.name,
            description=model.description,
            status=model.status,
            execution_mode=model.execution_mode,
            actions=model.actions,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _model_update_from_dto(
        model: AutomationModel, dto: AutomationStorageDTO
    ) -> None:
        model.name = dto.name
        model.description = dto.description
        model.status = dto.status
        model.execution_mode = dto.execution_mode
        model.actions = dto.actions
        model.created_at = dto.created_at
        model.updated_at = dto.updated_at

    @staticmethod
    def _trigger_model_to_dto(
        model: TriggerModel,
    ) -> TriggerStorageDTO:
        return TriggerStorageDTO(
            trigger_id=model.trigger_id,
            automation_id=model.automation_id,
            trigger_type=model.trigger_type,
            expression=model.expression,
            enabled=model.enabled,
        )

    @staticmethod
    def _execution_model_to_dto(
        model: AutomationExecutionModel,
    ) -> AutomationExecutionStorageDTO:
        return AutomationExecutionStorageDTO(
            execution_id=model.execution_id,
            automation_id=model.automation_id,
            status=model.status,
            result=model.result,
            failure_reason=model.failure_reason,
            started_at=model.started_at,
            completed_at=model.completed_at,
        )


class SqlAlchemyTriggerRepository:
    def __init__(
        self,
        session: Session,
        mapper: TriggerMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or TriggerMapperImpl()

    def save(self, trigger: Trigger, automation_id: str | None = None) -> None:
        dto = self._mapper.domain_to_dto(trigger, automation_id=automation_id)
        existing = self._session.get(TriggerModel, dto.trigger_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(self, trigger_id: TriggerId) -> Trigger | None:
        model = self._session.get(TriggerModel, str(trigger_id))
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_type(self, trigger_type: TriggerType) -> list[Trigger]:
        stmt = select(TriggerModel).where(
            TriggerModel.trigger_type == trigger_type.value
        )
        models = list(self._session.scalars(stmt))
        return [self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models]

    def find_enabled(self) -> list[Trigger]:
        stmt = select(TriggerModel).where(TriggerModel.enabled == True)
        models = list(self._session.scalars(stmt))
        return [self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models]

    def find_all(self) -> list[Trigger]:
        stmt = select(TriggerModel)
        models = list(self._session.scalars(stmt))
        return [self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models]

    def count(self) -> int:
        stmt = select(TriggerModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(dto: TriggerStorageDTO) -> TriggerModel:
        return TriggerModel(
            trigger_id=dto.trigger_id,
            automation_id=dto.automation_id,
            trigger_type=dto.trigger_type,
            expression=dto.expression,
            enabled=dto.enabled,
        )

    @staticmethod
    def _model_to_dto(model: TriggerModel) -> TriggerStorageDTO:
        return TriggerStorageDTO(
            trigger_id=model.trigger_id,
            automation_id=model.automation_id,
            trigger_type=model.trigger_type,
            expression=model.expression,
            enabled=model.enabled,
        )

    @staticmethod
    def _model_update_from_dto(
        model: TriggerModel, dto: TriggerStorageDTO
    ) -> None:
        if dto.automation_id is not None:
            model.automation_id = dto.automation_id
        model.trigger_type = dto.trigger_type
        model.expression = dto.expression
        model.enabled = dto.enabled


class SqlAlchemyAutomationExecutionRepository:
    def __init__(
        self,
        session: Session,
        mapper: AutomationExecutionMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or AutomationExecutionMapperImpl()

    def save(self, execution: AutomationExecution) -> None:
        dto = self._mapper.domain_to_dto(execution)
        existing = self._session.get(
            AutomationExecutionModel, dto.execution_id
        )
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(
        self, execution_id: WorkflowExecutionId
    ) -> AutomationExecution | None:
        model = self._session.get(
            AutomationExecutionModel, str(execution_id)
        )
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_status(
        self, status: ExecutionStatus
    ) -> list[AutomationExecution]:
        stmt = select(AutomationExecutionModel).where(
            AutomationExecutionModel.status == status.value
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models
        ]

    def find_by_automation_id(
        self, automation_id: AutomationId
    ) -> list[AutomationExecution]:
        stmt = select(AutomationExecutionModel).where(
            AutomationExecutionModel.automation_id == str(automation_id)
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models
        ]

    def find_all(self) -> list[AutomationExecution]:
        stmt = select(AutomationExecutionModel)
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models
        ]

    def count(self) -> int:
        stmt = select(AutomationExecutionModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(
        dto: AutomationExecutionStorageDTO,
    ) -> AutomationExecutionModel:
        return AutomationExecutionModel(
            execution_id=dto.execution_id,
            automation_id=dto.automation_id,
            status=dto.status,
            result=dto.result,
            failure_reason=dto.failure_reason,
            started_at=dto.started_at,
            completed_at=dto.completed_at,
        )

    @staticmethod
    def _model_to_dto(
        model: AutomationExecutionModel,
    ) -> AutomationExecutionStorageDTO:
        return AutomationExecutionStorageDTO(
            execution_id=model.execution_id,
            automation_id=model.automation_id,
            status=model.status,
            result=model.result,
            failure_reason=model.failure_reason,
            started_at=model.started_at,
            completed_at=model.completed_at,
        )

    @staticmethod
    def _model_update_from_dto(
        model: AutomationExecutionModel, dto: AutomationExecutionStorageDTO
    ) -> None:
        model.automation_id = dto.automation_id
        model.status = dto.status
        model.result = dto.result
        model.failure_reason = dto.failure_reason
        model.started_at = dto.started_at
        model.completed_at = dto.completed_at


class SqlAlchemyAutomationOutboxAdapter:
    def __init__(
        self,
        session: Session,
        mapper: AutomationOutboxMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or AutomationOutboxMapperImpl()

    def append(self, event: AutomationOutboxDomainEvent) -> None:
        dto = self._mapper.event_to_dto(event)
        model = AutomationOutboxModel(
            message_id=dto.event_id,
            subject=dto.event_type,
            aggregate_id=dto.aggregate_id,
            created_at=dto.occurred_at,
            payload=json.loads(dto.payload) if dto.payload else {},
            published_at=None,
            headers={},
            correlation_id=dto.event_id,
        )
        self._session.add(model)
        self._session.flush()

    def fetch_unpublished(
        self, limit: int = 100
    ) -> list[AutomationOutboxDomainEvent]:
        stmt = (
            select(AutomationOutboxModel)
            .where(AutomationOutboxModel.published_at.is_(None))
            .order_by(AutomationOutboxModel.created_at.asc())
            .limit(limit)
        )
        models = list(self._session.scalars(stmt))
        return [self._model_to_event(m) for m in models]

    def mark_published(self, event_id: str) -> None:
        stmt = (
            update(AutomationOutboxModel)
            .where(AutomationOutboxModel.message_id == event_id)
            .values(published_at=datetime.now(timezone.utc))
        )
        self._session.execute(stmt)
        self._session.flush()

    def _model_to_event(
        self, model: AutomationOutboxModel
    ) -> AutomationOutboxDomainEvent:
        from backend.automation.application.persistence.dto import (
            AutomationOutboxStorageDTO,
        )

        dto = AutomationOutboxStorageDTO(
            event_id=model.message_id,
            event_type=model.subject,
            aggregate_id=model.aggregate_id,
            occurred_at=model.created_at,
            payload=json.dumps(model.payload) if model.payload else None,
            published=model.published_at is not None,
        )
        return self._mapper.dto_to_event(dto)

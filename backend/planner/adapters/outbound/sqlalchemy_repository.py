from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.planner.adapters.outbound.mapper import (
    ExecutionStepMapperImpl,
    PlanMapperImpl,
    PlannerOutboxDomainEvent,
    PlannerOutboxMapperImpl,
    TaskMapperImpl,
)
from backend.planner.adapters.outbound.models import (
    ExecutionStepModel,
    PlanModel,
    PlannerOutboxModel,
    TaskModel,
)
from backend.planner.application.persistence.dto import (
    PlanStorageDTO,
    TaskStorageDTO,
)
from backend.planner.domain.model import (
    AgentType,
    ExecutionStep,
    Plan,
    PlanId,
    PlanPriority,
    PlanStatus,
    Task,
    TaskId,
    TaskStatus,
)


class SqlAlchemyPlanRepository:
    def __init__(
        self,
        session: Session,
        mapper: PlanMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or PlanMapperImpl()

    def save(self, plan: Plan) -> None:
        dto = self._mapper.domain_to_dto(plan)
        existing = self._session.get(PlanModel, dto.plan_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(self, plan_id: PlanId) -> Plan | None:
        model = self._session.get(PlanModel, str(plan_id))
        if model is None:
            return None
        tasks = self._load_tasks(str(plan_id))
        return self._mapper.dto_to_domain(self._model_to_dto(model), tasks=tasks)

    def find_by_status(self, status: PlanStatus) -> list[Plan]:
        stmt = select(PlanModel).where(PlanModel.status == status.value)
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(
                self._model_to_dto(m), tasks=self._load_tasks(m.plan_id)
            )
            for m in models
        ]

    def find_by_priority(self, priority: PlanPriority) -> list[Plan]:
        stmt = select(PlanModel).where(PlanModel.priority == priority.value)
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(
                self._model_to_dto(m), tasks=self._load_tasks(m.plan_id)
            )
            for m in models
        ]

    def find_active(self) -> list[Plan]:
        terminal = {PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.CANCELLED}
        terminal_values = {s.value for s in terminal}
        stmt = select(PlanModel).where(PlanModel.status.notin_(terminal_values))
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(
                self._model_to_dto(m), tasks=self._load_tasks(m.plan_id)
            )
            for m in models
        ]

    def count(self) -> int:
        stmt = select(PlanModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(dto: PlanStorageDTO) -> PlanModel:
        return PlanModel(
            plan_id=dto.plan_id,
            user_request=dto.user_request,
            goal=dto.goal,
            priority=dto.priority,
            strategy=dto.strategy,
            status=dto.status,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            failure_reason=dto.failure_reason,
        )

    def _load_tasks(self, plan_id: str) -> list[Task]:
        task_mapper = TaskMapperImpl()
        stmt = select(TaskModel).where(TaskModel.plan_id == plan_id)
        models = list(self._session.scalars(stmt))
        result: list[Task] = []
        for model in models:
            dto = TaskStorageDTO(
                task_id=model.task_id,
                plan_id=model.plan_id,
                description=model.description,
                assigned_agent=model.assigned_agent,
                status=model.status,
                failure_reason=model.failure_reason,
                estimated_duration=model.estimated_duration,
            )
            result.append(task_mapper.dto_to_domain(dto))
        return result

    @staticmethod
    def _model_to_dto(model: PlanModel) -> PlanStorageDTO:
        return PlanStorageDTO(
            plan_id=model.plan_id,
            user_request=model.user_request,
            goal=model.goal,
            priority=model.priority,
            strategy=model.strategy,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
            failure_reason=model.failure_reason,
        )

    @staticmethod
    def _model_update_from_dto(
        model: PlanModel, dto: PlanStorageDTO
    ) -> None:
        model.user_request = dto.user_request
        model.goal = dto.goal
        model.priority = dto.priority
        model.strategy = dto.strategy
        model.status = dto.status
        model.created_at = dto.created_at
        model.updated_at = dto.updated_at
        model.failure_reason = dto.failure_reason


class SqlAlchemyTaskRepository:
    def __init__(
        self,
        session: Session,
        mapper: TaskMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or TaskMapperImpl()

    def save(self, task: Task) -> None:
        dto = self._mapper.domain_to_dto(task)
        existing = self._session.get(TaskModel, dto.task_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(self, task_id: TaskId) -> Task | None:
        model = self._session.get(TaskModel, str(task_id))
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_status(self, status: TaskStatus) -> list[Task]:
        stmt = select(TaskModel).where(TaskModel.status == status.value)
        models = list(self._session.scalars(stmt))
        return [self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models]

    def find_by_agent(self, agent_type: AgentType) -> list[Task]:
        stmt = select(TaskModel).where(
            TaskModel.assigned_agent == agent_type.value
        )
        models = list(self._session.scalars(stmt))
        return [self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models]

    def find_by_plan_id(self, plan_id: PlanId) -> list[Task]:
        stmt = select(TaskModel).where(TaskModel.plan_id == str(plan_id))
        models = list(self._session.scalars(stmt))
        return [self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models]

    def count(self) -> int:
        stmt = select(TaskModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(dto: TaskStorageDTO) -> TaskModel:
        return TaskModel(
            task_id=dto.task_id,
            plan_id=dto.plan_id,
            description=dto.description,
            assigned_agent=dto.assigned_agent,
            status=dto.status,
            failure_reason=dto.failure_reason,
            estimated_duration=dto.estimated_duration,
        )

    @staticmethod
    def _model_to_dto(model: TaskModel) -> TaskStorageDTO:
        return TaskStorageDTO(
            task_id=model.task_id,
            plan_id=model.plan_id,
            description=model.description,
            assigned_agent=model.assigned_agent,
            status=model.status,
            failure_reason=model.failure_reason,
            estimated_duration=model.estimated_duration,
        )

    @staticmethod
    def _model_update_from_dto(
        model: TaskModel, dto: TaskStorageDTO
    ) -> None:
        model.plan_id = dto.plan_id
        model.description = dto.description
        model.assigned_agent = dto.assigned_agent
        model.status = dto.status
        model.failure_reason = dto.failure_reason
        model.estimated_duration = dto.estimated_duration


class SqlAlchemyPlannerOutboxAdapter:
    def __init__(
        self,
        session: Session,
        mapper: PlannerOutboxMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or PlannerOutboxMapperImpl()

    def append(self, event: PlannerOutboxDomainEvent) -> None:
        dto = self._mapper.event_to_dto(event)
        model = PlannerOutboxModel(
            message_id=dto.event_id,
            subject=dto.event_type,
            aggregate_id=dto.aggregate_id,
            created_at=dto.occurred_at,
            payload=json.loads(dto.payload) if dto.payload else {},
            headers={},
            attempts=0,
            last_error=None,
            correlation_id=dto.event_id,
            causation_id=None,
            published_at=None,
        )
        self._session.add(model)
        self._session.flush()

    def fetch_unpublished(
        self, limit: int = 100
    ) -> list[PlannerOutboxDomainEvent]:
        stmt = (
            select(PlannerOutboxModel)
            .where(PlannerOutboxModel.published_at.is_(None))
            .order_by(PlannerOutboxModel.created_at.asc())
            .limit(limit)
        )
        models = list(self._session.scalars(stmt))
        return [self._model_to_event(m) for m in models]

    def mark_published(self, event_id: str) -> None:
        stmt = (
            update(PlannerOutboxModel)
            .where(PlannerOutboxModel.message_id == event_id)
            .values(published_at=datetime.now(timezone.utc))
        )
        self._session.execute(stmt)
        self._session.flush()

    def _model_to_event(
        self, model: PlannerOutboxModel
    ) -> PlannerOutboxDomainEvent:
        from backend.planner.application.persistence.dto import (
            PlannerOutboxStorageDTO,
        )

        dto = PlannerOutboxStorageDTO(
            event_id=model.message_id,
            event_type=model.subject,
            aggregate_id=model.aggregate_id if model.aggregate_id else "",
            occurred_at=model.created_at,
            payload=json.dumps(model.payload) if model.payload else None,
            published=model.published_at is not None,
        )
        return self._mapper.dto_to_event(dto)

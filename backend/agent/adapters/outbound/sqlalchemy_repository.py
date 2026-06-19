from __future__ import annotations

import json
from datetime import UTC, datetime

from backend.agent.adapters.outbound.mapper import (
    AgentExecutionMapperImpl,
    AgentMapperImpl,
    AgentOutboxDomainEvent,
    AgentOutboxMapperImpl,
    AgentTaskMapperImpl,
)
from backend.agent.adapters.outbound.models import (
    AgentExecutionModel,
    AgentModel,
    AgentOutboxModel,
    AgentTaskModel,
)
from backend.agent.application.persistence.dto import (
    AgentExecutionStorageDTO,
    AgentStorageDTO,
    AgentTaskStorageDTO,
)
from backend.agent.domain.model import (
    Agent,
    AgentExecution,
    AgentExecutionId,
    AgentExecutionStatus,
    AgentId,
    AgentStatus,
    AgentTask,
    AgentTaskId,
    AgentTaskStatus,
    AgentType,
)
from sqlalchemy import select, update
from sqlalchemy.orm import Session


class SqlAlchemyAgentRepository:
    def __init__(
        self,
        session: Session,
        mapper: AgentMapperImpl | None = None,
        task_mapper: AgentTaskMapperImpl | None = None,
        execution_mapper: AgentExecutionMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or AgentMapperImpl()
        self._task_mapper = task_mapper or AgentTaskMapperImpl()
        self._execution_mapper = execution_mapper or AgentExecutionMapperImpl()

    def save(self, agent: Agent) -> None:
        dto = self._mapper.domain_to_dto(agent)
        existing = self._session.get(AgentModel, dto.agent_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)

        for task in agent.tasks:
            task_dto = self._task_mapper.domain_to_dto(task)
            task_existing = self._session.get(AgentTaskModel, task_dto.task_id)
            if task_existing is None:
                self._session.add(self._task_model_from_dto(task_dto))
            else:
                self._task_model_update_from_dto(task_existing, task_dto)

        for execution in agent.executions:
            exec_dto = self._execution_mapper.domain_to_dto(execution)
            exec_existing = self._session.get(AgentExecutionModel, exec_dto.execution_id)
            if exec_existing is None:
                self._session.add(self._execution_model_from_dto(exec_dto))
            else:
                self._execution_model_update_from_dto(exec_existing, exec_dto)

        self._session.flush()

    def find_by_id(self, agent_id: AgentId) -> Agent | None:
        model = self._session.get(AgentModel, str(agent_id))
        if model is None:
            return None
        tasks = self._load_tasks(str(agent_id))
        executions = self._load_executions(str(agent_id))
        return self._mapper.dto_to_domain(
            self._model_to_dto(model),
            tasks=tasks,
            executions=executions,
        )

    def find_by_status(self, status: AgentStatus) -> list[Agent]:
        stmt = select(AgentModel).where(
            AgentModel.status == status.value
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(
                self._model_to_dto(m),
                tasks=self._load_tasks(m.agent_id),
                executions=self._load_executions(m.agent_id),
            )
            for m in models
        ]

    def find_by_type(self, agent_type: AgentType) -> list[Agent]:
        stmt = select(AgentModel).where(
            AgentModel.agent_type == agent_type.value
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(
                self._model_to_dto(m),
                tasks=self._load_tasks(m.agent_id),
                executions=self._load_executions(m.agent_id),
            )
            for m in models
        ]

    def find_all(self) -> list[Agent]:
        stmt = select(AgentModel)
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(
                self._model_to_dto(m),
                tasks=self._load_tasks(m.agent_id),
                executions=self._load_executions(m.agent_id),
            )
            for m in models
        ]

    def count(self) -> int:
        stmt = select(AgentModel)
        return len(list(self._session.scalars(stmt)))

    def _load_tasks(self, agent_id: str) -> list[AgentTask]:
        stmt = select(AgentTaskModel).where(
            AgentTaskModel.agent_id == agent_id
        )
        models = list(self._session.scalars(stmt))
        return [
            self._task_mapper.dto_to_domain(self._task_model_to_dto(m))
            for m in models
        ]

    def _load_executions(self, agent_id: str) -> list[AgentExecution]:
        stmt = select(AgentExecutionModel).where(
            AgentExecutionModel.agent_id == agent_id
        )
        models = list(self._session.scalars(stmt))
        return [
            self._execution_mapper.dto_to_domain(
                self._execution_model_to_dto(m)
            )
            for m in models
        ]

    @staticmethod
    def _dto_to_model(dto: AgentStorageDTO) -> AgentModel:
        return AgentModel(
            agent_id=dto.agent_id,
            agent_type=dto.agent_type,
            name=dto.name,
            status=dto.status,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )

    @staticmethod
    def _model_to_dto(model: AgentModel) -> AgentStorageDTO:
        return AgentStorageDTO(
            agent_id=model.agent_id,
            agent_type=model.agent_type,
            name=model.name,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _model_update_from_dto(
        model: AgentModel, dto: AgentStorageDTO
    ) -> None:
        model.agent_type = dto.agent_type
        model.name = dto.name
        model.status = dto.status
        model.created_at = dto.created_at
        model.updated_at = dto.updated_at

    @staticmethod
    def _task_model_to_dto(
        model: AgentTaskModel,
    ) -> AgentTaskStorageDTO:
        return AgentTaskStorageDTO(
            task_id=model.task_id,
            agent_id=model.agent_id,
            goal=model.goal,
            instruction=model.instruction,
            status=model.status,
            result=model.result,
            failure_reason=model.failure_reason,
        )

    @staticmethod
    def _execution_model_to_dto(
        model: AgentExecutionModel,
    ) -> AgentExecutionStorageDTO:
        return AgentExecutionStorageDTO(
            execution_id=model.execution_id,
            agent_id=model.agent_id,
            task_id=model.task_id,
            status=model.status,
            result=model.result,
            failure_reason=model.failure_reason,
        )

    @staticmethod
    def _task_model_from_dto(dto: AgentTaskStorageDTO) -> AgentTaskModel:
        return AgentTaskModel(
            task_id=dto.task_id,
            agent_id=dto.agent_id,
            goal=dto.goal,
            instruction=dto.instruction,
            status=dto.status,
            result=dto.result,
            failure_reason=dto.failure_reason,
        )

    @staticmethod
    def _task_model_update_from_dto(
        model: AgentTaskModel, dto: AgentTaskStorageDTO
    ) -> None:
        if dto.agent_id is not None:
            model.agent_id = dto.agent_id
        model.goal = dto.goal
        model.instruction = dto.instruction
        model.status = dto.status
        model.result = dto.result
        model.failure_reason = dto.failure_reason

    @staticmethod
    def _execution_model_from_dto(
        dto: AgentExecutionStorageDTO,
    ) -> AgentExecutionModel:
        return AgentExecutionModel(
            execution_id=dto.execution_id,
            agent_id=dto.agent_id,
            task_id=dto.task_id,
            status=dto.status,
            result=dto.result,
            failure_reason=dto.failure_reason,
        )

    @staticmethod
    def _execution_model_update_from_dto(
        model: AgentExecutionModel, dto: AgentExecutionStorageDTO
    ) -> None:
        model.agent_id = dto.agent_id
        model.task_id = dto.task_id
        model.status = dto.status
        model.result = dto.result
        model.failure_reason = dto.failure_reason


class SqlAlchemyAgentTaskRepository:
    def __init__(
        self,
        session: Session,
        mapper: AgentTaskMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or AgentTaskMapperImpl()

    def save(self, task: AgentTask) -> None:
        dto = self._mapper.domain_to_dto(task)
        existing = self._session.get(AgentTaskModel, dto.task_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(self, task_id: AgentTaskId) -> AgentTask | None:
        model = self._session.get(AgentTaskModel, str(task_id))
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_status(self, status: AgentTaskStatus) -> list[AgentTask]:
        stmt = select(AgentTaskModel).where(
            AgentTaskModel.status == status.value
        )
        models = list(self._session.scalars(stmt))
        return [self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models]

    def find_by_agent_id(self, agent_id: AgentId) -> list[AgentTask]:
        stmt = select(AgentTaskModel).where(
            AgentTaskModel.agent_id == str(agent_id)
        )
        models = list(self._session.scalars(stmt))
        return [self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models]

    def find_all(self) -> list[AgentTask]:
        stmt = select(AgentTaskModel)
        models = list(self._session.scalars(stmt))
        return [self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models]

    def count(self) -> int:
        stmt = select(AgentTaskModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(dto: AgentTaskStorageDTO) -> AgentTaskModel:
        return AgentTaskModel(
            task_id=dto.task_id,
            agent_id=dto.agent_id,
            goal=dto.goal,
            instruction=dto.instruction,
            status=dto.status,
            result=dto.result,
            failure_reason=dto.failure_reason,
        )

    @staticmethod
    def _model_to_dto(model: AgentTaskModel) -> AgentTaskStorageDTO:
        return AgentTaskStorageDTO(
            task_id=model.task_id,
            agent_id=model.agent_id,
            goal=model.goal,
            instruction=model.instruction,
            status=model.status,
            result=model.result,
            failure_reason=model.failure_reason,
        )

    @staticmethod
    def _model_update_from_dto(
        model: AgentTaskModel, dto: AgentTaskStorageDTO
    ) -> None:
        if dto.agent_id is not None:
            model.agent_id = dto.agent_id
        model.goal = dto.goal
        model.instruction = dto.instruction
        model.status = dto.status
        model.result = dto.result
        model.failure_reason = dto.failure_reason


class SqlAlchemyAgentExecutionRepository:
    def __init__(
        self,
        session: Session,
        mapper: AgentExecutionMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or AgentExecutionMapperImpl()

    def save(self, execution: AgentExecution) -> None:
        dto = self._mapper.domain_to_dto(execution)
        existing = self._session.get(
            AgentExecutionModel, dto.execution_id
        )
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(
        self, execution_id: AgentExecutionId
    ) -> AgentExecution | None:
        model = self._session.get(
            AgentExecutionModel, str(execution_id)
        )
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_status(
        self, status: AgentExecutionStatus
    ) -> list[AgentExecution]:
        stmt = select(AgentExecutionModel).where(
            AgentExecutionModel.status == status.value
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models
        ]

    def find_by_agent_id(
        self, agent_id: AgentId
    ) -> list[AgentExecution]:
        stmt = select(AgentExecutionModel).where(
            AgentExecutionModel.agent_id == str(agent_id)
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models
        ]

    def find_by_task_id(
        self, task_id: AgentTaskId
    ) -> list[AgentExecution]:
        stmt = select(AgentExecutionModel).where(
            AgentExecutionModel.task_id == str(task_id)
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models
        ]

    def find_all(self) -> list[AgentExecution]:
        stmt = select(AgentExecutionModel)
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models
        ]

    def count(self) -> int:
        stmt = select(AgentExecutionModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(
        dto: AgentExecutionStorageDTO,
    ) -> AgentExecutionModel:
        return AgentExecutionModel(
            execution_id=dto.execution_id,
            agent_id=dto.agent_id,
            task_id=dto.task_id,
            status=dto.status,
            result=dto.result,
            failure_reason=dto.failure_reason,
        )

    @staticmethod
    def _model_to_dto(
        model: AgentExecutionModel,
    ) -> AgentExecutionStorageDTO:
        return AgentExecutionStorageDTO(
            execution_id=model.execution_id,
            agent_id=model.agent_id,
            task_id=model.task_id,
            status=model.status,
            result=model.result,
            failure_reason=model.failure_reason,
        )

    @staticmethod
    def _model_update_from_dto(
        model: AgentExecutionModel, dto: AgentExecutionStorageDTO
    ) -> None:
        model.agent_id = dto.agent_id
        model.task_id = dto.task_id
        model.status = dto.status
        model.result = dto.result
        model.failure_reason = dto.failure_reason


class SqlAlchemyAgentOutboxAdapter:
    def __init__(
        self,
        session: Session,
        mapper: AgentOutboxMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or AgentOutboxMapperImpl()

    def append(self, event: AgentOutboxDomainEvent) -> None:
        dto = self._mapper.event_to_dto(event)
        model = AgentOutboxModel(
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
    ) -> list[AgentOutboxDomainEvent]:
        stmt = (
            select(AgentOutboxModel)
            .where(AgentOutboxModel.published_at.is_(None))
            .order_by(AgentOutboxModel.created_at.asc())
            .limit(limit)
        )
        models = list(self._session.scalars(stmt))
        return [self._model_to_event(m) for m in models]

    def mark_published(self, event_id: str) -> None:
        stmt = (
            update(AgentOutboxModel)
            .where(AgentOutboxModel.message_id == event_id)
            .values(published_at=datetime.now(UTC))
        )
        self._session.execute(stmt)
        self._session.flush()

    def _model_to_event(
        self, model: AgentOutboxModel
    ) -> AgentOutboxDomainEvent:
        from backend.agent.application.persistence.dto import (
            AgentOutboxStorageDTO,
        )

        dto = AgentOutboxStorageDTO(
            event_id=model.message_id,
            event_type=model.subject,
            aggregate_id=model.aggregate_id,
            occurred_at=model.created_at,
            payload=json.dumps(model.payload) if model.payload else None,
            published=model.published_at is not None,
        )
        return self._mapper.dto_to_event(dto)

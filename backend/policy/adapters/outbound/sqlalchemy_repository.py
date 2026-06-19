from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.policy.adapters.outbound.mapper import (
    PolicyEvaluationMapperImpl,
    PolicyMapperImpl,
    PolicyOutboxDomainEvent,
    PolicyOutboxMapperImpl,
    PolicyRuleMapperImpl,
)
from backend.policy.adapters.outbound.models import (
    PolicyEvaluationModel,
    PolicyModel,
    PolicyOutboxModel,
    PolicyRuleModel,
)
from backend.policy.application.persistence.dto import (
    PolicyEvaluationStorageDTO,
    PolicyOutboxStorageDTO,
    PolicyRuleStorageDTO,
    PolicyStorageDTO,
)
from backend.policy.domain.model import (
    EvaluationId,
    Policy,
    PolicyEvaluation,
    PolicyEvaluationStatus,
    PolicyId,
    PolicyPriority,
    PolicyRule,
    PolicyRuleId,
    PolicyScope,
    PolicyStatus,
)


class SqlAlchemyPolicyRepository:
    def __init__(
        self,
        session: Session,
        mapper: PolicyMapperImpl | None = None,
        rule_mapper: PolicyRuleMapperImpl | None = None,
        evaluation_mapper: PolicyEvaluationMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or PolicyMapperImpl()
        self._rule_mapper = rule_mapper or PolicyRuleMapperImpl()
        self._evaluation_mapper = evaluation_mapper or PolicyEvaluationMapperImpl()

    def _load_rules(self, policy_id: str) -> list[PolicyRule]:
        stmt = select(PolicyRuleModel).where(
            PolicyRuleModel.policy_id == policy_id
        )
        models = list(self._session.scalars(stmt))
        return [
            self._rule_mapper.dto_to_domain(
                PolicyRuleStorageDTO(
                    rule_id=m.rule_id,
                    policy_id=m.policy_id,
                    condition=m.condition,
                    action=m.action,
                    priority=m.priority,
                    enabled=m.enabled,
                )
            )
            for m in models
        ]

    def _load_evaluations(self, policy_id: str) -> list[PolicyEvaluation]:
        stmt = select(PolicyEvaluationModel).where(
            PolicyEvaluationModel.policy_id == policy_id
        )
        models = list(self._session.scalars(stmt))
        return [
            self._evaluation_mapper.dto_to_domain(
                PolicyEvaluationStorageDTO(
                    evaluation_id=m.evaluation_id,
                    policy_id=m.policy_id,
                    status=m.status,
                    decision=m.decision,
                    result=m.result,
                    failure_reason=m.failure_reason,
                    started_at=m.started_at,
                    completed_at=m.completed_at,
                )
            )
            for m in models
        ]

    def _policy_from_model(self, model: PolicyModel) -> Policy:
        rules = self._load_rules(model.policy_id)
        evaluations = self._load_evaluations(model.policy_id)
        return self._mapper.dto_to_domain(
            self._model_to_dto(model),
            rules=rules,
            evaluations=evaluations,
        )

    def save(self, policy: Policy) -> None:
        dto = self._mapper.domain_to_dto(policy)
        existing = self._session.get(PolicyModel, dto.policy_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(self, policy_id: PolicyId) -> Policy | None:
        model = self._session.get(PolicyModel, str(policy_id))
        if model is None:
            return None
        return self._policy_from_model(model)

    def find_by_status(self, status: PolicyStatus) -> list[Policy]:
        stmt = select(PolicyModel).where(PolicyModel.status == status.value)
        models = list(self._session.scalars(stmt))
        return [self._policy_from_model(m) for m in models]

    def find_by_priority(self, priority: PolicyPriority) -> list[Policy]:
        stmt = select(PolicyModel).where(PolicyModel.priority == priority.value)
        models = list(self._session.scalars(stmt))
        return [self._policy_from_model(m) for m in models]

    def find_by_scope(self, scope: PolicyScope) -> list[Policy]:
        stmt = select(PolicyModel).where(PolicyModel.scope == scope.value)
        models = list(self._session.scalars(stmt))
        return [self._policy_from_model(m) for m in models]

    def find_all(self) -> list[Policy]:
        stmt = select(PolicyModel)
        models = list(self._session.scalars(stmt))
        return [self._policy_from_model(m) for m in models]

    def count(self) -> int:
        stmt = select(PolicyModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(dto: PolicyStorageDTO) -> PolicyModel:
        return PolicyModel(
            policy_id=dto.policy_id,
            name=dto.name,
            description=dto.description,
            status=dto.status,
            priority=dto.priority,
            scope=dto.scope,
            version=dto.version,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )

    @staticmethod
    def _model_to_dto(model: PolicyModel) -> PolicyStorageDTO:
        return PolicyStorageDTO(
            policy_id=model.policy_id,
            name=model.name,
            description=model.description,
            status=model.status,
            priority=model.priority,
            scope=model.scope,
            version=model.version,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _model_update_from_dto(
        model: PolicyModel, dto: PolicyStorageDTO
    ) -> None:
        model.name = dto.name
        model.description = dto.description
        model.status = dto.status
        model.priority = dto.priority
        model.scope = dto.scope
        model.version = dto.version
        model.created_at = dto.created_at
        model.updated_at = dto.updated_at


class SqlAlchemyPolicyRuleRepository:
    def __init__(
        self,
        session: Session,
        mapper: PolicyRuleMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or PolicyRuleMapperImpl()
        self._policy_ids: dict[str, str] = {}

    def save(self, rule: PolicyRule, policy_id: str | None = None) -> None:
        rule_id = str(rule.rule_id)
        if rule_id not in self._policy_ids and policy_id is not None:
            self._policy_ids[rule_id] = policy_id
        dto = self._mapper.domain_to_dto(
            rule, policy_id=self._policy_ids.get(rule_id)
        )
        existing = self._session.get(PolicyRuleModel, dto.rule_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def _from_model(self, model: PolicyRuleModel) -> PolicyRule:
        self._policy_ids[model.rule_id] = model.policy_id
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_id(self, rule_id: PolicyRuleId) -> PolicyRule | None:
        model = self._session.get(PolicyRuleModel, str(rule_id))
        if model is None:
            return None
        return self._from_model(model)

    def find_by_policy_id(self, policy_id: PolicyId) -> list[PolicyRule]:
        stmt = select(PolicyRuleModel).where(
            PolicyRuleModel.policy_id == str(policy_id)
        )
        models = list(self._session.scalars(stmt))
        return [self._from_model(m) for m in models]

    def find_enabled(self) -> list[PolicyRule]:
        stmt = select(PolicyRuleModel).where(PolicyRuleModel.enabled == True)
        models = list(self._session.scalars(stmt))
        return [self._from_model(m) for m in models]

    def find_all(self) -> list[PolicyRule]:
        stmt = select(PolicyRuleModel)
        models = list(self._session.scalars(stmt))
        return [self._from_model(m) for m in models]

    def count(self) -> int:
        stmt = select(PolicyRuleModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(dto: PolicyRuleStorageDTO) -> PolicyRuleModel:
        return PolicyRuleModel(
            rule_id=dto.rule_id,
            policy_id=dto.policy_id,
            condition=dto.condition,
            action=dto.action,
            priority=dto.priority,
            enabled=dto.enabled,
        )

    @staticmethod
    def _model_to_dto(model: PolicyRuleModel) -> PolicyRuleStorageDTO:
        return PolicyRuleStorageDTO(
            rule_id=model.rule_id,
            policy_id=model.policy_id,
            condition=model.condition,
            action=model.action,
            priority=model.priority,
            enabled=model.enabled,
        )

    @staticmethod
    def _model_update_from_dto(
        model: PolicyRuleModel, dto: PolicyRuleStorageDTO
    ) -> None:
        if dto.policy_id is not None:
            model.policy_id = dto.policy_id
        model.condition = dto.condition
        model.action = dto.action
        model.priority = dto.priority
        model.enabled = dto.enabled


class SqlAlchemyPolicyEvaluationRepository:
    def __init__(
        self,
        session: Session,
        mapper: PolicyEvaluationMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or PolicyEvaluationMapperImpl()

    def save(self, evaluation: PolicyEvaluation) -> None:
        dto = self._mapper.domain_to_dto(evaluation)
        existing = self._session.get(PolicyEvaluationModel, dto.evaluation_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(
        self, evaluation_id: EvaluationId
    ) -> PolicyEvaluation | None:
        model = self._session.get(PolicyEvaluationModel, str(evaluation_id))
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_status(
        self, status: PolicyEvaluationStatus
    ) -> list[PolicyEvaluation]:
        stmt = select(PolicyEvaluationModel).where(
            PolicyEvaluationModel.status == status.value
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models
        ]

    def find_by_policy_id(
        self, policy_id: PolicyId
    ) -> list[PolicyEvaluation]:
        stmt = select(PolicyEvaluationModel).where(
            PolicyEvaluationModel.policy_id == str(policy_id)
        )
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models
        ]

    def find_all(self) -> list[PolicyEvaluation]:
        stmt = select(PolicyEvaluationModel)
        models = list(self._session.scalars(stmt))
        return [
            self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models
        ]

    def count(self) -> int:
        stmt = select(PolicyEvaluationModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(
        dto: PolicyEvaluationStorageDTO,
    ) -> PolicyEvaluationModel:
        return PolicyEvaluationModel(
            evaluation_id=dto.evaluation_id,
            policy_id=dto.policy_id,
            status=dto.status,
            decision=dto.decision,
            result=dto.result,
            failure_reason=dto.failure_reason,
            started_at=dto.started_at,
            completed_at=dto.completed_at,
        )

    @staticmethod
    def _model_to_dto(
        model: PolicyEvaluationModel,
    ) -> PolicyEvaluationStorageDTO:
        return PolicyEvaluationStorageDTO(
            evaluation_id=model.evaluation_id,
            policy_id=model.policy_id,
            status=model.status,
            decision=model.decision,
            result=model.result,
            failure_reason=model.failure_reason,
            started_at=model.started_at,
            completed_at=model.completed_at,
        )

    @staticmethod
    def _model_update_from_dto(
        model: PolicyEvaluationModel,
        dto: PolicyEvaluationStorageDTO,
    ) -> None:
        model.policy_id = dto.policy_id
        model.status = dto.status
        model.decision = dto.decision
        model.result = dto.result
        model.failure_reason = dto.failure_reason
        model.started_at = dto.started_at
        model.completed_at = dto.completed_at


class SqlAlchemyPolicyOutboxAdapter:
    def __init__(
        self,
        session: Session,
        mapper: PolicyOutboxMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or PolicyOutboxMapperImpl()

    def append(self, event: PolicyOutboxDomainEvent) -> None:
        dto = self._mapper.event_to_dto(event)
        model = PolicyOutboxModel(
            message_id=dto.event_id,
            subject=dto.event_type,
            created_at=dto.occurred_at,
            published_at=None,
            headers={},
            correlation_id=dto.correlation_id if hasattr(dto, 'correlation_id') else None,
            aggregate_id=dto.aggregate_id,
            payload=json.loads(dto.payload) if dto.payload else {},
        )
        self._session.add(model)
        self._session.flush()

    def fetch_unpublished(
        self, limit: int = 100
    ) -> list[PolicyOutboxDomainEvent]:
        stmt = (
            select(PolicyOutboxModel)
            .where(PolicyOutboxModel.published_at.is_(None))
            .order_by(PolicyOutboxModel.created_at.asc())
            .limit(limit)
        )
        models = list(self._session.scalars(stmt))
        return [self._model_to_event(m) for m in models]

    def mark_published(self, event_id: str) -> None:
        stmt = (
            update(PolicyOutboxModel)
            .where(PolicyOutboxModel.message_id == event_id)
            .values(published_at=datetime.now(timezone.utc))
        )
        self._session.execute(stmt)
        self._session.flush()

    def _model_to_event(
        self, model: PolicyOutboxModel
    ) -> PolicyOutboxDomainEvent:
        dto = PolicyOutboxStorageDTO(
            event_id=model.message_id,
            event_type=model.subject,
            aggregate_id=model.aggregate_id,
            occurred_at=model.created_at,
            payload=json.dumps(model.payload) if model.payload else "{}",
            published=model.published_at is not None,
        )
        return self._mapper.dto_to_event(dto)

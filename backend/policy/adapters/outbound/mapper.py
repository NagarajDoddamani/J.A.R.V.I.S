from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from backend.policy.application.persistence.dto import (
    PolicyEvaluationStorageDTO,
    PolicyOutboxStorageDTO,
    PolicyRuleStorageDTO,
    PolicyStorageDTO,
)
from backend.policy.domain.model import (
    EvaluationId,
    EvaluationResult,
    FailureReason,
    Policy,
    PolicyAction,
    PolicyActivated,
    PolicyArchived,
    PolicyCondition,
    PolicyCreated,
    PolicyDecision,
    PolicyDescription,
    PolicyDisabled,
    PolicyEvaluation,
    PolicyEvaluationCompleted,
    PolicyEvaluationFailed,
    PolicyEvaluationStarted,
    PolicyEvaluationStatus,
    PolicyId,
    PolicyName,
    PolicyPriority,
    PolicyRule,
    PolicyRuleAdded,
    PolicyRuleDisabled,
    PolicyRuleEnabled,
    PolicyRuleId,
    PolicyRuleRemoved,
    PolicyScope,
    PolicyStatus,
    PolicyVersion,
)

PolicyOutboxDomainEvent = (
    PolicyCreated
    | PolicyActivated
    | PolicyDisabled
    | PolicyArchived
    | PolicyRuleAdded
    | PolicyRuleRemoved
    | PolicyRuleEnabled
    | PolicyRuleDisabled
    | PolicyEvaluationStarted
    | PolicyEvaluationCompleted
    | PolicyEvaluationFailed
)

_EVENT_TYPE_MAP: dict[type, str] = {
    PolicyCreated: "policy.created",
    PolicyActivated: "policy.activated",
    PolicyDisabled: "policy.disabled",
    PolicyArchived: "policy.archived",
    PolicyRuleAdded: "policy.rule_added",
    PolicyRuleRemoved: "policy.rule_removed",
    PolicyRuleEnabled: "policy.rule_enabled",
    PolicyRuleDisabled: "policy.rule_disabled",
    PolicyEvaluationStarted: "policy.evaluation_started",
    PolicyEvaluationCompleted: "policy.evaluation_completed",
    PolicyEvaluationFailed: "policy.evaluation_failed",
}

_EVENT_TYPE_REVERSE: dict[str, type] = {v: k for k, v in _EVENT_TYPE_MAP.items()}


class PolicyMapperImpl:
    def domain_to_dto(self, policy: Policy) -> PolicyStorageDTO:
        return PolicyStorageDTO(
            policy_id=str(policy.policy_id),
            name=str(policy.name) if policy.name else None,
            description=str(policy.description) if policy.description else None,
            status=policy.status.value,
            priority=policy.priority.value,
            scope=policy.scope.value,
            version=str(policy.version) if policy.version else None,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
        )

    def dto_to_domain(
        self,
        dto: PolicyStorageDTO,
        rules: list[PolicyRule] | None = None,
        evaluations: list[PolicyEvaluation] | None = None,
    ) -> Policy:
        name_vo = PolicyName(value=dto.name) if dto.name else None
        desc_vo = PolicyDescription(value=dto.description) if dto.description else None
        version_vo = PolicyVersion(value=dto.version) if dto.version else None
        return Policy(
            policy_id=PolicyId(value=UUID(dto.policy_id)),
            name=name_vo,
            description=desc_vo,
            status=PolicyStatus(dto.status),
            priority=PolicyPriority(dto.priority),
            scope=PolicyScope(dto.scope),
            version=version_vo,
            rules=rules or [],
            evaluations=evaluations or [],
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )


class PolicyRuleMapperImpl:
    def domain_to_dto(
        self, rule: PolicyRule, policy_id: str | None = None
    ) -> PolicyRuleStorageDTO:
        return PolicyRuleStorageDTO(
            rule_id=str(rule.rule_id),
            policy_id=policy_id,
            condition=str(rule.condition) if rule.condition else None,
            action=str(rule.action) if rule.action else None,
            priority=rule.priority,
            enabled=rule.enabled,
        )

    def dto_to_domain(self, dto: PolicyRuleStorageDTO) -> PolicyRule:
        condition_vo = (
            PolicyCondition(value=dto.condition) if dto.condition else None
        )
        action_vo = (
            PolicyAction(value=dto.action) if dto.action else None
        )
        policy_id = (
            PolicyId(value=UUID(dto.policy_id)) if dto.policy_id else None
        )
        return PolicyRule(
            rule_id=PolicyRuleId(value=UUID(dto.rule_id)),
            condition=condition_vo,
            action=action_vo,
            priority=dto.priority,
            enabled=dto.enabled,
            policy_id=policy_id,
        )


class PolicyEvaluationMapperImpl:
    def domain_to_dto(
        self, evaluation: PolicyEvaluation
    ) -> PolicyEvaluationStorageDTO:
        return PolicyEvaluationStorageDTO(
            evaluation_id=str(evaluation.evaluation_id),
            policy_id=str(evaluation.policy_id),
            status=evaluation.status.value,
            decision=evaluation.decision.value if evaluation.decision else None,
            result=str(evaluation.result) if evaluation.result else None,
            failure_reason=str(evaluation.failure_reason)
            if evaluation.failure_reason
            else None,
            started_at=evaluation.started_at,
            completed_at=evaluation.completed_at,
        )

    def dto_to_domain(
        self, dto: PolicyEvaluationStorageDTO
    ) -> PolicyEvaluation:
        decision_vo = (
            PolicyDecision(dto.decision) if dto.decision else None
        )
        result_vo = (
            EvaluationResult(value=dto.result) if dto.result else None
        )
        failure_vo = (
            FailureReason(value=dto.failure_reason)
            if dto.failure_reason
            else None
        )
        return PolicyEvaluation(
            evaluation_id=EvaluationId(value=UUID(dto.evaluation_id)),
            policy_id=PolicyId(value=UUID(dto.policy_id))
            if dto.policy_id
            else None,
            status=PolicyEvaluationStatus(dto.status),
            decision=decision_vo,
            result=result_vo,
            failure_reason=failure_vo,
            started_at=dto.started_at,
            completed_at=dto.completed_at,
        )


class PolicyOutboxMapperImpl:
    def event_to_dto(
        self, event: PolicyOutboxDomainEvent
    ) -> PolicyOutboxStorageDTO:
        event_type = _EVENT_TYPE_MAP.get(type(event), "unknown")
        aggregate_id = self._get_aggregate_id(event)
        payload = self._build_payload(event)
        return PolicyOutboxStorageDTO(
            event_id=str(uuid4()),
            event_type=event_type,
            aggregate_id=aggregate_id,
            occurred_at=event.occurred_at,
            payload=json.dumps(payload) if payload else None,
            published=False,
        )

    def dto_to_event(
        self, dto: PolicyOutboxStorageDTO
    ) -> PolicyOutboxDomainEvent:
        event_cls = _EVENT_TYPE_REVERSE.get(dto.event_type)
        if event_cls is None:
            raise ValueError(f"Unknown event_type: {dto.event_type}")
        if isinstance(dto.payload, dict):
            payload = dto.payload
        else:
            payload = json.loads(dto.payload) if dto.payload else {}
        aggregate_uuid = UUID(dto.aggregate_id)
        event_uuid = UUID(dto.event_id)

        if event_cls is PolicyCreated:
            return PolicyCreated(
                event_id=event_uuid,
                policy_id=PolicyId(value=aggregate_uuid),
                name=payload.get("name", ""),
                description=payload.get("description", ""),
                priority=payload.get("priority", "medium"),
                scope=payload.get("scope", "global"),
                version=payload.get("version", "1.0.0"),
                occurred_at=dto.occurred_at,
            )
        if event_cls is PolicyActivated:
            return PolicyActivated(
                event_id=event_uuid,
                policy_id=PolicyId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is PolicyDisabled:
            return PolicyDisabled(
                event_id=event_uuid,
                policy_id=PolicyId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is PolicyArchived:
            return PolicyArchived(
                event_id=event_uuid,
                policy_id=PolicyId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is PolicyRuleAdded:
            rule_uuid = UUID(payload.get("rule_id", ""))
            return PolicyRuleAdded(
                event_id=event_uuid,
                rule_id=PolicyRuleId(value=rule_uuid),
                policy_id=PolicyId(value=aggregate_uuid),
                condition=payload.get("condition", ""),
                action=payload.get("action", ""),
                occurred_at=dto.occurred_at,
            )
        if event_cls is PolicyRuleRemoved:
            return PolicyRuleRemoved(
                event_id=event_uuid,
                rule_id=PolicyRuleId(value=aggregate_uuid),
                policy_id=PolicyId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is PolicyRuleEnabled:
            return PolicyRuleEnabled(
                event_id=event_uuid,
                rule_id=PolicyRuleId(value=aggregate_uuid),
                policy_id=PolicyId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is PolicyRuleDisabled:
            return PolicyRuleDisabled(
                event_id=event_uuid,
                rule_id=PolicyRuleId(value=aggregate_uuid),
                policy_id=PolicyId(value=aggregate_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is PolicyEvaluationStarted:
            eval_uuid = UUID(payload.get("evaluation_id", ""))
            return PolicyEvaluationStarted(
                event_id=event_uuid,
                policy_id=PolicyId(value=aggregate_uuid),
                evaluation_id=EvaluationId(value=eval_uuid),
                occurred_at=dto.occurred_at,
            )
        if event_cls is PolicyEvaluationCompleted:
            eval_uuid = UUID(payload.get("evaluation_id", ""))
            return PolicyEvaluationCompleted(
                event_id=event_uuid,
                policy_id=PolicyId(value=aggregate_uuid),
                evaluation_id=EvaluationId(value=eval_uuid),
                decision=payload.get("decision", ""),
                result=payload.get("result", ""),
                occurred_at=dto.occurred_at,
            )
        if event_cls is PolicyEvaluationFailed:
            eval_uuid = UUID(payload.get("evaluation_id", ""))
            return PolicyEvaluationFailed(
                event_id=event_uuid,
                policy_id=PolicyId(value=aggregate_uuid),
                evaluation_id=EvaluationId(value=eval_uuid),
                failure_reason=payload.get("failure_reason", ""),
                occurred_at=dto.occurred_at,
            )

        raise ValueError(f"Unsupported event type: {event_cls}")

    @staticmethod
    def _get_aggregate_id(event: PolicyOutboxDomainEvent) -> str:
        if isinstance(
            event,
            (
                PolicyCreated,
                PolicyActivated,
                PolicyDisabled,
                PolicyArchived,
            ),
        ):
            return str(event.policy_id)
        if isinstance(
            event,
            (
                PolicyRuleAdded,
                PolicyRuleRemoved,
                PolicyRuleEnabled,
                PolicyRuleDisabled,
            ),
        ):
            return str(event.policy_id)
        if isinstance(
            event,
            (
                PolicyEvaluationStarted,
                PolicyEvaluationCompleted,
                PolicyEvaluationFailed,
            ),
        ):
            return str(event.policy_id)
        return ""

    @staticmethod
    def _build_payload(event: PolicyOutboxDomainEvent) -> dict | None:
        if isinstance(event, PolicyCreated):
            return {
                "name": event.name,
                "description": event.description,
                "priority": event.priority,
                "scope": event.scope,
                "version": event.version,
            }
        if isinstance(event, PolicyRuleAdded):
            return {
                "rule_id": str(event.rule_id),
                "condition": event.condition,
                "action": event.action,
            }
        if isinstance(event, PolicyEvaluationStarted):
            return {"evaluation_id": str(event.evaluation_id)}
        if isinstance(event, PolicyEvaluationCompleted):
            return {
                "evaluation_id": str(event.evaluation_id),
                "decision": event.decision,
                "result": event.result,
            }
        if isinstance(event, PolicyEvaluationFailed):
            return {
                "evaluation_id": str(event.evaluation_id),
                "failure_reason": event.failure_reason,
            }
        return None

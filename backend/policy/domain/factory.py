from __future__ import annotations

from datetime import datetime, timezone

from backend.policy.domain.model import (
    EvaluationId,
    EvaluationResult,
    FailureReason,
    Policy,
    PolicyAction,
    PolicyCondition,
    PolicyCreated,
    PolicyDecision,
    PolicyDescription,
    PolicyEvaluationCompleted,
    PolicyEvaluationFailed,
    PolicyEvaluationStarted,
    PolicyId,
    PolicyName,
    PolicyPriority,
    PolicyRule,
    PolicyRuleAdded,
    PolicyRuleId,
    PolicyScope,
    PolicyStatus,
    PolicyVersion,
)
from backend.policy.domain.rules import (
    assert_policy_description_required,
    assert_policy_name_required,
    assert_policy_version_required,
    assert_priority_valid,
    assert_rule_action_required,
    assert_rule_condition_required,
)


class PolicyFactory:
    """Factory for creating validated policy domain aggregates."""

    @staticmethod
    def create_policy(
        *,
        name: str,
        description: str,
        priority: str | PolicyPriority = PolicyPriority.MEDIUM,
        scope: str | PolicyScope = PolicyScope.GLOBAL,
        version: str = "1.0.0",
    ) -> tuple[Policy, PolicyCreated]:
        assert_policy_name_required(name)
        assert_policy_description_required(description)
        assert_policy_version_required(version)

        if isinstance(priority, str):
            priority = PolicyPriority(priority)

        if isinstance(scope, str):
            scope = PolicyScope(scope)

        name_vo = PolicyName(value=name)
        description_vo = PolicyDescription(value=description)
        version_vo = PolicyVersion(value=version)
        now = datetime.now(tz=timezone.utc)

        policy = Policy(
            policy_id=PolicyId(),
            name=name_vo,
            description=description_vo,
            status=PolicyStatus.DRAFT,
            priority=priority,
            scope=scope,
            version=version_vo,
            created_at=now,
        )

        event = PolicyCreated(
            policy_id=policy.policy_id,
            name=name,
            description=description,
            priority=priority.value,
            scope=scope.value,
            version=version,
            occurred_at=now,
        )

        return policy, event

    @staticmethod
    def add_rule(
        *,
        policy: Policy,
        condition: str,
        action: str,
        priority: int = 0,
    ) -> tuple[PolicyRule, PolicyRuleAdded]:
        assert_rule_condition_required(condition)
        assert_rule_action_required(action)
        assert_priority_valid(priority)

        condition_vo = PolicyCondition(value=condition)
        action_vo = PolicyAction(value=action)

        rule = PolicyRule(
            rule_id=PolicyRuleId(),
            condition=condition_vo,
            action=action_vo,
            priority=priority,
        )

        policy.add_rule(rule)
        event = policy.events[-1]

        return rule, event

    @staticmethod
    def remove_rule(
        *,
        policy: Policy,
        rule_id: PolicyRuleId,
    ) -> None:
        policy.remove_rule(rule_id)

    @staticmethod
    def enable_rule(
        *,
        policy: Policy,
        rule_id: PolicyRuleId,
    ) -> None:
        policy.enable_rule(rule_id)

    @staticmethod
    def disable_rule(
        *,
        policy: Policy,
        rule_id: PolicyRuleId,
    ) -> None:
        policy.disable_rule(rule_id)

    @staticmethod
    def start_evaluation(
        *,
        policy: Policy,
    ) -> tuple[PolicyEvaluation, PolicyEvaluationStarted]:
        evaluation = policy.start_evaluation()
        event = policy.events[-1]
        return evaluation, event

    @staticmethod
    def complete_evaluation(
        *,
        policy: Policy,
        evaluation_id: EvaluationId,
        decision: str | PolicyDecision,
        result: str,
    ) -> PolicyEvaluationCompleted:
        if isinstance(decision, str):
            decision = PolicyDecision(decision)
        result_vo = EvaluationResult(value=result)
        policy.complete_evaluation(evaluation_id, decision, result_vo)
        return policy.events[-1]

    @staticmethod
    def fail_evaluation(
        *,
        policy: Policy,
        evaluation_id: EvaluationId,
        reason: str,
    ) -> PolicyEvaluationFailed:
        reason_vo = FailureReason(value=reason)
        policy.fail_evaluation(evaluation_id, reason_vo)
        return policy.events[-1]

    @staticmethod
    def activate(policy: Policy) -> None:
        policy.activate()

    @staticmethod
    def disable(policy: Policy) -> None:
        policy.disable()

    @staticmethod
    def archive(policy: Policy) -> None:
        policy.archive()

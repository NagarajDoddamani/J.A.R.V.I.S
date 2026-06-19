from __future__ import annotations

from backend.policy.domain.model import (
    Policy,
    PolicyDecision,
    PolicyEvaluation,
    PolicyEvaluationStatus,
    PolicyRule,
    PolicyStatus,
    VALID_POLICY_TRANSITIONS,
    VALID_EVALUATION_TRANSITIONS,
)


# -- Name -----------------------------------------------------------------


def assert_policy_name_required(name: str | None) -> None:
    if not name or not name.strip():
        from backend.policy.domain.exceptions import InvalidPolicyNameError

        raise InvalidPolicyNameError("Policy name is required")


# -- Description ----------------------------------------------------------


def assert_policy_description_required(description: str | None) -> None:
    if not description or not description.strip():
        from backend.policy.domain.exceptions import InvalidPolicyDescriptionError

        raise InvalidPolicyDescriptionError("Policy description is required")


# -- Version --------------------------------------------------------------


def assert_policy_version_required(version: str | None) -> None:
    if not version or not version.strip():
        from backend.policy.domain.exceptions import InvalidPolicyVersionError

        raise InvalidPolicyVersionError("Policy version is required")


# -- Rule condition -------------------------------------------------------


def assert_rule_condition_required(condition: str | None) -> None:
    if not condition or not condition.strip():
        from backend.policy.domain.exceptions import InvalidPolicyConditionError

        raise InvalidPolicyConditionError("Rule condition is required")


# -- Rule action ----------------------------------------------------------


def assert_rule_action_required(action: str | None) -> None:
    if not action or not action.strip():
        from backend.policy.domain.exceptions import InvalidPolicyActionError

        raise InvalidPolicyActionError("Rule action is required")


# -- Has rules ------------------------------------------------------------


def assert_policy_has_rules(policy: Policy) -> None:
    if not policy.rules:
        from backend.policy.domain.exceptions import PolicyHasNoRulesError

        raise PolicyHasNoRulesError(
            "Policy must have at least one rule before activation"
        )


# -- Not disabled ---------------------------------------------------------


def assert_policy_not_disabled(policy: Policy) -> None:
    if policy.status == PolicyStatus.DISABLED:
        from backend.policy.domain.exceptions import PolicyDisabledError

        raise PolicyDisabledError()


# -- Modifiable -----------------------------------------------------------


def assert_policy_modifiable(policy: Policy) -> None:
    if not policy.is_modifiable:
        from backend.policy.domain.exceptions import PolicyNotModifiableError

        raise PolicyNotModifiableError(policy.status.value)


# -- Terminal states ------------------------------------------------------


def assert_policy_not_terminal(policy: Policy) -> None:
    if policy.is_terminal:
        from backend.policy.domain.exceptions import PolicyTerminalError

        raise PolicyTerminalError(policy.status.value)


# -- Transition guards ----------------------------------------------------


def assert_policy_can_transition(
    current: PolicyStatus, target: PolicyStatus
) -> None:
    allowed = VALID_POLICY_TRANSITIONS.get(current, set())
    if target not in allowed:
        from backend.policy.domain.exceptions import InvalidTransitionError

        raise InvalidTransitionError(current.value, target.value)


def assert_evaluation_can_transition(
    current: PolicyEvaluationStatus, target: PolicyEvaluationStatus
) -> None:
    allowed = VALID_EVALUATION_TRANSITIONS.get(current, set())
    if target not in allowed:
        from backend.policy.domain.exceptions import InvalidTransitionError

        raise InvalidTransitionError(current.value, target.value)


# -- Evaluation guards ----------------------------------------------------


def assert_evaluation_started_before(evaluation: PolicyEvaluation, action: str) -> None:
    if evaluation.status not in (PolicyEvaluationStatus.EVALUATING,):
        from backend.policy.domain.exceptions import (
            EvaluationNotStartedError,
        )

        raise EvaluationNotStartedError(action)


def assert_decision_required(decision: PolicyDecision | None) -> None:
    if decision is None:
        from backend.policy.domain.exceptions import DecisionRequiredError

        raise DecisionRequiredError()


def assert_evaluation_result_required(result: object | None) -> None:
    if result is None:
        from backend.policy.domain.exceptions import InvalidEvaluationResultError

        raise InvalidEvaluationResultError("Evaluation result is required")


def assert_failure_reason_required(reason: object | None) -> None:
    if reason is None:
        from backend.policy.domain.exceptions import InvalidFailureReasonError

        raise InvalidFailureReasonError("Failure reason is required")


# -- Uniqueness guards ----------------------------------------------------


def assert_rule_id_unique(rule_id, existing_rules: list[PolicyRule]) -> None:
    for rule in existing_rules:
        if rule.rule_id == rule_id:
            from backend.policy.domain.exceptions import DuplicateRuleIdError

            raise DuplicateRuleIdError(str(rule_id))


def assert_rule_condition_unique(condition, existing_rules: list[PolicyRule]) -> None:
    if condition is None:
        return
    for rule in existing_rules:
        if rule.condition is not None and rule.condition == condition:
            from backend.policy.domain.exceptions import (
                DuplicateRuleConditionError,
            )

            raise DuplicateRuleConditionError(str(condition))


# -- Rule guards ----------------------------------------------------------


def assert_rule_not_enabled_twice(rule: PolicyRule) -> None:
    if rule.enabled:
        from backend.policy.domain.exceptions import RuleAlreadyEnabledError

        raise RuleAlreadyEnabledError()


def assert_rule_not_disabled_twice(rule: PolicyRule) -> None:
    if not rule.enabled:
        from backend.policy.domain.exceptions import RuleAlreadyDisabledError

        raise RuleAlreadyDisabledError()


# -- Priority -------------------------------------------------------------


def assert_priority_valid(priority: object) -> None:
    if not isinstance(priority, int) or priority < 0 or priority > 100:
        from backend.policy.domain.exceptions import InvalidPriorityError

        raise InvalidPriorityError()

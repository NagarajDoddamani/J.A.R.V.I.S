from __future__ import annotations


class PolicyDomainError(Exception):
    """Base exception for policy domain errors."""

    def __init__(self, message: str = "") -> None:
        self.message = message
        super().__init__(message)


class InvalidPolicyNameError(PolicyDomainError):
    pass


class InvalidPolicyDescriptionError(PolicyDomainError):
    pass


class InvalidPolicyConditionError(PolicyDomainError):
    pass


class InvalidPolicyActionError(PolicyDomainError):
    pass


class InvalidPolicyVersionError(PolicyDomainError):
    pass


class InvalidFailureReasonError(PolicyDomainError):
    pass


class InvalidEvaluationResultError(PolicyDomainError):
    pass


class InvalidTransitionError(PolicyDomainError):
    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition from {current} to {target}")


class PolicyTerminalError(PolicyDomainError):
    def __init__(self, status: str) -> None:
        self.status = status
        super().__init__(f"Policy is terminal in status {status}")


class PolicyNotModifiableError(PolicyDomainError):
    def __init__(self, status: str) -> None:
        self.status = status
        super().__init__(f"Policy cannot be modified in status {status}")


class PolicyHasNoRulesError(PolicyDomainError):
    pass


class PolicyDisabledError(PolicyDomainError):
    def __init__(self) -> None:
        super().__init__("Policy is disabled and cannot be evaluated")


class EvaluationNotStartedError(PolicyDomainError):
    def __init__(self, action: str) -> None:
        self.action = action
        super().__init__(f"Evaluation must start before {action}")


class RuleNotFoundError(PolicyDomainError):
    def __init__(self, rule_id: str) -> None:
        self.rule_id = rule_id
        super().__init__(f"Rule not found: {rule_id}")


class EvaluationNotFoundError(PolicyDomainError):
    def __init__(self, evaluation_id: str) -> None:
        self.evaluation_id = evaluation_id
        super().__init__(f"Evaluation not found: {evaluation_id}")


class DuplicateRuleIdError(PolicyDomainError):
    def __init__(self, rule_id: str) -> None:
        self.rule_id = rule_id
        super().__init__(f"Duplicate rule ID: {rule_id}")


class DuplicateRuleConditionError(PolicyDomainError):
    def __init__(self, condition: str) -> None:
        self.condition = condition
        super().__init__(f"Duplicate rule condition: {condition}")


class RuleAlreadyEnabledError(PolicyDomainError):
    def __init__(self) -> None:
        super().__init__("Rule is already enabled")


class RuleAlreadyDisabledError(PolicyDomainError):
    def __init__(self) -> None:
        super().__init__("Rule is already disabled")


class InvalidPriorityError(PolicyDomainError):
    def __init__(self) -> None:
        super().__init__("Policy priority is invalid")


class DecisionRequiredError(PolicyDomainError):
    def __init__(self) -> None:
        super().__init__("Decision is required on complete")

from __future__ import annotations


class UseCaseError(Exception):
    """Base exception for all use-case-level errors."""


class PolicyNotFoundError(UseCaseError):
    def __init__(self, policy_id: str) -> None:
        super().__init__(f"Policy not found: {policy_id}")
        self.policy_id = policy_id


class PolicyRuleNotFoundError(UseCaseError):
    def __init__(self, rule_id: str) -> None:
        super().__init__(f"Policy rule not found: {rule_id}")
        self.rule_id = rule_id


class PolicyEvaluationNotFoundError(UseCaseError):
    def __init__(self, evaluation_id: str) -> None:
        super().__init__(f"Policy evaluation not found: {evaluation_id}")
        self.evaluation_id = evaluation_id

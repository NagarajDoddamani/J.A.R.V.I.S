from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RuleResponse:
    rule_id: str
    policy_id: str | None = None
    condition: str | None = None
    action: str | None = None
    priority: int = 0
    enabled: bool = True


@dataclass
class EvaluationResponse:
    evaluation_id: str
    policy_id: str | None = None
    status: str = "pending"
    decision: str | None = None
    result: str | None = None
    failure_reason: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class PolicyResponse:
    policy_id: str
    name: str | None = None
    description: str | None = None
    status: str = "draft"
    priority: str = "medium"
    scope: str = "global"
    version: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    rule_count: int = 0
    evaluation_count: int = 0


@dataclass
class CreatePolicyRequest:
    name: str
    description: str
    priority: str = "medium"
    scope: str = "global"
    version: str = "1.0.0"


@dataclass
class CreatePolicyResponse:
    policy_id: str
    name: str | None
    description: str | None
    status: str
    priority: str
    scope: str
    version: str | None
    created_at: datetime


@dataclass
class PolicyLifecycleRequest:
    policy_id: str


@dataclass
class PolicyLifecycleResponse:
    policy_id: str
    status: str
    updated_at: datetime | None = None


@dataclass
class AddRuleRequest:
    policy_id: str
    condition: str
    action: str
    priority: int = 0


@dataclass
class AddRuleResponse:
    rule_id: str
    policy_id: str | None
    condition: str | None
    action: str | None
    priority: int
    enabled: bool


@dataclass
class RemoveRuleRequest:
    policy_id: str
    rule_id: str


@dataclass
class RemoveRuleResponse:
    policy_id: str
    rule_id: str


@dataclass
class RuleLifecycleRequest:
    rule_id: str


@dataclass
class RuleLifecycleResponse:
    rule_id: str
    enabled: bool


@dataclass
class StartEvaluationRequest:
    policy_id: str


@dataclass
class StartEvaluationResponse:
    evaluation_id: str
    policy_id: str
    status: str
    started_at: datetime | None = None


@dataclass
class CompleteEvaluationRequest:
    policy_id: str
    evaluation_id: str
    decision: str
    result: str


@dataclass
class CompleteEvaluationResponse:
    evaluation_id: str
    policy_id: str | None
    status: str
    decision: str | None = None
    result: str | None = None
    completed_at: datetime | None = None


@dataclass
class FailEvaluationRequest:
    policy_id: str
    evaluation_id: str
    failure_reason: str


@dataclass
class FailEvaluationResponse:
    evaluation_id: str
    policy_id: str | None
    status: str
    completed_at: datetime | None = None
    failure_reason: str | None = None


@dataclass
class GetPolicyRequest:
    policy_id: str


@dataclass
class ListPoliciesRequest:
    status: str | None = None
    priority: str | None = None
    scope: str | None = None


@dataclass
class ListPoliciesResponse:
    policies: list[PolicyResponse] = field(default_factory=list)
    total: int = 0


@dataclass
class GetRuleRequest:
    rule_id: str


@dataclass
class ListRulesRequest:
    policy_id: str | None = None
    priority: int | None = None
    enabled: bool | None = None


@dataclass
class ListRulesResponse:
    rules: list[RuleResponse] = field(default_factory=list)
    total: int = 0


@dataclass
class GetEvaluationRequest:
    evaluation_id: str


@dataclass
class ListEvaluationsRequest:
    status: str | None = None
    policy_id: str | None = None


@dataclass
class ListEvaluationsResponse:
    evaluations: list[EvaluationResponse] = field(default_factory=list)
    total: int = 0

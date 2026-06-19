from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.policy.application.use_cases.dto import (
    AddRuleRequest,
    AddRuleResponse,
    CompleteEvaluationRequest,
    CompleteEvaluationResponse,
    CreatePolicyRequest,
    CreatePolicyResponse,
    EvaluationResponse,
    FailEvaluationRequest,
    FailEvaluationResponse,
    GetEvaluationRequest,
    GetPolicyRequest,
    GetRuleRequest,
    ListEvaluationsRequest,
    ListEvaluationsResponse,
    ListPoliciesRequest,
    ListPoliciesResponse,
    ListRulesRequest,
    ListRulesResponse,
    PolicyLifecycleRequest,
    PolicyLifecycleResponse,
    PolicyResponse,
    RemoveRuleRequest,
    RemoveRuleResponse,
    RuleLifecycleRequest,
    RuleLifecycleResponse,
    RuleResponse,
    StartEvaluationRequest,
    StartEvaluationResponse,
)
from backend.policy.application.use_cases.exceptions import (
    PolicyEvaluationNotFoundError,
    PolicyNotFoundError,
    PolicyRuleNotFoundError,
)
from backend.policy.bootstrap import (
    get_activate_policy_use_case,
    get_add_rule_use_case,
    get_archive_policy_use_case,
    get_complete_evaluation_use_case,
    get_create_policy_use_case,
    get_disable_policy_use_case,
    get_disable_rule_use_case,
    get_enable_rule_use_case,
    get_evaluation_use_case,
    get_fail_evaluation_use_case,
    get_list_evaluations_use_case,
    get_list_policies_use_case,
    get_list_rules_use_case,
    get_policy_use_case,
    get_remove_rule_use_case,
    get_rule_use_case,
    get_start_evaluation_use_case,
)
from backend.policy.domain.exceptions import PolicyDomainError

router = APIRouter()


def _value_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


# =====================================================================
# Policy CRUD + lifecycle
# =====================================================================


@router.post(
    "/",
    status_code=201,
    response_model=CreatePolicyResponse,
)
def create_policy(
    body: CreatePolicyRequest,
    use_case=Depends(get_create_policy_use_case),
) -> CreatePolicyResponse:
    try:
        return use_case.execute(body)
    except PolicyDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/",
    response_model=ListPoliciesResponse,
)
def list_policies(
    status: str | None = Query(None),
    priority: str | None = Query(None),
    scope: str | None = Query(None),
    use_case=Depends(get_list_policies_use_case),
) -> ListPoliciesResponse:
    try:
        return use_case.execute(
            ListPoliciesRequest(status=status, priority=priority, scope=scope)
        )
    except ValueError as exc:
        raise _value_error(exc)


# =====================================================================
# Rule CRUD + lifecycle (fixed paths before /{policy_id})
# =====================================================================


@router.delete(
    "/rules/{rule_id}",
    response_model=RemoveRuleResponse,
)
def remove_rule(
    rule_id: str,
    policy_id: str = Query(...),
    use_case=Depends(get_remove_rule_use_case),
) -> RemoveRuleResponse:
    try:
        return use_case.execute(
            RemoveRuleRequest(policy_id=policy_id, rule_id=rule_id)
        )
    except PolicyNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Policy not found: {policy_id}"
        )
    except PolicyDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/rules/{rule_id}/enable",
    response_model=RuleLifecycleResponse,
)
def enable_rule(
    rule_id: str,
    use_case=Depends(get_enable_rule_use_case),
) -> RuleLifecycleResponse:
    try:
        return use_case.execute(RuleLifecycleRequest(rule_id=rule_id))
    except PolicyRuleNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Rule not found: {rule_id}"
        )
    except PolicyDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/rules/{rule_id}/disable",
    response_model=RuleLifecycleResponse,
)
def disable_rule(
    rule_id: str,
    use_case=Depends(get_disable_rule_use_case),
) -> RuleLifecycleResponse:
    try:
        return use_case.execute(RuleLifecycleRequest(rule_id=rule_id))
    except PolicyRuleNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Rule not found: {rule_id}"
        )
    except PolicyDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.get(
    "/rules/{rule_id}",
    response_model=RuleResponse,
)
def get_rule(
    rule_id: str,
    use_case=Depends(get_rule_use_case),
) -> RuleResponse:
    try:
        return use_case.execute(GetRuleRequest(rule_id=rule_id))
    except PolicyRuleNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Rule not found: {rule_id}"
        )
    except ValueError as exc:
        raise _value_error(exc)


@router.get(
    "/rules",
    response_model=ListRulesResponse,
)
def list_rules(
    policy_id: str | None = Query(None),
    priority: int | None = Query(None),
    enabled: bool | None = Query(None),
    use_case=Depends(get_list_rules_use_case),
) -> ListRulesResponse:
    return use_case.execute(
        ListRulesRequest(
            policy_id=policy_id, priority=priority, enabled=enabled
        )
    )


# =====================================================================
# Evaluation lifecycle (fixed paths before /{policy_id})
# =====================================================================


@router.post(
    "/evaluations/{evaluation_id}/complete",
    response_model=CompleteEvaluationResponse,
)
def complete_evaluation(
    evaluation_id: str,
    body: CompleteEvaluationRequest,
    use_case=Depends(get_complete_evaluation_use_case),
) -> CompleteEvaluationResponse:
    try:
        return use_case.execute(
            CompleteEvaluationRequest(
                policy_id=body.policy_id,
                evaluation_id=evaluation_id,
                decision=body.decision,
                result=body.result,
            )
        )
    except PolicyNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Policy not found: {body.policy_id}",
        )
    except PolicyDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/evaluations/{evaluation_id}/fail",
    response_model=FailEvaluationResponse,
)
def fail_evaluation(
    evaluation_id: str,
    body: FailEvaluationRequest,
    use_case=Depends(get_fail_evaluation_use_case),
) -> FailEvaluationResponse:
    try:
        return use_case.execute(
            FailEvaluationRequest(
                policy_id=body.policy_id,
                evaluation_id=evaluation_id,
                failure_reason=body.failure_reason,
            )
        )
    except PolicyNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Policy not found: {body.policy_id}",
        )
    except PolicyDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.get(
    "/evaluations/{evaluation_id}",
    response_model=EvaluationResponse,
)
def get_evaluation(
    evaluation_id: str,
    use_case=Depends(get_evaluation_use_case),
) -> EvaluationResponse:
    try:
        return use_case.execute(
            GetEvaluationRequest(evaluation_id=evaluation_id)
        )
    except PolicyEvaluationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Evaluation not found: {evaluation_id}",
        )
    except ValueError as exc:
        raise _value_error(exc)


@router.get(
    "/evaluations",
    response_model=ListEvaluationsResponse,
)
def list_evaluations(
    status: str | None = Query(None),
    policy_id: str | None = Query(None),
    use_case=Depends(get_list_evaluations_use_case),
) -> ListEvaluationsResponse:
    return use_case.execute(
        ListEvaluationsRequest(status=status, policy_id=policy_id)
    )


# =====================================================================
# Policy lifecycle (path-parameter routes after fixed paths)
# =====================================================================


@router.post(
    "/{policy_id}/activate",
    response_model=PolicyLifecycleResponse,
)
def activate_policy(
    policy_id: str,
    use_case=Depends(get_activate_policy_use_case),
) -> PolicyLifecycleResponse:
    try:
        return use_case.execute(PolicyLifecycleRequest(policy_id=policy_id))
    except PolicyNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Policy not found: {policy_id}"
        )
    except PolicyDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/{policy_id}/disable",
    response_model=PolicyLifecycleResponse,
)
def disable_policy(
    policy_id: str,
    use_case=Depends(get_disable_policy_use_case),
) -> PolicyLifecycleResponse:
    try:
        return use_case.execute(PolicyLifecycleRequest(policy_id=policy_id))
    except PolicyNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Policy not found: {policy_id}"
        )
    except PolicyDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/{policy_id}/archive",
    response_model=PolicyLifecycleResponse,
)
def archive_policy(
    policy_id: str,
    use_case=Depends(get_archive_policy_use_case),
) -> PolicyLifecycleResponse:
    try:
        return use_case.execute(PolicyLifecycleRequest(policy_id=policy_id))
    except PolicyNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Policy not found: {policy_id}"
        )
    except PolicyDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/{policy_id}/rules",
    status_code=201,
    response_model=AddRuleResponse,
)
def add_rule(
    policy_id: str,
    body: AddRuleRequest,
    use_case=Depends(get_add_rule_use_case),
) -> AddRuleResponse:
    try:
        return use_case.execute(
            AddRuleRequest(
                policy_id=policy_id,
                condition=body.condition,
                action=body.action,
                priority=body.priority,
            )
        )
    except PolicyNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Policy not found: {policy_id}"
        )
    except PolicyDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/{policy_id}/evaluations/start",
    status_code=201,
    response_model=StartEvaluationResponse,
)
def start_evaluation(
    policy_id: str,
    use_case=Depends(get_start_evaluation_use_case),
) -> StartEvaluationResponse:
    try:
        return use_case.execute(
            StartEvaluationRequest(policy_id=policy_id)
        )
    except PolicyNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Policy not found: {policy_id}"
        )
    except PolicyDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.get(
    "/{policy_id}",
    response_model=PolicyResponse,
)
def get_policy(
    policy_id: str,
    use_case=Depends(get_policy_use_case),
) -> PolicyResponse:
    try:
        return use_case.execute(GetPolicyRequest(policy_id=policy_id))
    except PolicyNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Policy not found: {policy_id}"
        )
    except ValueError as exc:
        raise _value_error(exc)

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.policy.adapters.outbound.clock import SystemClockAdapter
from backend.policy.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.policy.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyPolicyEvaluationRepository,
    SqlAlchemyPolicyOutboxAdapter,
    SqlAlchemyPolicyRepository,
    SqlAlchemyPolicyRuleRepository,
)
from backend.policy.application.use_cases.activate_policy import (
    ActivatePolicyUseCase,
)
from backend.policy.application.use_cases.add_rule import AddRuleUseCase
from backend.policy.application.use_cases.archive_policy import (
    ArchivePolicyUseCase,
)
from backend.policy.application.use_cases.complete_evaluation import (
    CompleteEvaluationUseCase,
)
from backend.policy.application.use_cases.create_policy import (
    CreatePolicyUseCase,
)
from backend.policy.application.use_cases.disable_policy import (
    DisablePolicyUseCase,
)
from backend.policy.application.use_cases.disable_rule import (
    DisableRuleUseCase,
)
from backend.policy.application.use_cases.enable_rule import EnableRuleUseCase
from backend.policy.application.use_cases.fail_evaluation import (
    FailEvaluationUseCase,
)
from backend.policy.application.use_cases.get_evaluation import (
    GetEvaluationUseCase,
)
from backend.policy.application.use_cases.get_policy import GetPolicyUseCase
from backend.policy.application.use_cases.get_rule import GetRuleUseCase
from backend.policy.application.use_cases.list_evaluations import (
    ListEvaluationsUseCase,
)
from backend.policy.application.use_cases.list_policies import (
    ListPoliciesUseCase,
)
from backend.policy.application.use_cases.list_rules import ListRulesUseCase
from backend.policy.application.use_cases.remove_rule import RemoveRuleUseCase
from backend.policy.application.use_cases.start_evaluation import (
    StartEvaluationUseCase,
)


def _policy_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyPolicyRepository:
    return SqlAlchemyPolicyRepository(db)


def _rule_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyPolicyRuleRepository:
    return SqlAlchemyPolicyRuleRepository(db)


def _evaluation_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyPolicyEvaluationRepository:
    return SqlAlchemyPolicyEvaluationRepository(db)


def _outbox(
    db: Session = Depends(get_db),
) -> SqlAlchemyPolicyOutboxAdapter:
    return SqlAlchemyPolicyOutboxAdapter(db)


def _clock() -> SystemClockAdapter:
    return SystemClockAdapter()


def _id_generator() -> UuidGeneratorAdapter:
    return UuidGeneratorAdapter()


# -- Policy commands -----------------------------------------------------


def get_create_policy_use_case(
    policy_repo: SqlAlchemyPolicyRepository = Depends(_policy_repo),
    outbox: SqlAlchemyPolicyOutboxAdapter = Depends(_outbox),
) -> CreatePolicyUseCase:
    return CreatePolicyUseCase(policy_repo=policy_repo, outbox=outbox)


def get_activate_policy_use_case(
    policy_repo: SqlAlchemyPolicyRepository = Depends(_policy_repo),
    outbox: SqlAlchemyPolicyOutboxAdapter = Depends(_outbox),
) -> ActivatePolicyUseCase:
    return ActivatePolicyUseCase(policy_repo=policy_repo, outbox=outbox)


def get_disable_policy_use_case(
    policy_repo: SqlAlchemyPolicyRepository = Depends(_policy_repo),
    outbox: SqlAlchemyPolicyOutboxAdapter = Depends(_outbox),
) -> DisablePolicyUseCase:
    return DisablePolicyUseCase(policy_repo=policy_repo, outbox=outbox)


def get_archive_policy_use_case(
    policy_repo: SqlAlchemyPolicyRepository = Depends(_policy_repo),
    outbox: SqlAlchemyPolicyOutboxAdapter = Depends(_outbox),
) -> ArchivePolicyUseCase:
    return ArchivePolicyUseCase(policy_repo=policy_repo, outbox=outbox)


# -- Rule commands -------------------------------------------------------


def get_add_rule_use_case(
    policy_repo: SqlAlchemyPolicyRepository = Depends(_policy_repo),
    rule_repo: SqlAlchemyPolicyRuleRepository = Depends(_rule_repo),
    outbox: SqlAlchemyPolicyOutboxAdapter = Depends(_outbox),
) -> AddRuleUseCase:
    return AddRuleUseCase(
        policy_repo=policy_repo,
        rule_repo=rule_repo,
        outbox=outbox,
    )


def get_remove_rule_use_case(
    policy_repo: SqlAlchemyPolicyRepository = Depends(_policy_repo),
    outbox: SqlAlchemyPolicyOutboxAdapter = Depends(_outbox),
) -> RemoveRuleUseCase:
    return RemoveRuleUseCase(policy_repo=policy_repo, outbox=outbox)


def get_enable_rule_use_case(
    rule_repo: SqlAlchemyPolicyRuleRepository = Depends(_rule_repo),
    policy_repo: SqlAlchemyPolicyRepository = Depends(_policy_repo),
    outbox: SqlAlchemyPolicyOutboxAdapter = Depends(_outbox),
) -> EnableRuleUseCase:
    return EnableRuleUseCase(
        rule_repo=rule_repo,
        policy_repo=policy_repo,
        outbox=outbox,
    )


def get_disable_rule_use_case(
    rule_repo: SqlAlchemyPolicyRuleRepository = Depends(_rule_repo),
    policy_repo: SqlAlchemyPolicyRepository = Depends(_policy_repo),
    outbox: SqlAlchemyPolicyOutboxAdapter = Depends(_outbox),
) -> DisableRuleUseCase:
    return DisableRuleUseCase(
        rule_repo=rule_repo,
        policy_repo=policy_repo,
        outbox=outbox,
    )


# -- Evaluation commands -------------------------------------------------


def get_start_evaluation_use_case(
    policy_repo: SqlAlchemyPolicyRepository = Depends(_policy_repo),
    evaluation_repo: SqlAlchemyPolicyEvaluationRepository = Depends(
        _evaluation_repo
    ),
    outbox: SqlAlchemyPolicyOutboxAdapter = Depends(_outbox),
) -> StartEvaluationUseCase:
    return StartEvaluationUseCase(
        policy_repo=policy_repo,
        evaluation_repo=evaluation_repo,
        outbox=outbox,
    )


def get_complete_evaluation_use_case(
    policy_repo: SqlAlchemyPolicyRepository = Depends(_policy_repo),
    evaluation_repo: SqlAlchemyPolicyEvaluationRepository = Depends(
        _evaluation_repo
    ),
    outbox: SqlAlchemyPolicyOutboxAdapter = Depends(_outbox),
) -> CompleteEvaluationUseCase:
    return CompleteEvaluationUseCase(
        policy_repo=policy_repo,
        evaluation_repo=evaluation_repo,
        outbox=outbox,
    )


def get_fail_evaluation_use_case(
    policy_repo: SqlAlchemyPolicyRepository = Depends(_policy_repo),
    evaluation_repo: SqlAlchemyPolicyEvaluationRepository = Depends(
        _evaluation_repo
    ),
    outbox: SqlAlchemyPolicyOutboxAdapter = Depends(_outbox),
) -> FailEvaluationUseCase:
    return FailEvaluationUseCase(
        policy_repo=policy_repo,
        evaluation_repo=evaluation_repo,
        outbox=outbox,
    )


# -- Queries -------------------------------------------------------------


def get_policy_use_case(
    policy_repo: SqlAlchemyPolicyRepository = Depends(_policy_repo),
) -> GetPolicyUseCase:
    return GetPolicyUseCase(policy_repo=policy_repo)


def get_list_policies_use_case(
    policy_repo: SqlAlchemyPolicyRepository = Depends(_policy_repo),
) -> ListPoliciesUseCase:
    return ListPoliciesUseCase(policy_repo=policy_repo)


def get_rule_use_case(
    rule_repo: SqlAlchemyPolicyRuleRepository = Depends(_rule_repo),
) -> GetRuleUseCase:
    return GetRuleUseCase(rule_repo=rule_repo)


def get_list_rules_use_case(
    rule_repo: SqlAlchemyPolicyRuleRepository = Depends(_rule_repo),
) -> ListRulesUseCase:
    return ListRulesUseCase(rule_repo=rule_repo)


def get_evaluation_use_case(
    evaluation_repo: SqlAlchemyPolicyEvaluationRepository = Depends(
        _evaluation_repo
    ),
) -> GetEvaluationUseCase:
    return GetEvaluationUseCase(evaluation_repo=evaluation_repo)


def get_list_evaluations_use_case(
    evaluation_repo: SqlAlchemyPolicyEvaluationRepository = Depends(
        _evaluation_repo
    ),
) -> ListEvaluationsUseCase:
    return ListEvaluationsUseCase(evaluation_repo=evaluation_repo)

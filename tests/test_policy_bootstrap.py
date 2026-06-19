from __future__ import annotations

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.api.endpoints import policy
from backend.policy.adapters.outbound.models import Base
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
from backend.core.database import get_db

for _table in Base.metadata.tables.values():
    _table.schema = None


class TestBootstrapProviders:
    def test_create_policy_use_case_provider(self) -> None:
        with patch("backend.policy.bootstrap.get_db"):
            uc = get_create_policy_use_case()
            assert isinstance(uc, CreatePolicyUseCase)

    def test_activate_policy_use_case_provider(self) -> None:
        with patch("backend.policy.bootstrap.get_db"):
            uc = get_activate_policy_use_case()
            assert isinstance(uc, ActivatePolicyUseCase)

    def test_disable_policy_use_case_provider(self) -> None:
        with patch("backend.policy.bootstrap.get_db"):
            uc = get_disable_policy_use_case()
            assert isinstance(uc, DisablePolicyUseCase)

    def test_archive_policy_use_case_provider(self) -> None:
        with patch("backend.policy.bootstrap.get_db"):
            uc = get_archive_policy_use_case()
            assert isinstance(uc, ArchivePolicyUseCase)

    def test_add_rule_use_case_provider(self) -> None:
        with patch("backend.policy.bootstrap.get_db"):
            uc = get_add_rule_use_case()
            assert isinstance(uc, AddRuleUseCase)

    def test_remove_rule_use_case_provider(self) -> None:
        with patch("backend.policy.bootstrap.get_db"):
            uc = get_remove_rule_use_case()
            assert isinstance(uc, RemoveRuleUseCase)

    def test_enable_rule_use_case_provider(self) -> None:
        with patch("backend.policy.bootstrap.get_db"):
            uc = get_enable_rule_use_case()
            assert isinstance(uc, EnableRuleUseCase)

    def test_disable_rule_use_case_provider(self) -> None:
        with patch("backend.policy.bootstrap.get_db"):
            uc = get_disable_rule_use_case()
            assert isinstance(uc, DisableRuleUseCase)

    def test_start_evaluation_use_case_provider(self) -> None:
        with patch("backend.policy.bootstrap.get_db"):
            uc = get_start_evaluation_use_case()
            assert isinstance(uc, StartEvaluationUseCase)

    def test_complete_evaluation_use_case_provider(self) -> None:
        with patch("backend.policy.bootstrap.get_db"):
            uc = get_complete_evaluation_use_case()
            assert isinstance(uc, CompleteEvaluationUseCase)

    def test_fail_evaluation_use_case_provider(self) -> None:
        with patch("backend.policy.bootstrap.get_db"):
            uc = get_fail_evaluation_use_case()
            assert isinstance(uc, FailEvaluationUseCase)

    def test_get_policy_use_case_provider(self) -> None:
        with patch("backend.policy.bootstrap.get_db"):
            uc = get_policy_use_case()
            assert isinstance(uc, GetPolicyUseCase)

    def test_list_policies_use_case_provider(self) -> None:
        with patch("backend.policy.bootstrap.get_db"):
            uc = get_list_policies_use_case()
            assert isinstance(uc, ListPoliciesUseCase)

    def test_get_rule_use_case_provider(self) -> None:
        with patch("backend.policy.bootstrap.get_db"):
            uc = get_rule_use_case()
            assert isinstance(uc, GetRuleUseCase)

    def test_list_rules_use_case_provider(self) -> None:
        with patch("backend.policy.bootstrap.get_db"):
            uc = get_list_rules_use_case()
            assert isinstance(uc, ListRulesUseCase)

    def test_get_evaluation_use_case_provider(self) -> None:
        with patch("backend.policy.bootstrap.get_db"):
            uc = get_evaluation_use_case()
            assert isinstance(uc, GetEvaluationUseCase)

    def test_list_evaluations_use_case_provider(self) -> None:
        with patch("backend.policy.bootstrap.get_db"):
            uc = get_list_evaluations_use_case()
            assert isinstance(uc, ListEvaluationsUseCase)

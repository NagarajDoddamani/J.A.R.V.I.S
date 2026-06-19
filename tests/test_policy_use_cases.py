from __future__ import annotations

from uuid import UUID

import pytest

from backend.policy.application.ports.outbox import PolicyOutboxPort
from backend.policy.application.ports.repository import (
    PolicyEvaluationRepositoryPort,
    PolicyRepositoryPort,
    PolicyRuleRepositoryPort,
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
from backend.policy.application.use_cases.enable_rule import EnableRuleUseCase
from backend.policy.application.use_cases.exceptions import (
    PolicyEvaluationNotFoundError,
    PolicyNotFoundError,
    PolicyRuleNotFoundError,
    UseCaseError,
)
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
from backend.policy.application.use_cases.list_rules import (
    ListRulesUseCase,
)
from backend.policy.application.use_cases.remove_rule import RemoveRuleUseCase
from backend.policy.application.use_cases.start_evaluation import (
    StartEvaluationUseCase,
)
from backend.policy.domain.model import (
    EvaluationId,
    Policy,
    PolicyActivated,
    PolicyArchived,
    PolicyCreated,
    PolicyDisabled,
    PolicyEvaluation,
    PolicyEvaluationCompleted,
    PolicyEvaluationFailed,
    PolicyEvaluationStarted,
    PolicyId,
    PolicyRule,
    PolicyRuleAdded,
    PolicyRuleDisabled,
    PolicyRuleEnabled,
    PolicyRuleId,
    PolicyRuleRemoved,
    PolicyStatus,
)


class FakePolicyRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, Policy] = {}
        self.save_calls: list[Policy] = []

    def save(self, policy: Policy) -> None:
        self._store[policy.policy_id.value] = policy
        self.save_calls.append(policy)

    def find_by_id(self, policy_id: PolicyId) -> Policy | None:
        return self._store.get(policy_id.value)

    def find_by_status(self, status: PolicyStatus) -> list[Policy]:
        return [p for p in self._store.values() if p.status == status]

    def find_by_priority(self, priority: object) -> list[Policy]:
        return [p for p in self._store.values() if p.priority == priority]

    def find_by_scope(self, scope: object) -> list[Policy]:
        return [p for p in self._store.values() if p.scope == scope]

    def find_all(self) -> list[Policy]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class FakeRuleRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, PolicyRule] = {}
        self.save_calls: list[PolicyRule] = []

    def save(self, rule: PolicyRule, **kwargs: object) -> None:
        self._store[rule.rule_id.value] = rule
        self.save_calls.append(rule)

    def find_by_id(self, rule_id: PolicyRuleId) -> PolicyRule | None:
        return self._store.get(rule_id.value)

    def find_by_policy_id(self, policy_id: PolicyId) -> list[PolicyRule]:
        return list(self._store.values())

    def find_enabled(self) -> list[PolicyRule]:
        return [r for r in self._store.values() if r.enabled]

    def find_all(self) -> list[PolicyRule]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class FakeEvaluationRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, PolicyEvaluation] = {}
        self.save_calls: list[PolicyEvaluation] = []

    def save(self, evaluation: PolicyEvaluation) -> None:
        self._store[evaluation.evaluation_id.value] = evaluation
        self.save_calls.append(evaluation)

    def find_by_id(self, evaluation_id: EvaluationId) -> PolicyEvaluation | None:
        return self._store.get(evaluation_id.value)

    def find_by_status(self, status: object) -> list[PolicyEvaluation]:
        return [e for e in self._store.values() if e.status == status]

    def find_by_policy_id(self, policy_id: PolicyId) -> list[PolicyEvaluation]:
        return [e for e in self._store.values()]

    def find_all(self) -> list[PolicyEvaluation]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class FakePolicyOutbox:
    def __init__(self) -> None:
        self._events: list = []
        self.append_calls: list = []

    def append(self, event: object) -> None:
        self._events.append(event)
        self.append_calls.append(event)

    def fetch_unpublished(self, limit: int = 100) -> list:
        return list(self._events[:limit])

    def mark_published(self, aggregate_id: str) -> None:
        pass


@pytest.fixture
def fake_policy_repo() -> FakePolicyRepository:
    return FakePolicyRepository()


@pytest.fixture
def fake_rule_repo() -> FakeRuleRepository:
    return FakeRuleRepository()


@pytest.fixture
def fake_evaluation_repo() -> FakeEvaluationRepository:
    return FakeEvaluationRepository()


@pytest.fixture
def fake_outbox() -> FakePolicyOutbox:
    return FakePolicyOutbox()


@pytest.fixture
def create_policy_uc(
    fake_policy_repo: FakePolicyRepository,
    fake_outbox: FakePolicyOutbox,
) -> CreatePolicyUseCase:
    return CreatePolicyUseCase(
        policy_repo=fake_policy_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def activate_policy_uc(
    fake_policy_repo: FakePolicyRepository,
    fake_outbox: FakePolicyOutbox,
) -> ActivatePolicyUseCase:
    return ActivatePolicyUseCase(
        policy_repo=fake_policy_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def disable_policy_uc(
    fake_policy_repo: FakePolicyRepository,
    fake_outbox: FakePolicyOutbox,
) -> DisablePolicyUseCase:
    return DisablePolicyUseCase(
        policy_repo=fake_policy_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def archive_policy_uc(
    fake_policy_repo: FakePolicyRepository,
    fake_outbox: FakePolicyOutbox,
) -> ArchivePolicyUseCase:
    return ArchivePolicyUseCase(
        policy_repo=fake_policy_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def add_rule_uc(
    fake_policy_repo: FakePolicyRepository,
    fake_rule_repo: FakeRuleRepository,
    fake_outbox: FakePolicyOutbox,
) -> AddRuleUseCase:
    return AddRuleUseCase(
        policy_repo=fake_policy_repo,
        rule_repo=fake_rule_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def remove_rule_uc(
    fake_policy_repo: FakePolicyRepository,
    fake_outbox: FakePolicyOutbox,
) -> RemoveRuleUseCase:
    return RemoveRuleUseCase(
        policy_repo=fake_policy_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def enable_rule_uc(
    fake_rule_repo: FakeRuleRepository,
    fake_policy_repo: FakePolicyRepository,
    fake_outbox: FakePolicyOutbox,
) -> EnableRuleUseCase:
    return EnableRuleUseCase(
        rule_repo=fake_rule_repo,
        policy_repo=fake_policy_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def disable_rule_uc(
    fake_rule_repo: FakeRuleRepository,
    fake_policy_repo: FakePolicyRepository,
    fake_outbox: FakePolicyOutbox,
) -> DisableRuleUseCase:
    return DisableRuleUseCase(
        rule_repo=fake_rule_repo,
        policy_repo=fake_policy_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def start_evaluation_uc(
    fake_policy_repo: FakePolicyRepository,
    fake_evaluation_repo: FakeEvaluationRepository,
    fake_outbox: FakePolicyOutbox,
) -> StartEvaluationUseCase:
    return StartEvaluationUseCase(
        policy_repo=fake_policy_repo,
        evaluation_repo=fake_evaluation_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def complete_evaluation_uc(
    fake_policy_repo: FakePolicyRepository,
    fake_evaluation_repo: FakeEvaluationRepository,
    fake_outbox: FakePolicyOutbox,
) -> CompleteEvaluationUseCase:
    return CompleteEvaluationUseCase(
        policy_repo=fake_policy_repo,
        evaluation_repo=fake_evaluation_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def fail_evaluation_uc(
    fake_policy_repo: FakePolicyRepository,
    fake_evaluation_repo: FakeEvaluationRepository,
    fake_outbox: FakePolicyOutbox,
) -> FailEvaluationUseCase:
    return FailEvaluationUseCase(
        policy_repo=fake_policy_repo,
        evaluation_repo=fake_evaluation_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def get_policy_uc(
    fake_policy_repo: FakePolicyRepository,
) -> GetPolicyUseCase:
    return GetPolicyUseCase(policy_repo=fake_policy_repo)


@pytest.fixture
def list_policies_uc(
    fake_policy_repo: FakePolicyRepository,
) -> ListPoliciesUseCase:
    return ListPoliciesUseCase(policy_repo=fake_policy_repo)


@pytest.fixture
def get_rule_uc(
    fake_rule_repo: FakeRuleRepository,
) -> GetRuleUseCase:
    return GetRuleUseCase(rule_repo=fake_rule_repo)


@pytest.fixture
def list_rules_uc(
    fake_rule_repo: FakeRuleRepository,
) -> ListRulesUseCase:
    return ListRulesUseCase(rule_repo=fake_rule_repo)


@pytest.fixture
def get_evaluation_uc(
    fake_evaluation_repo: FakeEvaluationRepository,
) -> GetEvaluationUseCase:
    return GetEvaluationUseCase(evaluation_repo=fake_evaluation_repo)


@pytest.fixture
def list_evaluations_uc(
    fake_evaluation_repo: FakeEvaluationRepository,
) -> ListEvaluationsUseCase:
    return ListEvaluationsUseCase(evaluation_repo=fake_evaluation_repo)


def _create_policy(
    create_uc: CreatePolicyUseCase,
    name: str = "Test Policy",
    priority: str = "medium",
    scope: str = "global",
) -> tuple[CreatePolicyResponse, str]:
    request = CreatePolicyRequest(
        name=name,
        description="A test policy",
        priority=priority,
        scope=scope,
        version="1.0.0",
    )
    response = create_uc.execute(request)
    return response, response.policy_id


def _add_rule_to_policy(
    add_uc: AddRuleUseCase,
    policy_id: str,
    condition: str = "true",
    action: str = "allow",
) -> AddRuleResponse:
    request = AddRuleRequest(
        policy_id=policy_id,
        condition=condition,
        action=action,
        priority=0,
    )
    return add_uc.execute(request)


# ===================================================================
# CreatePolicyUseCase
# ===================================================================


class TestCreatePolicyUseCase:
    def test_create_policy(self, create_policy_uc: CreatePolicyUseCase,
                           fake_policy_repo: FakePolicyRepository,
                           fake_outbox: FakePolicyOutbox) -> None:
        request = CreatePolicyRequest(
            name="Test Policy",
            description="A test policy",
            priority="high",
            scope="user",
            version="1.0.0",
        )
        response = create_policy_uc.execute(request)
        assert response.name == "Test Policy"
        assert response.description == "A test policy"
        assert response.status == "draft"
        assert response.priority == "high"
        assert response.scope == "user"
        assert response.version == "1.0.0"
        assert response.created_at is not None
        assert fake_policy_repo.count() == 1

    def test_emits_policy_created_event(
        self, create_policy_uc: CreatePolicyUseCase,
        fake_outbox: FakePolicyOutbox,
    ) -> None:
        request = CreatePolicyRequest(
            name="Test", description="Desc",
        )
        create_policy_uc.execute(request)
        assert len(fake_outbox.append_calls) == 1
        event = fake_outbox.append_calls[0]
        assert isinstance(event, PolicyCreated)
        assert event.name == "Test"

    def test_default_priority_and_scope(
        self, create_policy_uc: CreatePolicyUseCase,
    ) -> None:
        request = CreatePolicyRequest(
            name="Default", description="Default test",
        )
        response = create_policy_uc.execute(request)
        assert response.priority == "medium"
        assert response.scope == "global"

    def test_default_version(
        self, create_policy_uc: CreatePolicyUseCase,
    ) -> None:
        request = CreatePolicyRequest(
            name="V", description="Version test",
        )
        response = create_policy_uc.execute(request)
        assert response.version == "1.0.0"


# ===================================================================
# ActivatePolicyUseCase
# ===================================================================


class TestActivatePolicyUseCase:
    def test_activate_policy(
        self, create_policy_uc: CreatePolicyUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        rule_resp = _add_rule_to_policy(
            AddRuleUseCase(
                policy_repo=fake_policy_repo,
                rule_repo=FakeRuleRepository(),
                outbox=FakePolicyOutbox(),
            ),
            pid,
        )
        req = PolicyLifecycleRequest(policy_id=pid)
        response = activate_policy_uc.execute(req)
        assert response.policy_id == pid
        assert response.status == "active"
        assert response.updated_at is not None

    def test_not_found(
        self, activate_policy_uc: ActivatePolicyUseCase,
    ) -> None:
        req = PolicyLifecycleRequest(policy_id="00000000-0000-0000-0000-000000000001")
        with pytest.raises(PolicyNotFoundError):
            activate_policy_uc.execute(req)

    def test_emits_activated_event(
        self, create_policy_uc: CreatePolicyUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        fake_policy_repo: FakePolicyRepository,
        fake_outbox: FakePolicyOutbox,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(
            AddRuleUseCase(
                policy_repo=fake_policy_repo,
                rule_repo=FakeRuleRepository(),
                outbox=FakePolicyOutbox(),
            ),
            pid,
        )
        req = PolicyLifecycleRequest(policy_id=pid)
        activate_policy_uc.execute(req)
        last_event = fake_outbox.append_calls[-1]
        assert isinstance(last_event, PolicyActivated)


# ===================================================================
# DisablePolicyUseCase
# ===================================================================


class TestDisablePolicyUseCase:
    def test_disable_policy(
        self, create_policy_uc: CreatePolicyUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        disable_policy_uc: DisablePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        response = disable_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        assert response.status == "disabled"
        assert response.updated_at is not None

    def test_not_found(
        self, disable_policy_uc: DisablePolicyUseCase,
    ) -> None:
        req = PolicyLifecycleRequest(policy_id="00000000-0000-0000-0000-000000000001")
        with pytest.raises(PolicyNotFoundError):
            disable_policy_uc.execute(req)

    def test_emits_disabled_event(
        self, create_policy_uc: CreatePolicyUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        disable_policy_uc: DisablePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        fake_outbox: FakePolicyOutbox,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        disable_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        last_event = fake_outbox.append_calls[-1]
        assert isinstance(last_event, PolicyDisabled)


# ===================================================================
# ArchivePolicyUseCase
# ===================================================================


class TestArchivePolicyUseCase:
    def test_archive_policy(
        self, create_policy_uc: CreatePolicyUseCase,
        archive_policy_uc: ArchivePolicyUseCase,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        req = PolicyLifecycleRequest(policy_id=pid)
        response = archive_policy_uc.execute(req)
        assert response.status == "archived"
        assert response.updated_at is not None

    def test_not_found(
        self, archive_policy_uc: ArchivePolicyUseCase,
    ) -> None:
        req = PolicyLifecycleRequest(policy_id="00000000-0000-0000-0000-000000000001")
        with pytest.raises(PolicyNotFoundError):
            archive_policy_uc.execute(req)

    def test_emits_archived_event(
        self, create_policy_uc: CreatePolicyUseCase,
        archive_policy_uc: ArchivePolicyUseCase,
        fake_outbox: FakePolicyOutbox,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        req = PolicyLifecycleRequest(policy_id=pid)
        archive_policy_uc.execute(req)
        last_event = fake_outbox.append_calls[-1]
        assert isinstance(last_event, PolicyArchived)


# ===================================================================
# AddRuleUseCase
# ===================================================================


class TestAddRuleUseCase:
    def test_add_rule(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        response = _add_rule_to_policy(add_rule_uc, pid)
        assert response.rule_id is not None
        assert response.condition == "true"
        assert response.action == "allow"
        assert response.priority == 0
        assert response.enabled is True

    def test_policy_not_found(
        self, add_rule_uc: AddRuleUseCase,
    ) -> None:
        request = AddRuleRequest(
            policy_id="00000000-0000-0000-0000-000000000001",
            condition="true", action="allow",
        )
        with pytest.raises(PolicyNotFoundError):
            add_rule_uc.execute(request)

    def test_emits_rule_added_event(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        fake_outbox: FakePolicyOutbox,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        last_event = fake_outbox.append_calls[-1]
        assert isinstance(last_event, PolicyRuleAdded)

    def test_rule_persisted_in_rule_repo(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        fake_rule_repo: FakeRuleRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        rule_resp = _add_rule_to_policy(add_rule_uc, pid)
        assert fake_rule_repo.count() == 1
        found = fake_rule_repo.find_by_id(
            PolicyRuleId(value=UUID(rule_resp.rule_id))
        )
        assert found is not None


# ===================================================================
# RemoveRuleUseCase
# ===================================================================


class TestRemoveRuleUseCase:
    def test_remove_rule(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        remove_rule_uc: RemoveRuleUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        rule_resp = _add_rule_to_policy(add_rule_uc, pid)
        req = RemoveRuleRequest(policy_id=pid, rule_id=rule_resp.rule_id)
        response = remove_rule_uc.execute(req)
        assert response.policy_id == pid
        assert response.rule_id == rule_resp.rule_id

    def test_policy_not_found(
        self, remove_rule_uc: RemoveRuleUseCase,
    ) -> None:
        req = RemoveRuleRequest(
            policy_id="00000000-0000-0000-0000-000000000001",
            rule_id="00000000-0000-0000-0000-000000000002",
        )
        with pytest.raises(PolicyNotFoundError):
            remove_rule_uc.execute(req)

    def test_emits_rule_removed_event(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        remove_rule_uc: RemoveRuleUseCase,
        fake_outbox: FakePolicyOutbox,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        rule_resp = _add_rule_to_policy(add_rule_uc, pid)
        req = RemoveRuleRequest(policy_id=pid, rule_id=rule_resp.rule_id)
        remove_rule_uc.execute(req)
        last_event = fake_outbox.append_calls[-1]
        assert isinstance(last_event, PolicyRuleRemoved)


# ===================================================================
# EnableRuleUseCase
# ===================================================================


class TestEnableRuleUseCase:
    def test_enable_rule(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        enable_rule_uc: EnableRuleUseCase,
        disable_rule_uc: DisableRuleUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        rule_resp = _add_rule_to_policy(add_rule_uc, pid)
        disable_rule_uc.execute(RuleLifecycleRequest(rule_id=rule_resp.rule_id))
        response = enable_rule_uc.execute(
            RuleLifecycleRequest(rule_id=rule_resp.rule_id)
        )
        assert response.enabled is True

    def test_not_found(
        self, enable_rule_uc: EnableRuleUseCase,
    ) -> None:
        req = RuleLifecycleRequest(rule_id="00000000-0000-0000-0000-000000000001")
        with pytest.raises(PolicyRuleNotFoundError):
            enable_rule_uc.execute(req)

    def test_emits_rule_enabled_event(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        enable_rule_uc: EnableRuleUseCase,
        disable_rule_uc: DisableRuleUseCase,
        fake_outbox: FakePolicyOutbox,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        rule_resp = _add_rule_to_policy(add_rule_uc, pid)
        disable_rule_uc.execute(RuleLifecycleRequest(rule_id=rule_resp.rule_id))
        enable_rule_uc.execute(RuleLifecycleRequest(rule_id=rule_resp.rule_id))
        last_event = fake_outbox.append_calls[-1]
        assert isinstance(last_event, PolicyRuleEnabled)


# ===================================================================
# DisableRuleUseCase
# ===================================================================


class TestDisableRuleUseCase:
    def test_disable_rule(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        disable_rule_uc: DisableRuleUseCase,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        rule_resp = _add_rule_to_policy(add_rule_uc, pid)
        response = disable_rule_uc.execute(
            RuleLifecycleRequest(rule_id=rule_resp.rule_id)
        )
        assert response.enabled is False

    def test_not_found(
        self, disable_rule_uc: DisableRuleUseCase,
    ) -> None:
        req = RuleLifecycleRequest(rule_id="00000000-0000-0000-0000-000000000001")
        with pytest.raises(PolicyRuleNotFoundError):
            disable_rule_uc.execute(req)

    def test_emits_rule_disabled_event(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        disable_rule_uc: DisableRuleUseCase,
        fake_outbox: FakePolicyOutbox,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        rule_resp = _add_rule_to_policy(add_rule_uc, pid)
        disable_rule_uc.execute(RuleLifecycleRequest(rule_id=rule_resp.rule_id))
        last_event = fake_outbox.append_calls[-1]
        assert isinstance(last_event, PolicyRuleDisabled)


# ===================================================================
# StartEvaluationUseCase
# ===================================================================


class TestStartEvaluationUseCase:
    def test_start_evaluation(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        start_evaluation_uc: StartEvaluationUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        response = start_evaluation_uc.execute(
            StartEvaluationRequest(policy_id=pid)
        )
        assert response.evaluation_id is not None
        assert response.status == "evaluating"
        assert response.started_at is not None

    def test_policy_not_found(
        self, start_evaluation_uc: StartEvaluationUseCase,
    ) -> None:
        req = StartEvaluationRequest(
            policy_id="00000000-0000-0000-0000-000000000001",
        )
        with pytest.raises(PolicyNotFoundError):
            start_evaluation_uc.execute(req)

    def test_emits_evaluation_started_event(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        start_evaluation_uc: StartEvaluationUseCase,
        fake_outbox: FakePolicyOutbox,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        start_evaluation_uc.execute(StartEvaluationRequest(policy_id=pid))
        last_event = fake_outbox.append_calls[-1]
        assert isinstance(last_event, PolicyEvaluationStarted)


# ===================================================================
# CompleteEvaluationUseCase
# ===================================================================


class TestCompleteEvaluationUseCase:
    def test_complete_evaluation(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        start_evaluation_uc: StartEvaluationUseCase,
        complete_evaluation_uc: CompleteEvaluationUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        eval_resp = start_evaluation_uc.execute(
            StartEvaluationRequest(policy_id=pid)
        )
        response = complete_evaluation_uc.execute(
            CompleteEvaluationRequest(
                policy_id=pid,
                evaluation_id=eval_resp.evaluation_id,
                decision="allow",
                result="ALLOW",
            )
        )
        assert response.status == "completed"
        assert response.decision == "allow"
        assert response.result == "ALLOW"
        assert response.completed_at is not None

    def test_policy_not_found(
        self, complete_evaluation_uc: CompleteEvaluationUseCase,
    ) -> None:
        req = CompleteEvaluationRequest(
            policy_id="00000000-0000-0000-0000-000000000001",
            evaluation_id="00000000-0000-0000-0000-000000000002",
            decision="allow", result="ok",
        )
        with pytest.raises(PolicyNotFoundError):
            complete_evaluation_uc.execute(req)

    def test_emits_evaluation_completed_event(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        start_evaluation_uc: StartEvaluationUseCase,
        complete_evaluation_uc: CompleteEvaluationUseCase,
        fake_outbox: FakePolicyOutbox,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        eval_resp = start_evaluation_uc.execute(
            StartEvaluationRequest(policy_id=pid)
        )
        complete_evaluation_uc.execute(
            CompleteEvaluationRequest(
                policy_id=pid, evaluation_id=eval_resp.evaluation_id,
                decision="deny", result="DENY",
            )
        )
        last_event = fake_outbox.append_calls[-1]
        assert isinstance(last_event, PolicyEvaluationCompleted)


# ===================================================================
# FailEvaluationUseCase
# ===================================================================


class TestFailEvaluationUseCase:
    def test_fail_evaluation(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        start_evaluation_uc: StartEvaluationUseCase,
        fail_evaluation_uc: FailEvaluationUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        eval_resp = start_evaluation_uc.execute(
            StartEvaluationRequest(policy_id=pid)
        )
        response = fail_evaluation_uc.execute(
            FailEvaluationRequest(
                policy_id=pid,
                evaluation_id=eval_resp.evaluation_id,
                failure_reason="Policy violation",
            )
        )
        assert response.status == "failed"
        assert response.failure_reason == "Policy violation"
        assert response.completed_at is not None

    def test_policy_not_found(
        self, fail_evaluation_uc: FailEvaluationUseCase,
    ) -> None:
        req = FailEvaluationRequest(
            policy_id="00000000-0000-0000-0000-000000000001",
            evaluation_id="00000000-0000-0000-0000-000000000002",
            failure_reason="err",
        )
        with pytest.raises(PolicyNotFoundError):
            fail_evaluation_uc.execute(req)

    def test_emits_evaluation_failed_event(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        start_evaluation_uc: StartEvaluationUseCase,
        fail_evaluation_uc: FailEvaluationUseCase,
        fake_outbox: FakePolicyOutbox,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        eval_resp = start_evaluation_uc.execute(
            StartEvaluationRequest(policy_id=pid)
        )
        fail_evaluation_uc.execute(
            FailEvaluationRequest(
                policy_id=pid, evaluation_id=eval_resp.evaluation_id,
                failure_reason="err",
            )
        )
        last_event = fake_outbox.append_calls[-1]
        assert isinstance(last_event, PolicyEvaluationFailed)


# ===================================================================
# GetPolicyUseCase
# ===================================================================


class TestGetPolicyUseCase:
    def test_get_policy(
        self, create_policy_uc: CreatePolicyUseCase,
        get_policy_uc: GetPolicyUseCase,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        response = get_policy_uc.execute(GetPolicyRequest(policy_id=pid))
        assert response.policy_id == pid
        assert response.name == "Test Policy"
        assert response.status == "draft"

    def test_not_found(
        self, get_policy_uc: GetPolicyUseCase,
    ) -> None:
        req = GetPolicyRequest(policy_id="00000000-0000-0000-0000-000000000001")
        with pytest.raises(PolicyNotFoundError):
            get_policy_uc.execute(req)

    def test_returns_rule_count(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        get_policy_uc: GetPolicyUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        rule_resp = _add_rule_to_policy(add_rule_uc, pid)
        response = get_policy_uc.execute(GetPolicyRequest(policy_id=pid))
        assert response.rule_count >= 1


# ===================================================================
# ListPoliciesUseCase
# ===================================================================


class TestListPoliciesUseCase:
    def test_list_all(
        self, create_policy_uc: CreatePolicyUseCase,
        list_policies_uc: ListPoliciesUseCase,
    ) -> None:
        _create_policy(create_policy_uc, name="P1")
        _create_policy(create_policy_uc, name="P2")
        response = list_policies_uc.execute(ListPoliciesRequest())
        assert response.total == 2
        assert len(response.policies) == 2

    def test_filter_by_status(
        self, create_policy_uc: CreatePolicyUseCase,
        list_policies_uc: ListPoliciesUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp1, pid1 = _create_policy(create_policy_uc, name="P1")
        resp2, pid2 = _create_policy(create_policy_uc, name="P2")
        _add_rule_to_policy(add_rule_uc, pid1)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid1))
        response = list_policies_uc.execute(
            ListPoliciesRequest(status="active")
        )
        assert response.total == 1
        assert response.policies[0].name == "P1"

    def test_filter_by_priority(
        self, create_policy_uc: CreatePolicyUseCase,
        list_policies_uc: ListPoliciesUseCase,
    ) -> None:
        _create_policy(create_policy_uc, name="High", priority="high")
        _create_policy(create_policy_uc, name="Low", priority="low")
        response = list_policies_uc.execute(
            ListPoliciesRequest(priority="high")
        )
        assert response.total == 1
        assert response.policies[0].name == "High"

    def test_filter_by_scope(
        self, create_policy_uc: CreatePolicyUseCase,
        list_policies_uc: ListPoliciesUseCase,
    ) -> None:
        _create_policy(create_policy_uc, name="Global", scope="global")
        _create_policy(create_policy_uc, name="User", scope="user")
        response = list_policies_uc.execute(
            ListPoliciesRequest(scope="user")
        )
        assert response.total == 1
        assert response.policies[0].name == "User"

    def test_empty(self, list_policies_uc: ListPoliciesUseCase) -> None:
        response = list_policies_uc.execute(ListPoliciesRequest())
        assert response.total == 0
        assert response.policies == []


# ===================================================================
# GetRuleUseCase
# ===================================================================


class TestGetRuleUseCase:
    def test_get_rule(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        get_rule_uc: GetRuleUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        rule_resp = _add_rule_to_policy(add_rule_uc, pid)
        response = get_rule_uc.execute(GetRuleRequest(rule_id=rule_resp.rule_id))
        assert response.rule_id == rule_resp.rule_id
        assert response.condition == "true"

    def test_not_found(
        self, get_rule_uc: GetRuleUseCase,
    ) -> None:
        req = GetRuleRequest(rule_id="00000000-0000-0000-0000-000000000001")
        with pytest.raises(PolicyRuleNotFoundError):
            get_rule_uc.execute(req)


# ===================================================================
# ListRulesUseCase
# ===================================================================


class TestListRulesUseCase:
    def test_list_all(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        list_rules_uc: ListRulesUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid, condition="c1")
        _add_rule_to_policy(add_rule_uc, pid, condition="c2")
        response = list_rules_uc.execute(ListRulesRequest())
        assert response.total == 2

    def test_filter_by_enabled(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        disable_rule_uc: DisableRuleUseCase,
        list_rules_uc: ListRulesUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        rule_resp = _add_rule_to_policy(add_rule_uc, pid)
        disable_rule_uc.execute(RuleLifecycleRequest(rule_id=rule_resp.rule_id))
        response = list_rules_uc.execute(ListRulesRequest(enabled=True))
        assert response.total == 0

    def test_filter_by_policy_id(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        list_rules_uc: ListRulesUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid1 = _create_policy(create_policy_uc, name="P1")
        resp, pid2 = _create_policy(create_policy_uc, name="P2")
        _add_rule_to_policy(add_rule_uc, pid1)
        _add_rule_to_policy(add_rule_uc, pid2)
        response = list_rules_uc.execute(
            ListRulesRequest(policy_id=pid1)
        )
        assert response.total >= 1

    def test_empty(self, list_rules_uc: ListRulesUseCase) -> None:
        response = list_rules_uc.execute(ListRulesRequest())
        assert response.total == 0


# ===================================================================
# GetEvaluationUseCase
# ===================================================================


class TestGetEvaluationUseCase:
    def test_get_evaluation(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        start_evaluation_uc: StartEvaluationUseCase,
        get_evaluation_uc: GetEvaluationUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        eval_resp = start_evaluation_uc.execute(
            StartEvaluationRequest(policy_id=pid)
        )
        response = get_evaluation_uc.execute(
            GetEvaluationRequest(evaluation_id=eval_resp.evaluation_id)
        )
        assert response.evaluation_id == eval_resp.evaluation_id
        assert response.status == "evaluating"

    def test_not_found(
        self, get_evaluation_uc: GetEvaluationUseCase,
    ) -> None:
        req = GetEvaluationRequest(
            evaluation_id="00000000-0000-0000-0000-000000000001",
        )
        with pytest.raises(PolicyEvaluationNotFoundError):
            get_evaluation_uc.execute(req)


# ===================================================================
# ListEvaluationsUseCase
# ===================================================================


class TestListEvaluationsUseCase:
    def test_list_all(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        start_evaluation_uc: StartEvaluationUseCase,
        list_evaluations_uc: ListEvaluationsUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        start_evaluation_uc.execute(StartEvaluationRequest(policy_id=pid))
        start_evaluation_uc.execute(StartEvaluationRequest(policy_id=pid))
        response = list_evaluations_uc.execute(ListEvaluationsRequest())
        assert response.total == 2

    def test_filter_by_status(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        start_evaluation_uc: StartEvaluationUseCase,
        complete_evaluation_uc: CompleteEvaluationUseCase,
        list_evaluations_uc: ListEvaluationsUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        eval_resp1 = start_evaluation_uc.execute(
            StartEvaluationRequest(policy_id=pid)
        )
        eval_resp2 = start_evaluation_uc.execute(
            StartEvaluationRequest(policy_id=pid)
        )
        complete_evaluation_uc.execute(
            CompleteEvaluationRequest(
                policy_id=pid, evaluation_id=eval_resp1.evaluation_id,
                decision="allow", result="ok",
            )
        )
        response = list_evaluations_uc.execute(
            ListEvaluationsRequest(status="completed")
        )
        assert response.total == 1

    def test_filter_by_policy_id(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        start_evaluation_uc: StartEvaluationUseCase,
        list_evaluations_uc: ListEvaluationsUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        start_evaluation_uc.execute(StartEvaluationRequest(policy_id=pid))
        response = list_evaluations_uc.execute(
            ListEvaluationsRequest(policy_id=pid)
        )
        assert response.total == 1

    def test_empty(
        self, list_evaluations_uc: ListEvaluationsUseCase,
    ) -> None:
        response = list_evaluations_uc.execute(ListEvaluationsRequest())
        assert response.total == 0


# ===================================================================
# Exception Tests
# ===================================================================


class TestExceptions:
    def test_use_case_error_is_base(self) -> None:
        err = UseCaseError()
        assert isinstance(err, Exception)

    def test_policy_not_found_error(self) -> None:
        err = PolicyNotFoundError("pid-1")
        assert str(err) == "Policy not found: pid-1"
        assert err.policy_id == "pid-1"

    def test_policy_rule_not_found_error(self) -> None:
        err = PolicyRuleNotFoundError("rid-1")
        assert str(err) == "Policy rule not found: rid-1"
        assert err.rule_id == "rid-1"

    def test_policy_evaluation_not_found_error(self) -> None:
        err = PolicyEvaluationNotFoundError("eid-1")
        assert str(err) == "Policy evaluation not found: eid-1"
        assert err.evaluation_id == "eid-1"


# ===================================================================
# Integration: Full lifecycle
# ===================================================================


class TestFullLifecycle:
    def test_create_activate_disable_archive(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        disable_policy_uc: DisablePolicyUseCase,
        archive_policy_uc: ArchivePolicyUseCase,
        get_policy_uc: GetPolicyUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        assert get_policy_uc.execute(
            GetPolicyRequest(policy_id=pid)
        ).status == "active"
        disable_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        assert get_policy_uc.execute(
            GetPolicyRequest(policy_id=pid)
        ).status == "disabled"
        archive_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        assert get_policy_uc.execute(
            GetPolicyRequest(policy_id=pid)
        ).status == "archived"

    def test_evaluation_start_complete_fail(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        start_evaluation_uc: StartEvaluationUseCase,
        complete_evaluation_uc: CompleteEvaluationUseCase,
        fail_evaluation_uc: FailEvaluationUseCase,
        get_evaluation_uc: GetEvaluationUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        e1 = start_evaluation_uc.execute(
            StartEvaluationRequest(policy_id=pid)
        )
        complete_evaluation_uc.execute(
            CompleteEvaluationRequest(
                policy_id=pid, evaluation_id=e1.evaluation_id,
                decision="allow", result="ALLOW",
            )
        )
        assert get_evaluation_uc.execute(
            GetEvaluationRequest(evaluation_id=e1.evaluation_id)
        ).status == "completed"
        e2 = start_evaluation_uc.execute(
            StartEvaluationRequest(policy_id=pid)
        )
        fail_evaluation_uc.execute(
            FailEvaluationRequest(
                policy_id=pid, evaluation_id=e2.evaluation_id,
                failure_reason="timeout",
            )
        )
        assert get_evaluation_uc.execute(
            GetEvaluationRequest(evaluation_id=e2.evaluation_id)
        ).status == "failed"

    def test_multiple_rules_added(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        list_rules_uc: ListRulesUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid, condition="c1", action="allow")
        _add_rule_to_policy(add_rule_uc, pid, condition="c2", action="deny")
        _add_rule_to_policy(add_rule_uc, pid, condition="c3", action="review")
        response = list_rules_uc.execute(ListRulesRequest())
        assert response.total == 3

    def test_activate_policy_then_add_rule_fails(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        disable_policy_uc: DisablePolicyUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        from backend.policy.domain.exceptions import PolicyNotModifiableError
        with pytest.raises(PolicyNotModifiableError):
            _add_rule_to_policy(add_rule_uc, pid, condition="extra")

    def test_add_rule_then_activate(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        get_policy_uc: GetPolicyUseCase,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        rule_resp = _add_rule_to_policy(add_rule_uc, pid)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        policy_resp = get_policy_uc.execute(GetPolicyRequest(policy_id=pid))
        assert policy_resp.rule_count >= 1
        assert policy_resp.status == "active"


# ===================================================================
# DTO Tests
# ===================================================================


class TestDTOs:
    def test_create_policy_request(self) -> None:
        req = CreatePolicyRequest(name="Test", description="Desc")
        assert req.name == "Test"
        assert req.description == "Desc"
        assert req.priority == "medium"
        assert req.scope == "global"
        assert req.version == "1.0.0"

    def test_policy_lifecycle_request(self) -> None:
        req = PolicyLifecycleRequest(policy_id="p1")
        assert req.policy_id == "p1"

    def test_add_rule_request(self) -> None:
        req = AddRuleRequest(
            policy_id="p1", condition="true", action="allow",
        )
        assert req.policy_id == "p1"
        assert req.condition == "true"
        assert req.action == "allow"
        assert req.priority == 0

    def test_remove_rule_request(self) -> None:
        req = RemoveRuleRequest(policy_id="p1", rule_id="r1")
        assert req.policy_id == "p1"
        assert req.rule_id == "r1"

    def test_rule_lifecycle_request(self) -> None:
        req = RuleLifecycleRequest(rule_id="r1")
        assert req.rule_id == "r1"

    def test_start_evaluation_request(self) -> None:
        req = StartEvaluationRequest(policy_id="p1")
        assert req.policy_id == "p1"

    def test_complete_evaluation_request(self) -> None:
        req = CompleteEvaluationRequest(
            policy_id="p1", evaluation_id="e1",
            decision="allow", result="ok",
        )
        assert req.policy_id == "p1"
        assert req.evaluation_id == "e1"
        assert req.decision == "allow"
        assert req.result == "ok"

    def test_fail_evaluation_request(self) -> None:
        req = FailEvaluationRequest(
            policy_id="p1", evaluation_id="e1",
            failure_reason="err",
        )
        assert req.policy_id == "p1"
        assert req.failure_reason == "err"

    def test_list_policies_request_defaults(self) -> None:
        req = ListPoliciesRequest()
        assert req.status is None
        assert req.priority is None
        assert req.scope is None

    def test_policy_response_defaults(self) -> None:
        resp = PolicyResponse(policy_id="p1")
        assert resp.policy_id == "p1"
        assert resp.status == "draft"
        assert resp.rule_count == 0

    def test_rule_response_defaults(self) -> None:
        resp = RuleResponse(rule_id="r1")
        assert resp.rule_id == "r1"
        assert resp.enabled is True
        assert resp.priority == 0

    def test_evaluation_response_defaults(self) -> None:
        resp = EvaluationResponse(evaluation_id="e1")
        assert resp.evaluation_id == "e1"
        assert resp.status == "pending"


# ===================================================================
# Outbox Event Verification
# ===================================================================


class TestOutboxEvents:
    def test_create_emits_policy_created(
        self, create_policy_uc: CreatePolicyUseCase,
        fake_outbox: FakePolicyOutbox,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        assert len(fake_outbox.append_calls) == 1
        assert isinstance(fake_outbox.append_calls[0], PolicyCreated)

    def test_activate_emits_policy_activated(
        self, create_policy_uc: CreatePolicyUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        fake_outbox: FakePolicyOutbox,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        before = len(fake_outbox.append_calls)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        assert isinstance(fake_outbox.append_calls[-1], PolicyActivated)

    def test_disable_emits_policy_disabled(
        self, create_policy_uc: CreatePolicyUseCase,
        activate_policy_uc: ActivatePolicyUseCase,
        disable_policy_uc: DisablePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        fake_outbox: FakePolicyOutbox,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        activate_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        disable_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        assert isinstance(fake_outbox.append_calls[-1], PolicyDisabled)

    def test_archive_emits_policy_archived(
        self, create_policy_uc: CreatePolicyUseCase,
        archive_policy_uc: ArchivePolicyUseCase,
        fake_outbox: FakePolicyOutbox,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        archive_policy_uc.execute(PolicyLifecycleRequest(policy_id=pid))
        assert isinstance(fake_outbox.append_calls[-1], PolicyArchived)

    def test_add_rule_emits_rule_added(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        fake_outbox: FakePolicyOutbox,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        _add_rule_to_policy(add_rule_uc, pid)
        assert isinstance(fake_outbox.append_calls[-1], PolicyRuleAdded)

    def test_remove_rule_emits_rule_removed(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        remove_rule_uc: RemoveRuleUseCase,
        fake_outbox: FakePolicyOutbox,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        rule_resp = _add_rule_to_policy(add_rule_uc, pid)
        before = len(fake_outbox.append_calls)
        remove_rule_uc.execute(
            RemoveRuleRequest(policy_id=pid, rule_id=rule_resp.rule_id)
        )
        assert isinstance(fake_outbox.append_calls[-1], PolicyRuleRemoved)

    def test_enable_rule_emits_rule_enabled(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        enable_rule_uc: EnableRuleUseCase,
        disable_rule_uc: DisableRuleUseCase,
        fake_outbox: FakePolicyOutbox,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        rule_resp = _add_rule_to_policy(add_rule_uc, pid)
        disable_rule_uc.execute(RuleLifecycleRequest(rule_id=rule_resp.rule_id))
        enable_rule_uc.execute(RuleLifecycleRequest(rule_id=rule_resp.rule_id))
        assert isinstance(fake_outbox.append_calls[-1], PolicyRuleEnabled)

    def test_disable_rule_emits_rule_disabled(
        self, create_policy_uc: CreatePolicyUseCase,
        add_rule_uc: AddRuleUseCase,
        disable_rule_uc: DisableRuleUseCase,
        fake_outbox: FakePolicyOutbox,
        fake_policy_repo: FakePolicyRepository,
    ) -> None:
        resp, pid = _create_policy(create_policy_uc)
        rule_resp = _add_rule_to_policy(add_rule_uc, pid)
        disable_rule_uc.execute(RuleLifecycleRequest(rule_id=rule_resp.rule_id))
        assert isinstance(fake_outbox.append_calls[-1], PolicyRuleDisabled)

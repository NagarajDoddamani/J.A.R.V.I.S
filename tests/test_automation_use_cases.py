from __future__ import annotations

from uuid import UUID

import pytest

from backend.automation.application.ports.outbox import AutomationOutboxPort
from backend.automation.application.ports.repository import (
    AutomationExecutionRepositoryPort,
    AutomationRepositoryPort,
    TriggerRepositoryPort,
)
from backend.automation.application.use_cases.activate_automation import (
    ActivateAutomationUseCase,
)
from backend.automation.application.use_cases.add_action import AddActionUseCase
from backend.automation.application.use_cases.add_trigger import (
    AddTriggerUseCase,
)
from backend.automation.application.use_cases.complete_execution import (
    CompleteExecutionUseCase,
)
from backend.automation.application.use_cases.create_automation import (
    CreateAutomationUseCase,
)
from backend.automation.application.use_cases.disable_automation import (
    DisableAutomationUseCase,
)
from backend.automation.application.use_cases.disable_trigger import (
    DisableTriggerUseCase,
)
from backend.automation.application.use_cases.dto import (
    AddActionRequest,
    AddActionResponse,
    AddTriggerRequest,
    AddTriggerResponse,
    AutomationLifecycleRequest,
    AutomationLifecycleResponse,
    AutomationResponse,
    CompleteExecutionRequest,
    CompleteExecutionResponse,
    CreateAutomationRequest,
    CreateAutomationResponse,
    ExecutionResponse,
    FailExecutionRequest,
    FailExecutionResponse,
    GetAutomationRequest,
    GetExecutionRequest,
    GetTriggerRequest,
    ListAutomationsRequest,
    ListAutomationsResponse,
    ListExecutionsRequest,
    ListExecutionsResponse,
    ListTriggersRequest,
    ListTriggersResponse,
    StartExecutionRequest,
    StartExecutionResponse,
    TriggerLifecycleRequest,
    TriggerLifecycleResponse,
    TriggerResponse,
)
from backend.automation.application.use_cases.enable_trigger import (
    EnableTriggerUseCase,
)
from backend.automation.application.use_cases.exceptions import (
    AutomationExecutionNotFoundError,
    AutomationNotFoundError,
    TriggerNotFoundError,
    UseCaseError,
)
from backend.automation.application.use_cases.fail_execution import (
    FailExecutionUseCase,
)
from backend.automation.application.use_cases.get_automation import (
    GetAutomationUseCase,
)
from backend.automation.application.use_cases.get_execution import (
    GetExecutionUseCase,
)
from backend.automation.application.use_cases.get_trigger import (
    GetTriggerUseCase,
)
from backend.automation.application.use_cases.list_automations import (
    ListAutomationsUseCase,
)
from backend.automation.application.use_cases.list_executions import (
    ListExecutionsUseCase,
)
from backend.automation.application.use_cases.list_triggers import (
    ListTriggersUseCase,
)
from backend.automation.application.use_cases.pause_automation import (
    PauseAutomationUseCase,
)
from backend.automation.application.use_cases.start_execution import (
    StartExecutionUseCase,
)
from backend.automation.domain.exceptions import (
    AutomationHasNoActionsError,
    AutomationHasNoTriggersError,
    AutomationTerminalError,
    InvalidActionTypeError,
    InvalidAutomationDescriptionError,
    InvalidAutomationNameError,
    InvalidExecutionResultError,
    InvalidFailureReasonError,
    InvalidScheduleExpressionError,
    InvalidTransitionError,
    TriggerAlreadyDisabledError,
    TriggerAlreadyEnabledError,
)
from backend.automation.domain.model import (
    ActionAdded,
    AutomationActivated,
    AutomationCreated,
    AutomationDisabled,
    AutomationExecution,
    AutomationExecutionCompleted,
    AutomationExecutionFailed,
    AutomationExecutionStarted,
    AutomationId,
    AutomationPaused,
    AutomationStatus,
    ExecutionStatus,
    TriggerAdded,
    TriggerDisabled,
    TriggerEnabled,
    TriggerId,
    WorkflowExecutionId,
)


class FakeAutomationRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, Automation] = {}
        self.save_calls: list[Automation] = []

    def save(self, automation: Automation) -> None:
        self._store[automation.automation_id.value] = automation
        self.save_calls.append(automation)

    def find_by_id(self, automation_id: AutomationId) -> Automation | None:
        return self._store.get(automation_id.value)

    def find_by_status(self, status: AutomationStatus) -> list[Automation]:
        return [a for a in self._store.values() if a.status == status]

    def find_by_execution_mode(
        self, mode: object
    ) -> list[Automation]:
        return [a for a in self._store.values() if a.execution_mode == mode]

    def find_all(self) -> list[Automation]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class FakeTriggerRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, object] = {}
        self.save_calls: list[object] = []

    def save(self, trigger: object, automation_id: str | None = None) -> None:
        self._store[trigger.trigger_id.value] = trigger
        self.save_calls.append(trigger)

    def find_by_id(self, trigger_id: TriggerId) -> object | None:
        return self._store.get(trigger_id.value)

    def find_by_type(self, trigger_type: object) -> list[object]:
        return [t for t in self._store.values() if t.trigger_type == trigger_type]

    def find_enabled(self) -> list[object]:
        return [t for t in self._store.values() if t.enabled]

    def find_all(self) -> list[object]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class FakeAutomationExecutionRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, AutomationExecution] = {}
        self.save_calls: list[AutomationExecution] = []

    def save(self, execution: AutomationExecution) -> None:
        self._store[execution.execution_id.value] = execution
        self.save_calls.append(execution)

    def find_by_id(
        self, execution_id: WorkflowExecutionId
    ) -> AutomationExecution | None:
        return self._store.get(execution_id.value)

    def find_by_status(
        self, status: ExecutionStatus
    ) -> list[AutomationExecution]:
        return [e for e in self._store.values() if e.status == status]

    def find_by_automation_id(
        self, automation_id: AutomationId
    ) -> list[AutomationExecution]:
        return [
            e
            for e in self._store.values()
            if e.automation_id == automation_id
        ]

    def find_all(self) -> list[AutomationExecution]:
        return list(self._store.values())

    def count(self) -> int:
        return len(self._store)


class FakeAutomationOutbox:
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
def fake_automation_repo() -> FakeAutomationRepository:
    return FakeAutomationRepository()


@pytest.fixture
def fake_trigger_repo() -> FakeTriggerRepository:
    return FakeTriggerRepository()


@pytest.fixture
def fake_execution_repo() -> FakeAutomationExecutionRepository:
    return FakeAutomationExecutionRepository()


@pytest.fixture
def fake_outbox() -> FakeAutomationOutbox:
    return FakeAutomationOutbox()


@pytest.fixture
def create_automation_uc(
    fake_automation_repo: FakeAutomationRepository,
    fake_outbox: FakeAutomationOutbox,
) -> CreateAutomationUseCase:
    return CreateAutomationUseCase(
        automation_repo=fake_automation_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def activate_automation_uc(
    fake_automation_repo: FakeAutomationRepository,
    fake_outbox: FakeAutomationOutbox,
) -> ActivateAutomationUseCase:
    return ActivateAutomationUseCase(
        automation_repo=fake_automation_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def pause_automation_uc(
    fake_automation_repo: FakeAutomationRepository,
    fake_outbox: FakeAutomationOutbox,
) -> PauseAutomationUseCase:
    return PauseAutomationUseCase(
        automation_repo=fake_automation_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def disable_automation_uc(
    fake_automation_repo: FakeAutomationRepository,
    fake_outbox: FakeAutomationOutbox,
) -> DisableAutomationUseCase:
    return DisableAutomationUseCase(
        automation_repo=fake_automation_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def add_trigger_uc(
    fake_automation_repo: FakeAutomationRepository,
    fake_trigger_repo: FakeTriggerRepository,
    fake_outbox: FakeAutomationOutbox,
) -> AddTriggerUseCase:
    return AddTriggerUseCase(
        automation_repo=fake_automation_repo,
        trigger_repo=fake_trigger_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def enable_trigger_uc(
    fake_trigger_repo: FakeTriggerRepository,
    fake_automation_repo: FakeAutomationRepository,
    fake_outbox: FakeAutomationOutbox,
) -> EnableTriggerUseCase:
    return EnableTriggerUseCase(
        trigger_repo=fake_trigger_repo,
        automation_repo=fake_automation_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def disable_trigger_uc(
    fake_trigger_repo: FakeTriggerRepository,
    fake_automation_repo: FakeAutomationRepository,
    fake_outbox: FakeAutomationOutbox,
) -> DisableTriggerUseCase:
    return DisableTriggerUseCase(
        trigger_repo=fake_trigger_repo,
        automation_repo=fake_automation_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def add_action_uc(
    fake_automation_repo: FakeAutomationRepository,
    fake_outbox: FakeAutomationOutbox,
) -> AddActionUseCase:
    return AddActionUseCase(
        automation_repo=fake_automation_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def start_execution_uc(
    fake_automation_repo: FakeAutomationRepository,
    fake_execution_repo: FakeAutomationExecutionRepository,
    fake_outbox: FakeAutomationOutbox,
) -> StartExecutionUseCase:
    return StartExecutionUseCase(
        automation_repo=fake_automation_repo,
        execution_repo=fake_execution_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def complete_execution_uc(
    fake_automation_repo: FakeAutomationRepository,
    fake_execution_repo: FakeAutomationExecutionRepository,
    fake_outbox: FakeAutomationOutbox,
) -> CompleteExecutionUseCase:
    return CompleteExecutionUseCase(
        automation_repo=fake_automation_repo,
        execution_repo=fake_execution_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def fail_execution_uc(
    fake_automation_repo: FakeAutomationRepository,
    fake_execution_repo: FakeAutomationExecutionRepository,
    fake_outbox: FakeAutomationOutbox,
) -> FailExecutionUseCase:
    return FailExecutionUseCase(
        automation_repo=fake_automation_repo,
        execution_repo=fake_execution_repo,
        outbox=fake_outbox,
    )


@pytest.fixture
def get_automation_uc(
    fake_automation_repo: FakeAutomationRepository,
) -> GetAutomationUseCase:
    return GetAutomationUseCase(automation_repo=fake_automation_repo)


@pytest.fixture
def list_automations_uc(
    fake_automation_repo: FakeAutomationRepository,
) -> ListAutomationsUseCase:
    return ListAutomationsUseCase(automation_repo=fake_automation_repo)


@pytest.fixture
def get_trigger_uc(
    fake_trigger_repo: FakeTriggerRepository,
) -> GetTriggerUseCase:
    return GetTriggerUseCase(trigger_repo=fake_trigger_repo)


@pytest.fixture
def list_triggers_uc(
    fake_trigger_repo: FakeTriggerRepository,
) -> ListTriggersUseCase:
    return ListTriggersUseCase(trigger_repo=fake_trigger_repo)


@pytest.fixture
def get_execution_uc(
    fake_execution_repo: FakeAutomationExecutionRepository,
) -> GetExecutionUseCase:
    return GetExecutionUseCase(execution_repo=fake_execution_repo)


@pytest.fixture
def list_executions_uc(
    fake_execution_repo: FakeAutomationExecutionRepository,
) -> ListExecutionsUseCase:
    return ListExecutionsUseCase(execution_repo=fake_execution_repo)


def _create_automation(
    create_automation_uc: CreateAutomationUseCase,
    *,
    name: str = "Test Automation",
    description: str = "Test Description",
    execution_mode: str = "once",
) -> CreateAutomationResponse:
    return create_automation_uc.execute(
        CreateAutomationRequest(
            name=name,
            description=description,
            execution_mode=execution_mode,
        )
    )


def _create_automation_with_trigger_and_action(
    create_automation_uc: CreateAutomationUseCase,
    add_trigger_uc: AddTriggerUseCase,
    add_action_uc: AddActionUseCase,
    *,
    name: str = "Test Automation",
) -> tuple[str, str]:
    resp = _create_automation(create_automation_uc, name=name)
    trigger_resp = add_trigger_uc.execute(
        AddTriggerRequest(
            automation_id=resp.automation_id,
            trigger_type="manual",
        )
    )
    add_action_uc.execute(
        AddActionRequest(
            automation_id=resp.automation_id,
            action_type="notification",
        )
    )
    return resp.automation_id, trigger_resp.trigger_id


def _create_automation_with_trigger(
    create_automation_uc: CreateAutomationUseCase,
    add_trigger_uc: AddTriggerUseCase,
    *,
    name: str = "Test Automation",
) -> tuple[str, str]:
    resp = _create_automation(create_automation_uc, name=name)
    trigger_resp = add_trigger_uc.execute(
        AddTriggerRequest(
            automation_id=resp.automation_id,
            trigger_type="manual",
        )
    )
    return resp.automation_id, trigger_resp.trigger_id


def _full_lifecycle_to_running(
    create_automation_uc: CreateAutomationUseCase,
    add_trigger_uc: AddTriggerUseCase,
    add_action_uc: AddActionUseCase,
    activate_automation_uc: ActivateAutomationUseCase,
    start_execution_uc: StartExecutionUseCase,
) -> tuple[str, str]:
    aid, _ = _create_automation_with_trigger_and_action(
        create_automation_uc, add_trigger_uc, add_action_uc,
    )
    activate_automation_uc.execute(AutomationLifecycleRequest(automation_id=aid))
    exec_resp = start_execution_uc.execute(
        StartExecutionRequest(automation_id=aid)
    )
    return aid, exec_resp.execution_id


class TestCreateAutomationUseCase:
    def test_happy_path(
        self,
        create_automation_uc: CreateAutomationUseCase,
        fake_automation_repo: FakeAutomationRepository,
        fake_outbox: FakeAutomationOutbox,
    ) -> None:
        response = _create_automation(create_automation_uc)
        assert response.name == "Test Automation"
        assert response.description == "Test Description"
        assert response.execution_mode == "once"
        assert response.status == "draft"
        assert response.created_at is not None
        assert isinstance(response, CreateAutomationResponse)

    def test_automation_persisted(
        self,
        create_automation_uc: CreateAutomationUseCase,
        fake_automation_repo: FakeAutomationRepository,
    ) -> None:
        response = _create_automation(create_automation_uc)
        assert fake_automation_repo.count() == 1
        stored = fake_automation_repo.find_by_id(
            AutomationId(value=UUID(response.automation_id))
        )
        assert stored is not None
        assert stored.status == AutomationStatus.DRAFT

    def test_event_emitted(
        self,
        create_automation_uc: CreateAutomationUseCase,
        fake_outbox: FakeAutomationOutbox,
    ) -> None:
        response = _create_automation(create_automation_uc)
        assert len(fake_outbox.append_calls) == 1
        event = fake_outbox.append_calls[0]
        assert isinstance(event, AutomationCreated)
        assert str(event.automation_id) == response.automation_id

    def test_event_fields(
        self,
        create_automation_uc: CreateAutomationUseCase,
        fake_outbox: FakeAutomationOutbox,
    ) -> None:
        response = _create_automation(
            create_automation_uc, name="My Automation"
        )
        event = fake_outbox.append_calls[0]
        assert isinstance(event, AutomationCreated)
        assert event.name == "My Automation"
        assert event.description == "Test Description"
        assert event.execution_mode == "once"

    def test_save_called(
        self,
        create_automation_uc: CreateAutomationUseCase,
        fake_automation_repo: FakeAutomationRepository,
    ) -> None:
        _create_automation(create_automation_uc)
        assert len(fake_automation_repo.save_calls) == 1

    def test_recurring_execution_mode(
        self,
        create_automation_uc: CreateAutomationUseCase,
    ) -> None:
        response = _create_automation(
            create_automation_uc, execution_mode="recurring"
        )
        assert response.execution_mode == "recurring"

    def test_continuous_execution_mode(
        self,
        create_automation_uc: CreateAutomationUseCase,
    ) -> None:
        response = _create_automation(
            create_automation_uc, execution_mode="continuous"
        )
        assert response.execution_mode == "continuous"

    def test_empty_name_rejected(
        self,
        create_automation_uc: CreateAutomationUseCase,
    ) -> None:
        with pytest.raises(InvalidAutomationNameError):
            _create_automation(create_automation_uc, name="")

    def test_empty_description_rejected(
        self,
        create_automation_uc: CreateAutomationUseCase,
    ) -> None:
        with pytest.raises(InvalidAutomationDescriptionError):
            _create_automation(create_automation_uc, description="")

    def test_invalid_execution_mode_rejected(
        self,
        create_automation_uc: CreateAutomationUseCase,
    ) -> None:
        with pytest.raises(ValueError):
            _create_automation(
                create_automation_uc, execution_mode="invalid"
            )

    def test_multiple_automations(
        self,
        create_automation_uc: CreateAutomationUseCase,
        fake_automation_repo: FakeAutomationRepository,
    ) -> None:
        _create_automation(create_automation_uc, name="First")
        _create_automation(create_automation_uc, name="Second")
        assert fake_automation_repo.count() == 2

    def test_response_type(
        self,
        create_automation_uc: CreateAutomationUseCase,
    ) -> None:
        response = _create_automation(create_automation_uc)
        assert isinstance(response, CreateAutomationResponse)


class TestActivateAutomationUseCase:
    def test_draft_to_active(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
    ) -> None:
        aid, _ = _create_automation_with_trigger_and_action(
            create_automation_uc, add_trigger_uc, add_action_uc,
        )
        response = activate_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=aid)
        )
        assert response.status == "active"
        assert isinstance(response, AutomationLifecycleResponse)

    def test_missing_automation_raises_error(
        self,
        activate_automation_uc: ActivateAutomationUseCase,
    ) -> None:
        with pytest.raises(AutomationNotFoundError):
            activate_automation_uc.execute(
                AutomationLifecycleRequest(
                    automation_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_event_emitted(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        fake_outbox: FakeAutomationOutbox,
    ) -> None:
        aid, _ = _create_automation_with_trigger_and_action(
            create_automation_uc, add_trigger_uc, add_action_uc,
        )
        activate_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=aid)
        )
        events = [
            e
            for e in fake_outbox.append_calls
            if isinstance(e, AutomationActivated)
        ]
        assert len(events) == 1

    def test_save_called(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        fake_automation_repo: FakeAutomationRepository,
    ) -> None:
        aid, _ = _create_automation_with_trigger_and_action(
            create_automation_uc, add_trigger_uc, add_action_uc,
        )
        before = len(fake_automation_repo.save_calls)
        activate_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=aid)
        )
        assert len(fake_automation_repo.save_calls) == before + 1

    def test_stored_status_updated(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        fake_automation_repo: FakeAutomationRepository,
    ) -> None:
        aid, _ = _create_automation_with_trigger_and_action(
            create_automation_uc, add_trigger_uc, add_action_uc,
        )
        activate_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=aid)
        )
        stored = fake_automation_repo.find_by_id(
            AutomationId(value=UUID(aid))
        )
        assert stored is not None
        assert stored.status == AutomationStatus.ACTIVE

    def test_requires_triggers(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
    ) -> None:
        resp = _create_automation(create_automation_uc)
        add_action_uc.execute(
            AddActionRequest(
                automation_id=resp.automation_id, action_type="notification"
            )
        )
        with pytest.raises(AutomationHasNoTriggersError):
            activate_automation_uc.execute(
                AutomationLifecycleRequest(automation_id=resp.automation_id)
            )

    def test_requires_actions(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
    ) -> None:
        resp = _create_automation(create_automation_uc, name="No Action")
        add_trigger_uc.execute(
            AddTriggerRequest(
                automation_id=resp.automation_id, trigger_type="manual"
            )
        )
        with pytest.raises(AutomationHasNoActionsError):
            activate_automation_uc.execute(
                AutomationLifecycleRequest(automation_id=resp.automation_id)
            )


class TestPauseAutomationUseCase:
    def test_active_to_paused(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        pause_automation_uc: PauseAutomationUseCase,
    ) -> None:
        aid, _ = _create_automation_with_trigger_and_action(
            create_automation_uc, add_trigger_uc, add_action_uc,
        )
        activate_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=aid)
        )
        response = pause_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=aid)
        )
        assert response.status == "paused"

    def test_missing_automation_raises_error(
        self,
        pause_automation_uc: PauseAutomationUseCase,
    ) -> None:
        with pytest.raises(AutomationNotFoundError):
            pause_automation_uc.execute(
                AutomationLifecycleRequest(
                    automation_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_event_emitted(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        pause_automation_uc: PauseAutomationUseCase,
        fake_outbox: FakeAutomationOutbox,
    ) -> None:
        aid, _ = _create_automation_with_trigger_and_action(
            create_automation_uc, add_trigger_uc, add_action_uc,
        )
        activate_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=aid)
        )
        pause_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=aid)
        )
        events = [
            e
            for e in fake_outbox.append_calls
            if isinstance(e, AutomationPaused)
        ]
        assert len(events) == 1

    def test_draft_to_paused_rejected(
        self,
        create_automation_uc: CreateAutomationUseCase,
        pause_automation_uc: PauseAutomationUseCase,
    ) -> None:
        resp = _create_automation(create_automation_uc)
        with pytest.raises(InvalidTransitionError):
            pause_automation_uc.execute(
                AutomationLifecycleRequest(automation_id=resp.automation_id)
            )


class TestDisableAutomationUseCase:
    def test_draft_to_disabled(
        self,
        create_automation_uc: CreateAutomationUseCase,
        disable_automation_uc: DisableAutomationUseCase,
    ) -> None:
        resp = _create_automation(create_automation_uc)
        response = disable_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=resp.automation_id)
        )
        assert response.status == "disabled"

    def test_missing_automation_raises_error(
        self,
        disable_automation_uc: DisableAutomationUseCase,
    ) -> None:
        with pytest.raises(AutomationNotFoundError):
            disable_automation_uc.execute(
                AutomationLifecycleRequest(
                    automation_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_event_emitted(
        self,
        create_automation_uc: CreateAutomationUseCase,
        disable_automation_uc: DisableAutomationUseCase,
        fake_outbox: FakeAutomationOutbox,
    ) -> None:
        resp = _create_automation(create_automation_uc)
        disable_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=resp.automation_id)
        )
        events = [
            e
            for e in fake_outbox.append_calls
            if isinstance(e, AutomationDisabled)
        ]
        assert len(events) == 1

    def test_double_disable_rejected(
        self,
        create_automation_uc: CreateAutomationUseCase,
        disable_automation_uc: DisableAutomationUseCase,
    ) -> None:
        resp = _create_automation(create_automation_uc)
        disable_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=resp.automation_id)
        )
        with pytest.raises(InvalidTransitionError):
            disable_automation_uc.execute(
                AutomationLifecycleRequest(automation_id=resp.automation_id)
            )


class TestAddTriggerUseCase:
    def test_happy_path(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        fake_automation_repo: FakeAutomationRepository,
    ) -> None:
        resp = _create_automation(create_automation_uc)
        response = add_trigger_uc.execute(
            AddTriggerRequest(
                automation_id=resp.automation_id,
                trigger_type="manual",
            )
        )
        assert isinstance(response, AddTriggerResponse)
        assert response.trigger_type == "manual"
        assert response.enabled is True
        stored = fake_automation_repo.find_by_id(
            AutomationId(value=UUID(resp.automation_id))
        )
        assert stored is not None
        assert len(stored.triggers) == 1

    def test_missing_automation_raises_error(
        self,
        add_trigger_uc: AddTriggerUseCase,
    ) -> None:
        with pytest.raises(AutomationNotFoundError):
            add_trigger_uc.execute(
                AddTriggerRequest(
                    automation_id="00000000-0000-0000-0000-000000000000",
                    trigger_type="manual",
                )
            )

    def test_event_emitted(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        fake_outbox: FakeAutomationOutbox,
    ) -> None:
        resp = _create_automation(create_automation_uc)
        add_trigger_uc.execute(
            AddTriggerRequest(
                automation_id=resp.automation_id,
                trigger_type="scheduled",
                expression="0 9 * * 1",
            )
        )
        events = [
            e
            for e in fake_outbox.append_calls
            if isinstance(e, TriggerAdded)
        ]
        assert len(events) == 1
        assert events[0].expression == "0 9 * * 1"

    def test_scheduled_trigger_without_expression_rejected(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
    ) -> None:
        resp = _create_automation(create_automation_uc)
        with pytest.raises(InvalidScheduleExpressionError):
            add_trigger_uc.execute(
                AddTriggerRequest(
                    automation_id=resp.automation_id,
                    trigger_type="scheduled",
                )
            )

    def test_trigger_persisted_separately(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        fake_trigger_repo: FakeTriggerRepository,
    ) -> None:
        resp = _create_automation(create_automation_uc)
        trigger_resp = add_trigger_uc.execute(
            AddTriggerRequest(
                automation_id=resp.automation_id,
                trigger_type="manual",
            )
        )
        assert fake_trigger_repo.count() == 1
        stored = fake_trigger_repo.find_by_id(
            TriggerId(value=UUID(trigger_resp.trigger_id))
        )
        assert stored is not None

    def test_terminal_automation_rejects_trigger(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        disable_automation_uc: DisableAutomationUseCase,
    ) -> None:
        resp = _create_automation(create_automation_uc)
        disable_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=resp.automation_id)
        )
        with pytest.raises(AutomationTerminalError):
            add_trigger_uc.execute(
                AddTriggerRequest(
                    automation_id=resp.automation_id,
                    trigger_type="manual",
                )
            )


class TestEnableTriggerUseCase:
    def test_enable_disabled_trigger(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        disable_trigger_uc: DisableTriggerUseCase,
        enable_trigger_uc: EnableTriggerUseCase,
    ) -> None:
        aid, tid = _create_automation_with_trigger(
            create_automation_uc, add_trigger_uc,
        )
        disable_trigger_uc.execute(TriggerLifecycleRequest(trigger_id=tid))
        response = enable_trigger_uc.execute(
            TriggerLifecycleRequest(trigger_id=tid)
        )
        assert response.enabled is True

    def test_missing_trigger_raises_error(
        self,
        enable_trigger_uc: EnableTriggerUseCase,
    ) -> None:
        with pytest.raises(TriggerNotFoundError):
            enable_trigger_uc.execute(
                TriggerLifecycleRequest(
                    trigger_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_event_emitted(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        disable_trigger_uc: DisableTriggerUseCase,
        enable_trigger_uc: EnableTriggerUseCase,
        fake_outbox: FakeAutomationOutbox,
    ) -> None:
        aid, tid = _create_automation_with_trigger(
            create_automation_uc, add_trigger_uc,
        )
        disable_trigger_uc.execute(TriggerLifecycleRequest(trigger_id=tid))
        enable_trigger_uc.execute(TriggerLifecycleRequest(trigger_id=tid))
        events = [
            e
            for e in fake_outbox.append_calls
            if isinstance(e, TriggerEnabled)
        ]
        assert len(events) == 1

    def test_double_enable_rejected(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        enable_trigger_uc: EnableTriggerUseCase,
    ) -> None:
        aid, tid = _create_automation_with_trigger(
            create_automation_uc, add_trigger_uc,
        )
        with pytest.raises(TriggerAlreadyEnabledError):
            enable_trigger_uc.execute(
                TriggerLifecycleRequest(trigger_id=tid)
            )


class TestDisableTriggerUseCase:
    def test_disable_enabled_trigger(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        disable_trigger_uc: DisableTriggerUseCase,
    ) -> None:
        aid, tid = _create_automation_with_trigger(
            create_automation_uc, add_trigger_uc,
        )
        response = disable_trigger_uc.execute(
            TriggerLifecycleRequest(trigger_id=tid)
        )
        assert response.enabled is False

    def test_missing_trigger_raises_error(
        self,
        disable_trigger_uc: DisableTriggerUseCase,
    ) -> None:
        with pytest.raises(TriggerNotFoundError):
            disable_trigger_uc.execute(
                TriggerLifecycleRequest(
                    trigger_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_event_emitted(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        disable_trigger_uc: DisableTriggerUseCase,
        fake_outbox: FakeAutomationOutbox,
    ) -> None:
        aid, tid = _create_automation_with_trigger(
            create_automation_uc, add_trigger_uc,
        )
        disable_trigger_uc.execute(TriggerLifecycleRequest(trigger_id=tid))
        events = [
            e
            for e in fake_outbox.append_calls
            if isinstance(e, TriggerDisabled)
        ]
        assert len(events) == 1

    def test_double_disable_rejected(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        disable_trigger_uc: DisableTriggerUseCase,
    ) -> None:
        aid, tid = _create_automation_with_trigger(
            create_automation_uc, add_trigger_uc,
        )
        disable_trigger_uc.execute(TriggerLifecycleRequest(trigger_id=tid))
        with pytest.raises(TriggerAlreadyDisabledError):
            disable_trigger_uc.execute(
                TriggerLifecycleRequest(trigger_id=tid)
            )


class TestAddActionUseCase:
    def test_happy_path(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_action_uc: AddActionUseCase,
    ) -> None:
        resp = _create_automation(create_automation_uc)
        response = add_action_uc.execute(
            AddActionRequest(
                automation_id=resp.automation_id,
                action_type="notification",
            )
        )
        assert isinstance(response, AddActionResponse)
        assert response.action_type == "notification"

    def test_missing_automation_raises_error(
        self,
        add_action_uc: AddActionUseCase,
    ) -> None:
        with pytest.raises(AutomationNotFoundError):
            add_action_uc.execute(
                AddActionRequest(
                    automation_id="00000000-0000-0000-0000-000000000000",
                    action_type="notification",
                )
            )

    def test_event_emitted(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_action_uc: AddActionUseCase,
        fake_outbox: FakeAutomationOutbox,
    ) -> None:
        resp = _create_automation(create_automation_uc)
        add_action_uc.execute(
            AddActionRequest(
                automation_id=resp.automation_id,
                action_type="memory",
            )
        )
        events = [
            e
            for e in fake_outbox.append_calls
            if isinstance(e, ActionAdded)
        ]
        assert len(events) == 1
        assert events[0].action_type == "memory"

    def test_duplicate_action_type_rejected(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_action_uc: AddActionUseCase,
    ) -> None:
        resp = _create_automation(create_automation_uc)
        add_action_uc.execute(
            AddActionRequest(
                automation_id=resp.automation_id,
                action_type="notification",
            )
        )
        with pytest.raises(Exception):
            add_action_uc.execute(
                AddActionRequest(
                    automation_id=resp.automation_id,
                    action_type="notification",
                )
            )

    def test_invalid_action_type_rejected(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_action_uc: AddActionUseCase,
    ) -> None:
        resp = _create_automation(create_automation_uc)
        with pytest.raises(InvalidActionTypeError):
            add_action_uc.execute(
                AddActionRequest(
                    automation_id=resp.automation_id,
                    action_type="invalid_action",
                )
            )

    def test_terminal_automation_rejects_action(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_action_uc: AddActionUseCase,
        disable_automation_uc: DisableAutomationUseCase,
    ) -> None:
        resp = _create_automation(create_automation_uc)
        disable_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=resp.automation_id)
        )
        with pytest.raises(AutomationTerminalError):
            add_action_uc.execute(
                AddActionRequest(
                    automation_id=resp.automation_id,
                    action_type="notification",
                )
            )


class TestStartExecutionUseCase:
    def test_happy_path(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        start_execution_uc: StartExecutionUseCase,
    ) -> None:
        aid, _ = _create_automation_with_trigger_and_action(
            create_automation_uc, add_trigger_uc, add_action_uc,
        )
        activate_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=aid)
        )
        response = start_execution_uc.execute(
            StartExecutionRequest(automation_id=aid)
        )
        assert isinstance(response, StartExecutionResponse)
        assert response.status == "running"
        assert response.started_at is not None

    def test_missing_automation_raises_error(
        self,
        start_execution_uc: StartExecutionUseCase,
    ) -> None:
        with pytest.raises(AutomationNotFoundError):
            start_execution_uc.execute(
                StartExecutionRequest(
                    automation_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_event_emitted(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        start_execution_uc: StartExecutionUseCase,
        fake_outbox: FakeAutomationOutbox,
    ) -> None:
        aid, _ = _create_automation_with_trigger_and_action(
            create_automation_uc, add_trigger_uc, add_action_uc,
        )
        activate_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=aid)
        )
        start_execution_uc.execute(StartExecutionRequest(automation_id=aid))
        events = [
            e
            for e in fake_outbox.append_calls
            if isinstance(e, AutomationExecutionStarted)
        ]
        assert len(events) == 1

    def test_execution_persisted(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        start_execution_uc: StartExecutionUseCase,
        fake_execution_repo: FakeAutomationExecutionRepository,
    ) -> None:
        aid, _ = _create_automation_with_trigger_and_action(
            create_automation_uc, add_trigger_uc, add_action_uc,
        )
        activate_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=aid)
        )
        response = start_execution_uc.execute(
            StartExecutionRequest(automation_id=aid)
        )
        assert fake_execution_repo.count() == 1
        stored = fake_execution_repo.find_by_id(
            WorkflowExecutionId(value=UUID(response.execution_id))
        )
        assert stored is not None
        assert stored.status == ExecutionStatus.RUNNING

    def test_paused_automation_rejected(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        pause_automation_uc: PauseAutomationUseCase,
        start_execution_uc: StartExecutionUseCase,
    ) -> None:
        aid, _ = _create_automation_with_trigger_and_action(
            create_automation_uc, add_trigger_uc, add_action_uc,
        )
        activate_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=aid)
        )
        pause_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=aid)
        )
        with pytest.raises(Exception):
            start_execution_uc.execute(
                StartExecutionRequest(automation_id=aid)
            )


class TestCompleteExecutionUseCase:
    def test_happy_path(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        start_execution_uc: StartExecutionUseCase,
        complete_execution_uc: CompleteExecutionUseCase,
    ) -> None:
        aid, eid = _full_lifecycle_to_running(
            create_automation_uc, add_trigger_uc, add_action_uc,
            activate_automation_uc, start_execution_uc,
        )
        response = complete_execution_uc.execute(
            CompleteExecutionRequest(
                automation_id=aid,
                execution_id=eid,
                result="Success",
            )
        )
        assert isinstance(response, CompleteExecutionResponse)
        assert response.status == "completed"
        assert response.result == "Success"

    def test_missing_automation_raises_error(
        self,
        complete_execution_uc: CompleteExecutionUseCase,
    ) -> None:
        with pytest.raises(AutomationNotFoundError):
            complete_execution_uc.execute(
                CompleteExecutionRequest(
                    automation_id="00000000-0000-0000-0000-000000000000",
                    execution_id="00000000-0000-0000-0000-000000000000",
                    result="Success",
                )
            )

    def test_event_emitted(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        start_execution_uc: StartExecutionUseCase,
        complete_execution_uc: CompleteExecutionUseCase,
        fake_outbox: FakeAutomationOutbox,
    ) -> None:
        aid, eid = _full_lifecycle_to_running(
            create_automation_uc, add_trigger_uc, add_action_uc,
            activate_automation_uc, start_execution_uc,
        )
        complete_execution_uc.execute(
            CompleteExecutionRequest(
                automation_id=aid, execution_id=eid, result="Done"
            )
        )
        events = [
            e
            for e in fake_outbox.append_calls
            if isinstance(e, AutomationExecutionCompleted)
        ]
        assert len(events) == 1
        assert events[0].result == "Done"

    def test_empty_result_rejected(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        start_execution_uc: StartExecutionUseCase,
        complete_execution_uc: CompleteExecutionUseCase,
    ) -> None:
        aid, eid = _full_lifecycle_to_running(
            create_automation_uc, add_trigger_uc, add_action_uc,
            activate_automation_uc, start_execution_uc,
        )
        with pytest.raises(InvalidExecutionResultError):
            complete_execution_uc.execute(
                CompleteExecutionRequest(
                    automation_id=aid, execution_id=eid, result=""
                )
            )


class TestFailExecutionUseCase:
    def test_happy_path(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        start_execution_uc: StartExecutionUseCase,
        fail_execution_uc: FailExecutionUseCase,
    ) -> None:
        aid, eid = _full_lifecycle_to_running(
            create_automation_uc, add_trigger_uc, add_action_uc,
            activate_automation_uc, start_execution_uc,
        )
        response = fail_execution_uc.execute(
            FailExecutionRequest(
                automation_id=aid,
                execution_id=eid,
                failure_reason="Something went wrong",
            )
        )
        assert isinstance(response, FailExecutionResponse)
        assert response.status == "failed"
        assert response.failure_reason == "Something went wrong"

    def test_missing_automation_raises_error(
        self,
        fail_execution_uc: FailExecutionUseCase,
    ) -> None:
        with pytest.raises(AutomationNotFoundError):
            fail_execution_uc.execute(
                FailExecutionRequest(
                    automation_id="00000000-0000-0000-0000-000000000000",
                    execution_id="00000000-0000-0000-0000-000000000000",
                    failure_reason="Error",
                )
            )

    def test_event_emitted(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        start_execution_uc: StartExecutionUseCase,
        fail_execution_uc: FailExecutionUseCase,
        fake_outbox: FakeAutomationOutbox,
    ) -> None:
        aid, eid = _full_lifecycle_to_running(
            create_automation_uc, add_trigger_uc, add_action_uc,
            activate_automation_uc, start_execution_uc,
        )
        fail_execution_uc.execute(
            FailExecutionRequest(
                automation_id=aid,
                execution_id=eid,
                failure_reason="Error",
            )
        )
        events = [
            e
            for e in fake_outbox.append_calls
            if isinstance(e, AutomationExecutionFailed)
        ]
        assert len(events) == 1
        assert events[0].failure_reason == "Error"

    def test_empty_failure_reason_rejected(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        start_execution_uc: StartExecutionUseCase,
        fail_execution_uc: FailExecutionUseCase,
    ) -> None:
        aid, eid = _full_lifecycle_to_running(
            create_automation_uc, add_trigger_uc, add_action_uc,
            activate_automation_uc, start_execution_uc,
        )
        with pytest.raises(InvalidFailureReasonError):
            fail_execution_uc.execute(
                FailExecutionRequest(
                    automation_id=aid,
                    execution_id=eid,
                    failure_reason="",
                )
            )


class TestGetAutomationUseCase:
    def test_get_existing_automation(
        self,
        create_automation_uc: CreateAutomationUseCase,
        get_automation_uc: GetAutomationUseCase,
    ) -> None:
        resp = _create_automation(create_automation_uc)
        response = get_automation_uc.execute(
            GetAutomationRequest(automation_id=resp.automation_id)
        )
        assert isinstance(response, AutomationResponse)
        assert response.automation_id == resp.automation_id
        assert response.name == "Test Automation"
        assert response.status == "draft"

    def test_get_nonexistent_automation_raises_error(
        self,
        get_automation_uc: GetAutomationUseCase,
    ) -> None:
        with pytest.raises(AutomationNotFoundError):
            get_automation_uc.execute(
                GetAutomationRequest(
                    automation_id="00000000-0000-0000-0000-000000000000"
                )
            )

    def test_automation_with_triggers_and_actions_shows_counts(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        get_automation_uc: GetAutomationUseCase,
    ) -> None:
        aid, _ = _create_automation_with_trigger_and_action(
            create_automation_uc, add_trigger_uc, add_action_uc,
        )
        response = get_automation_uc.execute(
            GetAutomationRequest(automation_id=aid)
        )
        assert response.trigger_count == 1
        assert response.action_count == 1


class TestListAutomationsUseCase:
    def test_list_all(
        self,
        create_automation_uc: CreateAutomationUseCase,
        list_automations_uc: ListAutomationsUseCase,
    ) -> None:
        _create_automation(create_automation_uc, name="First")
        _create_automation(create_automation_uc, name="Second")
        response = list_automations_uc.execute(ListAutomationsRequest())
        assert isinstance(response, ListAutomationsResponse)
        assert response.total == 2

    def test_list_empty(
        self,
        list_automations_uc: ListAutomationsUseCase,
    ) -> None:
        response = list_automations_uc.execute(ListAutomationsRequest())
        assert response.total == 0
        assert response.automations == []

    def test_filter_by_status(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        list_automations_uc: ListAutomationsUseCase,
    ) -> None:
        resp1 = _create_automation(create_automation_uc, name="Draft")
        aid2, _ = _create_automation_with_trigger_and_action(
            create_automation_uc, add_trigger_uc, add_action_uc,
            name="Active",
        )
        activate_automation_uc.execute(
            AutomationLifecycleRequest(automation_id=aid2)
        )
        response = list_automations_uc.execute(
            ListAutomationsRequest(status="active")
        )
        assert response.total == 1
        assert response.automations[0].name == "Active"

    def test_filter_by_execution_mode(
        self,
        create_automation_uc: CreateAutomationUseCase,
        list_automations_uc: ListAutomationsUseCase,
    ) -> None:
        _create_automation(create_automation_uc, name="Once")
        _create_automation(
            create_automation_uc, name="Recurring", execution_mode="recurring"
        )
        response = list_automations_uc.execute(
            ListAutomationsRequest(execution_mode="recurring")
        )
        assert response.total == 1
        assert response.automations[0].name == "Recurring"


class TestGetTriggerUseCase:
    def test_get_existing_trigger(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        get_trigger_uc: GetTriggerUseCase,
    ) -> None:
        aid, tid = _create_automation_with_trigger(
            create_automation_uc, add_trigger_uc,
        )
        response = get_trigger_uc.execute(
            GetTriggerRequest(trigger_id=tid)
        )
        assert isinstance(response, TriggerResponse)
        assert response.trigger_id == tid
        assert response.trigger_type == "manual"
        assert response.enabled is True

    def test_get_nonexistent_trigger_raises_error(
        self,
        get_trigger_uc: GetTriggerUseCase,
    ) -> None:
        with pytest.raises(TriggerNotFoundError):
            get_trigger_uc.execute(
                GetTriggerRequest(
                    trigger_id="00000000-0000-0000-0000-000000000000"
                )
            )


class TestListTriggersUseCase:
    def test_list_all(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        list_triggers_uc: ListTriggersUseCase,
    ) -> None:
        resp = _create_automation(create_automation_uc, name="A")
        add_trigger_uc.execute(
            AddTriggerRequest(
                automation_id=resp.automation_id, trigger_type="manual"
            )
        )
        add_trigger_uc.execute(
            AddTriggerRequest(
                automation_id=resp.automation_id, trigger_type="scheduled",
                expression="0 9 * * 1",
            )
        )
        response = list_triggers_uc.execute(ListTriggersRequest())
        assert response.total == 2

    def test_list_empty(
        self,
        list_triggers_uc: ListTriggersUseCase,
    ) -> None:
        response = list_triggers_uc.execute(ListTriggersRequest())
        assert response.total == 0
        assert response.triggers == []

    def test_filter_by_trigger_type(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        list_triggers_uc: ListTriggersUseCase,
    ) -> None:
        resp = _create_automation(create_automation_uc)
        add_trigger_uc.execute(
            AddTriggerRequest(
                automation_id=resp.automation_id, trigger_type="manual"
            )
        )
        add_trigger_uc.execute(
            AddTriggerRequest(
                automation_id=resp.automation_id,
                trigger_type="scheduled",
                expression="0 9 * * 1",
            )
        )
        response = list_triggers_uc.execute(
            ListTriggersRequest(trigger_type="manual")
        )
        assert response.total == 1


class TestGetExecutionUseCase:
    def test_get_existing_execution(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        start_execution_uc: StartExecutionUseCase,
        get_execution_uc: GetExecutionUseCase,
    ) -> None:
        aid, eid = _full_lifecycle_to_running(
            create_automation_uc, add_trigger_uc, add_action_uc,
            activate_automation_uc, start_execution_uc,
        )
        response = get_execution_uc.execute(
            GetExecutionRequest(execution_id=eid)
        )
        assert isinstance(response, ExecutionResponse)
        assert response.execution_id == eid
        assert response.status == "running"

    def test_get_nonexistent_execution_raises_error(
        self,
        get_execution_uc: GetExecutionUseCase,
    ) -> None:
        with pytest.raises(AutomationExecutionNotFoundError):
            get_execution_uc.execute(
                GetExecutionRequest(
                    execution_id="00000000-0000-0000-0000-000000000000"
                )
            )


class TestListExecutionsUseCase:
    def test_list_all(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        start_execution_uc: StartExecutionUseCase,
        list_executions_uc: ListExecutionsUseCase,
    ) -> None:
        aid, eid = _full_lifecycle_to_running(
            create_automation_uc, add_trigger_uc, add_action_uc,
            activate_automation_uc, start_execution_uc,
        )
        response = list_executions_uc.execute(ListExecutionsRequest())
        assert response.total == 1

    def test_list_empty(
        self,
        list_executions_uc: ListExecutionsUseCase,
    ) -> None:
        response = list_executions_uc.execute(ListExecutionsRequest())
        assert response.total == 0

    def test_filter_by_status(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        start_execution_uc: StartExecutionUseCase,
        list_executions_uc: ListExecutionsUseCase,
    ) -> None:
        aid, eid = _full_lifecycle_to_running(
            create_automation_uc, add_trigger_uc, add_action_uc,
            activate_automation_uc, start_execution_uc,
        )
        response = list_executions_uc.execute(
            ListExecutionsRequest(status="running")
        )
        assert response.total == 1

    def test_filter_by_automation_id(
        self,
        create_automation_uc: CreateAutomationUseCase,
        add_trigger_uc: AddTriggerUseCase,
        add_action_uc: AddActionUseCase,
        activate_automation_uc: ActivateAutomationUseCase,
        start_execution_uc: StartExecutionUseCase,
        list_executions_uc: ListExecutionsUseCase,
    ) -> None:
        aid, eid = _full_lifecycle_to_running(
            create_automation_uc, add_trigger_uc, add_action_uc,
            activate_automation_uc, start_execution_uc,
        )
        response = list_executions_uc.execute(
            ListExecutionsRequest(automation_id=aid)
        )
        assert response.total == 1


class TestExceptionHierarchy:
    def test_use_case_error_base(self) -> None:
        assert issubclass(AutomationNotFoundError, UseCaseError)
        assert issubclass(TriggerNotFoundError, UseCaseError)
        assert issubclass(AutomationExecutionNotFoundError, UseCaseError)

    def test_not_found_error_message(self) -> None:
        err = AutomationNotFoundError("abc-123")
        assert str(err) == "Automation not found: abc-123"
        assert err.automation_id == "abc-123"

    def test_trigger_not_found_message(self) -> None:
        err = TriggerNotFoundError("trg-456")
        assert str(err) == "Trigger not found: trg-456"
        assert err.trigger_id == "trg-456"

    def test_execution_not_found_message(self) -> None:
        err = AutomationExecutionNotFoundError("exc-789")
        assert str(err) == "Automation execution not found: exc-789"
        assert err.execution_id == "exc-789"


class TestDTOIntegrity:
    def test_create_automation_request_defaults(self) -> None:
        req = CreateAutomationRequest(name="Test", description="Desc")
        assert req.execution_mode == "once"

    def test_create_automation_response_type(self) -> None:
        from datetime import datetime

        resp = CreateAutomationResponse(
            automation_id="id",
            name="n",
            description="d",
            execution_mode="once",
            status="draft",
            created_at=datetime.now(),
        )
        assert isinstance(resp, CreateAutomationResponse)

    def test_list_automations_response_defaults(self) -> None:
        resp = ListAutomationsResponse()
        assert resp.automations == []
        assert resp.total == 0

    def test_automation_lifecycle_response_defaults(self) -> None:
        resp = AutomationLifecycleResponse(
            automation_id="id", status="active"
        )
        assert resp.updated_at is None

    def test_trigger_lifecycle_response(self) -> None:
        resp = TriggerLifecycleResponse(
            trigger_id="tid", enabled=False
        )
        assert resp.enabled is False

    def test_start_execution_response_defaults(self) -> None:
        resp = StartExecutionResponse(
            automation_id="aid",
            execution_id="eid",
            status="running",
        )
        assert resp.started_at is None

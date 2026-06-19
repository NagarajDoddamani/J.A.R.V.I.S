from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator
from uuid import UUID

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.automation.adapters.outbound.clock import SystemClockAdapter
from backend.automation.adapters.outbound.id_generator import (
    UuidGeneratorAdapter,
)
from backend.automation.adapters.outbound.mapper import (
    AutomationExecutionMapperImpl,
    AutomationMapperImpl,
    AutomationOutboxMapperImpl,
    TriggerMapperImpl,
)
from backend.automation.adapters.outbound.models import (
    AutomationOutboxModel,
    Base,
)
from backend.automation.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyAutomationExecutionRepository,
    SqlAlchemyAutomationOutboxAdapter,
    SqlAlchemyAutomationRepository,
    SqlAlchemyTriggerRepository,
)
from backend.automation.domain.model import (
    Automation,
    AutomationDescription,
    AutomationExecution,
    AutomationId,
    AutomationName,
    AutomationStatus,
    ExecutionMode,
    ExecutionResult,
    ExecutionStatus,
    FailureReason,
    Trigger,
    TriggerExpression,
    TriggerId,
    TriggerType,
    WorkflowExecutionId,
)

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def engine() -> Iterator[Engine]:
    e = create_engine("sqlite://", echo=False)
    for t in Base.metadata.tables.values():
        t.schema = None
    Base.metadata.create_all(bind=e)
    yield e
    e.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture
def automation_mapper() -> AutomationMapperImpl:
    return AutomationMapperImpl()


@pytest.fixture
def trigger_mapper() -> TriggerMapperImpl:
    return TriggerMapperImpl()


@pytest.fixture
def execution_mapper() -> AutomationExecutionMapperImpl:
    return AutomationExecutionMapperImpl()


@pytest.fixture
def outbox_mapper() -> AutomationOutboxMapperImpl:
    return AutomationOutboxMapperImpl()


@pytest.fixture
def clock() -> SystemClockAdapter:
    return SystemClockAdapter()


@pytest.fixture
def id_gen() -> UuidGeneratorAdapter:
    return UuidGeneratorAdapter()


@pytest.fixture
def automation_repo(
    session: Session,
    automation_mapper: AutomationMapperImpl,
    trigger_mapper: TriggerMapperImpl,
) -> SqlAlchemyAutomationRepository:
    return SqlAlchemyAutomationRepository(
        session=session,
        mapper=automation_mapper,
        trigger_mapper=trigger_mapper,
    )


@pytest.fixture
def trigger_repo(
    session: Session,
    trigger_mapper: TriggerMapperImpl,
) -> SqlAlchemyTriggerRepository:
    return SqlAlchemyTriggerRepository(
        session=session, mapper=trigger_mapper
    )


@pytest.fixture
def execution_repo(
    session: Session,
    execution_mapper: AutomationExecutionMapperImpl,
) -> SqlAlchemyAutomationExecutionRepository:
    return SqlAlchemyAutomationExecutionRepository(
        session=session, mapper=execution_mapper
    )


@pytest.fixture
def outbox_adapter(
    session: Session,
    outbox_mapper: AutomationOutboxMapperImpl,
) -> SqlAlchemyAutomationOutboxAdapter:
    return SqlAlchemyAutomationOutboxAdapter(
        session=session, mapper=outbox_mapper
    )


@pytest.fixture
def a_automation() -> Automation:
    return Automation(
        automation_id=AutomationId(
            value=UUID("00000000-0000-0000-0000-000000000001")
        ),
        name=AutomationName(value="Test Automation"),
        description=AutomationDescription(value="Test Description"),
        status=AutomationStatus.DRAFT,
        execution_mode=ExecutionMode.ONCE,
        created_at=NOW,
    )


@pytest.fixture
def a_trigger() -> Trigger:
    return Trigger(
        trigger_id=TriggerId(
            value=UUID("00000000-0000-0000-0000-000000000010")
        ),
        trigger_type=TriggerType.MANUAL,
        enabled=True,
    )


# ===================================================================
# Automation Repository Integration Tests
# ===================================================================


class TestAutomationRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        automation_repo: SqlAlchemyAutomationRepository,
        a_automation: Automation,
    ) -> None:
        automation_repo.save(a_automation)
        stored = automation_repo.find_by_id(a_automation.automation_id)
        assert stored is not None
        assert stored.automation_id == a_automation.automation_id
        assert str(stored.name) == "Test Automation"
        assert stored.status == AutomationStatus.DRAFT

    def test_save_updates_existing(
        self,
        automation_repo: SqlAlchemyAutomationRepository,
        a_automation: Automation,
    ) -> None:
        automation_repo.save(a_automation)
        a_automation._status = AutomationStatus.ACTIVE
        a_automation._updated_at = NOW
        automation_repo.save(a_automation)
        stored = automation_repo.find_by_id(a_automation.automation_id)
        assert stored is not None
        assert stored.status == AutomationStatus.ACTIVE

    def test_find_by_id_returns_none_for_missing(
        self,
        automation_repo: SqlAlchemyAutomationRepository,
    ) -> None:
        result = automation_repo.find_by_id(
            AutomationId(value=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"))
        )
        assert result is None

    def test_find_by_status(
        self,
        automation_repo: SqlAlchemyAutomationRepository,
        a_automation: Automation,
    ) -> None:
        automation_repo.save(a_automation)
        results = automation_repo.find_by_status(AutomationStatus.DRAFT)
        assert len(results) == 1
        results = automation_repo.find_by_status(AutomationStatus.ACTIVE)
        assert len(results) == 0

    def test_find_by_execution_mode(
        self,
        automation_repo: SqlAlchemyAutomationRepository,
        a_automation: Automation,
    ) -> None:
        automation_repo.save(a_automation)
        results = automation_repo.find_by_execution_mode(ExecutionMode.ONCE)
        assert len(results) == 1
        results = automation_repo.find_by_execution_mode(
            ExecutionMode.RECURRING
        )
        assert len(results) == 0

    def test_find_all(
        self,
        automation_repo: SqlAlchemyAutomationRepository,
        a_automation: Automation,
    ) -> None:
        automation_repo.save(a_automation)
        results = automation_repo.find_all()
        assert len(results) == 1

    def test_count(
        self,
        automation_repo: SqlAlchemyAutomationRepository,
        a_automation: Automation,
    ) -> None:
        assert automation_repo.count() == 0
        automation_repo.save(a_automation)
        assert automation_repo.count() == 1

    def test_multiple_automations(
        self,
        automation_repo: SqlAlchemyAutomationRepository,
        a_automation: Automation,
    ) -> None:
        automation_repo.save(a_automation)
        second = Automation(
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000002")
            ),
            name=AutomationName(value="Second"),
            description=AutomationDescription(value="Desc"),
            status=AutomationStatus.DRAFT,
            execution_mode=ExecutionMode.ONCE,
            created_at=NOW,
        )
        automation_repo.save(second)
        assert automation_repo.count() == 2
        assert len(automation_repo.find_all()) == 2


# ===================================================================
# Trigger Repository Integration Tests
# ===================================================================


class TestTriggerRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        trigger_repo: SqlAlchemyTriggerRepository,
        a_trigger: Trigger,
    ) -> None:
        trigger_repo.save(a_trigger)
        stored = trigger_repo.find_by_id(a_trigger.trigger_id)
        assert stored is not None
        assert stored.trigger_id == a_trigger.trigger_id
        assert stored.enabled is True

    def test_find_by_id_returns_none_for_missing(
        self,
        trigger_repo: SqlAlchemyTriggerRepository,
    ) -> None:
        result = trigger_repo.find_by_id(
            TriggerId(value=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"))
        )
        assert result is None

    def test_find_by_type(
        self,
        trigger_repo: SqlAlchemyTriggerRepository,
        a_trigger: Trigger,
    ) -> None:
        trigger_repo.save(a_trigger)
        results = trigger_repo.find_by_type(TriggerType.MANUAL)
        assert len(results) == 1
        results = trigger_repo.find_by_type(TriggerType.SCHEDULED)
        assert len(results) == 0

    def test_find_enabled(
        self,
        trigger_repo: SqlAlchemyTriggerRepository,
        a_trigger: Trigger,
    ) -> None:
        trigger_repo.save(a_trigger)
        results = trigger_repo.find_enabled()
        assert len(results) == 1
        disabled = Trigger(
            trigger_id=TriggerId(
                value=UUID("00000000-0000-0000-0000-000000000011")
            ),
            trigger_type=TriggerType.MANUAL,
            enabled=False,
        )
        trigger_repo.save(disabled)
        results = trigger_repo.find_enabled()
        assert len(results) == 1

    def test_save_updates_existing(
        self,
        trigger_repo: SqlAlchemyTriggerRepository,
        a_trigger: Trigger,
    ) -> None:
        trigger_repo.save(a_trigger)
        a_trigger._enabled = False
        trigger_repo.save(a_trigger)
        stored = trigger_repo.find_by_id(a_trigger.trigger_id)
        assert stored is not None
        assert stored.enabled is False

    def test_find_all(
        self,
        trigger_repo: SqlAlchemyTriggerRepository,
        a_trigger: Trigger,
    ) -> None:
        trigger_repo.save(a_trigger)
        assert len(trigger_repo.find_all()) == 1

    def test_count(
        self,
        trigger_repo: SqlAlchemyTriggerRepository,
        a_trigger: Trigger,
    ) -> None:
        assert trigger_repo.count() == 0
        trigger_repo.save(a_trigger)
        assert trigger_repo.count() == 1


# ===================================================================
# Automation Execution Repository Integration Tests
# ===================================================================


class TestExecutionRepositoryIntegration:
    def test_save_and_find_by_id(
        self,
        execution_repo: SqlAlchemyAutomationExecutionRepository,
    ) -> None:
        execution = AutomationExecution(
            execution_id=WorkflowExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
        )
        execution_repo.save(execution)
        stored = execution_repo.find_by_id(execution.execution_id)
        assert stored is not None
        assert stored.status == ExecutionStatus.PENDING

    def test_find_by_id_returns_none_for_missing(
        self,
        execution_repo: SqlAlchemyAutomationExecutionRepository,
    ) -> None:
        result = execution_repo.find_by_id(
            WorkflowExecutionId(
                value=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
            )
        )
        assert result is None

    def test_find_by_status(
        self,
        execution_repo: SqlAlchemyAutomationExecutionRepository,
    ) -> None:
        execution = AutomationExecution(
            execution_id=WorkflowExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
        )
        execution_repo.save(execution)
        results = execution_repo.find_by_status(ExecutionStatus.PENDING)
        assert len(results) == 1
        results = execution_repo.find_by_status(ExecutionStatus.RUNNING)
        assert len(results) == 0

    def test_find_by_automation_id(
        self,
        execution_repo: SqlAlchemyAutomationExecutionRepository,
    ) -> None:
        aid = AutomationId(
            value=UUID("00000000-0000-0000-0000-000000000001")
        )
        execution = AutomationExecution(
            execution_id=WorkflowExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            automation_id=aid,
        )
        execution_repo.save(execution)
        results = execution_repo.find_by_automation_id(aid)
        assert len(results) == 1

    def test_save_updates_existing(
        self,
        execution_repo: SqlAlchemyAutomationExecutionRepository,
    ) -> None:
        execution = AutomationExecution(
            execution_id=WorkflowExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
        )
        execution_repo.save(execution)
        execution._status = ExecutionStatus.RUNNING
        execution._started_at = NOW
        execution_repo.save(execution)
        stored = execution_repo.find_by_id(execution.execution_id)
        assert stored is not None
        assert stored.status == ExecutionStatus.RUNNING
        assert stored.started_at is not None

    def test_find_all(
        self,
        execution_repo: SqlAlchemyAutomationExecutionRepository,
    ) -> None:
        execution = AutomationExecution(
            execution_id=WorkflowExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
        )
        execution_repo.save(execution)
        assert len(execution_repo.find_all()) == 1

    def test_count(
        self,
        execution_repo: SqlAlchemyAutomationExecutionRepository,
    ) -> None:
        assert execution_repo.count() == 0
        execution = AutomationExecution(
            execution_id=WorkflowExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
        )
        execution_repo.save(execution)
        assert execution_repo.count() == 1

    def test_completed_execution_fields(
        self,
        execution_repo: SqlAlchemyAutomationExecutionRepository,
    ) -> None:
        execution = AutomationExecution(
            execution_id=WorkflowExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            status=ExecutionStatus.COMPLETED,
            result=ExecutionResult(value="Done"),
            started_at=NOW,
            completed_at=NOW,
        )
        execution_repo.save(execution)
        stored = execution_repo.find_by_id(execution.execution_id)
        assert stored is not None
        assert stored.status == ExecutionStatus.COMPLETED
        assert str(stored.result) == "Done"

    def test_failed_execution_fields(
        self,
        execution_repo: SqlAlchemyAutomationExecutionRepository,
    ) -> None:
        execution = AutomationExecution(
            execution_id=WorkflowExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            status=ExecutionStatus.FAILED,
            failure_reason=FailureReason(value="Error"),
            started_at=NOW,
            completed_at=NOW,
        )
        execution_repo.save(execution)
        stored = execution_repo.find_by_id(execution.execution_id)
        assert stored is not None
        assert stored.status == ExecutionStatus.FAILED
        assert str(stored.failure_reason) == "Error"


# ===================================================================
# Outbox Adapter Integration Tests
# ===================================================================


class TestOutboxAdapterIntegration:
    def test_append_and_fetch_unpublished(
        self,
        session: Session,
        outbox_adapter: SqlAlchemyAutomationOutboxAdapter,
    ) -> None:
        from backend.automation.domain.model import AutomationCreated

        event = AutomationCreated(
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            name="Test",
            description="Desc",
            execution_mode="once",
            occurred_at=NOW,
        )
        outbox_adapter.append(event)
        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], AutomationCreated)

    def test_mark_published(
        self,
        outbox_adapter: SqlAlchemyAutomationOutboxAdapter,
    ) -> None:
        from backend.automation.domain.model import AutomationCreated

        event = AutomationCreated(
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            name="Test",
            description="Desc",
            execution_mode="once",
            occurred_at=NOW,
        )
        outbox_adapter.append(event)
        fetched = outbox_adapter.fetch_unpublished()
        outbox_adapter.mark_published(str(fetched[0].event_id))
        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 0

    def test_fifo_ordering(
        self,
        outbox_adapter: SqlAlchemyAutomationOutboxAdapter,
    ) -> None:
        from datetime import timedelta
        from backend.automation.domain.model import (
            AutomationActivated,
            AutomationCreated,
        )

        event1 = AutomationCreated(
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            name="Test",
            description="Desc",
            execution_mode="once",
            occurred_at=NOW,
        )
        event2 = AutomationActivated(
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            occurred_at=NOW + timedelta(seconds=1),
        )
        outbox_adapter.append(event1)
        outbox_adapter.append(event2)
        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 2
        assert isinstance(unpublished[0], AutomationCreated)
        assert isinstance(unpublished[1], AutomationActivated)

    def test_fetch_unpublished_limit(
        self,
        outbox_adapter: SqlAlchemyAutomationOutboxAdapter,
    ) -> None:
        from backend.automation.domain.model import AutomationCreated

        for i in range(5):
            event = AutomationCreated(
                automation_id=AutomationId(),
                name=f"Test {i}",
                description="Desc",
                execution_mode="once",
                occurred_at=NOW,
            )
            outbox_adapter.append(event)
        assert len(outbox_adapter.fetch_unpublished(limit=3)) == 3
        assert len(outbox_adapter.fetch_unpublished()) == 5

    def test_mark_published_idempotent(
        self,
        outbox_adapter: SqlAlchemyAutomationOutboxAdapter,
    ) -> None:
        from backend.automation.domain.model import AutomationCreated

        event = AutomationCreated(
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            name="Test",
            description="Desc",
            execution_mode="once",
            occurred_at=NOW,
        )
        outbox_adapter.append(event)
        fetched = outbox_adapter.fetch_unpublished()
        outbox_adapter.mark_published(str(fetched[0].event_id))
        outbox_adapter.mark_published(str(fetched[0].event_id))
        assert len(outbox_adapter.fetch_unpublished()) == 0

    def test_outbox_model_default_published_false(
        self,
        session: Session,
    ) -> None:
        from uuid import uuid4

        model = AutomationOutboxModel(
            message_id=str(uuid4()),
            subject="automation.created",
            aggregate_id="agg",
            created_at=NOW,
            payload="{}",
        )
        session.add(model)
        session.flush()
        persisted = session.get(AutomationOutboxModel, model.message_id)
        assert persisted is not None
        assert persisted.published_at is None


# ===================================================================
# Relationship Integrity Tests
# ===================================================================


class TestRelationshipIntegrity:
    def test_automation_with_triggers_roundtrip(
        self,
        session: Session,
        automation_repo: SqlAlchemyAutomationRepository,
        trigger_repo: SqlAlchemyTriggerRepository,
        a_automation: Automation,
    ) -> None:
        automation_repo.save(a_automation)
        trigger = Trigger(
            trigger_id=TriggerId(
                value=UUID("00000000-0000-0000-0000-000000000010")
            ),
            trigger_type=TriggerType.MANUAL,
            enabled=True,
        )
        trigger_repo.save(trigger)
        stored = automation_repo.find_by_id(a_automation.automation_id)
        assert stored is not None

    def test_automation_save_with_trigger_load(
        self,
        session: Session,
        automation_repo: SqlAlchemyAutomationRepository,
        trigger_repo: SqlAlchemyTriggerRepository,
        a_automation: Automation,
    ) -> None:
        automation_repo.save(a_automation)
        trigger = Trigger(
            trigger_id=TriggerId(
                value=UUID("00000000-0000-0000-0000-000000000010")
            ),
            trigger_type=TriggerType.SCHEDULED,
            expression=TriggerExpression(value="0 9 * * 1"),
            enabled=True,
        )
        trigger_repo.save(trigger)
        stored = automation_repo.find_by_id(a_automation.automation_id)
        assert stored is not None

    def test_execution_belongs_to_automation(
        self,
        session: Session,
        automation_repo: SqlAlchemyAutomationRepository,
        execution_repo: SqlAlchemyAutomationExecutionRepository,
        a_automation: Automation,
    ) -> None:
        automation_repo.save(a_automation)
        execution = AutomationExecution(
            execution_id=WorkflowExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            automation_id=a_automation.automation_id,
        )
        execution_repo.save(execution)
        executions = execution_repo.find_by_automation_id(
            a_automation.automation_id
        )
        assert len(executions) == 1

    def test_complete_sqlite_roundtrip(
        self,
        session: Session,
        automation_repo: SqlAlchemyAutomationRepository,
        trigger_repo: SqlAlchemyTriggerRepository,
        execution_repo: SqlAlchemyAutomationExecutionRepository,
        outbox_adapter: SqlAlchemyAutomationOutboxAdapter,
    ) -> None:
        from backend.automation.domain.model import AutomationCreated

        automation = Automation(
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            name=AutomationName(value="Full"),
            description=AutomationDescription(value="Roundtrip"),
            status=AutomationStatus.DRAFT,
            execution_mode=ExecutionMode.ONCE,
            created_at=NOW,
        )
        automation_repo.save(automation)

        trigger = Trigger(
            trigger_id=TriggerId(
                value=UUID("00000000-0000-0000-0000-000000000010")
            ),
            trigger_type=TriggerType.MANUAL,
            enabled=True,
        )
        trigger_repo.save(trigger)

        execution = AutomationExecution(
            execution_id=WorkflowExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            automation_id=automation.automation_id,
        )
        execution_repo.save(execution)

        event = AutomationCreated(
            automation_id=automation.automation_id,
            name="Full",
            description="Roundtrip",
            execution_mode="once",
            occurred_at=NOW,
        )
        outbox_adapter.append(event)

        assert automation_repo.count() == 1
        assert trigger_repo.count() == 1
        assert execution_repo.count() == 1
        assert len(outbox_adapter.fetch_unpublished()) == 1

        stored_auto = automation_repo.find_by_id(automation.automation_id)
        assert stored_auto is not None

        stored_trigger = trigger_repo.find_by_id(trigger.trigger_id)
        assert stored_trigger is not None

        stored_exec = execution_repo.find_by_id(execution.execution_id)
        assert stored_exec is not None

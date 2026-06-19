from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

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
from backend.automation.application.persistence.mapper import (
    AutomationExecutionMapper,
    AutomationMapper,
    AutomationOutboxMapper,
    TriggerMapper,
)
from backend.automation.domain.model import (
    ActionAdded,
    ActionType,
    Automation,
    AutomationActivated,
    AutomationCreated,
    AutomationDescription,
    AutomationDisabled,
    AutomationExecution,
    AutomationExecutionCompleted,
    AutomationExecutionFailed,
    AutomationExecutionStarted,
    AutomationId,
    AutomationName,
    AutomationPaused,
    AutomationStatus,
    ExecutionMode,
    ExecutionResult,
    ExecutionStatus,
    FailureReason,
    Trigger,
    TriggerAdded,
    TriggerDisabled,
    TriggerEnabled,
    TriggerExpression,
    TriggerId,
    TriggerType,
    WorkflowExecutionId,
)

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


def _make_automation(
    status: AutomationStatus = AutomationStatus.DRAFT,
    execution_mode: ExecutionMode = ExecutionMode.ONCE,
) -> Automation:
    return Automation(
        automation_id=AutomationId(
            value=UUID("00000000-0000-0000-0000-000000000001")
        ),
        name=AutomationName(value="Test Automation"),
        description=AutomationDescription(value="Test Description"),
        status=status,
        execution_mode=execution_mode,
        created_at=NOW,
    )


def _make_trigger(
    trigger_type: TriggerType = TriggerType.MANUAL,
    enabled: bool = True,
) -> Trigger:
    return Trigger(
        trigger_id=TriggerId(
            value=UUID("00000000-0000-0000-0000-000000000010")
        ),
        trigger_type=trigger_type,
        expression=TriggerExpression(value="0 9 * * 1")
        if trigger_type == TriggerType.SCHEDULED
        else None,
        enabled=enabled,
    )


def _make_execution(
    status: ExecutionStatus = ExecutionStatus.PENDING,
) -> AutomationExecution:
    return AutomationExecution(
        execution_id=WorkflowExecutionId(
            value=UUID("00000000-0000-0000-0000-000000000020")
        ),
        automation_id=AutomationId(
            value=UUID("00000000-0000-0000-0000-000000000001")
        ),
        status=status,
        started_at=None,
        completed_at=None,
    )


class TestSystemClockAdapter:
    def test_now_returns_utc(self) -> None:
        clock = SystemClockAdapter()
        result = clock.now()
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result) == timezone.utc.utcoffset(result)

    def test_now_returns_datetime(self) -> None:
        clock = SystemClockAdapter()
        result = clock.now()
        assert isinstance(result, datetime)


class TestUuidGeneratorAdapter:
    def test_generate_automation_id_returns_str(self) -> None:
        gen = UuidGeneratorAdapter()
        result = gen.generate_automation_id()
        assert isinstance(result, str)
        assert UUID(result)

    def test_generate_trigger_id_returns_str(self) -> None:
        gen = UuidGeneratorAdapter()
        result = gen.generate_trigger_id()
        assert isinstance(result, str)
        assert UUID(result)

    def test_generate_execution_id_returns_str(self) -> None:
        gen = UuidGeneratorAdapter()
        result = gen.generate_execution_id()
        assert isinstance(result, str)
        assert UUID(result)

    def test_unique_ids(self) -> None:
        gen = UuidGeneratorAdapter()
        ids = {
            gen.generate_automation_id(),
            gen.generate_trigger_id(),
            gen.generate_execution_id(),
        }
        assert len(ids) == 3


class TestAutomationMapperImpl:
    def test_protocol_conformance(self) -> None:
        mapper: AutomationMapper = AutomationMapperImpl()
        assert isinstance(mapper, AutomationMapperImpl)

    def test_domain_to_dto(self) -> None:
        mapper = AutomationMapperImpl()
        automation = _make_automation()
        dto = mapper.domain_to_dto(automation)
        assert dto.automation_id == str(automation.automation_id)
        assert dto.name == "Test Automation"
        assert dto.description == "Test Description"
        assert dto.status == "draft"
        assert dto.execution_mode == "once"
        assert dto.created_at == NOW

    def test_dto_to_domain(self) -> None:
        mapper = AutomationMapperImpl()
        automation = _make_automation()
        dto = mapper.domain_to_dto(automation)
        result = mapper.dto_to_domain(dto)
        assert result.automation_id == automation.automation_id
        assert str(result.name) == "Test Automation"
        assert str(result.description) == "Test Description"
        assert result.status == AutomationStatus.DRAFT
        assert result.execution_mode == ExecutionMode.ONCE

    def test_roundtrip(self) -> None:
        mapper = AutomationMapperImpl()
        original = _make_automation(
            status=AutomationStatus.ACTIVE,
            execution_mode=ExecutionMode.RECURRING,
        )
        dto = mapper.domain_to_dto(original)
        result = mapper.dto_to_domain(dto)
        assert result.automation_id == original.automation_id
        assert str(result.name) == str(original.name)
        assert result.status == AutomationStatus.ACTIVE
        assert result.execution_mode == ExecutionMode.RECURRING

    def test_nullable_fields(self) -> None:
        mapper = AutomationMapperImpl()
        automation = Automation(
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            status=AutomationStatus.DRAFT,
            execution_mode=ExecutionMode.ONCE,
            created_at=NOW,
        )
        dto = mapper.domain_to_dto(automation)
        assert dto.name is None
        assert dto.description is None
        result = mapper.dto_to_domain(dto)
        assert result.name is None
        assert result.description is None


class TestTriggerMapperImpl:
    def test_protocol_conformance(self) -> None:
        mapper: TriggerMapper = TriggerMapperImpl()
        assert isinstance(mapper, TriggerMapperImpl)

    def test_domain_to_dto(self) -> None:
        mapper = TriggerMapperImpl()
        trigger = _make_trigger()
        dto = mapper.domain_to_dto(trigger)
        assert dto.trigger_id == str(trigger.trigger_id)
        assert dto.trigger_type == "manual"
        assert dto.enabled is True

    def test_dto_to_domain(self) -> None:
        mapper = TriggerMapperImpl()
        trigger = _make_trigger()
        dto = mapper.domain_to_dto(trigger)
        result = mapper.dto_to_domain(dto)
        assert result.trigger_id == trigger.trigger_id
        assert result.trigger_type == TriggerType.MANUAL
        assert result.enabled is True

    def test_roundtrip(self) -> None:
        mapper = TriggerMapperImpl()
        original = _make_trigger(
            trigger_type=TriggerType.SCHEDULED, enabled=False
        )
        dto = mapper.domain_to_dto(original)
        result = mapper.dto_to_domain(dto)
        assert result.trigger_id == original.trigger_id
        assert result.trigger_type == TriggerType.SCHEDULED
        assert result.enabled is False
        assert str(result.expression) == "0 9 * * 1"

    def test_nullable_expression(self) -> None:
        mapper = TriggerMapperImpl()
        trigger = Trigger(
            trigger_id=TriggerId(
                value=UUID("00000000-0000-0000-0000-000000000010")
            ),
            trigger_type=TriggerType.MANUAL,
        )
        dto = mapper.domain_to_dto(trigger)
        assert dto.expression is None
        result = mapper.dto_to_domain(dto)
        assert result.expression is None


class TestAutomationExecutionMapperImpl:
    def test_protocol_conformance(self) -> None:
        mapper: AutomationExecutionMapper = AutomationExecutionMapperImpl()
        assert isinstance(mapper, AutomationExecutionMapperImpl)

    def test_domain_to_dto(self) -> None:
        mapper = AutomationExecutionMapperImpl()
        execution = _make_execution()
        dto = mapper.domain_to_dto(execution)
        assert dto.execution_id == str(execution.execution_id)
        assert dto.status == "pending"
        assert dto.result is None
        assert dto.failure_reason is None

    def test_dto_to_domain(self) -> None:
        mapper = AutomationExecutionMapperImpl()
        execution = _make_execution()
        dto = mapper.domain_to_dto(execution)
        result = mapper.dto_to_domain(dto)
        assert result.execution_id == execution.execution_id
        assert result.status == ExecutionStatus.PENDING

    def test_roundtrip(self) -> None:
        mapper = AutomationExecutionMapperImpl()
        original = AutomationExecution(
            execution_id=WorkflowExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            status=ExecutionStatus.COMPLETED,
            result=ExecutionResult(value="Success"),
            started_at=NOW,
            completed_at=NOW,
        )
        dto = mapper.domain_to_dto(original)
        result = mapper.dto_to_domain(dto)
        assert result.execution_id == original.execution_id
        assert result.status == ExecutionStatus.COMPLETED
        assert str(result.result) == "Success"
        assert result.started_at == NOW

    def test_failed_execution(self) -> None:
        mapper = AutomationExecutionMapperImpl()
        original = AutomationExecution(
            execution_id=WorkflowExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            status=ExecutionStatus.FAILED,
            failure_reason=FailureReason(value="Error occurred"),
            started_at=NOW,
            completed_at=NOW,
        )
        dto = mapper.domain_to_dto(original)
        result = mapper.dto_to_domain(dto)
        assert result.status == ExecutionStatus.FAILED
        assert str(result.failure_reason) == "Error occurred"

    def test_nullable_fields(self) -> None:
        mapper = AutomationExecutionMapperImpl()
        execution = AutomationExecution(
            execution_id=WorkflowExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
        )
        dto = mapper.domain_to_dto(execution)
        assert dto.result is None
        assert dto.failure_reason is None
        assert dto.started_at is None
        assert dto.completed_at is None


class TestAutomationOutboxMapperImpl:
    def test_protocol_conformance(self) -> None:
        mapper: AutomationOutboxMapper = AutomationOutboxMapperImpl()
        assert isinstance(mapper, AutomationOutboxMapperImpl)

    def test_automation_created_event(self) -> None:
        mapper = AutomationOutboxMapperImpl()
        event = AutomationCreated(
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            name="Test",
            description="Desc",
            execution_mode="once",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.created"
        assert dto.aggregate_id == str(event.automation_id)
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AutomationCreated)
        assert result.name == "Test"

    def test_automation_activated_event(self) -> None:
        mapper = AutomationOutboxMapperImpl()
        event = AutomationActivated(
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.activated"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AutomationActivated)

    def test_automation_paused_event(self) -> None:
        mapper = AutomationOutboxMapperImpl()
        event = AutomationPaused(
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.paused"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AutomationPaused)

    def test_automation_disabled_event(self) -> None:
        mapper = AutomationOutboxMapperImpl()
        event = AutomationDisabled(
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.disabled"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AutomationDisabled)

    def test_execution_started_event(self) -> None:
        mapper = AutomationOutboxMapperImpl()
        event = AutomationExecutionStarted(
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            execution_id=WorkflowExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.execution_started"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AutomationExecutionStarted)

    def test_execution_completed_event(self) -> None:
        mapper = AutomationOutboxMapperImpl()
        event = AutomationExecutionCompleted(
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            execution_id=WorkflowExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            result="Success",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.execution_completed"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AutomationExecutionCompleted)
        assert result.result == "Success"

    def test_execution_failed_event(self) -> None:
        mapper = AutomationOutboxMapperImpl()
        event = AutomationExecutionFailed(
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            execution_id=WorkflowExecutionId(
                value=UUID("00000000-0000-0000-0000-000000000020")
            ),
            failure_reason="Error",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.execution_failed"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, AutomationExecutionFailed)
        assert result.failure_reason == "Error"

    def test_trigger_added_event(self) -> None:
        mapper = AutomationOutboxMapperImpl()
        event = TriggerAdded(
            trigger_id=TriggerId(
                value=UUID("00000000-0000-0000-0000-000000000010")
            ),
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            trigger_type="manual",
            expression="",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.trigger_added"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, TriggerAdded)

    def test_trigger_enabled_event(self) -> None:
        mapper = AutomationOutboxMapperImpl()
        event = TriggerEnabled(
            trigger_id=TriggerId(
                value=UUID("00000000-0000-0000-0000-000000000010")
            ),
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.trigger_enabled"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, TriggerEnabled)

    def test_trigger_disabled_event(self) -> None:
        mapper = AutomationOutboxMapperImpl()
        event = TriggerDisabled(
            trigger_id=TriggerId(
                value=UUID("00000000-0000-0000-0000-000000000010")
            ),
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.trigger_disabled"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, TriggerDisabled)

    def test_action_added_event(self) -> None:
        mapper = AutomationOutboxMapperImpl()
        event = ActionAdded(
            automation_id=AutomationId(
                value=UUID("00000000-0000-0000-0000-000000000001")
            ),
            action_type="notification",
            occurred_at=NOW,
        )
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.action_added"
        result = mapper.dto_to_event(dto)
        assert isinstance(result, ActionAdded)
        assert result.action_type == "notification"

    def test_all_events_have_unique_types(self) -> None:
        mapper = AutomationOutboxMapperImpl()
        events: list = [
            AutomationCreated(
                automation_id=AutomationId(), name="n", description="d",
                execution_mode="once", occurred_at=NOW,
            ),
            AutomationActivated(
                automation_id=AutomationId(), occurred_at=NOW,
            ),
            AutomationPaused(
                automation_id=AutomationId(), occurred_at=NOW,
            ),
            AutomationDisabled(
                automation_id=AutomationId(), occurred_at=NOW,
            ),
            AutomationExecutionStarted(
                automation_id=AutomationId(),
                execution_id=WorkflowExecutionId(), occurred_at=NOW,
            ),
            AutomationExecutionCompleted(
                automation_id=AutomationId(),
                execution_id=WorkflowExecutionId(),
                result="ok", occurred_at=NOW,
            ),
            AutomationExecutionFailed(
                automation_id=AutomationId(),
                execution_id=WorkflowExecutionId(),
                failure_reason="err", occurred_at=NOW,
            ),
            TriggerAdded(
                trigger_id=TriggerId(),
                automation_id=AutomationId(),
                trigger_type="manual", expression="", occurred_at=NOW,
            ),
            TriggerEnabled(
                trigger_id=TriggerId(),
                automation_id=AutomationId(), occurred_at=NOW,
            ),
            TriggerDisabled(
                trigger_id=TriggerId(),
                automation_id=AutomationId(), occurred_at=NOW,
            ),
            ActionAdded(
                automation_id=AutomationId(),
                action_type="notification", occurred_at=NOW,
            ),
        ]
        type_strings = {
            mapper.event_to_dto(e).event_type for e in events
        }
        assert len(type_strings) == 11

    def test_unknown_event_type_raises_error(self) -> None:
        from backend.automation.application.persistence.dto import (
            AutomationOutboxStorageDTO,
        )

        mapper = AutomationOutboxMapperImpl()
        dto = AutomationOutboxStorageDTO(
            event_id="id",
            event_type="unknown.type",
            aggregate_id="agg",
            occurred_at=NOW,
            payload=None,
            published=False,
        )
        with pytest.raises(ValueError, match="Unknown event_type"):
            mapper.dto_to_event(dto)

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, Union
from uuid import UUID, uuid4

import pytest

from backend.automation.application.persistence.dto import (
    AutomationExecutionStorageDTO,
    AutomationOutboxStorageDTO,
    AutomationStorageDTO,
    TriggerStorageDTO,
)
from backend.automation.application.persistence.mapper import (
    AutomationExecutionMapper,
    AutomationMapper,
    AutomationOutboxDomainEvent,
    AutomationOutboxMapper,
    TriggerMapper,
)
from backend.automation.application.persistence.schema import (
    AUTOMATIONS_TABLE,
    AUTOMATION_EXECUTIONS_TABLE,
    AUTOMATION_OUTBOX_TABLE,
    TRIGGERS_TABLE,
    ColumnContract,
    TableContract,
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
    ScheduleExpression,
    Trigger,
    TriggerAdded,
    TriggerDisabled,
    TriggerEnabled,
    TriggerExpression,
    TriggerId,
    TriggerType,
    WorkflowExecutionId,
)

# ===================================================================
# Constants
# ===================================================================

_NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)
_NOW2 = datetime(2026, 6, 13, 13, 0, 0, tzinfo=timezone.utc)

# ===================================================================
# Stub mapper implementations
# ===================================================================


class StubAutomationMapper:
    def domain_to_dto(self, automation: Automation) -> AutomationStorageDTO:
        return AutomationStorageDTO(
            automation_id=str(automation.automation_id),
            name=str(automation.name) if automation.name else None,
            description=str(automation.description) if automation.description else None,
            status=automation.status.value,
            execution_mode=automation.execution_mode.value,
            created_at=automation.created_at,
            updated_at=automation.updated_at,
        )

    def dto_to_domain(self, dto: AutomationStorageDTO) -> Automation:
        automation = Automation(
            automation_id=AutomationId(value=UUID(dto.automation_id)),
            name=AutomationName(value=dto.name) if dto.name else None,
            description=AutomationDescription(value=dto.description) if dto.description else None,
            execution_mode=ExecutionMode(dto.execution_mode),
        )
        object.__setattr__(automation, "_status", AutomationStatus(dto.status))
        if dto.created_at:
            object.__setattr__(automation, "_created_at", dto.created_at)
        if dto.updated_at:
            object.__setattr__(automation, "_updated_at", dto.updated_at)
        return automation


class StubTriggerMapper:
    def domain_to_dto(self, trigger: Trigger) -> TriggerStorageDTO:
        return TriggerStorageDTO(
            trigger_id=str(trigger.trigger_id),
            trigger_type=trigger.trigger_type.value,
            expression=str(trigger.expression) if trigger.expression else None,
            enabled=trigger.enabled,
        )

    def dto_to_domain(self, dto: TriggerStorageDTO) -> Trigger:
        expression: TriggerExpression | None = None
        if dto.expression:
            expression = TriggerExpression(value=dto.expression)
        return Trigger(
            trigger_id=TriggerId(value=UUID(dto.trigger_id)),
            trigger_type=TriggerType(dto.trigger_type),
            expression=expression,
            enabled=dto.enabled,
        )


class StubExecutionMapper:
    def domain_to_dto(
        self, execution: AutomationExecution
    ) -> AutomationExecutionStorageDTO:
        return AutomationExecutionStorageDTO(
            execution_id=str(execution.execution_id),
            automation_id=str(execution.automation_id),
            status=execution.status.value,
            result=str(execution.result) if execution.result else None,
            failure_reason=str(execution.failure_reason) if execution.failure_reason else None,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
        )

    def dto_to_domain(
        self, dto: AutomationExecutionStorageDTO
    ) -> AutomationExecution:
        result: ExecutionResult | None = None
        if dto.result:
            result = ExecutionResult(value=dto.result)
        failure_reason: FailureReason | None = None
        if dto.failure_reason:
            failure_reason = FailureReason(value=dto.failure_reason)
        execution = AutomationExecution(
            execution_id=WorkflowExecutionId(value=UUID(dto.execution_id)),
            automation_id=AutomationId(value=UUID(dto.automation_id)) if dto.automation_id else None,
            status=ExecutionStatus(dto.status),
            result=result,
            failure_reason=failure_reason,
            started_at=dto.started_at,
            completed_at=dto.completed_at,
        )
        return execution


class StubOutboxMapper:
    def event_to_dto(
        self, event: AutomationOutboxDomainEvent
    ) -> AutomationOutboxStorageDTO:
        event_type = _event_type_map(type(event))
        return AutomationOutboxStorageDTO(
            event_id=str(event.event_id),
            event_type=event_type,
            aggregate_id=str(getattr(event, "automation_id", event.event_id)),
            occurred_at=event.occurred_at,
            payload=_payload_for_event(event),
        )

    def dto_to_event(
        self, dto: AutomationOutboxStorageDTO
    ) -> AutomationOutboxDomainEvent:
        raise NotImplementedError("Outbox dto_to_event requires event reconstruction logic")


def _event_type_map(event_cls: type) -> str:
    mapping = {
        AutomationCreated: "automation.created",
        AutomationActivated: "automation.activated",
        AutomationPaused: "automation.paused",
        AutomationDisabled: "automation.disabled",
        AutomationExecutionStarted: "automation.execution_started",
        AutomationExecutionCompleted: "automation.execution_completed",
        AutomationExecutionFailed: "automation.execution_failed",
        TriggerAdded: "automation.trigger_added",
        TriggerEnabled: "automation.trigger_enabled",
        TriggerDisabled: "automation.trigger_disabled",
        ActionAdded: "automation.action_added",
    }
    return mapping[event_cls]


def _payload_for_event(event: AutomationOutboxDomainEvent) -> str | None:
    if isinstance(event, AutomationCreated):
        return f'{{"name":"{event.name}","description":"{event.description}"}}'
    return None


# ===================================================================
# Section 1: DTO Tests
# ===================================================================


class TestAutomationStorageDTO:
    def test_construction(self) -> None:
        dto = AutomationStorageDTO(automation_id="auto-1")
        assert dto.automation_id == "auto-1"

    def test_all_fields(self) -> None:
        dto = AutomationStorageDTO(
            automation_id="a1",
            name="Report",
            description="Daily report",
            status="active",
            execution_mode="once",
            created_at=_NOW,
            updated_at=_NOW2,
        )
        assert dto.automation_id == "a1"
        assert dto.name == "Report"
        assert dto.description == "Daily report"
        assert dto.status == "active"
        assert dto.execution_mode == "once"
        assert dto.created_at == _NOW
        assert dto.updated_at == _NOW2

    def test_frozen(self) -> None:
        dto = AutomationStorageDTO(automation_id="a1")
        with pytest.raises(AttributeError):
            dto.automation_id = "a2"

    def test_default_status(self) -> None:
        dto = AutomationStorageDTO(automation_id="a1")
        assert dto.status == "draft"

    def test_default_execution_mode(self) -> None:
        dto = AutomationStorageDTO(automation_id="a1")
        assert dto.execution_mode == "once"

    def test_default_name_none(self) -> None:
        dto = AutomationStorageDTO(automation_id="a1")
        assert dto.name is None

    def test_default_description_none(self) -> None:
        dto = AutomationStorageDTO(automation_id="a1")
        assert dto.description is None

    def test_default_created_at_none(self) -> None:
        dto = AutomationStorageDTO(automation_id="a1")
        assert dto.created_at is None

    def test_default_updated_at_none(self) -> None:
        dto = AutomationStorageDTO(automation_id="a1")
        assert dto.updated_at is None

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(AutomationStorageDTO)
        assert len(fields) == 8

    def test_equality(self) -> None:
        dto1 = AutomationStorageDTO(automation_id="a1")
        dto2 = AutomationStorageDTO(automation_id="a1")
        assert dto1 == dto2

    def test_inequality(self) -> None:
        dto1 = AutomationStorageDTO(automation_id="a1")
        dto2 = AutomationStorageDTO(automation_id="a2")
        assert dto1 != dto2

    def test_repr(self) -> None:
        dto = AutomationStorageDTO(automation_id="a1")
        r = repr(dto)
        assert "AutomationStorageDTO" in r
        assert "a1" in r


class TestTriggerStorageDTO:
    def test_construction(self) -> None:
        dto = TriggerStorageDTO(trigger_id="trig-1")
        assert dto.trigger_id == "trig-1"

    def test_all_fields(self) -> None:
        dto = TriggerStorageDTO(
            trigger_id="t1",
            automation_id="a1",
            trigger_type="scheduled",
            expression="0 8 * * *",
            enabled=False,
        )
        assert dto.trigger_id == "t1"
        assert dto.automation_id == "a1"
        assert dto.trigger_type == "scheduled"
        assert dto.expression == "0 8 * * *"
        assert dto.enabled is False

    def test_frozen(self) -> None:
        dto = TriggerStorageDTO(trigger_id="t1")
        with pytest.raises(AttributeError):
            dto.trigger_id = "t2"

    def test_default_trigger_type(self) -> None:
        dto = TriggerStorageDTO(trigger_id="t1")
        assert dto.trigger_type == "manual"

    def test_default_enabled(self) -> None:
        dto = TriggerStorageDTO(trigger_id="t1")
        assert dto.enabled is True

    def test_default_automation_id_none(self) -> None:
        dto = TriggerStorageDTO(trigger_id="t1")
        assert dto.automation_id is None

    def test_default_expression_none(self) -> None:
        dto = TriggerStorageDTO(trigger_id="t1")
        assert dto.expression is None

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(TriggerStorageDTO)
        assert len(fields) == 5

    def test_equality(self) -> None:
        dto1 = TriggerStorageDTO(trigger_id="t1")
        dto2 = TriggerStorageDTO(trigger_id="t1")
        assert dto1 == dto2


class TestAutomationExecutionStorageDTO:
    def test_construction(self) -> None:
        dto = AutomationExecutionStorageDTO(execution_id="exec-1")
        assert dto.execution_id == "exec-1"

    def test_all_fields(self) -> None:
        dto = AutomationExecutionStorageDTO(
            execution_id="e1",
            automation_id="a1",
            status="running",
            result="Success",
            failure_reason=None,
            started_at=_NOW,
            completed_at=_NOW2,
        )
        assert dto.execution_id == "e1"
        assert dto.automation_id == "a1"
        assert dto.status == "running"
        assert dto.result == "Success"
        assert dto.failure_reason is None
        assert dto.started_at == _NOW
        assert dto.completed_at == _NOW2

    def test_frozen(self) -> None:
        dto = AutomationExecutionStorageDTO(execution_id="e1")
        with pytest.raises(AttributeError):
            dto.execution_id = "e2"

    def test_default_status(self) -> None:
        dto = AutomationExecutionStorageDTO(execution_id="e1")
        assert dto.status == "pending"

    def test_default_result_none(self) -> None:
        dto = AutomationExecutionStorageDTO(execution_id="e1")
        assert dto.result is None

    def test_default_failure_reason_none(self) -> None:
        dto = AutomationExecutionStorageDTO(execution_id="e1")
        assert dto.failure_reason is None

    def test_default_started_at_none(self) -> None:
        dto = AutomationExecutionStorageDTO(execution_id="e1")
        assert dto.started_at is None

    def test_default_completed_at_none(self) -> None:
        dto = AutomationExecutionStorageDTO(execution_id="e1")
        assert dto.completed_at is None

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(AutomationExecutionStorageDTO)
        assert len(fields) == 7

    def test_equality(self) -> None:
        dto1 = AutomationExecutionStorageDTO(execution_id="e1")
        dto2 = AutomationExecutionStorageDTO(execution_id="e1")
        assert dto1 == dto2


class TestAutomationOutboxStorageDTO:
    def test_construction(self) -> None:
        dto = AutomationOutboxStorageDTO(
            event_id="evt-1", event_type="automation.created",
            aggregate_id="agg-1", occurred_at=_NOW,
        )
        assert dto.event_id == "evt-1"
        assert dto.event_type == "automation.created"
        assert dto.aggregate_id == "agg-1"
        assert dto.occurred_at == _NOW

    def test_frozen(self) -> None:
        dto = AutomationOutboxStorageDTO(
            event_id="e1", event_type="t", aggregate_id="a", occurred_at=_NOW,
        )
        with pytest.raises(AttributeError):
            dto.event_id = "e2"

    def test_default_payload_none(self) -> None:
        dto = AutomationOutboxStorageDTO(
            event_id="e1", event_type="t", aggregate_id="a", occurred_at=_NOW,
        )
        assert dto.payload is None

    def test_default_published_false(self) -> None:
        dto = AutomationOutboxStorageDTO(
            event_id="e1", event_type="t", aggregate_id="a", occurred_at=_NOW,
        )
        assert dto.published is False

    def test_equality(self) -> None:
        dto1 = AutomationOutboxStorageDTO(
            event_id="e1", event_type="t", aggregate_id="a", occurred_at=_NOW,
        )
        dto2 = AutomationOutboxStorageDTO(
            event_id="e1", event_type="t", aggregate_id="a", occurred_at=_NOW,
        )
        assert dto1 == dto2

    def test_field_count(self) -> None:
        import dataclasses
        fields = dataclasses.fields(AutomationOutboxStorageDTO)
        assert len(fields) == 6

    def test_nullable_payload(self) -> None:
        dto = AutomationOutboxStorageDTO(
            event_id="e1", event_type="t", aggregate_id="a",
            occurred_at=_NOW, payload="{}",
        )
        assert dto.payload == "{}"

    def test_published_true(self) -> None:
        dto = AutomationOutboxStorageDTO(
            event_id="e1", event_type="t", aggregate_id="a",
            occurred_at=_NOW, published=True,
        )
        assert dto.published is True


# ===================================================================
# Section 2: Mapper Protocol Tests (Stub Roundtrips)
# ===================================================================


class TestAutomationMapper:
    def test_stub_conforms_to_protocol(self) -> None:
        mapper: AutomationMapper = StubAutomationMapper()
        assert mapper is not None

    def test_domain_to_dto(self) -> None:
        aid = AutomationId(value=UUID("00000000-0000-0000-0000-000000000001"))
        automation = Automation(
            automation_id=aid,
            name=AutomationName(value="Test"),
            description=AutomationDescription(value="Desc"),
            execution_mode=ExecutionMode.ONCE,
            created_at=_NOW,
        )
        mapper = StubAutomationMapper()
        dto = mapper.domain_to_dto(automation)
        assert dto.automation_id == str(aid)
        assert dto.name == "Test"
        assert dto.description == "Desc"
        assert dto.status == "draft"
        assert dto.execution_mode == "once"
        assert dto.created_at == _NOW

    def test_dto_to_domain(self) -> None:
        dto = AutomationStorageDTO(
            automation_id="00000000-0000-0000-0000-000000000001",
            name="Test",
            description="Desc",
            status="active",
            execution_mode="recurring",
            created_at=_NOW,
            updated_at=_NOW2,
        )
        mapper = StubAutomationMapper()
        domain = mapper.dto_to_domain(dto)
        assert domain.automation_id == AutomationId(value=UUID("00000000-0000-0000-0000-000000000001"))
        assert domain.name is not None
        assert domain.name.value == "Test"
        assert domain.description is not None
        assert domain.description.value == "Desc"
        assert domain.status == AutomationStatus.ACTIVE
        assert domain.execution_mode == ExecutionMode.RECURRING
        assert domain.created_at == _NOW
        assert domain.updated_at == _NOW2

    def test_roundtrip(self) -> None:
        aid = AutomationId(value=UUID("00000000-0000-0000-0000-000000000001"))
        original = Automation(
            automation_id=aid,
            name=AutomationName(value="Roundtrip"),
            description=AutomationDescription(value="Roundtrip test"),
            execution_mode=ExecutionMode.RECURRING,
            created_at=_NOW,
        )
        mapper = StubAutomationMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert restored.automation_id == original.automation_id
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.status == original.status
        assert restored.execution_mode == original.execution_mode
        assert restored.created_at == original.created_at

    def test_domain_to_dto_nullable_fields(self) -> None:
        automation = Automation()
        mapper = StubAutomationMapper()
        dto = mapper.domain_to_dto(automation)
        assert dto.name is None
        assert dto.description is None
        assert dto.updated_at is None

    def test_dto_to_domain_nullable_fields(self) -> None:
        dto = AutomationStorageDTO(
            automation_id="00000000-0000-0000-0000-000000000001",
        )
        mapper = StubAutomationMapper()
        domain = mapper.dto_to_domain(dto)
        assert domain.name is None
        assert domain.description is None
        assert domain.updated_at is None


class TestTriggerMapper:
    def test_stub_conforms_to_protocol(self) -> None:
        mapper: TriggerMapper = StubTriggerMapper()
        assert mapper is not None

    def test_domain_to_dto(self) -> None:
        tid = TriggerId(value=UUID("00000000-0000-0000-0000-000000000002"))
        trigger = Trigger(
            trigger_id=tid,
            trigger_type=TriggerType.SCHEDULED,
            expression=TriggerExpression(value="0 8 * * *"),
            enabled=True,
        )
        mapper = StubTriggerMapper()
        dto = mapper.domain_to_dto(trigger)
        assert dto.trigger_id == str(tid)
        assert dto.trigger_type == "scheduled"
        assert dto.expression == "0 8 * * *"
        assert dto.enabled is True

    def test_dto_to_domain(self) -> None:
        dto = TriggerStorageDTO(
            trigger_id="00000000-0000-0000-0000-000000000002",
            trigger_type="scheduled",
            expression="0 9 * * *",
            enabled=False,
        )
        mapper = StubTriggerMapper()
        domain = mapper.dto_to_domain(dto)
        assert domain.trigger_id == TriggerId(value=UUID("00000000-0000-0000-0000-000000000002"))
        assert domain.trigger_type == TriggerType.SCHEDULED
        assert domain.expression is not None
        assert domain.expression.value == "0 9 * * *"
        assert domain.enabled is False

    def test_roundtrip(self) -> None:
        tid = TriggerId(value=UUID("00000000-0000-0000-0000-000000000002"))
        original = Trigger(
            trigger_id=tid,
            trigger_type=TriggerType.EVENT,
            expression=TriggerExpression(value="file.uploaded"),
            enabled=True,
        )
        mapper = StubTriggerMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert restored.trigger_id == original.trigger_id
        assert restored.trigger_type == original.trigger_type
        assert restored.expression == original.expression
        assert restored.enabled == original.enabled

    def test_domain_to_dto_nullable_expression(self) -> None:
        trigger = Trigger(trigger_type=TriggerType.MANUAL)
        mapper = StubTriggerMapper()
        dto = mapper.domain_to_dto(trigger)
        assert dto.expression is None

    def test_dto_to_domain_nullable_expression(self) -> None:
        dto = TriggerStorageDTO(
            trigger_id="00000000-0000-0000-0000-000000000002",
        )
        mapper = StubTriggerMapper()
        domain = mapper.dto_to_domain(dto)
        assert domain.expression is None


class TestExecutionMapper:
    def test_stub_conforms_to_protocol(self) -> None:
        mapper: AutomationExecutionMapper = StubExecutionMapper()
        assert mapper is not None

    def test_domain_to_dto(self) -> None:
        eid = WorkflowExecutionId(value=UUID("00000000-0000-0000-0000-000000000003"))
        aid = AutomationId(value=UUID("00000000-0000-0000-0000-000000000001"))
        execution = AutomationExecution(
            execution_id=eid,
            automation_id=aid,
            status=ExecutionStatus.RUNNING,
            started_at=_NOW,
        )
        mapper = StubExecutionMapper()
        dto = mapper.domain_to_dto(execution)
        assert dto.execution_id == str(eid)
        assert dto.automation_id == str(aid)
        assert dto.status == "running"
        assert dto.started_at == _NOW
        assert dto.completed_at is None

    def test_dto_to_domain(self) -> None:
        dto = AutomationExecutionStorageDTO(
            execution_id="00000000-0000-0000-0000-000000000003",
            automation_id="00000000-0000-0000-0000-000000000001",
            status="completed",
            result="Success",
            started_at=_NOW,
            completed_at=_NOW2,
        )
        mapper = StubExecutionMapper()
        domain = mapper.dto_to_domain(dto)
        assert domain.execution_id == WorkflowExecutionId(value=UUID("00000000-0000-0000-0000-000000000003"))
        assert domain.automation_id == AutomationId(value=UUID("00000000-0000-0000-0000-000000000001"))
        assert domain.status == ExecutionStatus.COMPLETED
        assert domain.result is not None
        assert domain.result.value == "Success"
        assert domain.started_at == _NOW
        assert domain.completed_at == _NOW2

    def test_roundtrip(self) -> None:
        eid = WorkflowExecutionId(value=UUID("00000000-0000-0000-0000-000000000003"))
        aid = AutomationId(value=UUID("00000000-0000-0000-0000-000000000001"))
        original = AutomationExecution(
            execution_id=eid,
            automation_id=aid,
            status=ExecutionStatus.PENDING,
        )
        mapper = StubExecutionMapper()
        dto = mapper.domain_to_dto(original)
        restored = mapper.dto_to_domain(dto)
        assert restored.execution_id == original.execution_id
        assert restored.automation_id == original.automation_id
        assert restored.status == original.status
        assert restored.result is None

    def test_domain_to_dto_nullable_result(self) -> None:
        execution = AutomationExecution()
        mapper = StubExecutionMapper()
        dto = mapper.domain_to_dto(execution)
        assert dto.result is None
        assert dto.failure_reason is None
        assert dto.started_at is None
        assert dto.completed_at is None

    def test_dto_to_domain_with_failure_reason(self) -> None:
        dto = AutomationExecutionStorageDTO(
            execution_id="00000000-0000-0000-0000-000000000003",
            status="failed",
            failure_reason="Timeout",
        )
        mapper = StubExecutionMapper()
        domain = mapper.dto_to_domain(dto)
        assert domain.status == ExecutionStatus.FAILED
        assert domain.failure_reason is not None
        assert domain.failure_reason.value == "Timeout"


class TestOutboxMapper:
    def test_stub_conforms_to_protocol(self) -> None:
        mapper: AutomationOutboxMapper = StubOutboxMapper()
        assert mapper is not None

    def test_event_to_dto_created(self) -> None:
        event = AutomationCreated(
            automation_id=AutomationId(),
            name="Test",
            description="Desc",
            execution_mode="once",
            occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.created"
        assert dto.occurred_at == _NOW
        assert dto.payload is not None

    def test_event_to_dto_activated(self) -> None:
        event = AutomationActivated(
            automation_id=AutomationId(), occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.activated"

    def test_event_to_dto_paused(self) -> None:
        event = AutomationPaused(
            automation_id=AutomationId(), occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.paused"

    def test_event_to_dto_disabled(self) -> None:
        event = AutomationDisabled(
            automation_id=AutomationId(), occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.disabled"

    def test_event_to_dto_execution_started(self) -> None:
        event = AutomationExecutionStarted(
            automation_id=AutomationId(), execution_id=WorkflowExecutionId(),
            occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.execution_started"

    def test_event_to_dto_execution_completed(self) -> None:
        event = AutomationExecutionCompleted(
            automation_id=AutomationId(), execution_id=WorkflowExecutionId(),
            result="ok", occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.execution_completed"

    def test_event_to_dto_execution_failed(self) -> None:
        event = AutomationExecutionFailed(
            automation_id=AutomationId(), execution_id=WorkflowExecutionId(),
            failure_reason="err", occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.execution_failed"

    def test_event_to_dto_trigger_added(self) -> None:
        event = TriggerAdded(
            trigger_id=TriggerId(), automation_id=AutomationId(),
            trigger_type="manual", expression="", occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.trigger_added"

    def test_event_to_dto_trigger_enabled(self) -> None:
        event = TriggerEnabled(
            trigger_id=TriggerId(), automation_id=AutomationId(),
            occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.trigger_enabled"

    def test_event_to_dto_trigger_disabled(self) -> None:
        event = TriggerDisabled(
            trigger_id=TriggerId(), automation_id=AutomationId(),
            occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.trigger_disabled"

    def test_event_to_dto_action_added(self) -> None:
        event = ActionAdded(
            automation_id=AutomationId(), action_type="notification",
            occurred_at=_NOW,
        )
        mapper = StubOutboxMapper()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "automation.action_added"


# ===================================================================
# Section 3: Schema Contract Tests
# ===================================================================


class TestColumnContract:
    def test_creation(self) -> None:
        col = ColumnContract(name="id", py_type=str, nullable=False)
        assert col.name == "id"
        assert col.py_type is str
        assert col.nullable is False

    def test_frozen(self) -> None:
        col = ColumnContract(name="id", py_type=str, nullable=False)
        with pytest.raises(AttributeError):
            col.name = "changed"


class TestTableContract:
    def test_creation(self) -> None:
        col = ColumnContract(name="id", py_type=str, nullable=False)
        table = TableContract(
            name="test", schema="auto", columns=(col,),
            primary_key="id", indexes=("ix_id",),
        )
        assert table.name == "test"
        assert table.schema == "auto"
        assert len(table.columns) == 1
        assert table.primary_key == "id"
        assert table.indexes == ("ix_id",)

    def test_frozen(self) -> None:
        col = ColumnContract(name="id", py_type=str, nullable=False)
        table = TableContract(
            name="test", schema="auto", columns=(col,), primary_key="id",
        )
        with pytest.raises(AttributeError):
            table.name = "changed"


class TestAutomationsTableSchema:
    def test_table_name(self) -> None:
        assert AUTOMATIONS_TABLE.name == "automations"

    def test_schema_name(self) -> None:
        assert AUTOMATIONS_TABLE.schema == "automation"

    def test_primary_key(self) -> None:
        assert AUTOMATIONS_TABLE.primary_key == "automation_id"

    def test_column_count(self) -> None:
        assert len(AUTOMATIONS_TABLE.columns) == 8

    def test_automation_id_column(self) -> None:
        col = AUTOMATIONS_TABLE.columns[0]
        assert col.name == "automation_id"
        assert col.py_type is str
        assert col.nullable is False

    def test_name_column(self) -> None:
        col = AUTOMATIONS_TABLE.columns[1]
        assert col.name == "name"
        assert col.py_type is str
        assert col.nullable is True

    def test_description_column(self) -> None:
        col = AUTOMATIONS_TABLE.columns[2]
        assert col.name == "description"
        assert col.py_type is str
        assert col.nullable is True

    def test_status_column(self) -> None:
        col = AUTOMATIONS_TABLE.columns[3]
        assert col.name == "status"
        assert col.py_type is str
        assert col.nullable is False
        assert col.max_length == 16
        assert col.enum_values == (
            "draft", "active", "paused", "running",
            "completed", "failed", "disabled",
        )

    def test_execution_mode_column(self) -> None:
        col = AUTOMATIONS_TABLE.columns[4]
        assert col.name == "execution_mode"
        assert col.py_type is str
        assert col.nullable is False
        assert col.max_length == 16
        assert col.enum_values == ("once", "recurring", "continuous")

    def test_actions_column(self) -> None:
        col = AUTOMATIONS_TABLE.columns[5]
        assert col.name == "actions"
        assert col.py_type is str
        assert col.nullable is True

    def test_created_at_column(self) -> None:
        col = AUTOMATIONS_TABLE.columns[6]
        assert col.name == "created_at"
        assert col.py_type is datetime
        assert col.nullable is False

    def test_updated_at_column(self) -> None:
        col = AUTOMATIONS_TABLE.columns[7]
        assert col.name == "updated_at"
        assert col.py_type is datetime
        assert col.nullable is True

    def test_indexes(self) -> None:
        assert "ix_automations_status" in AUTOMATIONS_TABLE.indexes
        assert "ix_automations_execution_mode" in AUTOMATIONS_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(AUTOMATIONS_TABLE.indexes) == 2


class TestTriggersTableSchema:
    def test_table_name(self) -> None:
        assert TRIGGERS_TABLE.name == "triggers"

    def test_schema_name(self) -> None:
        assert TRIGGERS_TABLE.schema == "automation"

    def test_primary_key(self) -> None:
        assert TRIGGERS_TABLE.primary_key == "trigger_id"

    def test_column_count(self) -> None:
        assert len(TRIGGERS_TABLE.columns) == 5

    def test_trigger_id_column(self) -> None:
        col = TRIGGERS_TABLE.columns[0]
        assert col.name == "trigger_id"
        assert col.py_type is str
        assert col.nullable is False

    def test_automation_id_column(self) -> None:
        col = TRIGGERS_TABLE.columns[1]
        assert col.name == "automation_id"
        assert col.py_type is str
        assert col.nullable is True

    def test_trigger_type_column(self) -> None:
        col = TRIGGERS_TABLE.columns[2]
        assert col.name == "trigger_type"
        assert col.py_type is str
        assert col.nullable is False
        assert col.max_length == 16
        assert col.enum_values == ("manual", "scheduled", "event", "webhook")

    def test_expression_column(self) -> None:
        col = TRIGGERS_TABLE.columns[3]
        assert col.name == "expression"
        assert col.py_type is str
        assert col.nullable is True

    def test_enabled_column(self) -> None:
        col = TRIGGERS_TABLE.columns[4]
        assert col.name == "enabled"
        assert col.py_type is bool
        assert col.nullable is False

    def test_indexes(self) -> None:
        assert "ix_triggers_automation_id" in TRIGGERS_TABLE.indexes
        assert "ix_triggers_trigger_type" in TRIGGERS_TABLE.indexes
        assert "ix_triggers_enabled" in TRIGGERS_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(TRIGGERS_TABLE.indexes) == 3


class TestAutomationExecutionsTableSchema:
    def test_table_name(self) -> None:
        assert AUTOMATION_EXECUTIONS_TABLE.name == "executions"

    def test_schema_name(self) -> None:
        assert AUTOMATION_EXECUTIONS_TABLE.schema == "automation"

    def test_primary_key(self) -> None:
        assert AUTOMATION_EXECUTIONS_TABLE.primary_key == "execution_id"

    def test_column_count(self) -> None:
        assert len(AUTOMATION_EXECUTIONS_TABLE.columns) == 7

    def test_execution_id_column(self) -> None:
        col = AUTOMATION_EXECUTIONS_TABLE.columns[0]
        assert col.name == "execution_id"
        assert col.py_type is str
        assert col.nullable is False

    def test_automation_id_column(self) -> None:
        col = AUTOMATION_EXECUTIONS_TABLE.columns[1]
        assert col.name == "automation_id"
        assert col.py_type is str
        assert col.nullable is True

    def test_status_column(self) -> None:
        col = AUTOMATION_EXECUTIONS_TABLE.columns[2]
        assert col.name == "status"
        assert col.py_type is str
        assert col.nullable is False
        assert col.max_length == 16
        assert col.enum_values == (
            "pending", "running", "completed", "failed", "cancelled",
        )

    def test_result_column(self) -> None:
        col = AUTOMATION_EXECUTIONS_TABLE.columns[3]
        assert col.name == "result"
        assert col.py_type is str
        assert col.nullable is True

    def test_failure_reason_column(self) -> None:
        col = AUTOMATION_EXECUTIONS_TABLE.columns[4]
        assert col.name == "failure_reason"
        assert col.py_type is str
        assert col.nullable is True

    def test_started_at_column(self) -> None:
        col = AUTOMATION_EXECUTIONS_TABLE.columns[5]
        assert col.name == "started_at"
        assert col.py_type is datetime
        assert col.nullable is True

    def test_completed_at_column(self) -> None:
        col = AUTOMATION_EXECUTIONS_TABLE.columns[6]
        assert col.name == "completed_at"
        assert col.py_type is datetime
        assert col.nullable is True

    def test_indexes(self) -> None:
        assert "ix_executions_automation_id" in AUTOMATION_EXECUTIONS_TABLE.indexes
        assert "ix_executions_status" in AUTOMATION_EXECUTIONS_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(AUTOMATION_EXECUTIONS_TABLE.indexes) == 2


class TestAutomationOutboxTableSchema:
    def test_table_name(self) -> None:
        assert AUTOMATION_OUTBOX_TABLE.name == "outbox"

    def test_schema_name(self) -> None:
        assert AUTOMATION_OUTBOX_TABLE.schema == "automation"

    def test_primary_key(self) -> None:
        assert AUTOMATION_OUTBOX_TABLE.primary_key == "event_id"

    def test_column_count(self) -> None:
        assert len(AUTOMATION_OUTBOX_TABLE.columns) == 6

    def test_event_id_column(self) -> None:
        col = AUTOMATION_OUTBOX_TABLE.columns[0]
        assert col.name == "event_id"
        assert col.py_type is str
        assert col.nullable is False

    def test_event_type_column(self) -> None:
        col = AUTOMATION_OUTBOX_TABLE.columns[1]
        assert col.name == "event_type"
        assert col.py_type is str
        assert col.nullable is False
        assert col.max_length == 32
        assert col.enum_values == (
            "automation.created",
            "automation.activated",
            "automation.paused",
            "automation.disabled",
            "automation.execution_started",
            "automation.execution_completed",
            "automation.execution_failed",
            "automation.trigger_added",
            "automation.trigger_enabled",
            "automation.trigger_disabled",
            "automation.action_added",
        )

    def test_aggregate_id_column(self) -> None:
        col = AUTOMATION_OUTBOX_TABLE.columns[2]
        assert col.name == "aggregate_id"
        assert col.py_type is str
        assert col.nullable is False

    def test_occurred_at_column(self) -> None:
        col = AUTOMATION_OUTBOX_TABLE.columns[3]
        assert col.name == "occurred_at"
        assert col.py_type is datetime
        assert col.nullable is False

    def test_payload_column(self) -> None:
        col = AUTOMATION_OUTBOX_TABLE.columns[4]
        assert col.name == "payload"
        assert col.py_type is str
        assert col.nullable is True

    def test_published_column(self) -> None:
        col = AUTOMATION_OUTBOX_TABLE.columns[5]
        assert col.name == "published"
        assert col.py_type is bool
        assert col.nullable is False

    def test_indexes(self) -> None:
        assert "ix_automation_outbox_unpublished" in AUTOMATION_OUTBOX_TABLE.indexes
        assert "ix_automation_outbox_aggregate" in AUTOMATION_OUTBOX_TABLE.indexes

    def test_index_count(self) -> None:
        assert len(AUTOMATION_OUTBOX_TABLE.indexes) == 2


# ===================================================================
# Section 4: Alignment Tests
# ===================================================================


class TestDTOAlignmentAutomation:
    def test_dto_field_count_matches_schema_column_count(self) -> None:
        import dataclasses
        dto_fields = dataclasses.fields(AutomationStorageDTO)
        schema_cols = AUTOMATIONS_TABLE.columns
        assert len(dto_fields) == len(schema_cols)

    def test_dto_field_names_match_schema_column_names(self) -> None:
        import dataclasses
        dto_names = {f.name for f in dataclasses.fields(AutomationStorageDTO)}
        schema_names = {c.name for c in AUTOMATIONS_TABLE.columns}
        assert dto_names == schema_names

    def test_domain_enum_values_match_schema_status_enum(self) -> None:
        schema_values = set(AUTOMATIONS_TABLE.columns[3].enum_values or ())
        domain_values = {s.value for s in AutomationStatus}
        assert schema_values == domain_values

    def test_domain_enum_values_match_schema_execution_mode_enum(self) -> None:
        schema_values = set(AUTOMATIONS_TABLE.columns[4].enum_values or ())
        domain_values = {m.value for m in ExecutionMode}
        assert schema_values == domain_values

    def test_domain_nullable_fields_match_dto_nullable(self) -> None:
        assert AutomationStorageDTO.__dataclass_fields__["name"].default is None
        assert AutomationStorageDTO.__dataclass_fields__["description"].default is None
        assert AutomationStorageDTO.__dataclass_fields__["updated_at"].default is None


class TestDTOAlignmentTriggers:
    def test_dto_field_count_matches_schema_column_count(self) -> None:
        import dataclasses
        dto_fields = dataclasses.fields(TriggerStorageDTO)
        schema_cols = TRIGGERS_TABLE.columns
        assert len(dto_fields) == len(schema_cols)

    def test_dto_field_names_match_schema_column_names(self) -> None:
        import dataclasses
        dto_names = {f.name for f in dataclasses.fields(TriggerStorageDTO)}
        schema_names = {c.name for c in TRIGGERS_TABLE.columns}
        assert dto_names == schema_names

    def test_domain_enum_values_match_schema_trigger_type_enum(self) -> None:
        schema_values = set(TRIGGERS_TABLE.columns[2].enum_values or ())
        domain_values = {t.value for t in TriggerType}
        assert schema_values == domain_values

    def test_expression_nullable_parity(self) -> None:
        schema_col = TRIGGERS_TABLE.columns[3]
        assert schema_col.nullable is True
        assert TriggerStorageDTO.__dataclass_fields__["expression"].default is None


class TestDTOAlignmentExecutions:
    def test_dto_field_count_matches_schema_column_count(self) -> None:
        import dataclasses
        dto_fields = dataclasses.fields(AutomationExecutionStorageDTO)
        schema_cols = AUTOMATION_EXECUTIONS_TABLE.columns
        assert len(dto_fields) == len(schema_cols)

    def test_dto_field_names_match_schema_column_names(self) -> None:
        import dataclasses
        dto_names = {f.name for f in dataclasses.fields(AutomationExecutionStorageDTO)}
        schema_names = {c.name for c in AUTOMATION_EXECUTIONS_TABLE.columns}
        assert dto_names == schema_names

    def test_domain_enum_values_match_schema_status_enum(self) -> None:
        schema_values = set(AUTOMATION_EXECUTIONS_TABLE.columns[2].enum_values or ())
        domain_values = {s.value for s in ExecutionStatus}
        assert schema_values == domain_values

    def test_result_nullable_parity(self) -> None:
        schema_col = AUTOMATION_EXECUTIONS_TABLE.columns[3]
        assert schema_col.nullable is True
        assert AutomationExecutionStorageDTO.__dataclass_fields__["result"].default is None

    def test_failure_reason_nullable_parity(self) -> None:
        schema_col = AUTOMATION_EXECUTIONS_TABLE.columns[4]
        assert schema_col.nullable is True
        assert AutomationExecutionStorageDTO.__dataclass_fields__["failure_reason"].default is None

    def test_started_at_nullable_parity(self) -> None:
        schema_col = AUTOMATION_EXECUTIONS_TABLE.columns[5]
        assert schema_col.nullable is True
        assert AutomationExecutionStorageDTO.__dataclass_fields__["started_at"].default is None

    def test_completed_at_nullable_parity(self) -> None:
        schema_col = AUTOMATION_EXECUTIONS_TABLE.columns[6]
        assert schema_col.nullable is True
        assert AutomationExecutionStorageDTO.__dataclass_fields__["completed_at"].default is None


class TestDTOAlignmentOutbox:
    def test_dto_field_count_matches_schema_column_count(self) -> None:
        import dataclasses
        dto_fields = dataclasses.fields(AutomationOutboxStorageDTO)
        schema_cols = AUTOMATION_OUTBOX_TABLE.columns
        assert len(dto_fields) == len(schema_cols)

    def test_dto_field_names_match_schema_column_names(self) -> None:
        import dataclasses
        dto_names = {f.name for f in dataclasses.fields(AutomationOutboxStorageDTO)}
        schema_names = {c.name for c in AUTOMATION_OUTBOX_TABLE.columns}
        assert dto_names == schema_names

    def test_payload_nullable_parity(self) -> None:
        schema_col = AUTOMATION_OUTBOX_TABLE.columns[4]
        assert schema_col.nullable is True
        assert AutomationOutboxStorageDTO.__dataclass_fields__["payload"].default is None


# ===================================================================
# Section 5: Outbox Event Union Conformance
# ===================================================================


class TestAutomationOutboxEventUnion:
    def test_automation_created_is_event(self) -> None:
        event: AutomationOutboxDomainEvent = AutomationCreated(
            automation_id=AutomationId(),
            name="n", description="d", execution_mode="once",
            occurred_at=_NOW,
        )
        assert event is not None

    def test_automation_activated_is_event(self) -> None:
        event: AutomationOutboxDomainEvent = AutomationActivated(
            automation_id=AutomationId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_automation_paused_is_event(self) -> None:
        event: AutomationOutboxDomainEvent = AutomationPaused(
            automation_id=AutomationId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_automation_disabled_is_event(self) -> None:
        event: AutomationOutboxDomainEvent = AutomationDisabled(
            automation_id=AutomationId(), occurred_at=_NOW,
        )
        assert event is not None

    def test_execution_started_is_event(self) -> None:
        event: AutomationOutboxDomainEvent = AutomationExecutionStarted(
            automation_id=AutomationId(),
            execution_id=WorkflowExecutionId(),
            occurred_at=_NOW,
        )
        assert event is not None

    def test_execution_completed_is_event(self) -> None:
        event: AutomationOutboxDomainEvent = AutomationExecutionCompleted(
            automation_id=AutomationId(),
            execution_id=WorkflowExecutionId(),
            result="ok", occurred_at=_NOW,
        )
        assert event is not None

    def test_execution_failed_is_event(self) -> None:
        event: AutomationOutboxDomainEvent = AutomationExecutionFailed(
            automation_id=AutomationId(),
            execution_id=WorkflowExecutionId(),
            failure_reason="err", occurred_at=_NOW,
        )
        assert event is not None

    def test_trigger_added_is_event(self) -> None:
        event: AutomationOutboxDomainEvent = TriggerAdded(
            trigger_id=TriggerId(), automation_id=AutomationId(),
            trigger_type="manual", expression="", occurred_at=_NOW,
        )
        assert event is not None

    def test_trigger_enabled_is_event(self) -> None:
        event: AutomationOutboxDomainEvent = TriggerEnabled(
            trigger_id=TriggerId(), automation_id=AutomationId(),
            occurred_at=_NOW,
        )
        assert event is not None

    def test_trigger_disabled_is_event(self) -> None:
        event: AutomationOutboxDomainEvent = TriggerDisabled(
            trigger_id=TriggerId(), automation_id=AutomationId(),
            occurred_at=_NOW,
        )
        assert event is not None

    def test_action_added_is_event(self) -> None:
        event: AutomationOutboxDomainEvent = ActionAdded(
            automation_id=AutomationId(), action_type="notification",
            occurred_at=_NOW,
        )
        assert event is not None

    def test_all_events_count(self) -> None:
        event_types = AutomationOutboxDomainEvent.__args__
        assert len(event_types) == 11

    def test_schema_enum_count_matches(self) -> None:
        schema_values = AUTOMATION_OUTBOX_TABLE.columns[1].enum_values
        assert schema_values is not None
        assert len(schema_values) == 11

    def test_schema_enum_values_match_event_types(self) -> None:
        schema_values = set(AUTOMATION_OUTBOX_TABLE.columns[1].enum_values or ())
        expected = {
            "automation.created",
            "automation.activated",
            "automation.paused",
            "automation.disabled",
            "automation.execution_started",
            "automation.execution_completed",
            "automation.execution_failed",
            "automation.trigger_added",
            "automation.trigger_enabled",
            "automation.trigger_disabled",
            "automation.action_added",
        }
        assert schema_values == expected


# ===================================================================
# Section 6: Mapper Protocol Method Signature Verification
# ===================================================================


class TestAutomationMapperProtocol:
    def test_domain_to_dto_signature(self) -> None:
        method = AutomationMapper.domain_to_dto
        assert callable(method)

    def test_dto_to_domain_signature(self) -> None:
        method = AutomationMapper.dto_to_domain
        assert callable(method)

    def test_protocol_has_required_methods(self) -> None:
        methods = {"domain_to_dto", "dto_to_domain"}
        protocol_methods = {
            m for m in dir(AutomationMapper) if not m.startswith("_")
        }
        assert methods.issubset(protocol_methods)


class TestTriggerMapperProtocol:
    def test_protocol_has_required_methods(self) -> None:
        methods = {"domain_to_dto", "dto_to_domain"}
        protocol_methods = {
            m for m in dir(TriggerMapper) if not m.startswith("_")
        }
        assert methods.issubset(protocol_methods)


class TestExecutionMapperProtocol:
    def test_protocol_has_required_methods(self) -> None:
        methods = {"domain_to_dto", "dto_to_domain"}
        protocol_methods = {
            m for m in dir(AutomationExecutionMapper) if not m.startswith("_")
        }
        assert methods.issubset(protocol_methods)


class TestOutboxMapperProtocol:
    def test_protocol_has_required_methods(self) -> None:
        methods = {"event_to_dto", "dto_to_event"}
        protocol_methods = {
            m for m in dir(AutomationOutboxMapper) if not m.startswith("_")
        }
        assert methods.issubset(protocol_methods)


class TestMapperInstantiation:
    def test_automation_mapper_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            AutomationMapper()

    def test_trigger_mapper_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            TriggerMapper()

    def test_execution_mapper_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            AutomationExecutionMapper()

    def test_outbox_mapper_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            AutomationOutboxMapper()


# ===================================================================
# Section 7: Module Importability
# ===================================================================


class TestModuleImportability:
    def test_persistence_modules_importable(self) -> None:
        from backend.automation.application.persistence import (
            AutomationExecutionStorageDTO,
            AutomationOutboxStorageDTO,
            AutomationStorageDTO,
            TriggerStorageDTO,
        )
        assert AutomationStorageDTO is not None
        assert TriggerStorageDTO is not None
        assert AutomationExecutionStorageDTO is not None
        assert AutomationOutboxStorageDTO is not None

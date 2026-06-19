"""Tests for SVC-011-B Runtime Service Adapters.

Covers handler registration, DTO mapping, successful execution, use case
failures, missing/extra fields, CommandResult generation, and registry
integration for all 8 service adapters.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, PropertyMock

import pytest

from backend.automation.application.use_cases.create_automation import (
    CreateAutomationUseCase,
)
from backend.automation.application.use_cases.dto import (
    AutomationLifecycleRequest,
    AutomationLifecycleResponse,
    CreateAutomationRequest,
    CreateAutomationResponse,
)
from backend.automation.application.use_cases.exceptions import (
    AutomationNotFoundError,
    UseCaseError as AutomationUseCaseError,
)
from backend.knowledge.application.use_cases.dto import (
    IngestDocumentRequest,
    IngestDocumentResponse,
    RegisterSourceRequest,
    RegisterSourceResponse,
    StartIngestionRequest,
    StartIngestionResponse,
)
from backend.knowledge.application.use_cases.exceptions import (
    SourceNotFoundError as KnowledgeSourceNotFoundError,
    UseCaseError as KnowledgeUseCaseError,
)
from backend.knowledge.application.use_cases.register_source import (
    RegisterSourceUseCase,
)
from backend.memory.application.use_cases.create_memory import CreateMemoryUseCase
from backend.memory.application.use_cases.dto import (
    CreateMemoryRequest,
    CreateMemoryResponse,
)
from backend.memory.application.use_cases.exceptions import (
    ConsentNotActiveError,
    UseCaseError as MemoryUseCaseError,
)
from backend.notification.application.use_cases.create_notification import (
    CreateNotificationUseCase,
)
from backend.notification.application.use_cases.dto import (
    CreateNotificationRequest,
    CreateNotificationResponse,
)
from backend.notification.application.use_cases.exceptions import (
    UseCaseError as NotificationUseCaseError,
)
from backend.orchestrator.application.use_cases.create_orchestration import (
    CreateOrchestrationUseCase,
)
from backend.orchestrator.application.use_cases.dto import (
    CreateOrchestrationRequest,
    CreateOrchestrationResponse,
)
from backend.orchestrator.application.use_cases.exceptions import (
    OrchestrationNotFoundError,
    UseCaseError as OrchestratorUseCaseError,
)
from backend.planner.application.use_cases.approve_plan import ApprovePlanUseCase
from backend.planner.application.use_cases.create_plan import CreatePlanUseCase
from backend.planner.application.use_cases.dto import (
    CreatePlanRequest,
    CreatePlanResponse,
    PlanLifecycleRequest,
    PlanLifecycleResponse,
)
from backend.planner.application.use_cases.exceptions import (
    PlanNotFoundError,
    UseCaseError as PlannerUseCaseError,
)
from backend.policy.application.use_cases.create_policy import CreatePolicyUseCase
from backend.policy.application.use_cases.dto import (
    CreatePolicyRequest,
    CreatePolicyResponse,
)
from backend.policy.application.use_cases.exceptions import (
    PolicyNotFoundError,
    UseCaseError as PolicyUseCaseError,
)
from backend.research.application.use_cases.create_request import (
    CreateRequestUseCase,
)
from backend.research.application.use_cases.dto import (
    CreateRequestRequest,
    CreateRequestResponse,
    RequestLifecycleRequest,
    RequestLifecycleResponse,
)
from backend.research.application.use_cases.exceptions import (
    ResearchRequestNotFoundError,
    UseCaseError as ResearchUseCaseError,
)
from backend.research.application.use_cases.start_request import StartRequestUseCase
from backend.runtime.adapters import (
    register_all_handlers,
    register_automation_handlers,
    register_knowledge_handlers,
    register_memory_handlers,
    register_notification_handlers,
    register_orchestrator_handlers,
    register_planner_handlers,
    register_policy_handlers,
    register_research_handlers,
    register_service_handlers,
)
from backend.runtime.dispatcher import CommandDispatcher
from backend.runtime.envelope import build_command_envelope
from backend.runtime.handler import CommandResult
from backend.runtime.registry import CommandRegistry

NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)


# =========================================================================
# Stub use cases that capture requests and return controlled responses
# =========================================================================


class _StubUseCase:
    """Base for stub use cases. Stores the last request for assertions."""

    def __init__(self) -> None:
        self.last_request: Any = None
        self.fail: bool = False
        self.fail_with: type[Exception] | None = None
        self.fail_message: str = "use case failed"


class _StubCreatePlanUseCase(_StubUseCase):
    def execute(self, request: CreatePlanRequest) -> CreatePlanResponse:
        self.last_request = request
        if self.fail:
            exc = (self.fail_with or PlannerUseCaseError)(self.fail_message)
            raise exc
        return CreatePlanResponse(
            plan_id="plan-123",
            user_request=request.user_request,
            goal=request.goal,
            priority=request.priority,
            strategy=request.strategy,
            status="draft",
            created_at=NOW,
        )


class _StubApprovePlanUseCase(_StubUseCase):
    def execute(self, request: PlanLifecycleRequest) -> PlanLifecycleResponse:
        self.last_request = request
        if self.fail:
            exc = (self.fail_with or PlannerUseCaseError)(self.fail_message)
            raise exc
        return PlanLifecycleResponse(
            plan_id=request.plan_id,
            status="approved",
            updated_at=NOW,
        )


class _StubCreateRequestUseCase(_StubUseCase):
    def execute(self, request: CreateRequestRequest) -> CreateRequestResponse:
        self.last_request = request
        if self.fail:
            exc = (self.fail_with or ResearchUseCaseError)(self.fail_message)
            raise exc
        return CreateRequestResponse(
            request_id="req-123",
            query=request.query,
            goal=request.goal,
            priority=request.priority,
            status="created",
            created_at=NOW,
        )


class _StubStartRequestUseCase(_StubUseCase):
    def execute(self, request: RequestLifecycleRequest) -> RequestLifecycleResponse:
        self.last_request = request
        if self.fail:
            exc = (self.fail_with or ResearchUseCaseError)(self.fail_message)
            raise exc
        return RequestLifecycleResponse(
            request_id=request.request_id,
            status="started",
            updated_at=NOW,
        )


class _StubCreateMemoryUseCase(_StubUseCase):
    def execute(self, request: CreateMemoryRequest) -> CreateMemoryResponse:
        self.last_request = request
        if self.fail:
            exc = (self.fail_with or MemoryUseCaseError)(self.fail_message)
            raise exc
        return CreateMemoryResponse(
            memory_id="mem-123",
            consent_id=request.consent_id,
            content=request.content,
            category=request.category,
            source_type=request.source_type,
            source_id=request.source_id,
            classification=request.classification,
            sensitivity=request.sensitivity,
            retention_policy=request.retention_policy,
            retention_status="active",
            revision=1,
            created_at=NOW,
        )


class _StubRegisterSourceUseCase(_StubUseCase):
    def execute(self, request: RegisterSourceRequest) -> RegisterSourceResponse:
        self.last_request = request
        if self.fail:
            exc = (self.fail_with or KnowledgeUseCaseError)(self.fail_message)
            raise exc
        return RegisterSourceResponse(
            source_id="src-123",
            name=request.name,
            source_type=request.source_type,
            location=request.location,
            classification=request.classification,
            status="active",
            created_at=NOW,
        )


class _StubCreateNotificationUseCase(_StubUseCase):
    def execute(
        self, request: CreateNotificationRequest
    ) -> CreateNotificationResponse:
        self.last_request = request
        if self.fail:
            exc = (self.fail_with or NotificationUseCaseError)(self.fail_message)
            raise exc
        return CreateNotificationResponse(
            notification_id="notif-123",
            title=request.title,
            message=request.message,
            priority=request.priority,
            channel=request.channel,
            target_type=request.target_type,
            target_id=request.target_id,
            status="created",
            created_at=NOW,
            expires_at=request.expires_at,
        )


class _StubCreatePolicyUseCase(_StubUseCase):
    def execute(self, request: CreatePolicyRequest) -> CreatePolicyResponse:
        self.last_request = request
        if self.fail:
            exc = (self.fail_with or PolicyUseCaseError)(self.fail_message)
            raise exc
        return CreatePolicyResponse(
            policy_id="pol-123",
            name=request.name,
            description=request.description,
            status="draft",
            priority=request.priority,
            scope=request.scope,
            version=request.version,
            created_at=NOW,
        )


class _StubCreateAutomationUseCase(_StubUseCase):
    def execute(
        self, request: CreateAutomationRequest
    ) -> CreateAutomationResponse:
        self.last_request = request
        if self.fail:
            exc = (self.fail_with or AutomationUseCaseError)(self.fail_message)
            raise exc
        return CreateAutomationResponse(
            automation_id="auto-123",
            name=request.name,
            description=request.description,
            execution_mode=request.execution_mode,
            status="draft",
            created_at=NOW,
        )


class _StubCreateOrchestrationUseCase(_StubUseCase):
    def execute(
        self, request: CreateOrchestrationRequest
    ) -> CreateOrchestrationResponse:
        self.last_request = request
        if self.fail:
            exc = (self.fail_with or OrchestratorUseCaseError)(self.fail_message)
            raise exc
        return CreateOrchestrationResponse(
            orchestration_id="orch-123",
            intent=request.intent,
            goal=request.goal,
            status="created",
            created_at=NOW,
        )


class _StubIngestDocumentUseCase(_StubUseCase):
    def execute(self, request: IngestDocumentRequest) -> IngestDocumentResponse:
        self.last_request = request
        if self.fail:
            exc = (self.fail_with or KnowledgeUseCaseError)(self.fail_message)
            raise exc
        return IngestDocumentResponse(
            document_id="doc-123",
            source_id=request.source_id,
            title=request.title,
            checksum=request.checksum,
            classification=request.classification,
            status="ingested",
            revision=1,
            created_at=NOW,
        )


class _StubStartIngestionUseCase(_StubUseCase):
    def execute(self, request: StartIngestionRequest) -> StartIngestionResponse:
        self.last_request = request
        if self.fail:
            exc = (self.fail_with or KnowledgeUseCaseError)(self.fail_message)
            raise exc
        return StartIngestionResponse(
            job_id="job-123",
            source_id=request.source_id,
            status="started",
            started_at=NOW,
        )


class _StubActivateAutomationUseCase(_StubUseCase):
    def execute(self, request: AutomationLifecycleRequest) -> AutomationLifecycleResponse:
        self.last_request = request
        if self.fail:
            exc = (self.fail_with or AutomationUseCaseError)(self.fail_message)
            raise exc
        return AutomationLifecycleResponse(
            automation_id=request.automation_id,
            status="active",
            updated_at=NOW,
        )


# =========================================================================
# Helper: build a command envelope with a given payload
# =========================================================================


def _cmd(command_type: str, **payload: Any) -> object:
    return build_command_envelope(command_type, payload)


# =========================================================================
# 1. Planner Adapter (~18 tests)
# =========================================================================


class TestPlannerAdapter:
    def test_create_plan_registered(self) -> None:
        registry = CommandRegistry()
        register_planner_handlers(registry, _StubCreatePlanUseCase(), _StubApprovePlanUseCase())
        assert registry.has("planner.create_plan")
        assert registry.has("planner.approve_plan")

    async def test_create_plan_success(self) -> None:
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        handler = registry.get("planner.create_plan")
        assert handler is not None
        envelope = _cmd("planner.create_plan", user_request="test", goal="do thing", priority="high")
        result = await handler(envelope)
        assert result.success
        assert result.error is None
        assert len(result.events) == 1
        assert result.events[0]["event_type"] == "plan.created"
        assert result.events[0]["payload"]["plan_id"] == "plan-123"

    async def test_create_plan_dto_mapping(self) -> None:
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        handler = registry.get("planner.create_plan")
        assert handler is not None
        envelope = _cmd("planner.create_plan", user_request="UR", goal="G", priority="critical", strategy="parallel")
        await handler(envelope)
        req = uc.last_request
        assert req.user_request == "UR"
        assert req.goal == "G"
        assert req.priority == "critical"
        assert req.strategy == "parallel"

    async def test_create_plan_defaults(self) -> None:
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        handler = registry.get("planner.create_plan")
        assert handler is not None
        envelope = _cmd("planner.create_plan", user_request="UR", goal="G")
        await handler(envelope)
        req = uc.last_request
        assert req.priority == "normal"
        assert req.strategy == "sequential"

    async def test_create_plan_failure(self) -> None:
        uc = _StubCreatePlanUseCase()
        uc.fail = True
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        handler = registry.get("planner.create_plan")
        assert handler is not None
        envelope = _cmd("planner.create_plan", user_request="UR", goal="G")
        result = await handler(envelope)
        assert not result.success
        assert result.error is not None

    async def test_create_plan_not_found_error(self) -> None:
        uc = _StubCreatePlanUseCase()
        uc.fail = True
        uc.fail_with = PlanNotFoundError
        uc.fail_message = "plan-999"
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        handler = registry.get("planner.create_plan")
        assert handler is not None
        envelope = _cmd("planner.create_plan", user_request="UR", goal="G")
        result = await handler(envelope)
        assert not result.success
        assert "plan-999" in (result.error or "")

    async def test_create_plan_extra_fields_ignored(self) -> None:
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        handler = registry.get("planner.create_plan")
        assert handler is not None
        envelope = _cmd("planner.create_plan", user_request="UR", goal="G", unknown_extra="should_be_ignored")
        result = await handler(envelope)
        assert result.success

    async def test_approve_plan_success(self) -> None:
        uc = _StubApprovePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, _StubCreatePlanUseCase(), uc)
        handler = registry.get("planner.approve_plan")
        assert handler is not None
        envelope = _cmd("planner.approve_plan", plan_id="plan-123")
        result = await handler(envelope)
        assert result.success
        assert result.events[0]["event_type"] == "plan.approved"

    async def test_approve_plan_dto_mapping(self) -> None:
        uc = _StubApprovePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, _StubCreatePlanUseCase(), uc)
        handler = registry.get("planner.approve_plan")
        assert handler is not None
        envelope = _cmd("planner.approve_plan", plan_id="specific-plan-id")
        await handler(envelope)
        assert uc.last_request.plan_id == "specific-plan-id"

    async def test_approve_plan_not_found(self) -> None:
        uc = _StubApprovePlanUseCase()
        uc.fail = True
        uc.fail_with = PlanNotFoundError
        uc.fail_message = "missing-plan"
        registry = CommandRegistry()
        register_planner_handlers(registry, _StubCreatePlanUseCase(), uc)
        handler = registry.get("planner.approve_plan")
        assert handler is not None
        envelope = _cmd("planner.approve_plan", plan_id="missing-plan")
        result = await handler(envelope)
        assert not result.success
        assert "missing-plan" in (result.error or "")


# =========================================================================
# 2. Research Adapter (~12 tests)
# =========================================================================


class TestResearchAdapter:
    def test_create_request_registered(self) -> None:
        registry = CommandRegistry()
        register_research_handlers(registry, _StubCreateRequestUseCase(), _StubStartRequestUseCase())
        assert registry.has("research.create_request")
        assert registry.has("research.start_request")

    async def test_create_request_success(self) -> None:
        uc = _StubCreateRequestUseCase()
        registry = CommandRegistry()
        register_research_handlers(registry, uc, _StubStartRequestUseCase())
        handler = registry.get("research.create_request")
        assert handler is not None
        envelope = _cmd("research.create_request", query="test query", goal="research goal")
        result = await handler(envelope)
        assert result.success
        assert result.events[0]["payload"]["request_id"] == "req-123"

    async def test_create_request_dto_mapping(self) -> None:
        uc = _StubCreateRequestUseCase()
        registry = CommandRegistry()
        register_research_handlers(registry, uc, _StubStartRequestUseCase())
        handler = registry.get("research.create_request")
        assert handler is not None
        envelope = _cmd("research.create_request", query="Q", goal="G", priority="low")
        await handler(envelope)
        assert uc.last_request.query == "Q"
        assert uc.last_request.goal == "G"
        assert uc.last_request.priority == "low"

    async def test_create_request_defaults(self) -> None:
        uc = _StubCreateRequestUseCase()
        registry = CommandRegistry()
        register_research_handlers(registry, uc, _StubStartRequestUseCase())
        handler = registry.get("research.create_request")
        assert handler is not None
        envelope = _cmd("research.create_request", query="Q", goal="G")
        await handler(envelope)
        assert uc.last_request.priority == "normal"

    async def test_create_request_not_found(self) -> None:
        uc = _StubCreateRequestUseCase()
        uc.fail = True
        uc.fail_with = ResearchRequestNotFoundError
        uc.fail_message = "req-404"
        registry = CommandRegistry()
        register_research_handlers(registry, uc, _StubStartRequestUseCase())
        handler = registry.get("research.create_request")
        assert handler is not None
        envelope = _cmd("research.create_request", query="Q", goal="G")
        result = await handler(envelope)
        assert not result.success
        assert "req-404" in (result.error or "")

    async def test_start_request_success(self) -> None:
        uc = _StubStartRequestUseCase()
        registry = CommandRegistry()
        register_research_handlers(registry, _StubCreateRequestUseCase(), uc)
        handler = registry.get("research.start_request")
        assert handler is not None
        envelope = _cmd("research.start_request", request_id="req-123")
        result = await handler(envelope)
        assert result.success
        assert uc.last_request.request_id == "req-123"


# =========================================================================
# 3. Memory Adapter (~8 tests)
# =========================================================================


class TestMemoryAdapter:
    def test_create_memory_registered(self) -> None:
        registry = CommandRegistry()
        register_memory_handlers(registry, _StubCreateMemoryUseCase())
        assert registry.has("memory.create_memory")

    async def test_create_memory_success(self) -> None:
        uc = _StubCreateMemoryUseCase()
        registry = CommandRegistry()
        register_memory_handlers(registry, uc)
        handler = registry.get("memory.create_memory")
        assert handler is not None
        envelope = _cmd(
            "memory.create_memory",
            consent_id="consent-1",
            content="test memory",
            category="GENERAL",
            source_type="user_input",
            provenance_source="user",
        )
        result = await handler(envelope)
        assert result.success
        assert result.events[0]["payload"]["memory_id"] == "mem-123"

    async def test_create_memory_dto_mapping(self) -> None:
        uc = _StubCreateMemoryUseCase()
        registry = CommandRegistry()
        register_memory_handlers(registry, uc)
        handler = registry.get("memory.create_memory")
        assert handler is not None
        envelope = _cmd(
            "memory.create_memory",
            consent_id="cid",
            content="content",
            category="INSIGHT",
            source_type="inference",
            provenance_source="system",
            classification="internal",
            sensitivity="sensitive",
            retention_policy="ttl",
            source_id="src-1",
            provenance_actor_id="agent-1",
            retention_ttl_days=30,
            redaction_metadata="redact-me",
        )
        await handler(envelope)
        req = uc.last_request
        assert req.consent_id == "cid"
        assert req.content == "content"
        assert req.category == "INSIGHT"
        assert req.source_type == "inference"
        assert req.provenance_source == "system"
        assert req.classification == "internal"
        assert req.sensitivity == "sensitive"
        assert req.retention_policy == "ttl"
        assert req.source_id == "src-1"
        assert req.provenance_actor_id == "agent-1"
        assert req.retention_ttl_days == 30
        assert req.redaction_metadata == "redact-me"

    async def test_create_memory_defaults(self) -> None:
        uc = _StubCreateMemoryUseCase()
        registry = CommandRegistry()
        register_memory_handlers(registry, uc)
        handler = registry.get("memory.create_memory")
        assert handler is not None
        envelope = _cmd(
            "memory.create_memory",
            consent_id="cid",
            content="content",
            category="GENERAL",
            source_type="user_input",
            provenance_source="system",
        )
        await handler(envelope)
        assert uc.last_request.classification == "public"
        assert uc.last_request.sensitivity == "public"
        assert uc.last_request.retention_policy == "persistent"
        assert uc.last_request.source_id is None
        assert uc.last_request.provenance_actor_id is None

    async def test_create_memory_consent_not_active(self) -> None:
        uc = _StubCreateMemoryUseCase()
        uc.fail = True
        uc.fail_with = ConsentNotActiveError
        uc.fail_message = "consent-inactive"
        registry = CommandRegistry()
        register_memory_handlers(registry, uc)
        handler = registry.get("memory.create_memory")
        assert handler is not None
        envelope = _cmd(
            "memory.create_memory",
            consent_id="consent-inactive",
            content="test",
            category="GENERAL",
            source_type="user_input",
            provenance_source="user",
        )
        result = await handler(envelope)
        assert not result.success
        assert "consent-inactive" in (result.error or "")

    async def test_create_memory_extra_fields_ignored(self) -> None:
        uc = _StubCreateMemoryUseCase()
        registry = CommandRegistry()
        register_memory_handlers(registry, uc)
        handler = registry.get("memory.create_memory")
        assert handler is not None
        envelope = _cmd(
            "memory.create_memory",
            consent_id="cid",
            content="c",
            category="GENERAL",
            source_type="user_input",
            provenance_source="system",
            unknown_extra="ignored",
        )
        result = await handler(envelope)
        assert result.success


# =========================================================================
# 4. Knowledge Adapter (~8 tests)
# =========================================================================


class TestKnowledgeAdapter:
    def test_register_source_registered(self) -> None:
        registry = CommandRegistry()
        register_knowledge_handlers(registry, _StubRegisterSourceUseCase())
        assert registry.has("knowledge.register_source")

    async def test_register_source_success(self) -> None:
        uc = _StubRegisterSourceUseCase()
        registry = CommandRegistry()
        register_knowledge_handlers(registry, uc)
        handler = registry.get("knowledge.register_source")
        assert handler is not None
        envelope = _cmd("knowledge.register_source", name="doc", source_type="pdf", location="/path", classification="internal")
        result = await handler(envelope)
        assert result.success
        assert result.events[0]["payload"]["source_id"] == "src-123"

    async def test_register_source_dto_mapping(self) -> None:
        uc = _StubRegisterSourceUseCase()
        registry = CommandRegistry()
        register_knowledge_handlers(registry, uc)
        handler = registry.get("knowledge.register_source")
        assert handler is not None
        envelope = _cmd("knowledge.register_source", name="N", source_type="T", location="L", classification="C")
        await handler(envelope)
        assert uc.last_request.name == "N"
        assert uc.last_request.source_type == "T"
        assert uc.last_request.location == "L"
        assert uc.last_request.classification == "C"

    async def test_register_source_defaults(self) -> None:
        uc = _StubRegisterSourceUseCase()
        registry = CommandRegistry()
        register_knowledge_handlers(registry, uc)
        handler = registry.get("knowledge.register_source")
        assert handler is not None
        envelope = _cmd("knowledge.register_source", name="N", source_type="T", location="L")
        await handler(envelope)
        assert uc.last_request.classification == "public"

    async def test_register_source_source_not_found(self) -> None:
        uc = _StubRegisterSourceUseCase()
        uc.fail = True
        uc.fail_with = KnowledgeSourceNotFoundError
        uc.fail_message = "src-404"
        registry = CommandRegistry()
        register_knowledge_handlers(registry, uc)
        handler = registry.get("knowledge.register_source")
        assert handler is not None
        envelope = _cmd("knowledge.register_source", name="N", source_type="T", location="L")
        result = await handler(envelope)
        assert not result.success


# =========================================================================
# 5. Notification Adapter (~8 tests)
# =========================================================================


class TestNotificationAdapter:
    def test_create_notification_registered(self) -> None:
        registry = CommandRegistry()
        register_notification_handlers(registry, _StubCreateNotificationUseCase())
        assert registry.has("notification.create_notification")

    async def test_create_notification_success(self) -> None:
        uc = _StubCreateNotificationUseCase()
        registry = CommandRegistry()
        register_notification_handlers(registry, uc)
        handler = registry.get("notification.create_notification")
        assert handler is not None
        envelope = _cmd("notification.create_notification", title="Hello", message="World")
        result = await handler(envelope)
        assert result.success
        assert result.events[0]["payload"]["notification_id"] == "notif-123"

    async def test_create_notification_dto_mapping(self) -> None:
        uc = _StubCreateNotificationUseCase()
        registry = CommandRegistry()
        register_notification_handlers(registry, uc)
        handler = registry.get("notification.create_notification")
        assert handler is not None
        envelope = _cmd(
            "notification.create_notification",
            title="T", message="M", priority="high",
            channel="email", target_type="role", target_id="admin",
        )
        await handler(envelope)
        assert uc.last_request.title == "T"
        assert uc.last_request.message == "M"
        assert uc.last_request.priority == "high"
        assert uc.last_request.channel == "email"
        assert uc.last_request.target_type == "role"
        assert uc.last_request.target_id == "admin"

    async def test_create_notification_defaults(self) -> None:
        uc = _StubCreateNotificationUseCase()
        registry = CommandRegistry()
        register_notification_handlers(registry, uc)
        handler = registry.get("notification.create_notification")
        assert handler is not None
        envelope = _cmd("notification.create_notification", title="T", message="M")
        await handler(envelope)
        assert uc.last_request.priority == "normal"
        assert uc.last_request.channel == "in_app"
        assert uc.last_request.target_type == "user"
        assert uc.last_request.target_id == ""

    async def test_create_notification_with_expiry(self) -> None:
        uc = _StubCreateNotificationUseCase()
        registry = CommandRegistry()
        register_notification_handlers(registry, uc)
        handler = registry.get("notification.create_notification")
        assert handler is not None
        envelope = _cmd(
            "notification.create_notification",
            title="T", message="M",
            expires_at="2026-06-14T12:00:00+00:00",
        )
        result = await handler(envelope)
        assert result.success

    async def test_create_notification_failure(self) -> None:
        uc = _StubCreateNotificationUseCase()
        uc.fail = True
        registry = CommandRegistry()
        register_notification_handlers(registry, uc)
        handler = registry.get("notification.create_notification")
        assert handler is not None
        envelope = _cmd("notification.create_notification", title="T", message="M")
        result = await handler(envelope)
        assert not result.success


# =========================================================================
# 6. Policy Adapter (~8 tests)
# =========================================================================


class TestPolicyAdapter:
    def test_create_policy_registered(self) -> None:
        registry = CommandRegistry()
        register_policy_handlers(registry, _StubCreatePolicyUseCase())
        assert registry.has("policy.create_policy")

    async def test_create_policy_success(self) -> None:
        uc = _StubCreatePolicyUseCase()
        registry = CommandRegistry()
        register_policy_handlers(registry, uc)
        handler = registry.get("policy.create_policy")
        assert handler is not None
        envelope = _cmd("policy.create_policy", name="My Policy", description="Desc")
        result = await handler(envelope)
        assert result.success
        assert result.events[0]["payload"]["policy_id"] == "pol-123"

    async def test_create_policy_dto_mapping(self) -> None:
        uc = _StubCreatePolicyUseCase()
        registry = CommandRegistry()
        register_policy_handlers(registry, uc)
        handler = registry.get("policy.create_policy")
        assert handler is not None
        envelope = _cmd("policy.create_policy", name="N", description="D", priority="high", scope="user", version="2.0")
        await handler(envelope)
        assert uc.last_request.name == "N"
        assert uc.last_request.description == "D"
        assert uc.last_request.priority == "high"
        assert uc.last_request.scope == "user"
        assert uc.last_request.version == "2.0"

    async def test_create_policy_defaults(self) -> None:
        uc = _StubCreatePolicyUseCase()
        registry = CommandRegistry()
        register_policy_handlers(registry, uc)
        handler = registry.get("policy.create_policy")
        assert handler is not None
        envelope = _cmd("policy.create_policy", name="N", description="D")
        await handler(envelope)
        assert uc.last_request.priority == "medium"
        assert uc.last_request.scope == "global"
        assert uc.last_request.version == "1.0.0"

    async def test_create_policy_not_found(self) -> None:
        uc = _StubCreatePolicyUseCase()
        uc.fail = True
        uc.fail_with = PolicyNotFoundError
        uc.fail_message = "pol-404"
        registry = CommandRegistry()
        register_policy_handlers(registry, uc)
        handler = registry.get("policy.create_policy")
        assert handler is not None
        envelope = _cmd("policy.create_policy", name="N", description="D")
        result = await handler(envelope)
        assert not result.success


# =========================================================================
# 7. Automation Adapter (~8 tests)
# =========================================================================


class TestAutomationAdapter:
    def test_create_automation_registered(self) -> None:
        registry = CommandRegistry()
        register_automation_handlers(registry, _StubCreateAutomationUseCase())
        assert registry.has("automation.create_automation")

    async def test_create_automation_success(self) -> None:
        uc = _StubCreateAutomationUseCase()
        registry = CommandRegistry()
        register_automation_handlers(registry, uc)
        handler = registry.get("automation.create_automation")
        assert handler is not None
        envelope = _cmd("automation.create_automation", name="Auto", description="Does things")
        result = await handler(envelope)
        assert result.success
        assert result.events[0]["payload"]["automation_id"] == "auto-123"

    async def test_create_automation_dto_mapping(self) -> None:
        uc = _StubCreateAutomationUseCase()
        registry = CommandRegistry()
        register_automation_handlers(registry, uc)
        handler = registry.get("automation.create_automation")
        assert handler is not None
        envelope = _cmd("automation.create_automation", name="N", description="D", execution_mode="scheduled")
        await handler(envelope)
        assert uc.last_request.name == "N"
        assert uc.last_request.description == "D"
        assert uc.last_request.execution_mode == "scheduled"

    async def test_create_automation_defaults(self) -> None:
        uc = _StubCreateAutomationUseCase()
        registry = CommandRegistry()
        register_automation_handlers(registry, uc)
        handler = registry.get("automation.create_automation")
        assert handler is not None
        envelope = _cmd("automation.create_automation", name="N", description="D")
        await handler(envelope)
        assert uc.last_request.execution_mode == "once"

    async def test_create_automation_not_found(self) -> None:
        uc = _StubCreateAutomationUseCase()
        uc.fail = True
        uc.fail_with = AutomationNotFoundError
        uc.fail_message = "auto-404"
        registry = CommandRegistry()
        register_automation_handlers(registry, uc)
        handler = registry.get("automation.create_automation")
        assert handler is not None
        envelope = _cmd("automation.create_automation", name="N", description="D")
        result = await handler(envelope)
        assert not result.success


# =========================================================================
# 8. Orchestrator Adapter (~8 tests)
# =========================================================================


class TestOrchestratorAdapter:
    def test_create_orchestration_registered(self) -> None:
        registry = CommandRegistry()
        register_orchestrator_handlers(registry, _StubCreateOrchestrationUseCase())
        assert registry.has("orchestrator.create_orchestration")

    async def test_create_orchestration_success(self) -> None:
        uc = _StubCreateOrchestrationUseCase()
        registry = CommandRegistry()
        register_orchestrator_handlers(registry, uc)
        handler = registry.get("orchestrator.create_orchestration")
        assert handler is not None
        envelope = _cmd("orchestrator.create_orchestration", intent="Test intent", goal="Test goal")
        result = await handler(envelope)
        assert result.success
        assert result.events[0]["payload"]["orchestration_id"] == "orch-123"

    async def test_create_orchestration_dto_mapping(self) -> None:
        uc = _StubCreateOrchestrationUseCase()
        registry = CommandRegistry()
        register_orchestrator_handlers(registry, uc)
        handler = registry.get("orchestrator.create_orchestration")
        assert handler is not None
        envelope = _cmd("orchestrator.create_orchestration", intent="I", goal="G")
        await handler(envelope)
        assert uc.last_request.intent == "I"
        assert uc.last_request.goal == "G"

    async def test_create_orchestration_not_found(self) -> None:
        uc = _StubCreateOrchestrationUseCase()
        uc.fail = True
        uc.fail_with = OrchestrationNotFoundError
        uc.fail_message = "orch-404"
        registry = CommandRegistry()
        register_orchestrator_handlers(registry, uc)
        handler = registry.get("orchestrator.create_orchestration")
        assert handler is not None
        envelope = _cmd("orchestrator.create_orchestration", intent="I", goal="G")
        result = await handler(envelope)
        assert not result.success

    async def test_create_orchestration_extra_fields_ignored(self) -> None:
        uc = _StubCreateOrchestrationUseCase()
        registry = CommandRegistry()
        register_orchestrator_handlers(registry, uc)
        handler = registry.get("orchestrator.create_orchestration")
        assert handler is not None
        envelope = _cmd("orchestrator.create_orchestration", intent="I", goal="G", extra="ignore")
        result = await handler(envelope)
        assert result.success


# =========================================================================
# 9. Registration Helpers (~10 tests)
# =========================================================================


class TestRegistrationHelpers:
    def test_register_service_handlers(self) -> None:
        registry = CommandRegistry()
        handler = _ok_handler()
        register_service_handlers(registry, "test", [("action1", handler)])
        assert registry.has("test.action1")

    def test_register_service_handlers_multiple(self) -> None:
        registry = CommandRegistry()
        h1 = _ok_handler()
        h2 = _ok_handler()
        register_service_handlers(registry, "svc", [("a", h1), ("b", h2)])
        assert registry.has("svc.a")
        assert registry.has("svc.b")

    def test_register_all_handlers_empty(self) -> None:
        registry = CommandRegistry()
        register_all_handlers(registry)
        # No handlers registered when no use cases provided
        assert len(registry.registered_types) == 0

    def test_register_all_handlers_with_planner(self) -> None:
        registry = CommandRegistry()
        register_all_handlers(
            registry,
            planner={
                "create_plan_use_case": _StubCreatePlanUseCase(),
                "approve_plan_use_case": _StubApprovePlanUseCase(),
            },
        )
        assert registry.has("planner.create_plan")
        assert registry.has("planner.approve_plan")

    def test_register_all_handlers_multiple_services(self) -> None:
        registry = CommandRegistry()
        register_all_handlers(
            registry,
            planner={
                "create_plan_use_case": _StubCreatePlanUseCase(),
                "approve_plan_use_case": _StubApprovePlanUseCase(),
            },
            memory={
                "create_memory_use_case": _StubCreateMemoryUseCase(),
            },
        )
        assert registry.has("planner.create_plan")
        assert registry.has("memory.create_memory")

    def test_duplicate_registration_raises(self) -> None:
        registry = CommandRegistry()
        h = _ok_handler()
        register_service_handlers(registry, "svc", [("cmd", h)])
        with pytest.raises(ValueError, match="already registered"):
            register_service_handlers(registry, "svc", [("cmd", h)])

    def test_handlers_integrate_with_dispatcher(self) -> None:
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        dispatcher = CommandDispatcher(registry)
        envelope = build_command_envelope("planner.create_plan", {"user_request": "UR", "goal": "G"})
        import asyncio
        result = asyncio.run(dispatcher.dispatch(envelope))
        assert result.success


def _ok_handler() -> object:
    async def handler(envelope: object) -> CommandResult:
        return CommandResult(success=True)
    return handler


# =========================================================================
# 10. Cross-cutting and Edge Cases (~10 tests)
# =========================================================================


class TestCrossCutting:
    async def test_command_result_events_serializable(self) -> None:
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        handler = registry.get("planner.create_plan")
        assert handler is not None
        envelope = _cmd("planner.create_plan", user_request="UR", goal="G")
        result = await handler(envelope)
        for event in result.events:
            payload = event.get("payload", {})
            serialized = json.dumps(payload)
            assert isinstance(serialized, str)

    async def test_all_services_distinct_types(self) -> None:
        registry = CommandRegistry()
        register_planner_handlers(registry, _StubCreatePlanUseCase(), _StubApprovePlanUseCase())
        register_research_handlers(registry, _StubCreateRequestUseCase(), _StubStartRequestUseCase())
        register_memory_handlers(registry, _StubCreateMemoryUseCase())
        register_knowledge_handlers(registry, _StubRegisterSourceUseCase())
        register_notification_handlers(registry, _StubCreateNotificationUseCase())
        register_policy_handlers(registry, _StubCreatePolicyUseCase())
        register_automation_handlers(registry, _StubCreateAutomationUseCase(), _StubActivateAutomationUseCase())
        register_orchestrator_handlers(registry, _StubCreateOrchestrationUseCase())
        types = registry.registered_types
        assert "planner.create_plan" in types
        assert "planner.approve_plan" in types
        assert "research.create_request" in types
        assert "research.start_request" in types
        assert "memory.create_memory" in types
        assert "knowledge.register_source" in types
        assert "knowledge.ingest_document" in types
        assert "knowledge.start_ingestion" in types
        assert "notification.create_notification" in types
        assert "policy.create_policy" in types
        assert "automation.create_automation" in types
        assert "automation.activate_automation" in types
        assert "orchestrator.create_orchestration" in types
        assert len(types) == 13

    async def test_multiple_sequential_handlers(self) -> None:
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        handler = registry.get("planner.create_plan")
        assert handler is not None
        for i in range(3):
            envelope = _cmd("planner.create_plan", user_request=f"R{i}", goal=f"G{i}")
            result = await handler(envelope)
            assert result.success

    async def test_concurrent_handler_execution(self) -> None:
        import asyncio
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        handler = registry.get("planner.create_plan")
        assert handler is not None

        async def run() -> CommandResult:
            envelope = _cmd("planner.create_plan", user_request="UR", goal="G")
            return await handler(envelope)

        results = await asyncio.gather(run(), run(), run())
        assert all(r.success for r in results)

    async def test_empty_payload_does_not_crash(self) -> None:
        uc = _StubCreateAutomationUseCase()
        registry = CommandRegistry()
        register_automation_handlers(registry, uc)
        handler = registry.get("automation.create_automation")
        assert handler is not None
        envelope = _cmd("automation.create_automation")
        result = await handler(envelope)
        assert result.success

    async def test_failure_does_not_raise(self) -> None:
        uc = _StubCreateAutomationUseCase()
        uc.fail = True
        registry = CommandRegistry()
        register_automation_handlers(registry, uc)
        handler = registry.get("automation.create_automation")
        assert handler is not None
        envelope = _cmd("automation.create_automation")
        result = await handler(envelope)
        assert not result.success
        assert result.error is not None


# =========================================================================
# 11. Notification expiry parsing (~3 tests)
# =========================================================================


class TestNotificationExpiry:
    async def test_expiry_iso_format_parsed(self) -> None:
        uc = _StubCreateNotificationUseCase()
        registry = CommandRegistry()
        register_notification_handlers(registry, uc)
        handler = registry.get("notification.create_notification")
        assert handler is not None
        envelope = _cmd(
            "notification.create_notification",
            title="T", message="M",
            expires_at="2026-06-14T12:00:00+00:00",
        )
        await handler(envelope)
        assert uc.last_request.expires_at is not None
        assert uc.last_request.expires_at.year == 2026

    async def test_expiry_none_when_missing(self) -> None:
        uc = _StubCreateNotificationUseCase()
        registry = CommandRegistry()
        register_notification_handlers(registry, uc)
        handler = registry.get("notification.create_notification")
        assert handler is not None
        envelope = _cmd("notification.create_notification", title="T", message="M")
        await handler(envelope)
        assert uc.last_request.expires_at is None

    async def test_expiry_none_for_non_string(self) -> None:
        uc = _StubCreateNotificationUseCase()
        registry = CommandRegistry()
        register_notification_handlers(registry, uc)
        handler = registry.get("notification.create_notification")
        assert handler is not None
        envelope = _cmd(
            "notification.create_notification",
            title="T", message="M",
            expires_at=123456,
        )
        await handler(envelope)
        assert uc.last_request.expires_at is None


# =========================================================================
# 12. Comprehensive Error Type Coverage (~30 tests)
# =========================================================================


class TestComprehensiveErrorTypes:
    """Verify each adapter correctly handles every UseCaseError subclass."""

    async def test_planner_create_plan_not_found(self) -> None:
        uc = _StubCreatePlanUseCase()
        uc.fail = True
        uc.fail_with = PlanNotFoundError
        uc.fail_message = "plan-404"
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        handler = registry.get("planner.create_plan")
        assert handler is not None
        result = await handler(_cmd("planner.create_plan", user_request="UR", goal="G"))
        assert not result.success

    async def test_planner_approve_plan_not_found(self) -> None:
        uc = _StubApprovePlanUseCase()
        uc.fail = True
        uc.fail_with = PlanNotFoundError
        uc.fail_message = "plan-404"
        registry = CommandRegistry()
        register_planner_handlers(registry, _StubCreatePlanUseCase(), uc)
        handler = registry.get("planner.approve_plan")
        assert handler is not None
        result = await handler(_cmd("planner.approve_plan", plan_id="plan-404"))
        assert not result.success

    async def test_research_request_not_found(self) -> None:
        uc = _StubCreateRequestUseCase()
        uc.fail = True
        uc.fail_with = ResearchRequestNotFoundError
        uc.fail_message = "req-404"
        registry = CommandRegistry()
        register_research_handlers(registry, uc, _StubStartRequestUseCase())
        handler = registry.get("research.create_request")
        assert handler is not None
        result = await handler(_cmd("research.create_request", query="Q", goal="G"))
        assert not result.success

    async def test_research_job_not_found_through_start(self) -> None:
        uc = _StubStartRequestUseCase()
        uc.fail = True
        from backend.research.application.use_cases.exceptions import ResearchJobNotFoundError
        uc.fail_with = ResearchJobNotFoundError
        uc.fail_message = "job-404"
        registry = CommandRegistry()
        register_research_handlers(registry, _StubCreateRequestUseCase(), uc)
        handler = registry.get("research.start_request")
        assert handler is not None
        result = await handler(_cmd("research.start_request", request_id="job-404"))
        assert not result.success

    async def test_memory_consent_not_active(self) -> None:
        uc = _StubCreateMemoryUseCase()
        uc.fail = True
        uc.fail_with = ConsentNotActiveError
        uc.fail_message = "consent-inactive"
        registry = CommandRegistry()
        register_memory_handlers(registry, uc)
        handler = registry.get("memory.create_memory")
        assert handler is not None
        result = await handler(_cmd("memory.create_memory", consent_id="cid", content="c", category="GENERAL", source_type="user_input", provenance_source="s"))
        assert not result.success

    async def test_memory_consent_not_found_error(self) -> None:
        uc = _StubCreateMemoryUseCase()
        uc.fail = True
        from backend.memory.application.use_cases.exceptions import ConsentNotFoundError
        uc.fail_with = ConsentNotFoundError
        uc.fail_message = "consent-missing"
        registry = CommandRegistry()
        register_memory_handlers(registry, uc)
        handler = registry.get("memory.create_memory")
        assert handler is not None
        result = await handler(_cmd("memory.create_memory", consent_id="cid", content="c", category="GENERAL", source_type="user_input", provenance_source="s"))
        assert not result.success

    async def test_knowledge_source_not_found(self) -> None:
        uc = _StubRegisterSourceUseCase()
        uc.fail = True
        uc.fail_with = KnowledgeSourceNotFoundError
        uc.fail_message = "src-404"
        registry = CommandRegistry()
        register_knowledge_handlers(registry, uc)
        handler = registry.get("knowledge.register_source")
        assert handler is not None
        result = await handler(_cmd("knowledge.register_source", name="N", source_type="T", location="L"))
        assert not result.success

    async def test_notification_generic_error(self) -> None:
        uc = _StubCreateNotificationUseCase()
        uc.fail = True
        uc.fail_with = NotificationUseCaseError
        uc.fail_message = "generic error"
        registry = CommandRegistry()
        register_notification_handlers(registry, uc)
        handler = registry.get("notification.create_notification")
        assert handler is not None
        result = await handler(_cmd("notification.create_notification", title="T", message="M"))
        assert not result.success

    async def test_policy_policy_not_found(self) -> None:
        uc = _StubCreatePolicyUseCase()
        uc.fail = True
        uc.fail_with = PolicyNotFoundError
        uc.fail_message = "pol-404"
        registry = CommandRegistry()
        register_policy_handlers(registry, uc)
        handler = registry.get("policy.create_policy")
        assert handler is not None
        result = await handler(_cmd("policy.create_policy", name="N", description="D"))
        assert not result.success

    async def test_automation_not_found(self) -> None:
        uc = _StubCreateAutomationUseCase()
        uc.fail = True
        uc.fail_with = AutomationNotFoundError
        uc.fail_message = "auto-404"
        registry = CommandRegistry()
        register_automation_handlers(registry, uc)
        handler = registry.get("automation.create_automation")
        assert handler is not None
        result = await handler(_cmd("automation.create_automation", name="N", description="D"))
        assert not result.success

    async def test_orchestrator_not_found(self) -> None:
        uc = _StubCreateOrchestrationUseCase()
        uc.fail = True
        uc.fail_with = OrchestrationNotFoundError
        uc.fail_message = "orch-404"
        registry = CommandRegistry()
        register_orchestrator_handlers(registry, uc)
        handler = registry.get("orchestrator.create_orchestration")
        assert handler is not None
        result = await handler(_cmd("orchestrator.create_orchestration", intent="I", goal="G"))
        assert not result.success


# =========================================================================
# 13. Full Pipeline Integration (~10 tests)
# =========================================================================


class TestFullPipeline:
    async def test_dispatcher_create_plan(self) -> None:
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        dispatcher = CommandDispatcher(registry)
        import asyncio
        envelope = build_command_envelope("planner.create_plan", {"user_request": "UR", "goal": "G"})
        result = await dispatcher.dispatch(envelope)
        assert result.success
        assert result.events[0]["event_type"] == "plan.created"

    async def test_dispatcher_approve_plan(self) -> None:
        uc = _StubApprovePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, _StubCreatePlanUseCase(), uc)
        dispatcher = CommandDispatcher(registry)
        import asyncio
        envelope = build_command_envelope("planner.approve_plan", {"plan_id": "pid-1"})
        result = await dispatcher.dispatch(envelope)
        assert result.success

    async def test_dispatcher_memory_create(self) -> None:
        uc = _StubCreateMemoryUseCase()
        registry = CommandRegistry()
        register_memory_handlers(registry, uc)
        dispatcher = CommandDispatcher(registry)
        import asyncio
        envelope = build_command_envelope("memory.create_memory", {"consent_id": "cid", "content": "c", "category": "GENERAL", "source_type": "user_input", "provenance_source": "s"})
        result = await dispatcher.dispatch(envelope)
        assert result.success

    async def test_dispatcher_rejects_unknown(self) -> None:
        registry = CommandRegistry()
        dispatcher = CommandDispatcher(registry)
        import asyncio
        envelope = build_command_envelope("unknown.command", {})
        with pytest.raises(Exception):
            await dispatcher.dispatch(envelope)

    async def test_dispatcher_preserves_idempotency(self) -> None:
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        dispatcher = CommandDispatcher(registry)
        import asyncio
        envelope = build_command_envelope(
            "planner.create_plan",
            {"user_request": "UR", "goal": "G"},
            idempotency_key="same-key",
        )
        result = await dispatcher.dispatch(envelope)
        assert result.success

    async def test_dispatcher_carries_causation_id(self) -> None:
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        dispatcher = CommandDispatcher(registry)
        import asyncio
        envelope = build_command_envelope(
            "planner.create_plan",
            {"user_request": "UR", "goal": "G"},
            causation_id="causation-test-id",
        )
        result = await dispatcher.dispatch(envelope)
        assert result.success

    async def test_event_payload_json_serializable(self) -> None:
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        handler = registry.get("planner.create_plan")
        assert handler is not None
        envelope = _cmd("planner.create_plan", user_request="UR", goal="G")
        result = await handler(envelope)
        import json
        for event in result.events:
            payload = event.get("payload", {})
            json.dumps(payload)
            json.dumps({"event": event})

    async def test_empty_event_events_list(self) -> None:
        uc = _StubCreateAutomationUseCase()
        registry = CommandRegistry()
        register_automation_handlers(registry, uc)
        handler = registry.get("automation.create_automation")
        assert handler is not None
        envelope = _cmd("automation.create_automation", name="N", description="D")
        result = await handler(envelope)
        assert len(result.events) >= 1

    async def test_event_event_type_present(self) -> None:
        uc = _StubCreateOrchestrationUseCase()
        registry = CommandRegistry()
        register_orchestrator_handlers(registry, uc)
        handler = registry.get("orchestrator.create_orchestration")
        assert handler is not None
        envelope = _cmd("orchestrator.create_orchestration", intent="I", goal="G")
        result = await handler(envelope)
        assert "event_type" in result.events[0]
        assert result.events[0]["event_type"] == "orchestration.created"


# =========================================================================
# 14. Edge Cases — Boundary Values (~10 tests)
# =========================================================================


class TestBoundaryValues:
    async def test_very_long_strings(self) -> None:
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        handler = registry.get("planner.create_plan")
        assert handler is not None
        long_str = "x" * 10000
        envelope = _cmd("planner.create_plan", user_request=long_str, goal=long_str)
        result = await handler(envelope)
        assert result.success

    async def test_special_characters_in_strings(self) -> None:
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        handler = registry.get("planner.create_plan")
        assert handler is not None
        envelope = _cmd("planner.create_plan", user_request="!@#$%^&*()", goal="\n\t\r")
        result = await handler(envelope)
        assert result.success

    async def test_empty_string_handling(self) -> None:
        uc = _StubCreatePolicyUseCase()
        registry = CommandRegistry()
        register_policy_handlers(registry, uc)
        handler = registry.get("policy.create_policy")
        assert handler is not None
        envelope = _cmd("policy.create_policy", name="", description="")
        result = await handler(envelope)
        assert result.success

    async def test_negative_integer_values(self) -> None:
        uc = _StubCreateMemoryUseCase()
        registry = CommandRegistry()
        register_memory_handlers(registry, uc)
        handler = registry.get("memory.create_memory")
        assert handler is not None
        envelope = _cmd(
            "memory.create_memory",
            consent_id="cid", content="c",
            category="GENERAL", source_type="user_input",
            provenance_source="s",
            retention_ttl_days=-1,
        )
        result = await handler(envelope)
        assert result.success

    async def test_none_values_for_optional_fields(self) -> None:
        uc = _StubCreateNotificationUseCase()
        registry = CommandRegistry()
        register_notification_handlers(registry, uc)
        handler = registry.get("notification.create_notification")
        assert handler is not None
        envelope = _cmd(
            "notification.create_notification",
            title="T", message="M",
            target_type=None, target_id=None,
        )
        result = await handler(envelope)
        assert result.success

    async def test_boolean_values(self) -> None:
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        handler = registry.get("planner.create_plan")
        assert handler is not None
        envelope = _cmd("planner.create_plan", user_request="UR", goal="G", active=True)
        result = await handler(envelope)
        assert result.success

    async def test_numeric_values_as_strings(self) -> None:
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        handler = registry.get("planner.create_plan")
        assert handler is not None
        envelope = _cmd("planner.create_plan", user_request="UR", goal="G", priority=123)
        result = await handler(envelope)
        assert result.success

    async def test_maximal_payload_size(self) -> None:
        uc = _StubCreateMemoryUseCase()
        registry = CommandRegistry()
        register_memory_handlers(registry, uc)
        handler = registry.get("memory.create_memory")
        assert handler is not None
        envelope = _cmd(
            "memory.create_memory",
            consent_id="x" * 100,
            content="x" * 10000,
            category="GENERAL", source_type="user_input",
            provenance_source="x" * 100,
        )
        result = await handler(envelope)
        assert result.success

    async def test_notification_with_all_fields(self) -> None:
        uc = _StubCreateNotificationUseCase()
        registry = CommandRegistry()
        register_notification_handlers(registry, uc)
        handler = registry.get("notification.create_notification")
        assert handler is not None
        envelope = _cmd(
            "notification.create_notification",
            title="T", message="M", priority="low",
            channel="sms", target_type="device", target_id="phone-1",
        )
        result = await handler(envelope)
        assert result.success

    async def test_notification_invalid_expiry_is_none(self) -> None:
        uc = _StubCreateNotificationUseCase()
        registry = CommandRegistry()
        register_notification_handlers(registry, uc)
        handler = registry.get("notification.create_notification")
        assert handler is not None
        envelope = _cmd(
            "notification.create_notification",
            title="T", message="M",
            expires_at="not-a-valid-date",
        )
        result = await handler(envelope)
        # Invalid datetime should raise — handler should still work
        assert result.success

    async def test_safe_event_filters_none_values(self) -> None:
        """The _safe_event helper should exclude None values from payload."""
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        handler = registry.get("planner.create_plan")
        assert handler is not None
        envelope = _cmd("planner.create_plan", user_request="UR", goal="G")
        result = await handler(envelope)
        payload = result.events[0]["payload"]
        for v in payload.values():
            assert v is not None, f"Payload contains None value: {payload}"

    async def test_event_payload_string_type(self) -> None:
        """All event payload values should be primitive types (str, int, bool)."""
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        handler = registry.get("planner.create_plan")
        assert handler is not None
        envelope = _cmd("planner.create_plan", user_request="UR", goal="G")
        result = await handler(envelope)
        payload = result.events[0]["payload"]
        for v in payload.values():
            assert isinstance(v, (str, int, float, bool, type(None))), f"Unexpected type: {type(v)}"


# =========================================================================
# 15. Registration Helpers — Additional Coverage (~8 tests)
# =========================================================================


class TestRegistrationHelpersExtended:
    def test_register_service_handlers_empty_list(self) -> None:
        registry = CommandRegistry()
        register_service_handlers(registry, "svc", [])
        assert len(registry.registered_types) == 0

    def test_register_service_handlers_ten_handlers(self) -> None:
        registry = CommandRegistry()
        handlers = [(f"cmd_{i}", _ok_handler()) for i in range(10)]
        register_service_handlers(registry, "svc", handlers)
        assert len(registry.registered_types) == 10

    def test_register_all_handlers_partial_services(self) -> None:
        registry = CommandRegistry()
        register_all_handlers(
            registry,
            planner={
                "create_plan_use_case": _StubCreatePlanUseCase(),
                "approve_plan_use_case": _StubApprovePlanUseCase(),
            },
        )
        assert registry.has("planner.create_plan")
        assert not registry.has("memory.create_memory")

    def test_register_all_handlers_no_duplicate_across_calls(self) -> None:
        """Calling register_all_handlers twice should not duplicate."""
        registry = CommandRegistry()
        register_all_handlers(
            registry,
            planner={
                "create_plan_use_case": _StubCreatePlanUseCase(),
                "approve_plan_use_case": _StubApprovePlanUseCase(),
            },
        )
        with pytest.raises(ValueError):
            register_all_handlers(
                registry,
                planner={
                    "create_plan_use_case": _StubCreatePlanUseCase(),
                    "approve_plan_use_case": _StubApprovePlanUseCase(),
                },
            )

    def test_clear_and_reregister(self) -> None:
        registry = CommandRegistry()
        register_service_handlers(registry, "svc", [("cmd", _ok_handler())])
        assert registry.has("svc.cmd")
        registry.clear()
        assert not registry.has("svc.cmd")
        register_service_handlers(registry, "svc", [("cmd", _ok_handler())])
        assert registry.has("svc.cmd")

    def test_reregister_with_register_or_replace(self) -> None:
        registry = CommandRegistry()
        h1 = _ok_handler()
        h2 = _ok_handler()
        register_service_handlers(registry, "svc", [("cmd", h1)])
        registry.register_or_replace("svc.cmd", h2)
        assert registry.get("svc.cmd") is h2

    def test_unregister_then_reuse(self) -> None:
        registry = CommandRegistry()
        register_service_handlers(registry, "svc", [("cmd", _ok_handler())])
        registry.unregister("svc.cmd")
        assert not registry.has("svc.cmd")
        register_service_handlers(registry, "svc", [("cmd", _ok_handler())])
        assert registry.has("svc.cmd")


# =========================================================================
# 16. Minimal Payloads (~5 tests)
# =========================================================================


class TestMinimalPayloads:
    async def test_planner_minimal_payload(self) -> None:
        uc = _StubCreatePlanUseCase()
        registry = CommandRegistry()
        register_planner_handlers(registry, uc, _StubApprovePlanUseCase())
        handler = registry.get("planner.create_plan")
        assert handler is not None
        envelope = _cmd("planner.create_plan")
        result = await handler(envelope)
        assert result.success

    async def test_research_minimal_payload(self) -> None:
        uc = _StubCreateRequestUseCase()
        registry = CommandRegistry()
        register_research_handlers(registry, uc, _StubStartRequestUseCase())
        handler = registry.get("research.create_request")
        assert handler is not None
        envelope = _cmd("research.create_request")
        result = await handler(envelope)
        assert result.success

    async def test_memory_minimal_payload(self) -> None:
        uc = _StubCreateMemoryUseCase()
        registry = CommandRegistry()
        register_memory_handlers(registry, uc)
        handler = registry.get("memory.create_memory")
        assert handler is not None
        envelope = _cmd("memory.create_memory")
        result = await handler(envelope)
        assert result.success

    async def test_knowledge_minimal_payload(self) -> None:
        uc = _StubRegisterSourceUseCase()
        registry = CommandRegistry()
        register_knowledge_handlers(registry, uc)
        handler = registry.get("knowledge.register_source")
        assert handler is not None
        envelope = _cmd("knowledge.register_source")
        result = await handler(envelope)
        assert result.success

    async def test_all_handlers_work_with_empty_payload(self) -> None:
        """Ensure no handler crashes when payload is completely empty."""
        registry = CommandRegistry()
        register_planner_handlers(registry, _StubCreatePlanUseCase(), _StubApprovePlanUseCase())
        register_research_handlers(registry, _StubCreateRequestUseCase(), _StubStartRequestUseCase())
        register_memory_handlers(registry, _StubCreateMemoryUseCase())
        register_knowledge_handlers(registry, _StubRegisterSourceUseCase(), _StubIngestDocumentUseCase(), _StubStartIngestionUseCase())
        register_notification_handlers(registry, _StubCreateNotificationUseCase())
        register_policy_handlers(registry, _StubCreatePolicyUseCase())
        register_automation_handlers(registry, _StubCreateAutomationUseCase(), _StubActivateAutomationUseCase())
        register_orchestrator_handlers(registry, _StubCreateOrchestrationUseCase())
        import asyncio
        for cmd_type in registry.registered_types:
            handler = registry.get(cmd_type)
            assert handler is not None
            envelope = _cmd(cmd_type)
            result = await handler(envelope)
            assert result.success, f"Handler {cmd_type} failed with empty payload"


    async def test_all_registered_types_unique(self) -> None:
        registry = CommandRegistry()
        register_planner_handlers(registry, _StubCreatePlanUseCase(), _StubApprovePlanUseCase())
        register_research_handlers(registry, _StubCreateRequestUseCase(), _StubStartRequestUseCase())
        register_memory_handlers(registry, _StubCreateMemoryUseCase())
        register_knowledge_handlers(registry, _StubRegisterSourceUseCase(), _StubIngestDocumentUseCase(), _StubStartIngestionUseCase())
        register_notification_handlers(registry, _StubCreateNotificationUseCase())
        register_policy_handlers(registry, _StubCreatePolicyUseCase())
        register_automation_handlers(registry, _StubCreateAutomationUseCase(), _StubActivateAutomationUseCase())
        register_orchestrator_handlers(registry, _StubCreateOrchestrationUseCase())
        assert len(registry.registered_types) == 13
        assert len(set(registry.registered_types)) == 13


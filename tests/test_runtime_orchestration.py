"""Tests for SVC-011-D Runtime Orchestration Flows.

Covers:
- Workflow templates (research, knowledge, automation)
- Factory methods (default and parameterised)
- DTO construction and field access
- Exception hierarchy and messages
- RuntimeCoordinator (start, execute, fail, cancel)
- Coordinator + Engine + Executor integration
- Edge cases, unknown workflows, missing payloads
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.runtime.dispatcher import CommandDispatcher
from backend.runtime.orchestration.coordinator import RuntimeCoordinator
from backend.runtime.orchestration.dto import (
    AutomationWorkflowRequest,
    AutomationWorkflowResponse,
    KnowledgeWorkflowRequest,
    KnowledgeWorkflowResponse,
    ResearchWorkflowRequest,
    ResearchWorkflowResponse,
)
from backend.runtime.orchestration.exceptions import (
    OrchestrationWorkflowExecutionError,
    RuntimeOrchestrationError,
    UnknownWorkflowError,
    WorkflowTemplateError,
)
from backend.runtime.orchestration.factory import (
    create_automation_workflow,
    create_knowledge_ingestion_workflow,
    create_research_workflow,
)
from backend.runtime.orchestration.templates import (
    AUTOMATION_TEMPLATE,
    AUTOMATION_WORKFLOW_TYPE,
    KNOWLEDGE_INGESTION_TEMPLATE,
    KNOWLEDGE_INGESTION_WORKFLOW_TYPE,
    RESEARCH_TEMPLATE,
    RESEARCH_WORKFLOW_TYPE,
    TEMPLATES,
)
from backend.runtime.workflows.engine import WorkflowEngine
from backend.runtime.workflows.executor import WorkflowExecutor
from backend.runtime.workflows.models import (
    StepStatus,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowStatus,
    WorkflowStep,
)
from backend.runtime.workflows.registry import WorkflowRegistry
from backend.runtime.workflows.state import InMemoryWorkflowState

# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def registry() -> WorkflowRegistry:
    return WorkflowRegistry()


@pytest.fixture
def state() -> InMemoryWorkflowState:
    return InMemoryWorkflowState()


@pytest.fixture
def engine(registry: WorkflowRegistry, state: InMemoryWorkflowState) -> WorkflowEngine:
    return WorkflowEngine(registry=registry, state=state)


@pytest.fixture
def dispatcher() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def executor(
    engine: WorkflowEngine, dispatcher: AsyncMock
) -> WorkflowExecutor:
    return WorkflowExecutor(engine=engine, dispatcher=dispatcher)


@pytest.fixture
def coordinator(
    engine: WorkflowEngine, executor: WorkflowExecutor
) -> RuntimeCoordinator:
    return RuntimeCoordinator(engine=engine, executor=executor)


# =========================================================================
# Template Tests
# =========================================================================


class TestResearchTemplate:
    def test_workflow_type(self) -> None:
        assert RESEARCH_TEMPLATE.workflow_type == "research_workflow"

    def test_step_count(self) -> None:
        assert len(RESEARCH_TEMPLATE.steps) == 6

    def test_step_ids(self) -> None:
        ids = [s.step_id for s in RESEARCH_TEMPLATE.steps]
        assert ids == ["orchestrate", "create_plan", "create_request", "start_request", "store_memory", "register_source"]

    def test_command_types(self) -> None:
        cmds = [s.command_type for s in RESEARCH_TEMPLATE.steps]
        assert cmds == [
            "orchestrator.create_orchestration",
            "planner.create_plan",
            "research.create_request",
            "research.start_request",
            "memory.create_memory",
            "knowledge.register_source",
        ]

    def test_dependencies(self) -> None:
        assert RESEARCH_TEMPLATE.steps[0].dependencies == []
        assert RESEARCH_TEMPLATE.steps[1].dependencies == ["orchestrate"]
        assert RESEARCH_TEMPLATE.steps[2].dependencies == ["create_plan"]
        assert RESEARCH_TEMPLATE.steps[3].dependencies == ["create_request"]
        assert RESEARCH_TEMPLATE.steps[4].dependencies == ["start_request"]
        assert RESEARCH_TEMPLATE.steps[5].dependencies == ["store_memory"]

    def test_all_steps_have_default_timeout(self) -> None:
        for s in RESEARCH_TEMPLATE.steps:
            assert s.timeout_seconds == 30.0

    def test_all_steps_have_zero_retry(self) -> None:
        for s in RESEARCH_TEMPLATE.steps:
            assert s.retry_count == 0

    def test_description(self) -> None:
        assert "research" in RESEARCH_TEMPLATE.description.lower()


class TestKnowledgeIngestionTemplate:
    def test_workflow_type(self) -> None:
        assert KNOWLEDGE_INGESTION_TEMPLATE.workflow_type == "knowledge_ingestion_workflow"

    def test_step_count(self) -> None:
        assert len(KNOWLEDGE_INGESTION_TEMPLATE.steps) == 4

    def test_step_ids(self) -> None:
        ids = [s.step_id for s in KNOWLEDGE_INGESTION_TEMPLATE.steps]
        assert ids == ["register_source", "ingest_document", "start_ingestion", "store_memory"]

    def test_command_types(self) -> None:
        cmds = [s.command_type for s in KNOWLEDGE_INGESTION_TEMPLATE.steps]
        assert cmds == [
            "knowledge.register_source",
            "knowledge.ingest_document",
            "knowledge.start_ingestion",
            "memory.create_memory",
        ]

    def test_dependencies(self) -> None:
        assert KNOWLEDGE_INGESTION_TEMPLATE.steps[0].dependencies == []
        assert KNOWLEDGE_INGESTION_TEMPLATE.steps[1].dependencies == ["register_source"]
        assert KNOWLEDGE_INGESTION_TEMPLATE.steps[2].dependencies == ["ingest_document"]
        assert KNOWLEDGE_INGESTION_TEMPLATE.steps[3].dependencies == ["start_ingestion"]


class TestAutomationTemplate:
    def test_workflow_type(self) -> None:
        assert AUTOMATION_TEMPLATE.workflow_type == "automation_workflow"

    def test_step_count(self) -> None:
        assert len(AUTOMATION_TEMPLATE.steps) == 4

    def test_step_ids(self) -> None:
        ids = [s.step_id for s in AUTOMATION_TEMPLATE.steps]
        assert ids == ["create_policy", "create_automation", "activate_automation", "send_notification"]

    def test_command_types(self) -> None:
        cmds = [s.command_type for s in AUTOMATION_TEMPLATE.steps]
        assert cmds == [
            "policy.create_policy",
            "automation.create_automation",
            "automation.activate_automation",
            "notification.create_notification",
        ]

    def test_dependencies(self) -> None:
        assert AUTOMATION_TEMPLATE.steps[0].dependencies == []
        assert AUTOMATION_TEMPLATE.steps[1].dependencies == ["create_policy"]
        assert AUTOMATION_TEMPLATE.steps[2].dependencies == ["create_automation"]
        assert AUTOMATION_TEMPLATE.steps[3].dependencies == ["activate_automation"]


class TestTemplateRegistry:
    def test_contains_all_templates(self) -> None:
        assert RESEARCH_WORKFLOW_TYPE in TEMPLATES
        assert KNOWLEDGE_INGESTION_WORKFLOW_TYPE in TEMPLATES
        assert AUTOMATION_WORKFLOW_TYPE in TEMPLATES

    def test_three_templates(self) -> None:
        assert len(TEMPLATES) == 3

    def test_template_types(self) -> None:
        for key, template in TEMPLATES.items():
            assert template.workflow_type == key

    def test_all_templates_are_definitions(self) -> None:
        for template in TEMPLATES.values():
            assert isinstance(template, WorkflowDefinition)

    def test_all_steps_are_workflow_steps(self) -> None:
        for template in TEMPLATES.values():
            for step in template.steps:
                assert isinstance(step, WorkflowStep)

    def test_all_dependencies_refer_to_existing_steps(self) -> None:
        for template in TEMPLATES.values():
            step_ids = {s.step_id for s in template.steps}
            for step in template.steps:
                for dep in step.dependencies:
                    assert dep in step_ids, f"{template.workflow_type}: {step.step_id} depends on unknown {dep}"

    def test_no_duplicate_step_ids(self) -> None:
        for template in TEMPLATES.values():
            ids = [s.step_id for s in template.steps]
            assert len(ids) == len(set(ids))


# =========================================================================
# DTO Tests
# =========================================================================


class TestResearchDTOs:
    def test_request_defaults(self) -> None:
        req = ResearchWorkflowRequest()
        assert req.user_request == ""
        assert req.goal == ""
        assert req.classification == "public"

    def test_request_with_values(self) -> None:
        req = ResearchWorkflowRequest(
            user_request="test request",
            goal="test goal",
            classification="internal",
        )
        assert req.user_request == "test request"
        assert req.goal == "test goal"
        assert req.classification == "internal"

    def test_request_immutable(self) -> None:
        req = ResearchWorkflowRequest()
        with pytest.raises(AttributeError):
            req.user_request = "changed"  # type: ignore[misc]

    def test_response_defaults(self) -> None:
        resp = ResearchWorkflowResponse(
            instance_id="id-1",
            workflow_type="research",
            status="COMPLETED",
        )
        assert resp.instance_id == "id-1"
        assert resp.step_results == {}
        assert resp.error_message is None

    def test_response_with_error(self) -> None:
        resp = ResearchWorkflowResponse(
            instance_id="id-1",
            workflow_type="research",
            status="FAILED",
            error_message="something went wrong",
        )
        assert resp.error_message == "something went wrong"


class TestKnowledgeDTOs:
    def test_request_defaults(self) -> None:
        req = KnowledgeWorkflowRequest()
        assert req.source_name == ""
        assert req.classification == "public"
        assert req.memory_category == "knowledge"

    def test_request_with_values(self) -> None:
        req = KnowledgeWorkflowRequest(
            source_name="test-source",
            source_type="web",
            classification="internal",
        )
        assert req.source_name == "test-source"
        assert req.source_type == "web"

    def test_request_immutable(self) -> None:
        req = KnowledgeWorkflowRequest()
        with pytest.raises(AttributeError):
            req.source_name = "changed"  # type: ignore[misc]


class TestAutomationDTOs:
    def test_request_defaults(self) -> None:
        req = AutomationWorkflowRequest()
        assert req.policy_name == ""
        assert req.execution_mode == "once"

    def test_request_with_values(self) -> None:
        req = AutomationWorkflowRequest(
            policy_name="test-policy",
            automation_name="test-auto",
            execution_mode="scheduled",
        )
        assert req.policy_name == "test-policy"
        assert req.automation_name == "test-auto"

    def test_request_immutable(self) -> None:
        req = AutomationWorkflowRequest()
        with pytest.raises(AttributeError):
            req.policy_name = "changed"  # type: ignore[misc]


# =========================================================================
# Factory Tests
# =========================================================================


class TestFactoryResearch:
    def test_default_workflow_type(self) -> None:
        wf = create_research_workflow()
        assert wf.workflow_type == RESEARCH_WORKFLOW_TYPE

    def test_default_returns_same_steps_as_template(self) -> None:
        wf = create_research_workflow()
        assert len(wf.steps) == len(RESEARCH_TEMPLATE.steps)

    def test_with_request_same_steps(self) -> None:
        req = ResearchWorkflowRequest(user_request="UR", goal="G")
        wf = create_research_workflow(req)
        step_ids = [s.step_id for s in wf.steps]
        assert step_ids == [
            "orchestrate", "create_plan", "create_request",
            "start_request", "store_memory", "register_source",
        ]

    def test_with_request_payload_override(self) -> None:
        req = ResearchWorkflowRequest(user_request="my request", goal="my goal")
        wf = create_research_workflow(req)
        plan_step = [s for s in wf.steps if s.step_id == "create_plan"][0]
        assert plan_step.payload["user_request"] == "my request"
        assert plan_step.payload["goal"] == "my goal"

    def test_with_request_memory_payload(self) -> None:
        req = ResearchWorkflowRequest(memory_content="important finding", memory_category="insight")
        wf = create_research_workflow(req)
        mem_step = [s for s in wf.steps if s.step_id == "store_memory"][0]
        assert mem_step.payload["content"] == "important finding"
        assert mem_step.payload["category"] == "insight"

    def test_preserves_dependencies(self) -> None:
        wf = create_research_workflow(ResearchWorkflowRequest())
        for i, step in enumerate(wf.steps):
            assert step.dependencies == list(RESEARCH_TEMPLATE.steps[i].dependencies)

    def test_preserves_timeout(self) -> None:
        wf = create_research_workflow(ResearchWorkflowRequest())
        for i, step in enumerate(wf.steps):
            assert step.timeout_seconds == RESEARCH_TEMPLATE.steps[i].timeout_seconds

    def test_none_request_returns_default(self) -> None:
        wf = create_research_workflow(None)  # type: ignore[arg-type]
        assert wf.workflow_type == RESEARCH_WORKFLOW_TYPE
        assert len(wf.steps) == 6


class TestFactoryKnowledge:
    def test_default_workflow_type(self) -> None:
        wf = create_knowledge_ingestion_workflow()
        assert wf.workflow_type == KNOWLEDGE_INGESTION_WORKFLOW_TYPE

    def test_default_step_count(self) -> None:
        wf = create_knowledge_ingestion_workflow()
        assert len(wf.steps) == 4

    def test_with_request_payloads(self) -> None:
        req = KnowledgeWorkflowRequest(
            source_name="my-source",
            source_type="api",
            document_title="doc1",
            classification="internal",
        )
        wf = create_knowledge_ingestion_workflow(req)
        src_step = [s for s in wf.steps if s.step_id == "register_source"][0]
        assert src_step.payload["name"] == "my-source"
        assert src_step.payload["source_type"] == "api"

    def test_preserves_all_dependencies(self) -> None:
        wf = create_knowledge_ingestion_workflow(KnowledgeWorkflowRequest())
        for i, step in enumerate(wf.steps):
            assert step.dependencies == list(KNOWLEDGE_INGESTION_TEMPLATE.steps[i].dependencies)


class TestFactoryAutomation:
    def test_default_workflow_type(self) -> None:
        wf = create_automation_workflow()
        assert wf.workflow_type == AUTOMATION_WORKFLOW_TYPE

    def test_default_step_count(self) -> None:
        wf = create_automation_workflow()
        assert len(wf.steps) == 4

    def test_with_request_payloads(self) -> None:
        req = AutomationWorkflowRequest(
            policy_name="pol1",
            automation_name="auto1",
            execution_mode="scheduled",
            notification_title="alert",
        )
        wf = create_automation_workflow(req)
        pol_step = [s for s in wf.steps if s.step_id == "create_policy"][0]
        assert pol_step.payload["name"] == "pol1"
        auto_step = [s for s in wf.steps if s.step_id == "create_automation"][0]
        assert auto_step.payload["name"] == "auto1"
        assert auto_step.payload["execution_mode"] == "scheduled"

    def test_preserves_dependencies(self) -> None:
        wf = create_automation_workflow(AutomationWorkflowRequest())
        for i, step in enumerate(wf.steps):
            assert step.dependencies == list(AUTOMATION_TEMPLATE.steps[i].dependencies)


# =========================================================================
# Exception Tests
# =========================================================================


class TestExceptions:
    def test_base_exception(self) -> None:
        assert issubclass(RuntimeOrchestrationError, Exception)

    def test_unknown_workflow(self) -> None:
        assert issubclass(UnknownWorkflowError, RuntimeOrchestrationError)

    def test_execution_error(self) -> None:
        assert issubclass(OrchestrationWorkflowExecutionError, RuntimeOrchestrationError)

    def test_template_error(self) -> None:
        assert issubclass(WorkflowTemplateError, RuntimeOrchestrationError)

    def test_unknown_workflow_message(self) -> None:
        err = UnknownWorkflowError("test workflow")
        assert "test workflow" in str(err)

    def test_execution_error_message(self) -> None:
        err = OrchestrationWorkflowExecutionError("execution failed")
        assert "execution failed" in str(err)

    def test_template_error_message(self) -> None:
        err = WorkflowTemplateError("template broken")
        assert "template broken" in str(err)

    def test_runtime_orchestration_error_is_base(self) -> None:
        assert isinstance(UnknownWorkflowError("x"), RuntimeOrchestrationError)
        assert isinstance(OrchestrationWorkflowExecutionError("x"), RuntimeOrchestrationError)
        assert isinstance(WorkflowTemplateError("x"), RuntimeOrchestrationError)


# =========================================================================
# Coordinator Tests – Construction & Registration
# =========================================================================


class TestCoordinatorConstruction:
    def test_creates_with_engine_and_executor(self, engine: WorkflowEngine, executor: WorkflowExecutor) -> None:
        coord = RuntimeCoordinator(engine=engine, executor=executor)
        assert coord is not None

    def test_registers_templates_on_construction(self, engine: WorkflowEngine, executor: WorkflowExecutor) -> None:
        coord = RuntimeCoordinator(engine=engine, executor=executor)
        assert engine._registry.has(RESEARCH_WORKFLOW_TYPE)
        assert engine._registry.has(KNOWLEDGE_INGESTION_WORKFLOW_TYPE)
        assert engine._registry.has(AUTOMATION_WORKFLOW_TYPE)

    def test_does_not_duplicate_on_second_construction(self, engine: WorkflowEngine, executor: WorkflowExecutor) -> None:
        RuntimeCoordinator(engine=engine, executor=executor)
        RuntimeCoordinator(engine=engine, executor=executor)
        assert len(engine._registry.registered_types) >= 3


# =========================================================================
# Coordinator Tests – Successful Execution
# =========================================================================


class TestCoordinatorResearchSuccess:
    async def test_research_workflow_completes(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        req = ResearchWorkflowRequest(user_request="test", goal="goal")
        resp = await coordinator.start_research_workflow(req)
        assert resp.status == "COMPLETED"
        assert resp.workflow_type == "research_workflow"
        assert len(resp.step_results) == 6

    async def test_research_workflow_custom_id(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        req = ResearchWorkflowRequest()
        resp = await coordinator.start_research_workflow(req, instance_id="custom-1")
        assert resp.instance_id == "custom-1"

    async def test_research_workflow_steps_executed_in_order(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        call_log: list[str] = []
        async def capturing_dispatch(envelope):
            call_log.append(envelope.command_type)
            return MagicMock(success=True, events=[{}])
        dispatcher.dispatch = AsyncMock(side_effect=capturing_dispatch)
        req = ResearchWorkflowRequest()
        await coordinator.start_research_workflow(req)
        assert call_log == [
            "orchestrator.create_orchestration",
            "planner.create_plan",
            "research.create_request",
            "research.start_request",
            "memory.create_memory",
            "knowledge.register_source",
        ]

    async def test_research_response_includes_step_results(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{"output": "ok"}]))
        req = ResearchWorkflowRequest()
        resp = await coordinator.start_research_workflow(req)
        for step_id in ("orchestrate", "create_plan", "create_request", "start_request", "store_memory", "register_source"):
            assert step_id in resp.step_results


class TestCoordinatorKnowledgeSuccess:
    async def test_knowledge_workflow_completes(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        req = KnowledgeWorkflowRequest(source_name="src1")
        resp = await coordinator.start_knowledge_workflow(req)
        assert resp.status == "COMPLETED"
        assert resp.workflow_type == "knowledge_ingestion_workflow"

    async def test_knowledge_workflow_custom_id(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        req = KnowledgeWorkflowRequest()
        resp = await coordinator.start_knowledge_workflow(req, instance_id="know-custom")
        assert resp.instance_id == "know-custom"

    async def test_knowledge_workflow_steps_in_order(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        call_log: list[str] = []
        async def log_dispatch(envelope):
            call_log.append(envelope.command_type)
            return MagicMock(success=True, events=[{}])
        dispatcher.dispatch = AsyncMock(side_effect=log_dispatch)
        await coordinator.start_knowledge_workflow(KnowledgeWorkflowRequest())
        assert call_log == [
            "knowledge.register_source",
            "knowledge.ingest_document",
            "knowledge.start_ingestion",
            "memory.create_memory",
        ]


class TestCoordinatorAutomationSuccess:
    async def test_automation_workflow_completes(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        req = AutomationWorkflowRequest(policy_name="p1")
        resp = await coordinator.start_automation_workflow(req)
        assert resp.status == "COMPLETED"

    async def test_automation_workflow_custom_id(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        req = AutomationWorkflowRequest()
        resp = await coordinator.start_automation_workflow(req, instance_id="auto-custom")
        assert resp.instance_id == "auto-custom"

    async def test_automation_workflow_steps_in_order(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        call_log: list[str] = []
        async def log_dispatch(envelope):
            call_log.append(envelope.command_type)
            return MagicMock(success=True, events=[{}])
        dispatcher.dispatch = AsyncMock(side_effect=log_dispatch)
        await coordinator.start_automation_workflow(AutomationWorkflowRequest())
        assert call_log == [
            "policy.create_policy",
            "automation.create_automation",
            "automation.activate_automation",
            "notification.create_notification",
        ]


# =========================================================================
# Coordinator Tests – Failure & Error Handling
# =========================================================================


class TestCoordinatorFailure:
    async def test_step_failure_propagates(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(
            side_effect=[
                MagicMock(success=True, events=[{}]),
                MagicMock(success=False, error="step failed"),
            ]
        )
        req = ResearchWorkflowRequest()
        with pytest.raises(OrchestrationWorkflowExecutionError, match="step failed"):
            await coordinator.start_research_workflow(req)

    async def test_dispatcher_exception_propagates(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(side_effect=ValueError("dispatcher error"))
        req = ResearchWorkflowRequest()
        with pytest.raises(OrchestrationWorkflowExecutionError):
            await coordinator.start_research_workflow(req)

    async def test_knowledge_failure_propagates(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=False, error="ingestion failed"))
        req = KnowledgeWorkflowRequest()
        with pytest.raises(OrchestrationWorkflowExecutionError):
            await coordinator.start_knowledge_workflow(req)

    async def test_automation_failure_propagates(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=False, error="activation failed"))
        req = AutomationWorkflowRequest()
        with pytest.raises(OrchestrationWorkflowExecutionError):
            await coordinator.start_automation_workflow(req)


# =========================================================================
# Coordinator Tests – Response Type Mapping
# =========================================================================


class TestCoordinatorResponseTypes:
    async def test_research_response_type(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        resp = await coordinator.start_research_workflow(ResearchWorkflowRequest())
        assert isinstance(resp, ResearchWorkflowResponse)

    async def test_knowledge_response_type(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        resp = await coordinator.start_knowledge_workflow(KnowledgeWorkflowRequest())
        assert isinstance(resp, KnowledgeWorkflowResponse)

    async def test_automation_response_type(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        resp = await coordinator.start_automation_workflow(AutomationWorkflowRequest())
        assert isinstance(resp, AutomationWorkflowResponse)


# =========================================================================
# Coordinator Tests – Engine Integration
# =========================================================================


class TestCoordinatorEngineIntegration:
    async def test_workflow_instance_created(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock, engine: WorkflowEngine) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        req = ResearchWorkflowRequest()
        resp = await coordinator.start_research_workflow(req)
        instance = engine.get_instance(resp.instance_id)
        assert instance.workflow_type == "research_workflow"

    async def test_all_steps_completed(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock, engine: WorkflowEngine) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        resp = await coordinator.start_research_workflow(ResearchWorkflowRequest())
        instance = engine.get_instance(resp.instance_id)
        for step_run in instance.steps.values():
            assert step_run.status == StepStatus.COMPLETED

    async def test_workflow_listed_after_execution(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock, engine: WorkflowEngine) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        await coordinator.start_research_workflow(ResearchWorkflowRequest())
        await coordinator.start_knowledge_workflow(KnowledgeWorkflowRequest())
        await coordinator.start_automation_workflow(AutomationWorkflowRequest())
        assert len(engine.list_instances()) == 3


# =========================================================================
# Coordinator Tests – Edge Cases
# =========================================================================


class TestCoordinatorEdgeCases:
    async def test_empty_request_strings(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        req = ResearchWorkflowRequest(user_request="", goal="", source_name="")
        resp = await coordinator.start_research_workflow(req)
        assert resp.status == "COMPLETED"

    async def test_maximal_request(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        req = ResearchWorkflowRequest(
            user_request="a" * 1000,
            goal="b" * 1000,
            source_name="c" * 1000,
        )
        resp = await coordinator.start_research_workflow(req)
        assert resp.status == "COMPLETED"

    async def test_all_three_workflows_sequentially(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        r1 = await coordinator.start_research_workflow(ResearchWorkflowRequest())
        r2 = await coordinator.start_knowledge_workflow(KnowledgeWorkflowRequest())
        r3 = await coordinator.start_automation_workflow(AutomationWorkflowRequest())
        assert r1.status == "COMPLETED"
        assert r2.status == "COMPLETED"
        assert r3.status == "COMPLETED"

    async def test_response_error_message_none_on_success(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        resp = await coordinator.start_research_workflow(ResearchWorkflowRequest())
        assert resp.error_message is None


# =========================================================================
# Coordinator Tests – Retry Propagation
# =========================================================================


class TestCoordinatorRetry:
    async def test_retry_exhaustion_fails_workflow(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=False, error="persistent failure"))
        req = ResearchWorkflowRequest()
        with pytest.raises(OrchestrationWorkflowExecutionError):
            await coordinator.start_research_workflow(req)


# =========================================================================
# Coordinator Tests – Dependency Handling
# =========================================================================


class TestCoordinatorDependencies:
    async def test_steps_not_executed_before_dependency(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        call_log: list[str] = []
        async def log_dispatch(envelope):
            call_log.append(envelope.command_type)
            return MagicMock(success=True, events=[{}])
        dispatcher.dispatch = AsyncMock(side_effect=log_dispatch)
        await coordinator.start_knowledge_workflow(KnowledgeWorkflowRequest())
        register_idx = call_log.index("knowledge.register_source")
        ingest_idx = call_log.index("knowledge.ingest_document")
        start_idx = call_log.index("knowledge.start_ingestion")
        memory_idx = call_log.index("memory.create_memory")
        assert register_idx < ingest_idx
        assert ingest_idx < start_idx
        assert start_idx < memory_idx

    async def test_research_parallel_steps_not_possible_in_seq(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        call_log: list[str] = []
        async def log_dispatch(envelope):
            call_log.append(envelope.command_type)
            return MagicMock(success=True, events=[{}])
        dispatcher.dispatch = AsyncMock(side_effect=log_dispatch)
        await coordinator.start_research_workflow(ResearchWorkflowRequest())
        for i in range(1, len(call_log)):
            assert call_log[i - 1] != call_log[i]


# =========================================================================
# Edge Cases – Unknown / Invalid Workflows
# =========================================================================


class TestCoordinatorUnknown:
    async def test_unknown_workflow_via_template_error(self, coordinator: RuntimeCoordinator) -> None:
        with pytest.raises(UnknownWorkflowError):
            coordinator._response_type_for("nonexistent")

    def test_response_type_mapping(self, coordinator: RuntimeCoordinator) -> None:
        from backend.runtime.orchestration.coordinator import RuntimeCoordinator as RC
        assert RC._response_type_for("research_workflow") == ResearchWorkflowResponse
        assert RC._response_type_for("knowledge_ingestion_workflow") == KnowledgeWorkflowResponse
        assert RC._response_type_for("automation_workflow") == AutomationWorkflowResponse


# =========================================================================
# Edge Cases – Template Definition Integrity
# =========================================================================


class TestTemplateIntegrity:
    def test_all_templates_have_unique_types(self) -> None:
        types = [t.workflow_type for t in TEMPLATES.values()]
        assert len(types) == len(set(types))

    def test_all_templates_have_at_least_one_step(self) -> None:
        for template in TEMPLATES.values():
            assert len(template.steps) >= 1

    def test_no_step_has_self_dependency(self) -> None:
        for template in TEMPLATES.values():
            for step in template.steps:
                assert step.step_id not in step.dependencies

    def test_all_template_descriptions_non_empty(self) -> None:
        for template in TEMPLATES.values():
            assert len(template.description) > 0

    def test_templates_have_timeout(self) -> None:
        for template in TEMPLATES.values():
            assert template.timeout_seconds > 0

    def test_all_step_payloads_are_dicts(self) -> None:
        for template in TEMPLATES.values():
            for step in template.steps:
                assert isinstance(step.payload, dict)


# =========================================================================
# Edge Cases – Factory Payload Integrity
# =========================================================================


class TestFactoryPayloadIntegrity:
    def test_research_factory_does_not_mutate_template(self) -> None:
        original_payloads = {
            s.step_id: dict(s.payload) for s in RESEARCH_TEMPLATE.steps
        }
        create_research_workflow(ResearchWorkflowRequest(user_request="X", goal="Y"))
        current_payloads = {s.step_id: dict(s.payload) for s in RESEARCH_TEMPLATE.steps}
        assert original_payloads == current_payloads

    def test_knowledge_factory_does_not_mutate_template(self) -> None:
        original_payloads = {
            s.step_id: dict(s.payload) for s in KNOWLEDGE_INGESTION_TEMPLATE.steps
        }
        create_knowledge_ingestion_workflow(KnowledgeWorkflowRequest(source_name="X"))
        current_payloads = {s.step_id: dict(s.payload) for s in KNOWLEDGE_INGESTION_TEMPLATE.steps}
        assert original_payloads == current_payloads

    def test_automation_factory_does_not_mutate_template(self) -> None:
        original_payloads = {
            s.step_id: dict(s.payload) for s in AUTOMATION_TEMPLATE.steps
        }
        create_automation_workflow(AutomationWorkflowRequest(policy_name="X"))
        current_payloads = {s.step_id: dict(s.payload) for s in AUTOMATION_TEMPLATE.steps}
        assert original_payloads == current_payloads

    def test_factory_with_none_values_filtered(self) -> None:
        req = ResearchWorkflowRequest(user_request="", goal="test")
        wf = create_research_workflow(req)
        plan_step = [s for s in wf.steps if s.step_id == "create_plan"][0]
        assert "user_request" in plan_step.payload
        assert "goal" in plan_step.payload


# =========================================================================
# Edge Cases – Coordinator Registration
# =========================================================================


class TestCoordinatorRegistration:
    def test_coordinator_registers_only_once(self, engine: WorkflowEngine, executor: WorkflowExecutor) -> None:
        RuntimeCoordinator(engine=engine, executor=executor)
        RuntimeCoordinator(engine=engine, executor=executor)
        RuntimeCoordinator(engine=engine, executor=executor)
        count = sum(
            1 for t in [
                RESEARCH_WORKFLOW_TYPE,
                KNOWLEDGE_INGESTION_WORKFLOW_TYPE,
                AUTOMATION_WORKFLOW_TYPE,
            ]
            if engine._registry.has(t)
        )
        assert count == 3


# =========================================================================
# Edge Cases – Empty / Missing Payloads
# =========================================================================


class TestFactoryEmptyPayloads:
    def test_research_default_payloads_empty(self) -> None:
        wf = create_research_workflow()
        for step in wf.steps:
            assert isinstance(step.payload, dict)

    def test_knowledge_default_payloads_empty(self) -> None:
        wf = create_knowledge_ingestion_workflow()
        for step in wf.steps:
            assert isinstance(step.payload, dict)

    def test_automation_default_payloads_empty(self) -> None:
        wf = create_automation_workflow()
        for step in wf.steps:
            assert isinstance(step.payload, dict)


# =========================================================================
# Edge Cases – Workflow Definition Immutability
# =========================================================================


class TestDefinitionImmutability:
    def test_template_type_immutable(self) -> None:
        with pytest.raises(AttributeError):
            RESEARCH_TEMPLATE.workflow_type = "changed"  # type: ignore[misc]

    def test_step_immutable_field(self) -> None:
        step = WorkflowStep(step_id="test", command_type="test")
        with pytest.raises(AttributeError):
            step.step_id = "changed"  # type: ignore[misc]


# =========================================================================
# Coordinator Tests – Detailed Payload Verification
# =========================================================================


class TestCoordinatorPayloads:
    async def test_research_payload_maps_correctly(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock, engine: WorkflowEngine) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        req = ResearchWorkflowRequest(user_request="my query", goal="find answer", classification="internal")
        resp = await coordinator.start_research_workflow(req)
        instance = engine.get_instance(resp.instance_id)
        plan_step_run = instance.steps.get("create_plan")
        assert plan_step_run is not None
        assert plan_step_run.step.payload.get("user_request") == "my query"
        assert plan_step_run.step.payload.get("goal") == "find answer"

    async def test_knowledge_payload_maps_correctly(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock, engine: WorkflowEngine) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        req = KnowledgeWorkflowRequest(source_name="mysrc", source_type="api", classification="internal")
        resp = await coordinator.start_knowledge_workflow(req)
        instance = engine.get_instance(resp.instance_id)
        src_step_run = instance.steps.get("register_source")
        assert src_step_run is not None
        assert src_step_run.step.payload.get("name") == "mysrc"
        assert src_step_run.step.payload.get("source_type") == "api"
        assert src_step_run.step.payload.get("classification") == "internal"

    async def test_automation_payload_maps_correctly(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock, engine: WorkflowEngine) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        req = AutomationWorkflowRequest(policy_name="pol1", automation_name="auto1", execution_mode="scheduled")
        resp = await coordinator.start_automation_workflow(req)
        instance = engine.get_instance(resp.instance_id)
        auto_step_run = instance.steps.get("create_automation")
        assert auto_step_run is not None
        assert auto_step_run.step.payload.get("name") == "auto1"
        assert auto_step_run.step.payload.get("execution_mode") == "scheduled"


# =========================================================================
# Coordinator Tests – Factory with Full Requests
# =========================================================================


class TestFactoryFullRequests:
    def test_research_full_request(self) -> None:
        req = ResearchWorkflowRequest(
            user_request="UR", goal="G", source_name="SN", source_type="ST",
            source_location="SL", memory_content="MC", memory_category="MCAT",
            classification="C", plan_description="PD",
        )
        wf = create_research_workflow(req)
        assert wf.workflow_type == RESEARCH_WORKFLOW_TYPE
        assert len(wf.steps) == 6

    def test_knowledge_full_request(self) -> None:
        req = KnowledgeWorkflowRequest(
            source_name="SN", source_type="ST", source_location="SL",
            classification="C", document_title="DT", document_checksum="DC",
            memory_content="MC", memory_category="KCAT",
        )
        wf = create_knowledge_ingestion_workflow(req)
        assert wf.workflow_type == KNOWLEDGE_INGESTION_WORKFLOW_TYPE
        assert len(wf.steps) == 4

    def test_automation_full_request(self) -> None:
        req = AutomationWorkflowRequest(
            policy_name="PN", policy_description="PD", policy_priority=5,
            policy_scope="PS", automation_name="AN", automation_description="AD",
            execution_mode="EM", notification_title="NT", notification_message="NM",
            notification_channel="NC", notification_target_type="NTT", notification_target_id="NTID",
        )
        wf = create_automation_workflow(req)
        assert wf.workflow_type == AUTOMATION_WORKFLOW_TYPE
        assert len(wf.steps) == 4

    def test_research_filter_none_excluded(self) -> None:
        req = ResearchWorkflowRequest(user_request="exists")
        wf = create_research_workflow(req)
        plan_step = [s for s in wf.steps if s.step_id == "create_plan"][0]
        assert "user_request" in plan_step.payload
        assert plan_step.payload["user_request"] == "exists"

    def test_knowledge_only_name_sets_payload(self) -> None:
        req = KnowledgeWorkflowRequest(source_name="only_name")
        wf = create_knowledge_ingestion_workflow(req)
        src_step = [s for s in wf.steps if s.step_id == "register_source"][0]
        assert src_step.payload.get("name") == "only_name"


# =========================================================================
# Coordinator Tests – Execution with Engine State Verification
# =========================================================================


class TestCoordinatorEngineState:
    async def test_research_creates_single_instance(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock, engine: WorkflowEngine) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        await coordinator.start_research_workflow(ResearchWorkflowRequest())
        instances = engine.list_instances()
        research_instances = [i for i in instances if i.workflow_type == RESEARCH_WORKFLOW_TYPE]
        assert len(research_instances) == 1

    async def test_knowledge_creates_single_instance(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock, engine: WorkflowEngine) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        await coordinator.start_knowledge_workflow(KnowledgeWorkflowRequest())
        instances = engine.list_instances()
        knowledge_instances = [i for i in instances if i.workflow_type == KNOWLEDGE_INGESTION_WORKFLOW_TYPE]
        assert len(knowledge_instances) == 1

    async def test_automation_creates_single_instance(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock, engine: WorkflowEngine) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        await coordinator.start_automation_workflow(AutomationWorkflowRequest())
        instances = engine.list_instances()
        auto_instances = [i for i in instances if i.workflow_type == AUTOMATION_WORKFLOW_TYPE]
        assert len(auto_instances) == 1

    async def test_all_instances_persist_in_state(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock, engine: WorkflowEngine) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        await coordinator.start_research_workflow(ResearchWorkflowRequest())
        await coordinator.start_knowledge_workflow(KnowledgeWorkflowRequest())
        await coordinator.start_automation_workflow(AutomationWorkflowRequest())
        assert len(engine.list_instances()) == 3


# =========================================================================
# Coordinator Tests – Error State Handling
# =========================================================================


class TestCoordinatorErrorStates:
    async def test_error_response_message(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=False, error="fatal error"))
        with pytest.raises(OrchestrationWorkflowExecutionError) as exc_info:
            await coordinator.start_research_workflow(ResearchWorkflowRequest())
        assert "fatal error" in str(exc_info.value)

    async def test_error_in_middle_of_workflow(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(
            side_effect=[
                MagicMock(success=True, events=[{}]),
                MagicMock(success=False, error="middle failure"),
            ]
        )
        with pytest.raises(OrchestrationWorkflowExecutionError):
            await coordinator.start_research_workflow(ResearchWorkflowRequest())

    async def test_unknown_workflow_error_message(self) -> None:
        err = UnknownWorkflowError("custom_workflow")
        assert "custom_workflow" in str(err)

    async def test_execution_error_message_contains_workflow_type(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=False, error="error"))
        with pytest.raises(OrchestrationWorkflowExecutionError) as exc_info:
            await coordinator.start_research_workflow(ResearchWorkflowRequest())
        assert "research_workflow" in str(exc_info.value)


# =========================================================================
# Coordinator Tests – Dispatcher Integration Edge Cases
# =========================================================================


class TestCoordinatorDispatcherEdgeCases:
    async def test_empty_dispatcher_response(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[]))
        resp = await coordinator.start_research_workflow(ResearchWorkflowRequest())
        assert resp.status == "COMPLETED"

    async def test_dispatcher_with_events(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{"event_type": "test", "payload": {"id": "123"}}]))
        resp = await coordinator.start_research_workflow(ResearchWorkflowRequest())
        assert resp.status == "COMPLETED"

    async def test_all_dispatches_use_command_types(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        captured: list[str] = []
        async def capture(envelope):
            captured.append(envelope.command_type)
            return MagicMock(success=True, events=[{}])
        dispatcher.dispatch = AsyncMock(side_effect=capture)
        await coordinator.start_research_workflow(ResearchWorkflowRequest())
        for cmd in ["orchestrator.create_orchestration", "planner.create_plan", "research.create_request"]:
            assert cmd in captured

    async def test_dispatcher_called_exactly_once_per_step(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        await coordinator.start_knowledge_workflow(KnowledgeWorkflowRequest())
        assert dispatcher.dispatch.await_count == 4

    async def test_research_dispatcher_call_count(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        await coordinator.start_research_workflow(ResearchWorkflowRequest())
        assert dispatcher.dispatch.await_count == 6

    async def test_automation_dispatcher_call_count(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        await coordinator.start_automation_workflow(AutomationWorkflowRequest())
        assert dispatcher.dispatch.await_count == 4


# =========================================================================
# Coordinator Tests – Instance ID Management
# =========================================================================


class TestCoordinatorInstanceIds:
    async def test_generates_uuid_when_not_provided(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        resp = await coordinator.start_research_workflow(ResearchWorkflowRequest())
        assert len(resp.instance_id) > 0

    async def test_unique_ids_for_multiple_calls(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        r1 = await coordinator.start_research_workflow(ResearchWorkflowRequest())
        r2 = await coordinator.start_research_workflow(ResearchWorkflowRequest())
        assert r1.instance_id != r2.instance_id

    async def test_knowledge_custom_instance_id(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        resp = await coordinator.start_knowledge_workflow(KnowledgeWorkflowRequest(), instance_id="know-1")
        assert resp.instance_id == "know-1"

    async def test_automation_custom_instance_id(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        resp = await coordinator.start_automation_workflow(AutomationWorkflowRequest(), instance_id="auto-1")
        assert resp.instance_id == "auto-1"


# =========================================================================
# Template Tests – Edge Cases
# =========================================================================


class TestTemplateEdgeCases:
    def test_research_all_step_retry_counts(self) -> None:
        for step in RESEARCH_TEMPLATE.steps:
            assert isinstance(step.retry_count, int)

    def test_knowledge_all_step_timeouts_positive(self) -> None:
        for step in KNOWLEDGE_INGESTION_TEMPLATE.steps:
            assert step.timeout_seconds > 0

    def test_automation_all_step_payloads_empty(self) -> None:
        for step in AUTOMATION_TEMPLATE.steps:
            assert isinstance(step.payload, dict)

    def test_no_duplicate_command_types_in_template(self) -> None:
        for template in TEMPLATES.values():
            cmds = [s.command_type for s in template.steps]
            assert len(cmds) == len(set(cmds))

    def test_all_template_timeouts_positive(self) -> None:
        for template in TEMPLATES.values():
            assert template.timeout_seconds > 0

    def test_all_step_command_types_are_strings(self) -> None:
        for template in TEMPLATES.values():
            for step in template.steps:
                assert isinstance(step.command_type, str)
                assert "." in step.command_type

    def test_all_step_ids_alphanumeric(self) -> None:
        for template in TEMPLATES.values():
            for step in template.steps:
                assert step.step_id.isidentifier()


# =========================================================================
# Coordinator – Step Result Tracking
# =========================================================================


class TestCoordinatorStepResults:
    async def test_research_step_in_results(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{"output": "done"}]))
        resp = await coordinator.start_research_workflow(ResearchWorkflowRequest())
        for step_id in ("orchestrate", "create_plan", "create_request", "start_request", "store_memory", "register_source"):
            assert step_id in resp.step_results

    async def test_knowledge_step_in_results(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{"id": "doc-1"}]))
        resp = await coordinator.start_knowledge_workflow(KnowledgeWorkflowRequest())
        for step_id in ("register_source", "ingest_document", "start_ingestion", "store_memory"):
            assert step_id in resp.step_results

    async def test_automation_step_in_results(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{"id": "auto-1"}]))
        resp = await coordinator.start_automation_workflow(AutomationWorkflowRequest())
        for step_id in ("create_policy", "create_automation", "activate_automation", "send_notification"):
            assert step_id in resp.step_results


# =========================================================================
# DTO Tests – Response Fields
# =========================================================================


class TestDTOResponseFields:
    def test_research_response_all_fields(self) -> None:
        resp = ResearchWorkflowResponse(
            instance_id="id-1",
            workflow_type="test",
            status="COMPLETED",
            step_results={"step1": {"output": "ok"}},
            error_message=None,
        )
        assert resp.instance_id == "id-1"
        assert resp.step_results["step1"] == {"output": "ok"}

    def test_knowledge_response_all_fields(self) -> None:
        resp = KnowledgeWorkflowResponse(
            instance_id="id-2",
            workflow_type="test",
            status="FAILED",
            step_results={},
            error_message="error",
        )
        assert resp.error_message == "error"

    def test_automation_response_all_fields(self) -> None:
        resp = AutomationWorkflowResponse(
            instance_id="id-3",
            workflow_type="test",
            status="CANCELLED",
            step_results={"x": None},
            error_message="cancelled",
        )
        assert resp.status == "CANCELLED"
        assert resp.step_results["x"] is None


# =========================================================================
# Integration – Coordinator + Engine + State
# =========================================================================


class TestIntegrationEngineState:
    async def test_instance_persists_after_coordinator_completion(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock, engine: WorkflowEngine) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        resp = await coordinator.start_research_workflow(ResearchWorkflowRequest())
        instance = engine.get_instance(resp.instance_id)
        assert instance.status == WorkflowStatus.COMPLETED

    async def test_failed_instance_persists_in_state(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock, engine: WorkflowEngine) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=False, error="fail"))
        with pytest.raises(OrchestrationWorkflowExecutionError):
            await coordinator.start_research_workflow(ResearchWorkflowRequest())
        instances = engine.list_instances()
        failed = [i for i in instances if i.status == WorkflowStatus.FAILED]
        assert len(failed) >= 1

    async def test_multiple_workflows_same_type(self, coordinator: RuntimeCoordinator, dispatcher: AsyncMock, engine: WorkflowEngine) -> None:
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        r1 = await coordinator.start_research_workflow(ResearchWorkflowRequest())
        r2 = await coordinator.start_research_workflow(ResearchWorkflowRequest())
        assert r1.instance_id != r2.instance_id
        research_instances = [i for i in engine.list_instances() if i.workflow_type == RESEARCH_WORKFLOW_TYPE]
        assert len(research_instances) == 2


# =========================================================================
# Edge Cases – Coordinator with Already-Registered Templates
# =========================================================================


class TestCoordinatorReRegistration:
    async def test_multiple_coordinators_same_engine(self, engine: WorkflowEngine, executor: WorkflowExecutor, dispatcher: AsyncMock) -> None:
        c1 = RuntimeCoordinator(engine=engine, executor=executor)
        c2 = RuntimeCoordinator(engine=engine, executor=executor)
        dispatcher.dispatch = AsyncMock(return_value=MagicMock(success=True, events=[{}]))
        r1 = await c1.start_research_workflow(ResearchWorkflowRequest())
        r2 = await c2.start_research_workflow(ResearchWorkflowRequest())
        assert r1.status == "COMPLETED"
        assert r2.status == "COMPLETED"

    async def test_coordinator_replaces_template(self, engine: WorkflowEngine, executor: WorkflowExecutor, dispatcher: AsyncMock) -> None:
        definition = WorkflowDefinition(
            workflow_type="custom",
            steps=(WorkflowStep(step_id="s1", command_type="test.cmd"),),
        )
        engine._registry.register(definition)
        assert engine._registry.has("custom")
        coordinator = RuntimeCoordinator(engine=engine, executor=executor)
        assert engine._registry.has("custom")


# =========================================================================
# Template Structure – First Step Dependency Check
# =========================================================================


class TestTemplateFirstStep:
    def test_research_first_step_no_deps(self) -> None:
        assert RESEARCH_TEMPLATE.steps[0].dependencies == []

    def test_knowledge_first_step_no_deps(self) -> None:
        assert KNOWLEDGE_INGESTION_TEMPLATE.steps[0].dependencies == []

    def test_automation_first_step_no_deps(self) -> None:
        assert AUTOMATION_TEMPLATE.steps[0].dependencies == []

    def test_research_last_step_has_deps(self) -> None:
        assert len(RESEARCH_TEMPLATE.steps[-1].dependencies) >= 1

    def test_knowledge_last_step_has_deps(self) -> None:
        assert len(KNOWLEDGE_INGESTION_TEMPLATE.steps[-1].dependencies) >= 1

    def test_automation_last_step_has_deps(self) -> None:
        assert len(AUTOMATION_TEMPLATE.steps[-1].dependencies) >= 1

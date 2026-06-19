from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

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
    UnknownWorkflowError,
    WorkflowTemplateError,
)
from backend.runtime.orchestration.factory import (
    create_automation_workflow,
    create_knowledge_ingestion_workflow,
    create_research_workflow,
)
from backend.runtime.orchestration.templates import (
    AUTOMATION_WORKFLOW_TYPE,
    KNOWLEDGE_INGESTION_WORKFLOW_TYPE,
    RESEARCH_WORKFLOW_TYPE,
    TEMPLATES,
)
from backend.runtime.workflows.engine import WorkflowEngine
from backend.runtime.workflows.executor import WorkflowExecutor
from backend.runtime.workflows.models import WorkflowInstance, WorkflowStatus


class RuntimeCoordinator:
    """Accepts orchestration requests, selects workflow templates,
    submits them to the WorkflowEngine, tracks execution state,
    and returns results.
    """

    def __init__(
        self,
        engine: WorkflowEngine,
        executor: WorkflowExecutor,
    ) -> None:
        self._engine = engine
        self._executor = executor
        self._register_templates()

    def _register_templates(self) -> None:
        """Register all orchestration templates with the engine's registry."""
        for definition in TEMPLATES.values():
            if self._engine._registry.has(definition.workflow_type):
                continue
            self._engine._registry.register(definition)

    # ------------------------------------------------------------------
    # Research
    # ------------------------------------------------------------------

    async def start_research_workflow(
        self,
        request: ResearchWorkflowRequest,
        *,
        instance_id: str | None = None,
    ) -> ResearchWorkflowResponse:
        """Start and execute a research workflow to completion."""
        definition = create_research_workflow(request)
        return await self._run_workflow(
            definition=definition,
            workflow_type=RESEARCH_WORKFLOW_TYPE,
            instance_id=instance_id,
        )

    # ------------------------------------------------------------------
    # Knowledge Ingestion
    # ------------------------------------------------------------------

    async def start_knowledge_workflow(
        self,
        request: KnowledgeWorkflowRequest,
        *,
        instance_id: str | None = None,
    ) -> KnowledgeWorkflowResponse:
        """Start and execute a knowledge ingestion workflow to completion."""
        definition = create_knowledge_ingestion_workflow(request)
        return await self._run_workflow(
            definition=definition,
            workflow_type=KNOWLEDGE_INGESTION_WORKFLOW_TYPE,
            instance_id=instance_id,
        )

    # ------------------------------------------------------------------
    # Automation
    # ------------------------------------------------------------------

    async def start_automation_workflow(
        self,
        request: AutomationWorkflowRequest,
        *,
        instance_id: str | None = None,
    ) -> AutomationWorkflowResponse:
        """Start and execute an automation workflow to completion."""
        definition = create_automation_workflow(request)
        return await self._run_workflow(
            definition=definition,
            workflow_type=AUTOMATION_WORKFLOW_TYPE,
            instance_id=instance_id,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _run_workflow(
        self,
        definition: Any,
        workflow_type: str,
        instance_id: str | None = None,
    ) -> Any:
        """Register the definition, start the workflow, execute it,
        and return the typed response."""
        try:
            self._engine._registry.register_or_replace(definition)

            inst = self._engine.start_workflow(
                workflow_type,
                instance_id=instance_id or str(uuid4()),
            )
            await self._executor.execute_workflow(inst.instance_id)
            instance = self._engine.get_instance(inst.instance_id)
            if instance.status == WorkflowStatus.FAILED:
                error_msg = instance.error_message or "Workflow failed"
                raise OrchestrationWorkflowExecutionError(
                    f"Workflow {workflow_type!r} failed: {error_msg}"
                )
            return self._build_response(instance)
        except OrchestrationWorkflowExecutionError:
            raise
        except Exception as exc:
            raise OrchestrationWorkflowExecutionError(
                f"Workflow {workflow_type!r} failed: {exc}"
            ) from exc

    def _build_response(
        self,
        instance: WorkflowInstance,
    ) -> Any:
        """Build a response DTO from a completed workflow instance."""
        step_results: dict[str, dict[str, Any] | None] = {}
        for step_id, step_run in instance.steps.items():
            step_results[step_id] = step_run.result

        resp_type = self._response_type_for(instance.workflow_type)
        return resp_type(
            instance_id=instance.instance_id,
            workflow_type=instance.workflow_type,
            status=instance.status.value,
            step_results=step_results,
            error_message=instance.error_message,
        )

    @staticmethod
    def _response_type_for(workflow_type: str) -> type:
        from backend.runtime.orchestration.dto import (
            AutomationWorkflowResponse,
            KnowledgeWorkflowResponse,
            ResearchWorkflowResponse,
        )
        mapping: dict[str, type] = {
            RESEARCH_WORKFLOW_TYPE: ResearchWorkflowResponse,
            KNOWLEDGE_INGESTION_WORKFLOW_TYPE: KnowledgeWorkflowResponse,
            AUTOMATION_WORKFLOW_TYPE: AutomationWorkflowResponse,
        }
        result = mapping.get(workflow_type)
        if result is None:
            raise UnknownWorkflowError(f"Unknown workflow type: {workflow_type!r}")
        return result

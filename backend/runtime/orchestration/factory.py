from __future__ import annotations

from backend.runtime.orchestration.dto import (
    AutomationWorkflowRequest,
    KnowledgeWorkflowRequest,
    ResearchWorkflowRequest,
)
from backend.runtime.orchestration.exceptions import WorkflowTemplateError
from backend.runtime.orchestration.templates import (
    AUTOMATION_TEMPLATE,
    AUTOMATION_WORKFLOW_TYPE,
    KNOWLEDGE_INGESTION_TEMPLATE,
    KNOWLEDGE_INGESTION_WORKFLOW_TYPE,
    RESEARCH_TEMPLATE,
    RESEARCH_WORKFLOW_TYPE,
)
from backend.runtime.workflows.models import WorkflowDefinition, WorkflowStep


def create_research_workflow(
    request: ResearchWorkflowRequest | None = None,
) -> WorkflowDefinition:
    """Create a research workflow definition with payload overrides."""
    if request is None:
        return RESEARCH_TEMPLATE
    return _build_definition(
        RESEARCH_TEMPLATE,
        payload_map={
            "orchestrate": _filter_none({
                "intent": request.user_request,
                "goal": request.goal,
            }),
            "create_plan": _filter_none({
                "user_request": request.user_request,
                "goal": request.goal,
                "description": request.plan_description,
            }),
            "create_request": _filter_none({
                "user_request": request.user_request,
                "goal": request.goal,
                "classification": request.classification,
            }),
            "start_request": {},
            "store_memory": _filter_none({
                "content": request.memory_content,
                "category": request.memory_category,
                "source": "research",
            }),
            "register_source": _filter_none({
                "name": request.source_name or "research-source",
                "source_type": request.source_type or "research",
                "location": request.source_location or "",
                "classification": request.classification,
            }),
        },
    )


def create_knowledge_ingestion_workflow(
    request: KnowledgeWorkflowRequest | None = None,
) -> WorkflowDefinition:
    """Create a knowledge ingestion workflow definition with payload overrides."""
    if request is None:
        return KNOWLEDGE_INGESTION_TEMPLATE
    return _build_definition(
        KNOWLEDGE_INGESTION_TEMPLATE,
        payload_map={
            "register_source": _filter_none({
                "name": request.source_name,
                "source_type": request.source_type,
                "location": request.source_location,
                "classification": request.classification,
            }),
            "ingest_document": _filter_none({
                "source_id": "",
                "title": request.document_title,
                "checksum": request.document_checksum,
                "classification": request.classification,
            }),
            "start_ingestion": _filter_none({
                "source_id": "",
            }),
            "store_memory": _filter_none({
                "content": request.memory_content,
                "category": request.memory_category,
                "source": "knowledge",
            }),
        },
    )


def create_automation_workflow(
    request: AutomationWorkflowRequest | None = None,
) -> WorkflowDefinition:
    """Create an automation workflow definition with payload overrides."""
    if request is None:
        return AUTOMATION_TEMPLATE
    return _build_definition(
        AUTOMATION_TEMPLATE,
        payload_map={
            "create_policy": _filter_none({
                "name": request.policy_name,
                "description": request.policy_description,
                "priority": request.policy_priority,
                "scope": request.policy_scope,
            }),
            "create_automation": _filter_none({
                "name": request.automation_name,
                "description": request.automation_description,
                "execution_mode": request.execution_mode,
            }),
            "activate_automation": _filter_none({
                "automation_id": "",
            }),
            "send_notification": _filter_none({
                "title": request.notification_title,
                "message": request.notification_message,
                "channel": request.notification_channel,
                "target_type": request.notification_target_type,
                "target_id": request.notification_target_id,
            }),
        },
    )


# =========================================================================
# Internal helpers
# =========================================================================


def _build_definition(
    template: WorkflowDefinition,
    payload_map: dict[str, dict[str, str | int | float | bool | None]],
) -> WorkflowDefinition:
    """Create a new WorkflowDefinition from a template with merged payloads."""
    new_steps: list[WorkflowStep] = []
    for step in template.steps:
        override = payload_map.get(step.step_id, {})
        if override:
            merged = dict(step.payload)
            merged.update({k: v for k, v in override.items() if v is not None})
            step = WorkflowStep(
                step_id=step.step_id,
                command_type=step.command_type,
                payload=merged,
                dependencies=list(step.dependencies),
                retry_count=step.retry_count,
                timeout_seconds=step.timeout_seconds,
            )
        new_steps.append(step)
    return WorkflowDefinition(
        workflow_type=template.workflow_type,
        steps=tuple(new_steps),
        description=template.description,
        timeout_seconds=template.timeout_seconds,
    )


def _filter_none(
    d: dict[str, str | int | float | bool | None],
) -> dict[str, str | int | float | bool]:
    return {k: v for k, v in d.items() if v is not None}

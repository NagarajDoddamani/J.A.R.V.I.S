from __future__ import annotations

from backend.runtime.workflows.models import WorkflowDefinition, WorkflowStep


# =========================================================================
# Template step helpers
# =========================================================================


def _step(
    step_id: str,
    command_type: str,
    payload: dict[str, str | int | float | bool | None] | None = None,
    dependencies: list[str] | None = None,
    retry_count: int = 0,
    timeout_seconds: float = 30.0,
) -> WorkflowStep:
    return WorkflowStep(
        step_id=step_id,
        command_type=command_type,
        payload=payload or {},
        dependencies=dependencies or [],
        retry_count=retry_count,
        timeout_seconds=timeout_seconds,
    )


# =========================================================================
# Research Workflow
#
# orchestrator.create_orchestration
#   → planner.create_plan
#   → research.create_request
#   → research.start_request
#   → memory.create_memory
#   → knowledge.register_source
# =========================================================================

RESEARCH_WORKFLOW_TYPE = "research_workflow"

RESEARCH_TEMPLATE = WorkflowDefinition(
    workflow_type=RESEARCH_WORKFLOW_TYPE,
    description="End-to-end research workflow: orchestrate, plan, execute research, store results",
    steps=(
        _step("orchestrate", "orchestrator.create_orchestration"),
        _step("create_plan", "planner.create_plan", dependencies=["orchestrate"]),
        _step("create_request", "research.create_request", dependencies=["create_plan"]),
        _step("start_request", "research.start_request", dependencies=["create_request"]),
        _step("store_memory", "memory.create_memory", dependencies=["start_request"]),
        _step("register_source", "knowledge.register_source", dependencies=["store_memory"]),
    ),
    timeout_seconds=600.0,
)


# =========================================================================
# Knowledge Ingestion Workflow
#
# knowledge.register_source
#   → knowledge.ingest_document
#   → knowledge.start_ingestion
#   → memory.create_memory
# =========================================================================

KNOWLEDGE_INGESTION_WORKFLOW_TYPE = "knowledge_ingestion_workflow"

KNOWLEDGE_INGESTION_TEMPLATE = WorkflowDefinition(
    workflow_type=KNOWLEDGE_INGESTION_WORKFLOW_TYPE,
    description="Ingest a knowledge source, document, and store a memory reference",
    steps=(
        _step("register_source", "knowledge.register_source"),
        _step("ingest_document", "knowledge.ingest_document", dependencies=["register_source"]),
        _step("start_ingestion", "knowledge.start_ingestion", dependencies=["ingest_document"]),
        _step("store_memory", "memory.create_memory", dependencies=["start_ingestion"]),
    ),
    timeout_seconds=300.0,
)


# =========================================================================
# Automation Workflow
#
# policy.create_policy
#   → automation.create_automation
#   → automation.activate_automation
#   → notification.create_notification
# =========================================================================

AUTOMATION_WORKFLOW_TYPE = "automation_workflow"

AUTOMATION_TEMPLATE = WorkflowDefinition(
    workflow_type=AUTOMATION_WORKFLOW_TYPE,
    description="Create a policy, automation, activate it, and send a notification",
    steps=(
        _step("create_policy", "policy.create_policy"),
        _step("create_automation", "automation.create_automation", dependencies=["create_policy"]),
        _step("activate_automation", "automation.activate_automation", dependencies=["create_automation"]),
        _step("send_notification", "notification.create_notification", dependencies=["activate_automation"]),
    ),
    timeout_seconds=300.0,
)


# =========================================================================
# Template registry
# =========================================================================

TEMPLATES: dict[str, WorkflowDefinition] = {
    RESEARCH_WORKFLOW_TYPE: RESEARCH_TEMPLATE,
    KNOWLEDGE_INGESTION_WORKFLOW_TYPE: KNOWLEDGE_INGESTION_TEMPLATE,
    AUTOMATION_WORKFLOW_TYPE: AUTOMATION_TEMPLATE,
}

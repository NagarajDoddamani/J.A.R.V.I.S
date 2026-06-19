from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# =========================================================================
# Research Workflow
# =========================================================================


@dataclass(frozen=True)
class ResearchWorkflowRequest:
    user_request: str = ""
    goal: str = ""
    source_name: str = ""
    source_type: str = ""
    source_location: str = ""
    memory_content: str = ""
    memory_category: str = "general"
    classification: str = "public"
    plan_description: str = ""


@dataclass(frozen=True)
class ResearchWorkflowResponse:
    instance_id: str
    workflow_type: str
    status: str
    step_results: dict[str, dict[str, Any] | None] = field(default_factory=dict)
    error_message: str | None = None


# =========================================================================
# Knowledge Ingestion Workflow
# =========================================================================


@dataclass(frozen=True)
class KnowledgeWorkflowRequest:
    source_name: str = ""
    source_type: str = ""
    source_location: str = ""
    classification: str = "public"
    document_title: str = ""
    document_checksum: str = ""
    memory_content: str = ""
    memory_category: str = "knowledge"


@dataclass(frozen=True)
class KnowledgeWorkflowResponse:
    instance_id: str
    workflow_type: str
    status: str
    step_results: dict[str, dict[str, Any] | None] = field(default_factory=dict)
    error_message: str | None = None


# =========================================================================
# Automation Workflow
# =========================================================================


@dataclass(frozen=True)
class AutomationWorkflowRequest:
    policy_name: str = ""
    policy_description: str = ""
    policy_priority: int = 0
    policy_scope: str = ""
    automation_name: str = ""
    automation_description: str = ""
    execution_mode: str = "once"
    notification_title: str = ""
    notification_message: str = ""
    notification_channel: str = "system"
    notification_target_type: str = "user"
    notification_target_id: str = ""


@dataclass(frozen=True)
class AutomationWorkflowResponse:
    instance_id: str
    workflow_type: str
    status: str
    step_results: dict[str, dict[str, Any] | None] = field(default_factory=dict)
    error_message: str | None = None

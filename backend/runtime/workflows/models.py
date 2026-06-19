from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class WorkflowStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StepStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class WorkflowStep:
    """A single step within a workflow definition or instance.

    Each step maps to exactly one command dispatch. Dependencies
    are expressed as a list of ``step_id`` values that must complete
    before this step is eligible for execution.
    """

    step_id: str
    command_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    retry_count: int = 0
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class WorkflowDefinition:
    """A reusable workflow template.

    The workflow is defined by its ordered set of steps. The engine
    resolves dependencies at runtime — the order in the ``steps``
    list is purely declarative; execution order is determined by
    the dependency graph.
    """

    workflow_type: str
    steps: tuple[WorkflowStep, ...]
    description: str = ""
    timeout_seconds: float = 300.0


@dataclass
class StepRun:
    """Mutable runtime state for a single step within an instance."""

    step: WorkflowStep
    status: StepStatus = StepStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    result: dict[str, Any] | None = None
    attempt: int = 0


@dataclass
class WorkflowInstance:
    """Mutable runtime state for a single workflow execution."""

    instance_id: str
    workflow_type: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    steps: dict[str, StepRun] = field(default_factory=dict)
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    error_message: str | None = None

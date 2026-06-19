from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.runtime.workflows.errors import (
    WorkflowDependencyError,
    WorkflowExecutionError,
    WorkflowInvalidTransitionError,
    WorkflowNotFoundError,
    WorkflowStepNotFoundError,
    WorkflowTimeoutError,
)
from backend.runtime.workflows.models import (
    StepRun,
    StepStatus,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowStatus,
    WorkflowStep,
)
from backend.runtime.workflows.registry import WorkflowRegistry
from backend.runtime.workflows.state import WorkflowState


class WorkflowEngine:
    """Orchestrates workflow lifecycle.

    The engine is dependency-agnostic — it tracks state, resolves
    ready-to-execute steps, and manages transitions. It delegates
    actual step execution to a caller-provided executor.
    """

    def __init__(
        self,
        registry: WorkflowRegistry,
        state: WorkflowState,
    ) -> None:
        self._registry = registry
        self._state = state

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_workflow(
        self,
        workflow_type: str,
        *,
        instance_id: str | None = None,
        payload_override: dict[str, Any] | None = None,
    ) -> WorkflowInstance:
        """Create and start a workflow instance from a registered definition.

        Returns the newly created instance with status ``RUNNING`` and
        all initial steps set to ``PENDING``.
        """
        definition = self._registry.get(workflow_type)
        now = datetime.now(tz=timezone.utc)
        instance = WorkflowInstance(
            instance_id=instance_id or str(uuid4()),
            workflow_type=workflow_type,
            status=WorkflowStatus.RUNNING,
            steps={
                s.step_id: StepRun(
                    step=_merge_payload(s, payload_override),
                )
                for s in definition.steps
            },
            created_at=now,
            started_at=now,
        )
        self._validate_dependencies(instance)
        self._check_workflow_completion(instance)
        self._state.save(instance)
        return instance

    def execute_step(self, instance_id: str, step_id: str) -> StepRun:
        """Mark a step as running and return the step run.

        Raises ``WorkflowInvalidTransitionError`` if the step is not
        ``PENDING`` or if its dependencies are not met.
        """
        instance = self._state.load(instance_id)
        step_run = instance.steps.get(step_id)
        if step_run is None:
            raise WorkflowStepNotFoundError(
                f"Step {step_id!r} not found in workflow {instance_id!r}"
            )
        if step_run.status not in (StepStatus.PENDING, StepStatus.FAILED):
            raise WorkflowInvalidTransitionError(
                f"Cannot execute step {step_id!r} in status {step_run.status.value}"
            )
        ready = self._ready_steps(instance)
        if step_id not in {s.step.step_id for s in ready}:
            raise WorkflowInvalidTransitionError(
                f"Step {step_id!r} dependencies are not met"
            )
        step_run.status = StepStatus.RUNNING
        step_run.started_at = datetime.now(tz=timezone.utc)
        step_run.attempt += 1
        self._state.save(instance)
        return step_run

    def complete_step(
        self,
        instance_id: str,
        step_id: str,
        *,
        result: dict[str, Any] | None = None,
    ) -> WorkflowInstance:
        """Mark a step as completed. Returns the updated instance.

        If all steps are completed the workflow is marked ``COMPLETED``.
        If the completed step unblocks dependent steps, they remain
        ``PENDING`` and will be picked up by the next ``ready_steps`` call.
        """
        instance = self._state.load(instance_id)
        step_run = instance.steps.get(step_id)
        if step_run is None:
            raise WorkflowStepNotFoundError(
                f"Step {step_id!r} not found in workflow {instance_id!r}"
            )
        if step_run.status != StepStatus.RUNNING:
            raise WorkflowInvalidTransitionError(
                f"Cannot complete step {step_id!r} in status {step_run.status.value}"
            )
        step_run.status = StepStatus.COMPLETED
        step_run.completed_at = datetime.now(tz=timezone.utc)
        step_run.result = result
        self._check_workflow_completion(instance)
        self._state.save(instance)
        return instance

    def fail_step(
        self,
        instance_id: str,
        step_id: str,
        *,
        error_message: str = "Step failed",
    ) -> WorkflowInstance:
        """Mark a step as failed.

        If the step has remaining retries it is set back to ``PENDING``.
        Otherwise it is ``FAILED`` and the workflow is also failed.
        """
        instance = self._state.load(instance_id)
        step_run = instance.steps.get(step_id)
        if step_run is None:
            raise WorkflowStepNotFoundError(
                f"Step {step_id!r} not found in workflow {instance_id!r}"
            )
        if step_run.status not in (StepStatus.RUNNING, StepStatus.PENDING):
            raise WorkflowInvalidTransitionError(
                f"Cannot fail step {step_id!r} in status {step_run.status.value}"
            )
        was_pending = step_run.status == StepStatus.PENDING
        step_run.status = StepStatus.FAILED
        step_run.error_message = error_message
        step_run.completed_at = datetime.now(tz=timezone.utc)

        if was_pending and step_run.attempt == 0:
            step_run.attempt = 1

        if step_run.attempt < step_run.step.retry_count + 1:
            step_run.status = StepStatus.PENDING
            step_run.error_message = error_message
            step_run.completed_at = None
        else:
            step_run.status = StepStatus.FAILED
            instance.status = WorkflowStatus.FAILED
            instance.failed_at = datetime.now(tz=timezone.utc)
            instance.error_message = (
                f"Step {step_id!r} failed after {step_run.attempt} attempt(s): {error_message}"
            )
            self._cancel_dependent_steps(instance, step_id)

        self._state.save(instance)
        return instance

    def cancel_workflow(self, instance_id: str, *, reason: str = "") -> WorkflowInstance:
        """Cancel a running or pending workflow."""
        instance = self._state.load(instance_id)
        if instance.status not in (WorkflowStatus.PENDING, WorkflowStatus.RUNNING):
            raise WorkflowInvalidTransitionError(
                f"Cannot cancel workflow in status {instance.status.value}"
            )
        instance.status = WorkflowStatus.CANCELLED
        instance.completed_at = datetime.now(tz=timezone.utc)
        instance.error_message = reason or "Workflow cancelled"
        for step_run in instance.steps.values():
            if step_run.status in (StepStatus.PENDING, StepStatus.RUNNING):
                step_run.status = StepStatus.CANCELLED
                step_run.error_message = reason or "Workflow cancelled"
        self._state.save(instance)
        return instance

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_instance(self, instance_id: str) -> WorkflowInstance:
        return self._state.load(instance_id)

    def ready_steps(self, instance_id: str) -> list[StepRun]:
        """Return all steps whose dependencies are met and are pending/retryable."""
        instance = self._state.load(instance_id)
        return self._ready_steps(instance)

    def list_instances(self) -> list[WorkflowInstance]:
        return self._state.list_all()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ready_steps(self, instance: WorkflowInstance) -> list[StepRun]:
        """Return steps eligible for execution (dependencies met + pending or failed with retries)."""
        ready: list[StepRun] = []
        for step_run in instance.steps.values():
            if step_run.status not in (StepStatus.PENDING,):
                continue
            if self._dependencies_met(instance, step_run):
                ready.append(step_run)
        return ready

    def _dependencies_met(self, instance: WorkflowInstance, step_run: StepRun) -> bool:
        """Return True if all dependency steps are completed."""
        for dep_id in step_run.step.dependencies:
            dep_step = instance.steps.get(dep_id)
            if dep_step is None:
                return False
            if dep_step.status != StepStatus.COMPLETED:
                return False
        return True

    def _check_workflow_completion(self, instance: WorkflowInstance) -> None:
        """If all steps are completed or skipped, mark workflow COMPLETED."""
        final_statuses = {StepStatus.COMPLETED, StepStatus.SKIPPED, StepStatus.CANCELLED}
        if all(s.status in final_statuses for s in instance.steps.values()):
            instance.status = WorkflowStatus.COMPLETED
            instance.completed_at = datetime.now(tz=timezone.utc)

    def _cancel_dependent_steps(self, instance: WorkflowInstance, failed_step_id: str) -> None:
        """Cancel all steps that depend on the failed step (directly or transitively)."""
        to_cancel = self._find_transitive_dependents(instance, failed_step_id)
        for step_id in to_cancel:
            step_run = instance.steps[step_id]
            if step_run.status in (StepStatus.PENDING,):
                step_run.status = StepStatus.CANCELLED
                step_run.error_message = f"Dependency {failed_step_id!r} failed"

    def _find_transitive_dependents(
        self, instance: WorkflowInstance, step_id: str
    ) -> set[str]:
        """Return all steps that directly or transitively depend on *step_id*."""
        dependents: set[str] = set()
        queue = {step_id}
        while queue:
            current = queue.pop()
            for sid, sr in instance.steps.items():
                if sid in dependents:
                    continue
                if current in sr.step.dependencies:
                    dependents.add(sid)
                    queue.add(sid)
        return dependents

    def _validate_dependencies(self, instance: WorkflowInstance) -> None:
        """Detect cycles in the step dependency graph."""
        all_ids = set(instance.steps)
        for step_run in instance.steps.values():
            for dep_id in step_run.step.dependencies:
                if dep_id not in all_ids:
                    raise WorkflowDependencyError(
                        f"Step {step_run.step.step_id!r} depends on unknown step {dep_id!r}"
                    )
        # Detect cycles via DFS
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def _has_cycle(step_id: str) -> bool:
            if step_id in rec_stack:
                return True
            if step_id in visited:
                return False
            visited.add(step_id)
            rec_stack.add(step_id)
            step_run = instance.steps.get(step_id)
            if step_run:
                for dep_id in step_run.step.dependencies:
                    if _has_cycle(dep_id):
                        return True
            rec_stack.discard(step_id)
            return False

        for sid in all_ids:
            if _has_cycle(sid):
                raise WorkflowDependencyError(
                    f"Circular dependency detected involving step {sid!r}"
                )


def _merge_payload(
    step: WorkflowStep, payload_override: dict[str, Any] | None
) -> WorkflowStep:
    """Merge workflow-level payload overrides into a step."""
    if not payload_override:
        return step
    merged = dict(step.payload)
    merged.update(payload_override)
    return WorkflowStep(
        step_id=step.step_id,
        command_type=step.command_type,
        payload=merged,
        dependencies=list(step.dependencies),
        retry_count=step.retry_count,
        timeout_seconds=step.timeout_seconds,
    )

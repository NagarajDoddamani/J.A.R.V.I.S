"""Step executor that bridges the workflow engine to the command dispatcher.

The executor is the integration point between the workflow layer and
the SVC-011-A/B command bus.  It takes a ready ``StepRun``, builds a
``CommandEnvelope``, dispatches it, and feeds the result back to the
engine.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from backend.runtime.dispatcher import CommandDispatcher
from backend.runtime.envelope import build_command_envelope
from backend.runtime.errors import CommandExpiredError, CommandRejectedError
from backend.runtime.handler import CommandResult
from backend.runtime.workflows.engine import WorkflowEngine
from backend.runtime.workflows.errors import WorkflowExecutionError
from backend.runtime.workflows.models import StepRun


class WorkflowExecutor:
    """Executes workflow steps via the command dispatcher.

    The executor handles retries, timeouts, and result propagation
    for each step.  It is designed to be called by external orchestration
    loops (e.g. a background task, an event handler, or a polling loop).
    """

    def __init__(
        self,
        engine: WorkflowEngine,
        dispatcher: CommandDispatcher,
    ) -> None:
        self._engine = engine
        self._dispatcher = dispatcher

    async def execute_ready_steps(self, instance_id: str) -> list[StepRun]:
        """Execute all currently-ready steps for a workflow instance.

        Each ready step is dispatched through the command bus.
        Steps are executed concurrently where possible.

        Returns a list of the executed ``StepRun`` objects.
        """
        ready = self._engine.ready_steps(instance_id)
        if not ready:
            return []

        tasks = [self._execute_single(instance_id, sr) for sr in ready]
        return await asyncio.gather(*tasks)

    async def _execute_single(self, instance_id: str, step_run: StepRun) -> StepRun:
        """Execute a single step with retry and timeout logic.

        Workflow:
            1. Mark step as RUNNING via the engine.
            2. Build and dispatch the command envelope.
            3. On success: complete the step via the engine.
            4. On transient failure: fail with retry (engine handles retry logic).
            5. On poison: fail without retry (exhausted or invalid).
        """
        step = step_run.step
        step_id = step.step_id

        try:
            self._engine.execute_step(instance_id, step_id)
        except Exception as exc:
            return _make_failed_run(step, str(exc))

        try:
            envelope = build_command_envelope(
                command_type=step.command_type,
                payload=dict(step.payload),
                producer="workflow-engine",
            )
            result = await asyncio.wait_for(
                self._dispatcher.dispatch(envelope),
                timeout=step.timeout_seconds,
            )
        except asyncio.TimeoutError:
            return _fail_step(self._engine, instance_id, step, "Step timed out")
        except CommandExpiredError as exc:
            return _fail_step(self._engine, instance_id, step, str(exc))
        except CommandRejectedError as exc:
            return _fail_step(self._engine, instance_id, step, str(exc))
        except Exception as exc:
            return _fail_step(self._engine, instance_id, step, str(exc))

        if result.success:
            self._engine.complete_step(instance_id, step_id, result=result.events[0] if result.events else None)
            step_run = self._engine.get_instance(instance_id).steps[step_id]
            return step_run
        else:
            return _fail_step(self._engine, instance_id, step, result.error or "Unknown error")

    async def execute_workflow(self, instance_id: str) -> None:
        """Execute a workflow to completion (or failure).

        Polls for ready steps and executes them until the workflow
        reaches a terminal state (COMPLETED, FAILED, CANCELLED).
        """
        while True:
            instance = self._engine.get_instance(instance_id)
            if instance.status.value in ("COMPLETED", "FAILED", "CANCELLED"):
                return
            ready = self._engine.ready_steps(instance_id)
            if not ready:
                return
            await self.execute_ready_steps(instance_id)


def _make_failed_run(step, error_message: str) -> StepRun:
    """Create a failed StepRun (used when execute_step itself fails)."""
    sr = StepRun(step=step)
    sr.status = "FAILED"  # type: ignore[assignment]
    sr.error_message = error_message
    return sr


def _fail_step(
    engine: WorkflowEngine, instance_id: str, step, error_message: str
) -> StepRun:
    """Fail a step through the engine and return the updated StepRun."""
    try:
        engine.fail_step(instance_id, step.step_id, error_message=error_message)
    except Exception:
        pass
    instance = engine.get_instance(instance_id)
    return instance.steps.get(step.step_id, _make_failed_run(step, error_message))

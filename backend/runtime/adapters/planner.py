from __future__ import annotations

from backend.planner.application.use_cases.approve_plan import ApprovePlanUseCase
from backend.planner.application.use_cases.create_plan import CreatePlanUseCase
from backend.planner.application.use_cases.dto import (
    CreatePlanRequest,
    PlanLifecycleRequest,
)
from backend.planner.application.use_cases.exceptions import UseCaseError
from backend.runtime.envelope import CommandEnvelope
from backend.runtime.handler import CommandResult
from backend.runtime.registry import CommandRegistry


def _safe_event(event_type: str, **fields: object) -> dict[str, object]:
    """Build a reference-only event payload with safe primitive types."""
    return {
        "event_type": event_type,
        "payload": {k: v for k, v in fields.items() if v is not None},
    }


def register_planner_handlers(
    registry: CommandRegistry,
    create_plan_use_case: CreatePlanUseCase,
    approve_plan_use_case: ApprovePlanUseCase,
) -> None:
    """Register all planner command handlers."""

    async def handle_create_plan(envelope: CommandEnvelope) -> CommandResult:
        try:
            request = CreatePlanRequest(
                user_request=envelope.payload.get("user_request", ""),
                goal=envelope.payload.get("goal", ""),
                priority=envelope.payload.get("priority", "normal"),
                strategy=envelope.payload.get("strategy", "sequential"),
            )
            response = create_plan_use_case.execute(request)
            return CommandResult(
                success=True,
                events=[
                    _safe_event(
                        "plan.created",
                        plan_id=response.plan_id,
                        status=response.status,
                        priority=response.priority,
                        strategy=response.strategy,
                    )
                ],
            )
        except UseCaseError as exc:
            return CommandResult(success=False, error=str(exc))

    async def handle_approve_plan(envelope: CommandEnvelope) -> CommandResult:
        try:
            request = PlanLifecycleRequest(
                plan_id=envelope.payload.get("plan_id", ""),
            )
            response = approve_plan_use_case.execute(request)
            return CommandResult(
                success=True,
                events=[
                    _safe_event(
                        "plan.approved",
                        plan_id=response.plan_id,
                        status=response.status,
                    )
                ],
            )
        except UseCaseError as exc:
            return CommandResult(success=False, error=str(exc))

    registry.register("planner.create_plan", handle_create_plan)
    registry.register("planner.approve_plan", handle_approve_plan)

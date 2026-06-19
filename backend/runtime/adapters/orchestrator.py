from __future__ import annotations

from backend.orchestrator.application.use_cases.create_orchestration import (
    CreateOrchestrationUseCase,
)
from backend.orchestrator.application.use_cases.dto import CreateOrchestrationRequest
from backend.orchestrator.application.use_cases.exceptions import UseCaseError
from backend.runtime.envelope import CommandEnvelope
from backend.runtime.handler import CommandResult
from backend.runtime.registry import CommandRegistry


def _safe_event(event_type: str, **fields: object) -> dict[str, object]:
    return {
        "event_type": event_type,
        "payload": {k: v for k, v in fields.items() if v is not None},
    }


def register_orchestrator_handlers(
    registry: CommandRegistry,
    create_orchestration_use_case: CreateOrchestrationUseCase,
) -> None:
    """Register all orchestrator command handlers."""

    async def handle_create_orchestration(envelope: CommandEnvelope) -> CommandResult:
        try:
            request = CreateOrchestrationRequest(
                intent=envelope.payload.get("intent", ""),
                goal=envelope.payload.get("goal", ""),
            )
            response = create_orchestration_use_case.execute(request)
            return CommandResult(
                success=True,
                events=[
                    _safe_event(
                        "orchestration.created",
                        orchestration_id=response.orchestration_id,
                        status=response.status,
                    )
                ],
            )
        except UseCaseError as exc:
            return CommandResult(success=False, error=str(exc))

    registry.register("orchestrator.create_orchestration", handle_create_orchestration)

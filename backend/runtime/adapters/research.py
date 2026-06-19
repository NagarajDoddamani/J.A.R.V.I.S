from __future__ import annotations

from backend.research.application.use_cases.create_request import (
    CreateRequestUseCase,
)
from backend.research.application.use_cases.dto import (
    CreateRequestRequest,
    RequestLifecycleRequest,
)
from backend.research.application.use_cases.exceptions import UseCaseError
from backend.research.application.use_cases.start_request import StartRequestUseCase
from backend.runtime.envelope import CommandEnvelope
from backend.runtime.handler import CommandResult
from backend.runtime.registry import CommandRegistry


def _safe_event(event_type: str, **fields: object) -> dict[str, object]:
    return {
        "event_type": event_type,
        "payload": {k: v for k, v in fields.items() if v is not None},
    }


def register_research_handlers(
    registry: CommandRegistry,
    create_request_use_case: CreateRequestUseCase,
    start_request_use_case: StartRequestUseCase,
) -> None:
    """Register all research command handlers."""

    async def handle_create_request(envelope: CommandEnvelope) -> CommandResult:
        try:
            request = CreateRequestRequest(
                query=envelope.payload.get("query", ""),
                goal=envelope.payload.get("goal", ""),
                priority=envelope.payload.get("priority", "normal"),
            )
            response = create_request_use_case.execute(request)
            return CommandResult(
                success=True,
                events=[
                    _safe_event(
                        "research.request_created",
                        request_id=response.request_id,
                        status=response.status,
                    )
                ],
            )
        except UseCaseError as exc:
            return CommandResult(success=False, error=str(exc))

    async def handle_start_request(envelope: CommandEnvelope) -> CommandResult:
        try:
            request = RequestLifecycleRequest(
                request_id=envelope.payload.get("request_id", ""),
            )
            response = start_request_use_case.execute(request)
            return CommandResult(
                success=True,
                events=[
                    _safe_event(
                        "research.request_started",
                        request_id=response.request_id,
                        status=response.status,
                    )
                ],
            )
        except UseCaseError as exc:
            return CommandResult(success=False, error=str(exc))

    registry.register("research.create_request", handle_create_request)
    registry.register("research.start_request", handle_start_request)

from __future__ import annotations

from backend.automation.application.use_cases.activate_automation import (
    ActivateAutomationUseCase,
)
from backend.automation.application.use_cases.create_automation import (
    CreateAutomationUseCase,
)
from backend.automation.application.use_cases.dto import (
    AutomationLifecycleRequest,
    CreateAutomationRequest,
)
from backend.automation.application.use_cases.exceptions import UseCaseError
from backend.runtime.envelope import CommandEnvelope
from backend.runtime.handler import CommandResult
from backend.runtime.registry import CommandRegistry


def _safe_event(event_type: str, **fields: object) -> dict[str, object]:
    return {
        "event_type": event_type,
        "payload": {k: v for k, v in fields.items() if v is not None},
    }


def register_automation_handlers(
    registry: CommandRegistry,
    create_automation_use_case: CreateAutomationUseCase,
    activate_automation_use_case: ActivateAutomationUseCase | None = None,
) -> None:
    """Register all automation command handlers."""

    async def handle_create_automation(envelope: CommandEnvelope) -> CommandResult:
        try:
            request = CreateAutomationRequest(
                name=envelope.payload.get("name", ""),
                description=envelope.payload.get("description", ""),
                execution_mode=envelope.payload.get("execution_mode", "once"),
            )
            response = create_automation_use_case.execute(request)
            return CommandResult(
                success=True,
                events=[
                    _safe_event(
                        "automation.created",
                        automation_id=response.automation_id,
                        status=response.status,
                        execution_mode=response.execution_mode,
                    )
                ],
            )
        except UseCaseError as exc:
            return CommandResult(success=False, error=str(exc))

    async def handle_activate_automation(envelope: CommandEnvelope) -> CommandResult:
        if activate_automation_use_case is None:
            return CommandResult(success=False, error="activate_automation handler not available")
        try:
            request = AutomationLifecycleRequest(
                automation_id=envelope.payload.get("automation_id", ""),
            )
            response = activate_automation_use_case.execute(request)
            return CommandResult(
                success=True,
                events=[
                    _safe_event(
                        "automation.activated",
                        automation_id=response.automation_id,
                        status=response.status,
                    )
                ],
            )
        except UseCaseError as exc:
            return CommandResult(success=False, error=str(exc))

    registry.register("automation.create_automation", handle_create_automation)
    registry.register("automation.activate_automation", handle_activate_automation)

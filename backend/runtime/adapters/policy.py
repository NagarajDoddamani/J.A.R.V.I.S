from __future__ import annotations

from backend.policy.application.use_cases.create_policy import CreatePolicyUseCase
from backend.policy.application.use_cases.dto import CreatePolicyRequest
from backend.policy.application.use_cases.exceptions import UseCaseError
from backend.runtime.envelope import CommandEnvelope
from backend.runtime.handler import CommandResult
from backend.runtime.registry import CommandRegistry


def _safe_event(event_type: str, **fields: object) -> dict[str, object]:
    return {
        "event_type": event_type,
        "payload": {k: v for k, v in fields.items() if v is not None},
    }


def register_policy_handlers(
    registry: CommandRegistry,
    create_policy_use_case: CreatePolicyUseCase,
) -> None:
    """Register all policy command handlers."""

    async def handle_create_policy(envelope: CommandEnvelope) -> CommandResult:
        try:
            request = CreatePolicyRequest(
                name=envelope.payload.get("name", ""),
                description=envelope.payload.get("description", ""),
                priority=envelope.payload.get("priority", "medium"),
                scope=envelope.payload.get("scope", "global"),
                version=envelope.payload.get("version", "1.0.0"),
            )
            response = create_policy_use_case.execute(request)
            return CommandResult(
                success=True,
                events=[
                    _safe_event(
                        "policy.created",
                        policy_id=response.policy_id,
                        status=response.status,
                        scope=response.scope,
                    )
                ],
            )
        except UseCaseError as exc:
            return CommandResult(success=False, error=str(exc))

    registry.register("policy.create_policy", handle_create_policy)

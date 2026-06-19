from __future__ import annotations

from backend.memory.application.use_cases.create_memory import CreateMemoryUseCase
from backend.memory.application.use_cases.dto import CreateMemoryRequest
from backend.memory.application.use_cases.exceptions import UseCaseError
from backend.runtime.envelope import CommandEnvelope
from backend.runtime.handler import CommandResult
from backend.runtime.registry import CommandRegistry


def _safe_event(event_type: str, **fields: object) -> dict[str, object]:
    return {
        "event_type": event_type,
        "payload": {k: v for k, v in fields.items() if v is not None},
    }


def register_memory_handlers(
    registry: CommandRegistry,
    create_memory_use_case: CreateMemoryUseCase,
) -> None:
    """Register all memory command handlers."""

    async def handle_create_memory(envelope: CommandEnvelope) -> CommandResult:
        try:
            request = CreateMemoryRequest(
                consent_id=envelope.payload.get("consent_id", ""),
                content=envelope.payload.get("content", ""),
                category=envelope.payload.get("category", "GENERAL"),
                source_type=envelope.payload.get("source_type", "user_input"),
                provenance_source=envelope.payload.get("provenance_source", ""),
                classification=envelope.payload.get("classification", "public"),
                sensitivity=envelope.payload.get("sensitivity", "public"),
                retention_policy=envelope.payload.get("retention_policy", "persistent"),
                source_id=envelope.payload.get("source_id"),
                provenance_actor_id=envelope.payload.get("provenance_actor_id"),
                retention_ttl_days=envelope.payload.get("retention_ttl_days"),
                redaction_metadata=envelope.payload.get("redaction_metadata"),
            )
            response = create_memory_use_case.execute(request)
            return CommandResult(
                success=True,
                events=[
                    _safe_event(
                        "memory.created",
                        memory_id=response.memory_id,
                        consent_id=response.consent_id,
                        revision=response.revision,
                        status="created",
                    )
                ],
            )
        except UseCaseError as exc:
            return CommandResult(success=False, error=str(exc))

    registry.register("memory.create_memory", handle_create_memory)

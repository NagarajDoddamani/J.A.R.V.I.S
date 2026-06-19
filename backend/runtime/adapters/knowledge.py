from __future__ import annotations

from backend.knowledge.application.use_cases.dto import (
    IngestDocumentRequest,
    RegisterSourceRequest,
    StartIngestionRequest,
)
from backend.knowledge.application.use_cases.exceptions import UseCaseError
from backend.knowledge.application.use_cases.ingest_document import (
    IngestDocumentUseCase,
)
from backend.knowledge.application.use_cases.register_source import (
    RegisterSourceUseCase,
)
from backend.knowledge.application.use_cases.start_ingestion import (
    StartIngestionUseCase,
)
from backend.runtime.envelope import CommandEnvelope
from backend.runtime.handler import CommandResult
from backend.runtime.registry import CommandRegistry


def _safe_event(event_type: str, **fields: object) -> dict[str, object]:
    return {
        "event_type": event_type,
        "payload": {k: v for k, v in fields.items() if v is not None},
    }


def register_knowledge_handlers(
    registry: CommandRegistry,
    register_source_use_case: RegisterSourceUseCase,
    ingest_document_use_case: IngestDocumentUseCase | None = None,
    start_ingestion_use_case: StartIngestionUseCase | None = None,
) -> None:
    """Register all knowledge command handlers."""

    async def handle_register_source(envelope: CommandEnvelope) -> CommandResult:
        try:
            request = RegisterSourceRequest(
                name=envelope.payload.get("name", ""),
                source_type=envelope.payload.get("source_type", ""),
                location=envelope.payload.get("location", ""),
                classification=envelope.payload.get("classification", "public"),
            )
            response = register_source_use_case.execute(request)
            return CommandResult(
                success=True,
                events=[
                    _safe_event(
                        "knowledge.source_registered",
                        source_id=response.source_id,
                        status=response.status,
                        source_type=response.source_type,
                    )
                ],
            )
        except UseCaseError as exc:
            return CommandResult(success=False, error=str(exc))

    async def handle_ingest_document(envelope: CommandEnvelope) -> CommandResult:
        if ingest_document_use_case is None:
            return CommandResult(success=False, error="ingest_document handler not available")
        try:
            request = IngestDocumentRequest(
                source_id=envelope.payload.get("source_id", ""),
                title=envelope.payload.get("title", ""),
                checksum=envelope.payload.get("checksum", ""),
                classification=envelope.payload.get("classification", "public"),
            )
            response = ingest_document_use_case.execute(request)
            return CommandResult(
                success=True,
                events=[
                    _safe_event(
                        "knowledge.document_ingested",
                        document_id=response.document_id,
                        title=response.title,
                        status=response.status,
                    )
                ],
            )
        except UseCaseError as exc:
            return CommandResult(success=False, error=str(exc))

    async def handle_start_ingestion(envelope: CommandEnvelope) -> CommandResult:
        if start_ingestion_use_case is None:
            return CommandResult(success=False, error="start_ingestion handler not available")
        try:
            request = StartIngestionRequest(
                source_id=envelope.payload.get("source_id", ""),
            )
            response = start_ingestion_use_case.execute(request)
            return CommandResult(
                success=True,
                events=[
                    _safe_event(
                        "knowledge.ingestion_started",
                        job_id=response.job_id,
                        status=response.status,
                    )
                ],
            )
        except UseCaseError as exc:
            return CommandResult(success=False, error=str(exc))

    registry.register("knowledge.register_source", handle_register_source)
    registry.register("knowledge.ingest_document", handle_ingest_document)
    registry.register("knowledge.start_ingestion", handle_start_ingestion)

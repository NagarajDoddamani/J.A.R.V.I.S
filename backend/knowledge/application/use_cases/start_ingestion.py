from __future__ import annotations

from backend.knowledge.application.ports.clock import KnowledgeClockPort
from backend.knowledge.application.ports.id_generator import KnowledgeIdGeneratorPort
from backend.knowledge.application.ports.outbox import KnowledgeOutboxPort
from backend.knowledge.application.ports.repository import (
    IngestionJobRepositoryPort,
    KnowledgeSourceRepositoryPort,
)
from backend.knowledge.application.use_cases.dto import (
    StartIngestionRequest,
    StartIngestionResponse,
)
from backend.knowledge.application.use_cases.exceptions import (
    SourceInactiveError,
    SourceNotFoundError,
)
from backend.knowledge.domain.factory import KnowledgeFactory
from backend.knowledge.domain.model import KnowledgeSourceId


class StartIngestionUseCase:
    def __init__(
        self,
        source_repo: KnowledgeSourceRepositoryPort,
        job_repo: IngestionJobRepositoryPort,
        outbox: KnowledgeOutboxPort,
        clock: KnowledgeClockPort,
        id_generator: KnowledgeIdGeneratorPort,
    ) -> None:
        self._source_repo = source_repo
        self._job_repo = job_repo
        self._outbox = outbox
        self._clock = clock
        self._id_generator = id_generator

    def execute(self, request: StartIngestionRequest) -> StartIngestionResponse:
        source_id = KnowledgeSourceId(value=__import__("uuid").UUID(request.source_id))
        source = self._source_repo.find_by_id(source_id)
        if source is None:
            raise SourceNotFoundError(request.source_id)
        if not source.is_active:
            raise SourceInactiveError(request.source_id)

        job, event = KnowledgeFactory.start_ingestion(source=source)
        self._job_repo.save(job)
        self._outbox.append(event)

        return StartIngestionResponse(
            job_id=str(job.job_id),
            source_id=str(job.source_id) if job.source_id else None,
            status=job.status.value,
            started_at=job.started_at,
        )

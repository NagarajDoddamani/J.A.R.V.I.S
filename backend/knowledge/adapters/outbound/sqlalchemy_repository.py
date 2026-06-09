from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.knowledge.adapters.outbound.mapper import (
    IngestionJobMapperImpl,
    KnowledgeChunkMapperImpl,
    KnowledgeDocumentMapperImpl,
    KnowledgeOutboxDomainEvent,
    KnowledgeOutboxMapperImpl,
    KnowledgeSourceMapperImpl,
)
from backend.knowledge.adapters.outbound.models import (
    IngestionJobModel,
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
    KnowledgeOutboxModel,
    KnowledgeSourceModel,
)
from backend.knowledge.application.persistence.dto import (
    IngestionJobStorageDTO,
    KnowledgeChunkStorageDTO,
    KnowledgeDocumentStorageDTO,
    KnowledgeSourceStorageDTO,
)
from backend.knowledge.domain.model import (
    ChunkId,
    DocumentChecksum,
    DocumentId,
    IngestionJob,
    IngestionJobId,
    IngestionStatus,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeSource,
    KnowledgeSourceId,
    SourceStatus,
    SourceType,
)


class SqlAlchemyKnowledgeSourceRepository:
    def __init__(
        self,
        session: Session,
        mapper: KnowledgeSourceMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or KnowledgeSourceMapperImpl()

    def save(self, source: KnowledgeSource) -> None:
        dto = self._mapper.domain_to_dto(source)
        existing = self._session.get(KnowledgeSourceModel, dto.source_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(self, source_id: KnowledgeSourceId) -> KnowledgeSource | None:
        model = self._session.get(KnowledgeSourceModel, str(source_id))
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_status(self, status: SourceStatus) -> list[KnowledgeSource]:
        stmt = select(KnowledgeSourceModel).where(
            KnowledgeSourceModel.status == status.value
        )
        models = list(self._session.scalars(stmt))
        return [self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models]

    def find_by_type(self, source_type: SourceType) -> list[KnowledgeSource]:
        stmt = select(KnowledgeSourceModel).where(
            KnowledgeSourceModel.source_type == source_type.value
        )
        models = list(self._session.scalars(stmt))
        return [self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models]

    def count(self) -> int:
        stmt = select(KnowledgeSourceModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(dto: KnowledgeSourceStorageDTO) -> KnowledgeSourceModel:
        return KnowledgeSourceModel(
            source_id=dto.source_id,
            name=dto.name,
            source_type=dto.source_type,
            location=dto.location,
            classification=dto.classification,
            status=dto.status,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            deleted_at=dto.deleted_at,
        )

    @staticmethod
    def _model_to_dto(model: KnowledgeSourceModel) -> KnowledgeSourceStorageDTO:
        return KnowledgeSourceStorageDTO(
            source_id=model.source_id,
            name=model.name,
            source_type=model.source_type,
            location=model.location,
            classification=model.classification,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def _model_update_from_dto(
        model: KnowledgeSourceModel, dto: KnowledgeSourceStorageDTO
    ) -> None:
        model.name = dto.name
        model.source_type = dto.source_type
        model.location = dto.location
        model.classification = dto.classification
        model.status = dto.status
        model.created_at = dto.created_at
        model.updated_at = dto.updated_at
        model.deleted_at = dto.deleted_at


class SqlAlchemyKnowledgeDocumentRepository:
    def __init__(
        self,
        session: Session,
        mapper: KnowledgeDocumentMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or KnowledgeDocumentMapperImpl()

    def save(self, document: KnowledgeDocument) -> None:
        dto = self._mapper.domain_to_dto(document)
        existing = self._session.get(KnowledgeDocumentModel, dto.document_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(self, document_id: DocumentId) -> KnowledgeDocument | None:
        model = self._session.get(KnowledgeDocumentModel, str(document_id))
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_source_id(
        self, source_id: KnowledgeSourceId
    ) -> list[KnowledgeDocument]:
        stmt = select(KnowledgeDocumentModel).where(
            KnowledgeDocumentModel.source_id == str(source_id)
        )
        models = list(self._session.scalars(stmt))
        return [self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models]

    def find_by_checksum(
        self, checksum: DocumentChecksum
    ) -> list[KnowledgeDocument]:
        stmt = select(KnowledgeDocumentModel).where(
            KnowledgeDocumentModel.checksum == str(checksum)
        )
        models = list(self._session.scalars(stmt))
        return [self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models]

    def find_deleted(self) -> list[KnowledgeDocument]:
        stmt = select(KnowledgeDocumentModel).where(
            KnowledgeDocumentModel.deleted_at.isnot(None)
        )
        models = list(self._session.scalars(stmt))
        return [self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models]

    def count(self) -> int:
        stmt = select(KnowledgeDocumentModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(dto: KnowledgeDocumentStorageDTO) -> KnowledgeDocumentModel:
        return KnowledgeDocumentModel(
            document_id=dto.document_id,
            source_id=dto.source_id,
            title=dto.title,
            checksum=dto.checksum,
            classification=dto.classification,
            status=dto.status,
            revision=dto.revision,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            deleted_at=dto.deleted_at,
        )

    @staticmethod
    def _model_to_dto(model: KnowledgeDocumentModel) -> KnowledgeDocumentStorageDTO:
        return KnowledgeDocumentStorageDTO(
            document_id=model.document_id,
            source_id=model.source_id,
            title=model.title,
            checksum=model.checksum,
            classification=model.classification,
            status=model.status,
            revision=model.revision,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def _model_update_from_dto(
        model: KnowledgeDocumentModel, dto: KnowledgeDocumentStorageDTO
    ) -> None:
        model.source_id = dto.source_id
        model.title = dto.title
        model.checksum = dto.checksum
        model.classification = dto.classification
        model.status = dto.status
        model.revision = dto.revision
        model.created_at = dto.created_at
        model.updated_at = dto.updated_at
        model.deleted_at = dto.deleted_at


class SqlAlchemyKnowledgeChunkRepository:
    def __init__(
        self,
        session: Session,
        mapper: KnowledgeChunkMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or KnowledgeChunkMapperImpl()

    def save(self, chunk: KnowledgeChunk) -> None:
        dto = self._mapper.domain_to_dto(chunk)
        existing = self._session.get(KnowledgeChunkModel, dto.chunk_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(self, chunk_id: ChunkId) -> KnowledgeChunk | None:
        model = self._session.get(KnowledgeChunkModel, str(chunk_id))
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_document_id(
        self, document_id: DocumentId
    ) -> list[KnowledgeChunk]:
        stmt = (
            select(KnowledgeChunkModel)
            .where(KnowledgeChunkModel.document_id == str(document_id))
            .order_by(KnowledgeChunkModel.chunk_index.asc().nullslast())
        )
        models = list(self._session.scalars(stmt))
        return [self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models]

    def find_by_index_range(
        self, document_id: DocumentId, start_index: int, end_index: int
    ) -> list[KnowledgeChunk]:
        stmt = (
            select(KnowledgeChunkModel)
            .where(KnowledgeChunkModel.document_id == str(document_id))
            .where(KnowledgeChunkModel.chunk_index >= start_index)
            .where(KnowledgeChunkModel.chunk_index <= end_index)
            .order_by(KnowledgeChunkModel.chunk_index.asc())
        )
        models = list(self._session.scalars(stmt))
        return [self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models]

    def count(self) -> int:
        stmt = select(KnowledgeChunkModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(dto: KnowledgeChunkStorageDTO) -> KnowledgeChunkModel:
        return KnowledgeChunkModel(
            chunk_id=dto.chunk_id,
            document_id=dto.document_id,
            chunk_index=dto.chunk_index,
            content=dto.content,
            classification=dto.classification,
            created_at=dto.created_at,
        )

    @staticmethod
    def _model_to_dto(model: KnowledgeChunkModel) -> KnowledgeChunkStorageDTO:
        return KnowledgeChunkStorageDTO(
            chunk_id=model.chunk_id,
            document_id=model.document_id,
            chunk_index=model.chunk_index,
            content=model.content,
            classification=model.classification,
            created_at=model.created_at,
        )

    @staticmethod
    def _model_update_from_dto(
        model: KnowledgeChunkModel, dto: KnowledgeChunkStorageDTO
    ) -> None:
        model.document_id = dto.document_id
        model.chunk_index = dto.chunk_index
        model.content = dto.content
        model.classification = dto.classification
        model.created_at = dto.created_at


class SqlAlchemyIngestionJobRepository:
    def __init__(
        self,
        session: Session,
        mapper: IngestionJobMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or IngestionJobMapperImpl()

    def save(self, job: IngestionJob) -> None:
        dto = self._mapper.domain_to_dto(job)
        existing = self._session.get(IngestionJobModel, dto.job_id)
        if existing is None:
            model = self._dto_to_model(dto)
            self._session.add(model)
        else:
            self._model_update_from_dto(existing, dto)
        self._session.flush()

    def find_by_id(self, job_id: IngestionJobId) -> IngestionJob | None:
        model = self._session.get(IngestionJobModel, str(job_id))
        if model is None:
            return None
        return self._mapper.dto_to_domain(self._model_to_dto(model))

    def find_by_source_id(
        self, source_id: KnowledgeSourceId
    ) -> list[IngestionJob]:
        stmt = select(IngestionJobModel).where(
            IngestionJobModel.source_id == str(source_id)
        )
        models = list(self._session.scalars(stmt))
        return [self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models]

    def find_by_status(
        self, status: IngestionStatus
    ) -> list[IngestionJob]:
        stmt = select(IngestionJobModel).where(
            IngestionJobModel.status == status.value
        )
        models = list(self._session.scalars(stmt))
        return [self._mapper.dto_to_domain(self._model_to_dto(m)) for m in models]

    def count(self) -> int:
        stmt = select(IngestionJobModel)
        return len(list(self._session.scalars(stmt)))

    @staticmethod
    def _dto_to_model(dto: IngestionJobStorageDTO) -> IngestionJobModel:
        return IngestionJobModel(
            job_id=dto.job_id,
            source_id=dto.source_id,
            status=dto.status,
            started_at=dto.started_at,
            completed_at=dto.completed_at,
            error_message=dto.error_message,
        )

    @staticmethod
    def _model_to_dto(model: IngestionJobModel) -> IngestionJobStorageDTO:
        return IngestionJobStorageDTO(
            job_id=model.job_id,
            source_id=model.source_id,
            status=model.status,
            started_at=model.started_at,
            completed_at=model.completed_at,
            error_message=model.error_message,
        )

    @staticmethod
    def _model_update_from_dto(
        model: IngestionJobModel, dto: IngestionJobStorageDTO
    ) -> None:
        model.source_id = dto.source_id
        model.status = dto.status
        model.started_at = dto.started_at
        model.completed_at = dto.completed_at
        model.error_message = dto.error_message


class SqlAlchemyKnowledgeOutboxAdapter:
    def __init__(
        self,
        session: Session,
        mapper: KnowledgeOutboxMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or KnowledgeOutboxMapperImpl()

    def append(self, event: KnowledgeOutboxDomainEvent) -> None:
        dto = self._mapper.event_to_dto(event)
        model = KnowledgeOutboxModel(
            event_id=dto.event_id,
            event_type=dto.event_type,
            aggregate_id=dto.aggregate_id,
            occurred_at=dto.occurred_at,
            correlation_id=dto.correlation_id,
            causation_id=dto.causation_id,
            payload=dto.payload,
            published=False,
        )
        self._session.add(model)
        self._session.flush()

    def fetch_unpublished(self, limit: int = 100) -> list[KnowledgeOutboxDomainEvent]:
        stmt = (
            select(KnowledgeOutboxModel)
            .where(KnowledgeOutboxModel.published == False)
            .order_by(KnowledgeOutboxModel.occurred_at.asc())
            .limit(limit)
        )
        models = list(self._session.scalars(stmt))
        return [self._model_to_event(m) for m in models]

    def mark_published(self, aggregate_id: str) -> None:
        stmt = (
            update(KnowledgeOutboxModel)
            .where(KnowledgeOutboxModel.aggregate_id == aggregate_id)
            .values(published=True)
        )
        self._session.execute(stmt)
        self._session.flush()

    def _model_to_event(self, model: KnowledgeOutboxModel) -> KnowledgeOutboxDomainEvent:
        from backend.knowledge.application.persistence.dto import (
            KnowledgeOutboxStorageDTO,
        )
        dto = KnowledgeOutboxStorageDTO(
            event_id=model.event_id,
            event_type=model.event_type,
            aggregate_id=model.aggregate_id,
            occurred_at=model.occurred_at,
            correlation_id=model.correlation_id,
            causation_id=model.causation_id,
            payload=model.payload,
            published=model.published,
        )
        return self._mapper.dto_to_event(dto)

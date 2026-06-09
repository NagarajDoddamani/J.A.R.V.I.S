from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.knowledge.application.use_cases.dto import (
    ChunkResponse,
    CompleteIngestionRequest,
    CompleteIngestionResponse,
    CreateChunkRequest,
    CreateChunkResponse,
    DeleteSourceRequest,
    DeleteSourceResponse,
    DocumentResponse,
    FailIngestionRequest,
    FailIngestionResponse,
    GetChunksByDocumentRequest,
    GetChunksByDocumentResponse,
    GetDocumentRequest,
    GetIngestionJobRequest,
    GetSourceRequest,
    IngestDocumentRequest,
    IngestDocumentResponse,
    IngestionJobResponse,
    ListSourcesRequest,
    ListSourcesResponse,
    RegisterSourceRequest,
    RegisterSourceResponse,
    ReindexResponse,
    RequestReindexRequest,
    SourceResponse,
    StartIngestionRequest,
    StartIngestionResponse,
)
from backend.knowledge.application.use_cases.exceptions import (
    ChunkNotFoundError,
    DocumentDeletedError,
    DocumentNotFoundError,
    IngestionJobNotFoundError,
    InvalidIngestionTransitionError,
    SourceInactiveError,
    SourceNotFoundError,
)
from backend.knowledge.bootstrap import (
    complete_ingestion_use_case,
    create_chunk_use_case,
    delete_source_use_case,
    fail_ingestion_use_case,
    get_chunks_by_document_use_case,
    get_document_use_case,
    get_ingestion_job_use_case,
    get_source_use_case,
    ingest_document_use_case,
    list_sources_use_case,
    register_source_use_case,
    request_reindex_use_case,
    start_ingestion_use_case,
)
from backend.knowledge.domain.exceptions import KnowledgeDomainError

router = APIRouter()


class _FailIngestionBody(BaseModel):
    error_message: str


# -------------------------------------------------------------------
# POST /sources — Register a new knowledge source
# -------------------------------------------------------------------


@router.post(
    "/sources",
    status_code=201,
    response_model=RegisterSourceResponse,
)
def register_source(
    body: RegisterSourceRequest,
    use_case=Depends(register_source_use_case),
) -> RegisterSourceResponse:
    try:
        return use_case.execute(body)
    except KnowledgeDomainError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# -------------------------------------------------------------------
# GET /sources — List knowledge sources
# -------------------------------------------------------------------


@router.get(
    "/sources",
    response_model=ListSourcesResponse,
)
def list_sources(
    status: str | None = Query(None),
    source_type: str | None = Query(None),
    use_case=Depends(list_sources_use_case),
) -> ListSourcesResponse:
    return use_case.execute(
        ListSourcesRequest(
            status=status,
            source_type=source_type,
        )
    )


# -------------------------------------------------------------------
# GET /sources/{source_id} — Get a single source
# -------------------------------------------------------------------


@router.get(
    "/sources/{source_id}",
    response_model=SourceResponse,
)
def get_source(
    source_id: str,
    use_case=Depends(get_source_use_case),
) -> SourceResponse:
    try:
        return use_case.execute(GetSourceRequest(source_id=source_id))
    except SourceNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Knowledge source not found: {source_id}"
        )


# -------------------------------------------------------------------
# DELETE /sources/{source_id} — Soft-delete a source
# -------------------------------------------------------------------


@router.delete(
    "/sources/{source_id}",
    response_model=DeleteSourceResponse,
)
def delete_source(
    source_id: str,
    use_case=Depends(delete_source_use_case),
) -> DeleteSourceResponse:
    try:
        return use_case.execute(DeleteSourceRequest(source_id=source_id))
    except SourceNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Knowledge source not found: {source_id}"
        )
    except KnowledgeDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# -------------------------------------------------------------------
# POST /documents — Ingest a document
# -------------------------------------------------------------------


@router.post(
    "/documents",
    status_code=201,
    response_model=IngestDocumentResponse,
)
def ingest_document(
    body: IngestDocumentRequest,
    use_case=Depends(ingest_document_use_case),
) -> IngestDocumentResponse:
    try:
        return use_case.execute(body)
    except (SourceNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (SourceInactiveError, KnowledgeDomainError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# -------------------------------------------------------------------
# GET /documents/{document_id} — Get a single document
# -------------------------------------------------------------------


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
)
def get_document(
    document_id: str,
    use_case=Depends(get_document_use_case),
) -> DocumentResponse:
    try:
        return use_case.execute(GetDocumentRequest(document_id=document_id))
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Knowledge document not found: {document_id}",
        )


# -------------------------------------------------------------------
# POST /chunks — Create a chunk
# -------------------------------------------------------------------


@router.post(
    "/chunks",
    status_code=201,
    response_model=CreateChunkResponse,
)
def create_chunk(
    body: CreateChunkRequest,
    use_case=Depends(create_chunk_use_case),
) -> CreateChunkResponse:
    try:
        return use_case.execute(body)
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Knowledge document not found: {body.document_id}"
        )
    except (DocumentDeletedError, KnowledgeDomainError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# -------------------------------------------------------------------
# GET /documents/{document_id}/chunks — List chunks for a document
# -------------------------------------------------------------------


@router.get(
    "/documents/{document_id}/chunks",
    response_model=GetChunksByDocumentResponse,
)
def get_chunks_by_document(
    document_id: str,
    use_case=Depends(get_chunks_by_document_use_case),
) -> GetChunksByDocumentResponse:
    return use_case.execute(
        GetChunksByDocumentRequest(document_id=document_id)
    )


# -------------------------------------------------------------------
# POST /ingestions — Start an ingestion job
# -------------------------------------------------------------------


@router.post(
    "/ingestions",
    status_code=201,
    response_model=StartIngestionResponse,
)
def start_ingestion(
    body: StartIngestionRequest,
    use_case=Depends(start_ingestion_use_case),
) -> StartIngestionResponse:
    try:
        return use_case.execute(body)
    except SourceNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Knowledge source not found: {body.source_id}"
        )
    except (SourceInactiveError, KnowledgeDomainError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# -------------------------------------------------------------------
# POST /ingestions/{job_id}/complete — Complete an ingestion job
# -------------------------------------------------------------------


@router.post(
    "/ingestions/{job_id}/complete",
    response_model=CompleteIngestionResponse,
)
def complete_ingestion(
    job_id: str,
    use_case=Depends(complete_ingestion_use_case),
) -> CompleteIngestionResponse:
    try:
        return use_case.execute(
            CompleteIngestionRequest(job_id=job_id)
        )
    except IngestionJobNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Ingestion job not found: {job_id}",
        )
    except (InvalidIngestionTransitionError, KnowledgeDomainError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# -------------------------------------------------------------------
# POST /ingestions/{job_id}/fail — Fail an ingestion job
# -------------------------------------------------------------------


@router.post(
    "/ingestions/{job_id}/fail",
    response_model=FailIngestionResponse,
)
def fail_ingestion(
    job_id: str,
    body: _FailIngestionBody,
    use_case=Depends(fail_ingestion_use_case),
) -> FailIngestionResponse:
    try:
        return use_case.execute(
            FailIngestionRequest(job_id=job_id, error_message=body.error_message)
        )
    except IngestionJobNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Ingestion job not found: {job_id}",
        )
    except (InvalidIngestionTransitionError, KnowledgeDomainError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# -------------------------------------------------------------------
# GET /ingestions/{job_id} — Get an ingestion job
# -------------------------------------------------------------------


@router.get(
    "/ingestions/{job_id}",
    response_model=IngestionJobResponse,
)
def get_ingestion_job(
    job_id: str,
    use_case=Depends(get_ingestion_job_use_case),
) -> IngestionJobResponse:
    try:
        return use_case.execute(GetIngestionJobRequest(job_id=job_id))
    except IngestionJobNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Ingestion job not found: {job_id}",
        )


# -------------------------------------------------------------------
# POST /sources/{source_id}/reindex — Request reindex
# -------------------------------------------------------------------


@router.post(
    "/sources/{source_id}/reindex",
    response_model=ReindexResponse,
)
def request_reindex(
    source_id: str,
    use_case=Depends(request_reindex_use_case),
) -> ReindexResponse:
    try:
        return use_case.execute(
            RequestReindexRequest(source_id=source_id)
        )
    except SourceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Knowledge source not found: {source_id}",
        )
    except (SourceInactiveError, KnowledgeDomainError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

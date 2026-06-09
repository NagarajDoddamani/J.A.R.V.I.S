from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.memory.application.use_cases.dto import (
    ConsentResponse,
    CreateMemoryRequest,
    CreateMemoryResponse,
    DeleteMemoryRequest,
    DeleteMemoryResponse,
    GetConsentRequest,
    GetMemoryRequest,
    GrantConsentRequest,
    GrantConsentResponse,
    MemoryResponse,
    RevokeConsentRequest,
    RevokeConsentResponse,
    SearchMemoriesRequest,
    SearchMemoriesResponse,
    UpdateMemoryRequest,
    UpdateMemoryResponse,
)
from backend.memory.application.use_cases.exceptions import (
    ConsentNotActiveError,
    ConsentNotFoundError,
    MemoryDeletedError,
    MemoryNotFoundError,
    UseCaseError,
)
from backend.memory.bootstrap import (
    create_memory_use_case,
    delete_memory_use_case,
    get_consent_use_case,
    get_memory_use_case,
    grant_consent_use_case,
    revoke_consent_use_case,
    search_memories_use_case,
    update_memory_use_case,
)
from backend.memory.domain.exceptions import (
    DeletedMemoryUpdateError,
    MemoryDomainError,
)

router = APIRouter()


# -------------------------------------------------------------------
# POST /memories — Create a new memory
# -------------------------------------------------------------------


@router.post(
    "/memories",
    status_code=201,
    response_model=CreateMemoryResponse,
)
def create_memory(
    body: CreateMemoryRequest,
    use_case=Depends(create_memory_use_case),
) -> CreateMemoryResponse:
    try:
        return use_case.execute(body)
    except (ConsentNotActiveError, ConsentNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except MemoryDomainError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# -------------------------------------------------------------------
# PATCH /memories/{memory_id} — Update memory content
# -------------------------------------------------------------------


@router.patch(
    "/memories/{memory_id}",
    response_model=UpdateMemoryResponse,
)
def update_memory(
    memory_id: str,
    body: UpdateMemoryRequest,
    use_case=Depends(update_memory_use_case),
) -> UpdateMemoryResponse:
    body.memory_id = memory_id
    try:
        return use_case.execute(body)
    except MemoryNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Memory not found: {memory_id}"
        )
    except MemoryDeletedError:
        raise HTTPException(
            status_code=400, detail=f"Memory is already deleted: {memory_id}"
        )
    except MemoryDomainError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# -------------------------------------------------------------------
# DELETE /memories/{memory_id} — Soft-delete a memory
# -------------------------------------------------------------------


@router.delete(
    "/memories/{memory_id}",
    response_model=DeleteMemoryResponse,
)
def delete_memory(
    memory_id: str,
    use_case=Depends(delete_memory_use_case),
) -> DeleteMemoryResponse:
    try:
        return use_case.execute(DeleteMemoryRequest(memory_id=memory_id))
    except MemoryNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Memory not found: {memory_id}"
        )
    except (DeletedMemoryUpdateError, MemoryDomainError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# -------------------------------------------------------------------
# GET /memories/{memory_id} — Get a single memory
# -------------------------------------------------------------------


@router.get(
    "/memories/{memory_id}",
    response_model=MemoryResponse,
)
def get_memory(
    memory_id: str,
    use_case=Depends(get_memory_use_case),
) -> MemoryResponse:
    try:
        return use_case.execute(GetMemoryRequest(memory_id=memory_id))
    except MemoryNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Memory not found: {memory_id}"
        )


# -------------------------------------------------------------------
# GET /memories — Search memories
# -------------------------------------------------------------------


@router.get(
    "/memories",
    response_model=SearchMemoriesResponse,
)
def search_memories(
    category: str | None = Query(None),
    consent_id: str | None = Query(None),
    source_type: str | None = Query(None),
    source_id: str | None = Query(None),
    use_case=Depends(search_memories_use_case),
) -> SearchMemoriesResponse:
    return use_case.execute(
        SearchMemoriesRequest(
            category=category,
            consent_id=consent_id,
            source_type=source_type,
            source_id=source_id,
        )
    )


# -------------------------------------------------------------------
# POST /consents — Grant a new consent
# -------------------------------------------------------------------


@router.post(
    "/consents",
    status_code=201,
    response_model=GrantConsentResponse,
)
def grant_consent(
    body: GrantConsentRequest,
    use_case=Depends(grant_consent_use_case),
) -> GrantConsentResponse:
    try:
        return use_case.execute(body)
    except UseCaseError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# -------------------------------------------------------------------
# POST /consents/{consent_id}/revoke — Revoke a consent
# -------------------------------------------------------------------


@router.post(
    "/consents/{consent_id}/revoke",
    response_model=RevokeConsentResponse,
)
def revoke_consent(
    consent_id: str,
    use_case=Depends(revoke_consent_use_case),
) -> RevokeConsentResponse:
    try:
        return use_case.execute(RevokeConsentRequest(consent_id=consent_id))
    except ConsentNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Consent not found: {consent_id}"
        )


# -------------------------------------------------------------------
# GET /consents/{consent_id} — Get a single consent
# -------------------------------------------------------------------


@router.get(
    "/consents/{consent_id}",
    response_model=ConsentResponse,
)
def get_consent(
    consent_id: str,
    use_case=Depends(get_consent_use_case),
) -> ConsentResponse:
    try:
        return use_case.execute(GetConsentRequest(consent_id=consent_id))
    except ConsentNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Consent not found: {consent_id}"
        )

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.audit.application.use_cases.dto import (
    AuditChainHeadResponse,
    AuditEntryResponse,
    GetAuditEntriesByCorrelationRequest,
    GetAuditChainHeadRequest,
    GetAuditChainRequest,
    GetAuditEntryRequest,
    RecordAuditEntryRequest,
    RecordAuditEntryResponse,
)
from backend.audit.application.use_cases.exceptions import (
    AuditEntryNotFoundError,
    ChainNotFoundError,
)
from backend.audit.bootstrap import (
    get_audit_chain_head_use_case,
    get_audit_chain_use_case,
    get_audit_entries_by_correlation_use_case,
    get_audit_entry_use_case,
    record_audit_entry_use_case,
)
from backend.audit.domain.exceptions import AuditDomainError

router = APIRouter()


# -------------------------------------------------------------------
# POST /audit/entries — Record a new audit entry
# -------------------------------------------------------------------


@router.post(
    "/audit/entries",
    status_code=201,
    response_model=RecordAuditEntryResponse,
)
def record_audit_entry(
    body: RecordAuditEntryRequest,
    use_case=Depends(record_audit_entry_use_case),
) -> RecordAuditEntryResponse:
    try:
        return use_case.execute(body)
    except AuditDomainError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# -------------------------------------------------------------------
# GET /audit/entries/{entry_id} — Retrieve a single entry by ID
# -------------------------------------------------------------------


@router.get(
    "/audit/entries/{entry_id}",
    response_model=AuditEntryResponse,
)
def get_audit_entry(
    entry_id: str,
    use_case=Depends(get_audit_entry_use_case),
) -> AuditEntryResponse:
    try:
        return use_case.execute(GetAuditEntryRequest(entry_id=entry_id))
    except AuditEntryNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Audit entry {entry_id} not found"
        )


# -------------------------------------------------------------------
# GET /audit/entries — Query entries by correlation ID
# -------------------------------------------------------------------


@router.get(
    "/audit/entries",
    response_model=list[AuditEntryResponse],
)
def list_audit_entries(
    correlation_id: str = Query(..., description="Correlation ID to filter by"),
    use_case=Depends(get_audit_entries_by_correlation_use_case),
) -> list[AuditEntryResponse]:
    result = use_case.execute(
        GetAuditEntriesByCorrelationRequest(correlation_id=correlation_id)
    )
    return result.entries


# -------------------------------------------------------------------
# GET /audit/chains/{chain_name} — Paginated chain entries
# -------------------------------------------------------------------


@router.get(
    "/audit/chains/{chain_name}",
    response_model=list[AuditEntryResponse],
)
def get_audit_chain(
    chain_name: str,
    since_index: int | None = Query(None, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    use_case=Depends(get_audit_chain_use_case),
) -> list[AuditEntryResponse]:
    result = use_case.execute(
        GetAuditChainRequest(
            chain_name=chain_name,
            since_index=since_index,
            limit=limit,
            offset=offset,
        )
    )
    return result.entries


# -------------------------------------------------------------------
# GET /audit/chains/{chain_name}/head — Chain head
# -------------------------------------------------------------------


@router.get(
    "/audit/chains/{chain_name}/head",
    response_model=AuditChainHeadResponse,
)
def get_audit_chain_head(
    chain_name: str,
    use_case=Depends(get_audit_chain_head_use_case),
) -> AuditChainHeadResponse:
    try:
        return use_case.execute(
            GetAuditChainHeadRequest(chain_name=chain_name)
        )
    except ChainNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Audit chain {chain_name} not found",
        )

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.research.application.use_cases.dto import (
    AddSourceRequest,
    AddSourceResponse,
    CreateJobRequest,
    CreateJobResponse,
    CreateRequestRequest,
    CreateRequestResponse,
    FailJobRequest,
    FailJobResponse,
    FailRequestRequest,
    FailRequestResponse,
    GenerateSummaryRequest,
    GenerateSummaryResponse,
    GetJobRequest,
    GetRequestRequest,
    JobLifecycleRequest,
    JobLifecycleResponse,
    JobResponse,
    ListJobsRequest,
    ListJobsResponse,
    ListRequestsRequest,
    ListRequestsResponse,
    RequestLifecycleRequest,
    RequestLifecycleResponse,
    RequestResponse,
)
from backend.research.application.use_cases.exceptions import (
    ResearchJobNotFoundError,
    ResearchRequestNotFoundError,
    UseCaseError,
)
from backend.research.bootstrap import (
    add_source_use_case,
    cancel_request_use_case,
    complete_job_use_case,
    complete_request_use_case,
    create_job_use_case,
    create_request_use_case,
    fail_job_use_case,
    fail_request_use_case,
    generate_summary_use_case,
    get_job_use_case,
    get_request_use_case,
    list_jobs_use_case,
    list_requests_use_case,
    start_job_use_case,
    start_request_use_case,
)
from backend.research.domain.exceptions import ResearchDomainError

router = APIRouter()


class _FailRequestBody(BaseModel):
    failure_reason: str


class _FailJobBody(BaseModel):
    failure_reason: str


class _AddSourceBody(BaseModel):
    reference: str
    source_type: str = "web"
    confidence_score: float = 0.5


class _GenerateSummaryBody(BaseModel):
    summary: str


class _CreateJobBody(BaseModel):
    goal: str
    priority: str | None = None


# =====================================================================
# Request CRUD + lifecycle
# =====================================================================


@router.post(
    "/requests",
    status_code=201,
    response_model=CreateRequestResponse,
)
def create_request(
    body: CreateRequestRequest,
    use_case=Depends(create_request_use_case),
) -> CreateRequestResponse:
    try:
        return use_case.execute(body)
    except ResearchDomainError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get(
    "/requests/{request_id}",
    response_model=RequestResponse,
)
def get_request(
    request_id: str,
    use_case=Depends(get_request_use_case),
) -> RequestResponse:
    try:
        return use_case.execute(GetRequestRequest(request_id=request_id))
    except ResearchRequestNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Research request not found: {request_id}",
        )


@router.get(
    "/requests",
    response_model=ListRequestsResponse,
)
def list_requests(
    status: str | None = Query(None),
    priority: str | None = Query(None),
    use_case=Depends(list_requests_use_case),
) -> ListRequestsResponse:
    return use_case.execute(
        ListRequestsRequest(status=status, priority=priority)
    )


@router.post(
    "/requests/{request_id}/start",
    response_model=RequestLifecycleResponse,
)
def start_request(
    request_id: str,
    use_case=Depends(start_request_use_case),
) -> RequestLifecycleResponse:
    try:
        return use_case.execute(
            RequestLifecycleRequest(request_id=request_id)
        )
    except ResearchRequestNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Research request not found: {request_id}",
        )
    except ResearchDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/requests/{request_id}/complete",
    response_model=RequestLifecycleResponse,
)
def complete_request(
    request_id: str,
    use_case=Depends(complete_request_use_case),
) -> RequestLifecycleResponse:
    try:
        return use_case.execute(
            RequestLifecycleRequest(request_id=request_id)
        )
    except ResearchRequestNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Research request not found: {request_id}",
        )
    except ResearchDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/requests/{request_id}/fail",
    response_model=FailRequestResponse,
)
def fail_request(
    request_id: str,
    body: _FailRequestBody,
    use_case=Depends(fail_request_use_case),
) -> FailRequestResponse:
    try:
        return use_case.execute(
            FailRequestRequest(
                request_id=request_id,
                failure_reason=body.failure_reason,
            )
        )
    except ResearchRequestNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Research request not found: {request_id}",
        )
    except (ResearchDomainError, UseCaseError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/requests/{request_id}/cancel",
    response_model=RequestLifecycleResponse,
)
def cancel_request(
    request_id: str,
    use_case=Depends(cancel_request_use_case),
) -> RequestLifecycleResponse:
    try:
        return use_case.execute(
            RequestLifecycleRequest(request_id=request_id)
        )
    except ResearchRequestNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Research request not found: {request_id}",
        )
    except ResearchDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# =====================================================================
# Job CRUD + lifecycle
# =====================================================================


@router.post(
    "/requests/{request_id}/jobs",
    status_code=201,
    response_model=CreateJobResponse,
)
def create_job(
    request_id: str,
    body: _CreateJobBody,
    use_case=Depends(create_job_use_case),
) -> CreateJobResponse:
    try:
        return use_case.execute(
            CreateJobRequest(
                request_id=request_id,
                goal=body.goal,
                priority=body.priority,
            )
        )
    except ResearchRequestNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Research request not found: {request_id}",
        )
    except ResearchDomainError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post(
    "/jobs/{job_id}/start",
    response_model=JobLifecycleResponse,
)
def start_job(
    job_id: str,
    use_case=Depends(start_job_use_case),
) -> JobLifecycleResponse:
    try:
        return use_case.execute(JobLifecycleRequest(job_id=job_id))
    except ResearchJobNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Research job not found: {job_id}",
        )
    except ResearchDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/jobs/{job_id}/complete",
    response_model=GenerateSummaryResponse,
)
def complete_job(
    job_id: str,
    body: _GenerateSummaryBody,
    use_case=Depends(complete_job_use_case),
) -> GenerateSummaryResponse:
    try:
        return use_case.execute(GenerateSummaryRequest(
            job_id=job_id, summary=body.summary
        ))
    except ResearchJobNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Research job not found: {job_id}",
        )
    except ResearchDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/jobs/{job_id}/fail",
    response_model=FailJobResponse,
)
def fail_job(
    job_id: str,
    body: _FailJobBody,
    use_case=Depends(fail_job_use_case),
) -> FailJobResponse:
    try:
        return use_case.execute(
            FailJobRequest(
                job_id=job_id, failure_reason=body.failure_reason
            )
        )
    except ResearchJobNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Research job not found: {job_id}",
        )
    except (ResearchDomainError, UseCaseError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
)
def get_job(
    job_id: str,
    use_case=Depends(get_job_use_case),
) -> JobResponse:
    try:
        return use_case.execute(GetJobRequest(job_id=job_id))
    except ResearchJobNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Research job not found: {job_id}",
        )


@router.get(
    "/jobs",
    response_model=ListJobsResponse,
)
def list_jobs(
    status: str | None = Query(None),
    request_id: str | None = Query(None),
    use_case=Depends(list_jobs_use_case),
) -> ListJobsResponse:
    return use_case.execute(
        ListJobsRequest(status=status, request_id=request_id)
    )


# =====================================================================
# Source / summary
# =====================================================================


@router.post(
    "/jobs/{job_id}/sources",
    status_code=201,
    response_model=AddSourceResponse,
)
def add_source(
    job_id: str,
    body: _AddSourceBody,
    use_case=Depends(add_source_use_case),
) -> AddSourceResponse:
    try:
        return use_case.execute(
            AddSourceRequest(
                job_id=job_id,
                reference=body.reference,
                source_type=body.source_type,
                confidence_score=body.confidence_score,
            )
        )
    except ResearchJobNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Research job not found: {job_id}",
        )
    except ResearchDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/jobs/{job_id}/summary",
    response_model=GenerateSummaryResponse,
)
def generate_summary(
    job_id: str,
    body: _GenerateSummaryBody,
    use_case=Depends(generate_summary_use_case),
) -> GenerateSummaryResponse:
    try:
        return use_case.execute(
            GenerateSummaryRequest(
                job_id=job_id, summary=body.summary
            )
        )
    except ResearchJobNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Research job not found: {job_id}",
        )
    except ResearchDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.orchestrator.application.use_cases.dto import (
    AddStepRequest,
    AddStepResponse,
    CompleteStepRequest,
    CompleteStepResponse,
    CreateOrchestrationRequest,
    CreateOrchestrationResponse,
    CreateWorkflowRequest,
    CreateWorkflowResponse,
    FailOrchestrationRequest,
    FailOrchestrationResponse,
    FailStepRequest,
    FailStepResponse,
    FailWorkflowRequest,
    FailWorkflowResponse,
    GetOrchestrationRequest,
    GetStepRequest,
    GetWorkflowRequest,
    ListOrchestrationsRequest,
    ListOrchestrationsResponse,
    ListWorkflowsRequest,
    ListWorkflowsResponse,
    OrchestrationLifecycleRequest,
    OrchestrationLifecycleResponse,
    OrchestrationResponse,
    StepLifecycleRequest,
    StepLifecycleResponse,
    WorkflowLifecycleRequest,
    WorkflowLifecycleResponse,
    WorkflowResponse,
    WorkflowStepResponse,
)
from backend.orchestrator.application.use_cases.exceptions import (
    OrchestrationNotFoundError,
    UseCaseError,
    WorkflowNotFoundError,
    WorkflowStepNotFoundError,
)
from backend.orchestrator.bootstrap import (
    add_step_use_case,
    cancel_orchestration_use_case,
    complete_orchestration_use_case,
    complete_step_use_case,
    complete_workflow_use_case,
    create_orchestration_use_case,
    create_workflow_use_case,
    fail_orchestration_use_case,
    fail_step_use_case,
    fail_workflow_use_case,
    get_orchestration_use_case,
    get_step_use_case,
    get_workflow_use_case,
    list_orchestrations_use_case,
    list_workflows_use_case,
    start_execution_use_case,
    start_planning_use_case,
    start_research_use_case,
    start_step_use_case,
)
from backend.orchestrator.domain.exceptions import OrchestratorDomainError

router = APIRouter()


class _FailOrchestrationBody(BaseModel):
    failure_reason: str


class _FailWorkflowBody(BaseModel):
    failure_reason: str


class _CompleteStepBody(BaseModel):
    result: str


class _FailStepBody(BaseModel):
    failure_reason: str


class _CreateWorkflowBody(BaseModel):
    goal: str
    mode: str = "sequential"


class _AddStepBody(BaseModel):
    agent_role: str = "research"
    execution_order: int = 0


# =====================================================================
# Orchestration CRUD + lifecycle
# =====================================================================


@router.post(
    "/orchestrations",
    status_code=201,
    response_model=CreateOrchestrationResponse,
)
def create_orchestration(
    body: CreateOrchestrationRequest,
    use_case=Depends(create_orchestration_use_case),
) -> CreateOrchestrationResponse:
    try:
        return use_case.execute(body)
    except OrchestratorDomainError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get(
    "/orchestrations/{orchestration_id}",
    response_model=OrchestrationResponse,
)
def get_orchestration(
    orchestration_id: str,
    use_case=Depends(get_orchestration_use_case),
) -> OrchestrationResponse:
    try:
        return use_case.execute(
            GetOrchestrationRequest(orchestration_id=orchestration_id)
        )
    except OrchestrationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Orchestration not found: {orchestration_id}",
        )


@router.get(
    "/orchestrations",
    response_model=ListOrchestrationsResponse,
)
def list_orchestrations(
    status: str | None = Query(None),
    use_case=Depends(list_orchestrations_use_case),
) -> ListOrchestrationsResponse:
    return use_case.execute(
        ListOrchestrationsRequest(status=status)
    )


@router.post(
    "/orchestrations/{orchestration_id}/planning",
    response_model=OrchestrationLifecycleResponse,
)
def start_planning(
    orchestration_id: str,
    use_case=Depends(start_planning_use_case),
) -> OrchestrationLifecycleResponse:
    try:
        return use_case.execute(
            OrchestrationLifecycleRequest(orchestration_id=orchestration_id)
        )
    except OrchestrationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Orchestration not found: {orchestration_id}",
        )
    except OrchestratorDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/orchestrations/{orchestration_id}/research",
    response_model=OrchestrationLifecycleResponse,
)
def start_research(
    orchestration_id: str,
    use_case=Depends(start_research_use_case),
) -> OrchestrationLifecycleResponse:
    try:
        return use_case.execute(
            OrchestrationLifecycleRequest(orchestration_id=orchestration_id)
        )
    except OrchestrationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Orchestration not found: {orchestration_id}",
        )
    except OrchestratorDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/orchestrations/{orchestration_id}/execution",
    response_model=OrchestrationLifecycleResponse,
)
def start_execution(
    orchestration_id: str,
    use_case=Depends(start_execution_use_case),
) -> OrchestrationLifecycleResponse:
    try:
        return use_case.execute(
            OrchestrationLifecycleRequest(orchestration_id=orchestration_id)
        )
    except OrchestrationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Orchestration not found: {orchestration_id}",
        )
    except OrchestratorDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/orchestrations/{orchestration_id}/complete",
    response_model=OrchestrationLifecycleResponse,
)
def complete_orchestration(
    orchestration_id: str,
    use_case=Depends(complete_orchestration_use_case),
) -> OrchestrationLifecycleResponse:
    try:
        return use_case.execute(
            OrchestrationLifecycleRequest(orchestration_id=orchestration_id)
        )
    except OrchestrationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Orchestration not found: {orchestration_id}",
        )
    except OrchestratorDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/orchestrations/{orchestration_id}/fail",
    response_model=FailOrchestrationResponse,
)
def fail_orchestration(
    orchestration_id: str,
    body: _FailOrchestrationBody,
    use_case=Depends(fail_orchestration_use_case),
) -> FailOrchestrationResponse:
    try:
        return use_case.execute(
            FailOrchestrationRequest(
                orchestration_id=orchestration_id,
                failure_reason=body.failure_reason,
            )
        )
    except OrchestrationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Orchestration not found: {orchestration_id}",
        )
    except (OrchestratorDomainError, UseCaseError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/orchestrations/{orchestration_id}/cancel",
    response_model=OrchestrationLifecycleResponse,
)
def cancel_orchestration(
    orchestration_id: str,
    use_case=Depends(cancel_orchestration_use_case),
) -> OrchestrationLifecycleResponse:
    try:
        return use_case.execute(
            OrchestrationLifecycleRequest(orchestration_id=orchestration_id)
        )
    except OrchestrationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Orchestration not found: {orchestration_id}",
        )
    except OrchestratorDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# =====================================================================
# Workflow CRUD + lifecycle
# =====================================================================


@router.post(
    "/orchestrations/{orchestration_id}/workflows",
    status_code=201,
    response_model=CreateWorkflowResponse,
)
def create_workflow(
    orchestration_id: str,
    body: _CreateWorkflowBody,
    use_case=Depends(create_workflow_use_case),
) -> CreateWorkflowResponse:
    try:
        return use_case.execute(
            CreateWorkflowRequest(
                orchestration_id=orchestration_id,
                goal=body.goal,
                mode=body.mode,
            )
        )
    except OrchestrationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Orchestration not found: {orchestration_id}",
        )
    except OrchestratorDomainError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get(
    "/workflows/{workflow_id}",
    response_model=WorkflowResponse,
)
def get_workflow(
    workflow_id: str,
    use_case=Depends(get_workflow_use_case),
) -> WorkflowResponse:
    try:
        return use_case.execute(GetWorkflowRequest(workflow_id=workflow_id))
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow not found: {workflow_id}",
        )


@router.get(
    "/workflows",
    response_model=ListWorkflowsResponse,
)
def list_workflows(
    status: str | None = Query(None),
    orchestration_id: str | None = Query(None),
    use_case=Depends(list_workflows_use_case),
) -> ListWorkflowsResponse:
    return use_case.execute(
        ListWorkflowsRequest(
            status=status, orchestration_id=orchestration_id
        )
    )


@router.post(
    "/workflows/{workflow_id}/complete",
    response_model=WorkflowLifecycleResponse,
)
def complete_workflow(
    workflow_id: str,
    use_case=Depends(complete_workflow_use_case),
) -> WorkflowLifecycleResponse:
    try:
        return use_case.execute(
            WorkflowLifecycleRequest(workflow_id=workflow_id)
        )
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow not found: {workflow_id}",
        )
    except OrchestratorDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/workflows/{workflow_id}/fail",
    response_model=FailWorkflowResponse,
)
def fail_workflow(
    workflow_id: str,
    body: _FailWorkflowBody,
    use_case=Depends(fail_workflow_use_case),
) -> FailWorkflowResponse:
    try:
        return use_case.execute(
            FailWorkflowRequest(
                workflow_id=workflow_id,
                failure_reason=body.failure_reason,
            )
        )
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow not found: {workflow_id}",
        )
    except (OrchestratorDomainError, UseCaseError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# =====================================================================
# Step lifecycle
# =====================================================================


@router.post(
    "/workflows/{workflow_id}/steps",
    status_code=201,
    response_model=AddStepResponse,
)
def add_step(
    workflow_id: str,
    body: _AddStepBody,
    use_case=Depends(add_step_use_case),
) -> AddStepResponse:
    try:
        return use_case.execute(
            AddStepRequest(
                workflow_id=workflow_id,
                agent_role=body.agent_role,
                execution_order=body.execution_order,
            )
        )
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow not found: {workflow_id}",
        )
    except OrchestratorDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/steps/{step_id}/start",
    response_model=StepLifecycleResponse,
)
def start_step(
    step_id: str,
    use_case=Depends(start_step_use_case),
) -> StepLifecycleResponse:
    try:
        return use_case.execute(StepLifecycleRequest(step_id=step_id))
    except WorkflowStepNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow step not found: {step_id}",
        )
    except OrchestratorDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/steps/{step_id}/complete",
    response_model=CompleteStepResponse,
)
def complete_step(
    step_id: str,
    body: _CompleteStepBody,
    use_case=Depends(complete_step_use_case),
) -> CompleteStepResponse:
    try:
        return use_case.execute(
            CompleteStepRequest(
                step_id=step_id, result=body.result
            )
        )
    except WorkflowStepNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow step not found: {step_id}",
        )
    except OrchestratorDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/steps/{step_id}/fail",
    response_model=FailStepResponse,
)
def fail_step(
    step_id: str,
    body: _FailStepBody,
    use_case=Depends(fail_step_use_case),
) -> FailStepResponse:
    try:
        return use_case.execute(
            FailStepRequest(
                step_id=step_id, failure_reason=body.failure_reason
            )
        )
    except WorkflowStepNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow step not found: {step_id}",
        )
    except (OrchestratorDomainError, UseCaseError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/steps/{step_id}",
    response_model=WorkflowStepResponse,
)
def get_step(
    step_id: str,
    use_case=Depends(get_step_use_case),
) -> WorkflowStepResponse:
    try:
        return use_case.execute(GetStepRequest(step_id=step_id))
    except WorkflowStepNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow step not found: {step_id}",
        )

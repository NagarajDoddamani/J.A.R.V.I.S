from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.planner.application.use_cases.dto import (
    AddTaskRequest,
    AddTaskResponse,
    AssignTaskRequest,
    AssignTaskResponse,
    CreatePlanRequest,
    CreatePlanResponse,
    FailPlanRequest,
    FailPlanResponse,
    FailTaskRequest,
    FailTaskResponse,
    GetPlanRequest,
    GetTaskRequest,
    ListPlansRequest,
    ListPlansResponse,
    ListTasksRequest,
    ListTasksResponse,
    PlanLifecycleRequest,
    PlanLifecycleResponse,
    PlanResponse,
    TaskLifecycleRequest,
    TaskLifecycleResponse,
    TaskResponse,
)
from backend.planner.application.use_cases.exceptions import (
    PlanNotFoundError,
    TaskNotFoundError,
    UseCaseError,
)
from backend.planner.bootstrap import (
    add_task_use_case,
    approve_plan_use_case,
    assign_task_use_case,
    cancel_plan_use_case,
    complete_plan_use_case,
    complete_task_use_case,
    create_plan_use_case,
    fail_plan_use_case,
    fail_task_use_case,
    get_plan_use_case,
    get_task_use_case,
    list_plans_use_case,
    list_tasks_use_case,
    mark_plan_ready_use_case,
    start_execution_use_case,
    start_planning_use_case,
    start_task_use_case,
)
from backend.planner.domain.exceptions import PlannerDomainError

router = APIRouter()


class _FailPlanBody(BaseModel):
    failure_reason: str


class _AssignTaskBody(BaseModel):
    agent: str


class _AddTaskBody(BaseModel):
    description: str


class _FailTaskBody(BaseModel):
    failure_reason: str


# =====================================================================
# Plan CRUD + lifecycle
# =====================================================================


@router.post(
    "/plans",
    status_code=201,
    response_model=CreatePlanResponse,
)
def create_plan(
    body: CreatePlanRequest,
    use_case=Depends(create_plan_use_case),
) -> CreatePlanResponse:
    try:
        return use_case.execute(body)
    except PlannerDomainError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get(
    "/plans/{plan_id}",
    response_model=PlanResponse,
)
def get_plan(
    plan_id: str,
    use_case=Depends(get_plan_use_case),
) -> PlanResponse:
    try:
        return use_case.execute(GetPlanRequest(plan_id=plan_id))
    except PlanNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Plan not found: {plan_id}"
        )


@router.get(
    "/plans",
    response_model=ListPlansResponse,
)
def list_plans(
    status: str | None = Query(None),
    priority: str | None = Query(None),
    use_case=Depends(list_plans_use_case),
) -> ListPlansResponse:
    return use_case.execute(
        ListPlansRequest(status=status, priority=priority)
    )


@router.post(
    "/plans/{plan_id}/approve",
    response_model=PlanLifecycleResponse,
)
def approve_plan(
    plan_id: str,
    use_case=Depends(approve_plan_use_case),
) -> PlanLifecycleResponse:
    try:
        return use_case.execute(PlanLifecycleRequest(plan_id=plan_id))
    except PlanNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Plan not found: {plan_id}"
        )
    except PlannerDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/plans/{plan_id}/planning",
    response_model=PlanLifecycleResponse,
)
def start_planning(
    plan_id: str,
    use_case=Depends(start_planning_use_case),
) -> PlanLifecycleResponse:
    try:
        return use_case.execute(PlanLifecycleRequest(plan_id=plan_id))
    except PlanNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Plan not found: {plan_id}"
        )
    except PlannerDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/plans/{plan_id}/ready",
    response_model=PlanLifecycleResponse,
)
def mark_plan_ready(
    plan_id: str,
    use_case=Depends(mark_plan_ready_use_case),
) -> PlanLifecycleResponse:
    try:
        return use_case.execute(PlanLifecycleRequest(plan_id=plan_id))
    except PlanNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Plan not found: {plan_id}"
        )
    except PlannerDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/plans/{plan_id}/execute",
    response_model=PlanLifecycleResponse,
)
def start_execution(
    plan_id: str,
    use_case=Depends(start_execution_use_case),
) -> PlanLifecycleResponse:
    try:
        return use_case.execute(PlanLifecycleRequest(plan_id=plan_id))
    except PlanNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Plan not found: {plan_id}"
        )
    except PlannerDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/plans/{plan_id}/complete",
    response_model=PlanLifecycleResponse,
)
def complete_plan(
    plan_id: str,
    use_case=Depends(complete_plan_use_case),
) -> PlanLifecycleResponse:
    try:
        return use_case.execute(PlanLifecycleRequest(plan_id=plan_id))
    except PlanNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Plan not found: {plan_id}"
        )
    except PlannerDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/plans/{plan_id}/fail",
    response_model=FailPlanResponse,
)
def fail_plan(
    plan_id: str,
    body: _FailPlanBody,
    use_case=Depends(fail_plan_use_case),
) -> FailPlanResponse:
    try:
        return use_case.execute(
            FailPlanRequest(
                plan_id=plan_id, failure_reason=body.failure_reason
            )
        )
    except PlanNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Plan not found: {plan_id}"
        )
    except PlannerDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/plans/{plan_id}/cancel",
    response_model=PlanLifecycleResponse,
)
def cancel_plan(
    plan_id: str,
    use_case=Depends(cancel_plan_use_case),
) -> PlanLifecycleResponse:
    try:
        return use_case.execute(PlanLifecycleRequest(plan_id=plan_id))
    except PlanNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Plan not found: {plan_id}"
        )
    except PlannerDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# =====================================================================
# Task CRUD + lifecycle
# =====================================================================


@router.post(
    "/plans/{plan_id}/tasks",
    status_code=201,
    response_model=AddTaskResponse,
)
def add_task(
    plan_id: str,
    body: _AddTaskBody,
    use_case=Depends(add_task_use_case),
) -> AddTaskResponse:
    try:
        return use_case.execute(
            AddTaskRequest(
                plan_id=plan_id, description=body.description
            )
        )
    except PlanNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Plan not found: {plan_id}"
        )
    except PlannerDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/tasks/{task_id}/assign",
    response_model=AssignTaskResponse,
)
def assign_task(
    task_id: str,
    body: _AssignTaskBody,
    use_case=Depends(assign_task_use_case),
) -> AssignTaskResponse:
    try:
        return use_case.execute(
            AssignTaskRequest(task_id=task_id, agent=body.agent)
        )
    except TaskNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Task not found: {task_id}"
        )
    except PlannerDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/tasks/{task_id}/start",
    response_model=TaskLifecycleResponse,
)
def start_task(
    task_id: str,
    use_case=Depends(start_task_use_case),
) -> TaskLifecycleResponse:
    try:
        return use_case.execute(TaskLifecycleRequest(task_id=task_id))
    except TaskNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Task not found: {task_id}"
        )
    except PlannerDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/tasks/{task_id}/complete",
    response_model=TaskLifecycleResponse,
)
def complete_task(
    task_id: str,
    use_case=Depends(complete_task_use_case),
) -> TaskLifecycleResponse:
    try:
        return use_case.execute(TaskLifecycleRequest(task_id=task_id))
    except TaskNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Task not found: {task_id}"
        )
    except PlannerDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/tasks/{task_id}/fail",
    response_model=FailTaskResponse,
)
def fail_task(
    task_id: str,
    body: _FailTaskBody,
    use_case=Depends(fail_task_use_case),
) -> FailTaskResponse:
    try:
        return use_case.execute(
            FailTaskRequest(
                task_id=task_id, failure_reason=body.failure_reason
            )
        )
    except TaskNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Task not found: {task_id}"
        )
    except PlannerDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
)
def get_task(
    task_id: str,
    use_case=Depends(get_task_use_case),
) -> TaskResponse:
    try:
        return use_case.execute(GetTaskRequest(task_id=task_id))
    except TaskNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Task not found: {task_id}"
        )


@router.get(
    "/tasks",
    response_model=ListTasksResponse,
)
def list_tasks(
    status: str | None = Query(None),
    assigned_agent: str | None = Query(None),
    plan_id: str | None = Query(None),
    use_case=Depends(list_tasks_use_case),
) -> ListTasksResponse:
    return use_case.execute(
        ListTasksRequest(
            status=status,
            assigned_agent=assigned_agent,
            plan_id=plan_id,
        )
    )

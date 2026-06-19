from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.agent.application.use_cases.dto import (
    AgentLifecycleRequest,
    AgentLifecycleResponse,
    AgentResponse,
    CompleteExecutionRequest,
    CompleteTaskRequest,
    CreateAgentRequest,
    CreateAgentResponse,
    CreateTaskRequest,
    CreateTaskResponse,
    ExecutionLifecycleResponse,
    ExecutionResponse,
    FailExecutionRequest,
    FailTaskRequest,
    GetAgentRequest,
    GetExecutionRequest,
    GetTaskRequest,
    ListAgentsRequest,
    ListAgentsResponse,
    ListExecutionsRequest,
    ListExecutionsResponse,
    ListTasksRequest,
    ListTasksResponse,
    StartExecutionRequest,
    StartExecutionResponse,
    TaskLifecycleRequest,
    TaskLifecycleResponse,
    TaskResponse,
)
from backend.agent.application.use_cases.exceptions import (
    AgentExecutionNotFoundError,
    AgentNotFoundError,
    AgentTaskNotFoundError,
)
from backend.agent.bootstrap import (
    get_activate_agent_use_case,
    get_cancel_task_use_case,
    get_complete_execution_use_case,
    get_complete_task_use_case,
    get_create_agent_use_case,
    get_create_task_use_case,
    get_disable_agent_use_case,
    get_execution_use_case,
    get_fail_execution_use_case,
    get_fail_task_use_case,
    get_agent_use_case,
    get_list_agents_use_case,
    get_list_executions_use_case,
    get_list_tasks_use_case,
    get_pause_agent_use_case,
    get_start_execution_use_case,
    get_start_task_use_case,
    get_task_use_case,
)
from backend.agent.domain.exceptions import AgentDomainError

router = APIRouter()


def _value_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


# =====================================================================
# Agent CRUD
# =====================================================================


@router.post(
    "/",
    status_code=201,
    response_model=CreateAgentResponse,
)
def create_agent(
    body: CreateAgentRequest,
    use_case=Depends(get_create_agent_use_case),
) -> CreateAgentResponse:
    try:
        return use_case.execute(body)
    except AgentDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.get(
    "/",
    response_model=ListAgentsResponse,
)
def list_agents(
    status: str | None = Query(None),
    agent_type: str | None = Query(None),
    use_case=Depends(get_list_agents_use_case),
) -> ListAgentsResponse:
    try:
        return use_case.execute(
            ListAgentsRequest(status=status, agent_type=agent_type)
        )
    except ValueError as exc:
        raise _value_error(exc)


# =====================================================================
# Task lifecycle (fixed paths before /{agent_id})
# =====================================================================


@router.post(
    "/tasks/{task_id}/start",
    response_model=TaskLifecycleResponse,
)
def start_task(
    task_id: str,
    agent_id: str = Query(...),
    use_case=Depends(get_start_task_use_case),
) -> TaskLifecycleResponse:
    try:
        return use_case.execute(
            TaskLifecycleRequest(agent_id=agent_id, task_id=task_id)
        )
    except AgentNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Agent not found: {agent_id}"
        )
    except AgentDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/tasks/{task_id}/complete",
    response_model=TaskLifecycleResponse,
)
def complete_task(
    task_id: str,
    body: CompleteTaskRequest,
    use_case=Depends(get_complete_task_use_case),
) -> TaskLifecycleResponse:
    try:
        return use_case.execute(
            CompleteTaskRequest(
                agent_id=body.agent_id,
                task_id=task_id,
                result=body.result,
            )
        )
    except AgentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Agent not found: {body.agent_id}",
        )
    except AgentTaskNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Task not found: {task_id}"
        )
    except AgentDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/tasks/{task_id}/fail",
    response_model=TaskLifecycleResponse,
)
def fail_task(
    task_id: str,
    body: FailTaskRequest,
    use_case=Depends(get_fail_task_use_case),
) -> TaskLifecycleResponse:
    try:
        return use_case.execute(
            FailTaskRequest(
                agent_id=body.agent_id,
                task_id=task_id,
                failure_reason=body.failure_reason,
            )
        )
    except AgentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Agent not found: {body.agent_id}",
        )
    except AgentTaskNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Task not found: {task_id}"
        )
    except AgentDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/tasks/{task_id}/cancel",
    response_model=TaskLifecycleResponse,
)
def cancel_task(
    task_id: str,
    agent_id: str = Query(...),
    use_case=Depends(get_cancel_task_use_case),
) -> TaskLifecycleResponse:
    try:
        return use_case.execute(
            TaskLifecycleRequest(agent_id=agent_id, task_id=task_id)
        )
    except AgentNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Agent not found: {agent_id}"
        )
    except AgentTaskNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Task not found: {task_id}"
        )
    except AgentDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


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
    except AgentTaskNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Task not found: {task_id}"
        )
    except ValueError as exc:
        raise _value_error(exc)


@router.get(
    "/tasks",
    response_model=ListTasksResponse,
)
def list_tasks(
    agent_id: str | None = Query(None),
    status: str | None = Query(None),
    use_case=Depends(get_list_tasks_use_case),
) -> ListTasksResponse:
    return use_case.execute(
        ListTasksRequest(agent_id=agent_id, status=status)
    )


@router.post(
    "/tasks/{task_id}/executions",
    status_code=201,
    response_model=StartExecutionResponse,
)
def start_execution(
    task_id: str,
    agent_id: str = Query(...),
    use_case=Depends(get_start_execution_use_case),
) -> StartExecutionResponse:
    try:
        return use_case.execute(
            StartExecutionRequest(agent_id=agent_id, task_id=task_id)
        )
    except AgentNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Agent not found: {agent_id}"
        )
    except AgentDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


# =====================================================================
# Execution lifecycle (fixed paths before /{agent_id})
# =====================================================================


@router.post(
    "/executions/{execution_id}/complete",
    response_model=ExecutionLifecycleResponse,
)
def complete_execution(
    execution_id: str,
    body: CompleteExecutionRequest,
    use_case=Depends(get_complete_execution_use_case),
) -> ExecutionLifecycleResponse:
    try:
        return use_case.execute(
            CompleteExecutionRequest(
                agent_id=body.agent_id,
                execution_id=execution_id,
                result=body.result,
            )
        )
    except AgentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Agent not found: {body.agent_id}",
        )
    except AgentExecutionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Execution not found: {execution_id}",
        )
    except AgentDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/executions/{execution_id}/fail",
    response_model=ExecutionLifecycleResponse,
)
def fail_execution(
    execution_id: str,
    body: FailExecutionRequest,
    use_case=Depends(get_fail_execution_use_case),
) -> ExecutionLifecycleResponse:
    try:
        return use_case.execute(
            FailExecutionRequest(
                agent_id=body.agent_id,
                execution_id=execution_id,
                failure_reason=body.failure_reason,
            )
        )
    except AgentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Agent not found: {body.agent_id}",
        )
    except AgentExecutionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Execution not found: {execution_id}",
        )
    except AgentDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.get(
    "/executions/{execution_id}",
    response_model=ExecutionResponse,
)
def get_execution(
    execution_id: str,
    use_case=Depends(get_execution_use_case),
) -> ExecutionResponse:
    try:
        return use_case.execute(
            GetExecutionRequest(execution_id=execution_id)
        )
    except AgentExecutionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Execution not found: {execution_id}",
        )
    except ValueError as exc:
        raise _value_error(exc)


@router.get(
    "/executions",
    response_model=ListExecutionsResponse,
)
def list_executions(
    agent_id: str | None = Query(None),
    task_id: str | None = Query(None),
    status: str | None = Query(None),
    use_case=Depends(get_list_executions_use_case),
) -> ListExecutionsResponse:
    return use_case.execute(
        ListExecutionsRequest(
            agent_id=agent_id, task_id=task_id, status=status
        )
    )


# =====================================================================
# Agent queries and lifecycle (path-parameter routes after fixed paths)
# =====================================================================


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
)
def get_agent(
    agent_id: str,
    use_case=Depends(get_agent_use_case),
) -> AgentResponse:
    try:
        return use_case.execute(GetAgentRequest(agent_id=agent_id))
    except AgentNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Agent not found: {agent_id}"
        )
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/{agent_id}/activate",
    response_model=AgentLifecycleResponse,
)
def activate_agent(
    agent_id: str,
    use_case=Depends(get_activate_agent_use_case),
) -> AgentLifecycleResponse:
    try:
        return use_case.execute(AgentLifecycleRequest(agent_id=agent_id))
    except AgentNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Agent not found: {agent_id}"
        )
    except AgentDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/{agent_id}/pause",
    response_model=AgentLifecycleResponse,
)
def pause_agent(
    agent_id: str,
    use_case=Depends(get_pause_agent_use_case),
) -> AgentLifecycleResponse:
    try:
        return use_case.execute(AgentLifecycleRequest(agent_id=agent_id))
    except AgentNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Agent not found: {agent_id}"
        )
    except AgentDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/{agent_id}/disable",
    response_model=AgentLifecycleResponse,
)
def disable_agent(
    agent_id: str,
    use_case=Depends(get_disable_agent_use_case),
) -> AgentLifecycleResponse:
    try:
        return use_case.execute(AgentLifecycleRequest(agent_id=agent_id))
    except AgentNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Agent not found: {agent_id}"
        )
    except AgentDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/{agent_id}/tasks",
    status_code=201,
    response_model=CreateTaskResponse,
)
def create_task(
    agent_id: str,
    body: CreateTaskRequest,
    use_case=Depends(get_create_task_use_case),
) -> CreateTaskResponse:
    try:
        return use_case.execute(
            CreateTaskRequest(
                agent_id=agent_id,
                goal=body.goal,
                instruction=body.instruction,
            )
        )
    except AgentNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Agent not found: {agent_id}"
        )
    except AgentDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)

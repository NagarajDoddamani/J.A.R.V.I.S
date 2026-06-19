from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.automation.application.use_cases.dto import (
    AddActionRequest,
    AddActionResponse,
    AddTriggerRequest,
    AddTriggerResponse,
    AutomationLifecycleRequest,
    AutomationLifecycleResponse,
    AutomationResponse,
    CompleteExecutionRequest,
    CompleteExecutionResponse,
    CreateAutomationRequest,
    CreateAutomationResponse,
    ExecutionResponse,
    FailExecutionRequest,
    FailExecutionResponse,
    GetAutomationRequest,
    GetExecutionRequest,
    GetTriggerRequest,
    ListAutomationsRequest,
    ListAutomationsResponse,
    ListExecutionsRequest,
    ListExecutionsResponse,
    ListTriggersRequest,
    ListTriggersResponse,
    StartExecutionRequest,
    StartExecutionResponse,
    TriggerLifecycleRequest,
    TriggerLifecycleResponse,
    TriggerResponse,
)
from backend.automation.application.use_cases.exceptions import (
    AutomationExecutionNotFoundError,
    AutomationNotFoundError,
    TriggerNotFoundError,
)
from backend.automation.bootstrap import (
    activate_automation_use_case,
    add_action_use_case,
    add_trigger_use_case,
    complete_execution_use_case,
    create_automation_use_case,
    disable_automation_use_case,
    disable_trigger_use_case,
    enable_trigger_use_case,
    fail_execution_use_case,
    get_automation_use_case,
    get_execution_use_case,
    get_trigger_use_case,
    list_automations_use_case,
    list_executions_use_case,
    list_triggers_use_case,
    pause_automation_use_case,
    start_execution_use_case,
)
from backend.automation.domain.exceptions import AutomationDomainError

router = APIRouter()


def _value_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


# =====================================================================
# Automation CRUD + lifecycle
# =====================================================================


@router.post(
    "/automations",
    status_code=201,
    response_model=CreateAutomationResponse,
)
def create_automation(
    body: CreateAutomationRequest,
    use_case=Depends(create_automation_use_case),
) -> CreateAutomationResponse:
    try:
        return use_case.execute(body)
    except AutomationDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/automations/{automation_id}",
    response_model=AutomationResponse,
)
def get_automation(
    automation_id: str,
    use_case=Depends(get_automation_use_case),
) -> AutomationResponse:
    try:
        return use_case.execute(GetAutomationRequest(automation_id=automation_id))
    except AutomationNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Automation not found: {automation_id}"
        )
    except ValueError as exc:
        raise _value_error(exc)


@router.get(
    "/automations",
    response_model=ListAutomationsResponse,
)
def list_automations(
    status: str | None = Query(None),
    execution_mode: str | None = Query(None),
    use_case=Depends(list_automations_use_case),
) -> ListAutomationsResponse:
    return use_case.execute(
        ListAutomationsRequest(status=status, execution_mode=execution_mode)
    )


@router.post(
    "/automations/{automation_id}/activate",
    response_model=AutomationLifecycleResponse,
)
def activate_automation(
    automation_id: str,
    use_case=Depends(activate_automation_use_case),
) -> AutomationLifecycleResponse:
    try:
        return use_case.execute(
            AutomationLifecycleRequest(automation_id=automation_id)
        )
    except AutomationNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Automation not found: {automation_id}"
        )
    except AutomationDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/automations/{automation_id}/pause",
    response_model=AutomationLifecycleResponse,
)
def pause_automation(
    automation_id: str,
    use_case=Depends(pause_automation_use_case),
) -> AutomationLifecycleResponse:
    try:
        return use_case.execute(
            AutomationLifecycleRequest(automation_id=automation_id)
        )
    except AutomationNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Automation not found: {automation_id}"
        )
    except AutomationDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/automations/{automation_id}/disable",
    response_model=AutomationLifecycleResponse,
)
def disable_automation(
    automation_id: str,
    use_case=Depends(disable_automation_use_case),
) -> AutomationLifecycleResponse:
    try:
        return use_case.execute(
            AutomationLifecycleRequest(automation_id=automation_id)
        )
    except AutomationNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Automation not found: {automation_id}"
        )
    except AutomationDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# =====================================================================
# Trigger CRUD + lifecycle
# =====================================================================


@router.post(
    "/automations/{automation_id}/triggers",
    status_code=201,
    response_model=AddTriggerResponse,
)
def add_trigger(
    automation_id: str,
    body: AddTriggerRequest,
    use_case=Depends(add_trigger_use_case),
) -> AddTriggerResponse:
    try:
        return use_case.execute(
            AddTriggerRequest(
                automation_id=automation_id,
                trigger_type=body.trigger_type,
                expression=body.expression,
            )
        )
    except AutomationNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Automation not found: {automation_id}"
        )
    except AutomationDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/triggers/{trigger_id}/enable",
    response_model=TriggerLifecycleResponse,
)
def enable_trigger(
    trigger_id: str,
    use_case=Depends(enable_trigger_use_case),
) -> TriggerLifecycleResponse:
    try:
        return use_case.execute(
            TriggerLifecycleRequest(trigger_id=trigger_id)
        )
    except TriggerNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Trigger not found: {trigger_id}"
        )
    except AutomationDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/triggers/{trigger_id}/disable",
    response_model=TriggerLifecycleResponse,
)
def disable_trigger(
    trigger_id: str,
    use_case=Depends(disable_trigger_use_case),
) -> TriggerLifecycleResponse:
    try:
        return use_case.execute(
            TriggerLifecycleRequest(trigger_id=trigger_id)
        )
    except TriggerNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Trigger not found: {trigger_id}"
        )
    except AutomationDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.get(
    "/triggers/{trigger_id}",
    response_model=TriggerResponse,
)
def get_trigger(
    trigger_id: str,
    use_case=Depends(get_trigger_use_case),
) -> TriggerResponse:
    try:
        return use_case.execute(GetTriggerRequest(trigger_id=trigger_id))
    except TriggerNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Trigger not found: {trigger_id}"
        )
    except ValueError as exc:
        raise _value_error(exc)


@router.get(
    "/triggers",
    response_model=ListTriggersResponse,
)
def list_triggers(
    trigger_type: str | None = Query(None),
    enabled: bool | None = Query(None),
    use_case=Depends(list_triggers_use_case),
) -> ListTriggersResponse:
    return use_case.execute(
        ListTriggersRequest(trigger_type=trigger_type, enabled=enabled)
    )


# =====================================================================
# Action
# =====================================================================


@router.post(
    "/automations/{automation_id}/actions",
    status_code=201,
    response_model=AddActionResponse,
)
def add_action(
    automation_id: str,
    body: AddActionRequest,
    use_case=Depends(add_action_use_case),
) -> AddActionResponse:
    try:
        return use_case.execute(
            AddActionRequest(
                automation_id=automation_id,
                action_type=body.action_type,
            )
        )
    except AutomationNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Automation not found: {automation_id}"
        )
    except AutomationDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


# =====================================================================
# Execution lifecycle
# =====================================================================


@router.post(
    "/automations/{automation_id}/executions",
    status_code=201,
    response_model=StartExecutionResponse,
)
def start_execution(
    automation_id: str,
    use_case=Depends(start_execution_use_case),
) -> StartExecutionResponse:
    try:
        return use_case.execute(
            StartExecutionRequest(automation_id=automation_id)
        )
    except AutomationNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Automation not found: {automation_id}"
        )
    except AutomationDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/executions/{execution_id}/complete",
    response_model=CompleteExecutionResponse,
)
def complete_execution(
    execution_id: str,
    body: CompleteExecutionRequest,
    use_case=Depends(complete_execution_use_case),
) -> CompleteExecutionResponse:
    try:
        return use_case.execute(
            CompleteExecutionRequest(
                automation_id=body.automation_id,
                execution_id=execution_id,
                result=body.result,
            )
        )
    except AutomationNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Automation not found: {body.automation_id}"
        )
    except AutomationDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise _value_error(exc)


@router.post(
    "/executions/{execution_id}/fail",
    response_model=FailExecutionResponse,
)
def fail_execution(
    execution_id: str,
    body: FailExecutionRequest,
    use_case=Depends(fail_execution_use_case),
) -> FailExecutionResponse:
    try:
        return use_case.execute(
            FailExecutionRequest(
                automation_id=body.automation_id,
                execution_id=execution_id,
                failure_reason=body.failure_reason,
            )
        )
    except AutomationNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Automation not found: {body.automation_id}"
        )
    except AutomationDomainError as exc:
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
        return use_case.execute(GetExecutionRequest(execution_id=execution_id))
    except AutomationExecutionNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Execution not found: {execution_id}"
        )
    except ValueError as exc:
        raise _value_error(exc)


@router.get(
    "/executions",
    response_model=ListExecutionsResponse,
)
def list_executions(
    status: str | None = Query(None),
    automation_id: str | None = Query(None),
    use_case=Depends(list_executions_use_case),
) -> ListExecutionsResponse:
    return use_case.execute(
        ListExecutionsRequest(status=status, automation_id=automation_id)
    )

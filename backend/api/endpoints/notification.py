from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.notification.application.use_cases.dto import (
    AcknowledgeNotificationRequest,
    AcknowledgeNotificationResponse,
    CreateActionRequest,
    CreateActionResponse,
    CreateNotificationRequest,
    CreateNotificationResponse,
    DismissNotificationRequest,
    DismissNotificationResponse,
    ExpireNotificationRequest,
    ExpireNotificationResponse,
    GetNotificationRequest,
    InvokeActionRequest,
    InvokeActionResponse,
    ListNotificationsRequest,
    ListNotificationsResponse,
    NotificationResponse,
    ShowNotificationRequest,
    ShowNotificationResponse,
)
from backend.notification.application.use_cases.exceptions import (
    NotificationActionNotFoundError,
    NotificationNotFoundError,
)
from backend.notification.bootstrap import (
    acknowledge_notification_use_case,
    create_action_use_case,
    create_notification_use_case,
    dismiss_notification_use_case,
    expire_notification_use_case,
    get_notification_use_case,
    invoke_action_use_case,
    list_notifications_use_case,
    show_notification_use_case,
)
from backend.notification.domain.exceptions import (
    InvalidNotificationTransitionError,
    NotificationDomainError,
)

router = APIRouter()


# -------------------------------------------------------------------
# POST /notifications — Create a new notification
# -------------------------------------------------------------------


@router.post(
    "/notifications",
    status_code=201,
    response_model=CreateNotificationResponse,
)
def create_notification(
    body: CreateNotificationRequest,
    use_case=Depends(create_notification_use_case),
) -> CreateNotificationResponse:
    try:
        return use_case.execute(body)
    except NotificationDomainError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# -------------------------------------------------------------------
# POST /notifications/{notification_id}/show — Mark as shown
# -------------------------------------------------------------------


@router.post(
    "/notifications/{notification_id}/show",
    response_model=ShowNotificationResponse,
)
def show_notification(
    notification_id: str,
    use_case=Depends(show_notification_use_case),
) -> ShowNotificationResponse:
    try:
        return use_case.execute(ShowNotificationRequest(notification_id=notification_id))
    except NotificationNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Notification not found: {notification_id}"
        )
    except InvalidNotificationTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except NotificationDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# -------------------------------------------------------------------
# POST /notifications/{notification_id}/acknowledge — Acknowledge
# -------------------------------------------------------------------


@router.post(
    "/notifications/{notification_id}/acknowledge",
    response_model=AcknowledgeNotificationResponse,
)
def acknowledge_notification(
    notification_id: str,
    use_case=Depends(acknowledge_notification_use_case),
) -> AcknowledgeNotificationResponse:
    try:
        return use_case.execute(
            AcknowledgeNotificationRequest(notification_id=notification_id)
        )
    except NotificationNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Notification not found: {notification_id}"
        )
    except InvalidNotificationTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except NotificationDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# -------------------------------------------------------------------
# POST /notifications/{notification_id}/dismiss — Dismiss
# -------------------------------------------------------------------


@router.post(
    "/notifications/{notification_id}/dismiss",
    response_model=DismissNotificationResponse,
)
def dismiss_notification(
    notification_id: str,
    use_case=Depends(dismiss_notification_use_case),
) -> DismissNotificationResponse:
    try:
        return use_case.execute(
            DismissNotificationRequest(notification_id=notification_id)
        )
    except NotificationNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Notification not found: {notification_id}"
        )
    except InvalidNotificationTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except NotificationDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# -------------------------------------------------------------------
# POST /notifications/{notification_id}/expire — Expire
# -------------------------------------------------------------------


@router.post(
    "/notifications/{notification_id}/expire",
    response_model=ExpireNotificationResponse,
)
def expire_notification(
    notification_id: str,
    use_case=Depends(expire_notification_use_case),
) -> ExpireNotificationResponse:
    try:
        return use_case.execute(
            ExpireNotificationRequest(notification_id=notification_id)
        )
    except NotificationNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Notification not found: {notification_id}"
        )
    except (InvalidNotificationTransitionError, NotificationDomainError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# -------------------------------------------------------------------
# GET /notifications/{notification_id} — Get a single notification
# -------------------------------------------------------------------


@router.get(
    "/notifications/{notification_id}",
    response_model=NotificationResponse,
)
def get_notification(
    notification_id: str,
    use_case=Depends(get_notification_use_case),
) -> NotificationResponse:
    try:
        return use_case.execute(
            GetNotificationRequest(notification_id=notification_id)
        )
    except NotificationNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Notification not found: {notification_id}"
        )


# -------------------------------------------------------------------
# GET /notifications — List notifications with optional filters
# -------------------------------------------------------------------


@router.get(
    "/notifications",
    response_model=ListNotificationsResponse,
)
def list_notifications(
    status: str | None = Query(None),
    priority: str | None = Query(None),
    target_type: str | None = Query(None),
    target_id: str | None = Query(None),
    use_case=Depends(list_notifications_use_case),
) -> ListNotificationsResponse:
    return use_case.execute(
        ListNotificationsRequest(
            status=status,
            priority=priority,
            target_type=target_type,
            target_id=target_id,
        )
    )


# -------------------------------------------------------------------
# POST /notifications/{notification_id}/actions — Create action
# -------------------------------------------------------------------


@router.post(
    "/notifications/{notification_id}/actions",
    status_code=201,
    response_model=CreateActionResponse,
)
def create_action(
    notification_id: str,
    body: CreateActionRequest,
    use_case=Depends(create_action_use_case),
) -> CreateActionResponse:
    body.notification_id = notification_id
    try:
        return use_case.execute(body)
    except NotificationNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Notification not found: {notification_id}"
        )
    except NotificationDomainError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# -------------------------------------------------------------------
# POST /notifications/actions/{action_id}/invoke — Invoke action
# -------------------------------------------------------------------


@router.post(
    "/notifications/actions/{action_id}/invoke",
    response_model=InvokeActionResponse,
)
def invoke_action(
    action_id: str,
    use_case=Depends(invoke_action_use_case),
) -> InvokeActionResponse:
    try:
        return use_case.execute(InvokeActionRequest(action_id=action_id))
    except NotificationActionNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Notification action not found: {action_id}"
        )

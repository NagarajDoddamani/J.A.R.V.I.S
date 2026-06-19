from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.notification.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyNotificationActionRepository,
    SqlAlchemyNotificationOutboxAdapter,
    SqlAlchemyNotificationRepository,
)
from backend.notification.application.use_cases.acknowledge_notification import (
    AcknowledgeNotificationUseCase,
)
from backend.notification.application.use_cases.create_action import (
    CreateActionUseCase,
)
from backend.notification.application.use_cases.create_notification import (
    CreateNotificationUseCase,
)
from backend.notification.application.use_cases.dismiss_notification import (
    DismissNotificationUseCase,
)
from backend.notification.application.use_cases.expire_notification import (
    ExpireNotificationUseCase,
)
from backend.notification.application.use_cases.get_notification import (
    GetNotificationUseCase,
)
from backend.notification.application.use_cases.invoke_action import (
    InvokeActionUseCase,
)
from backend.notification.application.use_cases.list_notifications import (
    ListNotificationsUseCase,
)
from backend.notification.application.use_cases.show_notification import (
    ShowNotificationUseCase,
)


def _notification_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyNotificationRepository:
    return SqlAlchemyNotificationRepository(db)


def _action_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyNotificationActionRepository:
    return SqlAlchemyNotificationActionRepository(db)


def _outbox(
    db: Session = Depends(get_db),
) -> SqlAlchemyNotificationOutboxAdapter:
    return SqlAlchemyNotificationOutboxAdapter(db)


def create_notification_use_case(
    notification_repo: SqlAlchemyNotificationRepository = Depends(_notification_repo),
    outbox: SqlAlchemyNotificationOutboxAdapter = Depends(_outbox),
) -> CreateNotificationUseCase:
    return CreateNotificationUseCase(
        notification_repo=notification_repo,
        outbox=outbox,
    )


def show_notification_use_case(
    notification_repo: SqlAlchemyNotificationRepository = Depends(_notification_repo),
    outbox: SqlAlchemyNotificationOutboxAdapter = Depends(_outbox),
) -> ShowNotificationUseCase:
    return ShowNotificationUseCase(
        notification_repo=notification_repo,
        outbox=outbox,
    )


def acknowledge_notification_use_case(
    notification_repo: SqlAlchemyNotificationRepository = Depends(_notification_repo),
    outbox: SqlAlchemyNotificationOutboxAdapter = Depends(_outbox),
) -> AcknowledgeNotificationUseCase:
    return AcknowledgeNotificationUseCase(
        notification_repo=notification_repo,
        outbox=outbox,
    )


def dismiss_notification_use_case(
    notification_repo: SqlAlchemyNotificationRepository = Depends(_notification_repo),
    outbox: SqlAlchemyNotificationOutboxAdapter = Depends(_outbox),
) -> DismissNotificationUseCase:
    return DismissNotificationUseCase(
        notification_repo=notification_repo,
        outbox=outbox,
    )


def expire_notification_use_case(
    notification_repo: SqlAlchemyNotificationRepository = Depends(_notification_repo),
    outbox: SqlAlchemyNotificationOutboxAdapter = Depends(_outbox),
) -> ExpireNotificationUseCase:
    return ExpireNotificationUseCase(
        notification_repo=notification_repo,
        outbox=outbox,
    )


def get_notification_use_case(
    notification_repo: SqlAlchemyNotificationRepository = Depends(_notification_repo),
) -> GetNotificationUseCase:
    return GetNotificationUseCase(notification_repo=notification_repo)


def list_notifications_use_case(
    notification_repo: SqlAlchemyNotificationRepository = Depends(_notification_repo),
) -> ListNotificationsUseCase:
    return ListNotificationsUseCase(notification_repo=notification_repo)


def create_action_use_case(
    notification_repo: SqlAlchemyNotificationRepository = Depends(_notification_repo),
    action_repo: SqlAlchemyNotificationActionRepository = Depends(_action_repo),
) -> CreateActionUseCase:
    return CreateActionUseCase(
        notification_repo=notification_repo,
        action_repo=action_repo,
    )


def invoke_action_use_case(
    action_repo: SqlAlchemyNotificationActionRepository = Depends(_action_repo),
    notification_repo: SqlAlchemyNotificationRepository = Depends(_notification_repo),
    outbox: SqlAlchemyNotificationOutboxAdapter = Depends(_outbox),
) -> InvokeActionUseCase:
    return InvokeActionUseCase(
        action_repo=action_repo,
        notification_repo=notification_repo,
        outbox=outbox,
    )

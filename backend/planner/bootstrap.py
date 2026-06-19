from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.planner.adapters.outbound.clock import SystemClockAdapter
from backend.planner.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.planner.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyPlanRepository,
    SqlAlchemyPlannerOutboxAdapter,
    SqlAlchemyTaskRepository,
)
from backend.planner.application.use_cases.add_task import AddTaskUseCase
from backend.planner.application.use_cases.approve_plan import ApprovePlanUseCase
from backend.planner.application.use_cases.assign_task import AssignTaskUseCase
from backend.planner.application.use_cases.cancel_plan import CancelPlanUseCase
from backend.planner.application.use_cases.complete_plan import CompletePlanUseCase
from backend.planner.application.use_cases.complete_task import CompleteTaskUseCase
from backend.planner.application.use_cases.create_plan import CreatePlanUseCase
from backend.planner.application.use_cases.fail_plan import FailPlanUseCase
from backend.planner.application.use_cases.fail_task import FailTaskUseCase
from backend.planner.application.use_cases.get_plan import GetPlanUseCase
from backend.planner.application.use_cases.get_task import GetTaskUseCase
from backend.planner.application.use_cases.list_plans import ListPlansUseCase
from backend.planner.application.use_cases.list_tasks import ListTasksUseCase
from backend.planner.application.use_cases.mark_plan_ready import (
    MarkPlanReadyUseCase,
)
from backend.planner.application.use_cases.start_execution import (
    StartExecutionUseCase,
)
from backend.planner.application.use_cases.start_planning import (
    StartPlanningUseCase,
)
from backend.planner.application.use_cases.start_task import StartTaskUseCase


def _plan_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyPlanRepository:
    return SqlAlchemyPlanRepository(db)


def _task_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyTaskRepository:
    return SqlAlchemyTaskRepository(db)


def _outbox(
    db: Session = Depends(get_db),
) -> SqlAlchemyPlannerOutboxAdapter:
    return SqlAlchemyPlannerOutboxAdapter(db)


def _clock() -> SystemClockAdapter:
    return SystemClockAdapter()


def _id_generator() -> UuidGeneratorAdapter:
    return UuidGeneratorAdapter()


# -- Plan commands ---------------------------------------------------------


def create_plan_use_case(
    plan_repo: SqlAlchemyPlanRepository = Depends(_plan_repo),
    outbox: SqlAlchemyPlannerOutboxAdapter = Depends(_outbox),
) -> CreatePlanUseCase:
    return CreatePlanUseCase(plan_repo=plan_repo, outbox=outbox)


def approve_plan_use_case(
    plan_repo: SqlAlchemyPlanRepository = Depends(_plan_repo),
    outbox: SqlAlchemyPlannerOutboxAdapter = Depends(_outbox),
) -> ApprovePlanUseCase:
    return ApprovePlanUseCase(plan_repo=plan_repo, outbox=outbox)


def start_planning_use_case(
    plan_repo: SqlAlchemyPlanRepository = Depends(_plan_repo),
) -> StartPlanningUseCase:
    return StartPlanningUseCase(plan_repo=plan_repo)


def mark_plan_ready_use_case(
    plan_repo: SqlAlchemyPlanRepository = Depends(_plan_repo),
    outbox: SqlAlchemyPlannerOutboxAdapter = Depends(_outbox),
) -> MarkPlanReadyUseCase:
    return MarkPlanReadyUseCase(plan_repo=plan_repo, outbox=outbox)


def start_execution_use_case(
    plan_repo: SqlAlchemyPlanRepository = Depends(_plan_repo),
    outbox: SqlAlchemyPlannerOutboxAdapter = Depends(_outbox),
) -> StartExecutionUseCase:
    return StartExecutionUseCase(plan_repo=plan_repo, outbox=outbox)


def complete_plan_use_case(
    plan_repo: SqlAlchemyPlanRepository = Depends(_plan_repo),
    outbox: SqlAlchemyPlannerOutboxAdapter = Depends(_outbox),
) -> CompletePlanUseCase:
    return CompletePlanUseCase(plan_repo=plan_repo, outbox=outbox)


def fail_plan_use_case(
    plan_repo: SqlAlchemyPlanRepository = Depends(_plan_repo),
    outbox: SqlAlchemyPlannerOutboxAdapter = Depends(_outbox),
) -> FailPlanUseCase:
    return FailPlanUseCase(plan_repo=plan_repo, outbox=outbox)


def cancel_plan_use_case(
    plan_repo: SqlAlchemyPlanRepository = Depends(_plan_repo),
    outbox: SqlAlchemyPlannerOutboxAdapter = Depends(_outbox),
) -> CancelPlanUseCase:
    return CancelPlanUseCase(plan_repo=plan_repo, outbox=outbox)


# -- Task commands ---------------------------------------------------------


def add_task_use_case(
    plan_repo: SqlAlchemyPlanRepository = Depends(_plan_repo),
    task_repo: SqlAlchemyTaskRepository = Depends(_task_repo),
    outbox: SqlAlchemyPlannerOutboxAdapter = Depends(_outbox),
) -> AddTaskUseCase:
    return AddTaskUseCase(
        plan_repo=plan_repo, task_repo=task_repo, outbox=outbox
    )


def assign_task_use_case(
    task_repo: SqlAlchemyTaskRepository = Depends(_task_repo),
    outbox: SqlAlchemyPlannerOutboxAdapter = Depends(_outbox),
) -> AssignTaskUseCase:
    return AssignTaskUseCase(task_repo=task_repo, outbox=outbox)


def start_task_use_case(
    task_repo: SqlAlchemyTaskRepository = Depends(_task_repo),
) -> StartTaskUseCase:
    return StartTaskUseCase(task_repo=task_repo)


def complete_task_use_case(
    task_repo: SqlAlchemyTaskRepository = Depends(_task_repo),
    outbox: SqlAlchemyPlannerOutboxAdapter = Depends(_outbox),
) -> CompleteTaskUseCase:
    return CompleteTaskUseCase(task_repo=task_repo, outbox=outbox)


def fail_task_use_case(
    task_repo: SqlAlchemyTaskRepository = Depends(_task_repo),
    outbox: SqlAlchemyPlannerOutboxAdapter = Depends(_outbox),
) -> FailTaskUseCase:
    return FailTaskUseCase(task_repo=task_repo, outbox=outbox)


# -- Queries ----------------------------------------------------------------


def get_plan_use_case(
    plan_repo: SqlAlchemyPlanRepository = Depends(_plan_repo),
) -> GetPlanUseCase:
    return GetPlanUseCase(plan_repo=plan_repo)


def list_plans_use_case(
    plan_repo: SqlAlchemyPlanRepository = Depends(_plan_repo),
) -> ListPlansUseCase:
    return ListPlansUseCase(plan_repo=plan_repo)


def get_task_use_case(
    task_repo: SqlAlchemyTaskRepository = Depends(_task_repo),
) -> GetTaskUseCase:
    return GetTaskUseCase(task_repo=task_repo)


def list_tasks_use_case(
    task_repo: SqlAlchemyTaskRepository = Depends(_task_repo),
) -> ListTasksUseCase:
    return ListTasksUseCase(task_repo=task_repo)

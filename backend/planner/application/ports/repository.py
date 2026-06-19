from __future__ import annotations

from typing import Protocol

from backend.planner.domain.model import (
    AgentType,
    Plan,
    PlanId,
    PlanPriority,
    PlanStatus,
    Task,
    TaskId,
    TaskStatus,
)


class PlanRepositoryPort(Protocol):
    """Repository port for ``Plan`` aggregate persistence.

    An implementation persists ``Plan`` aggregates to a concrete
    store. Plans are queryable by status, priority, and lifecycle.
    All methods are synchronous.
    """

    def save(self, plan: Plan) -> None:
        """Persist a new or updated plan.

        Uses upsert semantics — if a plan with the same ``plan_id``
        already exists it is replaced; otherwise a new record is
        created.

        Parameters
        ----------
        plan:
            The ``Plan`` aggregate to persist.
        """
        ...

    def find_by_id(self, plan_id: PlanId) -> Plan | None:
        """Retrieve a single plan by its unique identifier.

        Parameters
        ----------
        plan_id:
            The ``PlanId`` to look up.

        Returns
        -------
        The matching plan, or ``None`` if no plan exists with the
        given identifier.
        """
        ...

    def find_by_status(self, status: PlanStatus) -> list[Plan]:
        """Retrieve all plans with a given status.

        Parameters
        ----------
        status:
            The ``PlanStatus`` to filter by.

        Returns
        -------
        A list of ``Plan`` instances with the given status.
        """
        ...

    def find_by_priority(self, priority: PlanPriority) -> list[Plan]:
        """Retrieve all plans with a given priority.

        Parameters
        ----------
        priority:
            The ``PlanPriority`` to filter by.

        Returns
        -------
        A list of ``Plan`` instances with the given priority.
        """
        ...

    def find_active(self) -> list[Plan]:
        """Retrieve all non-terminal plans.

        Non-terminal plans are those whose status is not
        ``COMPLETED``, ``FAILED``, or ``CANCELLED``.

        Returns
        -------
        A list of ``Plan`` instances that have not yet reached a
        terminal state.
        """
        ...

    def count(self) -> int:
        """Return the total number of plans.

        This count includes all statuses.

        Returns
        -------
        Total plan count (0 if the store is empty).
        """
        ...


class TaskRepositoryPort(Protocol):
    """Repository port for ``Task`` persistence.

    An implementation persists ``Task`` aggregates to a concrete
    store. Tasks are queryable by status, assigned agent, and
    parent plan. Task ownership (the association between a task
    and its plan) is preserved by the implementing adapter.
    All methods are synchronous.
    """

    def save(self, task: Task) -> None:
        """Persist a new or updated task.

        Uses upsert semantics — if a task with the same ``task_id``
        already exists it is replaced; otherwise a new record is
        created.

        Parameters
        ----------
        task:
            The ``Task`` aggregate to persist.
        """
        ...

    def find_by_id(self, task_id: TaskId) -> Task | None:
        """Retrieve a single task by its unique identifier.

        Parameters
        ----------
        task_id:
            The ``TaskId`` to look up.

        Returns
        -------
        The matching task, or ``None`` if no task exists with the
        given identifier.
        """
        ...

    def find_by_status(self, status: TaskStatus) -> list[Task]:
        """Retrieve all tasks with a given status.

        Parameters
        ----------
        status:
            The ``TaskStatus`` to filter by.

        Returns
        -------
        A list of ``Task`` instances with the given status.
        """
        ...

    def find_by_agent(self, agent_type: AgentType) -> list[Task]:
        """Retrieve all tasks assigned to a given agent type.

        Parameters
        ----------
        agent_type:
            The ``AgentType`` to filter by.

        Returns
        -------
        A list of ``Task`` instances assigned to the given agent
        type.
        """
        ...

    def find_by_plan_id(self, plan_id: PlanId) -> list[Task]:
        """Retrieve all tasks belonging to a plan.

        Parameters
        ----------
        plan_id:
            The ``PlanId`` to search for.

        Returns
        -------
        A list of ``Task`` instances for the given plan.
        """
        ...

    def count(self) -> int:
        """Return the total number of tasks.

        Returns
        -------
        Total task count (0 if the store is empty).
        """
        ...

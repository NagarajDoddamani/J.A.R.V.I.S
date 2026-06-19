from __future__ import annotations

from typing import Protocol

from backend.automation.domain.model import (
    Automation,
    AutomationExecution,
    AutomationId,
    AutomationStatus,
    ExecutionMode,
    ExecutionStatus,
    Trigger,
    TriggerId,
    TriggerType,
    WorkflowExecutionId,
)


class AutomationRepositoryPort(Protocol):
    """Repository port for ``Automation`` aggregate persistence.

    An implementation persists ``Automation`` aggregates to a concrete
    store. Automations are queryable by status and execution mode.
    All methods are synchronous.
    """

    def save(self, automation: Automation) -> None:
        """Persist a new or updated automation.

        Uses upsert semantics — if an automation with the same
        ``automation_id`` already exists it is replaced; otherwise
        a new record is created.

        Parameters
        ----------
        automation:
            The ``Automation`` aggregate to persist.
        """
        ...

    def find_by_id(self, automation_id: AutomationId) -> Automation | None:
        """Retrieve a single automation by its unique identifier.

        Parameters
        ----------
        automation_id:
            The ``AutomationId`` to look up.

        Returns
        -------
        The matching automation, or ``None`` if no automation exists
        with the given identifier.
        """
        ...

    def find_by_status(self, status: AutomationStatus) -> list[Automation]:
        """Retrieve all automations with a given status.

        Parameters
        ----------
        status:
            The ``AutomationStatus`` to filter by.

        Returns
        -------
        A list of ``Automation`` instances with the given status.
        """
        ...

    def find_by_execution_mode(self, mode: ExecutionMode) -> list[Automation]:
        """Retrieve all automations with a given execution mode.

        Parameters
        ----------
        mode:
            The ``ExecutionMode`` to filter by.

        Returns
        -------
        A list of ``Automation`` instances with the given mode.
        """
        ...

    def find_all(self) -> list[Automation]:
        """Retrieve all automations.

        Returns
        -------
        A list of all ``Automation`` instances.
        """
        ...

    def count(self) -> int:
        """Return the total number of automations.

        This count includes all statuses and modes.

        Returns
        -------
        Total automation count (0 if the store is empty).
        """
        ...


class TriggerRepositoryPort(Protocol):
    """Repository port for ``Trigger`` persistence.

    An implementation persists ``Trigger`` entities to a concrete store.
    Triggers are queryable by type and enabled status.
    All methods are synchronous.
    """

    def save(self, trigger: Trigger) -> None:
        """Persist a new or updated trigger.

        Uses upsert semantics — if a trigger with the same
        ``trigger_id`` already exists it is replaced; otherwise a
        new record is created.

        Parameters
        ----------
        trigger:
            The ``Trigger`` to persist.
        """
        ...

    def find_by_id(self, trigger_id: TriggerId) -> Trigger | None:
        """Retrieve a single trigger by its unique identifier.

        Parameters
        ----------
        trigger_id:
            The ``TriggerId`` to look up.

        Returns
        -------
        The matching trigger, or ``None`` if no trigger exists with
        the given identifier.
        """
        ...

    def find_by_type(self, trigger_type: TriggerType) -> list[Trigger]:
        """Retrieve all triggers of a given type.

        Parameters
        ----------
        trigger_type:
            The ``TriggerType`` to filter by.

        Returns
        -------
        A list of ``Trigger`` instances with the given type.
        """
        ...

    def find_enabled(self) -> list[Trigger]:
        """Retrieve all enabled triggers.

        Returns
        -------
        A list of ``Trigger`` instances where ``enabled`` is ``True``.
        """
        ...

    def find_all(self) -> list[Trigger]:
        """Retrieve all triggers.

        Returns
        -------
        A list of all ``Trigger`` instances.
        """
        ...

    def count(self) -> int:
        """Return the total number of triggers.

        Returns
        -------
        Total trigger count (0 if the store is empty).
        """
        ...


class AutomationExecutionRepositoryPort(Protocol):
    """Repository port for ``AutomationExecution`` persistence.

    An implementation persists ``AutomationExecution`` entities to a
    concrete store. Executions are queryable by status and parent
    automation. All methods are synchronous.
    """

    def save(self, execution: AutomationExecution) -> None:
        """Persist a new or updated automation execution.

        Uses upsert semantics — if an execution with the same
        ``execution_id`` already exists it is replaced; otherwise a
        new record is created.

        Parameters
        ----------
        execution:
            The ``AutomationExecution`` to persist.
        """
        ...

    def find_by_id(
        self, execution_id: WorkflowExecutionId
    ) -> AutomationExecution | None:
        """Retrieve a single execution by its unique identifier.

        Parameters
        ----------
        execution_id:
            The ``WorkflowExecutionId`` to look up.

        Returns
        -------
        The matching execution, or ``None`` if no execution exists
        with the given identifier.
        """
        ...

    def find_by_status(self, status: ExecutionStatus) -> list[AutomationExecution]:
        """Retrieve all executions with a given status.

        Parameters
        ----------
        status:
            The ``ExecutionStatus`` to filter by.

        Returns
        -------
        A list of ``AutomationExecution`` instances with the given
        status.
        """
        ...

    def find_by_automation_id(
        self, automation_id: AutomationId
    ) -> list[AutomationExecution]:
        """Retrieve all executions belonging to an automation.

        Parameters
        ----------
        automation_id:
            The ``AutomationId`` to search for.

        Returns
        -------
        A list of ``AutomationExecution`` instances for the given
        automation.
        """
        ...

    def find_all(self) -> list[AutomationExecution]:
        """Retrieve all automation executions.

        Returns
        -------
        A list of all ``AutomationExecution`` instances.
        """
        ...

    def count(self) -> int:
        """Return the total number of automation executions.

        Returns
        -------
        Total execution count (0 if the store is empty).
        """
        ...

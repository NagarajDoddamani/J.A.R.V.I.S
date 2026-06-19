from __future__ import annotations

from typing import Protocol

from backend.orchestrator.domain.model import (
    AgentRole,
    Orchestration,
    OrchestrationId,
    OrchestrationStatus,
    Workflow,
    WorkflowId,
    WorkflowStep,
    WorkflowStepStatus,
    WorkflowStatus,
)


class OrchestrationRepositoryPort(Protocol):
    """Repository port for ``Orchestration`` aggregate persistence.

    An implementation persists ``Orchestration`` aggregates to a
    concrete store. Orchestrations are queryable by status.
    All methods are synchronous.
    """

    def save(self, orchestration: Orchestration) -> None:
        """Persist a new or updated orchestration.

        Uses upsert semantics — if an orchestration with the same
        ``orchestration_id`` already exists it is replaced; otherwise
        a new record is created.

        Parameters
        ----------
        orchestration:
            The ``Orchestration`` aggregate to persist.
        """
        ...

    def find_by_id(
        self, orchestration_id: OrchestrationId
    ) -> Orchestration | None:
        """Retrieve a single orchestration by its unique identifier.

        Parameters
        ----------
        orchestration_id:
            The ``OrchestrationId`` to look up.

        Returns
        -------
        The matching orchestration, or ``None`` if no orchestration
        exists with the given identifier.
        """
        ...

    def find_by_status(
        self, status: OrchestrationStatus
    ) -> list[Orchestration]:
        """Retrieve all orchestrations with a given status.

        Parameters
        ----------
        status:
            The ``OrchestrationStatus`` to filter by.

        Returns
        -------
        A list of ``Orchestration`` instances with the given status.
        """
        ...

    def find_all(self) -> list[Orchestration]:
        """Retrieve all orchestrations.

        Returns
        -------
        A list of all ``Orchestration`` instances in the store.
        """
        ...

    def count(self) -> int:
        """Return the total number of orchestrations.

        This count includes all statuses.

        Returns
        -------
        Total orchestration count (0 if the store is empty).
        """
        ...


class OrchestratorWorkflowRepositoryPort(Protocol):
    """Repository port for ``Workflow`` persistence.

    An implementation persists ``Workflow`` aggregates to a concrete
    store. Workflows are queryable by status and parent orchestration.
    All methods are synchronous.
    """

    def save(self, workflow: Workflow) -> None:
        """Persist a new or updated workflow.

        Uses upsert semantics — if a workflow with the same
        ``workflow_id`` already exists it is replaced; otherwise a
        new record is created.

        Parameters
        ----------
        workflow:
            The ``Workflow`` aggregate to persist.
        """
        ...

    def find_by_id(self, workflow_id: WorkflowId) -> Workflow | None:
        """Retrieve a single workflow by its unique identifier.

        Parameters
        ----------
        workflow_id:
            The ``WorkflowId`` to look up.

        Returns
        -------
        The matching workflow, or ``None`` if no workflow exists
        with the given identifier.
        """
        ...

    def find_by_status(self, status: WorkflowStatus) -> list[Workflow]:
        """Retrieve all workflows with a given status.

        Parameters
        ----------
        status:
            The ``WorkflowStatus`` to filter by.

        Returns
        -------
        A list of ``Workflow`` instances with the given status.
        """
        ...

    def find_by_orchestration_id(
        self, orchestration_id: OrchestrationId
    ) -> list[Workflow]:
        """Retrieve all workflows belonging to an orchestration.

        Parameters
        ----------
        orchestration_id:
            The ``OrchestrationId`` to search for.

        Returns
        -------
        A list of ``Workflow`` instances for the given orchestration.
        """
        ...

    def find_all(self) -> list[Workflow]:
        """Retrieve all workflows.

        Returns
        -------
        A list of all ``Workflow`` instances in the store.
        """
        ...

    def count(self) -> int:
        """Return the total number of workflows.

        Returns
        -------
        Total workflow count (0 if the store is empty).
        """
        ...


class OrchestratorStepRepositoryPort(Protocol):
    """Repository port for ``WorkflowStep`` persistence.

    An implementation persists ``WorkflowStep`` entities to a concrete
    store. Steps are queryable by status, parent workflow, and agent
    role. All methods are synchronous.
    """

    def save(self, step: WorkflowStep) -> None:
        """Persist a new or updated workflow step.

        Uses upsert semantics — if a step with the same ``step_id``
        already exists it is replaced; otherwise a new record is
        created.

        Parameters
        ----------
        step:
            The ``WorkflowStep`` to persist.
        """
        ...

    def find_by_id(self, step_id: WorkflowId) -> WorkflowStep | None:
        """Retrieve a single workflow step by its unique identifier.

        Parameters
        ----------
        step_id:
            The ``WorkflowId`` to look up.

        Returns
        -------
        The matching step, or ``None`` if no step exists with the
        given identifier.
        """
        ...

    def find_by_status(
        self, status: WorkflowStepStatus
    ) -> list[WorkflowStep]:
        """Retrieve all workflow steps with a given status.

        Parameters
        ----------
        status:
            The ``WorkflowStepStatus`` to filter by.

        Returns
        -------
        A list of ``WorkflowStep`` instances with the given status.
        """
        ...

    def find_by_workflow_id(
        self, workflow_id: WorkflowId
    ) -> list[WorkflowStep]:
        """Retrieve all steps belonging to a workflow.

        Parameters
        ----------
        workflow_id:
            The ``WorkflowId`` to search for.

        Returns
        -------
        A list of ``WorkflowStep`` instances for the given workflow.
        """
        ...

    def find_by_agent_role(
        self, agent_role: AgentRole
    ) -> list[WorkflowStep]:
        """Retrieve all workflow steps assigned to a given agent role.

        Parameters
        ----------
        agent_role:
            The ``AgentRole`` to filter by.

        Returns
        -------
        A list of ``WorkflowStep`` instances assigned to the given
        role.
        """
        ...

    def count(self) -> int:
        """Return the total number of workflow steps.

        Returns
        -------
        Total step count (0 if the store is empty).
        """
        ...

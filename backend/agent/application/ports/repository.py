from __future__ import annotations

from typing import Protocol

from backend.agent.domain.model import (
    Agent,
    AgentExecution,
    AgentExecutionId,
    AgentExecutionStatus,
    AgentId,
    AgentStatus,
    AgentTask,
    AgentTaskId,
    AgentTaskStatus,
    AgentType,
)


class AgentRepositoryPort(Protocol):
    """Repository port for ``Agent`` aggregate persistence.

    An implementation persists ``Agent`` aggregates to a concrete
    store. Agents are queryable by status and type.
    All methods are synchronous.
    """

    def save(self, agent: Agent) -> None:
        """Persist a new or updated agent.

        Uses upsert semantics — if an agent with the same
        ``agent_id`` already exists it is replaced; otherwise
        a new record is created.

        Parameters
        ----------
        agent:
            The ``Agent`` aggregate to persist.
        """
        ...

    def find_by_id(self, agent_id: AgentId) -> Agent | None:
        """Retrieve a single agent by its unique identifier.

        Parameters
        ----------
        agent_id:
            The ``AgentId`` to look up.

        Returns
        -------
        The matching agent, or ``None`` if no agent exists
        with the given identifier.
        """
        ...

    def find_by_status(self, status: AgentStatus) -> list[Agent]:
        """Retrieve all agents with a given status.

        Parameters
        ----------
        status:
            The ``AgentStatus`` to filter by.

        Returns
        -------
        A list of ``Agent`` instances with the given status.
        """
        ...

    def find_by_type(self, agent_type: AgentType) -> list[Agent]:
        """Retrieve all agents of a given type.

        Parameters
        ----------
        agent_type:
            The ``AgentType`` to filter by.

        Returns
        -------
        A list of ``Agent`` instances with the given type.
        """
        ...

    def find_all(self) -> list[Agent]:
        """Retrieve all agents.

        Returns
        -------
        A list of all ``Agent`` instances in the store.
        """
        ...

    def count(self) -> int:
        """Return the total number of agents.

        This count includes all statuses and types.

        Returns
        -------
        Total agent count (0 if the store is empty).
        """
        ...


class AgentTaskRepositoryPort(Protocol):
    """Repository port for ``AgentTask`` persistence.

    An implementation persists ``AgentTask`` entities to a concrete
    store. Tasks are queryable by status and parent agent.
    All methods are synchronous.
    """

    def save(self, task: AgentTask) -> None:
        """Persist a new or updated agent task.

        Uses upsert semantics — if a task with the same
        ``task_id`` already exists it is replaced; otherwise a
        new record is created.

        Parameters
        ----------
        task:
            The ``AgentTask`` to persist.
        """
        ...

    def find_by_id(self, task_id: AgentTaskId) -> AgentTask | None:
        """Retrieve a single task by its unique identifier.

        Parameters
        ----------
        task_id:
            The ``AgentTaskId`` to look up.

        Returns
        -------
        The matching task, or ``None`` if no task exists with
        the given identifier.
        """
        ...

    def find_by_agent_id(self, agent_id: AgentId) -> list[AgentTask]:
        """Retrieve all tasks belonging to an agent.

        Parameters
        ----------
        agent_id:
            The ``AgentId`` to search for.

        Returns
        -------
        A list of ``AgentTask`` instances for the given agent.
        """
        ...

    def find_by_status(self, status: AgentTaskStatus) -> list[AgentTask]:
        """Retrieve all tasks with a given status.

        Parameters
        ----------
        status:
            The ``AgentTaskStatus`` to filter by.

        Returns
        -------
        A list of ``AgentTask`` instances with the given status.
        """
        ...

    def find_all(self) -> list[AgentTask]:
        """Retrieve all agent tasks.

        Returns
        -------
        A list of all ``AgentTask`` instances in the store.
        """
        ...

    def count(self) -> int:
        """Return the total number of agent tasks.

        Returns
        -------
        Total task count (0 if the store is empty).
        """
        ...


class AgentExecutionRepositoryPort(Protocol):
    """Repository port for ``AgentExecution`` persistence.

    An implementation persists ``AgentExecution`` entities to a
    concrete store. Executions are queryable by status, parent
    agent, and parent task. All methods are synchronous.
    """

    def save(self, execution: AgentExecution) -> None:
        """Persist a new or updated agent execution.

        Uses upsert semantics — if an execution with the same
        ``execution_id`` already exists it is replaced; otherwise
        a new record is created.

        Parameters
        ----------
        execution:
            The ``AgentExecution`` to persist.
        """
        ...

    def find_by_id(
        self, execution_id: AgentExecutionId
    ) -> AgentExecution | None:
        """Retrieve a single execution by its unique identifier.

        Parameters
        ----------
        execution_id:
            The ``AgentExecutionId`` to look up.

        Returns
        -------
        The matching execution, or ``None`` if no execution exists
        with the given identifier.
        """
        ...

    def find_by_agent_id(self, agent_id: AgentId) -> list[AgentExecution]:
        """Retrieve all executions belonging to an agent.

        Parameters
        ----------
        agent_id:
            The ``AgentId`` to search for.

        Returns
        -------
        A list of ``AgentExecution`` instances for the given agent.
        """
        ...

    def find_by_task_id(self, task_id: AgentTaskId) -> list[AgentExecution]:
        """Retrieve all executions for a given task.

        Parameters
        ----------
        task_id:
            The ``AgentTaskId`` to search for.

        Returns
        -------
        A list of ``AgentExecution`` instances for the given task.
        """
        ...

    def find_by_status(
        self, status: AgentExecutionStatus
    ) -> list[AgentExecution]:
        """Retrieve all executions with a given status.

        Parameters
        ----------
        status:
            The ``AgentExecutionStatus`` to filter by.

        Returns
        -------
        A list of ``AgentExecution`` instances with the given
        status.
        """
        ...

    def find_all(self) -> list[AgentExecution]:
        """Retrieve all agent executions.

        Returns
        -------
        A list of all ``AgentExecution`` instances in the store.
        """
        ...

    def count(self) -> int:
        """Return the total number of agent executions.

        Returns
        -------
        Total execution count (0 if the store is empty).
        """
        ...

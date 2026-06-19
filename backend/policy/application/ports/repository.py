from __future__ import annotations

from typing import Protocol

from backend.policy.domain.model import (
    EvaluationId,
    Policy,
    PolicyEvaluation,
    PolicyEvaluationStatus,
    PolicyId,
    PolicyPriority,
    PolicyRule,
    PolicyRuleId,
    PolicyScope,
    PolicyStatus,
)


class PolicyRepositoryPort(Protocol):
    """Repository port for ``Policy`` aggregate persistence.

    An implementation persists ``Policy`` aggregates to a concrete
    store. Policies are queryable by status, priority, and scope.
    All methods are synchronous.
    """

    def save(self, policy: Policy) -> None:
        """Persist a new or updated policy.

        Uses upsert semantics — if a policy with the same
        ``policy_id`` already exists it is replaced; otherwise
        a new record is created.

        Parameters
        ----------
        policy:
            The ``Policy`` aggregate to persist.
        """
        ...

    def find_by_id(self, policy_id: PolicyId) -> Policy | None:
        """Retrieve a single policy by its unique identifier.

        Parameters
        ----------
        policy_id:
            The ``PolicyId`` to look up.

        Returns
        -------
        The matching policy, or ``None`` if no policy exists
        with the given identifier.
        """
        ...

    def find_by_status(self, status: PolicyStatus) -> list[Policy]:
        """Retrieve all policies with a given status.

        Parameters
        ----------
        status:
            The ``PolicyStatus`` to filter by.

        Returns
        -------
        A list of ``Policy`` instances with the given status.
        """
        ...

    def find_by_priority(self, priority: PolicyPriority) -> list[Policy]:
        """Retrieve all policies with a given priority.

        Parameters
        ----------
        priority:
            The ``PolicyPriority`` to filter by.

        Returns
        -------
        A list of ``Policy`` instances with the given priority.
        """
        ...

    def find_by_scope(self, scope: PolicyScope) -> list[Policy]:
        """Retrieve all policies with a given scope.

        Parameters
        ----------
        scope:
            The ``PolicyScope`` to filter by.

        Returns
        -------
        A list of ``Policy`` instances with the given scope.
        """
        ...

    def find_all(self) -> list[Policy]:
        """Retrieve all policies.

        Returns
        -------
        A list of all ``Policy`` instances.
        """
        ...

    def count(self) -> int:
        """Return the total number of policies.

        This count includes all statuses.

        Returns
        -------
        Total policy count (0 if the store is empty).
        """
        ...


class PolicyRuleRepositoryPort(Protocol):
    """Repository port for ``PolicyRule`` persistence.

    An implementation persists ``PolicyRule`` entities to a concrete
    store. Rules are queryable by policy and enabled status.
    All methods are synchronous.
    """

    def save(self, rule: PolicyRule) -> None:
        """Persist a new or updated rule.

        Uses upsert semantics — if a rule with the same
        ``rule_id`` already exists it is replaced; otherwise a
        new record is created.

        Parameters
        ----------
        rule:
            The ``PolicyRule`` to persist.
        """
        ...

    def find_by_id(self, rule_id: PolicyRuleId) -> PolicyRule | None:
        """Retrieve a single rule by its unique identifier.

        Parameters
        ----------
        rule_id:
            The ``PolicyRuleId`` to look up.

        Returns
        -------
        The matching rule, or ``None`` if no rule exists with
        the given identifier.
        """
        ...

    def find_by_policy_id(self, policy_id: PolicyId) -> list[PolicyRule]:
        """Retrieve all rules belonging to a policy.

        Parameters
        ----------
        policy_id:
            The ``PolicyId`` to search for.

        Returns
        -------
        A list of ``PolicyRule`` instances for the given policy.
        """
        ...

    def find_enabled(self) -> list[PolicyRule]:
        """Retrieve all enabled rules.

        Returns
        -------
        A list of ``PolicyRule`` instances where ``enabled`` is ``True``.
        """
        ...

    def find_all(self) -> list[PolicyRule]:
        """Retrieve all rules.

        Returns
        -------
        A list of all ``PolicyRule`` instances.
        """
        ...

    def count(self) -> int:
        """Return the total number of rules.

        Returns
        -------
        Total rule count (0 if the store is empty).
        """
        ...


class PolicyEvaluationRepositoryPort(Protocol):
    """Repository port for ``PolicyEvaluation`` persistence.

    An implementation persists ``PolicyEvaluation`` entities to a
    concrete store. Evaluations are queryable by status and parent
    policy. All methods are synchronous.
    """

    def save(self, evaluation: PolicyEvaluation) -> None:
        """Persist a new or updated evaluation.

        Uses upsert semantics — if an evaluation with the same
        ``evaluation_id`` already exists it is replaced; otherwise a
        new record is created.

        Parameters
        ----------
        evaluation:
            The ``PolicyEvaluation`` to persist.
        """
        ...

    def find_by_id(self, evaluation_id: EvaluationId) -> PolicyEvaluation | None:
        """Retrieve a single evaluation by its unique identifier.

        Parameters
        ----------
        evaluation_id:
            The ``EvaluationId`` to look up.

        Returns
        -------
        The matching evaluation, or ``None`` if no evaluation exists
        with the given identifier.
        """
        ...

    def find_by_status(
        self, status: PolicyEvaluationStatus
    ) -> list[PolicyEvaluation]:
        """Retrieve all evaluations with a given status.

        Parameters
        ----------
        status:
            The ``PolicyEvaluationStatus`` to filter by.

        Returns
        -------
        A list of ``PolicyEvaluation`` instances with the given
        status.
        """
        ...

    def find_by_policy_id(self, policy_id: PolicyId) -> list[PolicyEvaluation]:
        """Retrieve all evaluations belonging to a policy.

        Parameters
        ----------
        policy_id:
            The ``PolicyId`` to search for.

        Returns
        -------
        A list of ``PolicyEvaluation`` instances for the given
        policy.
        """
        ...

    def find_all(self) -> list[PolicyEvaluation]:
        """Retrieve all evaluations.

        Returns
        -------
        A list of all ``PolicyEvaluation`` instances.
        """
        ...

    def count(self) -> int:
        """Return the total number of evaluations.

        Returns
        -------
        Total evaluation count (0 if the store is empty).
        """
        ...

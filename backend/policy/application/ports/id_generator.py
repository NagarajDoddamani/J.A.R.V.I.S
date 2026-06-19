from __future__ import annotations

from typing import Protocol


class PolicyIdGeneratorPort(Protocol):
    """Identifier generator for the policy domain.

    Produces unique string identifiers for policies, rules,
    and evaluations. Swappable implementations allow UUID-based
    generation in production or deterministic sequences in tests.
    """

    def generate_policy_id(self) -> str:
        """Generate a unique policy identifier.

        The returned string MUST be globally unique and suitable for
        use as a ``PolicyId`` value.

        Returns
        -------
        A unique identifier string.
        """
        ...

    def generate_rule_id(self) -> str:
        """Generate a unique rule identifier.

        The returned string MUST be globally unique and suitable for
        use as a ``PolicyRuleId`` value.

        Returns
        -------
        A unique identifier string.
        """
        ...

    def generate_evaluation_id(self) -> str:
        """Generate a unique evaluation identifier.

        The returned string MUST be globally unique and suitable for
        use as an ``EvaluationId`` value.

        Returns
        -------
        A unique identifier string.
        """
        ...

from __future__ import annotations

from uuid import uuid4


class UuidGeneratorAdapter:
    def generate_policy_id(self) -> str:
        return str(uuid4())

    def generate_rule_id(self) -> str:
        return str(uuid4())

    def generate_evaluation_id(self) -> str:
        return str(uuid4())

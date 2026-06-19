from __future__ import annotations

from uuid import uuid4


class UuidGeneratorAdapter:
    def generate_orchestration_id(self) -> str:
        return str(uuid4())

    def generate_workflow_id(self) -> str:
        return str(uuid4())

    def generate_step_id(self) -> str:
        return str(uuid4())

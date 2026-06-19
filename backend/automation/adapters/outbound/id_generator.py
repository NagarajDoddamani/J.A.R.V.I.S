from __future__ import annotations

from uuid import uuid4


class UuidGeneratorAdapter:
    def generate_automation_id(self) -> str:
        return str(uuid4())

    def generate_trigger_id(self) -> str:
        return str(uuid4())

    def generate_execution_id(self) -> str:
        return str(uuid4())

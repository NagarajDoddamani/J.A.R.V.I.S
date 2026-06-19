from __future__ import annotations

from uuid import uuid4


class UuidGeneratorAdapter:
    def generate_agent_id(self) -> str:
        return uuid4().hex

    def generate_task_id(self) -> str:
        return uuid4().hex

    def generate_execution_id(self) -> str:
        return uuid4().hex

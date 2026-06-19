from __future__ import annotations

from uuid import uuid4


class UuidGeneratorAdapter:
    def generate_request_id(self) -> str:
        return str(uuid4())

    def generate_job_id(self) -> str:
        return str(uuid4())

    def generate_source_id(self) -> str:
        return str(uuid4())

from __future__ import annotations

from backend.research.application.ports.clock import ResearchClockPort
from backend.research.application.ports.id_generator import ResearchIdGeneratorPort
from backend.research.application.ports.outbox import (
    ResearchOutboxEvent,
    ResearchOutboxPort,
)
from backend.research.application.ports.repository import (
    ResearchJobRepositoryPort,
    ResearchRequestRepositoryPort,
    ResearchSourceRepositoryPort,
)

__all__ = [
    "ResearchClockPort",
    "ResearchIdGeneratorPort",
    "ResearchJobRepositoryPort",
    "ResearchOutboxEvent",
    "ResearchOutboxPort",
    "ResearchRequestRepositoryPort",
    "ResearchSourceRepositoryPort",
]

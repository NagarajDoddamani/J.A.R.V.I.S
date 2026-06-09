from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.memory.adapters.outbound.clock import SystemClockAdapter
from backend.memory.adapters.outbound.id_generator import UuidGeneratorAdapter
from backend.memory.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyConsentRepository,
    SqlAlchemyMemoryOutboxAdapter,
    SqlAlchemyMemoryRepository,
)
from backend.memory.application.use_cases.create_memory import (
    CreateMemoryUseCase,
)
from backend.memory.application.use_cases.delete_memory import (
    DeleteMemoryUseCase,
)
from backend.memory.application.use_cases.get_consent import GetConsentUseCase
from backend.memory.application.use_cases.get_memory import GetMemoryUseCase
from backend.memory.application.use_cases.grant_consent import (
    GrantConsentUseCase,
)
from backend.memory.application.use_cases.revoke_consent import (
    RevokeConsentUseCase,
)
from backend.memory.application.use_cases.search_memories import (
    SearchMemoriesUseCase,
)
from backend.memory.application.use_cases.update_memory import (
    UpdateMemoryUseCase,
)


def _memory_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyMemoryRepository:
    return SqlAlchemyMemoryRepository(db)


def _consent_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyConsentRepository:
    return SqlAlchemyConsentRepository(db)


def _outbox(
    db: Session = Depends(get_db),
) -> SqlAlchemyMemoryOutboxAdapter:
    return SqlAlchemyMemoryOutboxAdapter(db)


def _clock() -> SystemClockAdapter:
    return SystemClockAdapter()


def _id_generator() -> UuidGeneratorAdapter:
    return UuidGeneratorAdapter()


def create_memory_use_case(
    memory_repo: SqlAlchemyMemoryRepository = Depends(_memory_repo),
    consent_repo: SqlAlchemyConsentRepository = Depends(_consent_repo),
    outbox: SqlAlchemyMemoryOutboxAdapter = Depends(_outbox),
    clock: SystemClockAdapter = Depends(_clock),
    id_generator: UuidGeneratorAdapter = Depends(_id_generator),
) -> CreateMemoryUseCase:
    return CreateMemoryUseCase(
        memory_repo=memory_repo,
        consent_repo=consent_repo,
        outbox=outbox,
        clock=clock,
        id_generator=id_generator,
    )


def update_memory_use_case(
    memory_repo: SqlAlchemyMemoryRepository = Depends(_memory_repo),
    consent_repo: SqlAlchemyConsentRepository = Depends(_consent_repo),
    outbox: SqlAlchemyMemoryOutboxAdapter = Depends(_outbox),
) -> UpdateMemoryUseCase:
    return UpdateMemoryUseCase(
        memory_repo=memory_repo,
        consent_repo=consent_repo,
        outbox=outbox,
    )


def delete_memory_use_case(
    memory_repo: SqlAlchemyMemoryRepository = Depends(_memory_repo),
    outbox: SqlAlchemyMemoryOutboxAdapter = Depends(_outbox),
) -> DeleteMemoryUseCase:
    return DeleteMemoryUseCase(
        memory_repo=memory_repo,
        outbox=outbox,
    )


def get_memory_use_case(
    memory_repo: SqlAlchemyMemoryRepository = Depends(_memory_repo),
) -> GetMemoryUseCase:
    return GetMemoryUseCase(memory_repo=memory_repo)


def search_memories_use_case(
    memory_repo: SqlAlchemyMemoryRepository = Depends(_memory_repo),
) -> SearchMemoriesUseCase:
    return SearchMemoriesUseCase(memory_repo=memory_repo)


def grant_consent_use_case(
    consent_repo: SqlAlchemyConsentRepository = Depends(_consent_repo),
    outbox: SqlAlchemyMemoryOutboxAdapter = Depends(_outbox),
    clock: SystemClockAdapter = Depends(_clock),
    id_generator: UuidGeneratorAdapter = Depends(_id_generator),
) -> GrantConsentUseCase:
    return GrantConsentUseCase(
        consent_repo=consent_repo,
        outbox=outbox,
        clock=clock,
        id_generator=id_generator,
    )


def revoke_consent_use_case(
    consent_repo: SqlAlchemyConsentRepository = Depends(_consent_repo),
    outbox: SqlAlchemyMemoryOutboxAdapter = Depends(_outbox),
) -> RevokeConsentUseCase:
    return RevokeConsentUseCase(
        consent_repo=consent_repo,
        outbox=outbox,
    )


def get_consent_use_case(
    consent_repo: SqlAlchemyConsentRepository = Depends(_consent_repo),
) -> GetConsentUseCase:
    return GetConsentUseCase(consent_repo=consent_repo)

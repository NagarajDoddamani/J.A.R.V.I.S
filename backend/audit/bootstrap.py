from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.audit.adapters.outbound.clock import SystemClockAdapter
from backend.audit.adapters.outbound.id_generator import (
    UuidV7GeneratorAdapter,
)
from backend.audit.adapters.outbound.repositories import (
    SqlAlchemyAuditChainHeadRepository,
    SqlAlchemyAuditEntryRepository,
    SqlAlchemyAuditOutboxRepository,
)
from backend.audit.application.use_cases.get_by_correlation import (
    GetAuditEntriesByCorrelationUseCase,
)
from backend.audit.application.use_cases.get_chain import (
    GetAuditChainUseCase,
)
from backend.audit.application.use_cases.get_chain_head import (
    GetAuditChainHeadUseCase,
)
from backend.audit.application.use_cases.get_entry import (
    GetAuditEntryUseCase,
)
from backend.audit.application.use_cases.record_entry import (
    RecordAuditEntryUseCase,
)
from backend.core.database import get_db


def _entry_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyAuditEntryRepository:
    return SqlAlchemyAuditEntryRepository(db)


def _chain_head_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyAuditChainHeadRepository:
    return SqlAlchemyAuditChainHeadRepository(db)


def _outbox_repo(
    db: Session = Depends(get_db),
) -> SqlAlchemyAuditOutboxRepository:
    return SqlAlchemyAuditOutboxRepository(db)


def record_audit_entry_use_case(
    entry_repo: SqlAlchemyAuditEntryRepository = Depends(_entry_repo),
    chain_head_repo: SqlAlchemyAuditChainHeadRepository = Depends(
        _chain_head_repo
    ),
    outbox: SqlAlchemyAuditOutboxRepository = Depends(_outbox_repo),
) -> RecordAuditEntryUseCase:
    return RecordAuditEntryUseCase(
        entry_repo=entry_repo,
        chain_head_repo=chain_head_repo,
        outbox=outbox,
        clock=SystemClockAdapter(),
        id_generator=UuidV7GeneratorAdapter(),
    )


def get_audit_entry_use_case(
    entry_repo: SqlAlchemyAuditEntryRepository = Depends(_entry_repo),
) -> GetAuditEntryUseCase:
    return GetAuditEntryUseCase(entry_repo=entry_repo)


def get_audit_chain_use_case(
    entry_repo: SqlAlchemyAuditEntryRepository = Depends(_entry_repo),
) -> GetAuditChainUseCase:
    return GetAuditChainUseCase(entry_repo=entry_repo)


def get_audit_chain_head_use_case(
    chain_head_repo: SqlAlchemyAuditChainHeadRepository = Depends(
        _chain_head_repo
    ),
) -> GetAuditChainHeadUseCase:
    return GetAuditChainHeadUseCase(chain_head_repo=chain_head_repo)


def get_audit_entries_by_correlation_use_case(
    entry_repo: SqlAlchemyAuditEntryRepository = Depends(_entry_repo),
) -> GetAuditEntriesByCorrelationUseCase:
    return GetAuditEntriesByCorrelationUseCase(entry_repo=entry_repo)

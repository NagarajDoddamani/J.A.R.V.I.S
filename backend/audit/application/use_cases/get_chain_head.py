from __future__ import annotations

from backend.audit.application.ports.repository import (
    AuditChainHeadRepositoryPort,
)
from backend.audit.application.use_cases.dto import (
    AuditChainHeadResponse,
    GetAuditChainHeadRequest,
)
from backend.audit.application.use_cases.exceptions import (
    ChainNotFoundError,
)


class GetAuditChainHeadUseCase:
    """Retrieve the head of a named audit chain."""

    def __init__(
        self, chain_head_repo: AuditChainHeadRepositoryPort
    ) -> None:
        self._chain_head_repo = chain_head_repo

    def execute(
        self, request: GetAuditChainHeadRequest
    ) -> AuditChainHeadResponse:
        head = self._chain_head_repo.find_by_chain(request.chain_name)
        if head is None:
            raise ChainNotFoundError(request.chain_name)

        return AuditChainHeadResponse(
            chain_name=head.chain_name,
            head_hash_hex=(
                head.head_hash.hex() if head.head_hash else None
            ),
            entries_count=head.entries_count,
        )

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.policy.adapters.outbound.mapper import PolicyMapperImpl
from backend.policy.adapters.outbound.models import Base
from backend.policy.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemyPolicyOutboxAdapter,
    SqlAlchemyPolicyRepository,
)
from backend.policy.application.use_cases.create_policy import (
    CreatePolicyUseCase,
)
from backend.policy.application.use_cases.dto import CreatePolicyRequest
from backend.policy.domain.model import (
    EvaluationId,
    PolicyActivated,
    PolicyArchived,
    PolicyCreated,
    PolicyDisabled,
    PolicyEvaluationCompleted,
    PolicyEvaluationFailed,
    PolicyEvaluationStarted,
    PolicyId,
    PolicyRuleAdded,
    PolicyRuleDisabled,
    PolicyRuleEnabled,
    PolicyRuleId,
    PolicyRuleRemoved,
)
from backend.policy.nats import (
    publish_policy_outbox_events,
)

NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)

for _table in Base.metadata.tables.values():
    _table.schema = None


@pytest.fixture
def session():
    e = create_engine("sqlite://", echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    conn = e.connect()
    transaction = conn.begin()
    s = Session(bind=conn)
    yield s
    s.close()
    transaction.rollback()
    conn.close()
    e.dispose()


@pytest.fixture
def outbox(session):
    return SqlAlchemyPolicyOutboxAdapter(session)


@pytest.fixture
def mock_js():
    js = AsyncMock()
    js.publish = AsyncMock()
    return js


def _add_policy_outbox_entries(
    outbox: SqlAlchemyPolicyOutboxAdapter, session, count: int = 3
):
    policy_repo = SqlAlchemyPolicyRepository(
        session, mapper=PolicyMapperImpl()
    )
    uc = CreatePolicyUseCase(policy_repo=policy_repo, outbox=outbox)
    for i in range(count):
        uc.execute(
            CreatePolicyRequest(
                name=f"test-{i}",
                description=f"description-{i}",
                priority="medium",
                scope="global",
                version="1.0.0",
            )
        )


class TestPolicyNATSPublisher:
    @pytest.mark.asyncio
    async def test_publishes_events(
        self, outbox: SqlAlchemyPolicyOutboxAdapter, mock_js
    ) -> None:
        _add_policy_outbox_entries(outbox, outbox._session, count=2)
        await publish_policy_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        assert mock_js.publish.call_count >= 2

    @pytest.mark.asyncio
    async def test_fifo_ordering(
        self, outbox: SqlAlchemyPolicyOutboxAdapter, mock_js
    ) -> None:
        _add_policy_outbox_entries(outbox, outbox._session, count=3)
        await publish_policy_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        calls = [call[0][1] for call in mock_js.publish.call_args_list]
        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_batch_limit(
        self, outbox: SqlAlchemyPolicyOutboxAdapter, mock_js
    ) -> None:
        _add_policy_outbox_entries(outbox, outbox._session, count=5)
        await publish_policy_outbox_events(
            mock_js,
            outbox=outbox,
            batch=2,
            interval_seconds=0.1,
            max_iterations=1,
        )
        assert mock_js.publish.call_count <= 2

    @pytest.mark.asyncio
    async def test_max_iterations(
        self, outbox: SqlAlchemyPolicyOutboxAdapter, mock_js
    ) -> None:
        _add_policy_outbox_entries(outbox, outbox._session, count=2)
        await publish_policy_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=2,
        )
        assert mock_js.publish.call_count >= 2

    @pytest.mark.asyncio
    async def test_mark_published_after_publish(
        self, outbox: SqlAlchemyPolicyOutboxAdapter, mock_js, session
    ) -> None:
        _add_policy_outbox_entries(outbox, session, count=2)
        unpublished_before = outbox.fetch_unpublished()
        assert len(unpublished_before) == 2

        await publish_policy_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        session.flush()
        unpublished_after = outbox.fetch_unpublished()
        assert len(unpublished_after) == 0

    @pytest.mark.asyncio
    async def test_rollback_on_exception(
        self, outbox: SqlAlchemyPolicyOutboxAdapter, mock_js, session
    ) -> None:
        mock_js.publish = AsyncMock(side_effect=Exception("NATS error"))
        _add_policy_outbox_entries(outbox, session, count=1)
        await publish_policy_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )

    @pytest.mark.asyncio
    async def test_empty_outbox(
        self, outbox: SqlAlchemyPolicyOutboxAdapter, mock_js
    ) -> None:
        await publish_policy_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        mock_js.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_subject_for_policy_created(
        self, outbox: SqlAlchemyPolicyOutboxAdapter, mock_js
    ) -> None:
        _add_policy_outbox_entries(outbox, outbox._session, count=1)
        await publish_policy_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        args, _ = mock_js.publish.call_args
        subject = args[0]
        assert subject == "jarvis.event.policy.policy_created.v1"

    @pytest.mark.asyncio
    async def test_all_event_subjects(
        self, outbox: SqlAlchemyPolicyOutboxAdapter, mock_js
    ) -> None:
        pid = PolicyId()
        rid = PolicyRuleId()
        eid = EvaluationId()
        events = [
            PolicyCreated(pid, "n", "d", "medium", "global", "1.0.0", NOW),
            PolicyActivated(pid, NOW),
            PolicyDisabled(pid, NOW),
            PolicyArchived(pid, NOW),
            PolicyRuleAdded(rid, pid, "true", "allow", NOW),
            PolicyRuleRemoved(rid, pid, NOW),
            PolicyRuleEnabled(rid, pid, NOW),
            PolicyRuleDisabled(rid, pid, NOW),
            PolicyEvaluationStarted(pid, eid, NOW),
            PolicyEvaluationCompleted(pid, eid, "allow", "ok", NOW),
            PolicyEvaluationFailed(pid, eid, "err", NOW),
        ]
        for event in events:
            outbox.append(event)
        await publish_policy_outbox_events(
            mock_js,
            outbox=outbox,
            batch=20,
            interval_seconds=0.1,
            max_iterations=1,
        )
        assert mock_js.publish.call_count == 11

    @pytest.mark.asyncio
    async def test_envelope_contains_producer(
        self, outbox: SqlAlchemyPolicyOutboxAdapter, mock_js
    ) -> None:
        _add_policy_outbox_entries(outbox, outbox._session, count=1)
        await publish_policy_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        import json

        args, _ = mock_js.publish.call_args
        payload = json.loads(args[1].decode())
        assert payload["producer"] == "policy"
        assert "event_id" in payload
        assert "event_type" in payload
        assert "kind" in payload
        assert "aggregate_id" in payload
        assert "occurred_at" in payload

    @pytest.mark.asyncio
    async def test_policy_created_envelope_has_fields(
        self, outbox: SqlAlchemyPolicyOutboxAdapter, mock_js
    ) -> None:
        event = PolicyCreated(
            policy_id=PolicyId(),
            name="test-policy",
            description="test-desc",
            priority="high",
            scope="user",
            version="2.0.0",
            occurred_at=NOW,
        )
        outbox.append(event)
        await publish_policy_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        import json

        args, _ = mock_js.publish.call_args
        payload = json.loads(args[1].decode())
        assert payload["name"] == "test-policy"
        assert payload["description"] == "test-desc"
        assert payload["priority"] == "high"
        assert payload["scope"] == "user"
        assert payload["version"] == "2.0.0"

    @pytest.mark.asyncio
    async def test_rule_added_envelope_has_rule_fields(
        self, outbox: SqlAlchemyPolicyOutboxAdapter, mock_js
    ) -> None:
        pid = PolicyId()
        event = PolicyRuleAdded(
            rule_id=PolicyRuleId(), policy_id=pid,
            condition="x > 1", action="allow", occurred_at=NOW,
        )
        outbox.append(event)
        await publish_policy_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        import json

        args, _ = mock_js.publish.call_args
        payload = json.loads(args[1].decode())
        assert "rule_id" in payload
        assert payload["condition"] == "x > 1"
        assert payload["action"] == "allow"

    @pytest.mark.asyncio
    async def test_evaluation_failed_envelope_has_reason(
        self, outbox: SqlAlchemyPolicyOutboxAdapter, mock_js
    ) -> None:
        pid = PolicyId()
        event = PolicyEvaluationFailed(
            policy_id=pid, evaluation_id=EvaluationId(),
            failure_reason="policy violation", occurred_at=NOW,
        )
        outbox.append(event)
        await publish_policy_outbox_events(
            mock_js,
            outbox=outbox,
            batch=10,
            interval_seconds=0.1,
            max_iterations=1,
        )
        import json

        args, _ = mock_js.publish.call_args
        payload = json.loads(args[1].decode())
        assert payload["failure_reason"] == "policy violation"

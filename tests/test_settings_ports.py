from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

import pytest

from backend.settings.application.ports.clock import SettingsClockPort
from backend.settings.application.ports.id_generator import (
    SettingsIdGeneratorPort,
)
from backend.settings.application.ports.outbox import (
    SettingsDomainEvent,
    SettingsOutboxPort,
)
from backend.settings.application.ports.repository import (
    SettingsRepositoryPort,
)
from backend.settings.domain.model import (
    Setting,
    SettingCategory,
    SettingDefinition,
    SettingId,
    SettingScope,
    SettingsProfile,
    SettingsReset,
    SettingUpdated,
    Version,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_profile() -> SettingsProfile:
    registry = {
        "ui.theme": SettingDefinition(
            key="ui.theme",
            category=SettingCategory.UI,
            scope=SettingScope.USER,
            value_type="str",
            default_value="system",
            allowed_values=("light", "dark", "system"),
        ),
        "voice.wake_word_enabled": SettingDefinition(
            key="voice.wake_word_enabled",
            category=SettingCategory.VOICE,
            scope=SettingScope.USER,
            value_type="bool",
            default_value=True,
        ),
    }
    from backend.settings.domain.factory import SettingsProfileFactory

    return SettingsProfileFactory.create(registry)


def _make_updated_event(profile: SettingsProfile) -> SettingUpdated:
    return SettingUpdated(
        profile_id=profile.profile_id,
        key="ui.theme",
        old_value="system",
        new_value="dark",
        category=SettingCategory.UI,
        occurred_at=datetime.now(tz=timezone.utc),
    )


def _make_reset_event(profile: SettingsProfile) -> SettingsReset:
    return SettingsReset(
        profile_id=profile.profile_id,
        previous_count=profile.count(),
        occurred_at=datetime.now(tz=timezone.utc),
    )


# ---------------------------------------------------------------------------
# SettingsRepositoryPort Stub
# ---------------------------------------------------------------------------


class StubSettingsRepository:
    """Minimal stub conforming to SettingsRepositoryPort."""

    def __init__(self) -> None:
        self._profiles: dict[str, SettingsProfile] = {}

    def save(self, profile: SettingsProfile) -> None:
        key = str(profile.profile_id)
        self._profiles[key] = profile

    def find_by_id(self, profile_id: SettingId) -> SettingsProfile | None:
        return self._profiles.get(str(profile_id))

    def find_by_key(self, key: str) -> Setting | None:
        for profile in self._profiles.values():
            setting = profile.get(key)
            if setting is not None:
                return setting
        return None

    def get_all(self) -> list[Setting]:
        result: list[Setting] = []
        for profile in self._profiles.values():
            result.extend(profile.settings.values())
        return result


class TestSettingsRepositoryPort:
    """Contract tests for SettingsRepositoryPort."""

    @pytest.fixture
    def repo(self) -> StubSettingsRepository:
        return StubSettingsRepository()

    def test_save_and_find_by_id(self, repo: StubSettingsRepository) -> None:
        profile = _make_profile()
        repo.save(profile)
        found = repo.find_by_id(profile.profile_id)
        assert found is not None
        assert found.profile_id == profile.profile_id
        assert found.count() == 2

    def test_find_by_id_returns_none(
        self, repo: StubSettingsRepository
    ) -> None:
        missing_id = SettingId()
        assert repo.find_by_id(missing_id) is None

    def test_save_upsert_replaces_profile(
        self, repo: StubSettingsRepository
    ) -> None:
        profile = _make_profile()
        repo.save(profile)

        profile.apply_patch(
            {"ui.theme": "dark"},
            {
                "ui.theme": SettingDefinition(
                    key="ui.theme",
                    category=SettingCategory.UI,
                    scope=SettingScope.USER,
                    value_type="str",
                    default_value="system",
                    allowed_values=("light", "dark", "system"),
                ),
            },
        )
        repo.save(profile)

        found = repo.find_by_id(profile.profile_id)
        assert found is not None
        assert found.get("ui.theme") is not None
        assert found.get("ui.theme").value == "dark"  # type: ignore[union-attr]

    def test_find_by_key_returns_setting(
        self, repo: StubSettingsRepository
    ) -> None:
        profile = _make_profile()
        repo.save(profile)

        setting = repo.find_by_key("ui.theme")
        assert setting is not None
        assert setting.key == "ui.theme"
        assert setting.value == "system"

    def test_find_by_key_nonexistent_returns_none(
        self, repo: StubSettingsRepository
    ) -> None:
        repo.save(_make_profile())
        assert repo.find_by_key("nonexistent.key") is None

    def test_find_by_key_across_multiple_profiles(
        self, repo: StubSettingsRepository
    ) -> None:
        p1 = _make_profile()
        p2 = _make_profile()
        repo.save(p1)
        repo.save(p2)

        setting = repo.find_by_key("ui.theme")
        assert setting is not None
        assert setting.value == "system"

    def test_get_all_returns_flat_list(
        self, repo: StubSettingsRepository
    ) -> None:
        p1 = _make_profile()
        p2 = _make_profile()
        repo.save(p1)
        repo.save(p2)

        all_settings = repo.get_all()
        assert len(all_settings) == 4  # 2 profiles × 2 settings each
        keys = {s.key for s in all_settings}
        assert keys == {"ui.theme", "voice.wake_word_enabled"}

    def test_get_all_empty_when_no_profiles(
        self, repo: StubSettingsRepository
    ) -> None:
        assert repo.get_all() == []

    def test_save_preserves_schema_version(
        self, repo: StubSettingsRepository
    ) -> None:
        profile = _make_profile()
        repo.save(profile)
        found = repo.find_by_id(profile.profile_id)
        assert found is not None
        assert found.schema_version == Version(1, 0)

    def test_multiple_saves_same_profile_idempotent(
        self, repo: StubSettingsRepository
    ) -> None:
        profile = _make_profile()
        repo.save(profile)
        repo.save(profile)

        found = repo.find_by_id(profile.profile_id)
        assert found is not None
        assert found.count() == 2

    def test_save_with_no_settings(
        self, repo: StubSettingsRepository
    ) -> None:
        profile = SettingsProfile(profile_id=SettingId())
        repo.save(profile)
        found = repo.find_by_id(profile.profile_id)
        assert found is not None
        assert found.count() == 0

    def test_get_all_correct_number_settings(
        self, repo: StubSettingsRepository
    ) -> None:
        profile = _make_profile()
        repo.save(profile)
        assert len(repo.get_all()) == 2

    def test_find_by_key_returns_correct_value(
        self, repo: StubSettingsRepository
    ) -> None:
        profile = _make_profile()
        repo.save(profile)
        setting = repo.find_by_key("voice.wake_word_enabled")
        assert setting is not None
        assert setting.value is True


# ---------------------------------------------------------------------------
# SettingsOutboxPort Stub
# ---------------------------------------------------------------------------


class StubSettingsOutbox:
    """Minimal stub conforming to SettingsOutboxPort."""

    def __init__(self) -> None:
        self._events: dict[str, SettingsDomainEvent] = {}
        self._published: set[str] = set()
        self._order: list[str] = []

    def append(self, event: SettingsDomainEvent) -> None:
        message_id = f"msg-{len(self._order) + 1}"
        self._events[message_id] = event
        self._order.append(message_id)

    def fetch_unpublished(
        self, limit: int = 50
    ) -> list[SettingsDomainEvent]:
        results: list[SettingsDomainEvent] = []
        for mid in self._order:
            if mid not in self._published:
                results.append(self._events[mid])
                if len(results) >= limit:
                    break
        return results

    def mark_published(self, event_id: str) -> None:
        self._published.add(event_id)


class TestSettingsOutboxPort:
    """Contract tests for SettingsOutboxPort."""

    @pytest.fixture
    def outbox(self) -> StubSettingsOutbox:
        return StubSettingsOutbox()

    def test_append_updated_event(self, outbox: StubSettingsOutbox) -> None:
        profile = _make_profile()
        event = _make_updated_event(profile)
        outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], SettingUpdated)
        assert unpublished[0].key == "ui.theme"

    def test_append_reset_event(self, outbox: StubSettingsOutbox) -> None:
        profile = _make_profile()
        event = _make_reset_event(profile)
        outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], SettingsReset)
        assert unpublished[0].previous_count == 2

    def test_mark_published_excludes(
        self, outbox: StubSettingsOutbox
    ) -> None:
        profile = _make_profile()
        event = _make_updated_event(profile)
        outbox.append(event)
        outbox.mark_published("msg-1")
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 0

    def test_mark_published_idempotent(
        self, outbox: StubSettingsOutbox
    ) -> None:
        profile = _make_profile()
        event = _make_updated_event(profile)
        outbox.append(event)
        outbox.mark_published("msg-1")
        outbox.mark_published("msg-1")  # second call is no-op
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 0

    def test_fetch_respects_limit(self, outbox: StubSettingsOutbox) -> None:
        profile = _make_profile()
        for _ in range(5):
            outbox.append(_make_updated_event(profile))
        fetched = outbox.fetch_unpublished(limit=3)
        assert len(fetched) == 3

    def test_fifo_ordering(self, outbox: StubSettingsOutbox) -> None:
        profile = _make_profile()
        for key in ("a", "b", "c"):
            outbox.append(
                SettingUpdated(
                    profile_id=profile.profile_id,
                    key=key,
                    old_value=None,
                    new_value="val",
                    category=SettingCategory.UI,
                    occurred_at=datetime.now(tz=timezone.utc),
                )
            )
        unpublished = outbox.fetch_unpublished()
        assert [e.key for e in unpublished] == ["a", "b", "c"]

    def test_partial_publish(self, outbox: StubSettingsOutbox) -> None:
        profile = _make_profile()
        for _ in range(5):
            outbox.append(_make_updated_event(profile))

        outbox.mark_published("msg-1")
        outbox.mark_published("msg-2")
        outbox.mark_published("msg-3")

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 2

    def test_empty_outbox(self, outbox: StubSettingsOutbox) -> None:
        assert outbox.fetch_unpublished() == []

    def test_append_mixed_event_types(
        self, outbox: StubSettingsOutbox
    ) -> None:
        profile = _make_profile()
        outbox.append(_make_updated_event(profile))
        outbox.append(_make_reset_event(profile))

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 2
        assert isinstance(unpublished[0], SettingUpdated)
        assert isinstance(unpublished[1], SettingsReset)


# ---------------------------------------------------------------------------
# SettingsClockPort Stubs + Tests
# ---------------------------------------------------------------------------


class SystemClockStub:
    """Returns real system time — conforms to SettingsClockPort."""

    def now(self) -> datetime:
        return datetime.now(tz=timezone.utc)


class FixedClock:
    """Returns a fixed time — conforms to SettingsClockPort."""

    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        return self._fixed


class OffsetClock:
    """Returns system time offset by a delta — conforms to SettingsClockPort."""

    def __init__(self, offset_seconds: float = 0.0) -> None:
        self._offset = offset_seconds

    def now(self) -> datetime:
        from datetime import timedelta

        return datetime.now(tz=timezone.utc) + timedelta(seconds=self._offset)


class TestSettingsClockPort:
    """Contract tests for SettingsClockPort."""

    def test_system_clock_returns_utc(self) -> None:
        clock: SettingsClockPort = SystemClockStub()
        result = clock.now()
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result).total_seconds() == 0.0

    def test_fixed_clock_returns_configured_time(self) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        clock: SettingsClockPort = FixedClock(dt)
        assert clock.now() == dt

    def test_fixed_clock_is_deterministic(self) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        clock: SettingsClockPort = FixedClock(dt)
        assert clock.now() == clock.now() == dt

    def test_offset_clock_different_from_system(self) -> None:
        clock: SettingsClockPort = OffsetClock(3600)
        result = clock.now()
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_clock_protocol_conformance(self) -> None:
        def use_clock(c: SettingsClockPort) -> datetime:
            return c.now()

        assert use_clock(SystemClockStub()) is not None
        assert use_clock(
            FixedClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
        ) is not None
        assert use_clock(OffsetClock()) is not None

    def test_fixed_clock_timezone_preserved(self) -> None:
        dt = datetime(2026, 6, 9, 0, 0, 0, tzinfo=timezone.utc)
        clock: SettingsClockPort = FixedClock(dt)
        assert clock.now().tzinfo is not None


# ---------------------------------------------------------------------------
# SettingsIdGeneratorPort Stubs + Tests
# ---------------------------------------------------------------------------


class UuidGeneratorStub:
    """Generates UUID strings — conforms to SettingsIdGeneratorPort."""

    def generate(self) -> str:
        return str(SettingId())


class SequentialIdGenerator:
    """Generates deterministic sequential IDs — conforms to SettingsIdGeneratorPort."""

    def __init__(self) -> None:
        self._counter = 0

    def generate(self) -> str:
        self._counter += 1
        return f"sett-{self._counter:010d}"


class PrefixedUuidGenerator:
    """Generates prefixed UUIDs — conforms to SettingsIdGeneratorPort."""

    def __init__(self, prefix: str = "set_") -> None:
        self._prefix = prefix

    def generate(self) -> str:
        return f"{self._prefix}{SettingId()}"


class TestSettingsIdGeneratorPort:
    """Contract tests for SettingsIdGeneratorPort."""

    def test_uuid_generator_returns_string(self) -> None:
        gen: SettingsIdGeneratorPort = UuidGeneratorStub()
        result = gen.generate()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_uuid_generator_unique(self) -> None:
        gen: SettingsIdGeneratorPort = UuidGeneratorStub()
        ids = {gen.generate() for _ in range(100)}
        assert len(ids) == 100

    def test_sequential_generator(self) -> None:
        gen: SettingsIdGeneratorPort = SequentialIdGenerator()
        assert gen.generate() == "sett-0000000001"
        assert gen.generate() == "sett-0000000002"
        assert gen.generate() == "sett-0000000003"

    def test_prefixed_generator(self) -> None:
        gen: SettingsIdGeneratorPort = PrefixedUuidGenerator("cfg_")
        result = gen.generate()
        assert result.startswith("cfg_")

    def test_generator_protocol_conformance(self) -> None:
        def use_generator(g: SettingsIdGeneratorPort) -> str:
            return g.generate()

        assert isinstance(use_generator(UuidGeneratorStub()), str)
        assert use_generator(SequentialIdGenerator()) == "sett-0000000001"
        assert use_generator(PrefixedUuidGenerator()).startswith("set_")

    def test_sequential_generator_isolated(self) -> None:
        g1: SettingsIdGeneratorPort = SequentialIdGenerator()
        g2: SettingsIdGeneratorPort = SequentialIdGenerator()
        assert g1.generate() == "sett-0000000001"
        assert g1.generate() == "sett-0000000002"
        assert g2.generate() == "sett-0000000001"  # isolated state

    def test_empty_string_not_returned(self) -> None:
        gen: SettingsIdGeneratorPort = UuidGeneratorStub()
        for _ in range(10):
            assert len(gen.generate()) > 0


# ---------------------------------------------------------------------------
# Port method signature cross-verification
# ---------------------------------------------------------------------------


class TestMethodSignatures:
    """Verify that each port method signature matches expectations."""

    def test_repo_signatures(self) -> None:
        import inspect

        stub = StubSettingsRepository()
        expected = {
            "save": {"profile": SettingsProfile},
            "find_by_id": {
                "profile_id": SettingId,
            },
            "find_by_key": {"key": str},
            "get_all": {},
        }
        for method_name, params in expected.items():
            method = getattr(stub, method_name)
            sig = inspect.signature(method)
            for param_name in params:
                assert param_name in sig.parameters, (
                    f"{method_name} missing parameter {param_name!r}"
                )

    def test_outbox_signatures(self) -> None:
        stub = StubSettingsOutbox()
        assert hasattr(stub, "append")
        assert hasattr(stub, "fetch_unpublished")
        assert hasattr(stub, "mark_published")

        import inspect

        append_sig = inspect.signature(stub.append)
        assert "event" in append_sig.parameters

        fetch_sig = inspect.signature(stub.fetch_unpublished)
        assert "limit" in fetch_sig.parameters

        mark_sig = inspect.signature(stub.mark_published)
        assert "event_id" in mark_sig.parameters

    def test_clock_signature(self) -> None:
        assert hasattr(SystemClockStub(), "now")
        assert hasattr(FixedClock(datetime.now(tz=timezone.utc)), "now")
        assert hasattr(OffsetClock(), "now")

    def test_id_generator_signature(self) -> None:
        assert hasattr(UuidGeneratorStub(), "generate")
        assert hasattr(SequentialIdGenerator(), "generate")
        assert hasattr(PrefixedUuidGenerator(), "generate")

    def test_repo_protocol_structural(self) -> None:
        """Verify StubSettingsRepository satisfies SettingsRepositoryPort."""
        def use_port(p: SettingsRepositoryPort) -> None:
            p.save(_make_profile())

        use_port(StubSettingsRepository())

    def test_outbox_protocol_structural(self) -> None:
        """Verify StubSettingsOutbox satisfies SettingsOutboxPort."""
        def use_port(p: SettingsOutboxPort) -> None:
            p.append(_make_updated_event(_make_profile()))

        use_port(StubSettingsOutbox())

    def test_clock_protocol_structural(self) -> None:
        """Verify SystemClockStub satisfies SettingsClockPort."""
        def use_port(p: SettingsClockPort) -> datetime:
            return p.now()

        use_port(SystemClockStub())

    def test_id_generator_protocol_structural(self) -> None:
        """Verify UuidGeneratorStub satisfies SettingsIdGeneratorPort."""
        def use_port(p: SettingsIdGeneratorPort) -> str:
            return p.generate()

        use_port(UuidGeneratorStub())

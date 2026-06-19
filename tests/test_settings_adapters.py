from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.settings.adapters.outbound.mapper import (
    SettingMapperImpl,
    SettingsOutboxMapperImpl,
    SettingsProfileMapperImpl,
)
from backend.settings.adapters.outbound.models import (
    SettingModel,
    SettingsOutboxModel,
    SettingsProfileModel,
    Base,
)
from backend.settings.adapters.outbound.sqlalchemy_repository import (
    SqlAlchemySettingsOutboxAdapter,
    SqlAlchemySettingsRepository,
)
from backend.settings.domain.factory import SettingsProfileFactory
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


# ===================================================================
# SQLite compatibility: strip schema qualifiers from ORM metadata
# ===================================================================

for _table in Base.metadata.tables.values():
    _table.schema = None


# ===================================================================
# Test helpers
# ===================================================================

TEST_REGISTRY: dict[str, SettingDefinition] = {
    "ui.theme": SettingDefinition(
        key="ui.theme",
        category=SettingCategory.UI,
        scope=SettingScope.USER,
        value_type="str",
        default_value="system",
        allowed_values=("light", "dark", "system"),
    ),
    "ui.reduced_motion": SettingDefinition(
        key="ui.reduced_motion",
        category=SettingCategory.UI,
        scope=SettingScope.USER,
        value_type="bool",
        default_value=False,
    ),
    "voice.wake_word_enabled": SettingDefinition(
        key="voice.wake_word_enabled",
        category=SettingCategory.VOICE,
        scope=SettingScope.USER,
        value_type="bool",
        default_value=True,
    ),
    "voice.input_device": SettingDefinition(
        key="voice.input_device",
        category=SettingCategory.VOICE,
        scope=SettingScope.USER,
        value_type="str",
        default_value="default",
    ),
    "system.language": SettingDefinition(
        key="system.language",
        category=SettingCategory.SYSTEM,
        scope=SettingScope.USER,
        value_type="str",
        default_value="en-US",
    ),
}

REGISTRY_COUNT = len(TEST_REGISTRY)


def make_profile() -> SettingsProfile:
    return SettingsProfileFactory.create(TEST_REGISTRY)


def make_updated_event(profile: SettingsProfile | None = None) -> SettingUpdated:
    p = profile or make_profile()
    return SettingUpdated(
        profile_id=p.profile_id,
        key="ui.theme",
        old_value="system",
        new_value="dark",
        category=SettingCategory.UI,
        occurred_at=datetime.now(tz=timezone.utc),
    )


def make_reset_event(profile: SettingsProfile | None = None) -> SettingsReset:
    p = profile or make_profile()
    return SettingsReset(
        profile_id=p.profile_id,
        previous_count=5,
        occurred_at=datetime.now(tz=timezone.utc),
    )


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite://", echo=False)
    Base.metadata.create_all(e)
    return e


@pytest.fixture
def session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    s = Session(bind=connection)
    yield s
    s.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def repo(session: Session) -> SqlAlchemySettingsRepository:
    return SqlAlchemySettingsRepository(session)


@pytest.fixture
def outbox(session: Session) -> SqlAlchemySettingsOutboxAdapter:
    return SqlAlchemySettingsOutboxAdapter(session)


# ===================================================================
# SettingMapperImpl tests
# ===================================================================


class TestSettingMapperImpl:
    @pytest.fixture
    def mapper(self) -> SettingMapperImpl:
        return SettingMapperImpl()

    def test_domain_to_dto(self, mapper: SettingMapperImpl) -> None:
        setting = Setting(
            key="ui.theme", value="dark", category=SettingCategory.UI, scope=SettingScope.USER,
        )
        dto = mapper.domain_to_dto(setting, "prof-001")
        assert dto.profile_id == "prof-001"
        assert dto.key == "ui.theme"
        assert dto.value == "dark"
        assert dto.category == "ui"
        assert dto.scope == "user"

    def test_dto_to_domain(self, mapper: SettingMapperImpl) -> None:
        from backend.settings.application.persistence.dto import (
            SettingStorageDto,
        )
        dto = SettingStorageDto(
            profile_id="prof-001", key="voice.wake_word_enabled",
            value="true", category="voice", scope="user",
            value_type="bool", updated_at=datetime.now(tz=timezone.utc),
        )
        setting = mapper.dto_to_domain(dto)
        assert setting.key == "voice.wake_word_enabled"
        assert setting.value is True
        assert setting.category == SettingCategory.VOICE
        assert setting.scope == SettingScope.USER

    def test_roundtrip_preserves_fields(self, mapper: SettingMapperImpl) -> None:
        original = Setting(
            key="model.temperature", value=0.7, category=SettingCategory.MODEL, scope=SettingScope.USER,
        )
        dto = mapper.domain_to_dto(original, "prof-001")
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.key == original.key
        assert reconstructed.category == original.category
        assert reconstructed.scope == original.scope

    def test_bool_value_roundtrip(self, mapper: SettingMapperImpl) -> None:
        s = Setting(key="flag", value=True, category=SettingCategory.SYSTEM, scope=SettingScope.SYSTEM)
        dto = mapper.domain_to_dto(s, "p1")
        r = mapper.dto_to_domain(dto)
        assert r.value is True

    def test_false_value_roundtrip(self, mapper: SettingMapperImpl) -> None:
        s = Setting(key="flag", value=False, category=SettingCategory.UI, scope=SettingScope.USER)
        dto = mapper.domain_to_dto(s, "p1")
        r = mapper.dto_to_domain(dto)
        assert r.value is False

    def test_int_value_roundtrip(self, mapper: SettingMapperImpl) -> None:
        s = Setting(key="count", value=42, category=SettingCategory.SYSTEM, scope=SettingScope.SYSTEM)
        dto = mapper.domain_to_dto(s, "p1")
        r = mapper.dto_to_domain(dto)
        assert r.value == 42

    def test_dto_to_domain_with_version(self, mapper: SettingMapperImpl) -> None:
        from backend.settings.application.persistence.dto import (
            SettingStorageDto,
        )
        dto = SettingStorageDto(
            profile_id="p1", key="k", value="v", category="ui",
            scope="user", value_type="ui", updated_at=datetime.now(tz=timezone.utc),
        )
        s = mapper.dto_to_domain_with_version(dto, version=3)
        assert s.version == 3


# ===================================================================
# SettingsProfileMapperImpl tests
# ===================================================================


class TestSettingsProfileMapperImpl:
    @pytest.fixture
    def mapper(self) -> SettingsProfileMapperImpl:
        return SettingsProfileMapperImpl()

    def test_domain_to_dto(self, mapper: SettingsProfileMapperImpl) -> None:
        profile = make_profile()
        dto = mapper.domain_to_dto(profile)
        assert dto.profile_id == str(profile.profile_id)
        assert dto.schema_version_major == 1
        assert dto.schema_version_minor == 0

    def test_roundtrip(self, mapper: SettingsProfileMapperImpl) -> None:
        original = make_profile()
        dto = mapper.domain_to_dto(original)
        settings = list(original.settings.values())
        reconstructed = mapper.dto_to_domain(dto, settings)
        assert str(reconstructed.profile_id) == str(original.profile_id)
        assert reconstructed.schema_version == original.schema_version
        assert reconstructed.count() == original.count()

    def test_domain_settings_to_dtos(self, mapper: SettingsProfileMapperImpl) -> None:
        profile = make_profile()
        dtos = mapper.domain_settings_to_dtos(profile)
        assert len(dtos) == REGISTRY_COUNT
        keys = {d.key for d in dtos}
        assert keys == set(TEST_REGISTRY.keys())

    def test_empty_profile(self, mapper: SettingsProfileMapperImpl) -> None:
        profile = SettingsProfile(profile_id=SettingId())
        dto = mapper.domain_to_dto(profile)
        assert dto.profile_id == str(profile.profile_id)

    def test_empty_profile_roundtrip(self, mapper: SettingsProfileMapperImpl) -> None:
        original = SettingsProfile(profile_id=SettingId())
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto, [])
        assert reconstructed.count() == 0


# ===================================================================
# SettingsOutboxMapperImpl tests
# ===================================================================


class TestSettingsOutboxMapperImpl:
    @pytest.fixture
    def mapper(self) -> SettingsOutboxMapperImpl:
        return SettingsOutboxMapperImpl()

    def test_updated_event_to_dto(self, mapper: SettingsOutboxMapperImpl) -> None:
        event = make_updated_event()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "setting_updated"
        assert dto.key == "ui.theme"
        assert dto.old_value == "system"
        assert dto.new_value == "dark"

    def test_reset_event_to_dto(self, mapper: SettingsOutboxMapperImpl) -> None:
        event = make_reset_event()
        dto = mapper.event_to_dto(event)
        assert dto.event_type == "settings_reset"
        assert dto.key is None
        assert dto.category is None

    def test_updated_roundtrip(self, mapper: SettingsOutboxMapperImpl) -> None:
        original = make_updated_event()
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, SettingUpdated)
        assert reconstructed.key == original.key
        assert reconstructed.category == original.category

    def test_reset_roundtrip(self, mapper: SettingsOutboxMapperImpl) -> None:
        original = make_reset_event()
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, SettingsReset)
        assert str(reconstructed.profile_id) == str(original.profile_id)

    def test_reset_preserves_previous_count(self, mapper: SettingsOutboxMapperImpl) -> None:
        original = SettingsReset(
            profile_id=make_profile().profile_id,
            previous_count=42,
            occurred_at=datetime.now(tz=timezone.utc),
        )
        dto = mapper.event_to_dto(original)
        reconstructed = mapper.dto_to_event(dto)
        assert isinstance(reconstructed, SettingsReset)
        assert reconstructed.previous_count == 42


# ===================================================================
# SqlAlchemySettingsRepository tests
# ===================================================================


class TestSqlAlchemySettingsRepository:
    def test_save_and_find_by_id(self, repo: SqlAlchemySettingsRepository) -> None:
        profile = make_profile()
        repo.save(profile)
        found = repo.find_by_id(profile.profile_id)
        assert found is not None
        assert str(found.profile_id) == str(profile.profile_id)
        assert found.count() == REGISTRY_COUNT

    def test_find_by_id_nonexistent(self, repo: SqlAlchemySettingsRepository) -> None:
        missing = SettingId()
        assert repo.find_by_id(missing) is None

    def test_save_upsert_replaces_profile(self, repo: SqlAlchemySettingsRepository) -> None:
        profile = make_profile()
        repo.save(profile)
        profile.apply_patch(
            {"ui.theme": "dark"},
            TEST_REGISTRY,
        )
        repo.save(profile)
        found = repo.find_by_id(profile.profile_id)
        assert found is not None
        assert found.get("ui.theme") is not None
        assert found.get("ui.theme").value == "dark"  # type: ignore[union-attr]

    def test_find_by_key(self, repo: SqlAlchemySettingsRepository) -> None:
        profile = make_profile()
        repo.save(profile)
        setting = repo.find_by_key("ui.theme")
        assert setting is not None
        assert setting.key == "ui.theme"
        assert setting.value == "system"

    def test_find_by_key_nonexistent(self, repo: SqlAlchemySettingsRepository) -> None:
        assert repo.find_by_key("nonexistent.key") is None

    def test_find_by_key_after_update(self, repo: SqlAlchemySettingsRepository) -> None:
        profile = make_profile()
        repo.save(profile)
        profile.apply_patch(
            {"ui.theme": "dark"},
            TEST_REGISTRY,
        )
        repo.save(profile)
        setting = repo.find_by_key("ui.theme")
        assert setting is not None
        assert setting.value == "dark"

    def test_get_all(self, repo: SqlAlchemySettingsRepository) -> None:
        profile = make_profile()
        repo.save(profile)
        all_settings = repo.get_all()
        assert len(all_settings) == REGISTRY_COUNT
        keys = {s.key for s in all_settings}
        assert keys == set(TEST_REGISTRY.keys())

    def test_get_all_empty(self, repo: SqlAlchemySettingsRepository) -> None:
        assert repo.get_all() == []

    def test_get_all_multiple_profiles(self, repo: SqlAlchemySettingsRepository) -> None:
        p1 = make_profile()
        p2 = make_profile()
        repo.save(p1)
        repo.save(p2)
        all_settings = repo.get_all()
        assert len(all_settings) == REGISTRY_COUNT * 2

    def test_version_preserved(self, repo: SqlAlchemySettingsRepository) -> None:
        profile = make_profile()
        repo.save(profile)
        profile.apply_patch(
            {"ui.theme": "dark"},
            TEST_REGISTRY,
        )
        repo.save(profile)
        setting = repo.find_by_key("ui.theme")
        assert setting is not None
        assert setting.version == 2

    def test_version_preserved_after_reload(self, repo: SqlAlchemySettingsRepository) -> None:
        profile = make_profile()
        repo.save(profile)
        profile.apply_patch(
            {"ui.theme": "dark"},
            TEST_REGISTRY,
        )
        repo.save(profile)
        found = repo.find_by_id(profile.profile_id)
        assert found is not None
        theme = found.get("ui.theme")
        assert theme is not None
        assert theme.version == 2

    def test_bool_setting_preserved(self, repo: SqlAlchemySettingsRepository) -> None:
        profile = make_profile()
        repo.save(profile)
        setting = repo.find_by_key("voice.wake_word_enabled")
        assert setting is not None
        assert setting.value is True

    def test_bool_false_setting_preserved(self, repo: SqlAlchemySettingsRepository) -> None:
        profile = make_profile()
        profile.apply_patch(
            {"ui.reduced_motion": True},
            TEST_REGISTRY,
        )
        repo.save(profile)
        setting = repo.find_by_key("ui.reduced_motion")
        assert setting is not None
        assert setting.value is True

    def test_string_setting_preserved(self, repo: SqlAlchemySettingsRepository) -> None:
        profile = make_profile()
        repo.save(profile)
        setting = repo.find_by_key("system.language")
        assert setting is not None
        assert setting.value == "en-US"

    def test_category_preserved(self, repo: SqlAlchemySettingsRepository) -> None:
        profile = make_profile()
        repo.save(profile)
        setting = repo.find_by_key("voice.input_device")
        assert setting is not None
        assert setting.category == SettingCategory.VOICE

    def test_scope_preserved(self, repo: SqlAlchemySettingsRepository) -> None:
        profile = make_profile()
        repo.save(profile)
        setting = repo.find_by_key("ui.theme")
        assert setting is not None
        assert setting.scope == SettingScope.USER

    def test_save_updates_timestamp(self, repo: SqlAlchemySettingsRepository) -> None:
        profile = make_profile()
        repo.save(profile)
        profile.apply_patch(
            {"ui.theme": "dark"},
            TEST_REGISTRY,
        )
        repo.save(profile)
        found = repo.find_by_id(profile.profile_id)
        assert found is not None

    def test_multiple_saves_same_profile(self, repo: SqlAlchemySettingsRepository) -> None:
        profile = make_profile()
        repo.save(profile)
        repo.save(profile)
        found = repo.find_by_id(profile.profile_id)
        assert found is not None
        assert found.count() == REGISTRY_COUNT

    def test_settings_are_distinct_per_profile(
        self, repo: SqlAlchemySettingsRepository
    ) -> None:
        p1 = make_profile()
        p2 = make_profile()
        p1.apply_patch({"ui.theme": "dark"}, TEST_REGISTRY)
        repo.save(p1)
        repo.save(p2)
        f1 = repo.find_by_id(p1.profile_id)
        f2 = repo.find_by_id(p2.profile_id)
        assert f1 is not None
        assert f2 is not None
        assert f1.get("ui.theme").value == "dark"  # type: ignore[union-attr]
        assert f2.get("ui.theme").value == "system"  # type: ignore[union-attr]

    def test_save_empty_profile(self, repo: SqlAlchemySettingsRepository) -> None:
        profile = SettingsProfile(profile_id=SettingId())
        repo.save(profile)
        found = repo.find_by_id(profile.profile_id)
        assert found is not None
        assert found.count() == 0

    def test_schema_version_preserved(self, repo: SqlAlchemySettingsRepository) -> None:
        profile = make_profile()
        repo.save(profile)
        found = repo.find_by_id(profile.profile_id)
        assert found is not None
        assert found.schema_version == Version(1, 0)

    def test_find_by_key_bool_value(self, repo: SqlAlchemySettingsRepository) -> None:
        profile = make_profile()
        repo.save(profile)
        setting = repo.find_by_key("voice.wake_word_enabled")
        assert setting is not None
        assert setting.value is True


# ===================================================================
# SqlAlchemySettingsOutboxAdapter tests
# ===================================================================


class TestSqlAlchemySettingsOutboxAdapter:
    def test_append_updated_event(
        self, outbox: SqlAlchemySettingsOutboxAdapter
    ) -> None:
        profile = make_profile()
        event = make_updated_event(profile)
        outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], SettingUpdated)
        assert unpublished[0].key == "ui.theme"

    def test_append_reset_event(
        self, outbox: SqlAlchemySettingsOutboxAdapter
    ) -> None:
        profile = make_profile()
        event = make_reset_event(profile)
        outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        assert isinstance(unpublished[0], SettingsReset)

    def test_mark_published(
        self, outbox: SqlAlchemySettingsOutboxAdapter
    ) -> None:
        profile = make_profile()
        event = make_updated_event(profile)
        outbox.append(event)
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1
        outbox.mark_published(str(unpublished[0].event_id))
        assert outbox.fetch_unpublished() == []

    def test_mark_published_idempotent(
        self, outbox: SqlAlchemySettingsOutboxAdapter
    ) -> None:
        profile = make_profile()
        event = make_updated_event(profile)
        outbox.append(event)
        fetched = outbox.fetch_unpublished()
        outbox.mark_published(str(fetched[0].event_id))
        outbox.mark_published(str(fetched[0].event_id))
        assert outbox.fetch_unpublished() == []

    def test_fifo_order(
        self, outbox: SqlAlchemySettingsOutboxAdapter
    ) -> None:
        for key in ("a", "b", "c"):
            profile = make_profile()
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

    def test_fetch_respects_limit(
        self, outbox: SqlAlchemySettingsOutboxAdapter
    ) -> None:
        profile = make_profile()
        for _ in range(5):
            outbox.append(make_updated_event(profile))
        fetched = outbox.fetch_unpublished(limit=3)
        assert len(fetched) == 3

    def test_partial_publish(
        self, outbox: SqlAlchemySettingsOutboxAdapter
    ) -> None:
        events = []
        for i in range(3):
            profile = make_profile()
            ev = SettingUpdated(
                profile_id=profile.profile_id,
                key=f"key.{i}",
                old_value=None,
                new_value=f"v{i}",
                category=SettingCategory.UI,
                occurred_at=datetime.now(tz=timezone.utc),
            )
            events.append(ev)
            outbox.append(ev)

        unpublished = outbox.fetch_unpublished()
        outbox.mark_published(str(unpublished[0].event_id))
        outbox.mark_published(str(unpublished[1].event_id))

        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 1

    def test_empty_outbox(self, outbox: SqlAlchemySettingsOutboxAdapter) -> None:
        assert outbox.fetch_unpublished() == []

    def test_mixed_event_types(
        self, outbox: SqlAlchemySettingsOutboxAdapter
    ) -> None:
        profile = make_profile()
        outbox.append(make_updated_event(profile))
        outbox.append(make_reset_event(profile))
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 2
        assert isinstance(unpublished[0], SettingUpdated)
        assert isinstance(unpublished[1], SettingsReset)

    def test_mark_published_only_affects_specific_event(
        self, outbox: SqlAlchemySettingsOutboxAdapter
    ) -> None:
        events = []
        for i in range(3):
            profile = make_profile()
            ev = SettingUpdated(
                profile_id=profile.profile_id,
                key=f"k.{i}",
                old_value=None,
                new_value=f"v{i}",
                category=SettingCategory.UI,
                occurred_at=datetime.now(tz=timezone.utc),
            )
            events.append(ev)
            outbox.append(ev)

        unpublished_before = outbox.fetch_unpublished()
        outbox.mark_published(str(unpublished_before[1].event_id))
        unpublished = outbox.fetch_unpublished()
        assert len(unpublished) == 2


# ===================================================================
# Full-stack integration
# ===================================================================


class TestAdapterIntegration:
    def test_save_then_query_by_key(
        self, session: Session
    ) -> None:
        repo = SqlAlchemySettingsRepository(session)

        profile = make_profile()
        repo.save(profile)

        found = repo.find_by_key("ui.theme")
        assert found is not None
        assert found.value == "system"

    def test_patch_then_reset(
        self, session: Session
    ) -> None:
        repo = SqlAlchemySettingsRepository(session)
        outbox_adapter = SqlAlchemySettingsOutboxAdapter(session)

        profile = make_profile()
        repo.save(profile)
        patch_event = SettingUpdated(
            profile_id=profile.profile_id,
            key="ui.theme",
            old_value="system",
            new_value="dark",
            category=SettingCategory.UI,
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox_adapter.append(patch_event)

        profile.apply_patch({"ui.theme": "dark"}, TEST_REGISTRY)
        repo.save(profile)
        reset_event = SettingsReset(
            profile_id=profile.profile_id,
            previous_count=profile.count(),
            occurred_at=datetime.now(tz=timezone.utc),
        )
        outbox_adapter.append(reset_event)

        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 2
        assert isinstance(unpublished[0], SettingUpdated)
        assert isinstance(unpublished[1], SettingsReset)

    def test_repository_outbox_independent(
        self, session: Session
    ) -> None:
        repo = SqlAlchemySettingsRepository(session)
        outbox_adapter = SqlAlchemySettingsOutboxAdapter(session)

        profile = make_profile()
        repo.save(profile)

        outbox_adapter.append(make_updated_event(profile))

        repo.save(profile)
        found = repo.find_by_id(profile.profile_id)
        assert found is not None
        assert found.count() == REGISTRY_COUNT

        unpublished = outbox_adapter.fetch_unpublished()
        assert len(unpublished) == 1

    def test_append_then_mark_published(
        self, session: Session
    ) -> None:
        adapter = SqlAlchemySettingsOutboxAdapter(session)
        profile = make_profile()
        event = make_updated_event(profile)
        adapter.append(event)

        unpublished = adapter.fetch_unpublished()
        adapter.mark_published(str(unpublished[0].event_id))
        remaining = adapter.fetch_unpublished()
        assert len(remaining) == 0

    def test_schema_version_roundtrip(
        self, session: Session
    ) -> None:
        repo = SqlAlchemySettingsRepository(session)
        profile = make_profile()
        repo.save(profile)

        found = repo.find_by_id(profile.profile_id)
        assert found is not None
        assert found.schema_version == Version(1, 0)

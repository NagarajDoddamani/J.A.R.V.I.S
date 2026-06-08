from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

import pytest

from backend.settings.application.persistence.dto import (
    SettingStorageDto,
    SettingsOutboxStorageDto,
    SettingsProfileStorageDto,
)
from backend.settings.application.persistence.mapper import (
    SettingMapperProtocol,
    SettingsOutboxMapperProtocol,
    SettingsProfileMapperProtocol,
)
from backend.settings.application.persistence.schema import (
    SETTINGS_OUTBOX_TABLE,
    SETTINGS_PROFILES_TABLE,
    SETTINGS_SETTINGS_TABLE,
    ColumnContract,
    TableContract,
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
from backend.settings.domain.factory import SettingsProfileFactory


# ===================================================================
# Helpers
# ===================================================================


def _make_registry() -> dict[str, SettingDefinition]:
    return {
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
        "ui.reduced_motion": SettingDefinition(
            key="ui.reduced_motion",
            category=SettingCategory.UI,
            scope=SettingScope.USER,
            value_type="bool",
            default_value=False,
        ),
    }


def _make_profile() -> SettingsProfile:
    return SettingsProfileFactory.create(_make_registry())


def _make_updated_event() -> SettingUpdated:
    return SettingUpdated(
        profile_id=SettingId(),
        key="ui.theme",
        old_value="system",
        new_value="dark",
        category=SettingCategory.UI,
        occurred_at=datetime.now(tz=timezone.utc),
    )


def _make_reset_event() -> SettingsReset:
    return SettingsReset(
        profile_id=SettingId(),
        previous_count=3,
        occurred_at=datetime.now(tz=timezone.utc),
    )


def _convert_value(value: Any, value_type: str) -> str:
    if value is None:
        return ""
    if value_type == "bool":
        return "true" if value else "false"
    return str(value)


def _parse_value(raw: str, value_type: str) -> Any:
    if value_type == "bool":
        return raw == "true"
    if value_type == "int":
        return int(raw)
    if value_type == "float":
        return float(raw)
    if value_type == "none":
        return None
    return raw


# ===================================================================
# Stub mapper implementations (conform to mapper protocols)
# ===================================================================


class StubSettingMapper:
    """Stub conforming to ``SettingMapperProtocol``."""

    def domain_to_dto(self, setting: Setting, profile_id: str) -> SettingStorageDto:
        return SettingStorageDto(
            profile_id=profile_id,
            key=setting.key,
            value=_convert_value(setting.value, setting.category.value if setting.category else "str"),
            category=setting.category.value,
            scope=setting.scope.value,
            value_type=setting.category.value if setting.category else "str",
            updated_at=datetime.now(tz=timezone.utc),
        )

    def dto_to_domain(self, dto: SettingStorageDto) -> Setting:
        return Setting(
            key=dto.key,
            value=_parse_value(dto.value, dto.value_type),
            category=SettingCategory(dto.category),
            scope=SettingScope(dto.scope),
        )


class StubSettingsProfileMapper:
    """Stub conforming to ``SettingsProfileMapperProtocol``."""

    def domain_to_dto(self, profile: SettingsProfile) -> SettingsProfileStorageDto:
        return SettingsProfileStorageDto(
            profile_id=str(profile.profile_id),
            schema_version_major=profile.schema_version.major,
            schema_version_minor=profile.schema_version.minor,
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc),
        )

    def dto_to_domain(
        self, dto: SettingsProfileStorageDto, settings: list[Setting]
    ) -> SettingsProfile:
        sdict: dict[str, Setting] = {s.key: s for s in settings}
        return SettingsProfile(
            profile_id=SettingId(
                value=__import__("uuid", fromlist=["UUID"]).UUID(dto.profile_id)
            ),
            settings=sdict,
            schema_version=Version(major=dto.schema_version_major, minor=dto.schema_version_minor),
        )

    def domain_settings_to_dtos(
        self, profile: SettingsProfile
    ) -> list[SettingStorageDto]:
        pid = str(profile.profile_id)
        return [
            StubSettingMapper().domain_to_dto(s, pid)
            for s in profile.settings.values()
        ]


class StubSettingsOutboxMapper:
    """Stub conforming to ``SettingsOutboxMapperProtocol``."""

    def domain_to_dto(
        self, event: SettingUpdated | SettingsReset
    ) -> SettingsOutboxStorageDto:
        pid = str(event.profile_id)
        if isinstance(event, SettingUpdated):
            return SettingsOutboxStorageDto(
                event_id=pid,
                profile_id=pid,
                event_type="setting_updated",
                key=event.key,
                old_value=_convert_value(event.old_value, "str"),
                new_value=_convert_value(event.new_value, "str"),
                category=event.category.value,
                occurred_at=event.occurred_at,
            )
        return SettingsOutboxStorageDto(
            event_id=pid,
            profile_id=pid,
            event_type="settings_reset",
            key=None,
            old_value=None,
            new_value=None,
            category=None,
            occurred_at=event.occurred_at,
        )

    def dto_to_domain(
        self, dto: SettingsOutboxStorageDto
    ) -> SettingUpdated | SettingsReset:
        pid = SettingId(
            value=__import__("uuid", fromlist=["UUID"]).UUID(dto.profile_id)
        )
        if dto.event_type == "setting_updated":
            return SettingUpdated(
                profile_id=pid,
                key=dto.key or "",
                old_value=_parse_value(dto.old_value, "str") if dto.old_value else None,
                new_value=_parse_value(dto.new_value, "str") if dto.new_value else None,
                category=SettingCategory(dto.category) if dto.category else SettingCategory.UI,
                occurred_at=dto.occurred_at,
            )
        return SettingsReset(
            profile_id=pid,
            previous_count=0,
            occurred_at=dto.occurred_at,
        )


# ===================================================================
# DTO construction tests
# ===================================================================


class TestSettingStorageDto:
    def test_all_fields(self) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        dto = SettingStorageDto(
            profile_id="prof-001",
            key="ui.theme",
            value="dark",
            category="ui",
            scope="user",
            value_type="str",
            updated_at=dt,
        )
        assert dto.profile_id == "prof-001"
        assert dto.key == "ui.theme"
        assert dto.value == "dark"
        assert dto.category == "ui"
        assert dto.scope == "user"
        assert dto.value_type == "str"
        assert dto.updated_at == dt

    def test_value_none(self) -> None:
        dto = SettingStorageDto(
            profile_id="prof-001",
            key="test.key",
            value=None,
            category="system",
            scope="user",
            value_type="str",
            updated_at=datetime.now(tz=timezone.utc),
        )
        assert dto.value is None
        assert dto.key == "test.key"

    def test_frozen(self) -> None:
        dto = SettingStorageDto(
            profile_id="p", key="k", value="v",
            category="ui", scope="user", value_type="str",
            updated_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            dto.key = "changed"


class TestSettingsProfileStorageDto:
    def test_all_fields(self) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        dto = SettingsProfileStorageDto(
            profile_id="prof-001",
            schema_version_major=1,
            schema_version_minor=0,
            created_at=dt,
            updated_at=dt,
        )
        assert dto.profile_id == "prof-001"
        assert dto.schema_version_major == 1
        assert dto.schema_version_minor == 0

    def test_frozen(self) -> None:
        dto = SettingsProfileStorageDto(
            profile_id="p", schema_version_major=1,
            schema_version_minor=0, created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(AttributeError):
            dto.profile_id = "changed"


class TestSettingsOutboxStorageDto:
    def test_default_published_false(self) -> None:
        dto = SettingsOutboxStorageDto(
            event_id="evt-1",
            profile_id="prof-001",
            event_type="setting_updated",
            key="ui.theme",
            old_value="system",
            new_value="dark",
            category="ui",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        assert dto.published is False

    def test_explicit_published(self) -> None:
        dto = SettingsOutboxStorageDto(
            event_id="evt-1",
            profile_id="prof-001",
            event_type="settings_reset",
            key=None,
            old_value=None,
            new_value=None,
            category=None,
            occurred_at=datetime.now(tz=timezone.utc),
            published=True,
        )
        assert dto.published is True

    def test_reset_event_fields(self) -> None:
        dto = SettingsOutboxStorageDto(
            event_id="evt-2",
            profile_id="prof-001",
            event_type="settings_reset",
            key=None,
            old_value=None,
            new_value=None,
            category=None,
            occurred_at=datetime.now(tz=timezone.utc),
        )
        assert dto.key is None
        assert dto.category is None

    def test_updated_event_fields(self) -> None:
        dto = SettingsOutboxStorageDto(
            event_id="evt-3",
            profile_id="prof-001",
            event_type="setting_updated",
            key="ui.theme",
            old_value="system",
            new_value="dark",
            category="ui",
            occurred_at=datetime.now(tz=timezone.utc),
        )
        assert dto.key == "ui.theme"
        assert dto.old_value == "system"
        assert dto.new_value == "dark"


# ===================================================================
# Mapper protocol conformance tests
# ===================================================================


class TestSettingMapper:
    @pytest.fixture
    def mapper(self) -> StubSettingMapper:
        return StubSettingMapper()

    def test_protocol_conformance(self) -> None:
        mapper: SettingMapperProtocol = StubSettingMapper()
        assert isinstance(mapper, StubSettingMapper)

    def test_domain_to_dto(self, mapper: StubSettingMapper) -> None:
        setting = Setting(
            key="ui.theme",
            value="dark",
            category=SettingCategory.UI,
            scope=SettingScope.USER,
        )
        dto = mapper.domain_to_dto(setting, "prof-001")
        assert dto.profile_id == "prof-001"
        assert dto.key == "ui.theme"
        assert dto.value == "dark"
        assert dto.category == "ui"
        assert dto.scope == "user"

    def test_dto_to_domain(self, mapper: StubSettingMapper) -> None:
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

    def test_roundtrip(self, mapper: StubSettingMapper) -> None:
        original = Setting(
            key="model.temperature",
            value=0.7,
            category=SettingCategory.MODEL,
            scope=SettingScope.USER,
        )
        dto = mapper.domain_to_dto(original, "prof-001")
        reconstructed = mapper.dto_to_domain(dto)
        assert reconstructed.key == original.key
        assert reconstructed.category == original.category
        assert reconstructed.scope == original.scope
        assert reconstructed.value == _parse_value(
            _convert_value(original.value, "str"), "str"
        )


class TestSettingsProfileMapper:
    @pytest.fixture
    def mapper(self) -> StubSettingsProfileMapper:
        return StubSettingsProfileMapper()

    def test_protocol_conformance(self) -> None:
        mapper: SettingsProfileMapperProtocol = StubSettingsProfileMapper()
        assert isinstance(mapper, StubSettingsProfileMapper)

    def test_domain_to_dto(self, mapper: StubSettingsProfileMapper) -> None:
        profile = _make_profile()
        dto = mapper.domain_to_dto(profile)
        assert dto.profile_id == str(profile.profile_id)
        assert dto.schema_version_major == 1
        assert dto.schema_version_minor == 0

    def test_dto_to_domain(self, mapper: StubSettingsProfileMapper) -> None:
        dto = SettingsProfileStorageDto(
            profile_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            schema_version_major=1, schema_version_minor=0,
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc),
        )
        settings = [
            Setting(key="ui.theme", value="light", category=SettingCategory.UI, scope=SettingScope.USER),
        ]
        profile = mapper.dto_to_domain(dto, settings)
        assert str(profile.profile_id) == dto.profile_id
        assert profile.schema_version.major == 1
        assert profile.count() == 1

    def test_roundtrip(self, mapper: StubSettingsProfileMapper) -> None:
        original = _make_profile()
        dto = mapper.domain_to_dto(original)
        setting_dtos = mapper.domain_settings_to_dtos(original)
        settings = [StubSettingMapper().dto_to_domain(sd) for sd in setting_dtos]
        reconstructed = mapper.dto_to_domain(dto, settings)
        assert str(reconstructed.profile_id) == str(original.profile_id)
        assert reconstructed.schema_version == original.schema_version
        assert reconstructed.count() == original.count()

    def test_domain_settings_to_dtos(self, mapper: StubSettingsProfileMapper) -> None:
        profile = _make_profile()
        dtos = mapper.domain_settings_to_dtos(profile)
        assert len(dtos) == profile.count()
        keys = {d.key for d in dtos}
        assert keys == {"ui.theme", "voice.wake_word_enabled", "ui.reduced_motion"}


class TestSettingsOutboxMapper:
    @pytest.fixture
    def mapper(self) -> StubSettingsOutboxMapper:
        return StubSettingsOutboxMapper()

    def test_protocol_conformance(self) -> None:
        mapper: SettingsOutboxMapperProtocol = StubSettingsOutboxMapper()
        assert isinstance(mapper, StubSettingsOutboxMapper)

    def test_updated_event_to_dto(self, mapper: StubSettingsOutboxMapper) -> None:
        event = _make_updated_event()
        dto = mapper.domain_to_dto(event)
        assert dto.event_type == "setting_updated"
        assert dto.key == "ui.theme"
        assert dto.old_value == "system"
        assert dto.new_value == "dark"
        assert dto.category == "ui"

    def test_reset_event_to_dto(self, mapper: StubSettingsOutboxMapper) -> None:
        event = _make_reset_event()
        dto = mapper.domain_to_dto(event)
        assert dto.event_type == "settings_reset"
        assert dto.key is None
        assert dto.category is None

    def test_dto_to_updated_event(self, mapper: StubSettingsOutboxMapper) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        dto = SettingsOutboxStorageDto(
            event_id="evt-1", profile_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            event_type="setting_updated", key="ui.theme",
            old_value="system", new_value="dark", category="ui",
            occurred_at=dt,
        )
        event = mapper.dto_to_domain(dto)
        assert isinstance(event, SettingUpdated)
        assert event.key == "ui.theme"
        assert event.old_value == "system"
        assert event.new_value == "dark"

    def test_dto_to_reset_event(self, mapper: StubSettingsOutboxMapper) -> None:
        dt = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
        dto = SettingsOutboxStorageDto(
            event_id="evt-1", profile_id="01975c2f-4aef-7cf1-a940-ae54bf596280",
            event_type="settings_reset", key=None,
            old_value=None, new_value=None, category=None,
            occurred_at=dt,
        )
        event = mapper.dto_to_domain(dto)
        assert isinstance(event, SettingsReset)
        assert event.previous_count == 0

    def test_updated_roundtrip(self, mapper: StubSettingsOutboxMapper) -> None:
        original = _make_updated_event()
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert isinstance(reconstructed, SettingUpdated)
        assert reconstructed.key == original.key
        assert reconstructed.category == original.category

    def test_reset_roundtrip(self, mapper: StubSettingsOutboxMapper) -> None:
        original = _make_reset_event()
        dto = mapper.domain_to_dto(original)
        reconstructed = mapper.dto_to_domain(dto)
        assert isinstance(reconstructed, SettingsReset)
        assert str(reconstructed.profile_id) == str(original.profile_id)


# ===================================================================
# Schema contract consistency tests
# ===================================================================


class TestSchemaContracts:
    def test_profiles_column_count(self) -> None:
        assert len(SETTINGS_PROFILES_TABLE.columns) == 5

    def test_profiles_schema_name(self) -> None:
        assert SETTINGS_PROFILES_TABLE.schema == "settings"
        assert SETTINGS_PROFILES_TABLE.name == "profiles"

    def test_profiles_primary_key(self) -> None:
        assert SETTINGS_PROFILES_TABLE.primary_key == "profile_id"

    def test_profiles_no_indexes(self) -> None:
        assert SETTINGS_PROFILES_TABLE.indexes == ()

    def test_settings_column_count(self) -> None:
        assert len(SETTINGS_SETTINGS_TABLE.columns) == 7

    def test_settings_schema_name(self) -> None:
        assert SETTINGS_SETTINGS_TABLE.schema == "settings"
        assert SETTINGS_SETTINGS_TABLE.name == "settings"

    def test_settings_primary_key(self) -> None:
        assert SETTINGS_SETTINGS_TABLE.primary_key == ("profile_id", "key")

    def test_settings_indexes(self) -> None:
        expected = {"ix_settings_key", "ix_settings_category"}
        assert set(SETTINGS_SETTINGS_TABLE.indexes) == expected

    def test_settings_category_enum(self) -> None:
        col = next(
            c for c in SETTINGS_SETTINGS_TABLE.columns
            if c.name == "category"
        )
        assert col.enum_values == ("system", "privacy", "voice",
                                   "notification", "model", "ui")

    def test_settings_scope_enum(self) -> None:
        col = next(
            c for c in SETTINGS_SETTINGS_TABLE.columns
            if c.name == "scope"
        )
        assert col.enum_values == ("user", "system", "service")

    def test_settings_value_type_enum(self) -> None:
        col = next(
            c for c in SETTINGS_SETTINGS_TABLE.columns
            if c.name == "value_type"
        )
        assert col.enum_values == ("bool", "int", "float", "str", "list", "dict")

    def test_settings_nullable_columns(self) -> None:
        nullable = {
            c.name for c in SETTINGS_SETTINGS_TABLE.columns if c.nullable
        }
        assert nullable == {"value"}

    def test_outbox_column_count(self) -> None:
        assert len(SETTINGS_OUTBOX_TABLE.columns) == 9

    def test_outbox_schema_name(self) -> None:
        assert SETTINGS_OUTBOX_TABLE.schema == "settings"
        assert SETTINGS_OUTBOX_TABLE.name == "outbox"

    def test_outbox_primary_key(self) -> None:
        assert SETTINGS_OUTBOX_TABLE.primary_key == "event_id"

    def test_outbox_indexes(self) -> None:
        expected = {"ix_settings_outbox_unpublished", "ix_settings_outbox_profile"}
        assert set(SETTINGS_OUTBOX_TABLE.indexes) == expected

    def test_outbox_event_type_enum(self) -> None:
        col = next(
            c for c in SETTINGS_OUTBOX_TABLE.columns
            if c.name == "event_type"
        )
        assert col.enum_values == ("setting_updated", "settings_reset")

    def test_outbox_category_enum(self) -> None:
        col = next(
            c for c in SETTINGS_OUTBOX_TABLE.columns
            if c.name == "category"
        )
        assert col.enum_values is not None

    def test_outbox_nullable_columns(self) -> None:
        nullable = {
            c.name for c in SETTINGS_OUTBOX_TABLE.columns if c.nullable
        }
        assert nullable == {"key", "old_value", "new_value", "category"}

    def test_outbox_published_default_false(self) -> None:
        col = next(
            c for c in SETTINGS_OUTBOX_TABLE.columns
            if c.name == "published"
        )
        assert col.nullable is False
        assert col.py_type == bool


# ===================================================================
# DTO <-> Schema field alignment tests
# ===================================================================


class TestDtoFieldAlignment:
    def test_setting_dto_fields_match_settings_schema(self) -> None:
        dto_fields = {"profile_id", "key", "value", "category",
                      "scope", "value_type", "updated_at"}
        schema_cols = {c.name for c in SETTINGS_SETTINGS_TABLE.columns}
        assert dto_fields == schema_cols, (
            f"DTO fields not aligned with schema columns. "
            f"Missing from DTO: {schema_cols - dto_fields}. "
            f"Missing from schema: {dto_fields - schema_cols}."
        )

    def test_profile_dto_fields_match_profiles_schema(self) -> None:
        dto_fields = {"profile_id", "schema_version_major",
                      "schema_version_minor", "created_at", "updated_at"}
        schema_cols = {c.name for c in SETTINGS_PROFILES_TABLE.columns}
        assert dto_fields == schema_cols

    def test_outbox_dto_fields_match_outbox_schema(self) -> None:
        dto_fields = {"event_id", "profile_id", "event_type",
                      "key", "old_value", "new_value", "category",
                      "occurred_at", "published"}
        schema_cols = {c.name for c in SETTINGS_OUTBOX_TABLE.columns}
        assert dto_fields == schema_cols

    def test_setting_dto_field_types_match_schema(self) -> None:
        schema_map = {c.name: c.py_type for c in SETTINGS_SETTINGS_TABLE.columns}
        assert schema_map["profile_id"] == str
        assert schema_map["key"] == str
        assert schema_map["category"] == str
        assert schema_map["scope"] == str
        assert schema_map["value_type"] == str
        assert schema_map["updated_at"] == datetime

    def test_profile_dto_field_types_match_schema(self) -> None:
        schema_map = {c.name: c.py_type for c in SETTINGS_PROFILES_TABLE.columns}
        assert schema_map["profile_id"] == str
        assert schema_map["schema_version_major"] == int
        assert schema_map["schema_version_minor"] == int
        assert schema_map["created_at"] == datetime
        assert schema_map["updated_at"] == datetime

    def test_outbox_dto_field_types_match_schema(self) -> None:
        schema_map = {c.name: c.py_type for c in SETTINGS_OUTBOX_TABLE.columns}
        assert schema_map["event_id"] == str
        assert schema_map["profile_id"] == str
        assert schema_map["event_type"] == str
        assert schema_map["occurred_at"] == datetime
        assert schema_map["published"] == bool

    def test_setting_dto_nullability_matches_schema(self) -> None:
        schema_nullable = {
            c.name for c in SETTINGS_SETTINGS_TABLE.columns if c.nullable
        }
        dto_nullable = {"value"}
        assert schema_nullable == dto_nullable

    def test_profile_dto_nullability_matches_schema(self) -> None:
        schema_nullable = {
            c.name for c in SETTINGS_PROFILES_TABLE.columns if c.nullable
        }
        assert schema_nullable == set()

    def test_outbox_dto_nullability_matches_schema(self) -> None:
        schema_nullable = {
            c.name for c in SETTINGS_OUTBOX_TABLE.columns if c.nullable
        }
        dto_nullable = {"key", "old_value", "new_value", "category"}
        assert schema_nullable == dto_nullable


# ===================================================================
# Mapper interface signature verification
# ===================================================================


class TestMapperMethodSignatures:
    def test_setting_mapper_methods(self) -> None:
        mapper: SettingMapperProtocol = StubSettingMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")

    def test_profile_mapper_methods(self) -> None:
        mapper: SettingsProfileMapperProtocol = StubSettingsProfileMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")
        assert hasattr(mapper, "domain_settings_to_dtos")

    def test_outbox_mapper_methods(self) -> None:
        mapper: SettingsOutboxMapperProtocol = StubSettingsOutboxMapper()
        assert hasattr(mapper, "domain_to_dto")
        assert hasattr(mapper, "dto_to_domain")


# ===================================================================
# Schema value constraint alignment with domain rules
# ===================================================================


class TestSchemaDomainAlignment:
    def test_category_enum_matches_domain(self) -> None:
        expected = tuple(m.value for m in SettingCategory)
        col = next(
            c for c in SETTINGS_SETTINGS_TABLE.columns
            if c.name == "category"
        )
        assert col.enum_values is not None
        assert set(col.enum_values) == set(expected)

    def test_scope_enum_matches_domain(self) -> None:
        expected = tuple(m.value for m in SettingScope)
        col = next(
            c for c in SETTINGS_SETTINGS_TABLE.columns
            if c.name == "scope"
        )
        assert col.enum_values is not None
        assert set(col.enum_values) == set(expected)

    def test_value_type_enum_matches_domain(self) -> None:
        valid_value_types = {"bool", "int", "float", "str", "list", "dict"}
        col = next(
            c for c in SETTINGS_SETTINGS_TABLE.columns
            if c.name == "value_type"
        )
        assert col.enum_values is not None
        assert set(col.enum_values) == valid_value_types

    def test_outbox_event_type_enum_matches_events(self) -> None:
        col = next(
            c for c in SETTINGS_OUTBOX_TABLE.columns
            if c.name == "event_type"
        )
        assert col.enum_values is not None
        assert "setting_updated" in col.enum_values
        assert "settings_reset" in col.enum_values

    def test_profiles_has_no_enum_columns(self) -> None:
        enum_cols = [
            c.name for c in SETTINGS_PROFILES_TABLE.columns
            if c.enum_values is not None
        ]
        assert enum_cols == []

    def test_key_max_length_match_domain(self) -> None:
        col = next(
            c for c in SETTINGS_SETTINGS_TABLE.columns
            if c.name == "key"
        )
        assert col.max_length == 256

    def test_category_max_length(self) -> None:
        col = next(
            c for c in SETTINGS_SETTINGS_TABLE.columns
            if c.name == "category"
        )
        assert col.max_length == 32

    def test_scope_max_length(self) -> None:
        col = next(
            c for c in SETTINGS_SETTINGS_TABLE.columns
            if c.name == "scope"
        )
        assert col.max_length == 16

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.settings.adapters.outbound.mapper import (
    SettingMapperImpl,
    SettingsOutboxMapperImpl,
    SettingsProfileMapperImpl,
    _infer_type,
)
from backend.settings.adapters.outbound.models import (
    SettingModel,
    SettingsOutboxModel,
    SettingsProfileModel,
)
from backend.settings.domain.model import (
    Setting,
    SettingId,
    SettingsProfile,
    SettingsReset,
    SettingUpdated,
)


class SqlAlchemySettingsRepository:
    """SQLAlchemy-backed implementation of ``SettingsRepositoryPort``.

    Persists ``SettingsProfile`` aggregates across two tables:
    ``settings.profiles`` (profile metadata) and ``settings.settings``
    (individual setting rows). On save, the profile row is upserted
    and all setting rows are replaced.
    """

    def __init__(
        self,
        session: Session,
        profile_mapper: SettingsProfileMapperImpl | None = None,
        setting_mapper: SettingMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._profile_mapper = profile_mapper or SettingsProfileMapperImpl()
        self._setting_mapper = setting_mapper or SettingMapperImpl()

    def save(self, profile: SettingsProfile) -> None:
        now = datetime.now(tz=timezone.utc)
        pid = str(profile.profile_id)

        existing = self._session.get(SettingsProfileModel, pid)
        if existing is None:
            profile_model = SettingsProfileModel(
                profile_id=pid,
                schema_version_major=profile.schema_version.major,
                schema_version_minor=profile.schema_version.minor,
                created_at=now,
                updated_at=now,
            )
            self._session.add(profile_model)
        else:
            existing.schema_version_major = profile.schema_version.major
            existing.schema_version_minor = profile.schema_version.minor
            existing.updated_at = now

        self._session.execute(
            SettingModel.__table__.delete().where(
                SettingModel.profile_id == pid
            )
        )

        for setting in profile.settings.values():
            vt = _infer_type(setting.value)
            setting_model = SettingModel(
                profile_id=pid,
                key=setting.key,
                value=self._to_storage_value(setting.value),
                category=setting.category.value,
                scope=setting.scope.value,
                value_type=vt,
                version=setting.version,
                updated_at=now,
            )
            self._session.add(setting_model)

        self._session.flush()

    def find_by_id(self, profile_id: SettingId) -> SettingsProfile | None:
        pid = str(profile_id)
        profile_model = self._session.get(SettingsProfileModel, pid)
        if profile_model is None:
            return None

        stmt = select(SettingModel).where(
            SettingModel.profile_id == pid
        )
        setting_models = list(self._session.scalars(stmt))

        settings = [
            self._model_to_setting(m) for m in setting_models
        ]

        profile_dto = self._profile_mapper.domain_to_dto(
            SettingsProfile(profile_id=profile_id)
        )
        return self._profile_mapper.dto_to_domain(
            self._model_to_profile_dto(profile_model),
            settings,
        )

    def find_by_key(self, key: str) -> Setting | None:
        stmt = select(SettingModel).where(SettingModel.key == key)
        model = self._session.scalar(stmt)
        if model is None:
            return None
        return self._model_to_setting(model)

    def get_all(self) -> list[Setting]:
        stmt = select(SettingModel)
        models = list(self._session.scalars(stmt))
        return [self._model_to_setting(m) for m in models]

    # -- internal helpers --------------------------------------------

    @staticmethod
    def _to_storage_value(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    @staticmethod
    def _model_to_setting(model: SettingModel) -> Setting:
        from backend.settings.domain.model import (
            Setting as SettingDomain,
            SettingCategory,
            SettingScope,
        )

        raw = model.value or ""
        parsed: object = raw
        if model.value_type == "bool":
            parsed = raw == "true"
        elif model.value_type == "int":
            try:
                parsed = int(raw)
            except ValueError:
                parsed = 0
        elif model.value_type == "float":
            try:
                parsed = float(raw)
            except ValueError:
                parsed = 0.0
        return SettingDomain(
            key=model.key,
            value=parsed,
            category=SettingCategory(model.category),
            scope=SettingScope(model.scope),
            version=model.version,
        )

    @staticmethod
    def _model_to_profile_dto(
        model: SettingsProfileModel,
    ) -> object:
        from backend.settings.application.persistence.dto import (
            SettingsProfileStorageDto,
        )

        return SettingsProfileStorageDto(
            profile_id=model.profile_id,
            schema_version_major=model.schema_version_major,
            schema_version_minor=model.schema_version_minor,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SqlAlchemySettingsOutboxAdapter:
    """SQLAlchemy-backed implementation of ``SettingsOutboxPort``.

    Stores ``SettingUpdated`` and ``SettingsReset`` domain events
    in the ``settings.outbox`` table. Each event gets a unique
    UUID event_id. FIFO ordering is by ``occurred_at``.
    """

    def __init__(
        self,
        session: Session,
        mapper: SettingsOutboxMapperImpl | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or SettingsOutboxMapperImpl()

    def append(self, event: SettingUpdated | SettingsReset) -> None:
        dto = self._mapper.event_to_dto(event)
        model = SettingsOutboxModel(
            event_id=str(uuid4()),
            profile_id=dto.profile_id,
            event_type=dto.event_type,
            key=dto.key,
            old_value=dto.old_value,
            new_value=dto.new_value,
            category=dto.category,
            occurred_at=dto.occurred_at,
            published=False,
        )
        self._session.add(model)
        self._session.flush()

    def fetch_unpublished(
        self, limit: int = 50
    ) -> list[SettingUpdated | SettingsReset]:
        stmt = (
            select(SettingsOutboxModel)
            .where(SettingsOutboxModel.published == False)  # noqa: E712
            .order_by(SettingsOutboxModel.occurred_at.asc())
            .limit(limit)
        )
        models = list(self._session.scalars(stmt))
        return [self._from_model(m) for m in models]

    def mark_published(self, event_id: str) -> None:
        stmt = (
            update(SettingsOutboxModel)
            .where(
                SettingsOutboxModel.profile_id == event_id,
                SettingsOutboxModel.published == False,  # noqa: E712
            )
            .values(published=True)
        )
        result = self._session.execute(stmt)
        if result.rowcount > 0:
            self._session.flush()

    @staticmethod
    def _from_model(
        model: SettingsOutboxModel,
    ) -> SettingUpdated | SettingsReset:
        from backend.settings.domain.model import (
            SettingCategory,
            SettingId,
            SettingsReset as SettingsResetEvent,
            SettingUpdated as SettingUpdatedEvent,
        )

        pid = SettingId(value=__import__("uuid", fromlist=["UUID"]).UUID(model.profile_id))
        if model.event_type == "setting_updated":
            return SettingUpdatedEvent(
                profile_id=pid,
                key=model.key or "",
                old_value=model.old_value,
                new_value=model.new_value,
                category=SettingCategory(model.category) if model.category else SettingCategory.UI,
                occurred_at=model.occurred_at,
            )
        previous_count = int(model.old_value) if model.old_value else 0
        return SettingsResetEvent(
            profile_id=pid,
            previous_count=previous_count,
            occurred_at=model.occurred_at,
        )

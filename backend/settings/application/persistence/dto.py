from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SettingStorageDto:
    """Flat, serializable representation of a single domain ``Setting``.

    Flattens ``SettingDefinition`` fields (category, scope, value_type)
    into the DTO so that every column maps directly to a database row.
    Nullable fields mirror the database column nullability exactly.
    """

    profile_id: str
    key: str
    value: Any
    category: str
    scope: str
    value_type: str
    updated_at: datetime


@dataclass(frozen=True)
class SettingsProfileStorageDto:
    """Flat, serializable representation of a ``SettingsProfile`` aggregate.

    The profile itself carries identity, schema version, creation and
    update timestamps. Individual settings are stored in separate rows
    via ``SettingStorageDto``; the adapter uses the profile ID to
    link them.

    ``updated_at`` is managed by the adapter / database trigger (the
    domain ``SettingsProfile`` entity records it as a value object).
    """

    profile_id: str
    schema_version_major: int
    schema_version_minor: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class SettingsOutboxStorageDto:
    """Flat representation of a settings domain event for outbox storage.

    Carries enough context to reconstruct the ``SettingUpdated`` or
    ``SettingsReset`` event at the adapter layer.  The generic outbox
    table (``settings.outbox``) wraps these values in its standard
    envelope (``message_id``, ``subject``, ``created_at``, etc.).
    """

    event_id: str
    profile_id: str
    event_type: str  # "setting_updated" | "settings_reset"
    key: str | None
    old_value: str | None
    new_value: str | None
    category: str | None
    occurred_at: datetime
    published: bool = False

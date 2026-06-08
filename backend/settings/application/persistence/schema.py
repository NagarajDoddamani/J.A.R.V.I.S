from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ColumnContract:
    name: str
    py_type: type[Any]
    nullable: bool
    max_length: int | None = None
    enum_values: tuple[str, ...] | None = None


@dataclass(frozen=True)
class TableContract:
    name: str
    schema: str
    columns: tuple[ColumnContract, ...]
    primary_key: str | tuple[str, ...]
    indexes: tuple[str, ...] = ()
    unique_constraints: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# settings.profiles
# ---------------------------------------------------------------------------

SETTINGS_PROFILES_TABLE: TableContract = TableContract(
    name="profiles",
    schema="settings",
    columns=(
        ColumnContract("profile_id", str, nullable=False),
        ColumnContract("schema_version_major", int, nullable=False),
        ColumnContract("schema_version_minor", int, nullable=False),
        ColumnContract("created_at", datetime, nullable=False),
        ColumnContract("updated_at", datetime, nullable=False),
    ),
    primary_key="profile_id",
)

# ---------------------------------------------------------------------------
# settings.settings
# ---------------------------------------------------------------------------

SETTINGS_SETTINGS_TABLE: TableContract = TableContract(
    name="settings",
    schema="settings",
    columns=(
        ColumnContract("profile_id", str, nullable=False),
        ColumnContract("key", str, nullable=False, max_length=256),
        ColumnContract("value", str, nullable=True),
        ColumnContract("category", str, nullable=False, max_length=32,
                       enum_values=("system", "privacy", "voice",
                                    "notification", "model", "ui")),
        ColumnContract("scope", str, nullable=False, max_length=16,
                       enum_values=("user", "system", "service")),
        ColumnContract("value_type", str, nullable=False, max_length=16,
                       enum_values=("bool", "int", "float", "str", "list", "dict")),
        ColumnContract("updated_at", datetime, nullable=False),
    ),
    primary_key=("profile_id", "key"),
    indexes=("ix_settings_key", "ix_settings_category"),
)

# ---------------------------------------------------------------------------
# settings.outbox
# ---------------------------------------------------------------------------

SETTINGS_OUTBOX_TABLE: TableContract = TableContract(
    name="outbox",
    schema="settings",
    columns=(
        ColumnContract("event_id", str, nullable=False),
        ColumnContract("profile_id", str, nullable=False),
        ColumnContract("event_type", str, nullable=False, max_length=32,
                       enum_values=("setting_updated", "settings_reset")),
        ColumnContract("key", str, nullable=True, max_length=256),
        ColumnContract("old_value", str, nullable=True),
        ColumnContract("new_value", str, nullable=True),
        ColumnContract("category", str, nullable=True, max_length=32,
                       enum_values=("system", "privacy", "voice",
                                    "notification", "model", "ui")),
        ColumnContract("occurred_at", datetime, nullable=False),
        ColumnContract("published", bool, nullable=False),
    ),
    primary_key="event_id",
    indexes=(
        "ix_settings_outbox_unpublished",
        "ix_settings_outbox_profile",
    ),
)

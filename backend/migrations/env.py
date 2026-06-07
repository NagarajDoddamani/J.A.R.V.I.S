from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make ``backend`` importable when Alembic is invoked from the repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.core.config import settings  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Foundation-layer migrations do not use SQLAlchemy ORM metadata.
# The first iteration is hand-authored DDL; future revisions may add a
# declarative base in ``backend.core.db``.
target_metadata = None

# Per-service schemas we own from the foundation migration onward.
SERVICE_SCHEMAS: tuple[str, ...] = (
    "orchestration",
    "memory",
    "knowledge",
    "notification",
    "settings",
    "audit",
)


def _database_url() -> str:
    url = settings.POSTGRES_URL
    if not url:
        raise RuntimeError("POSTGRES_URL is not configured; check backend/.env")
    return url


def _ensure_version_schema(connection) -> None:
    """Make sure the schema hosting the Alembic version table exists.

    Alembic creates the version table lazily on first use; if the
    target schema is absent the create-table statement fails. Creating
    the schema here keeps ``version_table_schema = platform`` working
    for the foundation migration.
    """
    from sqlalchemy import text

    connection.execute(text('CREATE SCHEMA IF NOT EXISTS "platform"'))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema="platform",
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _ensure_version_schema(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema="platform",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

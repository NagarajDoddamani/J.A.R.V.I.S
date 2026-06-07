from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


def _build_postgres_url() -> str:
    """Derive a libpq DSN from the discrete PostgreSQL env variables.

    Falls back to a loopback DSN when components are absent so the
    foundation migration can run against the local Docker Compose
    cluster without requiring operators to repeat the DSN in two
    places. The connection string can still be overridden through
    the ``POSTGRES_URL`` environment variable.
    """
    explicit = os.getenv("POSTGRES_URL")
    if explicit:
        return explicit
    user = os.getenv("POSTGRES_USER", "jarvis_admin")
    password = os.getenv("POSTGRES_PASSWORD", "jarvis_secure_pass")
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "jarvis_db")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


class Settings(BaseSettings):
    PROJECT_NAME: str = "JARVIS"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # API
    API_PORT: int = 8000
    API_HOST: str = "127.0.0.1"

    # Infrastructure
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_URL: str = _build_postgres_url()
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    NATS_URL: str = "nats://127.0.0.1:4222"
    QDRANT_HOST: str = "127.0.0.1"
    QDRANT_PORT: int = 6333
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"

    # ------------------------------------------------------------------
    # NATS Governance (JDOS v1.2, Correction 10)
    # ------------------------------------------------------------------
    # Wire-level boundaries. These values are governance constants and
    # are intentionally narrow: the 256 KiB limit is the authoritative
    # boundary declared in the v1.2 addendum. Overriding these values
    # requires an ADR.
    NATS_MAX_PAYLOAD_BYTES: int = 256 * 1024  # 256 KiB
    NATS_PAYLOAD_HEADROOM_BYTES: int = 1024
    NATS_RETRY_ATTEMPTS: int = 5
    NATS_RETRY_BASE_MS: int = 250
    NATS_RETRY_MAX_BACKOFF_MS: int = 30_000
    NATS_ACK_WAIT_SECONDS: int = 30
    NATS_MAX_ACK_PENDING: int = 1000
    NATS_DUPLICATE_WINDOW_SECONDS: int = 120
    NATS_EVENTS_RETENTION_SECONDS: int = 30 * 24 * 60 * 60
    NATS_AUDIT_SIGNALS_BUFFER_SECONDS: int = 7 * 24 * 60 * 60
    NATS_STREAM_STORAGE: str = "file"
    NATS_STREAM_REPLICAS: int = 1

    # Bootstrap behaviour for the v1.2 governance topology.
    NATS_AUTO_BOOTSTRAP: bool = True

    # ------------------------------------------------------------------
    # PostgreSQL service schemas (JDOS v1.2, Correction 7 & 8)
    # ------------------------------------------------------------------
    # Per-service role names used for least-privilege production
    # connections. The dev path connects as POSTGRES_USER (the schema
    # owner) and bypasses these roles.
    POSTGRES_ROLE_ORCHESTRATION: str = "jarvis_orchestration_app"
    POSTGRES_ROLE_MEMORY: str = "jarvis_memory_app"
    POSTGRES_ROLE_KNOWLEDGE: str = "jarvis_knowledge_app"
    POSTGRES_ROLE_NOTIFICATION: str = "jarvis_notification_app"
    POSTGRES_ROLE_SETTINGS: str = "jarvis_settings_app"
    POSTGRES_ROLE_AUDIT: str = "jarvis_audit_app"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="forbid",
    )


settings = Settings()

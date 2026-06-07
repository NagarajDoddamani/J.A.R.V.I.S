from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "JARVIS"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # API
    API_PORT: int = 8000
    API_HOST: str = "127.0.0.1"

    # Infrastructure
    POSTGRES_URL: str = "postgresql+asyncpg://jarvis_admin:jarvis_secure_pass@localhost:5432/jarvis_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    NATS_URL: str = "nats://localhost:4222"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()

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
    POSTGRES_URL: str
    REDIS_URL: str
    NATS_URL: str
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # NATS Governance
    NATS_MAX_PAYLOAD: int = 1048576  # 1MB
    NATS_RETRY_ATTEMPTS: int = 5
    NATS_STREAM_RETENTION: str = "limits"
    NATS_STREAM_STORAGE: str = "file"
    NATS_STREAM_REPLICAS: int = 1

    model_config = SettingsConfigDict(
        env_file=".env", 
        case_sensitive=True, 
        extra="forbid"
    )

settings = Settings()

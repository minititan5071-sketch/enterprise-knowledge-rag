from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Enterprise Knowledge RAG"
    environment: str = "development"
    api_v1_prefix: str = ""

    database_url: str = "postgresql+psycopg://rag:rag@postgres:5432/rag"
    auto_create_tables: bool = False

    jwt_secret_key: str = Field(default="change-me-in-production", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    data_dir: Path = Path("data")
    upload_dir: Path = Path("data/uploads")
    max_upload_size_mb: int = 50

    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    celery_task_always_eager: bool = False

    vector_store: Literal["qdrant", "memory"] = "qdrant"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "enterprise_knowledge_chunks"

    embedding_provider: Literal["openai-compatible", "local"] = "local"
    embedding_base_url: str = "http://localhost:11434/v1"
    embedding_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 384

    llm_provider: Literal["openai-compatible", "local"] = "local"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0
    llm_timeout_seconds: int = 45

    rag_top_k: int = 8
    rag_min_score: float = 0.0
    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 180

    otel_enabled: bool = True
    otel_service_name: str = "enterprise-knowledge-rag-api"
    otel_exporter_otlp_endpoint: AnyHttpUrl | None = None

    frontend_backend_url: str = "http://backend:8000"

    @field_validator(
        "qdrant_api_key",
        "embedding_api_key",
        "llm_api_key",
        "otel_exporter_otlp_endpoint",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value):
        if value == "":
            return None
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()

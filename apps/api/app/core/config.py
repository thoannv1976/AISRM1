"""Application configuration loaded from environment (12-factor)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # App
    app_env: str = "local"
    app_name: str = "AISRM1"
    app_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"
    log_level: str = "INFO"
    default_locale: str = "vi"
    default_timezone: str = "Asia/Ho_Chi_Minh"
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql+psycopg://aisrm1:aisrm1@127.0.0.1:5432/aisrm1"

    # Auth
    auth_provider: str = "local"
    auth_secret: str = "dev-only-change-me-in-production-please-32+chars"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14
    jwt_algorithm: str = "HS256"
    oidc_issuer: str | None = None
    oidc_audience: str | None = None

    # Storage
    storage_driver: str = "local"
    storage_local_path: str = "./storage_local"
    minio_endpoint: str = "http://minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    gcs_bucket_documents: str = "aisrm1-documents"
    gcs_bucket_quarantine: str = "aisrm1-quarantine"

    # Tasks
    task_driver: str = "local"
    redis_url: str = "redis://redis:6379/0"
    worker_audience: str | None = None

    # AI
    llm_provider: str = "mock"
    llm_model: str = "claude-sonnet-4-6"
    anthropic_api_key: str | None = None
    vertex_project: str | None = None
    vertex_location: str | None = None
    embedding_provider: str = "mock"
    embedding_model: str = "mock-embed-768"
    embedding_dim: int = 768
    ai_monthly_budget: float = 100.0
    ai_allowed_classifications: str = "PUBLIC,INTERNAL,CONFIDENTIAL"

    # Email
    email_provider: str = "console"
    email_api_key: str | None = None

    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ai_allowed_classification_list(self) -> list[str]:
        return [c.strip().upper() for c in self.ai_allowed_classifications.split(",") if c.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

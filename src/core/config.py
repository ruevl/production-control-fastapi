from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    environment: str = "development"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/production_control"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "amqp://admin:admin@localhost:5672//"
    celery_result_backend: str = "redis://localhost:6379/1"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket_reports: str = "reports"
    minio_bucket_exports: str = "exports"
    minio_bucket_imports: str = "imports"

    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    log_level: str = "INFO"

    api_v1_prefix: str = "/api/v1"
    project_name: str = "Production Control System"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

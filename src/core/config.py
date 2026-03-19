from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    environment: str = "development"

    # --- БД / брокеры --- без дефолтов, обязательны через .env
    database_url: str
    redis_url: str
    celery_broker_url: str
    celery_result_backend: str

    # --- MinIO ---
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_secure: bool = False
    minio_bucket_reports: str = "reports"
    minio_bucket_exports: str = "exports"
    minio_bucket_imports: str = "imports"

    # --- JWT --- без дефолта, обязателен
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    log_level: str = "INFO"

    api_v1_prefix: str = "/api/v1"
    project_name: str = "Production Control System"

    # --- Валидаторы ---

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("jwt_secret_key must be at least 32 characters")
        forbidden = {"dev-secret-key-change-in-production", "secret", "changeme"}
        if v in forbidden:
            raise ValueError(f"jwt_secret_key is insecure: '{v}' is not allowed")
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.environment == "production":
            if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
                raise ValueError("localhost database_url is not allowed in production")
            if "localhost" in self.celery_broker_url:
                raise ValueError("localhost broker URL is not allowed in production")
            if self.minio_access_key in {"minioadmin", "admin"}:
                raise ValueError("Default minio_access_key is not allowed in production")
            if self.minio_secret_key in {"minioadmin", "admin"}:
                raise ValueError("Default minio_secret_key is not allowed in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
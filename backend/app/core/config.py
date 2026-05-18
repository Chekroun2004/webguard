from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: str = "development"
    debug: bool = True

    secret_key: str = "change-me-not-for-production"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    postgres_user: str = "webguard"
    postgres_password: str = "webguard"
    postgres_db: str = "webguard"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    redis_url: str = "redis://redis:6379/0"

    # Comma-separated string — pydantic-settings v2 parses list[str] as JSON,
    # which breaks plain URLs. We keep it as str and expose a property instead.
    backend_cors_origins: str = "http://localhost:5173"

    # Async task dispatch — Celery (dev) or FastAPI BackgroundTasks (prod free tier)
    use_celery: bool = True

    # Email (SMTP)
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_use_tls: bool = False
    from_email: str = "webguard@localhost"
    frontend_url: str = "http://localhost:5173"
    email_notifications_enabled: bool = True

    @property
    def cors_origins(self) -> list[str]:
        """Return CORS origins as a list (comma-separated in env var)."""
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

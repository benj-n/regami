from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache
import secrets


class Settings(BaseSettings):
    app_name: str = "Regami API"
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    access_token_expire_minutes: int = Field(default=60)
    database_url: str = Field(default="sqlite:///./regami.db")
    # Database connection settings
    db_pool_size: int = Field(default=20)
    db_max_overflow: int = Field(default=10)
    db_pool_timeout: int = Field(default=30)  # Seconds to wait for a connection from pool
    db_pool_recycle: int = Field(default=3600)  # Recycle connections after N seconds
    db_connect_timeout: int = Field(default=10)  # Seconds to wait for initial connection
    db_command_timeout: int = Field(default=30)  # Seconds to wait for query execution
    cors_origins: str = Field(default="http://localhost:5173,http://127.0.0.1:5173")
    app_env: str = Field(default="dev")
    reset_db_on_startup: bool = Field(default=False)
    # Storage
    storage_backend: str = Field(default="local")  # local | s3
    storage_local_dir: str = Field(default="./uploads")
    s3_endpoint_url: str | None = Field(default=None)
    s3_access_key: str | None = Field(default=None)
    s3_secret_key: str | None = Field(default=None)
    s3_region: str | None = Field(default=None)
    s3_bucket: str | None = Field(default=None)
    # Optional public base URL (e.g., http://localhost:9000/<bucket>) to construct browser-friendly URLs
    s3_public_base_url: str | None = Field(default=None)
    # Sentry configuration
    sentry_dsn: str | None = Field(default=None)
    sentry_environment: str | None = Field(default=None)
    sentry_traces_sample_rate: float = Field(default=0.1)  # 10% of transactions
    sentry_profiles_sample_rate: float = Field(default=0.1)  # 10% of transactions
    # Basic Auth for staging (optional)
    basic_auth_username: str | None = Field(default=None)
    basic_auth_password: str | None = Field(default=None)

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def reload_settings() -> None:
    get_settings.cache_clear()  # type: ignore[attr-defined]
    global settings
    settings = get_settings()


def validate_production_config() -> None:
    """Validate critical configuration for production environments."""
    if settings.app_env == "prod":
        # Ensure strong secret key in production
        if len(settings.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production")

        # Warn if using default database
        if "sqlite" in settings.database_url.lower():
            print("WARNING: Using SQLite in production is not recommended. Use PostgreSQL.")

        # Validate CORS configuration in production
        origins = [o.strip() for o in settings.cors_origins.split(',') if o.strip()]

        # Check for wildcard origins (security risk)
        if '*' in origins:
            raise ValueError("CORS_ORIGINS cannot contain wildcard '*' in production")

        # Ensure HTTPS-only origins
        for origin in origins:
            if not origin.startswith('https://') and origin not in ['https://localhost', 'https://127.0.0.1']:
                print(f"WARNING: CORS origin '{origin}' should use HTTPS in production")

        # Ensure at least one origin is configured
        if not origins:
            raise ValueError("CORS_ORIGINS must be configured in production")

        # Ensure reset_db is disabled
        if settings.reset_db_on_startup:
            raise ValueError("RESET_DB_ON_STARTUP must be False in production to prevent data loss")

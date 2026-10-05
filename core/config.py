# ============================
# WOLLOYEWA STORE BOT - CONFIGURATION
# ============================
"""Application configuration management using Pydantic settings."""

import secrets
from functools import lru_cache
from urllib.parse import quote, urlsplit

from cryptography.fernet import Fernet
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ============================
    # Application Core
    # ============================
    PROJECT_NAME: str = Field(default="Wolloyewa_Store_Bot")
    VERSION: str = Field(default="1.0.0")
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    TIMEZONE: str = Field(default="Africa/Addis_Ababa")
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    WEB_APP_URL: str | None = Field(default=None)

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = ["development", "staging", "production", "testing"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    @field_validator("DEBUG")
    @classmethod
    def reject_debug_in_production(cls, v: bool, info) -> bool:
        """Prevent insecure debug fallbacks from running in production."""
        if v and info.data.get("ENVIRONMENT") == "production":
            raise ValueError("DEBUG must be False in production.")
        return v

    # ============================
    # Database
    # ============================
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="")
    POSTGRES_DB: str = Field(default="wolloyewa")
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    DATABASE_URL: str | None = None
    DATABASE_POOL_SIZE: int = Field(default=20)
    DATABASE_MAX_OVERFLOW: int = Field(default=40)
    DATABASE_POOL_TIMEOUT: int = Field(default=30)
    DATABASE_POOL_RECYCLE: int = Field(default=3600)
    DATABASE_POOL_PRE_PING: bool = Field(default=True)

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def build_database_url(cls, v: str | None, info) -> str:
        """Build database URL from individual components if not provided."""
        if v:
            url = str(v)
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            return url
        data = info.data
        if data.get("ENVIRONMENT") == "testing":
            return "sqlite+aiosqlite:///./test.db"
        return f"postgresql+asyncpg://{data.get('POSTGRES_USER')}:{data.get('POSTGRES_PASSWORD')}@{data.get('POSTGRES_HOST')}:{data.get('POSTGRES_PORT')}/{data.get('POSTGRES_DB')}"

    # ============================
    # Redis
    # ============================
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: str | None = Field(default=None)
    REDIS_DB: int = Field(default=0)
    REDIS_URL: str | None = None
    REDIS_CACHE_TTL: int = Field(default=3600)
    REDIS_SESSION_TTL: int = Field(default=86400)

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def build_redis_url(cls, v: str | None, info) -> str:
        """Build Redis URL from individual components if not provided."""
        if v:
            return v
        data = info.data
        raw_password = data.get("REDIS_PASSWORD")
        password = f":{quote(str(raw_password), safe='')}@" if raw_password else ""
        return f"redis://{password}{data.get('REDIS_HOST')}:{data.get('REDIS_PORT')}/{data.get('REDIS_DB')}"

    # ============================
    # Telegram Bot
    # ============================
    TELEGRAM_BOT_TOKEN: str = Field(default="")
    TELEGRAM_WEBHOOK_URL: str | None = Field(default=None)
    TELEGRAM_WEBHOOK_SECRET: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ADMIN_IDS: str = Field(default="5848843259")

    @property
    def admin_ids_list(self) -> list[int]:
        """Return list of admin Telegram IDs."""
        return [int(id.strip()) for id in self.ADMIN_IDS.split(",") if id.strip()]

    # ============================
    # Payments
    # ============================
    # Chapa
    CHAPA_SECRET_KEY: str | None = Field(default=None)
    CHAPA_WEBHOOK_SECRET: str | None = Field(default=None)
    CHAPA_API_URL: str = Field(default="https://api.chapa.co/v1")

    # Telebirr
    TELEBIRR_APP_ID: str | None = Field(default=None)
    TELEBIRR_APP_KEY: str | None = Field(default=None)
    TELEBIRR_SHORT_CODE: str | None = Field(default=None)
    TELEBIRR_API_URL: str = Field(default="https://api.ethiotelecom.et/telebirr")

    # CBE Birr
    CBE_BIRR_MERCHANT_ID: str | None = Field(default=None)
    CBE_BIRR_TERMINAL_ID: str | None = Field(default=None)
    CBE_BIRR_SECRET_KEY: str | None = Field(default=None)
    CBE_BIRR_API_URL: str = Field(default="https://cbe-birr.api")

    # ============================
    # Storage
    # ============================
    STORAGE_PROVIDER: str = Field(default="local")
    STORAGE_BASE_URL: str = Field(default="http://localhost:8000")

    # ============================
    # Web App (Telegram Mini App)
    # ============================
    REPLIT_DOMAINS: str | None = Field(default=None)

    @property
    def web_app_url(self) -> str:
        """Public URL for the Telegram Mini App store page."""
        if self.WEB_APP_URL:
            url = self.WEB_APP_URL.strip()
            return url.rstrip("/") + "/" if url else ""
        if self.REPLIT_DOMAINS:
            domain = self.REPLIT_DOMAINS.split(",")[0].strip()
            return f"https://{domain}/app/" if domain else ""
        return ""

    @web_app_url.setter
    def web_app_url(self, value: str | None) -> None:
        normalized = value.strip() if value else ""
        parsed = urlsplit(normalized)
        if parsed.scheme != "https" or not parsed.netloc:
            self.WEB_APP_URL = None
            return
        self.WEB_APP_URL = normalized.rstrip("/") + "/"

    @web_app_url.deleter
    def web_app_url(self) -> None:
        self.WEB_APP_URL = None

    def __setattr__(self, name: str, value: object) -> None:
        if name == "web_app_url":
            normalized = value.strip() if isinstance(value, str) else ""
            parsed = urlsplit(normalized)
            self.WEB_APP_URL = (
                normalized.rstrip("/") + "/"
                if parsed.scheme == "https" and parsed.netloc
                else None
            )
            return
        super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        if name == "web_app_url":
            self.WEB_APP_URL = None
            return
        super().__delattr__(name)

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str | None = Field(default=None)
    CLOUDINARY_API_KEY: str | None = Field(default=None)
    CLOUDINARY_API_SECRET: str | None = Field(default=None)

    # AWS S3
    AWS_ACCESS_KEY_ID: str | None = Field(default=None)
    AWS_SECRET_ACCESS_KEY: str | None = Field(default=None)
    AWS_S3_BUCKET_NAME: str | None = Field(default=None)
    AWS_REGION: str = Field(default="eu-north-1")

    # ============================
    # Email & SMS
    # ============================
    SMTP_HOST: str = Field(default="smtp.gmail.com")
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: str | None = Field(default=None)
    SMTP_PASSWORD: str | None = Field(default=None)
    EMAIL_FROM: str = Field(default="noreply@wolloyewa.com")

    SMS_PROVIDER: str = Field(default="ethio_telecom")
    SMS_API_KEY: str | None = Field(default=None)
    SMS_SENDER_ID: str = Field(default="WOLLOYEWA")

    # ============================
    # Monitoring
    # ============================
    PROMETHEUS_ENABLED: bool = Field(default=True)
    PROMETHEUS_PORT: int = Field(default=9090)
    GRAFANA_ENABLED: bool = Field(default=True)
    SENTRY_DSN: str | None = Field(default=None)
    OTEL_TRACING_ENABLED: bool = Field(default=False)
    OTEL_EXPORTER_ENDPOINT: str | None = Field(default=None)

    # ============================
    # Rate Limiting
    # ============================
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, gt=0)
    RATE_LIMIT_PER_HOUR: int = Field(default=1000, gt=0)
    RATE_LIMIT_STRATEGY: str = Field(default="sliding_window")

    # ============================
    # Security
    # ============================
    JWT_SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRY_MINUTES: int = Field(default=1440)
    CORS_ALLOWED_ORIGINS: list[str] = Field(default_factory=lambda: ["*"])
    ALLOWED_HOSTS: list[str] = Field(default_factory=lambda: ["*"])
    ENCRYPTION_KEY: str | None = Field(default=None)
    GDPR_COMPLIANT: bool = Field(default=True)
    DATA_RETENTION_DAYS: int = Field(default=365)
    AUDIT_LOG_ENABLED: bool = Field(default=True)

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        """Parse allowed hosts from string or list."""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
        return v

    @field_validator("SECRET_KEY", "JWT_SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_keys(cls, v, info):
        """Ensure critical secrets are set in production."""
        if info.data.get("ENVIRONMENT") == "production" and not v:
            raise ValueError("SECRET_KEY and JWT_SECRET_KEY must be set in production.")
        return v or secrets.token_urlsafe(32)

    @model_validator(mode="after")
    def validate_production_configuration(self):
        """Reject insecure production defaults and derive allowlists from Replit domains."""
        if self.ENVIRONMENT != "production":
            return self

        required = (
            "SECRET_KEY",
            "JWT_SECRET_KEY",
            "ENCRYPTION_KEY",
            "DATABASE_URL",
            "REDIS_URL",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_WEBHOOK_SECRET",
            "ADMIN_IDS",
        )
        missing = [
            name
            for name in required
            if name not in self.model_fields_set or not getattr(self, name)
        ]
        if missing:
            raise ValueError(
                "Production requires non-empty, explicitly configured values for: "
                + ", ".join(missing)
            )

        if self.SECRET_KEY == self.JWT_SECRET_KEY:
            raise ValueError("SECRET_KEY and JWT_SECRET_KEY must be different values.")
        if self.DEV_SKIP_MIDDLEWARES:
            raise ValueError("DEV_SKIP_MIDDLEWARES must be False in production.")
        if self.DEV_FAKE_PAYMENT or self.DEV_POPULATE_DUMMY_DATA:
            raise ValueError(
                "DEV_FAKE_PAYMENT and DEV_POPULATE_DUMMY_DATA must be False in production."
            )
        if not self.RATE_LIMIT_ENABLED:
            raise ValueError("RATE_LIMIT_ENABLED must be True in production.")
        try:
            if not self.admin_ids_list:
                raise ValueError("ADMIN_IDS must include at least one numeric administrator ID.")
        except ValueError as exc:
            raise ValueError("ADMIN_IDS must contain only comma-separated numeric IDs.") from exc

        for name, value in (
            ("SECRET_KEY", self.SECRET_KEY),
            ("JWT_SECRET_KEY", self.JWT_SECRET_KEY),
            ("TELEGRAM_WEBHOOK_SECRET", self.TELEGRAM_WEBHOOK_SECRET),
            ("TELEGRAM_BOT_TOKEN", self.TELEGRAM_BOT_TOKEN),
            ("DATABASE_URL", self.DATABASE_URL or ""),
            ("REDIS_URL", self.REDIS_URL or ""),
        ):
            if not value or "CHANGE_ME" in value:
                raise ValueError(f"{name} must be configured and cannot contain a CHANGE_ME placeholder.")
            if name in {"SECRET_KEY", "JWT_SECRET_KEY", "TELEGRAM_WEBHOOK_SECRET"} and len(value) < 32:
                raise ValueError(f"{name} must be at least 32 characters long.")

        try:
            Fernet(self.ENCRYPTION_KEY.encode("utf-8"))
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("ENCRYPTION_KEY must be a valid Fernet key.") from exc

        domains = []
        if self.REPLIT_DOMAINS:
            domains = [
                entry.strip().split("://")[-1].split("/")[0].split(":")[0]
                for entry in self.REPLIT_DOMAINS.split(",")
                if entry.strip()
            ]
        elif self.WEB_APP_URL:
            host = self.WEB_APP_URL.split("://")[-1].split("/")[0].split(":")[0]
            if host:
                domains = [host]

        if domains:
            if self.CORS_ALLOWED_ORIGINS == ["*"]:
                self.CORS_ALLOWED_ORIGINS = [f"https://{domain}" for domain in domains]
            if self.ALLOWED_HOSTS == ["*"]:
                self.ALLOWED_HOSTS = domains

        if not self.CORS_ALLOWED_ORIGINS or "*" in self.CORS_ALLOWED_ORIGINS:
            raise ValueError(
                "Production requires CORS_ALLOWED_ORIGINS to be an explicit origin allowlist."
            )
        if not self.ALLOWED_HOSTS or "*" in self.ALLOWED_HOSTS:
            raise ValueError(
                "Production requires ALLOWED_HOSTS to be an explicit host allowlist."
            )
        return self

    # ============================
    # Feature Flags
    # ============================
    ENABLE_PUSH_NOTIFICATIONS: bool = Field(default=True)
    ENABLE_WEB_APP: bool = Field(default=True)
    ENABLE_AI_SUPPORT_BOT: bool = Field(default=False)
    ENABLE_LOYALTY_PROGRAM: bool = Field(default=True)
    ENABLE_ESCROW_SERVICE: bool = Field(default=False)
    ENABLE_AB_TESTING: bool = Field(default=False)

    # ============================
    # Celery
    # ============================
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None
    CELERY_TASK_ALWAYS_EAGER: bool = Field(default=False)
    CELERY_WORKER_CONCURRENCY: int = Field(default=4)

    @field_validator("CELERY_BROKER_URL", "CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def build_celery_urls(cls, v: str | None, info) -> str:
        """Build Celery URLs from Redis URL if not provided."""
        if v:
            return str(v)
        data = info.data
        redis_url = data.get("REDIS_URL", "redis://localhost:6379/0")
        return str(redis_url)

    # ============================
    # Logging
    # ============================
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")
    LOG_FILE_PATH: str = Field(default="./logs/bot_errors.log")

    # ============================
    # Backup
    # ============================
    BACKUP_ENABLED: bool = Field(default=True)
    BACKUP_SCHEDULE: str = Field(default="0 2 * * *")
    BACKUP_RETENTION_DAYS: int = Field(default=30)
    BACKUP_STORAGE_PATH: str = Field(default="/backups")

    # ============================
    # Session Limits (from image)
    # ============================
    MAX_ACTIVE_SESSIONS: int = Field(default=15)
    MAX_IDLE_SESSIONS: int = Field(default=10)
    SESSION_TIMEOUT_MINUTES: int = Field(default=30)
    TRANSACTIONS_PER_SECOND_ACTIVE: int = Field(default=4)
    TRANSACTIONS_PER_SECOND_IDLE: int = Field(default=2)

    # ============================
    # Development Only
    # ============================
    DEV_FAKE_PAYMENT: bool = Field(default=False)
    DEV_POPULATE_DUMMY_DATA: bool = Field(default=False)
    DEV_SKIP_MIDDLEWARES: bool = Field(default=False)

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.ENVIRONMENT == "testing"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()

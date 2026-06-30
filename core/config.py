# ============================
# WOLLOYEWA STORE BOT - CONFIGURATION
# ============================
"""Application configuration management using Pydantic settings."""

import secrets
from typing import List, Optional
from functools import lru_cache

from pydantic import Field, field_validator, AnyUrl, PostgresDsn, RedisDsn
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
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = ["development", "staging", "production", "testing"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v
    
    # ============================
    # Database
    # ============================
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="")
    POSTGRES_DB: str = Field(default="wolloyewa")
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    DATABASE_URL: Optional[str] = None
    DATABASE_POOL_SIZE: int = Field(default=20)
    DATABASE_MAX_OVERFLOW: int = Field(default=40)
    DATABASE_POOL_TIMEOUT: int = Field(default=30)
    DATABASE_POOL_RECYCLE: int = Field(default=3600)
    DATABASE_POOL_PRE_PING: bool = Field(default=True)
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def build_database_url(cls, v: Optional[str], info) -> str:
        """Build database URL from individual components if not provided."""
        if v:
            url = str(v)
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            return url
        data = info.data
        return f"postgresql+asyncpg://{data.get('POSTGRES_USER')}:{data.get('POSTGRES_PASSWORD')}@{data.get('POSTGRES_HOST')}:{data.get('POSTGRES_PORT')}/{data.get('POSTGRES_DB')}"
    
    # ============================
    # Redis
    # ============================
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    REDIS_DB: int = Field(default=0)
    REDIS_URL: Optional[str] = None
    REDIS_CACHE_TTL: int = Field(default=3600)
    REDIS_SESSION_TTL: int = Field(default=86400)
    
    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def build_redis_url(cls, v: Optional[str], info) -> str:
        """Build Redis URL from individual components if not provided."""
        if v:
            return v
        data = info.data
        password = f":{data.get('REDIS_PASSWORD')}@" if data.get('REDIS_PASSWORD') else ""
        return f"redis://{password}{data.get('REDIS_HOST')}:{data.get('REDIS_PORT')}/{data.get('REDIS_DB')}"
    
    # ============================
    # Telegram Bot
    # ============================
    TELEGRAM_BOT_TOKEN: str = Field(default="")
    TELEGRAM_WEBHOOK_URL: Optional[str] = Field(default=None)
    TELEGRAM_WEBHOOK_SECRET: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ADMIN_IDS: str = Field(default="5848843259")
    
    @property
    def admin_ids_list(self) -> List[int]:
        """Return list of admin Telegram IDs."""
        return [int(id.strip()) for id in self.ADMIN_IDS.split(",") if id.strip()]
    
    # ============================
    # Payments
    # ============================
    # Chapa
    CHAPA_SECRET_KEY: Optional[str] = Field(default=None)
    CHAPA_WEBHOOK_SECRET: Optional[str] = Field(default=None)
    CHAPA_API_URL: str = Field(default="https://api.chapa.co/v1")
    
    # Telebirr
    TELEBIRR_APP_ID: Optional[str] = Field(default=None)
    TELEBIRR_APP_KEY: Optional[str] = Field(default=None)
    TELEBIRR_SHORT_CODE: Optional[str] = Field(default=None)
    TELEBIRR_API_URL: str = Field(default="https://api.ethiotelecom.et/telebirr")
    
    # CBE Birr
    CBE_BIRR_MERCHANT_ID: Optional[str] = Field(default=None)
    CBE_BIRR_TERMINAL_ID: Optional[str] = Field(default=None)
    CBE_BIRR_SECRET_KEY: Optional[str] = Field(default=None)
    CBE_BIRR_API_URL: str = Field(default="https://cbe-birr.api")
    
    # ============================
    # Storage
    # ============================
    STORAGE_PROVIDER: str = Field(default="local")
    STORAGE_BASE_URL: str = Field(default="http://localhost:8000")
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME: Optional[str] = Field(default=None)
    CLOUDINARY_API_KEY: Optional[str] = Field(default=None)
    CLOUDINARY_API_SECRET: Optional[str] = Field(default=None)
    
    # AWS S3
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None)
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None)
    AWS_S3_BUCKET_NAME: Optional[str] = Field(default=None)
    AWS_REGION: str = Field(default="eu-north-1")
    
    # ============================
    # Email & SMS
    # ============================
    SMTP_HOST: str = Field(default="smtp.gmail.com")
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: Optional[str] = Field(default=None)
    SMTP_PASSWORD: Optional[str] = Field(default=None)
    EMAIL_FROM: str = Field(default="noreply@wolloyewa.com")
    
    SMS_PROVIDER: str = Field(default="ethio_telecom")
    SMS_API_KEY: Optional[str] = Field(default=None)
    SMS_SENDER_ID: str = Field(default="WOLLOYEWA")
    
    # ============================
    # Monitoring
    # ============================
    PROMETHEUS_ENABLED: bool = Field(default=True)
    PROMETHEUS_PORT: int = Field(default=9090)
    GRAFANA_ENABLED: bool = Field(default=True)
    SENTRY_DSN: Optional[str] = Field(default=None)
    OTEL_TRACING_ENABLED: bool = Field(default=False)
    OTEL_EXPORTER_ENDPOINT: Optional[str] = Field(default=None)
    
    # ============================
    # Rate Limiting
    # ============================
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    RATE_LIMIT_PER_HOUR: int = Field(default=1000)
    RATE_LIMIT_STRATEGY: str = Field(default="sliding_window")
    
    # ============================
    # Security
    # ============================
    JWT_SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRY_MINUTES: int = Field(default=1440)
    CORS_ALLOWED_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])
    ALLOWED_HOSTS: List[str] = Field(default_factory=lambda: ["*"])
    ENCRYPTION_KEY: Optional[str] = Field(default=None)
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
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CELERY_TASK_ALWAYS_EAGER: bool = Field(default=False)
    CELERY_WORKER_CONCURRENCY: int = Field(default=4)
    
    @field_validator("CELERY_BROKER_URL", "CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def build_celery_urls(cls, v: Optional[str], info) -> str:
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
    DEV_POPULATE_DUMMY_DATA: bool = Field(default=True)
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


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
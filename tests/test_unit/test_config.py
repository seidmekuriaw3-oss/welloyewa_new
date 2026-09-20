"""Focused tests for application settings and environment-derived values."""

from pydantic import ValidationError

from core.config import Settings, get_settings


def test_environment_and_runtime_properties():
    settings = Settings(ENVIRONMENT="production", DEBUG=False)

    assert settings.is_production is True
    assert settings.is_development is False
    assert settings.is_testing is False

    testing = Settings(ENVIRONMENT="testing", DEBUG=False)
    assert testing.is_testing is True


def test_invalid_environment_and_production_debug_are_rejected():
    try:
        Settings(ENVIRONMENT="invalid")
    except ValidationError as error:
        assert "ENVIRONMENT" in str(error)
    else:
        raise AssertionError("Invalid environment should fail validation")

    try:
        Settings(ENVIRONMENT="production", DEBUG=True)
    except ValidationError as error:
        assert "DEBUG must be False" in str(error)
    else:
        raise AssertionError("Production debug mode should fail validation")


def test_database_url_builder_supports_raw_and_testing_values():
    raw_postgresql = Settings(DATABASE_URL="postgresql://user:pass@db/shop")
    assert raw_postgresql.DATABASE_URL == "postgresql+asyncpg://user:pass@db/shop"

    raw_postgres = Settings(DATABASE_URL="postgres://user:pass@db/shop")
    assert raw_postgres.DATABASE_URL == "postgresql+asyncpg://user:pass@db/shop"

    testing = Settings(ENVIRONMENT="testing", DATABASE_URL=None)
    assert testing.DATABASE_URL.startswith("sqlite+aiosqlite:///")


def test_redis_and_celery_url_builders():
    no_password = Settings(
        REDIS_URL=None,
        REDIS_HOST="cache",
        REDIS_PORT=6380,
        REDIS_DB=3,
        CELERY_BROKER_URL=None,
        CELERY_RESULT_BACKEND=None,
    )
    assert no_password.REDIS_URL == "redis://cache:6380/3"
    assert no_password.CELERY_BROKER_URL == no_password.REDIS_URL
    assert no_password.CELERY_RESULT_BACKEND == no_password.REDIS_URL

    explicit = Settings(
        REDIS_URL="redis://explicit/1",
        CELERY_BROKER_URL="redis://broker/2",
        CELERY_RESULT_BACKEND="redis://backend/3",
    )
    assert explicit.REDIS_URL == "redis://explicit/1"
    assert explicit.CELERY_BROKER_URL == "redis://broker/2"
    assert explicit.CELERY_RESULT_BACKEND == "redis://backend/3"


def test_settings_parse_lists_and_admin_ids():
    settings = Settings(
        ADMIN_IDS="100, 200",
        CORS_ALLOWED_ORIGINS="https://a.example, https://b.example",
        ALLOWED_HOSTS="localhost, api.example.com",
    )

    assert settings.admin_ids_list == [100, 200]
    assert settings.CORS_ALLOWED_ORIGINS == ["https://a.example", "https://b.example"]
    assert settings.ALLOWED_HOSTS == ["localhost", "api.example.com"]


def test_web_app_url_normalization_and_setter():
    settings = Settings(WEB_APP_URL=" https://store.example/app/// ")
    assert settings.web_app_url == "https://store.example/app/"

    settings.web_app_url = "https://new.example/shop"
    assert settings.web_app_url == "https://new.example/shop/"

    settings.web_app_url = "http://localhost:8080/app/"
    assert settings.web_app_url == ""

    del settings.web_app_url
    assert settings.web_app_url == ""


def test_replit_domain_fallback_uses_first_domain():
    settings = Settings(WEB_APP_URL=None, REPLIT_DOMAINS="first.example, second.example")

    assert settings.web_app_url == "https://first.example/app/"


def test_get_settings_is_cached():
    first = get_settings()
    second = get_settings()

    assert first is second

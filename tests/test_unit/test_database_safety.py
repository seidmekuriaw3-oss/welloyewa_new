import importlib.util
from pathlib import Path

import pytest

_conftest_path = Path(__file__).resolve().parents[1] / "conftest.py"
_conftest_spec = importlib.util.spec_from_file_location(
    "wolloyewa_project_test_conftest", _conftest_path
)
conftest = importlib.util.module_from_spec(_conftest_spec)
_conftest_spec.loader.exec_module(conftest)


def test_database_fixture_is_disabled_without_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.delenv("ALLOW_TEST_DB_RESET", raising=False)

    assert conftest._validated_test_database_url() is None


def test_database_fixture_rejects_database_without_test_name(monkeypatch):
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/store")
    monkeypatch.setenv("ALLOW_TEST_DB_RESET", "1")

    with pytest.raises(pytest.UsageError):
        conftest._validated_test_database_url()


def test_database_fixture_rejects_runtime_database(monkeypatch):
    url = "postgresql+asyncpg://test:test@db.example:5432/store_test"
    monkeypatch.setenv("TEST_DATABASE_URL", url)
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("ALLOW_TEST_DB_RESET", "1")

    with pytest.raises(pytest.UsageError):
        conftest._validated_test_database_url()


def test_database_fixture_requires_explicit_reset_opt_in(monkeypatch):
    monkeypatch.setenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://test:test@localhost:5432/store_test",
    )
    monkeypatch.delenv("ALLOW_TEST_DB_RESET", raising=False)

    assert conftest._validated_test_database_url() is None

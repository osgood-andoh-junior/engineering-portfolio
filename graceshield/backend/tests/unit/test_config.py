import pytest
from pydantic import SecretStr

from app.core.config import Settings, database_identity, validate_database

# Deliberately inert, non-connectable URLs; no actual credentials or endpoints.
DEV = "postgresql://user:placeholder@development.invalid/graceshield_dev?sslmode=require"
TEST = "postgresql://user:placeholder@isolated.invalid/graceshield_test?sslmode=require"


def test_missing_database_is_clear():
    with pytest.raises(ValueError, match="DATABASE_URL is missing"):
        Settings(_env_file=None).connection_url()


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:///test.db",
        "postgresql://u:p@localhost/db?sslmode=require",
        "postgresql://u:p@cloud.invalid/db",
        "postgresql://cloud.invalid/db?sslmode=require",
    ],
)
def test_no_sqlite_or_unsafe_database(url):
    with pytest.raises(ValueError):
        validate_database(url)


def test_psycopg_and_tls():
    assert validate_database(DEV).startswith("postgresql+psycopg://")
    assert database_identity(DEV) == ("development.invalid", "graceshield_dev")


def test_test_database_guard():
    settings = Settings(
        _env_file=None,
        app_env="test",
        allow_test_database=True,
        test_database_url=SecretStr(TEST),
        database_url=SecretStr(DEV),
        test_database_host="isolated.invalid",
    )
    assert "graceshield_test" in settings.isolated_test_url()
    settings.database_url = SecretStr(TEST)
    with pytest.raises(ValueError, match="distinct"):
        settings.isolated_test_url()


@pytest.mark.parametrize(
    "changes",
    [
        {"app_env": "development"},
        {"allow_test_database": False},
        {"test_database_host": "other.invalid"},
        {"test_database_name": "graceshield_dev"},
        {"production_database_url": TEST},
    ],
)
def test_reject_unsafe_test_environment(changes):
    values = {
        "app_env": "test",
        "allow_test_database": True,
        "test_database_url": TEST,
        "test_database_host": "isolated.invalid",
        **changes,
    }
    with pytest.raises(ValueError):
        Settings(_env_file=None, **values).isolated_test_url()


def test_secrets_are_redacted():
    assert "placeholder" not in repr(Settings(_env_file=None, database_url=SecretStr(DEV)))


def test_production_requires_secure_cookies():
    with pytest.raises(ValueError):
        Settings(_env_file=None, app_env="production", cookie_secure=False)

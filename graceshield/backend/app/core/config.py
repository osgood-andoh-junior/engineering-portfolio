from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


def database_identity(value: str) -> tuple[str | None, str | None]:
    url = make_url(value)
    return ((url.host or "").replace("-pooler", ""), url.database)


def validate_database(value: str) -> str:
    url = make_url(value)
    if url.drivername not in {"postgresql", "postgresql+psycopg"}:
        raise ValueError("PostgreSQL with psycopg is required. SQLite is not supported.")
    if not url.host or not url.database or not url.username or not url.password:
        raise ValueError("A complete managed PostgreSQL connection is required.")
    if url.host in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Configure hosted PostgreSQL; no local database fallback is supported.")
    if url.query.get("sslmode") not in {"require", "verify-ca", "verify-full"}:
        raise ValueError(
            "Managed PostgreSQL connections require TLS (sslmode=require or stronger)."
        )
    return url.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", hide_input_in_errors=True, env_ignore_empty=True
    )
    app_env: Literal["development", "test", "production"] = "development"
    database_url: SecretStr = Field(default=SecretStr(""))
    migration_database_url: SecretStr = Field(default=SecretStr(""))
    test_database_url: SecretStr = Field(default=SecretStr(""))
    production_database_url: SecretStr = Field(default=SecretStr(""))
    test_database_name: str = "graceshield_test"
    test_database_host: str = ""
    allow_test_database: bool = False
    frontend_origin: str = "http://127.0.0.1:3000"
    cookie_secure: bool = False
    session_hours: int = Field(default=24, ge=1, le=168)
    shipping_fee_minor: int | None = Field(default=None, ge=0, le=10000000)
    shipping_regions: str = ""
    reservation_minutes: int = Field(default=15, ge=5, le=60)
    email_enabled: bool = False
    email_api_url: str = ""
    email_api_token: SecretStr = Field(default=SecretStr(""))
    email_from: str = ""
    allow_demo_seed: bool = False

    @model_validator(mode="after")
    def secure_production(self):
        if self.app_env == "production" and (
            not self.cookie_secure or not self.frontend_origin.startswith("https://")
        ):
            raise ValueError("Production requires HTTPS origin and Secure cookies.")
        return self

    def connection_url(self) -> str:
        if not self.database_url.get_secret_value():
            raise ValueError(
                "DATABASE_URL is missing. Follow docs/database/NEON_SETUP.md; configure backend/.env. No database was created."
            )
        try:
            return validate_database(self.database_url.get_secret_value())
        except Exception:
            raise ValueError(
                "Invalid DATABASE_URL. Use a complete managed PostgreSQL URL with TLS; see docs/database/NEON_SETUP.md."
            ) from None

    def isolated_test_url(self) -> str:
        raw = self.test_database_url.get_secret_value()
        if (
            self.app_env != "test"
            or not self.allow_test_database
            or not raw
            or not self.test_database_host
        ):
            raise ValueError(
                "Tests require APP_ENV=test, ALLOW_TEST_DATABASE=true and explicit TEST_DATABASE_URL/HOST/NAME."
            )
        value = validate_database(raw)
        host, name = database_identity(value)
        if (
            name != self.test_database_name
            or not name
            or not name.endswith("_test")
            or host != self.test_database_host.replace("-pooler", "")
        ):
            raise ValueError(
                "Test database must match the explicit host/name allowlist and end in _test."
            )
        for protected in (self.database_url, self.production_database_url):
            if protected.get_secret_value() and database_identity(protected.get_secret_value()) == (
                host,
                name,
            ):
                raise ValueError("Test database must be distinct from development and production.")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

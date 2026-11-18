from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICES = {
    "identity": ("Identity Service", 8101),
    "messaging": ("Messaging Service", 8102),
    "storage": ("Storage Service", 8103),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://cloudrescue:cloudrescue@127.0.0.1:5432/cloudrescue"
    admin_token: str = ""
    recovery_enabled: bool = False
    recovery_operator: Annotated[str, Field(min_length=1, max_length=64)] = "local-admin"
    poll_seconds: Annotated[float, Field(gt=0)] = 5
    timeout_seconds: Annotated[float, Field(gt=0)] = 3
    max_backoff_seconds: Annotated[float, Field(gt=0)] = 20
    max_concurrency: Annotated[int, Field(ge=1, le=3)] = 3
    degraded_ms: Annotated[int, Field(gt=0, lt=10000)] = 500
    down_after: Annotated[int, Field(ge=1)] = 3
    recover_after: Annotated[int, Field(ge=1)] = 3
    sim_network: Literal["loopback", "compose"] = "loopback"

    @model_validator(mode="after")
    def validate_thresholds(self) -> "Settings":
        if not self.database_url.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use PostgreSQL with psycopg")
        if self.degraded_ms >= self.timeout_seconds * 1000:
            raise ValueError("DEGRADED_MS must be shorter than TIMEOUT_SECONDS")
        if self.max_backoff_seconds < self.poll_seconds:
            raise ValueError("MAX_BACKOFF_SECONDS must be at least POLL_SECONDS")
        return self

    def target(self, slug: str) -> str:
        _, port = SERVICES[slug]
        host = "127.0.0.1" if self.sim_network == "loopback" else slug
        return f"http://{host}:{port}/health"


@lru_cache
def settings() -> Settings:
    return Settings()

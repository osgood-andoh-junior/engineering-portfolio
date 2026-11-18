from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert

from backend.config import SERVICES, settings
from backend.db import sessions
from backend.models import ApplicationSetting, FaultConfiguration, Service


def seed() -> None:
    now = datetime.now(UTC)
    config = monitoring_settings()
    with sessions().begin() as db:
        for slug, (name, _) in SERVICES.items():
            db.execute(insert(Service).values(slug=slug, name=name).on_conflict_do_nothing())
            db.execute(
                insert(FaultConfiguration)
                .values(service_slug=slug, mode="healthy", latency_ms=0, updated_at=now)
                .on_conflict_do_nothing()
            )
        db.execute(
            insert(ApplicationSetting)
            .values(key="monitoring", value=config)
            .on_conflict_do_update(index_elements=[ApplicationSetting.key], set_={"value": config})
        )


def monitoring_settings() -> dict[str, int | float]:
    return settings().model_dump(
        include={
            "poll_seconds",
            "timeout_seconds",
            "max_backoff_seconds",
            "max_concurrency",
            "degraded_ms",
            "down_after",
            "recover_after",
        }
    )


if __name__ == "__main__":
    seed()

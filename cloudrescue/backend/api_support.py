from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.db import sessions
from backend.models import FaultConfiguration, FaultEvent


def database() -> Iterator[Session]:
    with sessions()() as db:
        yield db


DB = Annotated[Session, Depends(database)]


def update_fault(
    db: Session,
    fault: FaultConfiguration,
    mode: str,
    latency: int,
    at: datetime | None = None,
    expires_at: datetime | None = None,
) -> None:
    fault.mode, fault.latency_ms, fault.updated_at = mode, latency, at or datetime.now(UTC)
    fault.expires_at = expires_at
    db.add(
        FaultEvent(
            service_slug=fault.service_slug,
            mode=mode,
            latency_ms=latency,
            occurred_at=fault.updated_at,
            expires_at=expires_at,
        )
    )

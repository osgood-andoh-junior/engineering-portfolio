from datetime import timedelta

from fastapi import Request
from sqlalchemy import case
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.core.security import digest, utcnow
from app.db.session import get_engine
from app.models.entities import RateLimit


def rate_limit(request: Request, scope: str, maximum: int = 10, identity: str = ""):
    # Separate committed transaction: failed authentication must still consume attempts.
    key = digest(f"{scope}:{request.client.host if request.client else 'unknown'}:{identity}")
    now = utcnow()
    expired = RateLimit.expires_at <= now
    stmt = (
        insert(RateLimit)
        .values(key=key, count=1, expires_at=now + timedelta(minutes=10))
        .on_conflict_do_update(
            index_elements=[RateLimit.key],
            set_={
                "count": case((expired, 1), else_=RateLimit.count + 1),
                "expires_at": case(
                    (expired, now + timedelta(minutes=10)), else_=RateLimit.expires_at
                ),
            },
        )
        .returning(RateLimit.count)
    )
    with Session(get_engine()) as limiter:
        count = limiter.scalar(stmt)
        limiter.commit()
    if count and count > maximum:
        raise DomainError("rate_limited", "Too many attempts. Please try again later.", 429)

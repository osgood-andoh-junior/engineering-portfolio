import secrets
from datetime import timedelta

from fastapi import Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.core.security import digest, token, utcnow
from app.db.session import get_db
from app.models.entities import CustomerProfile, SessionRecord, User

COOKIE = "graceshield_session"


def set_cookie(response: Response, raw: str):
    settings = get_settings()
    response.set_cookie(
        COOKIE,
        raw,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_hours * 3600,
        path="/",
    )


def session_record(
    request: Request, db: Session = Depends(get_db, scope="function")
) -> SessionRecord:
    raw = request.cookies.get(COOKIE, "")
    record = (
        db.scalar(
            select(SessionRecord).where(
                SessionRecord.token_hash == digest(raw), SessionRecord.expires_at > utcnow()
            )
        )
        if raw
        else None
    )
    if record is None:
        raise DomainError("session_required", "Start a browser session and try again.", 401)
    return record


def csrf_if_mutation(request: Request, record: SessionRecord = Depends(session_record)):
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    supplied = request.headers.get("x-csrf-token", "")
    if request.headers.get(
        "origin"
    ) != get_settings().frontend_origin or not secrets.compare_digest(supplied, record.csrf):
        raise DomainError(
            "csrf_failed", "Your session changed. Refresh the page and try again.", 403
        )


def current_user(
    record: SessionRecord = Depends(session_record), db: Session = Depends(get_db, scope="function")
) -> User:
    user = db.get(User, record.user_id) if record.user_id else None
    if user is None or not user.active:
        raise DomainError("authentication_required", "Please sign in to continue.", 401)
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if not user.verified or not any(item.role.name == "admin" for item in user.roles):
        raise DomainError("forbidden", "You do not have permission to access this resource.", 403)
    return user


def public_user(db: Session, user: User):
    profile = db.scalar(select(CustomerProfile).where(CustomerProfile.user_id == user.id))
    return {
        "id": str(user.id),
        "email": user.email,
        "name": profile.name if profile else "",
        "verified": user.verified,
        "roles": [item.role.name for item in user.roles],
    }


def new_session(db: Session, response: Response):
    raw = token()
    record = SessionRecord(
        token_hash=digest(raw),
        csrf=token(),
        expires_at=utcnow() + timedelta(hours=get_settings().session_hours),
    )
    db.add(record)
    db.flush()
    set_cookie(response, raw)
    return record

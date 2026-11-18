from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.core.security import DUMMY_HASH, digest, password_hasher, token, utcnow, verify_password
from app.db.session import get_db
from app.dependencies.auth import (
    COOKIE,
    csrf_if_mutation,
    current_user,
    new_session,
    public_user,
    session_record,
    set_cookie,
)
from app.integrations.email import send_account_email
from app.models.entities import AccountToken, CustomerProfile, SessionRecord, User
from app.schemas.contracts import (
    Credentials,
    EmailRequest,
    PublicUser,
    Registration,
    ResetPassword,
    TokenRequest,
)
from app.services.rate_limit import rate_limit

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/session")
def browser_session(
    request: Request, response: Response, db: Session = Depends(get_db, scope="function")
):
    raw = request.cookies.get(COOKIE)
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
        rate_limit(request, "new_session", 120)
        record = new_session(db, response)
    response.headers["Cache-Control"] = "no-store"
    return {"csrf": record.csrf}


@router.post("/register", status_code=201, dependencies=[Depends(csrf_if_mutation)])
def register(data: Registration, request: Request, db: Session = Depends(get_db, scope="function")):
    rate_limit(request, "register", 5)
    email = str(data.email).lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise DomainError(
            "registration_unavailable",
            "Unable to create this account. Try signing in or resetting your password.",
            409,
        )
    user = User(email=email, password_hash=password_hasher.hash(data.password))
    db.add(user)
    db.flush()
    db.add(CustomerProfile(user_id=user.id, name=data.name))
    return {
        "message": "Account created. Sign in, then request verification. Email availability is shown when requested."
    }


@router.post("/login", response_model=PublicUser, dependencies=[Depends(csrf_if_mutation)])
def login(
    data: Credentials,
    request: Request,
    response: Response,
    record: SessionRecord = Depends(session_record),
    db: Session = Depends(get_db, scope="function"),
):
    rate_limit(request, "login", 20)
    rate_limit(request, "login_identity", 8, str(data.email).lower())
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    valid = verify_password(data.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid or not user.active:
        raise DomainError("invalid_credentials", "Email or password is incorrect.", 401)
    from app.services.cart import merge_guest_cart

    merge_guest_cart(db, record, user)
    raw = token()
    record.user_id = user.id
    record.token_hash = digest(raw)
    record.csrf = token()
    record.expires_at = utcnow() + timedelta(hours=get_settings().session_hours)
    set_cookie(response, raw)
    return public_user(db, user)


@router.post("/logout", dependencies=[Depends(csrf_if_mutation)])
def logout(
    response: Response,
    record: SessionRecord = Depends(session_record),
    db: Session = Depends(get_db, scope="function"),
):
    db.delete(record)
    response.delete_cookie(
        COOKIE, path="/", secure=get_settings().cookie_secure, httponly=True, samesite="lax"
    )
    return {"message": "Signed out."}


@router.get("/me", response_model=PublicUser)
def me(
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    response.headers["Cache-Control"] = "no-store"
    return public_user(db, user)


@router.post("/verification/request", dependencies=[Depends(csrf_if_mutation)])
def request_verification(
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    rate_limit(request, "verification", 5)
    if user.verified:
        return {"message": "Your email is already verified."}
    issue_account_token(db, user, "verify")
    return {"message": "Verification request accepted by the configured email service."}


def issue_account_token(db: Session, user: User, purpose: str):
    raw = token()
    send_account_email(get_settings(), user.email, purpose, raw)
    previous = db.scalars(
        select(AccountToken).where(
            AccountToken.user_id == user.id,
            AccountToken.purpose == purpose,
            AccountToken.used.is_(False),
        )
    )
    for item in previous:
        item.used = True
    db.add(
        AccountToken(
            user_id=user.id,
            token_hash=digest(raw),
            purpose=purpose,
            expires_at=utcnow() + timedelta(minutes=30),
        )
    )


def consume_token(db: Session, raw: str, purpose: str):
    record = db.scalar(
        select(AccountToken)
        .where(AccountToken.token_hash == digest(raw), AccountToken.purpose == purpose)
        .with_for_update()
    )
    if not record or record.used or record.expires_at <= utcnow():
        raise DomainError("invalid_token", "This link is invalid or expired. Request a new link.")
    record.used = True
    user = db.get(User, record.user_id)
    if not user or not user.active:
        raise DomainError("invalid_token", "This link is invalid or expired.")
    return user


@router.post("/verification/confirm", dependencies=[Depends(csrf_if_mutation)])
def confirm_verification(
    data: TokenRequest, request: Request, db: Session = Depends(get_db, scope="function")
):
    rate_limit(request, "verify_confirm", 15)
    user = consume_token(db, data.token, "verify")
    user.verified = True
    return {"message": "Email verified."}


@router.post("/password/request", dependencies=[Depends(csrf_if_mutation)])
def request_password(
    data: EmailRequest, request: Request, db: Session = Depends(get_db, scope="function")
):
    rate_limit(request, "reset_request", 5)
    settings = get_settings()
    if not settings.email_enabled:
        raise DomainError(
            "email_unavailable", "Email delivery is not configured. No reset email was sent.", 503
        )
    user = db.scalar(
        select(User).where(User.email == str(data.email).lower(), User.active.is_(True))
    )
    if user:
        issue_account_token(db, user, "reset")
    return {"message": "If the account is eligible, a reset request was accepted."}


@router.post("/password/confirm", dependencies=[Depends(csrf_if_mutation)])
def confirm_password(
    data: ResetPassword, request: Request, db: Session = Depends(get_db, scope="function")
):
    rate_limit(request, "reset_confirm", 10)
    user = consume_token(db, data.token, "reset")
    user.password_hash = password_hasher.hash(data.password)
    db.execute(delete(SessionRecord).where(SessionRecord.user_id == user.id))
    return {
        "message": "Password reset. All previous sessions have been invalidated. Sign in again."
    }

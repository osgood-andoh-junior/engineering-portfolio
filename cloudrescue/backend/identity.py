import argparse
import getpass
import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hmac import compare_digest
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.audit_chain import append
from backend.config import settings
from backend.db import sessions
from backend.security_models import Operator, OperatorSession

ROLES = {"viewer": 0, "operator": 1, "administrator": 2}
auth = HTTPBearer(auto_error=False)
ITERATIONS = 600_000


@dataclass(frozen=True)
class Principal:
    username: str
    role: str


def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    value = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return salt.hex() + ":" + value.hex()


def check_password(password: str, encoded: str | None) -> bool:
    salt = bytes.fromhex(encoded.split(":")[0]) if encoded else bytes(16)
    actual = password_hash(password, salt)
    return bool(encoded and compare_digest(encoded, actual))


def digest_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(auth)],
) -> Principal:
    if credentials and len(credentials.credentials) <= 512:
        value = credentials.credentials
        config = settings()
        with sessions()() as db:
            row = db.get(OperatorSession, digest_token(value))
            account = (
                db.get(Operator, row.username)
                if row and row.expires_at > datetime.now(UTC)
                else None
            )
            if account and account.active:
                return Principal(account.username, account.role)
            # Transitional token access ends as soon as any named account is provisioned.
            if (
                config.admin_token
                and compare_digest(value.encode(), config.admin_token.encode())
                and db.scalar(select(Operator.username).limit(1)) is None
            ):
                return Principal(config.recovery_operator, "administrator")
    raise HTTPException(
        401, "Valid operator credentials required", headers={"WWW-Authenticate": "Bearer"}
    )


def permit(role: str):
    def check(actor: Annotated[Principal, Depends(principal)]) -> Principal:
        if ROLES[actor.role] < ROLES[role]:
            with sessions().begin() as db:
                append(
                    db, actor.username, "authorization_denied", required_role=role, role=actor.role
                )
            raise HTTPException(403, "This role cannot perform that operation")
        return actor

    return check


require_admin = permit("administrator")
require_operator = permit("operator")
Viewer = Annotated[Principal, Depends(principal)]
Admin = Annotated[Principal, Depends(require_admin)]
OperatorActor = Annotated[Principal, Depends(require_operator)]


def issue(db: Session, account: Operator) -> str:
    token = secrets.token_urlsafe(32)
    db.add(
        OperatorSession(
            digest=digest_token(token),
            username=account.username,
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
    )
    return token


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    args = parser.parse_args()
    import re

    if not re.fullmatch(r"[a-z][a-z0-9_-]{2,47}", args.username):
        parser.error("Use 3–48 lowercase letters, digits, underscores, or hyphens")
    password = getpass.getpass("New administrator password: ")
    if not 12 <= len(password) <= 128 or password != getpass.getpass("Repeat password: "):
        parser.error("Passwords must match and be 12–128 characters")
    with sessions().begin() as db:
        db.execute(text("SELECT pg_advisory_xact_lock(726031026)"))
        if db.scalar(select(Operator.username).limit(1)) is not None:
            parser.error("Accounts already exist. Use Security Administration.")
        db.add(
            Operator(
                username=args.username,
                password=password_hash(password),
                role="administrator",
                active=True,
            )
        )
        append(db, args.username, "bootstrap_administrator", target=args.username)
    print("Administrator created. Legacy bearer access is disabled.")

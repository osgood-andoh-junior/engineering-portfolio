from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.security import digest, password_hasher, token, utcnow
from app.dependencies.auth import COOKIE
from app.models.entities import AccountToken, SessionRecord, User

from .conftest import csrf

pytestmark = pytest.mark.integration


def test_one_use_tokens_password_reset_revocation_and_session_expiration(client, db):
    user = User(
        email=uuid4().hex + "@example.com",
        password_hash=password_hasher.hash("initial-isolated-password"),
        verified=False,
    )
    db.add(user)
    db.flush()
    db.commit()
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "initial-isolated-password"},
            headers=csrf(client),
        ).status_code
        == 200
    )
    raw = token()
    db.add(
        AccountToken(
            user_id=user.id,
            token_hash=digest(raw),
            purpose="verify",
            expires_at=utcnow() + timedelta(minutes=5),
        )
    )
    db.commit()
    assert (
        client.post(
            "/api/v1/auth/verification/confirm", json={"token": raw}, headers=csrf(client)
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/auth/verification/confirm", json={"token": raw}, headers=csrf(client)
        ).status_code
        == 400
    )
    reset = token()
    db.add(
        AccountToken(
            user_id=user.id,
            token_hash=digest(reset),
            purpose="reset",
            expires_at=utcnow() + timedelta(minutes=5),
        )
    )
    db.commit()
    assert (
        client.post(
            "/api/v1/auth/password/confirm",
            json={"token": reset, "password": "new-isolated-password"},
            headers=csrf(client),
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "new-isolated-password"},
            headers=csrf(client),
        ).status_code
        == 200
    )
    raw_session = client.cookies.get(COOKIE)
    record = db.scalar(select(SessionRecord).where(SessionRecord.token_hash == digest(raw_session)))
    record.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert client.get("/api/v1/auth/me").status_code == 401

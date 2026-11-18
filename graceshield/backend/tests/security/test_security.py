import pytest
from starlette.requests import Request

from app.core.config import Settings
from app.core.exceptions import DomainError
from app.core.security import digest, password_hasher, token, verify_password
from app.dependencies.auth import admin_user, csrf_if_mutation
from app.integrations.email import send_account_email
from app.integrations.payments import configured_provider
from app.models.entities import Role, SessionRecord, User, UserRole


def test_argon2id_passwords_and_random_session_tokens():
    hashed = password_hasher.hash("a-long-example-password")
    assert hashed.startswith("$argon2id$")
    assert verify_password("a-long-example-password", hashed)
    assert not verify_password("incorrect-password", hashed)
    assert token() != token()
    assert len(digest(token())) == 64


def test_csrf_requires_token_and_allowed_origin():
    record = SessionRecord(csrf="expected-secret-csrf")

    def request(origin, csrf):
        return Request(
            {
                "type": "http",
                "method": "POST",
                "headers": [(b"origin", origin.encode()), (b"x-csrf-token", csrf.encode())],
            }
        )

    csrf_if_mutation(request("http://127.0.0.1:3000", "expected-secret-csrf"), record)
    for origin, csrf in [
        ("https://attacker.invalid", "expected-secret-csrf"),
        ("http://127.0.0.1:3000", "wrong"),
    ]:
        with pytest.raises(DomainError):
            csrf_if_mutation(request(origin, csrf), record)


def test_server_side_admin_authorization():
    user = User(verified=True, roles=[])
    with pytest.raises(DomainError):
        admin_user(user)
    user.roles = [UserRole(role=Role(name="admin"))]
    assert admin_user(user) is user
    user.verified = False
    with pytest.raises(DomainError):
        admin_user(user)


def test_unconfigured_email_and_payments_never_report_success():
    with pytest.raises(DomainError, match="No email was sent"):
        send_account_email(Settings(_env_file=None), "sample@example.com", "verify", token())
    with pytest.raises(DomainError, match="No payment has been processed"):
        configured_provider()

import hashlib
import secrets
from datetime import UTC, datetime

from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()
DUMMY_HASH = password_hasher.hash(secrets.token_urlsafe(32))


def utcnow() -> datetime:
    return datetime.now(UTC)


def token() -> str:
    return secrets.token_urlsafe(32)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def verify_password(value: str, hashed: str) -> bool:
    try:
        return password_hasher.verify(value, hashed)
    except Exception:
        return False

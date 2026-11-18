"""Explicit cloud-test-only fixture setup; never imported by the live application."""

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cli import seed
from app.core.config import get_settings
from app.core.security import password_hasher
from app.db.session import get_engine
from app.models.entities import Cart, CustomerProfile, Role, User, UserRole


def main():
    settings = get_settings()
    settings.isolated_test_url()
    if not settings.allow_demo_seed:
        raise SystemExit("ALLOW_DEMO_SEED=true is required for explicit test fixtures.")
    with Session(get_engine()) as db, db.begin():
        seed(db)
        for label in ["CUSTOMER", "ADMIN"]:
            email = os.environ.get(f"E2E_{label}_EMAIL", "").lower()
            password = os.environ.get(f"E2E_{label}_PASSWORD", "")
            if not email.endswith("@example.com") or len(password) < 12:
                raise SystemExit(
                    "Set example.com synthetic E2E account emails and 12+ character passwords privately."
                )
            user = db.scalar(select(User).where(User.email == email))
            if not user:
                user = User(
                    email=email, password_hash=password_hasher.hash(password), verified=True
                )
                db.add(user)
                db.flush()
                db.add(CustomerProfile(user_id=user.id, name=f"Automated {label.title()}"))
            else:
                user.password_hash = password_hasher.hash(password)
                user.verified = True
            cart = db.scalar(select(Cart).where(Cart.user_id == user.id))
            if cart:
                cart.items.clear()
            if label == "ADMIN":
                role = db.scalar(select(Role).where(Role.name == "admin"))
                if not role:
                    role = Role(name="admin")
                    db.add(role)
                    db.flush()
                if not db.get(UserRole, (user.id, role.id)):
                    db.add(UserRole(user_id=user.id, role_id=role.id))
    print(
        "Synthetic E2E fixtures prepared in the guarded test database. No credentials were printed."
    )


if __name__ == "__main__":
    main()

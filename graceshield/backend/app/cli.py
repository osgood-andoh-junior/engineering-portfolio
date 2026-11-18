import argparse
import getpass
import json
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import password_hasher
from app.db.session import get_engine
from app.models.entities import (
    AuditLog,
    Category,
    CustomerProfile,
    Inventory,
    InventoryMovement,
    Product,
    ProductImage,
    ProductVariant,
    Role,
    User,
    UserRole,
)
from app.schemas.contracts import Credentials
from app.services.orders import expire_orders


def seed(db: Session):
    settings = get_settings()
    if settings.app_env not in {"development", "test"} or not settings.allow_demo_seed:
        raise SystemExit(
            "Demonstration seed requires a non-production environment and ALLOW_DEMO_SEED=true."
        )
    source = json.loads(
        (Path(__file__).parent.parent / "seeds" / "catalogue.json").read_text(encoding="utf-8")
    )
    category_ids = {}
    for item in source["categories"]:
        category = db.scalar(select(Category).where(Category.slug == item["slug"]))
        if not category:
            category = Category(
                name=item["name"],
                slug=item["slug"],
                description=item["description"],
                icon=item["icon"],
                color=item["color"],
            )
            db.add(category)
            db.flush()
        category_ids[item["id"]] = category.id
    for item in source["products"]:
        if db.scalar(select(Product.id).where(Product.slug == item["slug"])):
            continue  # Idempotent: never reset edited prices or existing stock.
        product = Product(
            name=item["name"],
            slug=item["slug"],
            description=item["description"],
            category_id=category_ids[item["categoryId"]],
            price_minor=item["price"]["amount"],
            status="published",
            demonstration=True,
        )
        product.images = [
            ProductImage(path=img["src"], alt=img["alt"], position=i)
            for i, img in enumerate(item["images"])
        ]
        stock = 30 if item["availability"] == "available" else 0
        variant = ProductVariant(
            sku=f"DEMO-{item['id'].upper()}", inventory=Inventory(quantity=stock, reserved=0)
        )
        product.variants = [variant]
        db.add(product)
        db.flush()
        db.add(
            InventoryMovement(
                variant_id=variant.id, delta=stock, reason="Explicit demonstration seed"
            )
        )


def bootstrap(db: Session):
    db.execute(select(func.pg_advisory_xact_lock(10471003)))
    if db.scalar(select(UserRole).join(Role).where(Role.name == "admin")):
        raise SystemExit(
            "An administrator already exists. Use a reviewed role-management procedure."
        )
    email = input("Administrator email: ").strip().lower()
    password = getpass.getpass("New password (12–128 characters): ")
    Credentials(email=email, password=password)
    if password != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords do not match.")
    if (
        input("Type BOOTSTRAP ADMIN to confirm local privileged account creation: ")
        != "BOOTSTRAP ADMIN"
    ):
        raise SystemExit("Cancelled.")
    if db.scalar(select(User.id).where(User.email == email)):
        raise SystemExit("Email already registered. Existing accounts are not silently promoted.")
    role = db.scalar(select(Role).where(Role.name == "admin"))
    if not role:
        role = Role(name="admin")
        db.add(role)
        db.flush()
    user = User(email=email, password_hash=password_hasher.hash(password), verified=True)
    db.add(user)
    db.flush()
    db.add_all(
        [
            UserRole(user_id=user.id, role_id=role.id),
            CustomerProfile(user_id=user.id, name="Administrator"),
            AuditLog(actor_id=user.id, action="admin.bootstrapped", resource_id=str(user.id)),
        ]
    )


def main():
    parser = argparse.ArgumentParser(description="GraceShield non-production operations")
    parser.add_argument(
        "command", choices=["check-db", "seed", "bootstrap-admin", "expire-reservations"]
    )
    args = parser.parse_args()
    if get_settings().app_env == "production":
        raise SystemExit("Production operations require separate explicit approval.")
    with Session(get_engine()) as db, db.begin():
        if args.command == "check-db":
            db.execute(text("SELECT 1"))
            print("Managed PostgreSQL connectivity verified. Credentials were not printed.")
        elif args.command == "seed":
            seed(db)
            print("Demonstration seed applied. No existing stock was reset.")
        elif args.command == "bootstrap-admin":
            bootstrap(db)
            print("Administrator created. No credentials were logged.")
        else:
            print(f"Expired {expire_orders(db)} reservations.")


if __name__ == "__main__":
    main()

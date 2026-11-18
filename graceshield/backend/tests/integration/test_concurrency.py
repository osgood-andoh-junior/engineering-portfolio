from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.core.security import digest, password_hasher, token, utcnow
from app.db.session import get_engine
from app.models.entities import (
    AuditLog,
    Cart,
    CartItem,
    Category,
    Inventory,
    InventoryMovement,
    Order,
    OrderItem,
    Product,
    ProductImage,
    ProductVariant,
    SessionRecord,
    User,
)
from app.schemas.contracts import CheckoutInput
from app.services.orders import prepare_order

pytestmark = pytest.mark.integration


def test_two_concurrent_checkouts_cannot_oversell(db, monkeypatch):
    # Guarded fixture validates the isolated test database before any committed test data.
    settings = get_settings()
    settings.isolated_test_url()
    monkeypatch.setattr(settings, "shipping_fee_minor", 1000)
    monkeypatch.setattr(settings, "shipping_regions", "Greater Accra")
    engine = get_engine()
    marker = uuid4().hex
    user_ids = []
    with Session(engine) as setup, setup.begin():
        category = Category(name="Concurrency fixture", slug=f"concurrency-{marker}")
        setup.add(category)
        setup.flush()
        product = Product(
            category_id=category.id,
            name="Concurrency fixture",
            slug=f"stock-{marker}",
            description="Isolated automated test fixture",
            price_minor=100,
            status="published",
        )
        variant = ProductVariant(sku=f"CONC-{marker}", inventory=Inventory(quantity=3, reserved=0))
        product.variants = [variant]
        setup.add(product)
        setup.flush()
        variant_id, product_id, category_id = variant.id, product.id, category.id
        for index in range(2):
            user = User(
                email=f"{marker}-{index}@example.com",
                password_hash=password_hasher.hash(token()),
                verified=True,
            )
            setup.add(user)
            setup.flush()
            user_ids.append(user.id)
            session = SessionRecord(
                user_id=user.id,
                token_hash=digest(token()),
                csrf=token(),
                expires_at=utcnow() + timedelta(hours=1),
            )
            setup.add(session)
            setup.add(Cart(user_id=user.id, items=[CartItem(variant_id=variant_id, quantity=2)]))
    barrier = Barrier(2)

    def attempt(user_id):
        try:
            with Session(engine) as session, session.begin():
                user = session.get(User, user_id)
                browser = session.scalar(
                    select(SessionRecord).where(SessionRecord.user_id == user_id)
                )
                data = CheckoutInput(
                    firstName="Sample",
                    lastName="Customer",
                    email=user.email,
                    phone="0241234567",
                    address="Isolated test address",
                    region="Greater Accra",
                    city="Accra",
                )
                barrier.wait(timeout=10)
                prepare_order(session, user, browser, data, uuid4().hex)
            return "reserved"
        except DomainError as error:
            return error.code

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, user_ids))
        assert sorted(results) == ["insufficient_stock", "reserved"]
        with Session(engine) as verify:
            stock = verify.get(Inventory, variant_id)
            assert stock.quantity == 3 and stock.reserved == 2
    finally:
        # Delete only this test's UUID-tagged records; never reset/truncate a database.
        with Session(engine) as cleanup, cleanup.begin():
            order_ids = select(Order.id).where(Order.user_id.in_(user_ids))
            cleanup.execute(delete(OrderItem).where(OrderItem.order_id.in_(order_ids)))
            cleanup.execute(delete(Order).where(Order.user_id.in_(user_ids)))
            cleanup.execute(
                delete(InventoryMovement).where(InventoryMovement.variant_id == variant_id)
            )
            cleanup.execute(delete(AuditLog).where(AuditLog.actor_id.in_(user_ids)))
            cleanup.execute(
                delete(CartItem).where(
                    CartItem.cart_id.in_(select(Cart.id).where(Cart.user_id.in_(user_ids)))
                )
            )
            cleanup.execute(delete(Cart).where(Cart.user_id.in_(user_ids)))
            cleanup.execute(delete(SessionRecord).where(SessionRecord.user_id.in_(user_ids)))
            cleanup.execute(delete(User).where(User.id.in_(user_ids)))
            cleanup.execute(delete(Inventory).where(Inventory.variant_id == variant_id))
            cleanup.execute(delete(ProductImage).where(ProductImage.product_id == product_id))
            cleanup.execute(delete(ProductVariant).where(ProductVariant.id == variant_id))
            cleanup.execute(delete(Product).where(Product.id == product_id))
            cleanup.execute(delete(Category).where(Category.id == category_id))

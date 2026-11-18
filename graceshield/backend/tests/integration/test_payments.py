import hashlib
import hmac
import json
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.exceptions import DomainError
from app.core.security import utcnow
from app.integrations.payments import VerifiedPayment
from app.models.entities import (
    Cart,
    CartItem,
    Category,
    Inventory,
    Payment,
    Product,
    ProductVariant,
    SessionRecord,
    User,
)
from app.schemas.contracts import CheckoutInput
from app.services.orders import prepare_order
from app.services.payments import apply_verified_event

pytestmark = pytest.mark.integration


class TestOnlyPaymentAdapter:
    """Never imported by application code; no customer-facing fake success."""

    __test__ = False
    secret = b"automated-test-signing-key"

    def __init__(self, reference, amount):
        self.reference, self.amount = reference, amount

    def initialize(self, order_reference, amount_minor, idempotency_key):
        return {"reference": self.reference}

    def verify(self, reference):
        if reference != self.reference:
            raise DomainError("unknown_payment", "Unknown payment reference.", 404)
        return VerifiedPayment("test", uuid4().hex, reference, self.amount, "GHS", "paid")

    def authenticate_webhook(self, body, signature, timestamp):
        expected = hmac.new(
            self.secret, timestamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise DomainError("invalid_signature", "Invalid signature.", 401)
        payload = json.loads(body)
        return VerifiedPayment(
            "test", payload["event_id"], self.reference, self.amount, "GHS", "paid"
        )

    def refund(self, reference, amount_minor, idempotency_key):
        return {"status": "refunded"}

    def reconcile(self):
        return [self.verify(self.reference)]


def test_verified_event_is_deduplicated_and_cannot_downgrade_paid_state(db, monkeypatch):
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "shipping_fee_minor", 0)
    monkeypatch.setattr(settings, "shipping_regions", "Greater Accra")
    marker = uuid4().hex
    category = Category(name="Payment fixture", slug=marker)
    db.add(category)
    db.flush()
    product = Product(
        category_id=category.id,
        name="Payment test",
        slug="product-" + marker,
        description="Isolated test fixture",
        price_minor=4500,
        status="published",
    )
    variant = ProductVariant(sku="PAY-" + marker, inventory=Inventory(quantity=10, reserved=0))
    product.variants = [variant]
    user = User(email=marker + "@example.com", password_hash="not-used-for-login", verified=True)
    db.add_all([product, user])
    db.flush()
    record = SessionRecord(user_id=user.id)
    db.add(Cart(user_id=user.id, items=[CartItem(variant_id=variant.id, quantity=2)]))
    db.flush()
    data = CheckoutInput(
        firstName="Sample",
        lastName="Customer",
        email=user.email,
        phone="0241234567",
        address="Isolated test address",
        region="Greater Accra",
        city="Accra",
    )
    order = prepare_order(db, user, record, data, marker)
    payment = Payment(
        order_id=order.id, provider="test", provider_reference=marker, amount_minor=9000
    )
    db.add(payment)
    db.flush()
    adapter = TestOnlyPaymentAdapter(marker, 9000)
    event = adapter.verify(marker)
    assert apply_verified_event(db, event) == "applied"
    assert order.status == "paid"
    assert apply_verified_event(db, event) == "duplicate"
    stale = VerifiedPayment("test", uuid4().hex, marker, 9000, "GHS", "pending")
    assert apply_verified_event(db, stale) == "ignored_stale"
    assert payment.status == "paid"
    stock = db.scalar(select(Inventory).where(Inventory.variant_id == variant.id))
    assert stock.quantity == 8 and stock.reserved == 0
    with pytest.raises(DomainError, match="reconciliation"):
        apply_verified_event(db, VerifiedPayment("test", uuid4().hex, marker, 1, "GHS", "paid"))
    with pytest.raises(DomainError, match="Invalid signature"):
        adapter.authenticate_webhook(b"{}", "wrong", utcnow().isoformat())

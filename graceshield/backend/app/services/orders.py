import json
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.core.security import digest, utcnow
from app.models.entities import (
    AuditLog,
    Inventory,
    InventoryMovement,
    Order,
    OrderItem,
    Product,
    SessionRecord,
    Shipment,
    User,
)
from app.schemas.contracts import CheckoutInput
from app.services.cart import owned_cart, purchasable_variant
from app.services.rules import available, totals, validate_transition


def locked_inventory(db: Session, variant_id):
    stock = db.scalar(
        select(Inventory)
        .where(Inventory.variant_id == variant_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not stock:
        raise DomainError("stock_unavailable", "Inventory is unavailable for an item.", 409)
    return stock


def release_order(db: Session, order: Order, actor=None):
    for item in sorted(order.items, key=lambda i: str(i.variant_id)):
        stock = locked_inventory(db, item.variant_id)
        if stock.reserved < item.quantity:
            raise DomainError("inventory_conflict", "Inventory reconciliation is required.", 409)
        stock.reserved -= item.quantity
        db.add(
            InventoryMovement(
                variant_id=item.variant_id,
                delta=0,
                reserved_delta=-item.quantity,
                reason=f"Release {order.reference}",
                actor_id=actor,
            )
        )
    order.status = "cancelled"


def expire_orders(db: Session) -> int:
    if not db.scalar(select(func.pg_try_advisory_xact_lock(10471001))):
        return 0
    orders = db.scalars(
        select(Order)
        .where(Order.status == "pending_payment", Order.expires_at <= utcnow())
        .order_by(Order.id)
        .limit(100)
        .with_for_update(skip_locked=True)
    ).all()
    for order in orders:
        release_order(db, order)
        db.add(AuditLog(action="order.expired", resource_id=str(order.id)))
    db.flush()
    return len(orders)


def prepare_order(db: Session, user: User, record: SessionRecord, data: CheckoutInput, key: str):
    if not user.verified:
        raise DomainError("email_unverified", "Verify your email before preparing an order.", 403)
    cart = owned_cart(db, record, True)
    fingerprint = digest(json.dumps(data.model_dump(mode="json"), sort_keys=True))
    existing = db.scalar(
        select(Order).where(Order.user_id == user.id, Order.idempotency_key == key)
    )
    if existing:
        if existing.request_hash != fingerprint:
            raise DomainError(
                "idempotency_conflict",
                "This submission key was used for different checkout details.",
                409,
            )
        return existing
    settings = get_settings()
    if settings.shipping_fee_minor is None or data.region not in [
        r.strip() for r in settings.shipping_regions.split(",") if r.strip()
    ]:
        raise DomainError(
            "shipping_unavailable",
            "Delivery pricing or coverage is not configured for this address. No order was created.",
            503,
        )
    if not cart.items:
        raise DomainError("empty_cart", "Your bag is empty.", 409)
    expire_orders(db)
    lines = []
    # Lock products and inventory consistently. Backend prices only; request schema forbids totals.
    variants = [purchasable_variant(db, i.variant_id)[0] for i in cart.items]
    for product_id in sorted({v.product_id for v in variants}, key=str):
        db.scalar(
            select(Product)
            .where(Product.id == product_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    for item in sorted(cart.items, key=lambda i: str(i.variant_id)):
        variant, product = purchasable_variant(db, item.variant_id)
        stock = locked_inventory(db, item.variant_id)
        if not available(stock.quantity, stock.reserved, item.quantity):
            raise DomainError(
                "insufficient_stock", f"Requested quantity is unavailable for {product.name}.", 409
            )
        lines.append((item, variant, product, stock))
    subtotal, total = totals(
        [(p.price_minor, i.quantity) for i, _, p, _ in lines], settings.shipping_fee_minor
    )
    order = Order(
        user_id=user.id,
        reference=f"GS-{uuid4().hex[:20].upper()}",
        idempotency_key=key,
        request_hash=fingerprint,
        subtotal_minor=subtotal,
        shipping_minor=settings.shipping_fee_minor,
        total_minor=total,
        customer=data.model_dump(mode="json"),
        expires_at=utcnow() + timedelta(minutes=settings.reservation_minutes),
    )
    db.add(order)
    db.flush()
    for item, variant, product, stock in lines:
        stock.reserved += item.quantity
        db.add(
            OrderItem(
                order_id=order.id,
                variant_id=variant.id,
                product_name=product.name,
                sku=variant.sku,
                quantity=item.quantity,
                unit_price_minor=product.price_minor,
            )
        )
        db.add(
            InventoryMovement(
                variant_id=variant.id,
                delta=0,
                reserved_delta=item.quantity,
                reason=f"Reserve {order.reference}",
                actor_id=user.id,
            )
        )
    cart.items.clear()
    db.add(AuditLog(actor_id=user.id, action="order.prepared", resource_id=str(order.id)))
    db.flush()
    db.refresh(order)
    return order


def transition_order(db: Session, order: Order, status: str, actor):
    validate_transition(order.status, status)
    if status == "cancelled":
        release_order(db, order, actor)
    else:
        order.status = status
        if status == "shipped":
            shipment = db.scalar(select(Shipment).where(Shipment.order_id == order.id))
            if not shipment:
                db.add(Shipment(order_id=order.id, status="shipped"))
        if status == "delivered":
            shipment = db.scalar(select(Shipment).where(Shipment.order_id == order.id))
            if shipment:
                shipment.status = "delivered"
    db.add(AuditLog(actor_id=actor, action=f"order.{status}", resource_id=str(order.id)))
    db.flush()


def order_payload(order: Order):
    return {
        "id": str(order.id),
        "reference": order.reference,
        "status": order.status,
        "subtotal": order.subtotal_minor,
        "shipping": order.shipping_minor,
        "total": order.total_minor,
        "currency": order.currency,
        "expiresAt": order.expires_at.isoformat(),
        "createdAt": order.created_at.isoformat(),
        "items": [
            {
                "name": item.product_name,
                "quantity": item.quantity,
                "unitPrice": item.unit_price_minor,
                "sku": item.sku,
            }
            for item in order.items
        ],
        "paymentAvailable": False,
        "nextSteps": "Order is pending payment. Payments are not connected. No payment has been taken; the reservation expires automatically.",
    }

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.core.security import utcnow
from app.integrations.payments import VerifiedPayment
from app.models.entities import AuditLog, InventoryMovement, Order, Payment, PaymentEvent
from app.services.orders import locked_inventory, release_order


def apply_verified_event(db: Session, event: VerifiedPayment):
    # Internal boundary only. No HTTP route accepts caller-supplied VerifiedPayment values.
    payment = db.scalar(
        select(Payment).where(
            Payment.provider == event.provider, Payment.provider_reference == event.reference
        )
    )
    if not payment:
        raise DomainError("payment_unknown", "Payment reference is unknown.", 404)
    order = db.scalar(select(Order).where(Order.id == payment.order_id).with_for_update())
    if not order:
        raise DomainError("order_unknown", "Order is unavailable.", 409)
    payment = db.scalar(
        select(Payment)
        .where(Payment.id == payment.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if db.scalar(
        select(PaymentEvent.id).where(
            PaymentEvent.provider == event.provider, PaymentEvent.event_id == event.event_id
        )
    ):
        return "duplicate"
    if event.amount_minor != order.total_minor or event.currency != "GHS":
        raise DomainError("payment_mismatch", "Payment reconciliation is required.", 409)
    if payment.status in {"paid", "refunded"} and (
        event.status in {"pending", "failed"} or event.status == payment.status
    ):
        db.add(
            PaymentEvent(
                payment_id=payment.id,
                provider=event.provider,
                event_id=event.event_id,
                kind="ignored_stale",
            )
        )
        db.flush()
        return "ignored_stale"
    if event.status == "paid":
        if order.status != "pending_payment" or order.expires_at <= utcnow():
            raise DomainError(
                "late_payment",
                "Payment requires manual reconciliation. Fulfilment was not triggered.",
                409,
            )
        for line in sorted(order.items, key=lambda i: str(i.variant_id)):
            stock = locked_inventory(db, line.variant_id)
            if stock.reserved < line.quantity or stock.quantity < line.quantity:
                raise DomainError(
                    "inventory_conflict", "Inventory reconciliation is required.", 409
                )
            stock.reserved -= line.quantity
            stock.quantity -= line.quantity
            db.add(
                InventoryMovement(
                    variant_id=line.variant_id,
                    delta=-line.quantity,
                    reserved_delta=-line.quantity,
                    reason=f"Verified payment {order.reference}",
                )
            )
        order.status = "paid"
    elif event.status == "failed":
        if order.status == "pending_payment":
            release_order(db, order)
    elif event.status == "refunded":
        if order.status not in {"paid", "processing", "shipped", "delivered"}:
            raise DomainError("invalid_refund", "Refund reconciliation is required.", 409)
        order.status = "refunded"
    payment.status = event.status
    db.add(
        PaymentEvent(
            payment_id=payment.id,
            provider=event.provider,
            event_id=event.event_id,
            kind=event.status,
        )
    )
    db.add(AuditLog(action=f"payment.{event.status}", resource_id=str(payment.id)))
    db.flush()
    return "applied"

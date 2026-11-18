from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.core.security import utcnow
from app.db.session import get_db
from app.dependencies.auth import csrf_if_mutation, current_user
from app.integrations.payments import configured_provider
from app.models.entities import Order, User
from app.services.payments import apply_verified_event

router = APIRouter(prefix="/payments", tags=["Payments — disabled until provider approval"])


@router.post("/orders/{order_id}/initialize", dependencies=[Depends(csrf_if_mutation)])
def initialize(
    order_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    order = db.scalar(select(Order).where(Order.id == order_id, Order.user_id == user.id))
    if not order:
        raise DomainError("not_found", "Order not found.", 404)
    configured_provider()  # Always fails closed in this phase. Never creates a fake payment.


@router.post("/webhook/{provider}")
async def webhook(provider: str, request: Request, db: Session = Depends(get_db, scope="function")):
    adapter = configured_provider()
    timestamp = request.headers.get("x-payment-timestamp", "")
    try:
        instant = datetime.fromisoformat(timestamp)
        if instant.tzinfo is None or abs((utcnow() - instant).total_seconds()) > 300:
            raise ValueError
    except (ValueError, OverflowError):
        raise DomainError("invalid_webhook", "Webhook timestamp is invalid.", 401) from None
    body = await request.body()
    if len(body) > 65536:
        raise DomainError("invalid_webhook", "Webhook body is too large.", 413)
    event = adapter.authenticate_webhook(
        body, request.headers.get("x-payment-signature", ""), timestamp
    )
    if event.provider != provider:
        raise DomainError("invalid_webhook", "Webhook provider mismatch.", 401)
    # Authentication and replay window precede event de-duplication and transactional updates.
    return {"result": apply_verified_event(db, event)}

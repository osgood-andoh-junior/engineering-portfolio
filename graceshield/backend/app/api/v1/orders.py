from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.db.session import get_db
from app.dependencies.auth import csrf_if_mutation, current_user, session_record
from app.models.entities import Order, SessionRecord, User
from app.schemas.contracts import CheckoutInput
from app.services.orders import order_payload, prepare_order, transition_order

router = APIRouter(tags=["Checkout and orders"], dependencies=[Depends(csrf_if_mutation)])


@router.post("/checkout/prepare", status_code=201)
def prepare(
    data: CheckoutInput,
    idempotency_key: str = Header(min_length=16, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$"),
    user: User = Depends(current_user),
    record: SessionRecord = Depends(session_record),
    db: Session = Depends(get_db, scope="function"),
):
    return order_payload(prepare_order(db, user, record, data, idempotency_key))


@router.get("/orders")
def orders(
    page: int = Query(default=1, ge=1, le=100000),
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    records = db.scalars(
        select(Order)
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .offset((page - 1) * 20)
        .limit(20)
    ).all()
    return {"orders": [order_payload(o) for o in records], "page": page}


def owned_order(db: Session, order_id, user, lock=False):
    query = select(Order).where(Order.id == order_id, Order.user_id == user.id)
    record = db.scalar(query.with_for_update() if lock else query)
    if not record:
        raise DomainError("not_found", "Order not found.", 404)
    return record


@router.get("/orders/{order_id}")
def detail(
    order_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    return order_payload(owned_order(db, order_id, user))


@router.post("/orders/{order_id}/cancel")
def cancel(
    order_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    record = owned_order(db, order_id, user, True)
    transition_order(db, record, "cancelled", user.id)
    return order_payload(record)

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import csrf_if_mutation, session_record
from app.models.entities import SessionRecord
from app.schemas.contracts import CartChange
from app.services.cart import cart_payload, change_cart, owned_cart

router = APIRouter(prefix="/cart", tags=["Cart"], dependencies=[Depends(csrf_if_mutation)])


@router.get("")
def view(
    record: SessionRecord = Depends(session_record), db: Session = Depends(get_db, scope="function")
):
    return cart_payload(db, owned_cart(db, record))


@router.post("/items")
def add(
    data: CartChange,
    record: SessionRecord = Depends(session_record),
    db: Session = Depends(get_db, scope="function"),
):
    cart = owned_cart(db, record, True)
    change_cart(db, cart, data.variant_id, data.quantity, True)
    return cart_payload(db, cart)


@router.put("/items/{variant_id}")
def update(
    variant_id: UUID,
    data: CartChange,
    record: SessionRecord = Depends(session_record),
    db: Session = Depends(get_db, scope="function"),
):
    from app.core.exceptions import DomainError

    if variant_id != data.variant_id:
        raise DomainError("invalid_variant", "Variant does not match the requested item.")
    cart = owned_cart(db, record, True)
    change_cart(db, cart, variant_id, data.quantity, False)
    return cart_payload(db, cart)


@router.delete("/items/{variant_id}")
def remove(
    variant_id: UUID,
    record: SessionRecord = Depends(session_record),
    db: Session = Depends(get_db, scope="function"),
):
    cart = owned_cart(db, record, True)
    cart.items[:] = [i for i in cart.items if i.variant_id != variant_id]
    db.flush()
    return cart_payload(db, cart)


@router.delete("")
def clear(
    record: SessionRecord = Depends(session_record), db: Session = Depends(get_db, scope="function")
):
    cart = owned_cart(db, record, True)
    cart.items.clear()
    db.flush()
    return cart_payload(db, cart)

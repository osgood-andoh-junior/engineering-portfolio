from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.models.entities import (
    Cart,
    CartItem,
    Category,
    Product,
    ProductVariant,
    SessionRecord,
    User,
)
from app.repositories.catalogue import public_product
from app.services.rules import available


def owned_cart(db: Session, record: SessionRecord, lock: bool = False) -> Cart:
    # Session lock serializes guest creation; user lock serializes carts across sessions.
    if record.user_id:
        db.scalar(select(User).where(User.id == record.user_id).with_for_update())
        query = select(Cart).where(Cart.user_id == record.user_id)
    else:
        db.scalar(select(SessionRecord).where(SessionRecord.id == record.id).with_for_update())
        query = select(Cart).where(Cart.session_id == record.id, Cart.user_id.is_(None))
    cart = db.scalar(query.with_for_update() if lock else query)
    if not cart:
        cart = Cart(user_id=record.user_id, session_id=None if record.user_id else record.id)
        db.add(cart)
        db.flush()
    return cart


def purchasable_variant(db: Session, variant_id):
    variant = db.get(ProductVariant, variant_id)
    product = db.get(Product, variant.product_id) if variant else None
    category = db.get(Category, product.category_id) if product else None
    if (
        not variant
        or not variant.active
        or not product
        or product.status != "published"
        or not category
        or category.archived
    ):
        raise DomainError("product_unavailable", "This product is no longer available.", 409)
    return variant, product


def change_cart(db: Session, cart: Cart, variant_id, quantity: int, add: bool):
    variant, _ = purchasable_variant(db, variant_id)
    item = next((i for i in cart.items if i.variant_id == variant_id), None)
    desired = quantity + item.quantity if add and item else quantity
    if not variant.inventory or not available(
        variant.inventory.quantity, variant.inventory.reserved, desired
    ):
        raise DomainError(
            "insufficient_stock", "Requested quantity is unavailable. Maximum 20 per item.", 409
        )
    if item:
        item.quantity = desired
    else:
        if len(cart.items) >= 100:
            raise DomainError("cart_limit", "Your bag has reached its item limit.", 409)
        cart.items.append(CartItem(variant_id=variant_id, quantity=desired))
    db.flush()


def cart_payload(db: Session, cart: Cart):
    lines = []
    for item in cart.items:
        variant = db.get(ProductVariant, item.variant_id)
        product = db.get(Product, variant.product_id) if variant else None
        if product and variant:
            category = db.get(Category, product.category_id)
            stock = variant.inventory
            valid = (
                variant.active
                and product.status == "published"
                and category
                and not category.archived
                and stock
                and available(stock.quantity, stock.reserved, item.quantity)
            )
            lines.append(
                {
                    "productId": str(product.id),
                    "variantId": str(variant.id),
                    "quantity": item.quantity,
                    "product": public_product(product),
                    "valid": bool(valid),
                    "lineTotal": product.price_minor * item.quantity,
                }
            )
    return {
        "items": lines,
        "subtotal": sum(line["lineTotal"] for line in lines),
        "count": sum(line["quantity"] for line in lines),
        "currency": "GHS",
    }


def merge_guest_cart(db: Session, record: SessionRecord, user: User):
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    guest = db.scalar(
        select(Cart).where(Cart.session_id == record.id, Cart.user_id.is_(None)).with_for_update()
    )
    existing = db.scalar(select(Cart).where(Cart.user_id == user.id).with_for_update())
    if not guest:
        return
    if not existing:
        guest.user_id = user.id
        guest.session_id = None
        return
    for line in list(guest.items):
        target = next((i for i in existing.items if i.variant_id == line.variant_id), None)
        if target:
            target.quantity = min(20, target.quantity + line.quantity)
        elif len(existing.items) < 100:
            existing.items.append(CartItem(variant_id=line.variant_id, quantity=line.quantity))
    db.delete(guest)
    # Invalid or insufficient-stock merged items are surfaced as invalid, never silently charged.

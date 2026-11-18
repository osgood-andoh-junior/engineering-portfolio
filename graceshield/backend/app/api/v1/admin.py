from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.db.session import get_db
from app.dependencies.auth import admin_user, csrf_if_mutation, public_user
from app.models.entities import (
    AuditLog,
    Category,
    Inventory,
    InventoryMovement,
    Order,
    Product,
    ProductImage,
    ProductVariant,
    User,
)
from app.repositories.catalogue import public_category, public_product
from app.schemas.contracts import (
    CategoryInput,
    InventoryAdjustment,
    ProductInput,
    TransitionInput,
    VariantInput,
)
from app.services.orders import locked_inventory, order_payload, transition_order

router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
    dependencies=[Depends(admin_user), Depends(csrf_if_mutation)],
)


def audit(db: Session, actor: User, action: str, resource):
    db.add(AuditLog(actor_id=actor.id, action=action, resource_id=str(resource)))


def require(db: Session, model, identifier, lock=False):
    record = (
        db.scalar(select(model).where(model.id == identifier).with_for_update())
        if lock
        else db.get(model, identifier)
    )
    if not record:
        raise DomainError("not_found", "Resource not found.", 404)
    return record


@router.get("/overview")
def overview(db: Session = Depends(get_db, scope="function")):
    sales = db.scalar(
        select(func.coalesce(func.sum(Order.total_minor), 0)).where(
            Order.status.in_(["paid", "processing", "shipped", "delivered"])
        )
    )
    low_stock = db.scalar(
        select(func.count())
        .select_from(Inventory)
        .where(Inventory.quantity - Inventory.reserved <= Inventory.low_stock_threshold)
    )
    return {
        "customers": db.scalar(select(func.count()).select_from(User)),
        "products": db.scalar(select(func.count()).select_from(Product)),
        "orders": db.scalar(select(func.count()).select_from(Order)),
        "verifiedSalesMinor": sales,
        "lowStockVariants": low_stock,
        "currency": "GHS",
    }


@router.get("/categories")
def categories(db: Session = Depends(get_db, scope="function")):
    return [
        {**public_category(c), "archived": c.archived}
        for c in db.scalars(select(Category).order_by(Category.name).limit(500))
    ]


def validate_parent(db: Session, parent_id, identifier=None):
    seen = {identifier} if identifier else set()
    while parent_id:
        if parent_id in seen:
            raise DomainError("invalid_parent", "A category cannot be its own ancestor.")
        seen.add(parent_id)
        parent = require(db, Category, parent_id)
        parent_id = parent.parent_id


@router.post("/categories", status_code=201)
def create_category(
    data: CategoryInput,
    actor: User = Depends(admin_user),
    db: Session = Depends(get_db, scope="function"),
):
    validate_parent(db, data.parent_id)
    record = Category(**data.model_dump())
    db.add(record)
    db.flush()
    audit(db, actor, "category.created", record.id)
    return public_category(record)


@router.put("/categories/{identifier}")
def update_category(
    identifier: UUID,
    data: CategoryInput,
    actor: User = Depends(admin_user),
    db: Session = Depends(get_db, scope="function"),
):
    # Serialize hierarchy edits to prevent concurrent cycle creation.
    db.execute(select(func.pg_advisory_xact_lock(10471002)))
    record = require(db, Category, identifier, True)
    validate_parent(db, data.parent_id, identifier)
    for key, value in data.model_dump().items():
        setattr(record, key, value)
    audit(db, actor, "category.updated", identifier)
    db.flush()
    return public_category(record)


@router.delete("/categories/{identifier}")
def archive_category(
    identifier: UUID,
    actor: User = Depends(admin_user),
    db: Session = Depends(get_db, scope="function"),
):
    require(db, Category, identifier, True).archived = True
    audit(db, actor, "category.archived", identifier)
    return {"message": "Category archived."}


@router.get("/products")
def products(page: int = Query(default=1, ge=1), db: Session = Depends(get_db, scope="function")):
    records = db.scalars(
        select(Product).order_by(Product.created_at.desc()).offset((page - 1) * 20).limit(20)
    )
    return [{**public_product(p), "status": p.status} for p in records]


def assign_product(db: Session, record: Product, data: ProductInput):
    from app.integrations.images import image_storage

    for image in data.images:
        image_storage().validate_reference(image.path)
    category = require(db, Category, data.category_id)
    if category.archived:
        raise DomainError("category_archived", "Choose an active category.")
    for key in (
        "category_id",
        "name",
        "slug",
        "description",
        "price_minor",
        "status",
        "demonstration",
    ):
        setattr(record, key, getattr(data, key))
    for image in list(record.images):
        db.delete(image)
    record.images = [
        ProductImage(path=img.path, alt=img.alt, position=i) for i, img in enumerate(data.images)
    ]


@router.post("/products", status_code=201)
def create_product(
    data: ProductInput,
    actor: User = Depends(admin_user),
    db: Session = Depends(get_db, scope="function"),
):
    record = Product()
    assign_product(db, record, data)
    variant = ProductVariant(
        sku=data.sku, name="Standard", inventory=Inventory(quantity=0, reserved=0)
    )
    record.variants = [variant]
    db.add(record)
    db.flush()
    audit(db, actor, "product.created", record.id)
    return public_product(record)


@router.put("/products/{identifier}")
def update_product(
    identifier: UUID,
    data: ProductInput,
    actor: User = Depends(admin_user),
    db: Session = Depends(get_db, scope="function"),
):
    record = require(db, Product, identifier, True)
    assign_product(db, record, data)
    if record.variants:
        record.variants[0].sku = data.sku
    audit(db, actor, "product.updated", identifier)
    db.flush()
    return public_product(record)


@router.post("/products/{identifier}/variants", status_code=201)
def create_variant(
    identifier: UUID,
    data: VariantInput,
    actor: User = Depends(admin_user),
    db: Session = Depends(get_db, scope="function"),
):
    record = require(db, Product, identifier, True)
    if len(record.variants) >= 50:
        raise DomainError("variant_limit", "Maximum variants reached.")
    record.variants.append(
        ProductVariant(**data.model_dump(), inventory=Inventory(quantity=0, reserved=0))
    )
    db.flush()
    audit(db, actor, "variant.created", identifier)
    return public_product(record)


@router.delete("/products/{identifier}")
def archive_product(
    identifier: UUID,
    actor: User = Depends(admin_user),
    db: Session = Depends(get_db, scope="function"),
):
    require(db, Product, identifier, True).status = "archived"
    audit(db, actor, "product.archived", identifier)
    return {"message": "Product archived."}


@router.get("/inventory")
def inventory(page: int = Query(default=1, ge=1), db: Session = Depends(get_db, scope="function")):
    records = db.execute(
        select(Inventory, ProductVariant)
        .join(ProductVariant)
        .order_by(ProductVariant.sku)
        .offset((page - 1) * 50)
        .limit(50)
    )
    return [
        {
            "variantId": str(v.id),
            "sku": v.sku,
            "quantity": i.quantity,
            "reserved": i.reserved,
            "available": i.quantity - i.reserved,
            "lowStockThreshold": i.low_stock_threshold,
        }
        for i, v in records
    ]


@router.post("/inventory/{variant_id}/adjust")
def adjust(
    variant_id: UUID,
    data: InventoryAdjustment,
    actor: User = Depends(admin_user),
    db: Session = Depends(get_db, scope="function"),
):
    stock = locked_inventory(db, variant_id)
    if stock.quantity + data.delta < stock.reserved:
        raise DomainError(
            "stock_conflict", "Adjustment would reduce stock below reserved units.", 409
        )
    stock.quantity += data.delta
    stock.low_stock_threshold = data.low_stock_threshold
    db.add(
        InventoryMovement(
            variant_id=variant_id, delta=data.delta, reason=data.reason, actor_id=actor.id
        )
    )
    audit(db, actor, "inventory.adjusted", variant_id)
    return {"quantity": stock.quantity, "reserved": stock.reserved}


@router.get("/inventory/{variant_id}/movements")
def movements(
    variant_id: UUID,
    page: int = Query(default=1, ge=1),
    db: Session = Depends(get_db, scope="function"),
):
    return [
        {
            "delta": m.delta,
            "reservedDelta": m.reserved_delta,
            "reason": m.reason,
            "createdAt": m.created_at.isoformat(),
        }
        for m in db.scalars(
            select(InventoryMovement)
            .where(InventoryMovement.variant_id == variant_id)
            .order_by(InventoryMovement.created_at.desc())
            .offset((page - 1) * 50)
            .limit(50)
        )
    ]


@router.get("/orders")
def orders(page: int = Query(default=1, ge=1), db: Session = Depends(get_db, scope="function")):
    return [
        order_payload(o)
        for o in db.scalars(
            select(Order).order_by(Order.created_at.desc()).offset((page - 1) * 20).limit(20)
        )
    ]


@router.post("/orders/{identifier}/status")
def order_status(
    identifier: UUID,
    data: TransitionInput,
    actor: User = Depends(admin_user),
    db: Session = Depends(get_db, scope="function"),
):
    record = require(db, Order, identifier, True)
    transition_order(db, record, data.status, actor.id)
    return order_payload(record)


@router.get("/customers")
def customers(page: int = Query(default=1, ge=1), db: Session = Depends(get_db, scope="function")):
    return [
        public_user(db, u)
        for u in db.scalars(
            select(User).order_by(User.created_at.desc()).offset((page - 1) * 20).limit(20)
        )
    ]

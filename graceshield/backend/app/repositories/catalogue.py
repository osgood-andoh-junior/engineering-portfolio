from math import ceil
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.models.entities import Category, Product


def public_category(category: Category):
    return {
        "id": str(category.id),
        "name": category.name,
        "shortName": category.name,
        "slug": category.slug,
        "description": category.description,
        "icon": category.icon,
        "color": category.color,
    }


def public_product(product: Product):
    active = sorted(
        (v for v in product.variants if v.active), key=lambda v: (v.created_at, str(v.id))
    )
    preferred = next(
        (v for v in active if v.inventory and v.inventory.quantity > v.inventory.reserved),
        active[0] if active else None,
    )
    return {
        "id": str(product.id),
        "slug": product.slug,
        "name": product.name,
        "categoryId": str(product.category_id),
        "categoryName": product.category.name,
        "price": {"amount": product.price_minor, "currency": "GHS"},
        "images": [{"path": img.path, "alt": img.alt} for img in product.images],
        "description": product.description,
        "details": ["Demonstration product — not approved stock"] if product.demonstration else [],
        "availability": "available"
        if preferred
        and preferred.inventory
        and preferred.inventory.quantity > preferred.inventory.reserved
        else "unavailable",
        "featured": False,
        "demonstration": product.demonstration,
        "variantId": str(preferred.id) if preferred else None,
        "variants": [
            {
                "id": str(v.id),
                "name": v.name,
                "sku": v.sku,
                "available": max(0, v.inventory.quantity - v.inventory.reserved)
                if v.inventory
                else 0,
            }
            for v in active
        ],
    }


def list_products(
    db: Session,
    q: str,
    category: UUID | None,
    minimum: int | None,
    maximum: int | None,
    sort: str,
    page: int,
):
    filters = [
        Product.status == "published",
        Product.category_id.in_(select(Category.id).where(Category.archived.is_(False))),
    ]
    if q:
        needle = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(
            or_(
                Product.name.ilike(f"%{needle}%", escape="\\"),
                Product.description.ilike(f"%{needle}%", escape="\\"),
            )
        )
    if category:
        filters.append(Product.category_id == category)
    if minimum is not None:
        filters.append(Product.price_minor >= minimum)
    if maximum is not None:
        filters.append(Product.price_minor <= maximum)
    total = db.scalar(select(func.count()).select_from(Product).where(*filters)) or 0
    pages = max(1, ceil(total / 8))
    page = min(page, pages)
    ordering = {
        "price-asc": Product.price_minor.asc(),
        "price-desc": Product.price_minor.desc(),
        "name": Product.name.asc(),
    }.get(sort, Product.created_at.desc())
    products = db.scalars(
        select(Product)
        .where(*filters)
        .order_by(ordering, Product.id)
        .offset((page - 1) * 8)
        .limit(8)
    ).all()
    return {
        "products": [public_product(p) for p in products],
        "total": total,
        "page": page,
        "pages": pages,
    }


def published_product(db: Session, slug: str):
    product = db.scalar(
        select(Product)
        .join(Category)
        .where(Product.slug == slug, Product.status == "published", Category.archived.is_(False))
    )
    if not product:
        raise DomainError("not_found", "Product not found.", 404)
    return product

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.db.session import get_db
from app.models.entities import Category
from app.repositories.catalogue import (
    list_products,
    public_category,
    public_product,
    published_product,
)
from app.schemas.contracts import ProductPage, PublicCategory, PublicProduct

router = APIRouter(tags=["Catalogue"])


@router.get("/categories", response_model=list[PublicCategory])
def categories(db: Session = Depends(get_db, scope="function")):
    return [
        public_category(c)
        for c in db.scalars(
            select(Category)
            .where(Category.archived.is_(False))
            .order_by(Category.created_at, Category.id)
        )
    ]


@router.get("/categories/{slug}", response_model=PublicCategory)
def category(slug: str, db: Session = Depends(get_db, scope="function")):
    record = db.scalar(select(Category).where(Category.slug == slug, Category.archived.is_(False)))
    if not record:
        raise DomainError("not_found", "Category not found.", 404)
    return public_category(record)


@router.get("/products", response_model=ProductPage)
def products(
    q: str = Query(default="", max_length=120),
    category: UUID | None = None,
    min_minor: int | None = Query(default=None, ge=0),
    max_minor: int | None = Query(default=None, ge=0),
    sort: str = Query(default="", pattern="^(|price-asc|price-desc|name)$"),
    page: int = Query(default=1, ge=1, le=1000000),
    db: Session = Depends(get_db, scope="function"),
):
    return list_products(db, q, category, min_minor, max_minor, sort, page)


@router.get("/products/{slug}", response_model=PublicProduct)
def product(slug: str, db: Session = Depends(get_db, scope="function")):
    return public_product(published_product(db, slug))

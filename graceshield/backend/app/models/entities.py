import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security import utcnow
from app.db.base import Base


class Record:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Record, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(500))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    roles: Mapped[list["UserRole"]] = relationship(lazy="selectin")


class Role(Record, Base):
    __tablename__ = "roles"
    name: Mapped[str] = mapped_column(String(30), unique=True)


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    role: Mapped[Role] = relationship(lazy="joined")


class CustomerProfile(Record, Base):
    __tablename__ = "customer_profiles"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    name: Mapped[str] = mapped_column(String(160))


class Address(Record, Base):
    __tablename__ = "addresses"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    street: Mapped[str] = mapped_column(String(200))
    region: Mapped[str] = mapped_column(String(80))
    city: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20))


class SessionRecord(Record, Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf: Mapped[str] = mapped_column(String(100))
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AccountToken(Record, Base):
    __tablename__ = "account_tokens"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    purpose: Mapped[str] = mapped_column(String(20))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class RateLimit(Base):
    __tablename__ = "rate_limits"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Category(Record, Base):
    __tablename__ = "categories"
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(140))
    description: Mapped[str] = mapped_column(Text, default="")
    icon: Mapped[str] = mapped_column(String(30), default="book")
    color: Mapped[str] = mapped_column(String(7), default="#eaf0f8")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id"))
    archived: Mapped[bool] = mapped_column(Boolean, default=False)


class Product(Record, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price_minor >= 0", name="price_nonnegative"),
        CheckConstraint("status IN ('draft','published','archived')", name="publication_status"),
        Index("ix_products_category_status", "category_id", "status"),
    )
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"))
    category: Mapped["Category"] = relationship(lazy="selectin")
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    price_minor: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    demonstration: Mapped[bool] = mapped_column(Boolean, default=False)
    images: Mapped[list["ProductImage"]] = relationship(
        lazy="selectin", order_by="ProductImage.position"
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        lazy="selectin", order_by="(ProductVariant.created_at, ProductVariant.id)"
    )


class ProductVariant(Record, Base):
    __tablename__ = "product_variants"
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), index=True)
    sku: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(100), default="Standard")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    inventory: Mapped["Inventory"] = relationship(lazy="selectin", uselist=False)


class ProductImage(Record, Base):
    __tablename__ = "product_images"
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), index=True)
    path: Mapped[str] = mapped_column(String(300))
    alt: Mapped[str] = mapped_column(String(300))
    position: Mapped[int] = mapped_column(Integer, default=0)


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        CheckConstraint(
            "quantity >= 0 AND reserved >= 0 AND reserved <= quantity", name="stock_bounds"
        ),
        CheckConstraint("low_stock_threshold >= 0", name="threshold_nonnegative"),
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id"), primary_key=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    reserved: Mapped[int] = mapped_column(Integer, default=0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5)


class InventoryMovement(Record, Base):
    __tablename__ = "inventory_movements"
    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_variants.id"), index=True)
    delta: Mapped[int] = mapped_column(Integer)
    reserved_delta: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str] = mapped_column(String(200))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class Cart(Record, Base):
    __tablename__ = "carts"
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), unique=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), unique=True
    )
    items: Mapped[list["CartItem"]] = relationship(lazy="selectin", cascade="all, delete-orphan")


class CartItem(Record, Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "variant_id"),
        CheckConstraint("quantity BETWEEN 1 AND 20", name="quantity_bounds"),
    )
    cart_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("carts.id", ondelete="CASCADE"), index=True
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_variants.id"))
    quantity: Mapped[int] = mapped_column(Integer)


class Order(Record, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key"),
        CheckConstraint(
            "subtotal_minor >= 0 AND shipping_minor >= 0 AND total_minor = subtotal_minor + shipping_minor",
            name="totals_consistent",
        ),
        CheckConstraint(
            "status IN ('pending_payment','paid','processing','shipped','delivered','cancelled','refunded')",
            name="order_status",
        ),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(100))
    request_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="pending_payment")
    subtotal_minor: Mapped[int] = mapped_column(BigInteger)
    shipping_minor: Mapped[int] = mapped_column(BigInteger)
    total_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3), default="GHS")
    customer: Mapped[dict] = mapped_column(JSONB)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    items: Mapped[list["OrderItem"]] = relationship(lazy="selectin")


class OrderItem(Record, Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0 AND unit_price_minor >= 0", name="line_values"),
    )
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_variants.id"))
    product_name: Mapped[str] = mapped_column(String(200))
    sku: Mapped[str] = mapped_column(String(80))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_minor: Mapped[int] = mapped_column(BigInteger)


class Payment(Record, Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount_minor >= 0", name="amount_nonnegative"),)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    provider_reference: Mapped[str | None] = mapped_column(String(200), unique=True)
    provider: Mapped[str] = mapped_column(String(40))
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(30), default="pending")


class PaymentEvent(Record, Base):
    __tablename__ = "payment_events"
    __table_args__ = (UniqueConstraint("provider", "event_id"),)
    payment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payments.id"))
    provider: Mapped[str] = mapped_column(String(40))
    event_id: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(40))


class Shipment(Record, Base):
    __tablename__ = "shipments"
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), unique=True)
    tracking_reference: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default="pending")


class AuditLog(Record, Base):
    __tablename__ = "audit_logs"
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(80))
    resource_id: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)

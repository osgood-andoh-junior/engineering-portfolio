import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import configure_mappers
from sqlalchemy.schema import CreateTable

from app.db.base import Base
from app.models import entities  # noqa: F401
from app.schemas.contracts import CartChange, CheckoutInput, ProductInput, Registration


def test_public_registration_cannot_grant_admin():
    with pytest.raises(ValidationError):
        Registration(
            email="customer@example.com",
            password="a-long-example-password",
            name="Customer",
            roles=["admin"],
        )


def test_password_whitespace_is_not_silently_changed():
    registration = Registration(
        email="sample@example.com", name="Sample", password="  a-long-password  "
    )
    assert registration.password == "  a-long-password  "


@pytest.mark.parametrize("quantity", [0, -1, 21, 1.5, True])
def test_quantity_validation(quantity):
    with pytest.raises(ValidationError):
        CartChange(variant_id="00000000-0000-4000-8000-000000000001", quantity=quantity)


def test_checkout_rejects_client_totals_and_unknown_regions():
    data = dict(
        firstName="Sample",
        lastName="Customer",
        email="sample@example.com",
        phone="0241234567",
        address="Sample street",
        region="Greater Accra",
        city="Accra",
    )
    assert CheckoutInput(**data).region == "Greater Accra"
    with pytest.raises(ValidationError):
        CheckoutInput(**{**data, "total_minor": 1})
    with pytest.raises(ValidationError):
        CheckoutInput(**{**data, "region": "invented"})


def test_product_rejects_float_money_and_unsafe_image_paths():
    data = dict(
        category_id="00000000-0000-4000-8000-000000000001",
        name="Notebook",
        slug="notebook",
        description="Sample notebook",
        price_minor=4500,
        sku="TEST-NOTEBOOK",
        images=[{"path": "/images/notebook.svg", "alt": "Notebook illustration"}],
    )
    assert ProductInput(**data).price_minor == 4500
    for update in [
        {"price_minor": 1.1},
        {"sku": "bad sku"},
        {"images": [{"path": "/images/../../private.svg", "alt": "Unsafe"}]},
    ]:
        with pytest.raises(ValidationError):
            ProductInput(**{**data, **update})


def test_schema_mappers_and_postgresql_constraints_compile():
    configure_mappers()
    expected = {
        "users",
        "roles",
        "user_roles",
        "customer_profiles",
        "addresses",
        "categories",
        "products",
        "product_variants",
        "product_images",
        "inventory",
        "inventory_movements",
        "carts",
        "cart_items",
        "orders",
        "order_items",
        "payments",
        "payment_events",
        "shipments",
        "audit_logs",
        "sessions",
        "account_tokens",
        "rate_limits",
    }
    assert set(Base.metadata.tables) == expected
    sql = "\n".join(
        str(CreateTable(table).compile(dialect=postgresql.dialect()))
        for table in Base.metadata.sorted_tables
    )
    assert "reserved <= quantity" in sql
    assert "UNIQUE (user_id, idempotency_key)" in sql

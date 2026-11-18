from uuid import uuid4

import pytest

from app.core.security import password_hasher
from app.models.entities import (
    Category,
    CustomerProfile,
    Inventory,
    Product,
    ProductImage,
    ProductVariant,
    User,
)

from .conftest import csrf

pytestmark = pytest.mark.integration


def test_registration_login_authorization_and_logout(client):
    email = f"test-{uuid4().hex}@example.com"
    data = {"email": email, "password": "a-unique-example-password", "name": "Sample Customer"}
    assert client.post("/api/v1/auth/register", json=data).status_code == 401
    headers = csrf(client)
    assert (
        client.post(
            "/api/v1/auth/register", json={**data, "roles": ["admin"]}, headers=headers
        ).status_code
        == 422
    )
    assert client.post("/api/v1/auth/register", json=data, headers=headers).status_code == 201
    assert (
        client.post(
            "/api/v1/auth/login", json={k: data[k] for k in ["email", "password"]}, headers=headers
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me").json()["email"] == email
    assert client.get("/api/v1/admin/customers").status_code == 403
    assert client.post("/api/v1/auth/logout", headers=csrf(client)).status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


def test_catalogue_cart_checkout_idempotency_and_inventory(client, db, monkeypatch):
    suffix = uuid4().hex
    category = Category(name="Test category", slug=f"test-{suffix}")
    product = Product(
        category_id=uuid4(),
        name="Test notebook",
        slug=f"notebook-{suffix}",
        description="Isolated test product",
        price_minor=4500,
        status="published",
    )
    db.add(category)
    db.flush()
    product.category_id = category.id
    product.images = [ProductImage(path="/images/notebook.svg", alt="Notebook illustration")]
    variant = ProductVariant(sku=f"TEST-{suffix}", inventory=Inventory(quantity=3, reserved=0))
    product.variants = [variant]
    db.add(product)
    db.flush()
    email = f"customer-{suffix}@example.com"
    user = User(
        email=email, password_hash=password_hasher.hash("a-unique-example-password"), verified=True
    )
    db.add(user)
    db.flush()
    db.add(CustomerProfile(user_id=user.id, name="Test Customer"))
    db.commit()
    assert client.get(f"/api/v1/products/{product.slug}").status_code == 200
    assert (
        client.post(
            "/api/v1/cart/items",
            json={"variant_id": str(variant.id), "quantity": 2},
            headers=csrf(client),
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "a-unique-example-password"},
            headers=csrf(client),
        ).status_code
        == 200
    )
    assert client.get("/api/v1/cart").json()["subtotal"] == 9000
    settings = __import__("app.core.config", fromlist=["get_settings"]).get_settings()
    monkeypatch.setattr(settings, "shipping_fee_minor", 1000)
    monkeypatch.setattr(settings, "shipping_regions", "Greater Accra")
    data = {
        "firstName": "Sample",
        "lastName": "Customer",
        "email": email,
        "phone": "0241234567",
        "address": "Test address 12",
        "region": "Greater Accra",
        "city": "Accra",
    }
    key = uuid4().hex
    headers = {**csrf(client), "idempotency-key": key}
    response = client.post("/api/v1/checkout/prepare", json=data, headers=headers)
    assert response.status_code == 201, response.text
    order = response.json()
    assert order["total"] == 10000 and order["status"] == "pending_payment"
    assert (
        client.post("/api/v1/checkout/prepare", json=data, headers=headers).json()["id"]
        == order["id"]
    )
    assert (
        client.post("/api/v1/orders/" + order["id"] + "/cancel", headers=csrf(client)).status_code
        == 200
    )
    assert client.get("/api/v1/orders").json()["orders"][0]["status"] == "cancelled"
    db.expire_all()
    assert db.get(Inventory, variant.id).reserved == 0

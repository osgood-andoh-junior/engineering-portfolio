from uuid import uuid4

import pytest

from app.core.security import password_hasher
from app.models.entities import Role, User, UserRole

from .conftest import csrf

pytestmark = pytest.mark.integration


def test_admin_catalogue_and_inventory_are_authorized_and_audited(client, db):
    marker = uuid4().hex
    role = Role(name="admin-" + marker)
    # Use actual admin role, reusing it if present in the isolated database.
    from sqlalchemy import select

    role = db.scalar(select(Role).where(Role.name == "admin")) or Role(name="admin")
    db.add(role)
    db.flush()
    user = User(
        email=marker + "@example.com",
        password_hash=password_hasher.hash("isolated-admin-password"),
        verified=True,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "isolated-admin-password"},
        headers=csrf(client),
    )
    assert login.status_code == 200
    category = client.post(
        "/api/v1/admin/categories",
        json={"name": "Test category", "slug": "cat-" + marker},
        headers=csrf(client),
    )
    assert category.status_code == 201, category.text
    payload = {
        "category_id": category.json()["id"],
        "name": "Test product",
        "slug": "prod-" + marker,
        "description": "Isolated catalogue fixture",
        "price_minor": 1250,
        "sku": "SKU-" + marker.upper(),
        "status": "draft",
        "images": [{"path": "/images/notebook.svg", "alt": "Test notebook"}],
    }
    created = client.post("/api/v1/admin/products", json=payload, headers=csrf(client))
    assert created.status_code == 201, created.text
    product = created.json()
    assert client.get("/api/v1/products/" + product["slug"]).status_code == 404
    assert (
        client.put(
            "/api/v1/admin/products/" + product["id"],
            json={**payload, "status": "published"},
            headers=csrf(client),
        ).status_code
        == 200
    )
    variant = product["variants"][0]["id"]
    assert (
        client.post(
            "/api/v1/admin/inventory/" + variant + "/adjust",
            json={"delta": 10, "reason": "Automated test stock"},
            headers=csrf(client),
        ).status_code
        == 200
    )
    assert client.get("/api/v1/products/" + product["slug"]).json()["availability"] == "available"
    assert (
        client.delete("/api/v1/admin/products/" + product["id"], headers=csrf(client)).status_code
        == 200
    )
    assert client.get("/api/v1/products/" + product["slug"]).status_code == 404
    from app.models.entities import AuditLog

    assert db.scalar(
        select(AuditLog.id).where(
            AuditLog.actor_id == user.id, AuditLog.action == "product.created"
        )
    )

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


def test_openapi_exposes_versioned_contracts():
    schema = app.openapi()
    for path in [
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/cart",
        "/api/v1/checkout/prepare",
        "/api/v1/admin/products",
        "/api/v1/admin/inventory/{variant_id}/adjust",
    ]:
        assert path in schema["paths"]
    assert "roles" not in schema["components"]["schemas"]["Registration"]["properties"]


def test_health_endpoint_does_not_leak_configuration():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200 and response.json() == {"status": "ok"}
    assert response.headers["Cache-Control"] == "no-store"
    assert "X-Request-ID" in response.headers


def test_invalid_query_is_rejected_without_echoing_input():
    client = TestClient(app)
    # Invalid JSON fields can be rejected before any DB access only on public health; actual
    # registration requires a persisted CSRF session and is covered in cloud integration tests.
    app.dependency_overrides[get_db] = lambda: None
    try:
        response = client.get(
            "/api/v1/products", params={"page": "not-a-number", "q": "secret-marker"}
        )
        assert response.status_code == 422
        assert "secret-marker" not in response.text
    finally:
        app.dependency_overrides.clear()

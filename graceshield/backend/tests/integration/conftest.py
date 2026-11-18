import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db, get_engine
from app.main import app


@pytest.fixture
def db(monkeypatch):
    if os.environ.get("RUN_DB_TESTS") != "true":
        pytest.skip(
            "Cloud PostgreSQL tests not run: configure isolated TEST_DATABASE_URL/HOST/NAME and RUN_DB_TESTS=true."
        )
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_settings().isolated_test_url()  # Explicit failure, never skip, for unsafe requested runs.
    connection = get_engine().connect()
    transaction = connection.begin()
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    yield session
    session.close()
    transaction.rollback()
    connection.close()
    get_engine().dispose()
    get_engine.cache_clear()
    get_settings.cache_clear()


@pytest.fixture
def client(db):
    def override():
        yield db
        db.commit()

    app.dependency_overrides[get_db] = override
    with TestClient(app, client=(f"test-{uuid4().hex}", 50000)) as client:
        yield client
    app.dependency_overrides.clear()


def csrf(client):
    result = client.get("/api/v1/auth/session")
    assert result.status_code == 200
    return {"origin": "http://127.0.0.1:3000", "x-csrf-token": result.json()["csrf"]}

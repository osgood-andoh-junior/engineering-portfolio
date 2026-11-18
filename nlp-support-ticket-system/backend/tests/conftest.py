import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app


@pytest.fixture
def settings(tmp_path):
    return Settings(tmp_path / "database.sqlite", tmp_path / "artifacts", "http://localhost:3000")


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


@pytest.fixture
def repo(client, app):
    return app.state.repository

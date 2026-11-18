from fastapi.testclient import TestClient

from backend.app.main import create_app
from ml.src.interfaces import CATEGORIES


class ContractFixture:
    """Test-only canned responses verify plumbing; no learning or inference is performed."""

    def fit(self, texts, labels):
        assert texts == ["fixture ticket"]
        assert labels == ["Other"]

    def save(self, path):
        path.write_text("test fixture", encoding="utf-8")

    def load(self, path):
        assert path.read_text(encoding="utf-8") == "test fixture"

    def predict(self, texts):
        return ["Other"]

    def predict_proba(self, texts):
        return [{name: float(name == "Other") for name in CATEGORIES}]


def test_swappable_contract_training_prediction_and_storage(settings):
    app = create_app(settings, factories={"naive_bayes": ContractFixture})
    with TestClient(app) as client:
        ticket = client.post(
            "/api/tickets",
            json={"text": "fixture ticket", "actual_category": "Other"},
        ).json()
        response = client.post("/api/training/start", json={})
        assert response.status_code == 201
        version = response.json()["model"]["version"]
        response = client.post("/api/predictions", json={"ticket_id": ticket["id"]})
        assert response.status_code == 200
        assert response.json()["model"] == version
        assert response.json()["processing_time_ms"] >= 0
        stored = client.get(f"/api/tickets/{ticket['id']}").json()
        assert stored["predicted_category"] == "Other"
        assert stored["model_version"] == version
        assert client.get("/api/training/runs").json()[0]["status"] == "completed"


def test_invalid_classifier_output_is_not_stored(settings):
    class InvalidFixture(ContractFixture):
        def predict_proba(self, texts):
            return [{"Other": 2.0}]

    app = create_app(settings, factories={"naive_bayes": InvalidFixture})
    with TestClient(app) as client:
        ticket = client.post(
            "/api/tickets",
            json={"text": "fixture ticket", "actual_category": "Other"},
        ).json()
        client.post("/api/training/start", json={})
        assert (
            client.post(
                "/api/predictions",
                json={"ticket_id": ticket["id"]},
            ).status_code
            == 502
        )
        assert client.get(f"/api/tickets/{ticket['id']}").json()["predicted_category"] is None


def test_training_without_artifact_does_not_register_model(settings):
    class NoArtifactFixture(ContractFixture):
        def save(self, path):
            pass

    with TestClient(create_app(settings, factories={"naive_bayes": NoArtifactFixture})) as client:
        client.post("/api/tickets", json={"text": "fixture ticket", "actual_category": "Other"})
        assert client.post("/api/training/start", json={}).status_code == 409
        assert client.get("/api/models").json() == []
        assert client.get("/api/training/runs").json()[0]["status"] == "failed"

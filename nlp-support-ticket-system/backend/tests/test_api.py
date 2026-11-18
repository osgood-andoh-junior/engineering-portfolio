import pytest


def test_health_and_sqlite_initialization(client, settings, repo):
    assert client.get("/health").json() == {"status": "ok", "database": "sqlite"}
    assert settings.database_path.is_file()
    names = {r["name"] for r in repo.rows("SELECT name FROM sqlite_master WHERE type='table'")}
    assert names == {"tickets", "model_versions", "evaluation_results", "training_runs"}


def test_ticket_crud(client):
    response = client.post(
        "/api/tickets", json={"text": " Wi-Fi issue ", "actual_category": "Network"}
    )
    assert response.status_code == 201
    ticket = response.json()
    assert ticket["text"] == "Wi-Fi issue"
    assert ticket["predicted_category"] is None
    assert ticket["confidence"] is None
    assert ticket["model_version"] is None
    assert ticket["created_at"]
    path = f"/api/tickets/{ticket['id']}"
    assert client.get(path).json() == ticket
    assert client.get("/api/tickets").json() == [ticket]
    response = client.patch(path, json={"text": "Account issue", "actual_category": "Account"})
    assert response.json()["actual_category"] == "Account"
    assert client.patch(path, json={"actual_category": None}).json()["actual_category"] is None
    assert client.delete(path).status_code == 204
    assert client.get(path).status_code == 404
    assert client.delete(path).status_code == 404
    assert client.get("/api/tickets").json() == []


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"text": ""},
        {"text": "   "},
        {"text": "x" * 10001},
        {"text": 123},
        {"text": "x", "actual_category": "Invalid"},
        {"text": "x", "confidence": 0.9},
    ],
)
def test_ticket_validation(client, body):
    assert client.post("/api/tickets", json=body).status_code == 422


@pytest.mark.parametrize("body", [{}, {"text": None}, {"text": " "}, {"id": 1}])
def test_patch_validation(client, body):
    ticket = client.post("/api/tickets", json={"text": "valid"}).json()
    assert client.patch(f"/api/tickets/{ticket['id']}", json=body).status_code == 422


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"text": ""},
        {"text": "x", "ticket_id": 1},
        {"ticket_id": 0},
        {"text": "x", "model_version": ""},
        {"text": "x", "extra": True},
    ],
)
def test_prediction_validation(client, body):
    assert client.post("/api/predictions", json=body).status_code == 422


def test_missing_resources(client):
    assert client.get("/api/tickets/999").status_code == 404
    assert client.patch("/api/tickets/999", json={"text": "x"}).status_code == 404
    assert client.post("/api/predictions", json={"ticket_id": 999}).status_code == 404
    assert (
        client.post(
            "/api/predictions",
            json={"text": "x", "model_version": "missing"},
        ).status_code
        == 404
    )


def test_clean_prediction_error_leaves_ticket_unmodified(client):
    ticket = client.post("/api/tickets", json={"text": "Wi-Fi unavailable"}).json()
    for body in ({"text": "Wi-Fi unavailable"}, {"ticket_id": ticket["id"]}):
        response = client.post("/api/predictions", json=body)
        assert response.status_code == 501
        assert response.json() == {
            "error": "STUDENT_ML_NOT_IMPLEMENTED",
            "component": "naive_bayes",
            "message": "Complete TODO(STUDENT-ML) in the ML module.",
        }
    assert client.get(f"/api/tickets/{ticket['id']}").json() == ticket
    assert client.get("/api/models").json() == []
    assert client.get("/api/evaluations").json() == []


@pytest.mark.parametrize(
    "model", ["naive_bayes", "neural_network", "rnn", "attention", "transformer"]
)
def test_training_stubs_fail_cleanly_and_record_failure(client, model):
    response = client.post("/api/training/start", json={"model": model})
    assert response.status_code == 501
    assert response.json()["component"] == model
    run = client.get("/api/training/runs").json()[0]
    assert run["status"] == "failed"
    assert run["model_version"] is None
    assert run["finished_at"]
    assert client.get("/api/models").json() == []


def test_training_validation_and_cors(client):
    assert client.post("/api/training/start", json={"model": "unknown"}).status_code == 422
    response = client.options(
        "/api/tickets",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    response = client.options(
        "/api/tickets",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers

import sqlite3

import pytest
from pydantic import ValidationError

from backend.app.database.repository import Repository
from backend.app.database.session import Database

# Storage fixtures only: these values are never generated or served by a real classifier.
METRICS = {"accuracy": 0.5, "precision": 0.4, "recall": 0.3, "f1": 0.2}


def test_persistence_and_sql_values(repo, settings):
    text = "Student's ticket; DROP TABLE tickets; --"
    ticket = repo.create_ticket(text)
    reopened = Repository(Database(settings.database_path))
    assert reopened.get_ticket(ticket["id"])["text"] == text
    assert reopened.tickets() == [ticket]


def test_model_registry_and_evaluation_storage(client, repo, settings):
    model = repo.register_model("naive_bayes", "test-v1", settings.artifact_dir / "test.model")
    assert repo.get_model("test-v1") == model
    assert repo.get_model("absent") is None
    assert client.get("/api/models").json() == [model]
    evaluation = repo.save_evaluation("test-v1", METRICS)
    assert evaluation["metrics"] == METRICS
    assert client.get("/api/evaluations").json() == [evaluation]
    with pytest.raises(sqlite3.IntegrityError):
        repo.register_model("naive_bayes", "test-v1", "duplicate.model")
    with pytest.raises(sqlite3.IntegrityError):
        repo.save_evaluation("missing", METRICS)
    with pytest.raises(ValidationError):
        repo.save_evaluation("test-v1", {**METRICS, "accuracy": 2})
    with pytest.raises(ValidationError):
        repo.save_evaluation("test-v1", {**METRICS, "f1": float("nan")})


def test_editing_text_clears_old_prediction(repo):
    repo.register_model("naive_bayes", "test-v1", "unused-test-artifact")
    ticket = repo.create_ticket("first", "Network")
    repo.record_prediction(ticket["id"], "Network", 0.5, "test-v1")
    updated = repo.update_ticket(ticket["id"], {"text": "different"})
    assert updated["predicted_category"] is None
    assert updated["confidence"] is None
    assert updated["model_version"] is None


def test_transaction_rolls_back_and_foreign_keys_hold(repo):
    with pytest.raises(sqlite3.IntegrityError):
        with repo.database.connect() as db:
            db.execute("INSERT INTO tickets (text, created_at) VALUES ('valid', 'now')")
            db.execute("INSERT INTO tickets (text, created_at) VALUES ('', 'now')")
    assert repo.tickets() == []
    ticket = repo.create_ticket("valid")
    with pytest.raises(sqlite3.IntegrityError):
        repo.record_prediction(ticket["id"], "Network", 0.5, "unregistered")


def test_missing_artifact_is_a_conflict(client, repo, settings):
    repo.register_model("naive_bayes", "missing-file", settings.artifact_dir / "missing.model")
    response = client.post("/api/predictions", json={"text": "ticket"})
    assert response.status_code == 409


def test_artifact_path_must_stay_inside_artifact_directory(client, repo, settings):
    outside = settings.database_path.parent / "outside.model"
    outside.write_text("fixture")
    repo.register_model("naive_bayes", "outside", outside)
    assert client.post("/api/predictions", json={"text": "ticket"}).status_code == 409

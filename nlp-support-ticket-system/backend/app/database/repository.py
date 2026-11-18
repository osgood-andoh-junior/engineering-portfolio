import json
from datetime import datetime, timezone

from backend.app.schemas import Metrics

from .session import Database


def now():
    return datetime.now(timezone.utc).isoformat()


class Repository:
    def __init__(self, database: Database):
        self.database = database

    def rows(self, query, values=()):
        with self.database.connect() as db:
            return [dict(row) for row in db.execute(query, values).fetchall()]

    def write(self, query, values=()):
        with self.database.connect() as db:
            return db.execute(query, values).lastrowid

    def create_ticket(self, text, actual_category=None):
        ticket_id = self.write(
            "INSERT INTO tickets (text, actual_category, created_at) VALUES (?, ?, ?)",
            (text, actual_category, now()),
        )
        return self.get_ticket(ticket_id)

    def get_ticket(self, ticket_id):
        rows = self.rows("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        return rows[0] if rows else None

    def tickets(self):
        return self.rows("SELECT * FROM tickets ORDER BY id DESC")

    def update_ticket(self, ticket_id, changes):
        # Only API-owned fields are accepted; SQL identifiers never come from request values.
        with self.database.connect() as db:
            for field in ("text", "actual_category"):
                if field in changes:
                    db.execute(
                        f"UPDATE tickets SET {field} = ? WHERE id = ?",
                        (changes[field], ticket_id),
                    )
            if "text" in changes:
                db.execute(
                    "UPDATE tickets SET predicted_category=NULL, confidence=NULL, "
                    "model_version=NULL WHERE id=?",
                    (ticket_id,),
                )
        return self.get_ticket(ticket_id)

    def delete_ticket(self, ticket_id):
        with self.database.connect() as db:
            return db.execute("DELETE FROM tickets WHERE id=?", (ticket_id,)).rowcount > 0

    def record_prediction(self, ticket_id, category, confidence, version):
        self.write(
            "UPDATE tickets SET predicted_category=?, confidence=?, model_version=? WHERE id=?",
            (category, confidence, version, ticket_id),
        )

    def register_model(self, model, version, artifact_path):
        model_id = self.write(
            "INSERT INTO model_versions (model, version, artifact_path, created_at) "
            "VALUES (?,?,?,?)",
            (model, version, str(artifact_path), now()),
        )
        return self.rows("SELECT * FROM model_versions WHERE id=?", (model_id,))[0]

    def models(self):
        return self.rows("SELECT * FROM model_versions ORDER BY id DESC")

    def get_model(self, version):
        rows = self.rows("SELECT * FROM model_versions WHERE version=?", (version,))
        return rows[0] if rows else None

    def save_evaluation(self, version, metrics):
        validated = Metrics.model_validate(metrics).model_dump()
        result_id = self.write(
            "INSERT INTO evaluation_results (model_version, metrics, created_at) VALUES (?,?,?)",
            (version, json.dumps(validated), now()),
        )
        return next(row for row in self.evaluations() if row["id"] == result_id)

    def evaluations(self):
        rows = self.rows("SELECT * FROM evaluation_results ORDER BY id DESC")
        for row in rows:
            row["metrics"] = json.loads(row["metrics"])
        return rows

    def start_training(self, model):
        return self.write(
            "INSERT INTO training_runs (model, status, created_at) VALUES (?, 'running', ?)",
            (model, now()),
        )

    def finish_training(self, run_id, status, version=None, error=None):
        self.write(
            "UPDATE training_runs SET status=?, model_version=?, error=?, finished_at=? WHERE id=?",
            (status, version, error, now(), run_id),
        )

    def training_runs(self):
        return self.rows("SELECT * FROM training_runs ORDER BY id DESC")

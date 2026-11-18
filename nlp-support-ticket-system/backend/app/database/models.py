# SQLite schema; model binary artifacts live on disk.
SCHEMA = """
CREATE TABLE IF NOT EXISTS model_versions (
    id INTEGER PRIMARY KEY,
    model TEXT NOT NULL,
    version TEXT NOT NULL UNIQUE,
    artifact_path TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY,
    text TEXT NOT NULL CHECK(length(trim(text)) > 0),
    actual_category TEXT CHECK(actual_category IN
        ('Network','Account','Payment','Software','Hardware','Other')),
    predicted_category TEXT CHECK(predicted_category IN
        ('Network','Account','Payment','Software','Hardware','Other')),
    confidence REAL CHECK(confidence BETWEEN 0 AND 1),
    model_version TEXT REFERENCES model_versions(version),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evaluation_results (
    id INTEGER PRIMARY KEY,
    model_version TEXT NOT NULL REFERENCES model_versions(version),
    metrics TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS training_runs (
    id INTEGER PRIMARY KEY,
    model TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('running','completed','failed')),
    model_version TEXT REFERENCES model_versions(version),
    error TEXT,
    created_at TEXT NOT NULL,
    finished_at TEXT
);
"""

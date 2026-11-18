"""Import student-produced evaluation results without calculating any metrics."""

import argparse
import json
from pathlib import Path

from backend.app.config import Settings
from backend.app.database.repository import Repository
from backend.app.database.session import Database


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_version")
    parser.add_argument("metrics_file", type=Path)
    args = parser.parse_args()
    database = Database(Settings.from_env().database_path)
    database.initialize()
    repository = Repository(database)
    if repository.get_model(args.model_version) is None:
        parser.error("Model version is not registered.")
    metrics = json.loads(args.metrics_file.read_text(encoding="utf-8"))
    result = repository.save_evaluation(args.model_version, metrics)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

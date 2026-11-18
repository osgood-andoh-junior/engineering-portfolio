import math
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import HTTPException

from backend.app.schemas import PredictionResult
from ml.src.interfaces import CATEGORIES, Classifier


class IntelligenceService:
    def __init__(self, repository, factories, artifact_dir: Path):
        self.repository = repository
        self.factories = factories
        self.artifact_dir = artifact_dir.resolve()

    def classifier(self, name: str) -> Classifier:
        factory = self.factories.get(name)
        if factory is None:
            raise HTTPException(409, "Model implementation is not registered.")
        return factory()

    def predict(self, request):
        started = perf_counter()
        ticket = None
        if request.ticket_id is not None:
            ticket = self.repository.get_ticket(request.ticket_id)
            if ticket is None:
                raise HTTPException(404, "Ticket not found.")
        text = ticket["text"] if ticket else request.text
        record = (
            self.repository.get_model(request.model_version)
            if request.model_version
            else next(iter(self.repository.models()), None)
        )
        if request.model_version and record is None:
            raise HTTPException(404, "Model version not found.")
        classifier = self.classifier(record["model"] if record else "naive_bayes")
        if record:
            path = Path(record["artifact_path"]).resolve()
            if not path.is_relative_to(self.artifact_dir) or not path.is_file():
                raise HTTPException(409, "Model artifact is missing or outside ARTIFACT_DIR.")
            classifier.load(path)
        categories = classifier.predict([text])
        probabilities = classifier.predict_proba([text])
        if not record:
            raise HTTPException(409, "Train and register a model before serving predictions.")
        try:
            if len(categories) != 1 or len(probabilities) != 1:
                raise ValueError()
            category = categories[0]
            distribution = probabilities[0]
            if set(distribution) != set(CATEGORIES):
                raise ValueError()
            if any(not math.isfinite(p) or not 0 <= p <= 1 for p in distribution.values()):
                raise ValueError()
            if not math.isclose(sum(distribution.values()), 1, abs_tol=1e-5):
                raise ValueError()
            result = PredictionResult(
                category=category,
                confidence=distribution[category],
                model=record["version"],
                processing_time_ms=(perf_counter() - started) * 1000,
            )
        except (ValueError, TypeError, KeyError):
            raise HTTPException(502, "Classifier returned an invalid prediction.") from None
        if ticket:
            self.repository.record_prediction(
                ticket["id"],
                result.category,
                result.confidence,
                result.model,
            )
        return result

    def train(self, name):
        run_id = self.repository.start_training(name)
        try:
            tickets = [t for t in self.repository.tickets() if t["actual_category"] is not None]
            classifier = self.classifier(name)
            classifier.fit([t["text"] for t in tickets], [t["actual_category"] for t in tickets])
            version = f"{name}-{uuid4().hex}"
            self.artifact_dir.mkdir(parents=True, exist_ok=True)
            path = self.artifact_dir / f"{version}.model"
            classifier.save(path)
            if not path.is_file():
                raise HTTPException(409, "Classifier did not produce an artifact.")
            model = self.repository.register_model(name, version, path)
            self.repository.finish_training(run_id, "completed", version)
            return {"run_id": run_id, "status": "completed", "model": model}
        except Exception as error:
            self.repository.finish_training(run_id, "failed", error=type(error).__name__)
            raise

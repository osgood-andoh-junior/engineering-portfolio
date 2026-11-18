from pathlib import Path
from typing import Protocol, Sequence

CATEGORIES = ("Network", "Account", "Payment", "Software", "Hardware", "Other")


class StudentMLNotImplemented(NotImplementedError):
    def __init__(self, component: str):
        self.component = component
        super().__init__(f"Complete TODO(STUDENT-ML): {component}")


class Classifier(Protocol):
    """Backend contract. Probability mappings use the category names in CATEGORIES."""

    def fit(self, texts: Sequence[str], labels: Sequence[str]) -> None: ...
    def predict(self, texts: Sequence[str]) -> Sequence[str]: ...
    def predict_proba(self, texts: Sequence[str]) -> Sequence[dict[str, float]]: ...
    def save(self, path: Path) -> None: ...
    def load(self, path: Path) -> None: ...

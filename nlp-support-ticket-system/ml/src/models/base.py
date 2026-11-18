from pathlib import Path
from typing import Sequence

from ml.src.interfaces import StudentMLNotImplemented


class StudentClassifier:
    """Shared unimplemented contract; each model owns its future implementation."""

    component = "classifier"

    def fit(self, texts: Sequence[str], labels: Sequence[str]) -> None:
        """TODO(STUDENT-ML): implement fit in the chosen classifier."""
        raise StudentMLNotImplemented(self.component)

    def predict(self, texts: Sequence[str]) -> Sequence[str]:
        """TODO(STUDENT-ML): implement predict in the chosen classifier."""
        raise StudentMLNotImplemented(self.component)

    def predict_proba(self, texts: Sequence[str]) -> Sequence[dict[str, float]]:
        """TODO(STUDENT-ML): implement predict_proba in the chosen classifier."""
        raise StudentMLNotImplemented(self.component)

    def save(self, path: Path) -> None:
        """TODO(STUDENT-ML): implement artifact serialization in the chosen classifier."""
        raise StudentMLNotImplemented(self.component)

    def load(self, path: Path) -> None:
        """TODO(STUDENT-ML): implement artifact loading in the chosen classifier."""
        raise StudentMLNotImplemented(self.component)

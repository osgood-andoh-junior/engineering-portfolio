from pathlib import Path
from typing import Protocol

from app.core.exceptions import DomainError


class ImageStorage(Protocol):
    def validate_reference(self, reference: str) -> None: ...


class ControlledLocalAssets:
    """References approved repository assets only. This is not an upload endpoint."""

    def __init__(self, root: Path):
        self.root = root.resolve()

    def validate_reference(self, reference: str) -> None:
        path = (self.root / reference.lstrip("/")).resolve()
        if (
            not path.is_relative_to(self.root / "images")
            or path.suffix.lower() not in {".svg", ".png", ".jpg", ".webp"}
            or not path.is_file()
        ):
            raise DomainError("invalid_image", "Choose an existing approved image asset.")


def image_storage() -> ImageStorage:
    return ControlledLocalAssets(Path(__file__).parents[3] / "frontend" / "public")

from pathlib import Path

import pytest

from app.core.exceptions import DomainError
from app.integrations.images import ControlledLocalAssets, image_storage


def test_only_existing_controlled_images_are_accepted(tmp_path: Path):
    store = ControlledLocalAssets(tmp_path)
    for reference in [
        "/images/../../secret.svg",
        "/images/missing.svg",
        "https://external.invalid/a.png",
    ]:
        with pytest.raises(DomainError):
            store.validate_reference(reference)
    image_storage().validate_reference("/images/notebook.svg")

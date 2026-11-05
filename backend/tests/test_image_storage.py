"""Private storage and exact-image lookup tests, not a diagnosis evaluation."""

from types import SimpleNamespace
from PIL import Image
from app.modules.images.image_store import normalized_image, reference_result, image_path
import pytest


def test_pixel_digest_is_deterministic_and_metadata_is_removed():
    image = Image.new("RGB", (2000, 1000), "gray")
    image.info["private"] = "metadata"
    normalized, digest = normalized_image(image)
    assert normalized.size == (1600, 800)
    assert not normalized.info
    assert digest == normalized_image(image)[1]
    assert digest != normalized_image(Image.new("RGB", (2000, 1000), "red"))[1]


def test_reference_lookup_abstains_on_conflicting_labels(tmp_path, monkeypatch):
    monkeypatch.setenv("DERMA_IMAGE_STORAGE", str(tmp_path))
    from uuid import uuid4

    records = [
        SimpleNamespace(id=1, file_uuid=str(uuid4()), disease_id=1),
        SimpleNamespace(id=2, file_uuid=str(uuid4()), disease_id=2),
    ]
    for record in records:
        image_path(record.file_uuid).write_bytes(b"fixture")
    db = SimpleNamespace(
        scalars=lambda *args: records,
        get=lambda model, key: SimpleNamespace(
            id=key, name=key, published=True, category="Da liễu"
        ),
    )
    result = reference_result(Image.new("RGB", (512, 512), "gray"), "clinical", db)
    assert result["status"] == "unknown" and "candidates" not in result


def test_storage_path_rejects_traversal():
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        image_path("../private-file")

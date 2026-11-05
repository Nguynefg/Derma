"""Keep tests independent of a model installed on the developer's machine."""

import pytest


@pytest.fixture(autouse=True)
def isolate_image_model(monkeypatch):
    monkeypatch.setenv("DERMA_IMAGE_MODEL_CARD", "off")

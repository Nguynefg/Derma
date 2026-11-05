import io
import json
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest
from fastapi import HTTPException
from PIL import Image
import app.modules.images.image_gemini as vision
import app.integrations.gemini.client as gemini
from app.modules.images.image_catalog import match_model_result


@pytest.mark.parametrize(
    "uncertain,ids,expected",
    [
        (False, ["1"], "research_result"),
        (True, ["1"], "unknown"),
        (False, ["invented-id"], "unknown"),
        (False, [], "unknown"),
    ],
)
def test_vision_validates_database_ids(monkeypatch, uncertain, ids, expected):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    topic = SimpleNamespace(
        id=1,
        name="Chàm",
        english_name="Eczema",
        published=True,
        summary="Bài tham khảo",
        category="Da liễu",
        version=1,
    )
    db = SimpleNamespace(scalars=lambda *a: [topic], get=lambda *a: topic)

    def fake_open(request, timeout):
        body = json.loads(request.data)
        assert request.get_header("X-goog-api-key") == "test-only"
        content = body["contents"][0]["parts"]
        assert content[1]["inlineData"]["mimeType"] == "image/jpeg"
        assert body["generationConfig"]["responseMimeType"] == "application/json"
        output = json.dumps(
            dict(
                uncertain=uncertain,
                disease_ids=ids,
                observations="Vùng da đỏ",
                explanation="Cần khám để xác định",
                observation_labels=["pustules", "itch", "invented-label", "pustules"],
            )
        )
        return io.BytesIO(
            json.dumps(
                {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": output}]}}]}
            ).encode()
        )

    monkeypatch.setattr(gemini, "urlopen", fake_open)
    result = match_model_result(vision.analyze_with_gemini(Image.new("RGB", (300, 300)), db), db)
    assert result["status"] == expected
    assert result["observation_labels"] == [{"id": "pustules", "name": "Mụn mủ"}]
    if expected == "research_result":
        assert result["candidates"][0]["name"] == "Chàm"
        assert result["database_match"]["status"] == "matched"
    else:
        assert not result.get("candidates")


def test_vision_missing_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(HTTPException) as error:
        vision.analyze_with_gemini(None, None)
    assert error.value.status_code == 503


def test_vision_does_not_offer_internal_disease_from_photo(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    skin = SimpleNamespace(
        id=1, name="Chàm", english_name="Eczema", category="Da liễu", summary="Da", slug="eczema"
    )
    internal = SimpleNamespace(
        id=2, name="Hen", english_name="Asthma", category="Hô hấp", summary="Phổi", slug="asthma"
    )

    def fake_generate(instructions, parts, **kwargs):
        payload = json.loads(parts[0]["text"])
        assert [t["id"] for t in payload["topics"]] == ["1"]
        return json.dumps(
            {"uncertain": False, "observations": "Ảnh", "explanation": "Test", "disease_ids": ["2"]}
        )

    monkeypatch.setattr(vision, "generate", fake_generate)
    result = vision.analyze_with_gemini(
        Image.new("RGB", (300, 300)), SimpleNamespace(scalars=lambda *args: [skin, internal])
    )
    assert result["status"] == "unknown"
    assert result["candidates"] == []


def test_vision_provider_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    topic = SimpleNamespace(id=1, name="Chàm", english_name="Eczema", category="Da liễu")

    def fail(*a, **k):
        raise HTTPError("https://generativelanguage.googleapis.com", 429, "private", {}, None)

    monkeypatch.setattr(gemini, "urlopen", fail)
    with pytest.raises(HTTPException) as error:
        vision.analyze_with_gemini(
            Image.new("RGB", (300, 300)), SimpleNamespace(scalars=lambda *a: [topic])
        )
    assert error.value.status_code == 502
    assert "private" not in error.value.detail

import io
import json
from urllib.error import HTTPError

import pytest
from fastapi import HTTPException
import app.modules.assistant.chat as chat
import app.integrations.gemini.client as gemini


def test_missing_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(HTTPException) as error:
        chat.generate_answer("Vảy nến là gì?", [])
    assert error.value.status_code == 503


def test_grounded_response(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-secret")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setenv("GEMINI_CHAT_MODEL", "test-model")

    def fake_open(request, timeout):
        body = json.loads(request.data)
        assert request.get_header("X-goog-api-key") == "test-secret"
        assert "test-model:generateContent" in request.full_url
        assert json.loads(body["contents"][0]["parts"][0]["text"])["sources"][0]["source"] == 1
        assert timeout == 25
        return io.BytesIO(
            json.dumps(
                {
                    "candidates": [
                        {
                            "finishReason": "STOP",
                            "content": {"parts": [{"text": "Thông tin tham khảo [1]."}]},
                        }
                    ]
                }
            ).encode()
        )

    monkeypatch.setattr(gemini, "urlopen", fake_open)
    assert (
        chat.generate_answer(
            "Vảy nến là gì?", [{"disease_name": "Vảy nến", "content": "Nội dung thư viện"}]
        )
        == "Thông tin tham khảo [1]."
    )


def test_general_conversation_without_library_evidence(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-secret")
    captured = []
    def fake_generate(instructions, parts):
        payload = json.loads(parts[0]["text"])
        captured.append(payload)
        assert "sources trống" in instructions
        assert "không thêm trích dẫn" in instructions
        return "Chào bạn! Mình có thể giúp gì hôm nay?"
    monkeypatch.setattr(chat, "generate", fake_generate)
    assert "Chào bạn" in chat.generate_answer("hihi", [], [{"role": "user", "content": "Xin chào"}])
    assert captured[0]["sources"] == []
    assert captured[0]["history"][0]["content"] == "Xin chào"


def test_quota_error_hides_provider_details(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-secret")

    def fail(*args, **kwargs):
        raise HTTPError(
            "https://generativelanguage.googleapis.com", 429, "private-details", {}, None
        )

    monkeypatch.setattr(gemini, "urlopen", fail)
    with pytest.raises(HTTPException) as error:
        chat.generate_answer("Câu hỏi", [{"disease_name": "Test", "content": "Test"}])
    assert error.value.status_code == 502
    assert "private-details" not in error.value.detail

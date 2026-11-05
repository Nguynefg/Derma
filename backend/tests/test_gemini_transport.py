import io
import json
from urllib.error import HTTPError
import pytest
from fastapi import HTTPException
import app.integrations.gemini.client as gemini


def test_bulk_options_are_explicit_and_do_not_change_defaults(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    calls = []

    def respond(request, **kwargs):
        calls.append((json.loads(request.data), kwargs))
        return io.BytesIO(
            json.dumps(
                {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "ok"}]}}]}
            ).encode()
        )

    monkeypatch.setattr(gemini, "urlopen", respond)
    gemini.generate("test", [{"text": "test"}])
    gemini.generate("test", [{"text": "test"}], timeout=90, thinking_level="low")
    assert calls[0][1]["timeout"] == 25
    assert "thinkingConfig" not in calls[0][0]["generationConfig"]
    assert calls[1][1]["timeout"] == 90
    assert calls[1][0]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "low"}


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429])
def test_nonretryable_provider_errors_preserve_status(monkeypatch, status):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    calls = []

    def fail(*args, **kwargs):
        calls.append(1)
        raise HTTPError("https://example.test", status, "error", {}, None)

    monkeypatch.setattr(gemini, "urlopen", fail)
    with pytest.raises(HTTPException) as error:
        gemini.generate("test", [{"text": "test"}])
    assert error.value.upstream_status == status
    assert len(calls) == 1


def test_retries_temporary_overload_once(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    calls = []

    def respond(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise HTTPError("https://example.test", 503, "busy", {}, None)
        return io.BytesIO(
            json.dumps(
                {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "ok"}]}}]}
            ).encode()
        )

    monkeypatch.setattr(gemini, "urlopen", respond)
    assert gemini.generate("test", [{"text": "test"}]) == "ok"
    assert len(calls) == 2


def test_overload_stops_after_two_calls(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    calls = []

    def fail(*args, **kwargs):
        calls.append(1)
        raise HTTPError("https://example.test", 503, "busy", {}, None)

    monkeypatch.setattr(gemini, "urlopen", fail)
    with pytest.raises(HTTPException) as error:
        gemini.generate("test", [{"text": "test"}])
    assert len(calls) == 2
    assert "đang bận" in error.value.detail
    assert "Gemini" not in error.value.detail


def test_timeout_retried_with_delay(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    calls, delays = [], []

    def respond(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise TimeoutError()
        return io.BytesIO(
            json.dumps(
                {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "ok"}]}}]}
            ).encode()
        )

    monkeypatch.setattr(gemini, "urlopen", respond)
    monkeypatch.setattr(gemini.time, "sleep", delays.append)
    assert gemini.generate("test", [{"text": "test"}]) == "ok"
    assert len(calls) == 2
    assert delays == [1]

"""Regression checks for local extractive chat without API credentials."""
from app.modules.assistant.chat import generate_answer


def test_local_answer_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    evidence = [{"disease_name": "Vảy nến", "content": "Đoạn trích nguyên văn."}]
    reply = generate_answer("Vảy nến là gì?", evidence)
    assert "Đoạn trích nguyên văn." in reply
    assert "[1]" in reply


def test_no_evidence_does_not_use_history_as_a_source():
    reply = generate_answer("Bệnh đó chữa thế nào?", [], [{"role": "assistant", "content": "Nội dung chưa xác minh"}])
    assert "Chưa tìm thấy" in reply
    assert "Nội dung chưa xác minh" not in reply


def test_social_reply_has_no_medical_citations():
    assert "Chào bạn" in generate_answer("hihi", [])
    assert "[1]" not in generate_answer("Cảm ơn", [])

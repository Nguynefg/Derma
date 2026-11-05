import pytest
from app.modules.assistant.knowledge import extract_symptoms, retrieve


@pytest.mark.parametrize(
    "text,presence",
    [
        ("Tôi bị ngứa", "present"),
        ("Tôi không bị ngứa", "absent"),
        ("Tôi chưa ngứa", "absent"),
        ("Tôi không biết có ngứa không", "unknown"),
        ("Con tôi bị ngứa", "unknown"),
        ("Tôi ngứa nhưng hôm nay không ngứa", "unknown"),
        ("toi bi NGUA", "present"),
    ],
)
def test_conservative_symptom_parser(text, presence):
    parsed = extract_symptoms(text)
    symptom = next(s for s in parsed["symptoms"] if s["id"] == "itch")
    assert symptom["presence"] == presence
    assert symptom["requires_confirmation"] is True


def test_negation_stops_at_clause():
    parsed = extract_symptoms("Tôi không ngứa nhưng da đỏ")
    status = {s["id"]: s["presence"] for s in parsed["symptoms"]}
    assert status == {"itch": "absent", "redness": "present"}


def test_no_substring_match():
    assert extract_symptoms("Ngựa chạy trên đường")["symptoms"] == []


def test_retrieval_requires_evidence_and_preserves_text():
    docs = [
        {
            "document_id": "eczema",
            "title": "Viêm da cơ địa",
            "disease_name": "Viêm da cơ địa",
            "content": "Viêm da cơ địa có thể gây ngứa. Tình trạng này không lây giữa người với người.",
            "symptom_ids": ["itch"],
        },
        {
            "document_id": "acne",
            "title": "Mụn trứng cá",
            "disease_name": "Mụn trứng cá",
            "content": "Mụn trứng cá xuất hiện ở mặt và lưng.",
            "symptom_ids": ["bumps"],
        },
    ]
    results = retrieve("Viêm da cơ địa có lây không?", docs)
    assert results[0]["document_id"] == "eczema"
    assert results[0]["content"] == docs[0]["content"]
    assert retrieve("du lịch sao hỏa", docs) == []

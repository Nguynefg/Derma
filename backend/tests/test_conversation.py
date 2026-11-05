"""Conversation routing checks with an isolated database and no provider requests."""
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request
from app.core.schemas import ChatInput
from app.core.security import _buckets
from app.database.models import Base, Disease, MedicalDocument, DocumentVersion
from app.modules.assistant import routes


@pytest.fixture
def conversation(monkeypatch):
    _buckets.clear()
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    captured = []
    def fake_answer(question, passages, history, image_context):
        captured.append(dict(question=question, passages=passages, history=history, image_context=image_context))
        return 'Phản hồi trò chuyện.'
    monkeypatch.setattr(routes, 'generate_answer', fake_answer)
    with Session(engine) as db:
        topic = Disease(slug='psoriasis', name='Vảy nến', english_name='Psoriasis', category='Viêm da',
                        summary='Vảy nến gây mảng da bong vảy.', details='Tình trạng viêm da.',
                        risk_factors='Di truyền.', prevention='Chăm sóc da.', aliases=[], published=True)
        db.add(topic); db.flush()
        doc = MedicalDocument(slug='psoriasis-document', disease_id=topic.id, title='Vảy nến',
                              publisher='Test source', source_url='https://example.test/source',
                              usage_note='Synthetic fixture', published=True, version=1)
        db.add(doc); db.flush()
        db.add(DocumentVersion(document_id=doc.id, version=1, title=doc.title, publisher=doc.publisher,
                               source_url=doc.source_url, usage_note=doc.usage_note,
                               content='Vảy nến là bệnh viêm da, có thể gây mảng bong vảy. Bệnh không lây.', checksum='0'*64))
        db.commit()
        yield db, captured
    engine.dispose()


def send(body, db):
    request = Request({'type': 'http', 'method': 'POST', 'path': '/api/v1/chat', 'headers': [], 'client': ('test', 1)})
    return routes.chat_question(ChatInput(**body), request, db)


def test_greeting_ignores_previous_medical_sources(conversation):
    _, captured = conversation
    result = send({'question': 'hihi', 'history': [{'role': 'user', 'content': 'Vảy nến là gì?'}]}, None)
    assert result['status'] == 'general' and result['passages'] == []
    assert result['reply'] == 'Phản hồi trò chuyện.'
    assert captured[0]['history'][0]['content'] == 'Vảy nến là gì?'


def test_general_question_after_health_does_not_attach_stale_sources(conversation):
    db, captured = conversation
    result = send({'question': 'Giải thích Python là gì?', 'history': [{'role': 'user', 'content': 'Vảy nến là gì?'}]}, db)
    assert result['method'] == 'gemini-conversation'
    assert captured[0]['passages'] == []


def test_followup_keeps_published_topic_and_citations(conversation):
    db, captured = conversation
    result = send({'question': 'Bệnh đó có lây không?', 'history': [{'role': 'user', 'content': 'Vảy nến là gì?'}]}, db)
    assert result['status'] == 'supported'
    assert captured[0]['passages']
    assert all(p['disease_name'] == 'Vảy nến' for p in result['passages'])


def test_no_evidence_still_calls_conversational_model(conversation):
    db, captured = conversation
    result = send({'question': 'Tôi đang lo về sức khỏe, bạn có thể giúp không?'}, db)
    assert result['reply'] == 'Phản hồi trò chuyện.' and len(captured) == 1


def test_unknown_image_context_cannot_fabricate_disease(conversation):
    db, captured = conversation
    result = send({'question': 'Giải thích kết quả ảnh này', 'image_context': {'disease_ids': ['999999']}}, db)
    assert result['status'] == 'insufficient_evidence' and not result['passages']
    assert not captured


def test_greeting_does_not_reuse_image_observations(conversation):
    _, captured = conversation
    send({'question': 'hi', 'image_context': {'observations': 'Gợi ý chưa xác nhận'}}, None)
    assert captured[0]['image_context'] is None


def test_short_and_long_messages_and_validation():
    assert ChatInput(question='hi').question == 'hi'
    assert len(ChatInput(question='x' * 4000).question) == 4000
    for value in ['', '  ', 'x' * 4001]:
        with pytest.raises(ValidationError):
            ChatInput(question=value)

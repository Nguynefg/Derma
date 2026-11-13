"""Regression evidence for frozen-image abstention and local source-grounded answers."""
from types import SimpleNamespace
import hashlib
import importlib.util
from pathlib import Path
import pytest
from PIL import Image
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from starlette.requests import Request
from app.database.models import Base, Disease, MedicalDocument, DocumentVersion
from app.core.schemas import QuestionInput
from app.core.security import _buckets
from app.modules.assistant.routes import retrieve_answer
from app.modules.images.image_catalog import match_model_result
from app.modules.images import image_model

spec = importlib.util.spec_from_file_location('abstention_audit', Path(__file__).resolve().parents[2] / 'research/evaluate_abstention.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


@pytest.mark.parametrize('scores', [[float('nan'), .1], [.5], [-.1, 1.1], [.2, .2], [float('inf'), 0]])
def test_invalid_model_scores_never_create_a_group_result(monkeypatch, scores):
    card = SimpleNamespace(version='test', image_type='clinical', classification_unit='group',
                           labels=[SimpleNamespace(disease_id=None), SimpleNamespace(disease_id=None)])
    monkeypatch.setattr(image_model, 'read_configuration', lambda: (card, None))
    monkeypatch.setattr(image_model, 'score_image', lambda *args: scores)
    result = image_model.analyze_with_model(Image.new('RGB', (512,512)), 'clinical', {'issues':[]}, None)
    assert result['status'] == 'model_unavailable'
    assert 'group' not in result and 'candidates' not in result


def test_unknown_acceptance_is_reported_honestly_and_policy_is_not_tuned():
    card = SimpleNamespace(labels=['a','b'], minimum_score=.8, minimum_margin=.2)
    assert audit.decision([.9,.1], card)  # even an unknown image may cross the threshold
    assert not audit.decision([.6,.4], card)
    with pytest.raises(ValueError):
        audit.decision([float('nan'), .1], card)
    images = list(audit.controls())
    before = vars(card).copy()
    report = audit.evaluate(images, card, None, scorer=lambda *args: [.9,.1])
    assert report['counts']['quality_review_required'] == 3
    assert report['counts']['accepted_unknown'] == 1
    assert report['accepted_unknown_rate'] == .25
    assert vars(card) == before


def test_group_links_exclude_hidden_non_photo_and_duplicate_topics(monkeypatch):
    topics = {1: SimpleNamespace(id=1,name='Da',published=True),
              2: SimpleNamespace(id=2,name='Ẩn',published=False),
              3: SimpleNamespace(id=3,name='Nội khoa',published=True)}
    monkeypatch.setattr('app.modules.images.image_catalog.find_record',lambda db,model,key: topics.get(key))
    monkeypatch.setattr('app.modules.images.image_catalog.supports_photo',lambda topic: topic.id == 1)
    result = match_model_result({'status':'group_result','related_articles':[
        {'disease_id':i,'name':'untrusted client name'} for i in [1,1,2,3,999]
    ]}, None)
    assert result['related_articles'] == [{'disease_id':1,'name':'Da'}]
    assert result['database_match']['status'] == 'matched'
    assert 'candidates' not in result


def test_retrieval_uses_current_published_versions_in_bounded_queries():
    _buckets.clear()
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        topic = Disease(slug='evidence',name='Bệnh kiểm thử',english_name='Example',category='Nhóm',
                        summary='Tóm tắt',details='Nội dung',risk_factors='',prevention='',aliases=[],published=True)
        db.add(topic); db.flush()
        current = 'Bệnh kiểm thử: đoạn trích nguyên văn đang xuất bản.'
        for i in range(30):
            doc=MedicalDocument(slug=f'doc-{i}',disease_id=topic.id,title='Bệnh kiểm thử',publisher='Fixture',
                                source_url='https://example.test/source',usage_note='Test',published=i!=0,version=2)
            db.add(doc); db.flush()
            for version, content in [(1,'Nội dung cũ đã thay thế'),(2,current)]:
                db.add(DocumentVersion(document_id=doc.id,version=version,title=doc.title,publisher=doc.publisher,
                                       source_url=doc.source_url,usage_note=doc.usage_note,content=content,
                                       checksum=hashlib.sha256(content.encode()).hexdigest()))
        db.commit()
        statements=[]
        def capture(*args): statements.append(args[2])
        event.listen(engine,'before_cursor_execute',capture)
        request=Request({'type':'http','method':'POST','path':'/api/v1/answers','headers':[],'client':('sprint4',1)})
        try:
            result=retrieve_answer(QuestionInput(question='Bệnh kiểm thử'),request,db)
        finally:
            event.remove(engine,'before_cursor_execute',capture)
        assert result['status']=='supported' and result['passages']
        assert all(p['content']==current and p['document_version']==2 for p in result['passages'])
        assert all(p['checksum']==hashlib.sha256(current.encode()).hexdigest() for p in result['passages'])
        assert len(statements)==2
        unknown=retrieve_answer(QuestionInput(question='du lịch sao hỏa'),request,db)
        assert unknown['status']=='insufficient_evidence' and unknown['passages']==[]

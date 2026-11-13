import io
import json
from types import SimpleNamespace
import pytest
from PIL import Image
from fastapi import HTTPException
from starlette.requests import Request
from starlette.datastructures import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database.models import Base
from app.core.schemas import ChatInput
from app.core.security import _buckets
from app.modules.images import routes as images
from app.modules.assistant import routes as chat
from app.modules.assistant import external
from app.integrations.gemini import client


def request():
    _buckets.clear()
    return Request({'type':'http','method':'POST','path':'/api/v1/test','headers':[], 'client':('fallback-test',1)})


def image_call(monkeypatch, local, allowed=False):
    monkeypatch.setattr(images,'analyze_with_model',lambda *args: dict(local))
    monkeypatch.setattr(images,'match_model_result',lambda result,db: {**result,'database_match':{'status':'inconclusive'}})
    data=io.BytesIO()
    Image.new('RGB',(512,512),(120,140,160)).save(data,format='PNG')
    data.seek(0)
    return images.analyze_image(request(),UploadFile(filename='test.png',file=data), image_type='clinical',crop=None,
                                analysis_mode='ai',save_image=False,observations=None,allow_external_ai=allowed,db=None)


@pytest.mark.parametrize('status',['quality_review_required','out_of_scope','unknown'])
def test_inconclusive_image_does_not_mean_missing_sql_article(monkeypatch,status):
    monkeypatch.setattr(images,'external_answer',lambda *args,**kwargs: pytest.fail('must not call Google'))
    result=image_call(monkeypatch,{'status':status,'message':'local'},True)
    assert result['status']==status and 'fallback' not in result


def test_missing_group_needs_consent_and_keeps_local_result_on_upstream_error(monkeypatch):
    def fail(*args,**kwargs): raise HTTPException(503,'Chưa có khóa API')
    monkeypatch.setattr(images,'external_answer',fail)
    local={'status':'group_result','message':'local','group':{'name':'Nhóm'},'related_articles':[]}
    assert image_call(monkeypatch,local)['fallback']['status']=='consent_required'
    result=image_call(monkeypatch,local,True)
    assert result['status']=='group_result' and result['fallback']['status']=='unavailable'


def test_missing_sql_link_returns_external_sources_without_fabricating_database_ids(monkeypatch):
    monkeypatch.setattr(images,'external_answer',lambda *args,**kwargs:{'status':'external_result','message':'web',
        'reply':'web','method':'gemini-web-fallback','external_sources':[{'title':'WHO','url':'https://www.who.int'}]})
    result=image_call(monkeypatch,{'status':'catalog_mismatch','message':'missing'},True)
    assert result['status']=='catalog_mismatch' and not result['stored']
    assert result['external_result']['method']=='gemini-web-fallback'
    assert result['database_match']['status']=='inconclusive'
    assert 'candidates' not in result and result['message']=='missing'


def test_chat_no_evidence_only_calls_google_after_opt_in(monkeypatch):
    engine=create_engine('sqlite://'); Base.metadata.create_all(engine)
    calls=[]
    def respond(*args):
        calls.append(args)
        return {'status':'external_result','reply':'web','passages':[],'external_sources':[]}
    monkeypatch.setattr(chat,'external_answer',respond)
    with Session(engine) as db:
        body={'question':'Tìm thông tin về bệnh chưa có trong thư viện'}
        assert chat.chat_question(ChatInput(**body),request(),db)['status']=='insufficient_evidence'
        assert not calls
        assert chat.chat_question(ChatInput(**body,allow_external_ai=True),request(),db)['status']=='external_result'
        assert len(calls)==1
        chat.chat_question(ChatInput(question='Xin chào',allow_external_ai=True),request(),db)
        assert len(calls)==1


def test_grounded_answer_without_provider_sources_is_not_presented_as_medical_evidence(monkeypatch):
    monkeypatch.setattr(external,'generate',lambda *args,**kwargs:{'reply':'Unsupported medical claim', 'external_sources':[], 'search_suggestions_html':''})
    result=external.external_answer('Tìm bệnh')
    assert result['status']=='insufficient_evidence'
    assert 'Unsupported medical claim' not in result['reply']


def test_grounding_payload_and_source_urls_come_from_metadata_not_model_text(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','test-secret')
    def respond(req,**kwargs):
        payload=json.loads(req.data)
        assert payload['tools']==[{'google_search':{}}]
        return io.BytesIO(json.dumps({'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'Answer'}]},
            'groundingMetadata':{'groundingChunks':[
                {'web':{'uri':'https://www.who.int','title':'WHO'}},
                {'web':{'uri':'javascript:alert(1)','title':'unsafe'}},
                {'web':{'uri':'https://www.who.int','title':'duplicate'}},
                {'web':{'uri':'https://name:password@example.test','title':'credential URL'}}],
            'searchEntryPoint':{'renderedContent':'<div>Google Search</div>'}}}]}).encode())
    monkeypatch.setattr(client,'urlopen',respond)
    answer=client.generate('test',[{'text':'question'}],grounding=True)
    assert answer['external_sources']==[{'title':'WHO','url':'https://www.who.int'}]
    assert answer['search_suggestions_html']=='<div>Google Search</div>'


def test_external_without_sources_preserves_local_group(monkeypatch):
    monkeypatch.setattr(images, 'external_answer', lambda *args, **kwargs: {
        'status': 'insufficient_evidence', 'reply': 'Chưa có nguồn', 'external_sources': []})
    result = image_call(monkeypatch, {'status': 'group_result', 'message': 'local',
        'group': {'name': 'Nhóm'}, 'related_articles': []}, True)
    assert result['status'] == 'group_result' and result['group']['name'] == 'Nhóm'
    assert result['message'] == 'local'
    assert result['fallback']['status'] == 'insufficient_evidence'


def test_uncertain_image_only_sends_after_consent_and_keeps_local_result(monkeypatch):
    calls = []
    def respond(question, **kwargs):
        calls.append((question, kwargs))
        return {'status': 'external_result', 'reply': 'Tham khảo web',
                'external_sources': [{'title': 'WHO', 'url': 'https://www.who.int'}]}
    monkeypatch.setattr(images, 'external_answer', respond)
    local = {'status': 'insufficient_confidence', 'message': 'Chưa đủ tin cậy'}
    first = image_call(monkeypatch, local)
    assert not calls and first['fallback']['status'] == 'consent_required'
    assert first['fallback']['reason'] == 'insufficient_confidence'
    result = image_call(monkeypatch, local, True)
    assert len(calls) == 1 and calls[0][1]['image'] is not None
    assert calls[0][1]['image_context']['local_status'] == 'insufficient_confidence'
    assert result['status'] == local['status'] and result['message'] == local['message']
    assert result['external_result']['status'] == 'external_result'
    assert result['database_match']['status'] == 'inconclusive'


def test_uncertain_image_keeps_result_when_gemini_is_unavailable(monkeypatch):
    def fail(*args, **kwargs):
        raise HTTPException(502, 'Hết hạn mức')
    monkeypatch.setattr(images, 'external_answer', fail)
    result = image_call(monkeypatch, {'status': 'insufficient_confidence', 'message': 'local'}, True)
    assert result['status'] == 'insufficient_confidence'
    assert result['fallback']['status'] == 'unavailable'
    assert result['fallback']['reason'] == 'insufficient_confidence'


def test_local_match_does_not_call_gemini_even_with_automatic_mode(monkeypatch):
    monkeypatch.setattr(images, 'external_answer', lambda *a, **k: pytest.fail('Matched article needs no fallback'))
    local = {'status': 'group_result', 'message': 'local', 'group': {'name': 'Nhóm'},
             'related_articles': [{'disease_id': '1', 'name': 'Bài đọc'}]}
    result = image_call(monkeypatch, local, True)
    assert result['related_articles'] == local['related_articles'] and 'fallback' not in result


def observation_json(in_scope=True):
    return json.dumps({'image_in_scope': in_scope, 'observations': 'Vùng ảnh có màu đỏ.',
                       'limitations': 'Ảnh không đủ để xác định bệnh.',
                       'next_steps': 'Khám nếu triệu chứng kéo dài.', 'search_query': 'skin redness'}, ensure_ascii=False)


def test_image_observation_survives_search_quota_error(monkeypatch):
    calls = []
    def respond(instructions, parts, **kwargs):
        calls.append((parts, kwargs))
        if not kwargs['grounding']:
            assert kwargs['image'] and 'inlineData' in parts[1]
            return observation_json()
        assert not kwargs['image'] and all('inlineData' not in part for part in parts)
        failure = HTTPException(502, 'Google chặn tìm kiếm')
        failure.upstream_status = 429
        raise failure
    monkeypatch.setattr(external, 'generate', respond)
    result = external.external_answer('Xem ảnh', image=Image.new('RGB', (300, 300)))
    assert len(calls) == 2
    assert result['status'] == 'external_observation'
    assert 'Vùng ảnh có màu đỏ.' in result['reply']
    assert result['evidence_status'] == 'unverified' and not result['external_sources']
    assert result['source_lookup']['upstream_status'] == 429


def test_non_skin_observation_does_not_search(monkeypatch):
    calls = []
    def respond(*args, **kwargs):
        calls.append(kwargs)
        return observation_json(False)
    monkeypatch.setattr(external, 'generate', respond)
    result = external.external_answer('Xem ảnh', image=Image.new('RGB', (300, 300)))
    assert len(calls) == 1 and result['source_lookup']['status'] == 'not_applicable'
    assert result['evidence_status'] == 'unverified'


def test_search_sources_do_not_turn_image_observation_into_confirmed_diagnosis(monkeypatch):
    def respond(*args, **kwargs):
        if not kwargs['grounding']:
            return observation_json()
        return {'reply': 'Thông tin nguồn', 'external_sources': [{'title': 'WHO', 'url': 'https://www.who.int'}]}
    monkeypatch.setattr(external, 'generate', respond)
    result = external.external_answer('Xem ảnh', image=Image.new('RGB', (300, 300)))
    assert result['evidence_status'] == 'related_sources'
    assert result['source_reply'] == 'Thông tin nguồn'
    assert 'Ảnh không đủ để xác định bệnh.' in result['reply']


def test_malformed_image_observation_is_not_displayed(monkeypatch):
    monkeypatch.setattr(external, 'generate', lambda *a, **k: 'invalid-json')
    with pytest.raises(HTTPException) as caught:
        external.external_answer('Xem ảnh', image=Image.new('RGB', (300, 300)))
    assert caught.value.status_code == 502


def test_image_route_accepts_unverified_observation_without_replacing_local_result(monkeypatch):
    monkeypatch.setattr(images, 'external_answer', lambda *a, **k: {
        'status': 'external_observation', 'reply': 'Nhận xét chưa có nguồn',
        'evidence_status': 'unverified', 'external_sources': []})
    result = image_call(monkeypatch, {'status': 'insufficient_confidence', 'message': 'local'}, True)
    assert result['status'] == 'insufficient_confidence'
    assert result['external_result']['status'] == 'external_observation'
    assert result['fallback']['status'] == 'used'

import importlib.util
import json
from pathlib import Path
import sys
import pytest
from sqlalchemy import create_engine,select,event
from sqlalchemy.orm import Session
from app.database.models import Base,Disease,User,Bookmark,Symptom,DiseaseSymptom,ImageRecord,Reference,MedicalDocument,DocumentVersion

SCRIPTS=Path(__file__).resolve().parents[2]/'scripts/maintenance'
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('fix_remaining',SCRIPTS/'fix_remaining_library.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def setup():
    engine=create_engine('sqlite://')
    @event.listens_for(engine,'connect')
    def fk(c,_):c.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user=User(email='test@example.test',name='Test',password_hash='hash');db.add(user)
        keeper=Disease(slug='kept',name='Bệnh thử',english_name='Example disease',category='Bệnh',summary='Bài gốc đã viết',details='Nội dung tổng quan đang được bổ sung.',risk_factors='Giữ nguyên',prevention='Giữ nguyên',aliases=['test'],published=True)
        source=Disease(slug='source-row',name='Bệnh thử',english_name='Example disease',category='Bệnh',summary='Bản nhập',details='Chi tiết có nguồn',risk_factors='',prevention='',aliases=['article-columns:v1','chapter:05','kind:category','CODE-TEST'],published=False,review_status='icd_classification')
        reserved=Disease(slug='reserved',name='Mã khẩn cấp quốc tế 05',english_name='International emergency code 05',category='Khẩn cấp',summary='',details='',risk_factors='',prevention='',aliases=['chapter:25','kind:category'],published=False,review_status='icd_classification')
        db.add_all([keeper,source,reserved]);db.flush()
        symptom=Symptom(name='Dấu hiệu');db.add(symptom);db.flush()
        for row in [keeper,source]:
            db.add(Bookmark(user_id=user.id,disease_id=row.id));db.add(DiseaseSymptom(disease_id=row.id,symptom_id=symptom.id))
        image=ImageRecord(user_id=user.id,disease_id=source.id,pixel_sha256='a'*64,image_type='clinical',width=224,height=224,is_reference=True);db.add(image)
        db.add(Reference(disease_id=source.id,title='Source',publisher='Source',url='https://example.test',accessed_at='2026-10-21',usage_note='Test'))
        data={'title':'Example disease','class_kind':'category','chapter_no':'05','code':'CODE-TEST','linearization_uri':'https://example.test/1','browser_url':'https://example.test/source','parent_uri':None}
        doc=MedicalDocument(slug=f'library-source-{source.id}',disease_id=source.id,title='Source',publisher='Source',source_url='https://example.test',usage_note='original');db.add(doc);db.flush()
        db.add(DocumentVersion(document_id=doc.id,version=1,title='Source',publisher='Source',source_url='https://example.test',usage_note='original',content=json.dumps({'source':data}),checksum='a'*64))
        db.commit();keep,old,code,img=keeper.id,source.id,reserved.id,image.id
    with engine.connect() as c:snapshot={r['disease_id']:dict(r) for r in c.execute(select(Disease.__table__)).mappings()}
    return engine,snapshot,keep,old,code,img

def test_atomic_cleanup_preserves_content_relations_provenance_and_old_links(tmp_path):
    from app.modules.library.identifiers import find_record
    from app.modules.library.icd_links import article_icd_links
    from app.modules.library.library_source import source_data
    from app.modules.library.icd_routes import detail
    from app.modules.library.routes import combined_library
    engine,snapshot,keep,old,code,img=setup()
    pairs=[{'keep':keep,'remove':old,'exact_source_title':'example disease'}]
    result=module.apply_cleanup(engine,snapshot,[code],pairs,tmp_path/'apply',True)
    assert result['remaining_records']==1 and result['status']=='applied' and Path(result['backup']).exists()
    with Session(engine) as db:
        row=db.get(Disease,keep)
        assert row.summary=='Bài gốc đã viết' and row.details=='Chi tiết có nguồn'
        assert db.get(ImageRecord,img).disease_id==keep and db.get(ImageRecord,img).is_reference
        assert len(list(db.scalars(select(Bookmark.disease_id))))==1
        assert len(list(db.scalars(select(DiseaseSymptom.disease_id))))==1
        assert db.scalar(select(Reference.disease_id))==keep
        assert source_data(row)['code']=='CODE-TEST'
        assert find_record(db,Disease,str(old)).id==keep
        assert find_record(db,Disease,'source-row').id==keep
        assert article_icd_links(db)[keep]['id']==old
        assert detail(old,db)['article_content']['summary']==row.summary
        docs=list(db.scalars(select(MedicalDocument)))
        archived=next(d for d in docs if d.slug==f'merged-record-{old}')
        body=db.scalar(select(DocumentVersion.content).where(DocumentVersion.document_id==archived.id))
        assert json.loads(body)['summary']=='Bản nhập'
        response=combined_library(q='CODE-TEST',content_type='all',specialty='',category='',symptom='',chapter='',sort='name',page=1,page_size=12,db=db)
        assert response['total']==1 and response['items'][0]['id']==keep
    assert module.apply_cleanup(engine,snapshot,[code],pairs,tmp_path/'repeat',True)['status']=='already_applied'

def test_changed_live_content_aborts_whole_cleanup(tmp_path):
    engine,snapshot,keep,old,code,img=setup()
    with Session(engine) as db,db.begin():db.get(Disease,keep).summary='New admin edit'
    with pytest.raises(ValueError,match='Conflicts'):
        module.apply_cleanup(engine,snapshot,[code],[{'keep':keep,'remove':old,'exact_source_title':'example disease'}],tmp_path/'conflict',True)
    with Session(engine) as db:
        assert db.get(Disease,old) and db.get(Disease,code)
        assert db.get(Disease,keep).summary=='New admin edit'

def test_backup_failure_aborts_before_changes(tmp_path,monkeypatch):
    engine,snapshot,keep,old,code,img=setup()
    def fail(*a,**k):raise OSError('Disk unavailable')
    monkeypatch.setattr(module.gzip,'open',fail)
    with pytest.raises(OSError,match='Disk unavailable'):
        module.apply_cleanup(engine,snapshot,[code],[{'keep':keep,'remove':old,'exact_source_title':'example disease'}],tmp_path/'fail',True)
    with Session(engine) as db:assert db.get(Disease,old) and db.get(Disease,code)

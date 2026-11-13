import importlib.util
import gzip
import json
from pathlib import Path
import pytest
from sqlalchemy import create_engine, select, event
from sqlalchemy.orm import Session
from app.database.models import Base, Disease, User, ImageRecord, Bookmark, DiseaseSymptom, Symptom, Reference, MedicalDocument, DocumentVersion

spec=importlib.util.spec_from_file_location('delete_reviewed',Path(__file__).resolve().parents[2]/'scripts/maintenance/delete_non_disease_entries.py')
if not Path(spec.origin).is_file():
    pytest.skip('Retired non-disease deletion script is not installed.', allow_module_level=True)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def fixture():
    engine=create_engine('sqlite://')
    @event.listens_for(engine,'connect')
    def foreign_keys(c,_):c.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user=User(email='test@example.test',name='Test',password_hash='hash');db.add(user)
        target=Disease(slug='reviewed-substance',name='Substance',english_name='Substance',category='Chất',summary='summary',details='details',risk_factors='',prevention='',aliases=['chapter:X','kind:category'],review_status='icd_classification')
        keep=Disease(slug='keep-disease',name='Bệnh giữ lại',english_name='Disease',category='Bệnh',summary='Keep content',details='Keep details',risk_factors='',prevention='',aliases=[])
        db.add_all([target,keep]);db.flush()
        symptom=Symptom(name='Ngứa');db.add(symptom);db.flush()
        db.add_all([Bookmark(user_id=user.id,disease_id=target.id),DiseaseSymptom(disease_id=target.id,symptom_id=symptom.id),Reference(disease_id=target.id,title='Source',publisher='Source',url='https://example.test',accessed_at='2026-10-21',usage_note='Test')])
        image=ImageRecord(user_id=user.id,disease_id=target.id,pixel_sha256='a'*64,image_type='clinical',width=224,height=224,is_reference=True);db.add(image)
        doc=MedicalDocument(disease_id=target.id,title='Source',publisher='Source',source_url='https://example.test',usage_note='Test');db.add(doc);db.flush()
        db.add(DocumentVersion(document_id=doc.id,version=1,title='Source',publisher='Source',source_url='https://example.test',usage_note='Test',content='Original document',checksum='a'*64))
        db.commit();rid=target.id;kid=keep.id;image_id=image.id
    targets={rid:{'slug':'reviewed-substance','name':'Substance','source_title':'Substance','source_chapter':'X','source_kind':'category'}}
    return engine,targets,kid,image_id

def test_backup_delete_keeps_other_ids_and_images(tmp_path):
    engine,targets,kid,image_id=fixture()
    preview=module.prune(engine,targets,tmp_path/'preview')
    assert preview['found_records']==1
    with Session(engine) as db:assert db.get(Disease,next(iter(targets))) is not None
    result=module.prune(engine,targets,tmp_path/'apply',True)
    assert result['deleted_records']==1 and result['remaining_records']==1
    with gzip.open(result['backup'],'rt',encoding='utf-8') as file:backup=[json.loads(line) for line in file]
    assert {r['table'] for r in backup[1:]}=={t.name for t in module.TABLES}
    assert any(r.get('row',{}).get('content')=='Original document' for r in backup)
    with Session(engine) as db:
        assert list(db.scalars(select(Disease.id)))==[kid]
        assert db.get(Disease,kid).summary=='Keep content'
        image=db.get(ImageRecord,image_id)
        assert image.disease_id is None and not image.is_reference
        assert db.scalar(select(User.id)) and db.scalar(select(Symptom.id))
    assert module.prune(engine,targets,tmp_path/'repeat',True)['status']=='already_absent'

def test_conflict_refuses_entire_deletion(tmp_path):
    engine,targets,kid,image_id=fixture()
    targets[next(iter(targets))]['slug']='wrong-slug'
    with pytest.raises(ValueError,match='conflicts'):module.prune(engine,targets,tmp_path/'conflict',True)
    with Session(engine) as db:
        assert db.get(Disease,next(iter(targets))) is not None
        assert db.get(ImageRecord,image_id).disease_id==next(iter(targets))

def test_backup_failure_never_mutates_database(tmp_path,monkeypatch):
    engine,targets,kid,image_id=fixture()
    def fail(*args,**kwargs):raise OSError('Disk unavailable')
    monkeypatch.setattr(module.gzip,'open',fail)
    with pytest.raises(OSError,match='Disk unavailable'):module.prune(engine,targets,tmp_path/'fail',True)
    with Session(engine) as db:
        assert db.get(Disease,next(iter(targets))) is not None
        assert db.get(ImageRecord,image_id).is_reference

def test_only_exact_reviewed_renames_are_accepted():
    for (rid,slug),(old,new) in module.REVIEWED_RENAMES.items():
        expected={'slug':slug,'name':old,'source_title':old,'source_chapter':'X','source_kind':'category'}
        assert new in module.allowed_names(rid,expected)
        assert new not in module.allowed_names(rid+1,expected)
        assert new not in module.allowed_names(rid,{**expected,'slug':'different-slug'})
        assert new not in module.allowed_names(rid,{**expected,'source_chapter':'14'})

def test_other_renames_remain_blocked(tmp_path):
    engine,targets,kid,image_id=fixture()
    with Session(engine) as db,db.begin():db.get(Disease,next(iter(targets))).name='Unreviewed name'
    with pytest.raises(ValueError,match='conflicts'):
        module.prune(engine,targets,tmp_path/'unreviewed-name',True)
    report=json.loads((tmp_path/'unreviewed-name/delete-result.json').read_text(encoding='utf-8'))
    assert report['conflicts'][0]['fields']==['name']
    with Session(engine) as db:assert db.get(Disease,next(iter(targets))) is not None

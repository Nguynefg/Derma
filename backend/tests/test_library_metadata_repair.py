import importlib.util
import json
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.database.models import Base, Disease

spec=importlib.util.spec_from_file_location('metadata_repair',Path(__file__).resolve().parents[2]/'scripts/maintenance/repair_library_metadata.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def test_repair_backs_up_and_preserves_content_and_is_idempotent(tmp_path):
    engine=create_engine('sqlite:///'+(tmp_path/'test.sqlite').as_posix())
    Base.metadata.create_all(engine)
    with Session(engine) as db,db.begin():
        row=Disease(slug='level-zero',name='0 Không có vấn đề',english_name='0 No problem',category='Giá trị thang đo vấn đề',summary='Nội dung đã viết',details='Chi tiết đã viết',risk_factors='Giữ nguyên',prevention='Giữ nguyên',aliases=['article-columns:v1','vi:0 Không có vấn đề'],published=False,review_status='icd_classification',version=3)
        db.add(row);db.flush();rid=row.id
    source={rid:{'fields':{'slug':'level-zero','name':'0 Không có vấn đề','category':'Giá trị thang đo vấn đề'},'source_title':'0 No problem'}}
    result=module.repair(engine,source,tmp_path/'first')
    assert result['updated_records']==1 and Path(result['backup']).exists()
    with Session(engine) as db:
        row=db.get(Disease,rid)
        assert row.name=='Không có vấn đề (mức 0)' and row.category=='Mức độ vấn đề'
        assert row.summary=='Nội dung đã viết' and row.version==4
        assert row.published is False and row.review_status=='icd_classification'
        assert 'vi:Không có vấn đề (mức 0)' in row.aliases
    assert module.repair(engine,source,tmp_path/'repeat')['updated_records']==0

def test_repair_keeps_manual_live_changes(tmp_path):
    engine=create_engine('sqlite:///'+(tmp_path/'conflict.sqlite').as_posix())
    Base.metadata.create_all(engine)
    with Session(engine) as db,db.begin():
        row=Disease(slug='level-zero',name='Tên do người quản trị sửa',english_name='0 No problem',category='Giá trị thang đo vấn đề',summary='summary',details='details',risk_factors='',prevention='',aliases=[],review_status='icd_classification')
        db.add(row);db.flush();rid=row.id
    source={rid:{'fields':{'slug':'level-zero','name':'0 Không có vấn đề','category':'Giá trị thang đo vấn đề'},'source_title':'0 No problem'}}
    import pytest
    with pytest.raises(ValueError,match='Live edits'):
        module.repair(engine,source,tmp_path/'conflict')
    with Session(engine) as db:
        assert db.get(Disease,rid).name=='Tên do người quản trị sửa'

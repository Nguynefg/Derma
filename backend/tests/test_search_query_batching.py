import json
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from app.database.models import Base, Disease, Symptom, DiseaseSymptom, Reference, MedicalDocument, DocumentVersion
from app.modules.library.catalog import preload_disease_relations, serialize_disease
from app.modules.library.library_source import preload_sources, source_data


def test_serialization_batch_reduces_queries_without_changing_results():
    engine=create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        symptom=Symptom(slug='itch',name='Ngứa');db.add(symptom);db.flush()
        for i in range(12):
            row=Disease(slug=f'row-{i}',name=f'Bệnh {i}',english_name='Example',category='Da liễu',summary='Tóm tắt',details='Chi tiết',risk_factors='',prevention='',aliases=[])
            db.add(row);db.flush()
            db.add(DiseaseSymptom(disease_id=row.id,symptom_id=symptom.id))
            db.add(Reference(disease_id=row.id,title='Source',publisher='Publisher',url='https://example.test',accessed_at='2026-10-19',usage_note='test'))
        db.commit()
        rows=list(db.scalars(select(Disease).order_by(Disease.id)))
        queries=[]
        def count(*args):queries.append(args[2])
        event.listen(engine,'before_cursor_execute',count)
        expected=[serialize_disease(r,db,{}) for r in rows]
        assert len(queries)==24
        queries.clear()
        preload_disease_relations(db,rows)
        actual=[serialize_disease(r,db,{}) for r in rows]
        assert len(queries)==2
        assert actual==expected
        event.remove(engine,'before_cursor_execute',count)


def test_search_preserves_merged_results_counts_and_empty_search():
    from app.modules.library.routes import combined_library
    engine=create_engine('sqlite://');Base.metadata.create_all(engine)
    with Session(engine) as db:
        article=Disease(slug='authored',name='Đái tháo đường',english_name='Type 2 diabetes mellitus',category='Nội tiết',summary='Diabetes',details='Thông tin',risk_factors='',prevention='',aliases=['dai thao duong'],published=True)
        db.add(article)
        for i,title in enumerate(['Type 2 diabetes mellitus','Other diabetes']):
            source={'title':title,'chapter_no':'05','class_kind':'category','linearization_uri':f'https://example.test/{i}','browser_url':'https://example.test','code':str(i),'parent_uri':None}
            db.add(Disease(slug=f'import-{i}',name=title,english_name=title,category='ICD-11 05',summary=title,details=json.dumps(source),risk_factors='',prevention='',aliases=[],published=False,review_status='icd_classification'))
        db.commit()
        def search(q):
            return combined_library(q=q,content_type='all',specialty='',category='',symptom='',chapter='',sort='name',page=1,page_size=12,db=db)
        value=search('diabetes')
        assert value['total']==2 and value['article_count']==1 and value['icd_count']==1
        assert {r['type'] for r in value['items']}=={'article','icd'}
        empty=search('does-not-exist')
        assert empty['total']==0 and empty['article_count']==0 and empty['items']==[]


def test_search_accented_unaccented_and_literal_wildcards():
    from app.modules.library.routes import combined_library
    engine=create_engine('sqlite://');Base.metadata.create_all(engine)
    with Session(engine) as db:
        for i,name in enumerate(['Viêm da','100% example','100x example']):
            source={'title':name,'chapter_no':'14','class_kind':'category','linearization_uri':f'https://example.test/{i}','browser_url':'https://example.test','code':str(i),'parent_uri':None}
            db.add(Disease(slug=f'keyword-{i}',name=name,english_name=name,category='ICD-11 14',summary=name,details=json.dumps(source),risk_factors='',prevention='',aliases=['viem da'] if i==0 else [],published=False,review_status='icd_classification'))
        db.commit()
        def search(q):
            return combined_library(q=q,content_type='all',specialty='',category='',symptom='',chapter='',sort='name',page=1,page_size=12,db=db)
        assert search('viêm')['total']==search('viem')['total']==1
        assert search('viêm')['items'][0]['id']==search('viem')['items'][0]['id']
        literal=search('100%')
        assert literal['total']==1 and literal['items'][0]['title']=='100% example'


def test_converted_sources_are_loaded_in_one_query_per_page():
    engine=create_engine('sqlite://');Base.metadata.create_all(engine)
    with Session(engine) as db:
        for i in range(12):
            row=Disease(slug=f'converted-{i}',name='Tên',english_name='Name',category='Nhóm',summary='Summary',details='Nội dung',risk_factors='',prevention='',aliases=['article-columns:v1'])
            db.add(row);db.flush()
            doc=MedicalDocument(slug=f'library-source-{row.id}',disease_id=row.id,title='Name',publisher='Source',source_url='https://example.test',usage_note='source')
            db.add(doc);db.flush()
            db.add(DocumentVersion(document_id=doc.id,version=1,title='Name',publisher='Source',source_url='https://example.test',usage_note='source',content=json.dumps({'source':{'title':f'Name {i}'}}),checksum='a'*64))
        db.commit()
        rows=list(db.scalars(select(Disease).order_by(Disease.id)))
        queries=[]
        def count(*args):queries.append(args[2])
        event.listen(engine,'before_cursor_execute',count)
        preload_sources(db,rows)
        assert [source_data(r)['title'] for r in rows]==[f'Name {i}' for i in range(12)]
        assert len(queries)==1
        event.remove(engine,'before_cursor_execute',count)

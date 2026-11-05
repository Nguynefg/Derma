"""Backed-up cleanup: reserved codes and exact source-title duplicates only."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
import argparse
import gzip
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from sqlalchemy import select, update, delete, inspect

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from app.database.models import Disease,MedicalDocument,DocumentVersion,Bookmark,DiseaseSymptom,Reference,ImageRecord,LibraryUpdate,now
from scripts.maintenance.delete_non_disease_entries import TABLES,batches

SNAPSHOT=ROOT/'storage/exports/database-word/20261020T235915095684Z/tbldiseases.jsonl'
EMPTY={'','Thông tin tóm tắt đang được bổ sung.','Nội dung tổng quan đang được bổ sung.','Chưa bổ sung thông tin về yếu tố liên quan.','Chưa bổ sung thông tin về phòng ngừa và chăm sóc.'}
CLINICAL=['summary','details','risk_factors','prevention']
MARKER='remaining-library-exact-cleanup-20261021-v1'

def exact(value):return re.sub(r'\s+',' ',value.casefold()).strip()

def make_plan():
    snapshot={r['disease_id']:r for r in map(json.loads,SNAPSHOT.open(encoding='utf-8'))}
    metadata={r['fields']['slug']:r for r in map(json.loads,(ROOT/'storage/temporary/word-content-20261019/records.jsonl').open(encoding='utf-8'))}
    by_name=defaultdict(list);reserved=[]
    for rid,row in snapshot.items():
        source=metadata.get(row['slug'])
        title=source['source_title'] if source else row['english_name']
        by_name[exact(title)].append(rid)
        if source and source['chapter']=='25' and re.match(r'^(International|National) emergency code\b',title,re.I):reserved.append(rid)
    merges=[]
    for title,ids in by_name.items():
        if len(ids)!=2:continue
        authored=[i for i in ids if snapshot[i]['published'] and snapshot[i]['review_status']!='icd_classification']
        imported=[i for i in ids if snapshot[i]['review_status']=='icd_classification' and metadata.get(snapshot[i]['slug'],{}).get('kind')=='category']
        if len(authored)==len(imported)==1:
            merges.append({'keep':authored[0],'remove':imported[0],'exact_source_title':title})
    assert len(snapshot)==15519 and len(reserved)==13 and len(merges)==67
    assert not set(reserved)&{m['remove'] for m in merges}
    return snapshot,reserved,merges

def apply_cleanup(engine,snapshot,reserved,merges,output,apply=False):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    with engine.connect().execution_options(isolation_level='SERIALIZABLE') as c,c.begin():
        known={t.name for t in TABLES}
        inspector=inspect(c)
        for table in inspector.get_table_names():
            for fk in inspector.get_foreign_keys(table):
                if fk['referred_table'] in {'tbldiseases','tblmedical_documents'} and table not in known:raise ValueError('Unexpected related table '+table)
        before=set(c.scalars(select(Disease.id)))
        affected=set(reserved)|{i for m in merges for i in [m['keep'],m['remove']]}
        rows={}
        for batch in batches(affected):
            q=select(Disease.__table__).where(Disease.id.in_(batch))
            if c.dialect.name=='mssql':q=q.with_hint(Disease.__table__,'WITH (UPDLOCK, HOLDLOCK)',dialect_name='mssql')
            rows.update({r['disease_id']:dict(r) for r in c.execute(q).mappings()})
        check_fields=['slug','name','english_name','published','review_status','version','category','aliases',*CLINICAL]
        conflicts=[];pending=[]
        for m in merges:
            if m['remove'] not in rows:
                if m['keep'] not in rows or f"merged-id:{m['remove']}" not in rows[m['keep']]['aliases']:
                    conflicts.append({'id':m['remove'],'reason':'Missing source without retained merge marker'})
                continue
            pending.append(m)
        live_reserved=[i for i in reserved if i in rows]
        live_affected=set(live_reserved)|{i for m in pending for i in [m['keep'],m['remove']]}
        for rid in live_affected:
            if rid not in rows:conflicts.append({'id':rid,'reason':'Missing keeper'});continue
            differing=[key for key in check_fields if rows[rid][key]!=snapshot[rid][key]]
            if differing:conflicts.append({'id':rid,'fields':differing,'reason':'Live data changed after export'})
        report={'status':'preview','reserved_codes_to_delete':len(live_reserved),'duplicate_pairs_to_merge':len(pending),'before_records':len(before),'expected_remaining':len(before)-len(live_reserved)-len(pending),'conflicts':conflicts}
        target=output/'fix-result.json';target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        if conflicts:raise ValueError('Conflicts found. Nothing changed. See '+str(target))
        if not apply:return report
        if not live_affected:
            report['status']='already_applied';target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');return report
        doc_ids=[]
        for batch in batches(live_affected):doc_ids.extend(c.scalars(select(MedicalDocument.id).where(MedicalDocument.disease_id.in_(batch))))
        backup=output/'before-fix.jsonl.gz';counts={}
        with gzip.open(backup,'xt',encoding='utf-8') as file:
            file.write(json.dumps({'manifest':{'merges':pending,'reserved':live_reserved,'created_at':now().isoformat()}},ensure_ascii=False)+'\n')
            for table in TABLES:
                key=table.c.document_id if table.name=='tbldocument_versions' else table.c.disease_id
                ids=doc_ids if table.name=='tbldocument_versions' else live_affected
                count=0
                for batch in batches(ids):
                    for row in c.execute(select(table).where(key.in_(batch))).mappings():
                        file.write(json.dumps({'table':table.name,'row':dict(row)},ensure_ascii=False,default=str)+'\n');count+=1
                counts[table.name]=count
        verified=defaultdict(int)
        with gzip.open(backup,'rt',encoding='utf-8') as file:
            next(file)
            for line in file:verified[json.loads(line)['table']]+=1
        if any(verified[k]!=v for k,v in counts.items()):raise ValueError('Backup readback mismatch')
        with backup.open('r+b') as file:os.fsync(file.fileno())
        for m in pending:
            old,new=m['remove'],m['keep'];source=rows[old];keeper=rows[new]
            # Keep every source row's full contents in the existing document tables.
            content=json.dumps(source,ensure_ascii=False,default=str)
            document={'slug':f'merged-record-{old}','disease_id':new,'title':('Bản ghi trước khi gộp '+source['name'])[:200],'publisher':'Thư viện Derma','source_url':'','usage_note':'merged_original_record','published':False,'version':1,'updated_at':now()}
            doc_id=c.execute(MedicalDocument.__table__.insert(),document).inserted_primary_key[0]
            c.execute(DocumentVersion.__table__.insert(),{'document_id':doc_id,'version':1,'title':document['title'],'publisher':document['publisher'],'source_url':'','usage_note':document['usage_note'],'content':content,'checksum':hashlib.sha256(content.encode()).hexdigest(),'editor_id':None,'created_at':now()})
            for model,column in [(Bookmark,Bookmark.user_id),(DiseaseSymptom,DiseaseSymptom.symptom_id)]:
                values=list(c.scalars(select(column).where(model.disease_id==old)))
                existing=set(c.scalars(select(column).where(model.disease_id==new)))
                c.execute(delete(model).where(model.disease_id==old))
                for value in values:
                    if value not in existing:c.execute(model.__table__.insert(),{'disease_id':new,column.key:value})
            # Preserve source documents and versions, but avoid letting an old
            # editorial overlay override the retained authored article.
            editorial_docs=c.execute(select(MedicalDocument.id).where(MedicalDocument.disease_id==old,MedicalDocument.slug.startswith('library-editorial-'))).scalars().all()
            for did in editorial_docs:c.execute(update(MedicalDocument).where(MedicalDocument.id==did).values(slug=f'merged-editorial-{old}-{did}'))
            c.execute(update(MedicalDocument).where(MedicalDocument.disease_id==old,MedicalDocument.slug==f'library-source-{old}').values(slug=f'library-source-{new}'))
            for model in [MedicalDocument,Reference,ImageRecord]:c.execute(update(model).where(model.disease_id==old).values(disease_id=new))
            aliases=list(dict.fromkeys([*keeper['aliases'],*(a for a in source['aliases'] if not a.startswith('vi:') and a!='article-columns:v1'),f'merged-id:{old}',f"merged-slug:{source['slug']}"]))
            updates={'aliases':aliases,'version':keeper['version']+1,'updated_at':now()}
            for field in CLINICAL:
                if keeper[field].strip() in EMPTY and source[field].strip() not in EMPTY:updates[field]=source[field]
            c.execute(update(Disease).where(Disease.id==new).values(**updates))
            c.execute(delete(Disease).where(Disease.id==old))
        # Remove the thirteen reserved code entries using explicit FK-safe steps.
        removed_docs=[]
        for batch in batches(live_reserved):
            removed_docs.extend(c.scalars(select(MedicalDocument.id).where(MedicalDocument.disease_id.in_(batch))))
            c.execute(update(ImageRecord).where(ImageRecord.disease_id.in_(batch)).values(disease_id=None,is_reference=False))
        for batch in batches(removed_docs):c.execute(delete(DocumentVersion).where(DocumentVersion.document_id.in_(batch)))
        for model in [MedicalDocument,Reference,Bookmark,DiseaseSymptom,Disease]:
            key=model.id if model is Disease else model.disease_id
            for batch in batches(live_reserved):c.execute(delete(model).where(key.in_(batch)))
        after=set(c.scalars(select(Disease.id)))
        if after!=before-set(live_reserved)-{m['remove'] for m in pending}:raise ValueError('Unexpected retained IDs; transaction rolled back')
        if not c.scalar(select(LibraryUpdate.id).where(LibraryUpdate.id==MARKER)):
            c.execute(LibraryUpdate.__table__.insert(),{'update_id':MARKER,'applied_at':now()})
        report.update(status='applied',remaining_records=len(after),backup=str(backup),backed_up_rows=counts,retained_ids_verified=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');parser.add_argument('--plan-only',action='store_true');args=parser.parse_args()
    snapshot,reserved,merges=make_plan()
    output=ROOT/'storage/temporary/fix-remaining-library-20261021';output.mkdir(parents=True,exist_ok=True)
    (output/'plan.json').write_text(json.dumps({'snapshot':str(SNAPSHOT),'reserved_ids':reserved,'merges':merges},ensure_ascii=False,indent=2),encoding='utf-8')
    if args.plan_only:print(json.dumps({'reserved_codes':len(reserved),'duplicate_pairs':len(merges),'expected_remaining':len(snapshot)-len(reserved)-len(merges)}));return
    from app.database.connection import engine
    try:print(json.dumps(apply_cleanup(engine,snapshot,reserved,merges,output/now().strftime('%Y%m%dT%H%M%S%fZ'),args.apply),ensure_ascii=True))
    except Exception as error:print(json.dumps({'status':'not_completed','reason':str(error)},ensure_ascii=True));raise SystemExit(1)
    finally:engine.dispose()

if __name__=='__main__':main()

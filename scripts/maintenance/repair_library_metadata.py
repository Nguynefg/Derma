"""Apply source-bounded terminology corrections, preserving clinical content and IDs."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
import argparse
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.models import Disease, now
from app.modules.library.icd_terminology import medical_title
from app.modules.library.library_groups import group_title
from app.modules.library.catalog import normalize
from app.modules.library.library_editorial import editorials

def proposed(record):
    before=record['fields']
    after={}
    title=medical_title(record['source_title'],before['name'])
    if title != before['name']:
        after['name']=title[:120]
    category=group_title(before['category'])
    if category != before['category']:
        after['category']=category
    return after

def repair(engine, records, output):
    output.mkdir(parents=True,exist_ok=True)
    with Session(engine) as db, db.begin():
        query=select(Disease).where(Disease.review_status=='icd_classification')
        if engine.dialect.name=='mssql':
            query=query.with_hint(Disease,'WITH (UPDLOCK, HOLDLOCK)',dialect_name='mssql')
        rows=list(db.scalars(query))
        edited=editorials(db,[r.id for r in rows])
        pending=[]; conflicts=[]
        for row in rows:
            source=records.get(row.id)
            if not source or row.id in edited:
                continue
            changes=proposed(source)
            if not changes:
                continue
            before=source['fields']
            if row.slug != before['slug'] or any(getattr(row,k) not in (before[k],v) for k,v in changes.items()):
                conflicts.append(row.id)
                continue
            changes={k:v for k,v in changes.items() if getattr(row,k)!=v}
            if changes:pending.append((row,changes))
        report={'updated_records':len(pending),'conflicts':conflicts}
        (output/'repair-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        if conflicts:
            raise ValueError('Live edits detected; nothing written. See repair-result.json')
        backup=output/'before-repair.json.gz'
        with gzip.open(backup,'wt',encoding='utf-8') as file:
            json.dump([{c.name:getattr(row,'id' if c.name=='disease_id' else c.name) for c in Disease.__table__.columns} for row,changes in pending],file,ensure_ascii=False,default=str)
        for row,changes in pending:
            for key,value in changes.items():setattr(row,key,value)
            if 'name' in changes:
                row.aliases=list(dict.fromkeys([*(a for a in row.aliases if not a.startswith('vi:')),'vi:'+row.name,normalize(row.name)]))
            row.version+=1;row.updated_at=now()
        db.flush()
        for row,changes in pending:
            db.refresh(row)
            if any(getattr(row,k)!=v for k,v in changes.items()):
                raise ValueError('Database readback differs; rolling back')
        report.update(status='applied',backup=str(backup))
    (output/'repair-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    records={int(r['fields']['disease_id']):r for r in map(json.loads,(ROOT/'storage/temporary/word-content-20261019/records.jsonl').open(encoding='utf-8'))}
    changes=[{'id':i,'before':{k:r['fields'][k] for k in proposed(r)},'after':proposed(r)} for i,r in records.items() if proposed(r)]
    output=ROOT/'storage/temporary/library-quality';output.mkdir(parents=True,exist_ok=True)
    (output/'metadata-corrections.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
    if not args.apply:
        print(json.dumps({'scanned_records':len(records),'proposed_records':len(changes)},ensure_ascii=True));return
    from app.database.connection import engine
    try:print(json.dumps(repair(engine,records,output/now().strftime('%Y%m%dT%H%M%S%fZ')),ensure_ascii=True))
    finally:engine.dispose()

if __name__=='__main__':main()

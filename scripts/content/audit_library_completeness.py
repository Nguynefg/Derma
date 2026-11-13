"""Audit every latest Word record; do not label generated scope text as authored content."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
import csv
import json
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]


def read_folder(folder):
    try:
        from scripts.import_export.sync_word_database import read_folder as read_word_folder
    except ModuleNotFoundError as error:
        if error.name != 'scripts.import_export.sync_word_database':
            raise
        raise SystemExit('Word audit requires the retired sync_word_database.py reader. Use the web editor for current content; no data was changed.') from None
    return read_word_folder(folder)

EMPTY={'','Thông tin tóm tắt đang được bổ sung.','Nội dung tổng quan đang được bổ sung.','Chưa bổ sung thông tin về yếu tố liên quan.','Chưa bổ sung thông tin về phòng ngừa và chăm sóc.'}
FIELDS=['summary','details','risk_factors','prevention']

def main():
    records=read_folder(ROOT/'storage/exports/tbldiseases-50-ban-ghi-ra-soat-lan-4')
    sources={int(r['fields']['disease_id']):r for r in map(json.loads,(ROOT/'storage/temporary/word-content-20261019/records.jsonl').open(encoding='utf-8'))}
    folder=ROOT/'storage/temporary/library-quality';folder.mkdir(parents=True,exist_ok=True)
    missing_counts=Counter();unchanged_chapters=Counter();kinds=Counter();health_gaps=0;missing=[];names=[]
    for rid,row in records.items():
        gaps=[key for key in FIELDS if row[key].strip() in EMPTY]
        missing_counts.update(gaps)
        source=sources.get(rid,{})
        role='supporting_term' if source.get('chapter')=='X' else 'function_assessment' if source.get('chapter')=='V' else 'topic_group' if source.get('kind') in {'block','chapter'} else 'health_topic'
        kinds[role]+=1
        health_gaps+=int(bool(gaps) and role=='health_topic')
        if gaps:
            missing.append({'disease_id':rid,'name':row['name'],'category':row['category'],'chapter':source.get('chapter',''),'record_role':role,'missing_fields':', '.join(gaps),'has_source_definition':bool(source.get('source',{}))})
        if row['name']==row['english_name']:
            unchanged_chapters[source.get('chapter','authored')]+=1
            names.append({'disease_id':rid,'name':row['name'],'category':row['category'],'chapter':source.get('chapter',''),'action':'Đối chiếu danh pháp chuyên ngành; không dịch máy tên riêng.'})
    for filename,rows in [('missing-content.csv',missing),('unchanged-source-names.csv',names)]:
        with (folder/filename).open('w',encoding='utf-8-sig',newline='') as file:
            writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    report={'records_scanned':len(records),'records_with_all_four_content_fields':len(records)-len(missing),'records_missing_content':len(missing),'record_roles':dict(kinds),'health_topics_missing_at_least_one_field':health_gaps,'missing_by_field':dict(missing_counts),'names_identical_to_source':len(names),'identical_names_by_chapter':dict(unchanged_chapters),'scope_descriptions_are_not_clinical_articles':True,'clinical_validation':False}
    (folder/'full-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))

if __name__=='__main__':main()

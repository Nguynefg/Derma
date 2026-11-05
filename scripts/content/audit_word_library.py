"""Independent structural, change-scope and source checks for Word pass three."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from collections import Counter
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from zipfile import ZipFile
from lxml import etree as ET

ROOT=Path(__file__).resolve().parents[2]
BEFORE=ROOT/'storage/exports/tbldiseases-50-ban-ghi-ra-soat-lan-2'
AFTER=ROOT/'storage/exports/tbldiseases-50-ban-ghi-ra-soat-lan-3'
WORK=ROOT/'storage/temporary/word-content-20261019/medlineplus'
OUT=ROOT/'storage/temporary/word-content-20261019/audit-lan-3'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W='{'+NS['w']+'}'
KEYS=['disease_id','slug','name','english_name','category','summary','details','risk_factors','prevention','aliases','published','review_status','version','updated_at']
CLINICAL=set(KEYS[5:9])
EMPTY={'','Thông tin tóm tắt đang được bổ sung.','Nội dung tổng quan đang được bổ sung.','Chưa bổ sung thông tin về yếu tố liên quan.','Chưa bổ sung thông tin về phòng ngừa và chăm sóc.'}
VI=set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ')

def text(cell):
    paragraphs=[]
    for p in cell.findall('w:p',NS):
        chars=[]
        for node in p.iter():
            if node.tag==W+'t':chars.append(node.text or '')
            elif node.tag==W+'br':chars.append('\n')
            elif node.tag==W+'tab':chars.append('\t')
        paragraphs.append(''.join(chars))
    return '\n'.join(paragraphs)

def read(path):
    with ZipFile(path) as z:
        if z.testzip() is not None:raise ValueError('Broken DOCX ZIP: '+str(path))
        root=ET.fromstring(z.read('word/document.xml'))
    rows=[]
    for t in root.findall('w:body/w:tbl',NS):
        cells=t.findall('w:tr',NS)
        assert len(cells)==14,(path.name,'field count')
        pairs=[]
        for row in cells:
            pair=row.findall('w:tc',NS);assert len(pair)==2
            pairs.append((text(pair[0]),text(pair[1])))
        assert [k for k,v in pairs]==KEYS,(path.name,'field order/names')
        rows.append(dict(pairs))
    return rows

def main():
    global BEFORE,AFTER,OUT
    parser=argparse.ArgumentParser();parser.add_argument('--proofread',action='store_true');args=parser.parse_args()
    if args.proofread:
        BEFORE=ROOT/'storage/exports/tbldiseases-50-ban-ghi-ra-soat-lan-3'
        AFTER=ROOT/'storage/exports/tbldiseases-50-ban-ghi-ra-soat-lan-4'
        OUT=ROOT/'storage/temporary/word-content-20261019/audit-lan-4'
    OUT.mkdir(exist_ok=True)
    manifest=json.loads((AFTER/('Thay-doi-hieu-dinh-lan-4.json' if args.proofread else 'Thay-doi-va-nguon-lan-3.json')).read_text('utf-8'))
    planned={(x['disease_id'],x['field']):x for x in manifest};assert len(planned)==len(manifest)
    sources={r['fields']['disease_id']:r for r in map(json.loads,(WORK/'candidates.jsonl').open(encoding='utf-8'))}
    old_sources={r['fields']['disease_id']:r for r in map(json.loads,(WORK.parent/'records.jsonl').open(encoding='utf-8'))}
    if args.proofread:
        sources={rid:dict(r,scope_match_approved=True,source={
          'text':r['source_title']+'\n'+'\n'.join(r['source']['definitions']),
          'url':r['source_url']}) for rid,r in old_sources.items() if r['source']}
    files=sorted(p for p in AFTER.glob('*.docx') if not p.name.startswith('~$'))
    assert {p.name for p in files}=={p.name for p in BEFORE.glob('*.docx') if not p.name.startswith('~$')}
    seen=set();actual={};missing=Counter();with_gaps=0;language=[];errors=[];total=0;existing_edits=0
    for i,path in enumerate(files,1):
        a=read(path);b=read(BEFORE/path.name)
        assert len(a)==len(b) and 0<len(a)<=50
        for now,old in zip(a,b):
            rid=now['disease_id'];assert rid==old['disease_id']
            assert rid.isdigit() and int(rid)>0 and rid not in seen,(rid,'invalid or duplicate id')
            seen.add(rid);total+=1;hasgap=False
            for key in KEYS:
                if now[key]!=old[key]:
                    assert key in CLINICAL and (args.proofread or old[key].strip() in EMPTY),(rid,key,'unapproved overwrite')
                    existing_edits+=int(old[key].strip() not in EMPTY)
                    entry=planned[(rid,key)];assert entry['text']==now[key] and entry['previous']==old[key]
                    row=sources[rid];assert row['scope_match_approved'] and row['fields']['slug']==now['slug']
                    full=' '.join(row['source']['text'].split())
                    assert hashlib.sha256(full.encode()).hexdigest()==entry['source_normalized_sha256']
                    assert row['source']['url']==entry['source_url']
                    for span in entry['evidence_offsets_in_normalized_source']:
                        assert 0<=span['start']<span['end']<=len(full)
                    actual[(rid,key)]=now[key]
                if '\ufffd' in now[key]:errors.append({'id':rid,'field':key,'error':'Unicode replacement character'})
            src=old_sources.get(rid,{}).get('source')
            reference=now['english_name']+' '+ (' '.join(src['definitions']) if src else '')
            # These are valid scientific names, not malformed Vietnamese.
            reference+=' '+{'19096':'vāta','26418':'Waldenström','1405':'Waldenström'}.get(rid,'')
            for key in CLINICAL:
                value=now[key]
                if value.strip() in EMPTY:missing[key]+=1;hasgap=True;continue
                strange=sorted({c for c in value if 'LATIN' in unicodedata.name(c,'') and c not in VI and c not in reference})
                mixed=re.findall(r'\b[a-zà-ỹ]+[ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zà-ỹ]+\b',value)
                if strange or mixed:language.append({'id':rid,'file':path.name,'field':key,'unusual_characters':''.join(strange),'mixed_case_words':'; '.join(mixed),'text':value,'new_in_pass_3':(rid,key) in planned})
                if src and re.search(r'clonal|clonality',' '.join(src['definitions']),re.I) and re.search(r'vô tính|đơn tính|dòng đơn|dòng dòng',value,re.I):
                    errors.append({'id':rid,'field':key,'error':'Clonal terminology needs correction','text':value})
            with_gaps+=int(hasgap)
        if i%200==0:print(json.dumps({'checked_files':i,'records':total}),flush=True)
    assert set(actual)==set(planned)
    assert total==37236 and len(files)==745
    with ZipFile(AFTER.with_suffix('.zip')) as z:
        assert z.testzip() is None
        assert sum(n.endswith('.docx') for n in z.namelist())==len(files)
        for p in files:assert z.read(AFTER.name+'/'+p.name)==p.read_bytes(),('ZIP differs',p.name)
    report={'docx_files':len(files),'records':total,'unique_ids':len(seen),'fields_per_record':14,
      'changed_fields':len(actual),'changed_records':len({rid for rid,key in actual}),
      'all_changes_match_manifest':True,'authorized_edits_to_populated_content_fields':existing_edits,'unapproved_overwrites':0,'protected_field_changes':0,
      'source_hash_and_scope_checks_passed':True,'zip_matches_docx_files':True,
      'definite_encoding_errors':errors,'potential_language_issues_to_inspect':len(language),
      'records_missing_at_least_one_content_field':with_gaps,'missing_fields':dict(missing),
      'visual_render_verified':False,'clinical_validation':False}
    (OUT/'audit-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    (OUT/'potential-language-issues.json').write_text(json.dumps(language,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2))
if __name__=='__main__':main()

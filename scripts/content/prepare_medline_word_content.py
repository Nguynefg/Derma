"""Index permitted NLM summaries and match only exact condition names."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as ET, html
from scripts.content.prepare_word_content import normalized

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'storage/temporary/word-content-20261019'
OUT=WORK/'medlineplus'

def clean(raw):
    if not raw:return ''
    tree=html.fragment_fromstring(raw,create_parent='div')
    return '\n'.join(' '.join(n.itertext()).strip() for n in tree if isinstance(n.tag,str) and ' '.join(n.itertext()).strip()) or ' '.join(tree.itertext()).strip()

def main():
    index=defaultdict(list)
    with ZipFile(OUT/'health-topics.zip') as z:
        root=ET.fromstring(z.read(next(n for n in z.namelist() if n.endswith('.xml'))))
    for row in root:
        if row.get('language')!='English':continue
        text=clean(row.findtext('full-summary'))
        if not text:continue
        entry={'title':row.get('title'),'url':row.get('url'),'text':text,'type':'health_topic_summary'}
        index[normalized(entry['title'])].append(entry)
    root=ET.parse(OUT/'genetics.xml').getroot()
    ns={'g':ET.QName(root).namespace}
    for row in root.findall('g:health-condition-summary',ns):
        title=row.findtext('g:name',namespaces=ns)
        url=row.findtext('g:ghr-page',namespaces=ns)
        parts=[]
        for text in row.findall('g:text-list/g:text',ns):
            role=text.findtext('g:text-role',namespaces=ns)
            node=text.find('g:html',ns)
            if node is not None and role in {'description','causes','inheritance'}:
                parts.append(role+':\n'+' '.join(node.itertext()))
        memos=row.findall('g:inheritance-pattern-list/g:inheritance-pattern/g:memo',ns)
        if memos:parts.append('Inheritance pattern(s): '+ '; '.join(m.text for m in memos if m.text))
        entry={'title':title,'url':url,'text':'\n\n'.join(parts),'type':'genetic_condition_summary'}
        if not entry['text']:continue
        names=[title]+[n.text for n in row.findall('g:synonym-list/g:synonym',ns) if n.text]
        for name in names:index[normalized(name)].append(entry)
    missing={r['disease_id']:r['missing_fields'].split('; ') for r in csv.DictReader((ROOT/'storage/exports/tbldiseases-50-ban-ghi-ra-soat-lan-2/Cac-muc-con-thieu-noi-dung.csv').open(encoding='utf-8-sig'))}
    candidates=[];ambiguous=[]
    for row in map(json.loads,(WORK/'records.jsonl').open(encoding='utf-8')):
        rid=row['fields']['disease_id']
        if rid not in missing:continue
        hits=index.get(normalized(row['source_title']),[])
        unique={h['url']:h for h in hits}
        # An exact title takes precedence over a synonym, then only one source
        # is accepted. No code crosswalks or parent terms are used.
        exact={u:h for u,h in unique.items() if normalized(h['title'])==normalized(row['source_title'])}
        if exact:unique=exact
        if len(unique)>1:
            # A general topic and a genetics topic may differ in scope. Keep
            # these for explicit review rather than arbitrarily choosing one.
            ambiguous.append({'id':rid,'title':row['source_title'],'sources':list(unique)})
            continue
        if len(unique)!=1:continue
        source=next(iter(unique.values()))
        candidates.append({'fields':row['fields'],'file':row['file'],'missing':missing[rid],
          'source_title':row['source_title'],'source':source,'kind':row['kind'],'chapter':row['chapter']})
    # One condition per source in a pass, preventing reuse across differently
    # scoped rows and keeping the paraphrase budget per source explicit.
    seen=set();accepted=[];duplicates=[]
    for row in candidates:
        url=row['source']['url']
        if url in seen:duplicates.append(row['fields']['disease_id']);continue
        seen.add(url);accepted.append(row)
    (OUT/'candidates.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in accepted),'utf-8')
    report={'matched_records':len(accepted),'ambiguous_matches_not_used':ambiguous,
      'duplicate_source_rows_not_used':duplicates,'types':dict(Counter(r['source']['type'] for r in accepted)),
      'download_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUT/'health-topics.zip',OUT/'genetics.xml']},
      'attribution':'Source: MedlinePlus, National Library of Medicine.',
      'permissions':'https://medlineplus.gov/about/using/usingcontent/',
      'matched_name_policy':'Exact normalized source title or explicit genetics synonym; no parent or code-based match.'}
    (OUT/'matching-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in {'ambiguous_matches_not_used','duplicate_source_rows_not_used'}},ensure_ascii=True))
if __name__=='__main__':main()

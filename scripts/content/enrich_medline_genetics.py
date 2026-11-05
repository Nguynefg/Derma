"""Add condition-specific causes/inheritance prose from public NLM pages.

The compact XML inheritance labels alone may hide important distinctions
between acquired and inherited forms; the prose is needed for editorial QA.
"""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import json
import re
from pathlib import Path
import time
from urllib.request import Request,urlopen
from urllib.parse import urlparse
from lxml import html
from scripts.content.prepare_word_content import normalized

WORK=Path(__file__).resolve().parents[2]/'storage/temporary/word-content-20261019/medlineplus'

def fetch(row):
    url=row['source']['url'];assert urlparse(url).hostname=='medlineplus.gov'
    path=WORK/'genetics-pages'/(hashlib.sha256(url.encode()).hexdigest()+'.html')
    if not path.exists():
        req=Request(url,headers={'User-Agent':'MedicalReferenceDraftReview/1.0'})
        with urlopen(req,timeout=35) as response:
            assert urlparse(response.url).hostname=='medlineplus.gov'
            data=response.read()
        path.write_bytes(data)
        time.sleep(1)
    root=html.fromstring(path.read_bytes())
    h=root.xpath('//h1');assert len(h)==1
    assert normalized(h[0].text_content())==normalized(row['source']['title'])
    sections=[]
    for role in ['causes','inheritance']:
        for section in root.xpath('//div[@data-bookmark="'+role+'"]'):
            content=section.xpath('.//div[contains(concat(" ",normalize-space(@class)," ")," mp-content ")]')
            paragraphs=[]
            for node in content:
                paragraphs.extend(' '.join(p.text_content().split()) for p in node.xpath('./p') if p.text_content().strip())
            if paragraphs:sections.append(role+':\n'+'\n'.join(paragraphs))
    return row['fields']['disease_id'],sections

def main():
    path=WORK/'candidates.jsonl';original=path.read_text('utf-8')
    rows=list(map(json.loads,original.splitlines()))
    (WORK/'genetics-pages').mkdir(exist_ok=True)
    selected=[r for r in rows if r['source']['type']=='genetic_condition_summary' and
      any(f in r['missing'] for f in ['summary','details','risk_factors'])]
    additions={};failures=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        active={pool.submit(fetch,r):r for r in selected}
        for future in as_completed(active):
            r=active[future]
            try:
                rid,sections=future.result();additions[rid]=sections
            except Exception as exc:failures.append({'id':r['fields']['disease_id'],'error':str(exc)})
            if (len(additions)+len(failures))%25==0:print(json.dumps({'fetched':len(additions),'failed':len(failures)}),flush=True)
    backup=WORK/'candidates-before-genetics-prose.jsonl'
    if not backup.exists():backup.write_text(original,'utf-8')
    for r in rows:
        sections=additions.get(r['fields']['disease_id'])
        if sections:
            r['source']['additional_source_sections']=sections
            # Idempotent: always append to the original compact summary.
            base=next(x for x in map(json.loads,backup.read_text('utf-8').splitlines()) if x['fields']['disease_id']==r['fields']['disease_id'])
            compact=re.sub(r'^Inheritance pattern\(s\):.*$', '', base['source']['text'], flags=re.M).strip()
            r['source']['text']=compact+'\n\n'+'\n\n'.join(sections)
    temp=path.with_suffix('.tmp');temp.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),'utf-8');temp.replace(path)
    report={'selected':len(selected),'fetched':len(additions),'with_additional_sections':sum(bool(v) for v in additions.values()),'failures':failures}
    (WORK/'genetics-prose-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(report,ensure_ascii=True),flush=True)
if __name__=='__main__':main()

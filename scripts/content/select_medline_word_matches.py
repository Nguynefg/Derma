"""Reject broad/narrow synonym matches before any Word content is written."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
import json
from pathlib import Path
from scripts.content.prepare_word_content import normalized

WORK=Path(__file__).resolve().parents[2]/'storage/temporary/word-content-20261019/medlineplus'
# Individually assessed terminology/orthography equivalents. This deliberately
# excludes narrower genetic subtypes and broader syndrome groups.
EQUIVALENT_IDS=set('556 842 2648 2681 2743 2818 2872 2896 3103 3104 3194 3409 3482 3580 4690 4714 4814 5269 5304 6203 6204 6380 6425 6774 8209 8333 8436 10130 10430 10493 12370 12458 12474 12584'.split())
CONTEXT_EXCLUSIONS={
  '10345':'The classification grouping may include spontaneous loss; the NLM topic specifically discusses induced abortion.',
  '11596':'This developmental-anomaly record must not receive an acquired eye-injury cause.',
  '13056':'An anxiety symptom must not automatically receive risk factors for anxiety disorders.'}

def main():
    path=WORK/'candidates.jsonl';rows=list(map(json.loads,path.read_text('utf-8').splitlines()))
    excluded=[]
    for row in rows:
        rid=row['fields']['disease_id'];exact=normalized(row['source_title'])==normalized(row['source']['title'])
        allowed=row['chapter']!='X' and (exact or rid in EQUIVALENT_IDS) and rid not in CONTEXT_EXCLUSIONS
        row['scope_match_approved']=allowed
        row['scope_match_reason']='Exact title or individually checked equivalent term' if allowed else (
          'Extension/anatomy/substance/device record excluded from a disease-article pass' if row['chapter']=='X' else 'Synonym may have broader/narrower clinical scope; not used without further review')
        if rid in CONTEXT_EXCLUSIONS:row['scope_match_reason']=CONTEXT_EXCLUSIONS[rid]
        if not allowed:excluded.append({'id':rid,'title':row['source_title'],'source_title':row['source']['title'],'reason':row['scope_match_reason']})
    path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),'utf-8')
    report={'initial_matches':len(rows),'scope_approved':sum(r['scope_match_approved'] for r in rows),'excluded':excluded}
    (WORK/'scope-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='excluded'}))
if __name__=='__main__':main()

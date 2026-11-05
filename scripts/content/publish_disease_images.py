import re
"""Publish only explicit, visually reviewed approvals; no automatic redirect inheritance."""
import json,shutil,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'storage/temporary/disease-covers'
registry=ROOT/'frontend/src/shared/data/diseaseCovers.json';public=ROOT/'frontend/public/assets/library/diseases'
rows=json.loads((public/'credits.json').read_text(encoding='utf-8'));staged={r['key']:r for r in json.loads((OUT/'staged.json').read_text(encoding='utf-8'))};approvals=json.loads((OUT/'approvals.json').read_text(encoding='utf-8'))
norm=lambda s:' '.join(s.casefold().split())
known={norm(n) for r in rows for n in r['names']};added=0
for key,approval in approvals.items():
 r=staged[key];names=[n for n in approval['names'] if norm(n) not in known]
 if not names:continue
 assert bool(re.fullmatch(r'CC BY(?:-SA)? \d+\.\d+(?: [a-z]{2})?',r['license'])) or r['license'] in ('CC0','Public domain')
 p=Path(r['path']).resolve();assert p.parent==(OUT/'staged').resolve() and p.suffix=='.webp'
 assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
 dst=public/(key+'.webp');shutil.copyfile(p,dst)
 record={k:v for k,v in r.items() if k not in ('file','path','topics')};record.update(names=names,src='/assets/library/diseases/'+dst.name,caption=approval['caption'])
 record['licenseUrl']=record['licenseUrl'].replace('http://creativecommons.org/','https://creativecommons.org/')
 rows.append(record);known.update(map(norm,names));added+=1
fields=('key','names','src','sourceUrl','creator','license','licenseUrl','caption')
registry.write_text(json.dumps([{k:v for k,v in row.items() if k in fields} for row in rows],ensure_ascii=False,indent=2),encoding='utf-8')
(public/'credits.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('New images:',added,'Total images:',len(rows),'Exact topic names:',len(known))

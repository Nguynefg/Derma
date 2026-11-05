"""Read the public library of the running local web app without credentials or writes."""
import json,time,urllib.request

def read_live_records(base_url='http://127.0.0.1:8000'):
 rows=[];total=None
 for page in range(1,1000):
  url=f'{base_url.rstrip("/")}/api/v1/library/search?page={page}&page_size=100&sort=name'
  with urllib.request.urlopen(url,timeout=30) as response:result=json.load(response)
  if total is None:total=result['total'];print('Live website library:',total,flush=True)
  if result['total']!=total:raise RuntimeError('Library count changed during export')
  for item in result['items']:
   article=item.get('article') or {};source=item.get('icd') or {}
   rows.append(dict(disease_id=item['id'],slug=article.get('slug',''),name=item['title'],english_name=article.get('english_name') or source.get('original_title') or ''))
  if page%25==0:print('Website records read:',len(rows),flush=True)
  if page*100>=total:break
  time.sleep(.05)
 if len(rows)!=total or len({r['disease_id'] for r in rows})!=total:raise RuntimeError('Incomplete or unstable library snapshot')
 return rows

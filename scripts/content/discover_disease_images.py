"""Discover exact Wikipedia image candidates for every exported disease; never publish automatically."""
import json,urllib.request,urllib.parse,time,concurrent.futures,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'storage/temporary/disease-covers';OUT.mkdir(parents=True,exist_ok=True)

_last_request = 0.0

def query(host,params):
 global _last_request
 import urllib.error
 from email.utils import parsedate_to_datetime
 url='https://'+host+'/w/api.php?'+urllib.parse.urlencode(dict(action='query',format='json',maxlag=5,**params))
 for attempt in range(8):
  time.sleep(max(0,7-(time.monotonic()-_last_request)))
  _last_request=time.monotonic()
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'DermaLibraryEducationalProject/1.0'}),timeout=35) as response:result=json.load(response)
   if 'error' in result:raise RuntimeError(result['error'].get('code','API error'))
   return result
  except urllib.error.HTTPError as error:
   if error.code not in (429,503) or attempt==7:raise
   retry=error.headers.get('Retry-After','60')
   try:delay=float(retry)
   except ValueError:delay=max(60,parsedate_to_datetime(retry).timestamp()-time.time())
   print('Source rate limited; waiting',int(delay),'seconds',flush=True)
   time.sleep(max(60,delay))
  except Exception:
   if attempt==7:raise
   time.sleep(min(60,5*2**attempt))

def batch(index,names):
 cache=OUT/'discovery-cache'/f'{index:04d}-{hashlib.sha256(chr(10).join(names).encode()).hexdigest()[:12]}.json';cache.parent.mkdir(exist_ok=True)
 if cache.exists():return json.loads(cache.read_text(encoding='utf-8'))
 result=query('en.wikipedia.org',{'redirects':1,'prop':'pageimages','piprop':'name|original','pilimit':50,'titles':'|'.join(names)})
 q=result.get('query',{});redirect={x['from']:x['to'] for x in q.get('normalized',[])+q.get('redirects',[])}
 pages={p['title']:p for p in q.get('pages',{}).values()};rows=[]
 for name in names:
  resolved=name;seen=set()
  while resolved in redirect and resolved not in seen:seen.add(resolved);resolved=redirect[resolved]
  p=pages.get(resolved,{})
  rows.append(dict(name=name,resolved=resolved,page=p,status='candidate' if p.get('pageimage') else 'no_image' if 'missing' not in p and p else 'no_page'))
 cache.write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8');return rows

if __name__=='__main__':
 records=json.loads((OUT/'library-records.json').read_text(encoding='utf-8'));names=list(dict.fromkeys(r['english_name'].strip() for r in records if r.get('english_name') and '|' not in r['english_name'] and len(r['english_name'])<240))
 batches=[names[i:i+40] for i in range(0,len(names),40)];results=[]
 for i,chunk in enumerate(batches):
  try:results.extend(batch(i,chunk))
  except Exception as e:print('Batch failed',i,type(e).__name__,flush=True)
  if (i+1)%10==0:print('Batches',i+1,'/',len(batches),'candidates',sum(r['status']=='candidate' for r in results),flush=True)
 (OUT/'all-discovery.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
 counts={s:sum(r['status']==s for r in results) for s in ('candidate','no_image','no_page')}
 (OUT/'discovery-result.json').write_text(json.dumps(dict(snapshot_records=len(records),unique_names=len(names),processed=len(results),**counts),indent=2),encoding='utf-8');print(counts,flush=True)

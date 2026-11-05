"""Collect indexed medical pages in bulk and match exact names locally."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from discover_disease_images import query,OUT
if __name__=='__main__':
 offset=0;pages=[]
 while True:
  cache=OUT/f'medical-pages-{offset//500:03d}.json'
  if cache.exists():result=json.loads(cache.read_text(encoding='utf-8'))
  else:
   result=query('en.wikipedia.org',{'generator':'search','gsrsearch':'hastemplate:"Infobox medical condition"','gsrlimit':500,'gsrnamespace':0,'gsroffset':offset,'prop':'pageprops','ppprop':'page_image_free'})
   cache.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
  pages.extend(result.get('query',{}).get('pages',{}).values());print('Medical pages indexed:',len(pages),flush=True)
  if 'continue' not in result:break
  offset=result['continue']['gsroffset']
 records=json.loads((OUT/'library-records.json').read_text(encoding='utf-8'));norm=lambda s:' '.join(s.casefold().replace('_',' ').split())
 byname={norm(p['title']):p for p in pages};candidates={}
 for row in records:
  name=row.get('english_name','');p=byname.get(norm(name))
  if p and p.get('pageprops',{}).get('page_image_free'):
   candidates[name]=dict(name=name,resolved=p['title'],page=dict(title=p['title'],pageimage=p['pageprops']['page_image_free']),status='candidate')
 for p in (OUT/'discovery-cache').glob('*.json'):
  for row in json.loads(p.read_text(encoding='utf-8')):
   if row['status']=='candidate':candidates.setdefault(row['name'],row)
 (OUT/'all-discovery.json').write_text(json.dumps(list(candidates.values()),ensure_ascii=False,indent=2),encoding='utf-8')
 print('Library names with candidate images:',len(candidates),'Indexed pages:',len(pages),flush=True)

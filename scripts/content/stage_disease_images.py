"""Stage licensed candidates for visual review. Does not change the public image registry."""
import sys,json,re,html,urllib.request,urllib.error,hashlib,io,concurrent.futures,time
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parent))
from discover_disease_images import query,OUT,ROOT

def clean(s):return html.unescape(re.sub('<[^>]+>','',s)).strip()
def norm(s):return s.casefold().strip().replace('_',' ')
class SourceRateLimited(RuntimeError):
 pass

_last_download=0.0

def download(url):
 global _last_download
 state=OUT/'download-state.json'
 if state.exists():
  saved=json.loads(state.read_text(encoding='utf-8'))
  if saved.get('retry_after_unix',0)>time.time():raise SourceRateLimited('Image source cooldown is still active')
 from email.utils import parsedate_to_datetime
 for attempt in range(4):
  time.sleep(max(0,1.2-(time.monotonic()-_last_download)))
  _last_download=time.monotonic()
  req=urllib.request.Request(url,headers={'User-Agent':'DermaLibraryEducationalProject/1.0'})
  try:
   with urllib.request.urlopen(req,timeout=35) as response:return response.read()
  except urllib.error.HTTPError as error:
   if error.code not in (429,503) or attempt==3:raise
   retry=error.headers.get('Retry-After','60')
   try:delay=float(retry)
   except ValueError:delay=max(60,parsedate_to_datetime(retry).timestamp()-time.time())
   if delay>=60:
    state.write_text(json.dumps({'status':'paused_by_source','retry_after_seconds':delay,'retry_after_unix':time.time()+delay},indent=2),encoding='utf-8')
    raise SourceRateLimited('Image source requires a cooldown; progress saved') from error
   print('Image source throttled; waiting',int(delay),'seconds',flush=True)
   time.sleep(max(1,delay))

def stage(pair):
 title,info=pair;meta=info.get('extmetadata',{});lic=meta.get('LicenseShortName',{}).get('value','')
 if not (bool(re.fullmatch(r'CC BY(?:-SA)? \d+\.\d+(?: [a-z]{2})?',lic)) or lic in ('Public domain','CC0')):return None
 url=info.get('thumburl',info.get('url',''))
 if not url.startswith(('https://upload.wikimedia.org/','https://thumb.wikimedia.org/')):return None
 key=hashlib.sha256(title.encode()).hexdigest()[:20];p=OUT/'staged'/f'{key}.webp';p.parent.mkdir(exist_ok=True)
 try:
  if not p.exists():
   if '--offline' in sys.argv:return None
   raw=download(url)
   with Image.open(io.BytesIO(raw)) as source:
    im=ImageOps.exif_transpose(source).convert('RGB');im.thumbnail((960,960));im.save(p,'WEBP',quality=86)
  return dict(key=key,file=title,path=str(p),sourceUrl=info['descriptionurl'],creator=clean(meta.get('Artist',{}).get('value','Wikimedia Commons')),license=lic,licenseUrl=meta.get('LicenseUrl',{}).get('value','https://commons.wikimedia.org/wiki/Commons:Copyright_tags#Public_domain'),description=clean(meta.get('ImageDescription',{}).get('value','')),modifications='Resized without cropping; converted to WebP',sha256=hashlib.sha256(p.read_bytes()).hexdigest())
 except SourceRateLimited:raise
 except Exception as e:print('Skip image',key,type(e).__name__,getattr(e,'code',''),flush=True);return None

if __name__=='__main__':
 candidates=json.loads((OUT/'all-discovery.json').read_text(encoding='utf-8')) if (OUT/'all-discovery.json').exists() else []
 for p in sorted((OUT/'discovery-cache').glob('*.json')):
  candidates.extend(r for r in json.loads(p.read_text(encoding='utf-8')) if r['status']=='candidate')
 # Every topic remains a candidate until exact meaning and its image have been reviewed.
 byfile={}
 for row in candidates:byfile.setdefault('File:'+row['page']['pageimage'].replace('_',' '),[]).append(row)
 files=list(byfile);metadata={};cache=OUT/'metadata-cache';cache.mkdir(exist_ok=True)
 for cached in cache.glob('*.json'):
  result=json.loads(cached.read_text(encoding='utf-8'))
  for item in result.get('query',{}).get('pages',{}).values():
   if item.get('imageinfo'):metadata[item['title'].replace('_',' ')]=item['imageinfo'][0]
 missing=[f for f in files if f not in metadata]
 for start in range(0,len(missing),50):
  if '--offline' in sys.argv:break
  chunk=missing[start:start+50];key=hashlib.sha256('|'.join(chunk).encode()).hexdigest()[:20];p=cache/f'{key}.json'
  try:
   result=query('commons.wikimedia.org',{'prop':'imageinfo','iiprop':'url|extmetadata|size','iiurlwidth':640,'titles':'|'.join(chunk)})
   p.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
   for item in result.get('query',{}).get('pages',{}).values():
    if item.get('imageinfo'):metadata[item['title'].replace('_',' ')]=item['imageinfo'][0]
   print('Metadata processed',min(start+50,len(missing)),'/',len(missing),flush=True)
  except Exception as e:print('Metadata batch failed',type(e).__name__,getattr(e,'code',''),flush=True)
 staged=[]
 paused=False
 for index,pair in enumerate(metadata.items(),1):
  try:row=stage(pair)
  except SourceRateLimited as error:
   print(str(error),flush=True);paused=True;break
  if row:
   row['topics']=list({r['name']:dict(name=r['name'],resolved=r['resolved']) for r in byfile.get(row['file'],[])}.values())
   staged.append(row)
  if index%25==0:
   (OUT/'staged.json').write_text(json.dumps(staged,ensure_ascii=False,indent=2),encoding='utf-8')
   print('Images processed',index,'/',len(metadata),'staged',len(staged),flush=True)
 staged.sort(key=lambda r:r['topics'][0]['name'] if r['topics'] else r['key'])
 (OUT/'staged.json').write_text(json.dumps(staged,ensure_ascii=False,indent=2),encoding='utf-8')
 sheets=OUT/'review';sheets.mkdir(exist_ok=True)
 for start in range(0,len(staged),40):
  sheet=Image.new('RGB',(1200,230*10),'white');draw=ImageDraw.Draw(sheet)
  for offset,row in enumerate(staged[start:start+40]):
   x=(offset%4)*300;y=(offset//4)*230;im=Image.open(row['path']);im.thumbnail((290,175));sheet.paste(im,(x+(300-im.width)//2,y));
   name=row['topics'][0]['name'] if row['topics'] else row['key'];safe=name.encode('ascii','replace').decode()
   draw.text((x+5,y+178),f'{start+offset}: '+safe[:42],fill='black');draw.text((x+5,y+194),safe[42:84],fill='black');draw.text((x+5,y+210),row['license'],fill='black')
  sheet.save(sheets/f'sheet-{start//40:03d}.jpg')
 print('Staged licensed images:',len(staged),flush=True)

 if paused:sys.exit(2)

"""Read only the fields needed for cover lookup; never log connection details."""
import sys,json,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from dotenv import load_dotenv
load_dotenv(ROOT/'.env')
from app.database.connection import engine
from sqlalchemy import text
from read_website_library import read_live_records
OUT=ROOT/'storage/temporary/disease-covers';OUT.mkdir(parents=True,exist_ok=True)
try:
 with engine.connect() as connection:
  rows=[dict(r) for r in connection.execute(text('SELECT disease_id, slug, name, english_name FROM dbo.tbldiseases')).mappings()]
 source='Live SQL read-only query'
except Exception as error:
 print('Direct SQL read unavailable:',type(error).__name__,flush=True)
 try:
  rows=read_live_records();source='Live website public library API'
 except Exception as error:
  print('Website read unavailable:',type(error).__name__,flush=True)
  snapshot=ROOT/'storage/exports/database-word/20261020T235915095684Z/tbldiseases.jsonl'
  rows=[{k:r.get(k) for k in ('disease_id','slug','name','english_name')} for line in snapshot.read_text(encoding='utf-8').splitlines() if (r:=json.loads(line))]
  source='Export snapshot 20261020T235915095684Z; live sources unavailable'
(OUT/'library-records.json').write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')
(OUT/'record-source.json').write_text(json.dumps({'source':source,'records':len(rows),'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2),encoding='utf-8')
print('Image lookup input records:',len(rows),'Source:',source,flush=True)

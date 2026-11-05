"""Convert all imported records in the configured database to article columns."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.database.connection import engine
from app.modules.library.library_conversion import convert_articles

if __name__ == '__main__':
    try:
        result = convert_articles(engine, ROOT / 'storage/backups')
        result.update(database_backend=engine.dialect.name, database=engine.url.database)
        output = ROOT / 'storage/temporary/library-conversion'
        output.mkdir(parents=True, exist_ok=True)
        (output / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=True, indent=2))
    finally:
        engine.dispose()

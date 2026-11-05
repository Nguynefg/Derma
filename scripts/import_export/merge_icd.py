"""Consolidate existing ICD data, verify and drop only successfully moved tables."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
from app.database.connection import engine
from app.modules.library.icd_merge import merge_icd_tables

result = merge_icd_tables(engine, ROOT / 'storage/backups')
(ROOT / 'storage/imports/icd-import' / "merge-result.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(result, ensure_ascii=True, indent=2))

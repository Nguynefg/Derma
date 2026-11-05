"""Import the WHO snapshot into the project's configured database, atomically."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
from app.database.connection import engine
from app.modules.library.icd_import import parse_sources, import_payload

parser = argparse.ArgumentParser()
parser.add_argument(
    "--zip", default=str(ROOT / "storage/imports/icd-import/SimpleTabulation-ICD-11-MMS-en.zip")
)
parser.add_argument("--docx", default=str(ROOT / "storage/imports/icd-import/print_Foundation_MMS-en.docx"))
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()
payload = parse_sources(args.zip, args.docx)
report = dict(
    version=payload["version"],
    fingerprint=payload["fingerprint"],
    entities=len(payload["entities"]),
    chapters=len(payload["documents"]),
    source_files=len(payload["sources"]),
)
if args.apply:
    report.update(import_payload(engine, payload))
    target = ROOT / "storage/imports/icd-import/import-result.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=True, indent=2))

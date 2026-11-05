"""Apply completed title translations to the configured app database."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.database.connection import engine
from app.modules.library.icd_translation import apply_translated_titles

if __name__ == "__main__":
    try:
        print(json.dumps(apply_translated_titles(engine)))
    finally:
        engine.dispose()

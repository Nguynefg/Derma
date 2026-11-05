"""Apply approved Vietnamese chapter titles to the configured application database."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.database.connection import engine
from app.modules.library.icd_chapters import translate_chapter_titles

if __name__ == "__main__":
    try:
        print(json.dumps(translate_chapter_titles(engine), ensure_ascii=False))
    finally:
        engine.dispose()

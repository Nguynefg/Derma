"""Check/upgrade the configured database. Run while the web server is stopped."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.database.connection import engine
from app.database.migrations.numeric_ids import upgrade


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                upgrade(engine, ROOT / "storage/backups", args.apply), ensure_ascii=False, indent=2
            )
        )
    finally:
        engine.dispose()

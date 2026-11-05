from app.modules.library.library_source import source_data, source_filter, preload_sources
"""Resumable title translations; original WHO source fields remain intact."""

import json
from pathlib import Path
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import Session
from app.database.models import Disease
from app.modules.library.icd_terminology import medical_title

TRANSLATION_FILE = Path(__file__).resolve().parents[4] / "storage/imports/icd-import/titles-vi.json"
PACKAGED_TRANSLATIONS = Path(__file__).resolve().parents[2] / "data/icd_titles_vi.json"


def translated_title(row, source):
    title = next((a[3:] for a in (row.aliases or []) if a.startswith("vi:")), source)
    return medical_title(source, title)


def apply_translated_titles(engine, path=None):
    if path is None:
        path = TRANSLATION_FILE if TRANSLATION_FILE.exists() else PACKAGED_TRANSLATIONS
    if not Path(path).exists():
        return {"updated_titles": 0}
    translations = json.loads(Path(path).read_text(encoding="utf-8"))["translations"]
    from app.modules.library.catalog import normalize

    changed = 0
    with Session(engine) as db, db.begin():
        rows = db.scalars(
            select(Disease).where(
                or_(
                    Disease.review_status == "icd_classification",
                    and_(Disease.published == True, Disease.name == Disease.english_name),
                )
            )
        )
        rows = list(rows)
        preload_sources(db, rows)
        # Manual editor titles take precedence over automatic dictionary refreshes.
        from app.modules.library.library_editorial import editorials
        manually_edited = editorials(db, [r.id for r in rows])
        for row in rows:
            if row.id in manually_edited:
                continue
            original = (
                source_data(row)["title"]
                if row.review_status == "icd_classification"
                else row.english_name
            )
            title = translations.get(original)
            if not isinstance(title, str) or not title.strip() or len(title) > 1000:
                continue
            title = medical_title(original, title.strip())
            old_normalized = {normalize(a[3:]) for a in (row.aliases or []) if a.startswith("vi:")}
            aliases = [
                a
                for a in (row.aliases or [])
                if not a.startswith("vi:") and a not in old_normalized
            ]
            aliases = list(dict.fromkeys([*aliases, "vi:" + title, normalize(title)]))
            if row.name != title[:120] or row.aliases != aliases:
                row.name = title[:120]
                row.aliases = aliases
                changed += 1
    return {"updated_titles": changed}

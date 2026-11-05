"""Convert imported source envelopes into ordinary article columns, transactionally."""
import gzip
import hashlib
import json
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.models import Disease, MedicalDocument, DocumentVersion, now
from app.modules.library.library_source import SOURCE_PREFIX, source_data
from app.modules.library.library_editorial import editorials
from app.modules.library.catalog import normalize
from app.modules.library.icd_terminology import medical_title
from app.modules.library.library_groups import specific_group
from app.modules.library.icd_chapters import CHAPTER_TITLES_VI


def conversion_status(db):
    from collections import Counter
    statuses = Counter()
    converted_ids, raw_ids, imported_ids = set(), set(), set()
    for record_id, status, aliases, details in db.execute(select(
        Disease.id, Disease.review_status, Disease.aliases, Disease.details
    )):
        statuses[status] += 1
        if status == 'icd_classification':
            imported_ids.add(record_id)
        if 'article-columns:v1' in (aliases or []):
            converted_ids.add(record_id)
        try:
            value = json.loads(details)
        except (ValueError, TypeError):
            continue
        if isinstance(value, dict) and 'class_kind' in value:
            raw_ids.add(record_id)
    preserved_ids = set(db.scalars(select(MedicalDocument.disease_id).join(
        DocumentVersion, DocumentVersion.document_id == MedicalDocument.id
    ).where(MedicalDocument.slug.startswith(SOURCE_PREFIX),
            DocumentVersion.version == MedicalDocument.version)))
    return {
        'total_records': sum(statuses.values()), 'review_status_counts': dict(statuses),
        'imported_records': len(imported_ids), 'converted_records': len(converted_ids),
        'remaining_source_json': len(raw_ids),
        'source_json_with_other_status': len(raw_ids - imported_ids),
        'converted_missing_source_document': len(converted_ids - preserved_ids),
        'unrecognized_imported_records': len(imported_ids - raw_ids - converted_ids),
    }


def convert_articles(engine, backup_dir):
    from app.modules.library.icd_routes import group_name
    translations_path = Path(__file__).resolve().parents[2] / 'data/icd_titles_vi.json'
    translations = json.loads(translations_path.read_text(encoding='utf-8'))['translations']
    with Session(engine) as db, db.begin():
        rows = db.scalars(select(Disease).where(Disease.review_status == 'icd_classification').order_by(Disease.id)).all()
        pending = []
        for row in rows:
            try:
                data = json.loads(row.details)
            except (ValueError, TypeError):
                continue
            if isinstance(data, dict) and 'class_kind' in data:
                pending.append((row, data))
        if not pending:
            stats = conversion_status(db)
            complete = (stats['converted_records'] > 0
                        and stats['remaining_source_json'] == 0
                        and stats['converted_missing_source_document'] == 0
                        and stats['unrecognized_imported_records'] == 0)
            return {'converted': 0, 'status': 'already_converted' if complete else 'needs_inspection', **stats}
        # Finish a restorable backup before the first mutation. Identity/slug/FKs stay intact.
        folder = Path(backup_dir)
        folder.mkdir(parents=True, exist_ok=True)
        backup = folder / ('article-columns-' + now().strftime('%Y%m%dT%H%M%S%fZ') + '.json.gz')
        with gzip.open(backup, 'wt', encoding='utf-8') as file:
            json.dump([{c.key: (getattr(row, 'id' if c.key == 'disease_id' else c.key).isoformat() if c.key == 'updated_at' else getattr(row, 'id' if c.key == 'disease_id' else c.key)) for c in Disease.__table__.columns} for row, _ in pending], file, ensure_ascii=False)
        edits = editorials(db, [r.id for r, _ in pending])
        existing_sources = set(db.scalars(select(MedicalDocument.slug).where(MedicalDocument.slug.startswith(SOURCE_PREFIX))))
        for row, source in pending:
            original = {key: getattr(row, key) for key in ['name','english_name','category','summary','details','risk_factors','prevention','aliases','published','review_status','version']}
            content = json.dumps({'source': source, 'before': original}, ensure_ascii=False)
            if SOURCE_PREFIX + str(row.id) in existing_sources:
                raise ValueError('Source document collision; transaction rolled back')
            doc = MedicalDocument(slug=SOURCE_PREFIX + str(row.id), disease_id=row.id,
                title=source['title'][:200], publisher='World Health Organization',
                source_url=source['browser_url'], usage_note='library_source_provenance', published=False, version=1)
            db.add(doc)
            db.flush()
            db.add(DocumentVersion(document_id=doc.id, version=1, title=doc.title,
                publisher=doc.publisher, source_url=doc.source_url, usage_note=doc.usage_note,
                content=content, checksum=hashlib.sha256(content.encode()).hexdigest(), editor_id=None))
            row._library_source = source
            title = medical_title(source['title'], translations.get(source['title'], source['title']))
            if source['class_kind'] == 'chapter':
                title = CHAPTER_TITLES_VI.get(source['chapter_no'], title)
            row.name = title[:120]
            row.english_name = source['title'][:120]
            row.category = (specific_group(source) or group_name(source['chapter_no']))[:60]
            row.summary = 'Thông tin tóm tắt đang được bổ sung.'
            row.details = 'Nội dung tổng quan đang được bổ sung.'
            row.risk_factors = 'Chưa bổ sung thông tin về yếu tố liên quan.'
            row.prevention = 'Chưa bổ sung thông tin về phòng ngừa và chăm sóc.'
            row.aliases = list(dict.fromkeys([*(a for a in (row.aliases or []) if not a.startswith('vi:')), 'vi:' + title, normalize(title), normalize(source['title']), 'chapter:' + source['chapter_no'], 'kind:' + source['class_kind'], 'article-columns:v1']))
            if row.id in edits:
                edit = edits[row.id]
                for key in ['name','english_name','category','summary','details','risk_factors','prevention','published']:
                    setattr(row, key, edit[key])
            row.version += 1
            row.updated_at = now()
        db.flush()
        for row, original_source in pending:
            if source_data(row) != original_source:
                raise ValueError('Source verification failed')
            if row.details.lstrip().startswith('{'):
                raise ValueError('Article body still contains source JSON')
        return {'converted': len(pending), 'status': 'converted', 'backup': str(backup),
                'note': 'Missing clinical text explicitly marked for editorial completion; source provenance retained.'}

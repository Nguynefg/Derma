"""Source provenance stored in existing versioned documents, outside article text."""
import json
from sqlalchemy import select, cast, or_
from sqlalchemy.orm import object_session
from app.database.models import Disease, MedicalDocument, DocumentVersion, Text

SOURCE_PREFIX = 'library-source-'


def preload_sources(db, rows):
    targets = {row.id: row for row in rows if 'article-columns:v1' in (row.aliases or []) or any(a.startswith('merged-id:') for a in (row.aliases or []))}
    ids = list(targets)
    for offset in range(0, len(ids), 500):
        values = db.execute(select(MedicalDocument.disease_id, DocumentVersion.content).join(
            DocumentVersion, DocumentVersion.document_id == MedicalDocument.id
        ).where(MedicalDocument.disease_id.in_(ids[offset:offset + 500]),
                MedicalDocument.slug.startswith(SOURCE_PREFIX),
                DocumentVersion.version == MedicalDocument.version))
        for disease_id, content in values:
            targets[disease_id]._library_source = json.loads(content)['source']


def source_data(row):
    try:
        data = json.loads(row.details)
        if isinstance(data, dict) and 'class_kind' in data:
            return data
    except (ValueError, TypeError):
        pass
    cached = getattr(row, '_library_source', None)
    if cached is not None:
        return cached
    db = object_session(row)
    if db is None:
        raise ValueError('Source document requires an attached database session')
    content = db.scalar(select(DocumentVersion.content).join(
        MedicalDocument, MedicalDocument.id == DocumentVersion.document_id
    ).where(MedicalDocument.slug == SOURCE_PREFIX + str(row.id),
            DocumentVersion.version == MedicalDocument.version))
    if not content:
        raise ValueError('Missing original source document for library entry')
    data = json.loads(content)['source']
    row._library_source = data
    return data


def source_filter(field, value):
    marker = ('chapter:' if field == 'chapter_no' else 'kind:') + value
    return or_(
        Disease.category == 'ICD-11 ' + value if field == 'chapter_no' else
        Disease.details.contains('"class_kind":"' + value + '"', autoescape=True),
        Disease.details.contains('"' + field + '": "' + value + '"', autoescape=True),
        cast(Disease.aliases, Text).contains('"' + marker + '"', autoescape=True),
    )

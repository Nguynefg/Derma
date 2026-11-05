"""Versioned editorial content for imported entries, preserving their source records."""

import hashlib
import json
from sqlalchemy import select
from app.database.models import MedicalDocument, DocumentVersion, AuditLog, now

PREFIX = "library-editorial-"


def editorials(db, ids):
    if not ids:
        return {}
    if len(ids) > 500:
        result = {}
        for offset in range(0, len(ids), 500):
            result.update(editorials(db, ids[offset:offset + 500]))
        return result
    rows = db.execute(
        select(MedicalDocument, DocumentVersion)
        .join(DocumentVersion, DocumentVersion.document_id == MedicalDocument.id)
        .where(
            MedicalDocument.disease_id.in_(ids),
            MedicalDocument.slug.startswith(PREFIX),
            DocumentVersion.version == MedicalDocument.version,
        )
    )
    return {
        doc.disease_id: {
            **json.loads(version.content),
            "version": doc.version,
            "updated_at": doc.updated_at.isoformat(),
        }
        for doc, version in rows
    }


def imported_form(row, db, edits=None):
    from app.modules.library.icd_routes import item

    value = item(row)
    edit = (editorials(db, [row.id]) if edits is None else edits).get(row.id)
    result = {
        "id": row.id,
        "slug": row.slug,
        "code": f"BL{row.id:06d}",
        "name": value["title"][:120],
        "english_name": value["original_title"][:120],
        "category": value["group_name"][:60],
        "summary": "",
        "details": "",
        "risk_factors": "",
        "prevention": "",
        "published": False,
        "review_status": "pending",
        "version": row.version,
        "updated_at": row.updated_at.isoformat(),
        "symptoms": [],
        "references": [
            {"title": value["original_title"][:200], "url": value["source_url"], "slug": "source"}
        ],
    }
    if edit:
        result.update(
            {
                key: edit[key]
                for key in [
                    "name",
                    "english_name",
                    "category",
                    "summary",
                    "details",
                    "risk_factors",
                    "prevention",
                    "published",
                    "version",
                    "updated_at",
                ]
            }
        )
        result["review_status"] = "editor_reviewed"
        result["symptoms"] = [{"id": s} for s in edit["symptom_ids"]]
        result["references"] = [
            {"title": edit["source_title"], "url": edit["source_url"], "slug": "editor-content"}
        ]
    elif 'article-columns:v1' in (row.aliases or []):
        for key in ['name', 'english_name', 'category', 'summary', 'details', 'risk_factors', 'prevention', 'published']:
            result[key] = getattr(row, key)
    return result


def save_editorial(row, body, db, admin):
    before = editorials(db, [row.id]).get(row.id)
    doc = db.scalar(select(MedicalDocument).where(MedicalDocument.slug == PREFIX + str(row.id)))
    if not doc:
        doc = MedicalDocument(slug=PREFIX + str(row.id), disease_id=row.id, version=1)
        db.add(doc)
    else:
        doc.version += 1
    doc.title = body.name
    doc.publisher = "Ban biên tập thư viện"
    doc.source_url = body.source_url
    doc.usage_note = body.category
    doc.published = body.published
    doc.updated_at = now()
    if 'article-columns:v1' in (row.aliases or []):
        from app.modules.library.catalog import normalize
        for key in ['name', 'english_name', 'category', 'summary', 'details', 'risk_factors', 'prevention', 'published']:
            setattr(row, key, getattr(body, key))
        row.aliases = list(dict.fromkeys([
            *(a for a in row.aliases if not a.startswith('vi:')),
            'vi:' + body.name, normalize(body.name), normalize(body.english_name),
        ]))
        row.version += 1
        row.updated_at = doc.updated_at
    db.flush()
    content = json.dumps(body.model_dump(), ensure_ascii=False)
    db.add(
        DocumentVersion(
            document_id=doc.id,
            version=doc.version,
            title=doc.title,
            publisher=doc.publisher,
            source_url=doc.source_url,
            usage_note=doc.usage_note,
            content=content,
            checksum=hashlib.sha256(content.encode()).hexdigest(),
            editor_id=admin.id,
        )
    )
    db.add(
        AuditLog(
            actor_id=admin.id,
            action="library_edit",
            entity_id=str(row.id),
            snapshot={"before": before, "input": body.model_dump()},
        )
    )
    db.commit()
    return imported_form(row, db)

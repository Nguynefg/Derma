import hashlib
from app.modules.library.identifiers import find_record
from sqlalchemy import select
from app.database.connection import SessionLocal, MedicalDocument, DocumentVersion, Disease, Reference


def seed_documents():
    with SessionLocal() as db:
        # Upgrade existing MVP installations once, without re-creating hidden documents.
        if db.scalar(select(MedicalDocument.id).limit(1)):
            return
        for ref in db.scalars(select(Reference)).all():
            disease = find_record(db, Disease, ref.disease_id)
            content = disease.summary + "\n\n" + disease.details + "\n\n" + disease.risk_factors
            document = MedicalDocument(
                slug=ref.slug,
                disease_id=disease.id,
                title=ref.title,
                publisher=ref.publisher,
                source_url=ref.url,
                usage_note=ref.usage_note,
                published=disease.published,
                version=1,
            )
            db.add(document)
            db.flush()
            db.add(
                DocumentVersion(
                    document_id=document.id,
                    version=1,
                    title=document.title,
                    publisher=document.publisher,
                    source_url=document.source_url,
                    usage_note=document.usage_note,
                    content=content,
                    checksum=hashlib.sha256(content.encode()).hexdigest(),
                    editor_id=None,
                )
            )
        db.commit()


def serialize_document(doc, db, include_content=False):
    version = db.scalar(
        select(DocumentVersion).where(
            DocumentVersion.document_id == doc.id, DocumentVersion.version == doc.version
        )
    )
    value = {
        key: getattr(doc, key)
        for key in [
            "id",
            "disease_id",
            "title",
            "publisher",
            "source_url",
            "usage_note",
            "published",
            "version",
        ]
    }
    value["updated_at"] = doc.updated_at.isoformat()
    value["checksum"] = version.checksum if version else None
    if include_content:
        value["content"] = version.content if version else ""
    return value

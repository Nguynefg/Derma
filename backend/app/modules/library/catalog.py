"""Keyword normalization and public disease serialization."""

import unicodedata
from sqlalchemy import select
from app.database.connection import Symptom, DiseaseSymptom, Reference
from app.modules.library.specialties import specialty_for, supports_photo


def normalize(text):
    text = text.lower().replace("đ", "d")
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def preload_disease_relations(db, rows):
    targets = {row.id: row for row in rows}
    for row in targets.values():
        row._catalog_symptoms = []
        row._catalog_references = []
    ids = list(targets)
    for offset in range(0, len(ids), 500):
        batch = ids[offset:offset+500]
        for disease_id, symptom in db.execute(
            select(DiseaseSymptom.disease_id, Symptom)
            .join(Symptom, DiseaseSymptom.symptom_id == Symptom.id)
            .where(DiseaseSymptom.disease_id.in_(batch))
        ):
            targets[disease_id]._catalog_symptoms.append(symptom)
        for reference in db.scalars(select(Reference).where(Reference.disease_id.in_(batch))):
            targets[reference.disease_id]._catalog_references.append(reference)


def serialize_disease(disease, db, icd_links=None):
    if icd_links is None:
        from app.modules.library.icd_links import article_icd_links

        icd_links = article_icd_links(db)
    symptoms = getattr(disease, '_catalog_symptoms', None)
    if symptoms is None:
        symptoms = db.scalars(
            select(Symptom)
            .join(DiseaseSymptom, DiseaseSymptom.symptom_id == Symptom.id)
            .where(DiseaseSymptom.disease_id == disease.id)
        ).all()
    refs = getattr(disease, '_catalog_references', None)
    if refs is None:
        refs = db.scalars(select(Reference).where(Reference.disease_id == disease.id)).all()
    return {
        **{
            key: getattr(disease, key)
            for key in [
                "id",
                "name",
                "english_name",
                "category",
                "summary",
                "details",
                "risk_factors",
                "prevention",
                "aliases",
                "published",
                "review_status",
                "version",
            ]
        },
        "code": f"BL{disease.id:06d}",
        "icd": icd_links.get(disease.id),
        "specialty": specialty_for(disease.category),
        "photo_supported": supports_photo(disease),
        "slug": disease.slug,
        "updated_at": disease.updated_at.isoformat(),
        "symptoms": [{"id": s.id, "name": s.name} for s in symptoms],
        "references": [
            {
                key: getattr(r, key)
                for key in ["id", "slug", "title", "publisher", "url", "accessed_at", "usage_note"]
            }
            for r in refs
        ],
    }

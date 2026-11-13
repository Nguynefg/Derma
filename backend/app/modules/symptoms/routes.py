from app.modules.library.library_source import source_filter, preload_sources
"""Library HTTP endpoints."""

import re
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Literal
from app.modules.library.identifiers import find_record
from sqlalchemy import select, func, cast, or_, and_, false, case
from app.database.models import Text, MedicalDocument
from sqlalchemy.orm import Session, load_only
from app.database.connection import get_db, Disease, Symptom, DiseaseSymptom
from app.core.schemas import SymptomSearch
from app.modules.library.catalog import normalize, serialize_disease, preload_disease_relations
from app.modules.library.specialties import specialty_for, DERMATOLOGY_CATEGORIES, GENERAL_SPECIALTIES
from app.modules.library.icd_routes import item as icd_item
from app.modules.library.icd_links import article_icd_links
from app.modules.library.library_editorial import editorials, PREFIX
from app.modules.library.library_order import alphabetical
from app.modules.library.library_pagination import article_page

router = APIRouter()

ICD_SPECIALTIES = {
    "Da liễu": ["14"],
    "Hô hấp": ["12"],
    "Tiêu hóa": ["13"],
    "Tim mạch": ["11"],
    "Nội tiết": ["05"],
    "Thần kinh": ["08"],
    "Cơ xương khớp": ["15"],
    "Thận & tiết niệu": ["16"],
    "Tai mũi họng": ["10"],
}


@router.get("/api/v1/symptoms")
def symptoms(db: Session = Depends(get_db)):
    groups = {}
    for symptom_id, category in db.execute(
        select(DiseaseSymptom.symptom_id, Disease.category)
        .join(Disease, Disease.id == DiseaseSymptom.disease_id)
        .where(Disease.published == True)
    ):
        groups.setdefault(symptom_id, set()).add(specialty_for(category))
    return [
        {"id": s.id, "slug": s.slug, "name": s.name, "specialties": sorted(groups.get(s.id, set()))}
        for s in db.scalars(select(Symptom).order_by(Symptom.name))
    ]


@router.post("/api/v1/search/symptoms")
def symptom_search(body: SymptomSearch, db: Session = Depends(get_db)):
    selected = [find_record(db, Symptom, s.id) for s in body.symptoms]
    known = {s.id: s.name for s in db.scalars(select(Symptom))}
    if any(s is None for s in selected):
        raise HTTPException(422, "Có triệu chứng không nằm trong danh mục.")
    if len({s.id for s in selected}) != len(body.symptoms):
        raise HTTPException(422, "Triệu chứng bị lặp.")
    present = {
        row.id for choice, row in zip(body.symptoms, selected) if choice.presence == "present"
    }
    if not present:
        raise HTTPException(422, "Hãy chọn ít nhất một triệu chứng đang có.")
    result = []
    links = article_icd_links(db)
    matching_ids = select(DiseaseSymptom.disease_id).where(
        DiseaseSymptom.symptom_id.in_(present)
    )
    rows = list(db.scalars(select(Disease).where(
        Disease.published == True, Disease.id.in_(matching_ids)
    )))
    if body.specialty:
        rows = [row for row in rows if specialty_for(row.category) == body.specialty]
    preload_disease_relations(db, rows)
    for row in rows:
        linked = {symptom.id for symptom in row._catalog_symptoms}
        matched = sorted(linked & present)
        if matched:
            result.append(
                {
                    **serialize_disease(row, db, links),
                    "matched_symptoms": [known[s] for s in matched],
                    "match_count": len(matched),
                }
            )
    result.sort(key=lambda r: (-r["match_count"], r["name"]))
    return {
        "items": result,
        "method": "topic-overlap-v1",
        "notice": "Chủ đề có nhắc đến triệu chứng đã chọn. Đây không phải xếp hạng xác suất mắc bệnh.",
    }

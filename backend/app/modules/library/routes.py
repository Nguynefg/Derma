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


@router.get("/api/v1/library/search")
def combined_library(
    q: str = Query("", max_length=300),
    content_type: Literal["all", "article", "icd"] = "all",
    specialty: str = Query("", max_length=60),
    category: str = Query("", max_length=60),
    symptom: str = Query("", max_length=50),
    chapter: str = Query("", max_length=10),
    sort: Literal["name", "updated"] = "name",
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    db: Session = Depends(get_db),
):
    is_icd = Disease.review_status == "icd_classification"
    is_article = and_(Disease.published == True, Disease.review_status != "icd_classification")
    links = article_icd_links(db)
    linked_ids = [value["id"] for value in links.values()]
    query = select(Disease).where(or_(is_icd, is_article))
    if linked_ids:
        query = query.where(~Disease.id.in_(linked_ids))
    if content_type == "article":
        query = query.where(is_article)
    if content_type == "icd":
        query = query.where(or_(is_icd, Disease.id.in_(list(links))))
    if q.strip():
        tokens = re.findall(r"\w+", normalize(q))
        articles = db.scalars(select(Disease).options(load_only(
            Disease.id, Disease.name, Disease.english_name, Disease.summary, Disease.aliases
        )).where(is_article)).all()
        matching = []
        for article in articles:
            words = set(re.findall(r"\w+", normalize(" ".join([
                article.name, article.english_name, article.summary, *article.aliases
            ]))))
            if tokens and all(token in words for token in tokens):
                matching.append(article.id)
        icd_match = is_icd
        for token in q.lower().split():
            # ASCII keywords already equal their normalized form. Avoid applying
            # LOWER/LIKE to the same large JSON column twice per row and token.
            aliases = func.lower(cast(Disease.aliases, Text))
            alias_terms = dict.fromkeys([token, normalize(token)])
            icd_match = and_(
                icd_match,
                or_(
                    func.lower(Disease.name).contains(token, autoescape=True),
                    func.lower(Disease.summary).contains(token, autoescape=True),
                    *(aliases.contains(term, autoescape=True) for term in alias_terms),
                ),
            )
        # Only linked IDs are needed for merge propagation; never materialize
        # every matching imported ID or send them back as thousands of parameters.
        matching_icd_ids = set(db.scalars(select(Disease.id).where(
            icd_match, Disease.id.in_(linked_ids)
        ))) if linked_ids else set()
        edited_query = select(MedicalDocument.disease_id).where(
            MedicalDocument.slug.startswith(PREFIX), MedicalDocument.published == True
        )
        for token in q.lower().split():
            edited_query = edited_query.where(
                func.lower(MedicalDocument.title).contains(token, autoescape=True)
            )
        matching.extend(aid for aid, link in links.items() if link["id"] in matching_icd_ids)
        query = query.where(or_(Disease.id.in_(matching), Disease.id.in_(edited_query), icd_match))
    if specialty:
        article_match = (
            Disease.category.in_(DERMATOLOGY_CATEGORIES)
            if specialty == "Da liễu"
            else Disease.category == specialty
        )
        icd_categories = ["ICD-11 " + c for c in ICD_SPECIALTIES.get(specialty, [])]
        icd_match = or_(false(), *[source_filter("chapter_no", c) for c in ICD_SPECIALTIES.get(specialty, [])])
        if specialty == "Khác":
            article_match = ~Disease.category.in_(DERMATOLOGY_CATEGORIES | GENERAL_SPECIALTIES)
            icd_match = ~or_(*[source_filter("chapter_no", c) for codes in ICD_SPECIALTIES.values() for c in codes])
        query = query.where(or_(and_(is_article, article_match), and_(is_icd, icd_match)))
    if category:
        query = query.where(
            or_(
                Disease.category == category,
                Disease.id.in_(
                    select(MedicalDocument.disease_id).where(
                        MedicalDocument.slug.startswith(PREFIX),
                        MedicalDocument.published == True,
                        MedicalDocument.usage_note == category,
                    )
                ),
            )
        )
    if chapter:
        query = query.where(
            or_(
                and_(is_icd, source_filter("chapter_no", chapter)),
                Disease.id.in_([aid for aid, link in links.items() if link["chapter"] == chapter]),
            )
        )
    if symptom:
        row = find_record(db, Symptom, symptom)
        if not row:
            raise HTTPException(422, "Triệu chứng không hợp lệ.")
        query = query.where(
            Disease.id.in_(
                select(DiseaseSymptom.disease_id).where(DiseaseSymptom.symptom_id == row.id)
            )
        )
    counts = query.with_only_columns(
        Disease.id.label('id'), Disease.review_status.label('review_status')
    ).subquery()
    total, article_count = db.execute(select(
        func.count(), func.coalesce(func.sum(case(
            (counts.c.review_status != 'icd_classification', 1), else_=0
        )), 0)
    ).select_from(counts)).one()
    ordering = (
        [Disease.updated_at.desc(), Disease.id] if sort == "updated" else [*alphabetical(db, Disease.name), Disease.id]
    )
    rows = article_page(db, query, ordering, page, page_size)
    items = []
    preload_sources(db, rows)
    preload_disease_relations(db, [r for r in rows if r.review_status != 'icd_classification'])
    edits = editorials(db, [row.id for row in rows])
    for row in rows:
        if row.review_status == "icd_classification":
            value = icd_item(row, edits.get(row.id))
            items.append(
                {
                    "id": row.id,
                    "type": "icd",
                    "title": value["title"],
                    "code": value["code"],
                    "category": value["group_name"],
                    "summary": value.get("article_content", {}).get("summary")
                    or "Thông tin tóm tắt đang được bổ sung.",
                    "icd": value,
                }
            )
        else:
            value = serialize_disease(row, db, links)
            items.append(
                {
                    "id": row.id,
                    "type": "article",
                    "title": row.name,
                    "code": links[row.id]["code"] if row.id in links else value["code"],
                    "category": row.category,
                    "summary": row.summary,
                    "article": value,
                }
            )
    return {
        "items": items,
        "total": total,
        "article_count": article_count,
        "icd_count": total - article_count,
        "page": page,
        "page_size": page_size,
    }


@router.get("/api/v1/diseases")
def diseases(q: str = "", category: str = "", specialty: str = "", db: Session = Depends(get_db)):
    if len(q) > 300:
        raise HTTPException(422, "Từ khóa quá dài.")
    query = select(Disease).where(Disease.published == True)
    if category:
        query = query.where(Disease.category == category)
    rows = db.scalars(query.order_by(*alphabetical(db, Disease.name), Disease.id)).all()
    tokens = re.findall(r"\w+", normalize(q))
    result = []
    links = article_icd_links(db)
    preload_disease_relations(db, rows)
    for row in rows:
        if category and row.category != category:
            continue
        if specialty and specialty_for(row.category) != specialty:
            continue
        # The initial page has no keyword: do not tokenize every article.
        words = set(re.findall(r"\w+", normalize(" ".join([
            row.name, row.english_name, row.summary, *row.aliases
        ])))) if tokens else set()
        if all(token in words for token in tokens):
            result.append(serialize_disease(row, db, links))
    return {"items": result, "total": len(result), "method": "keyword-v1"}


@router.get("/api/v1/diseases/{disease_id}")
def disease_detail(disease_id: str, db: Session = Depends(get_db)):
    row = find_record(db, Disease, disease_id)
    if not row or not row.published:
        raise HTTPException(404, "Không tìm thấy bài viết.")
    return serialize_disease(row, db)



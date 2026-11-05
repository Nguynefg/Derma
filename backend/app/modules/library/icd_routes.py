from app.modules.library.library_source import source_data, source_filter, preload_sources
"""Paginated public classification lookup, without publishing draft clinical articles."""

import json
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, cast, or_
from sqlalchemy.orm import Session
from app.database.connection import get_db, Disease, MedicalDocument, DocumentVersion
from app.database.models import Text
from app.modules.library.icd_links import article_icd_links
from app.modules.library.icd_chapters import CHAPTER_TITLES_VI
from app.modules.library.icd_translation import translated_title
from app.modules.library.catalog import normalize
from app.modules.library.library_groups import specific_group, group_title
from app.modules.library.library_editorial import editorials
from app.modules.library.library_order import alphabetical
from app.modules.library.library_pagination import article_page

router = APIRouter(prefix="/api/v1/icd", tags=["Thư viện sức khỏe"])
KINDS = {"chapter": "Nhóm chủ đề", "block": "Nhóm chủ đề", "category": "Nội dung thư viện"}


def group_name(chapter):
    return {
        "25": "Thông tin sức khỏe đặc biệt",
        "26": "Y học cổ truyền",
        "V": "Đánh giá chức năng",
        "X": "Giải phẫu, hoạt chất và thông tin bổ sung",
    }.get(chapter, CHAPTER_TITLES_VI.get(chapter, "Kiến thức sức khỏe"))


def base_query():
    return select(Disease).where(Disease.review_status == "icd_classification")


def item(row, edit=None):
    data = source_data(row)
    result = {
        "id": row.id,
        "title": (
            CHAPTER_TITLES_VI.get(data["chapter_no"], data["title"])
            if data["class_kind"] == "chapter"
            else translated_title(row, data["title"])
        ),
        "original_title": data["title"],
        "chapter_title": group_name(data["chapter_no"]),
        "group_name": specific_group(data) or group_name(data["chapter_no"]),
        "code": data.get("code"),
        "kind": data["class_kind"],
        "kind_name": KINDS.get(data["class_kind"], data["class_kind"]),
        "chapter": data["chapter_no"],
        "uri": data["linearization_uri"],
        "parent_uri": data.get("parent_uri"),
        "source_url": data["browser_url"],
    }
    if 'article-columns:v1' in (row.aliases or []) or any(a.startswith('merged-id:') for a in (row.aliases or [])):
        from app.modules.library.icd_terminology import medical_title
        result.update(title=medical_title(data['title'], next((a[3:] for a in row.aliases if a.startswith('vi:')), row.name)),
            group_name=specific_group(data) or group_title(row.category),
            article_content={key: getattr(row, key) for key in ['summary', 'details', 'risk_factors', 'prevention']})
    if edit and edit["published"]:
        result.update(
            title=edit["name"],
            group_name=edit["category"],
            article_content={
                key: edit[key] for key in ["summary", "details", "risk_factors", "prevention"]
            },
            editorial_source={"title": edit["source_title"], "url": edit["source_url"]},
        )
    return result


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    total = db.scalar(
        select(func.count())
        .select_from(Disease)
        .where(Disease.review_status == "icd_classification")
    )
    chapters = []
    rows = db.scalars(
        base_query().where(source_filter("class_kind", "chapter"))
    ).all()
    for row in rows:
        value = item(row)
        chapters.append({"code": value["chapter"], "title": value["group_name"]})
    # Chapter headings can be intentionally removed while their disease entries
    # remain. Derive available filters from the retained source markers instead.
    if not chapters:
        available = set()
        for aliases in db.scalars(select(Disease.aliases).where(Disease.review_status == 'icd_classification')):
            available.update(a[8:] for a in (aliases or []) if isinstance(a,str) and a.startswith('chapter:'))
        chapters = [{'code': code, 'title': group_name(code)} for code in sorted(available)]
    chapters = sorted({c["code"]: c for c in chapters}.values(), key=lambda c: c["code"])
    return {
        "total": total,
        "merged_articles": len(article_icd_links(db)),
        "chapters": chapters,
        "language": "en",
        "chapter_language": "vi",
        "notice": "Thư viện sức khỏe gồm bệnh lý, triệu chứng, giải phẫu và các thông tin bổ sung. Nội dung dùng để tham khảo.",
    }


@router.get("")
def search(
    q: str = Query("", max_length=200),
    chapter: str = Query("", max_length=10),
    kind: Literal["", "chapter", "block", "category"] = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = base_query()
    for token in q.strip().lower().split():
        query = query.where(
            or_(
                func.lower(Disease.name).contains(token, autoescape=True),
                func.lower(Disease.summary).contains(token, autoescape=True),
                func.lower(cast(Disease.aliases, Text)).contains(token, autoescape=True),
                func.lower(cast(Disease.aliases, Text)).contains(normalize(token), autoescape=True),
            )
        )
    if chapter:
        query = query.where(source_filter("chapter_no", chapter))
    if kind:
        query = query.where(
            source_filter("class_kind", kind)
        )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = article_page(db, query, [*alphabetical(db, Disease.name), Disease.id], page, page_size)
    preload_sources(db, rows)
    edits = editorials(db, [row.id for row in rows])
    return {
        "items": [item(row, edits.get(row.id)) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{entity_id}")
def detail(entity_id: int, db: Session = Depends(get_db)):
    from app.modules.library.identifiers import find_record
    row = find_record(db, Disease, entity_id)
    merged_public = row is not None and row.published and any(a.startswith('merged-id:') for a in (row.aliases or []))
    if not row or (row.review_status != "icd_classification" and not merged_public):
        raise HTTPException(404, "Không tìm thấy nội dung thư viện.")
    result = item(row, editorials(db, [row.id]).get(row.id))
    result["metadata"] = source_data(row)
    result["chapters"] = []
    docs = db.execute(
        select(MedicalDocument.id, MedicalDocument.title, DocumentVersion.content)
        .join(DocumentVersion, DocumentVersion.document_id == MedicalDocument.id)
        .where(
            MedicalDocument.slug.startswith(row.slug.rsplit("-", 1)[0] + "-chapter-"),
            MedicalDocument.slug.endswith("-" + result["chapter"]),
            DocumentVersion.version == 1,
        )
    ).all()
    result["chapters"] = [{"id": d.id, "title": d.title, "content": d.content} for d in docs]
    return result

"""Admin HTTP endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Literal
from pydantic import BaseModel, Field
from app.modules.library.identifiers import find_record
from sqlalchemy import select, delete, func, update, and_, or_, cast, case
from app.database.models import Text
from sqlalchemy.orm import Session
from app.database.connection import (
    get_db,
    now,
    User,
    Disease,
    Symptom,
    DiseaseSymptom,
    Reference,
    History,
    AuditLog,
    MedicalDocument,
    DocumentVersion,
    LoginSession,
)
from app.modules.library.documents import serialize_document
from app.core.schemas import DiseaseEdit, DocumentEdit
from app.modules.auth.dependencies import get_admin
from app.modules.library.catalog import serialize_disease, preload_disease_relations
from app.modules.library.icd_links import article_icd_links
from app.modules.library.library_editorial import PREFIX, editorials, imported_form, save_editorial
from app.modules.library.library_source import SOURCE_PREFIX, preload_sources
from app.modules.library.library_order import alphabetical
from app.modules.library.library_pagination import article_page

router = APIRouter()


class AccountEdit(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    role: Literal["user", "admin"]


@router.get("/api/v1/admin/users")
def accounts(db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "created_at": u.created_at.isoformat(),
        }
        for u in db.scalars(select(User).order_by(User.created_at.desc()))
    ]


@router.put("/api/v1/admin/users/{user_id}")
def edit_account(
    user_id: int, body: AccountEdit, db: Session = Depends(get_db), admin: User = Depends(get_admin)
):
    row = db.get(User, user_id)
    if not row:
        raise HTTPException(404, "Không tìm thấy tài khoản.")
    if not body.name.strip():
        raise HTTPException(422, "Tên hiển thị không được để trống.")
    if row.id == admin.id and body.role != "admin":
        raise HTTPException(422, "Không thể tự gỡ quyền quản trị của tài khoản đang sử dụng.")
    before = {"name": row.name, "role": row.role}
    changed_role = row.role != body.role
    row.name, row.role = body.name.strip(), body.role
    if changed_role:
        db.execute(delete(LoginSession).where(LoginSession.user_id == row.id))
    db.add(
        AuditLog(
            actor_id=admin.id,
            action="account_update",
            entity_id=str(row.id),
            snapshot={"before": before, "after": {"name": row.name, "role": row.role}},
        )
    )
    db.commit()
    return {"id": row.id, "name": row.name, "email": row.email, "role": row.role}


@router.get("/api/v1/admin/diseases")
def admin_diseases(db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    links = article_icd_links(db)
    return [
        serialize_disease(d, db, links)
        for d in db.scalars(
            select(Disease)
            .where(Disease.review_status != "icd_classification")
            .order_by(*alphabetical(db, Disease.name), Disease.id)
        )
    ]


@router.get("/api/v1/admin/library")
def admin_library(
    q: str = Query("", max_length=300),
    status: Literal["", "pending", "published", "draft"] = "",
    category: str = Query("", max_length=60),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin),
):
    from app.modules.library.icd_routes import group_name
    from app.modules.library.catalog import normalize

    links = article_icd_links(db)
    imported = Disease.review_status == "icd_classification"
    joined = and_(MedicalDocument.disease_id == Disease.id, MedicalDocument.slug.startswith(PREFIX))
    query = select(Disease).outerjoin(MedicalDocument, joined)
    if links:
        query = query.where(~Disease.id.in_([v["id"] for v in links.values()]))
    total_all = db.scalar(select(func.count()).select_from(query.subquery()))
    if status == "pending":
        query = query.where(imported, MedicalDocument.id.is_(None))
    elif status:
        published = status == "published"
        query = query.where(
            or_(
                and_(~imported, Disease.published == published),
                and_(
                    imported,
                    MedicalDocument.id.is_not(None),
                    MedicalDocument.published == published,
                ),
            )
        )
    if category:
        query = query.where(
            or_(Disease.category == category, MedicalDocument.usage_note == category)
        )
    for token in q.strip().lower().split():
        code_id = int(token[2:]) if token.startswith("bl") and token[2:].isdigit() else -1
        query = query.where(
            or_(
                func.lower(Disease.name).contains(token, autoescape=True),
                func.lower(Disease.english_name).contains(token, autoescape=True),
                func.lower(cast(Disease.aliases, Text)).contains(normalize(token), autoescape=True),
                func.lower(MedicalDocument.title).contains(token, autoescape=True),
                Disease.id == code_id,
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = article_page(db, query, [
            *alphabetical(db, case((MedicalDocument.id.is_not(None), MedicalDocument.title), else_=Disease.name)),
            Disease.id,
        ], page, page_size)
    preload_sources(db, rows)
    preload_disease_relations(db, [r for r in rows if r.review_status != 'icd_classification'])
    edits = editorials(db, [r.id for r in rows])
    items = []
    for row in rows:
        value = (
            imported_form(row, db, edits)
            if row.review_status == "icd_classification"
            else serialize_disease(row, db, links)
        )
        items.append(
            {
                k: value[k]
                for k in [
                    "id",
                    "code",
                    "name",
                    "english_name",
                    "category",
                    "published",
                    "review_status",
                    "version",
                ]
            }
        )
    categories = set(db.scalars(select(Disease.category).distinct()))
    categories.update(
        db.scalars(
            select(MedicalDocument.usage_note)
            .where(MedicalDocument.slug.startswith(PREFIX))
            .distinct()
        )
    )
    return {
        "items": items,
        "total": total,
        "total_all": total_all,
        "page": page,
        "page_size": page_size,
        "categories": [
            {"value": c, "label": group_name(c[7:]) if c.startswith("ICD-11 ") else c}
            for c in sorted(categories)
        ],
    }


@router.get("/api/v1/admin/library/{disease_id}")
def admin_library_detail(
    disease_id: str, db: Session = Depends(get_db), admin: User = Depends(get_admin)
):
    row = find_record(db, Disease, disease_id)
    if not row:
        raise HTTPException(404, "Không tìm thấy nội dung.")
    return (
        imported_form(row, db)
        if row.review_status == "icd_classification"
        else serialize_disease(row, db)
    )


def apply_edit(row, body, db, admin, action):
    selected = [find_record(db, Symptom, value) for value in body.symptom_ids]
    valid_ids = {str(s.id) for s in db.scalars(select(Symptom))} | {
        s.slug for s in db.scalars(select(Symptom))
    }
    if not set(body.symptom_ids) <= valid_ids:
        raise HTTPException(422, "Triệu chứng không hợp lệ.")
    if row.review_status == "icd_classification":
        return save_editorial(row, body, db, admin)
    before = serialize_disease(row, db) if action == "update" else None
    for key, value in body.model_dump(
        exclude={"symptom_ids", "source_title", "source_url"}
    ).items():
        setattr(row, key, value)
    row.review_status = "editor_reviewed"
    row.updated_at = now()
    if action == "update":
        row.version += 1
    db.add(row)
    db.flush()
    db.execute(delete(DiseaseSymptom).where(DiseaseSymptom.disease_id == row.id))
    for symptom_id in {s.id for s in selected}:
        db.add(DiseaseSymptom(disease_id=row.id, symptom_id=symptom_id))
    # The editable source is additional; preserve seeded provenance.
    ref_id = f"editor-{row.id}"
    ref = find_record(db, Reference, ref_id)
    if not ref:
        ref = Reference(
            slug=ref_id,
            disease_id=row.id,
            publisher="Nguồn do biên tập viên cung cấp",
            usage_note="Biên tập nội dung không tương đương thẩm định lâm sàng.",
        )
    ref.title, ref.url, ref.accessed_at = (
        body.source_title,
        body.source_url,
        now().date().isoformat(),
    )
    db.add(ref)
    # Keep an immutable snapshot for ordinary articles too. This document is
    # private: JSON revision snapshots must not enter the public retrieval corpus.
    import hashlib
    import json

    revision = db.scalar(select(MedicalDocument).where(
        MedicalDocument.slug == f"article-revision-{row.id}"
    ))
    if revision is None:
        revision = MedicalDocument(slug=f"article-revision-{row.id}", disease_id=row.id)
        db.add(revision)
    revision.title = row.name
    revision.publisher = "Ban biên tập thư viện"
    revision.source_url = body.source_url
    revision.usage_note = "Lịch sử biên tập bài viết"
    revision.published = False
    revision.version = row.version
    revision.updated_at = row.updated_at
    db.flush()
    content = json.dumps(body.model_dump(), ensure_ascii=False, sort_keys=True)
    db.add(DocumentVersion(
        document_id=revision.id, version=row.version, title=revision.title,
        publisher=revision.publisher, source_url=revision.source_url,
        usage_note=revision.usage_note, content=content,
        checksum=hashlib.sha256(content.encode()).hexdigest(), editor_id=admin.id,
    ))
    db.add(
        AuditLog(
            actor_id=admin.id,
            action=action,
            entity_id=str(row.id),
            snapshot={"before": before, "input": body.model_dump()},
        )
    )
    db.commit()
    return serialize_disease(row, db)


@router.post("/api/v1/admin/diseases", status_code=201)
def create_disease(
    body: DiseaseEdit, db: Session = Depends(get_db), admin: User = Depends(get_admin)
):
    row = Disease(aliases=[], version=1)
    return apply_edit(row, body, db, admin, "create")


@router.put("/api/v1/admin/diseases/{disease_id}")
def edit_disease(
    disease_id: str,
    body: DiseaseEdit,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin),
):
    row = find_record(db, Disease, disease_id)
    if not row:
        raise HTTPException(404, "Không tìm thấy bài viết.")
    return apply_edit(row, body, db, admin, "update")


@router.get("/api/v1/admin/statistics")
def statistics(db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    return {
        "users": db.scalar(select(func.count()).select_from(User)),
        "articles": db.scalar(select(func.count()).select_from(Disease)),
        "saved_searches": db.scalar(select(func.count()).select_from(History)),
        "edits": db.scalar(select(func.count()).select_from(AuditLog)),
    }


@router.get("/api/v1/admin/audit-logs")
def audits(db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    return [
        {
            "id": r.id,
            "action": r.action,
            "entity_id": r.entity_id,
            "created_at": r.created_at.isoformat(),
        }
        for r in db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(50))
    ]


@router.get("/api/v1/admin/documents")
def admin_documents(db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    return [
        serialize_document(doc, db, True)
        for doc in db.scalars(
            select(MedicalDocument)
            .where(~MedicalDocument.slug.startswith(PREFIX), ~MedicalDocument.slug.startswith(SOURCE_PREFIX))
            .order_by(MedicalDocument.title)
        )
    ]


@router.get("/api/v1/admin/documents-page")
def admin_documents_page(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin),
):
    visible = (~MedicalDocument.slug.startswith(PREFIX), ~MedicalDocument.slug.startswith(SOURCE_PREFIX))
    total = db.scalar(select(func.count()).select_from(MedicalDocument).where(*visible)) or 0
    documents = db.scalars(select(MedicalDocument).where(*visible)
                           .order_by(MedicalDocument.title, MedicalDocument.id)
                           .offset((page - 1) * page_size).limit(page_size))
    return {"items": [serialize_document(doc, db, True) for doc in documents],
            "total": total, "page": page, "page_size": page_size}


@router.get("/api/v1/admin/documents/{document_id}/versions")
def document_versions(
    document_id: str, db: Session = Depends(get_db), admin: User = Depends(get_admin)
):
    if not find_record(db, MedicalDocument, document_id):
        raise HTTPException(404, "Không tìm thấy tài liệu.")
    return [
        {
            k: getattr(v, k)
            for k in [
                "id",
                "version",
                "title",
                "publisher",
                "source_url",
                "usage_note",
                "content",
                "checksum",
            ]
        }
        for v in db.scalars(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version.desc())
        )
    ]


def save_document(body, db, admin, document_id=None):
    import hashlib

    if not find_record(db, Disease, body.disease_id):
        raise HTTPException(422, "Chủ đề liên kết không tồn tại.")
    doc = find_record(db, MedicalDocument, document_id) if document_id else None
    if doc and doc.slug.startswith(SOURCE_PREFIX):
        raise HTTPException(422, "Tài liệu nguồn được bảo toàn; hãy sửa nội dung trong mục biên tập bài viết.")
    if document_id and not doc:
        raise HTTPException(404, "Không tìm thấy tài liệu.")
    fields = body.model_dump(exclude={"content", "expected_version"})
    fields["disease_id"] = find_record(db, Disease, body.disease_id).id
    before = serialize_document(doc, db, True) if doc else None
    if doc:
        if body.expected_version is None:
            raise HTTPException(422, "Cần gửi phiên bản đang biên tập.")
        changed = db.execute(
            update(MedicalDocument)
            .where(MedicalDocument.id == doc.id, MedicalDocument.version == body.expected_version)
            .values(**fields, version=body.expected_version + 1, updated_at=now())
        )
        if changed.rowcount != 1:
            db.rollback()
            raise HTTPException(
                409, "Tài liệu đã được thay đổi. Tải lại trước khi lưu để tránh ghi đè."
            )
        db.refresh(doc)
    else:
        doc = MedicalDocument(**fields, version=1)
        db.add(doc)
        db.flush()
    db.add(
        DocumentVersion(
            document_id=doc.id,
            version=doc.version,
            title=doc.title,
            publisher=doc.publisher,
            source_url=doc.source_url,
            usage_note=doc.usage_note,
            content=body.content,
            checksum=hashlib.sha256(body.content.encode()).hexdigest(),
            editor_id=admin.id,
        )
    )
    db.add(
        AuditLog(
            actor_id=admin.id,
            action="document_update" if document_id else "document_create",
            entity_id=str(doc.id),
            snapshot={"before": before, "input": body.model_dump()},
        )
    )
    db.commit()
    return serialize_document(doc, db, True)


@router.post("/api/v1/admin/documents", status_code=201)
def create_document(
    body: DocumentEdit, db: Session = Depends(get_db), admin: User = Depends(get_admin)
):
    return save_document(body, db, admin)


@router.put("/api/v1/admin/documents/{document_id}")
def edit_document(
    document_id: str,
    body: DocumentEdit,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin),
):
    return save_document(body, db, admin, document_id)

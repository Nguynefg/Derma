"""Images HTTP endpoints."""

from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from app.modules.library.identifiers import find_record
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.models import ImageRecord, Disease, User, AuditLog
from app.modules.auth.dependencies import get_user, get_admin
from app.core.security import rate_limit
from app.modules.images.image_analysis import Crop, decode_image, inspect_quality
from app.modules.images.image_model import public_status, analyze_with_model
from app.modules.images.image_catalog import catalog_coverage, match_model_result
from app.modules.images.image_store import store_image, reference_result, image_path
from app.modules.images.image_gemini import analyze_with_gemini
from app.modules.assistant.external import external_answer
from app.modules.images.vision_labels import ObservationContext, LABELS, SITES, photo_scope
from app.database.models import Symptom
from app.modules.library.specialties import supports_photo

router = APIRouter()


@router.get("/api/v1/images/labels")
def image_labels(db: Session = Depends(get_db)):
    topics = db.scalars(
        select(Disease).where(Disease.published == True).order_by(Disease.name)
    ).all()
    return {
        "labels": [
            {"id": s.slug, "name": s.name}
            for s in db.scalars(select(Symptom).order_by(Symptom.name))
            if s.slug in LABELS
        ],
        "sites": [{"id": code, "name": name} for code, name in SITES.items()],
        "topics": [
            {
                "id": d.id,
                "name": d.name,
                "english_name": d.english_name,
                "category": d.category,
                "scope": photo_scope(d.slug),
            }
            for d in topics
            if supports_photo(d)
        ],
        "notice": "Danh mục tham khảo cho AI, không phải danh sách bệnh đã được mô hình kiểm định nhận diện.",
    }


@router.get("/api/v1/models/status")
def model_status():
    return {
        "image_model": public_status(),
        "image_quality": {"status": "available", "version": "quality-heuristics-v1"},
        "retrieval": "keyword-v1",
        "symptoms": "topic-overlap-v1",
        "questions": "bm25-extractive-v1",
    }


@router.get("/api/v1/images/catalog")
def image_catalog(db: Session = Depends(get_db)):
    return {
        "model": public_status(),
        "catalog": catalog_coverage(db),
        "reference_images": db.scalar(
            select(func.count()).select_from(ImageRecord).where(ImageRecord.is_reference == True)
        ),
    }


@router.post("/api/v1/images/check")
def check_image(request: Request, file: UploadFile = File(...)):
    rate_limit(request, "image", 10)
    try:
        image, metadata, transparency = decode_image(file.file.read(5 * 1024 * 1024 + 1))
        return {
            "status": "model_unavailable",
            "file_valid": True,
            **metadata,
            "stored": False,
            "quality": inspect_quality(image, transparency),
            "message": "Đã kiểm tra tệp và chất lượng kỹ thuật; không có kết luận bệnh lý. Ảnh không được lưu.",
        }
    finally:
        file.file.close()


@router.post("/api/v1/images/analyze")
def analyze_image(
    request: Request,
    file: UploadFile = File(...),
    image_type: Literal["clinical", "dermoscopy"] = Form("clinical"),
    crop: str | None = Form(None),
    analysis_mode: Literal["ai", "reference", "gemini"] = Form("ai"),
    save_image: bool = Form(False),
    observations: str | None = Form(None),
    allow_external_ai: bool = Form(False),
    db: Session = Depends(get_db),
):
    rate_limit(request, "image", 10)
    try:
        user = get_user(request, db) if save_image else None
        context = None
        if observations:
            if len(observations) > 2000:
                raise HTTPException(422, "Thông tin dấu hiệu quá dài.")
            try:
                context = ObservationContext.model_validate_json(observations)
            except ValueError:
                raise HTTPException(422, "Thông tin dấu hiệu không hợp lệ.")
            if len(set(context.label_ids)) != len(context.label_ids) or any(
                i not in LABELS for i in context.label_ids
            ):
                raise HTTPException(422, "Nhãn dấu hiệu không hợp lệ hoặc bị lặp.")
        region = None
        if crop:
            if len(crop) > 500:
                raise HTTPException(422, "Thông tin vùng chọn quá dài.")
            try:
                region = Crop.model_validate_json(crop)
            except ValueError:
                raise HTTPException(422, "Vùng chọn không hợp lệ hoặc vượt ra ngoài ảnh.")
        image, metadata, transparency = decode_image(file.file.read(5 * 1024 * 1024 + 1), region)
        quality = inspect_quality(image, transparency)
        if analysis_mode == "gemini":
            if allow_external_ai is not True:
                raise HTTPException(403, "Cần đồng ý gửi ảnh tới Gemini trước khi phân tích trực tuyến.")
            rate_limit(request, "image-gemini", 5)
            result = (
                analyze_with_gemini(image, db, context)
                if context
                else analyze_with_gemini(image, db)
            )
        elif analysis_mode == "reference":
            result = reference_result(image, image_type, db)
        else:
            result = analyze_with_model(image, image_type, quality, db)
            result["method"] = "resnet18-image-v1"
            if result["status"] == "model_unavailable":
                result["status"] = "unknown"
                result["reason"] = "model_unavailable"
                result["message"] = (
                    "Chưa rõ: mô hình AI chưa sẵn sàng. Ảnh không được chẩn đoán bằng cách tìm ảnh trùng. Cần huấn luyện và cài mô hình trước khi nhận diện ảnh mới."
                )
        result = match_model_result(result, db)
        missing_article = result['status'] == 'catalog_mismatch' or (
            result['status'] == 'group_result' and not result.get('related_articles')
        )
        uncertain = result['status'] == 'insufficient_confidence'
        if analysis_mode == 'ai' and (missing_article or uncertain):
            reason = 'insufficient_confidence' if uncertain else 'missing_article'
            result['fallback'] = {'status': 'consent_required', 'reason': reason}
            if allow_external_ai is True:
                local = result
                try:
                    rate_limit(request, 'image-gemini', 5)
                    external = external_answer(
                        ('Tham khảo ảnh da và tìm nguồn đọc thêm. Mô hình cục bộ chưa đủ độ tin cậy; chưa thể kết luận thư viện có bài tương ứng hay không.'
                         if uncertain else 'Tham khảo ảnh da và tìm nguồn đọc thêm; thư viện chưa có bài liên quan đến nhóm kết quả.'),
                        image_context={'group': local.get('group'), 'local_status': local['status'],
                                       'notice': 'Không có chẩn đoán được xác nhận. Không ép ảnh vào một bệnh.'},
                        image=image,
                    )
                    result = {**local, 'external_result': external,
                              'fallback': {'status': 'used' if external['status'] in {'external_result', 'external_observation'} else 'insufficient_evidence', 'reason': reason}}
                except HTTPException as error:
                    result = {**local, 'fallback': {'status': 'unavailable', 'reason': reason, 'message': str(error.detail),
                                  'model': getattr(error, 'upstream_model', None),
                                  'upstream_status': getattr(error, 'upstream_status', None),
                                  'error_kind': getattr(error, 'error_kind', None)}}
        record = store_image(image, image_type, user, db) if user else None
        return {
            "file_valid": True,
            **metadata,
            "image_type": image_type,
            "analysis_mode": analysis_mode,
            "stored": record is not None,
            "image_record_id": record.id if record else None,
            "metadata_removed": True,
            "quality": quality,
            **result,
        }
    finally:
        file.file.close()


def record_json(record, db):
    disease = find_record(db, Disease, record.disease_id) if record.disease_id else None
    return {
        "id": record.id,
        "image_type": record.image_type,
        "width": record.width,
        "height": record.height,
        "created_at": record.created_at.isoformat(),
        "is_reference": record.is_reference,
        "disease_id": record.disease_id,
        "disease_name": disease.name if disease else None,
        "image_url": "/api/v1/images/records/" + str(record.id) + "/file",
    }


@router.get("/api/v1/images/records")
def my_images(db: Session = Depends(get_db), user: User = Depends(get_user)):
    return [
        record_json(row, db)
        for row in db.scalars(
            select(ImageRecord)
            .where(ImageRecord.user_id == user.id)
            .order_by(ImageRecord.created_at.desc())
        )
    ]


@router.get("/api/v1/images/records/{record_id}/file")
def private_image(record_id: str, db: Session = Depends(get_db), user: User = Depends(get_user)):
    record = find_record(db, ImageRecord, record_id)
    if not record or (record.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Không tìm thấy ảnh.")
    path = image_path(record.file_uuid)
    if not path.is_file():
        raise HTTPException(404, "Tệp ảnh không còn tồn tại.")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.delete("/api/v1/images/records/{record_id}", status_code=204)
def delete_image(record_id: str, db: Session = Depends(get_db), user: User = Depends(get_user)):
    record = find_record(db, ImageRecord, record_id)
    if not record or (record.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Không tìm thấy ảnh.")
    path = image_path(record.file_uuid)
    # Remove bytes first: a file error leaves the database record available for retry.
    path.unlink(missing_ok=True)
    db.delete(record)
    db.commit()


class ReferenceEdit(BaseModel):
    disease_id: str | None = Field(default=None, max_length=60)
    is_reference: bool = False


@router.get("/api/v1/admin/image-records")
def admin_images(db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    return [
        record_json(row, db)
        for row in db.scalars(
            select(ImageRecord).order_by(ImageRecord.created_at.desc()).limit(100)
        )
    ]


@router.put("/api/v1/admin/image-records/{record_id}")
def label_image(
    record_id: str,
    body: ReferenceEdit,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin),
):
    record = find_record(db, ImageRecord, record_id)
    if not record:
        raise HTTPException(404, "Không tìm thấy ảnh.")
    if body.is_reference:
        disease = find_record(db, Disease, body.disease_id) if body.disease_id else None
        if not disease or not disease.published:
            raise HTTPException(422, "Chọn bệnh lý đang xuất bản trước khi dùng làm ảnh mẫu.")
        if not supports_photo(disease):
            raise HTTPException(
                422,
                "Bệnh này cần tra cứu bằng thông tin lâm sàng, không dùng làm nhãn ảnh chụp thông thường.",
            )
        if not image_path(record.file_uuid).is_file():
            raise HTTPException(422, "Tệp ảnh không còn tồn tại.")
    before = {"disease_id": record.disease_id, "is_reference": record.is_reference}
    record.disease_id = disease.id if body.is_reference else None
    record.is_reference = body.is_reference
    db.add(
        AuditLog(
            actor_id=admin.id,
            action="image_label",
            entity_id=str(record.id),
            snapshot={
                "before": before,
                "after": {"disease_id": record.disease_id, "is_reference": record.is_reference},
            },
        )
    )
    db.commit()
    return record_json(record, db)

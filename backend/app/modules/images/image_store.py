"""Private, normalized image storage and exact reference lookup; no diagnostic inference."""

import hashlib
import io
import os
from pathlib import Path
from uuid import uuid4
from PIL import Image
from fastapi import HTTPException
from app.modules.library.identifiers import find_record
from sqlalchemy import select, func
from app.database.models import ImageRecord, Disease
from app.modules.library.specialties import supports_photo


def storage_root():
    default = Path(__file__).resolve().parents[3] / "data" / "images"
    return Path(os.getenv("DERMA_IMAGE_STORAGE", str(default))).resolve()


def normalized_image(image):
    result = image.copy().convert("RGB")
    result.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
    result.info.clear()
    pixel_hash = hashlib.sha256(str(result.size).encode() + result.tobytes()).hexdigest()
    return result, pixel_hash


def image_path(record_id):
    # Database IDs never become arbitrary filesystem paths.
    from uuid import UUID

    try:
        safe_id = str(UUID(record_id))
    except ValueError:
        raise HTTPException(404, "Không tìm thấy ảnh.")
    return storage_root() / (safe_id + ".png")


def store_image(image, image_type, user, db):
    if (
        db.scalar(
            select(func.count()).select_from(ImageRecord).where(ImageRecord.user_id == user.id)
        )
        >= 50
    ):
        raise HTTPException(409, "Tài khoản đã lưu 50 ảnh. Xóa ảnh cũ trước khi lưu thêm.")
    normalized, pixel_hash = normalized_image(image)
    stream = io.BytesIO()
    normalized.save(stream, format="PNG")
    payload = stream.getvalue()
    if len(payload) > 8 * 1024 * 1024:
        raise HTTPException(422, "Ảnh sau chuẩn hóa quá lớn để lưu.")
    record = ImageRecord(
        file_uuid=str(uuid4()),
        user_id=user.id,
        pixel_sha256=pixel_hash,
        image_type=image_type,
        width=normalized.width,
        height=normalized.height,
        is_reference=False,
    )
    folder = storage_root()
    folder.mkdir(parents=True, exist_ok=True)
    path = image_path(record.file_uuid)
    try:
        with path.open("xb") as destination:
            destination.write(payload)
        db.add(record)
        db.commit()
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    return record


def reference_result(image, image_type, db):
    _, pixel_hash = normalized_image(image)
    records = list(
        db.scalars(
            select(ImageRecord).where(
                ImageRecord.pixel_sha256 == pixel_hash,
                ImageRecord.image_type == image_type,
                ImageRecord.is_reference == True,
            )
        )
    )
    topics = {}
    for record in records:
        topic = find_record(db, Disease, record.disease_id) if record.disease_id else None
        if (
            topic
            and topic.published
            and supports_photo(topic)
            and image_path(record.file_uuid).is_file()
        ):
            topics[topic.id] = topic
    if len(topics) == 1:
        topic = next(iter(topics.values()))
        return {
            "status": "research_result",
            "method": "exact-reference-v1",
            "message": "Ảnh trùng điểm ảnh sau chuẩn hóa với ảnh mẫu được quản trị viên gắn nhãn. Đây là đối chiếu ảnh, không phải chẩn đoán.",
            "candidates": [{"disease_id": topic.id, "name": topic.name, "score": 1.0}],
            "score_notice": "1.0 biểu thị trùng ảnh mẫu, không phải xác suất mắc bệnh.",
        }
    return {
        "status": "unknown",
        "method": "exact-reference-v1",
        "message": (
            "Chưa rõ: ảnh mẫu trùng có nhãn mâu thuẫn, cần quản trị viên kiểm tra."
            if len(topics) > 1
            else "Chưa rõ: chưa có ảnh mẫu trùng đã gắn nhãn. Ảnh khác của cùng một bệnh vẫn có thể không khớp; cần mô hình đã huấn luyện để nhận diện ảnh mới."
        ),
    }

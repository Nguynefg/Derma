"""Match model output to published database records, without inventing diagnoses."""

from app.modules.library.identifiers import find_record
from sqlalchemy import select
from app.database.models import Disease
import app.modules.images.image_model as image_model
from app.modules.images.vision_labels import photo_scope
from app.modules.library.specialties import supports_photo


def catalog_coverage(db):
    topics = list(db.scalars(select(Disease).where(Disease.published == True)))
    photo_topics = [topic for topic in topics if supports_photo(topic)]
    by_id = {str(topic.id): topic for topic in photo_topics}
    by_id.update({topic.slug: topic for topic in photo_topics})
    try:
        configured = image_model.read_configuration()
    except Exception:
        configured = None
    labels = configured[0].labels if configured else []
    linked_ids = {
        disease_id
        for label in labels
        for disease_id in (
            [label.disease_id] if label.disease_id else getattr(label, "related_disease_ids", [])
        )
    }
    supported = [
        {"disease_id": by_id[disease_id].id, "name": by_id[disease_id].name}
        for disease_id in sorted(linked_ids)
        if disease_id in by_id
    ]
    return {
        "published_topics": len(topics),
        "photo_topics": len(photo_topics),
        "mapped_topics": len(supported),
        "mapped_labels": supported,
        "mapping_valid": bool(labels) and linked_ids <= set(by_id),
        "notice": "Có bài trong CSDL không có nghĩa mô hình đã được huấn luyện cho bệnh đó.",
    }


def match_model_result(result, db):
    """A match confirms a catalog link; it does not confirm the patient's disease."""
    result = {**result}
    status = result.get("status")
    result["database_match"] = {
        "status": (
            "inconclusive" if status in {"insufficient_confidence", "unknown"} else "not_evaluated"
        ),
        "message": "Chưa đủ cơ sở đối chiếu ảnh với bệnh lý trong CSDL; không thể kết luận ảnh nằm ngoài thư viện.",
    }
    if status != "research_result":
        result.pop("candidates", None)
        return result
    candidates = result.get("candidates", [])
    enriched = []
    for candidate in candidates:
        topic = find_record(db, Disease, candidate["disease_id"])
        if topic is None or not topic.published or not supports_photo(topic):
            result.pop("candidates", None)
            result["status"] = "catalog_mismatch"
            result["message"] = (
                "Chủ đề mô hình trả về chưa có hoặc đã bị ẩn trong thư viện. Chưa thể gợi ý bệnh lý."
            )
            return result
        enriched.append(
            {
                **candidate,
                "disease_id": topic.id,
                "name": topic.name,
                "english_name": topic.english_name,
                "category": topic.category,
                "summary": topic.summary,
                "content_version": topic.version,
                "photo_scope": photo_scope(getattr(topic, "slug", "")),
            }
        )
    if not enriched:
        result["status"] = "insufficient_confidence"
        result["message"] = "Mô hình không có chủ đề để đối chiếu với thư viện."
        result["database_match"]["status"] = "inconclusive"
        result.pop("candidates", None)
        return result
    result["candidates"] = enriched
    result["database_match"] = {
        "status": "matched",
        "message": "Các chủ đề gợi ý dưới đây có bài đang xuất bản trong CSDL. Đây không phải xác nhận chẩn đoán.",
    }
    return result

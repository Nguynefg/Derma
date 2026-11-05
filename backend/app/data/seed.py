from sqlalchemy import select
from app.database.connection import SessionLocal, Disease, Symptom, DiseaseSymptom, Reference

SYMPTOMS = {
    "itch": "Ngứa",
    "redness": "Đỏ da",
    "scale": "Bong vảy",
    "bumps": "Sẩn / mụn",
    "dry": "Da khô, nứt",
    "burning": "Nóng rát",
    "white-patches": "Mảng da mất màu",
    "hair-loss": "Rụng tóc từng mảng",
}
# Short, independently worded Vietnamese source summaries. Not clinician-reviewed.
# Associations index topics, not diagnostic probabilities or clinical prevalence.
DATA = [
    dict(
        id="acne",
        name="Mụn trứng cá",
        english_name="Acne",
        category="Nang lông",
        summary="Tình trạng các nang lông bị bít tắc bởi bã nhờn và tế bào da chết, hình thành mụn.",
        details="Mụn thường xuất hiện ở mặt, lưng, ngực và vai. Biểu hiện có thể gồm các nốt mụn và vùng viêm đỏ.",
        risk_factors="Hormone và tiền sử gia đình có thể liên quan. Tham khảo nguồn gốc để tìm hiểu đầy đủ.",
        aliases=["mun", "trung ca", "pimples"],
        symptoms=["bumps", "redness"],
    ),
    dict(
        id="atopic-dermatitis",
        name="Viêm da cơ địa",
        english_name="Atopic dermatitis",
        category="Viêm da",
        summary="Tình trạng viêm da kéo dài, thường gây ngứa, khô da và xuất hiện thành từng đợt.",
        details="Gãi có thể làm da đỏ, nứt hoặc bong vảy. Bệnh thường bắt đầu từ nhỏ nhưng có thể xuất hiện ở nhiều độ tuổi; không lây giữa người với người.",
        risk_factors="Di truyền, hệ miễn dịch và môi trường có vai trò trong bệnh.",
        aliases=["eczema", "cham", "viem da"],
        symptoms=["itch", "redness", "scale", "dry"],
    ),
    dict(
        id="psoriasis",
        name="Vảy nến",
        english_name="Psoriasis",
        category="Viêm da",
        summary="Tình trạng kéo dài liên quan đến hệ miễn dịch, khiến tế bào da phát triển nhanh và tạo mảng viêm, bong vảy.",
        details="Các mảng thường gặp ở da đầu, khuỷu tay hoặc đầu gối, nhưng có thể xuất hiện ở vị trí khác. Triệu chứng có thể tăng giảm theo đợt.",
        risk_factors="Có sự tham gia của yếu tố di truyền và môi trường.",
        aliases=["vay nen"],
        symptoms=["redness", "scale"],
    ),
    dict(
        id="rosacea",
        name="Trứng cá đỏ",
        english_name="Rosacea",
        category="Viêm da",
        summary="Tình trạng viêm da kéo dài thường gây đỏ vùng mũi, má và có thể kèm những nốt giống mụn.",
        details="Một số người có cảm giác nóng rát hoặc thấy các mạch máu nhỏ. Biểu hiện thay đổi theo từng người và từng đợt.",
        risk_factors="Thường gặp hơn ở người trung niên hoặc lớn tuổi; yếu tố gia đình và môi trường có thể liên quan.",
        aliases=["do mat", "trung ca do"],
        symptoms=["redness", "bumps", "burning"],
    ),
    dict(
        id="vitiligo",
        name="Bạch biến",
        english_name="Vitiligo",
        category="Sắc tố da",
        summary="Rối loạn tự miễn làm mất sắc tố, tạo các vùng da có màu trắng nhạt.",
        details="Các mảng mất màu có thể xuất hiện ở nhiều vị trí. Tóc tại vùng ảnh hưởng cũng có thể chuyển trắng.",
        risk_factors="Tiền sử gia đình và một số bệnh tự miễn có thể liên quan.",
        aliases=["bach bien", "mat sac to"],
        symptoms=["white-patches"],
    ),
    dict(
        id="alopecia-areata",
        name="Rụng tóc từng mảng",
        english_name="Alopecia areata",
        category="Tóc & da đầu",
        summary="Tình trạng hệ miễn dịch tác động đến nang tóc, thường gây rụng tóc theo từng mảng.",
        details="Có nhiều dạng và mức độ khác nhau. Các nguyên nhân khác cũng có thể gây rụng tóc với biểu hiện tương tự.",
        risk_factors="Tiền sử gia đình, một số bệnh tự miễn hoặc dị ứng có thể liên quan.",
        aliases=["rung toc", "hoi tung mang"],
        symptoms=["hair-loss"],
    ),
]


def seed():
    with SessionLocal() as db:
        # Initialization only: never overwrite edits or republish archived records.
        if db.scalar(select(Disease.id).limit(1)):
            return
        for code, name in SYMPTOMS.items():
            db.add(Symptom(slug=code, name=name))
        db.flush()
        for original in DATA:
            row = original.copy()
            symptom_ids = row.pop("symptoms")
            disease = Disease(
                slug=row.pop("id"),
                **row,
                prevention="Bản tóm tắt này chưa cung cấp hướng dẫn phòng ngừa cá nhân. Xem tài liệu nguồn và trao đổi với nhân viên y tế khi cần.",
                published=True,
            )
            db.add(disease)
            db.flush()
            for symptom_id in symptom_ids:
                db.add(
                    DiseaseSymptom(
                        disease_id=disease.id,
                        symptom_id=db.scalar(select(Symptom.id).where(Symptom.slug == symptom_id)),
                    )
                )
            db.add(
                Reference(
                    slug=f"niams-{disease.slug}",
                    disease_id=disease.id,
                    title=f"{row['english_name']} — Overview, Symptoms & Causes",
                    publisher="NIAMS · National Institutes of Health",
                    url=f"https://www.niams.nih.gov/health-topics/{disease.slug}",
                    accessed_at="2026-10-14",
                    usage_note="Tóm tắt ngắn bằng tiếng Việt và liên kết nguồn; chưa được chuyên gia y tế duyệt. Không sao chép hình ảnh.",
                )
            )
        db.commit()

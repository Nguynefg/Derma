"""Additive, one-time library expansion; do not overwrite editorial content."""

import hashlib
from app.modules.library.identifiers import find_record
from sqlalchemy import select
from app.database.connection import (
    SessionLocal,
    LibraryUpdate,
    Disease,
    Symptom,
    DiseaseSymptom,
    Reference,
    MedicalDocument,
    DocumentVersion,
)

RELEASE = "nhs-library-2026-10-v1"
SYMPTOMS = {
    "blisters": "Mụn nước",
    "pain": "Đau da",
    "crust": "Đóng vảy tiết",
    "rough": "Da sần ráp",
    "wheals": "Sẩn phù / mảng nổi",
}
# Independently worded short summaries from the linked NHS pages, checked 2026-10-14.
# Symptom links indicate source mentions only, never diagnoses or probabilities.
DATA = [
    dict(
        id="contact-dermatitis",
        name="Viêm da tiếp xúc",
        english_name="Contact dermatitis",
        category="Viêm da",
        summary="Viêm da xuất hiện sau khi tiếp xúc với chất gây kích ứng hoặc dị ứng.",
        details="Da có thể ngứa, khô, nứt hoặc nổi mụn nước. Biểu hiện thường xuất hiện trong vài giờ hoặc vài ngày sau tiếp xúc; bàn tay và mặt là vị trí hay gặp.",
        risk_factors="Xà phòng, chất tẩy rửa và tiếp xúc thường xuyên với nước có thể gây kích ứng. Một số mỹ phẩm hoặc kim loại như nickel có thể gây dị ứng.",
        aliases=["viem da tiep xuc", "contact eczema"],
        symptoms=["itch", "redness", "dry", "blisters"],
    ),
    dict(
        id="hives",
        name="Mề đay",
        english_name="Hives (urticaria)",
        category="Dị ứng & sẩn phù",
        summary="Ban da nổi thành sẩn hoặc mảng phù, thường ngứa và có thể nóng rát.",
        details="Mảng nổi có nhiều hình dạng và kích thước, có thể khu trú hoặc lan rộng. Nếu kèm khó thở hay sưng đột ngột môi, lưỡi hoặc họng, cần hỗ trợ y tế khẩn cấp.",
        risk_factors="Thức ăn, thuốc, nhiễm trùng hoặc các kích thích như lạnh, nóng và áp lực lên da có thể là yếu tố khởi phát; không phải lúc nào cũng xác định được.",
        aliases=["me day", "may day", "urticaria"],
        symptoms=["itch", "wheals", "burning"],
    ),
    dict(
        id="ringworm",
        name="Nấm da (hắc lào)",
        english_name="Ringworm (tinea)",
        category="Nhiễm nấm",
        summary="Nhiễm nấm da có thể tạo mảng ngứa, khô hoặc bong vảy, thường có dạng vòng.",
        details="Nấm da có thể ảnh hưởng nhiều vị trí, gồm da đầu và bẹn. Hình dạng không phải lúc nào cũng giống vòng; tổn thương ở da đầu có thể kèm rụng tóc.",
        risk_factors="Có thể lây khi tiếp xúc với người, động vật hoặc vật dụng bị nhiễm như khăn và lược.",
        aliases=["nam da", "hac lao", "lac dong tien", "tinea"],
        symptoms=["itch", "redness", "scale", "dry", "hair-loss"],
    ),
    dict(
        id="scabies",
        name="Ghẻ",
        english_name="Scabies",
        category="Ký sinh trùng",
        summary="Tổn thương ngứa do cái ghẻ, có thể lây qua tiếp xúc da gần gũi.",
        details="Ngứa thường rõ về đêm, kèm sẩn hoặc ban nổi. Tổn thương có thể gặp ở kẽ ngón tay, cổ tay, nách và quanh eo. Nhiều tình trạng khác cũng gây ngứa tương tự.",
        risk_factors="Bất kỳ ai cũng có thể mắc; tiếp xúc da gần gũi là đường lây được tài liệu nguồn đề cập.",
        aliases=["ghe", "cai ghe"],
        symptoms=["itch", "bumps", "redness"],
    ),
    dict(
        id="impetigo",
        name="Chốc lở",
        english_name="Impetigo",
        category="Nhiễm khuẩn",
        summary="Nhiễm trùng da dễ lây, thường gặp ở trẻ nhỏ, có thể để lại vảy tiết vàng nâu.",
        details="Tổn thương có thể bắt đầu bằng vết đỏ hoặc mụn nước, sau đó vỡ và đóng vảy tiết. Thường gặp quanh mũi, miệng hoặc bàn tay; có thể ngứa hay đau.",
        risk_factors="Mọi lứa tuổi có thể mắc, nhưng trẻ nhỏ gặp nhiều hơn. Tổn thương có thể lan sang vùng da khác.",
        aliases=["choc lo", "choc"],
        symptoms=["redness", "blisters", "crust", "itch", "pain"],
    ),
    dict(
        id="warts",
        name="Mụn cóc",
        english_name="Warts and verrucas",
        category="Tổn thương da do virus",
        source_slug="warts-and-verrucas",
        summary="Các nốt da nhỏ, thường cứng và sần; mụn cóc lòng bàn chân có thể có chấm đen nhỏ.",
        details="Mụn cóc có thể gặp ở ngón tay, khớp ngón, đầu gối và lòng bàn tay. Một số tự hết nhưng có thể kéo dài nhiều tháng hoặc nhiều năm.",
        risk_factors="Bản tóm tắt này giới thiệu biểu hiện; cần xem nguồn để tìm hiểu nguyên nhân và cách hạn chế lây lan.",
        aliases=["mun coc", "hat com", "verruca"],
        symptoms=["bumps", "rough"],
    ),
    dict(
        id="shingles",
        name="Zona thần kinh",
        english_name="Shingles (herpes zoster)",
        category="Tổn thương da do virus",
        summary="Bệnh gây ban đau, có thể kèm mụn nước tập trung ở một bên cơ thể.",
        details="Cảm giác đau hoặc châm chích có thể xuất hiện trước ban. Mụn nước có thể rỉ dịch rồi khô và đóng vảy. Khi nghi ngờ zona, nên liên hệ nhân viên y tế sớm.",
        risk_factors="Nguồn mô tả tổn thương có thể gặp cả ở mặt và mắt; triệu chứng cần được nhân viên y tế đánh giá thay vì tự xác nhận bằng hình ảnh.",
        aliases=["zona", "zona than kinh", "herpes zoster"],
        symptoms=["pain", "blisters", "itch", "crust"],
    ),
    dict(
        id="hidradenitis-suppurativa",
        name="Viêm tuyến mồ hôi mủ",
        english_name="Hidradenitis suppurativa (HS)",
        category="Nang lông",
        summary="Tình trạng da kéo dài gây nốt đau, áp xe và sẹo, thường ở các vùng nếp gấp.",
        details="Có thể gặp nốt giống nhọt, nang và các đường dưới da rỉ mủ. Vị trí thường được đề cập gồm nách, bẹn, vùng mông và quanh ngực.",
        risk_factors="Nguyên nhân chính xác chưa rõ. Tổn thương xuất hiện gần nang lông ở vùng có tuyến mồ hôi.",
        aliases=["viem tuyen mo hoi mu", "hidradenitis"],
        symptoms=["bumps", "pain"],
    ),
    dict(
        id="pityriasis-rosea",
        name="Vảy phấn hồng",
        english_name="Pityriasis rosea",
        category="Viêm da",
        summary="Ban da có thể bắt đầu bằng một mảng bong vảy, sau đó xuất hiện nhiều mảng nhỏ hơn.",
        details="Mảng đầu thường tròn hoặc bầu dục. Ban nhỏ có thể xuất hiện ở ngực và lưng, đôi khi ngứa. Biểu hiện có thể giống nấm da, chàm hoặc vảy nến.",
        risk_factors="Bản tóm tắt không xác định nguyên nhân cá nhân; cần khám nếu chưa rõ loại ban da.",
        aliases=["vay phan hong", "pityriasis rosea"],
        symptoms=["scale", "itch", "redness"],
    ),
    dict(
        id="keratosis-pilaris",
        name="Dày sừng nang lông",
        english_name="Keratosis pilaris",
        category="Nang lông",
        summary="Các sẩn nhỏ đi kèm da khô và sần ráp; thường là tình trạng lành tính.",
        details="Sẩn có thể gặp ở cánh tay, đùi hoặc vùng mông, thường không đau. Da đôi khi ngứa; màu sẩn có thể giống màu da hoặc thay đổi theo tông da.",
        risk_factors="Có thể gặp ở nhiều độ tuổi và kéo dài. Nguồn ghi nhận biểu hiện có thể tốt hơn vào mùa hè và rõ hơn vào mùa đông.",
        aliases=["day sung nang long", "da ga", "keratosis"],
        symptoms=["bumps", "rough", "dry", "itch"],
    ),
]


def seed_expansion():
    return apply_release(RELEASE, DATA, SYMPTOMS)


def apply_release(
    release,
    data,
    symptoms,
    *,
    source_name="NHS",
    source_prefix="nhs",
    accessed_at="2026-10-14",
    extra_links=None,
):
    with SessionLocal() as db:
        if db.get(LibraryUpdate, release):
            return 0
        for code, name in symptoms.items():
            if not find_record(db, Symptom, code):
                db.add(Symptom(slug=code, name=name))
        db.flush()
        added = 0
        for original in data:
            # Existing ID belongs to the installation: preserve edits/publication state.
            if find_record(db, Disease, original["id"]):
                continue
            row = original.copy()
            symptom_ids = row.pop("symptoms")
            slug = row.pop("source_slug", row["id"])
            source_url = row.pop("source_url", None)
            disease = Disease(
                slug=row.pop("id"),
                **row,
                prevention="Xem tài liệu nguồn và trao đổi với nhân viên y tế để lựa chọn cách chăm sóc phù hợp. Không tự dùng thuốc dựa trên bản tóm tắt.",
                published=True,
            )
            db.add(disease)
            db.flush()
            for symptom_id in symptom_ids:
                db.add(
                    DiseaseSymptom(
                        disease_id=disease.id, symptom_id=find_record(db, Symptom, symptom_id).id
                    )
                )
            ref_id = source_prefix + "-" + disease.slug
            title = disease.english_name + " — " + source_name
            publisher = "NHS · National Health Service" if source_name == "NHS" else source_name
            url = source_url or "https://www.nhs.uk/conditions/" + slug + "/"
            note = f"Tóm tắt ngắn viết lại bằng tiếng Việt từ nguồn {source_name}; chưa được chuyên gia y tế thẩm định. Không sao chép hình ảnh."
            db.add(
                Reference(
                    slug=ref_id,
                    disease_id=disease.id,
                    title=title,
                    publisher=publisher,
                    url=url,
                    accessed_at=accessed_at,
                    usage_note=note,
                )
            )
            document = MedicalDocument(
                slug=ref_id,
                disease_id=disease.id,
                title=title,
                publisher=publisher,
                source_url=url,
                usage_note=note,
                published=True,
                version=1,
            )
            db.add(document)
            db.flush()
            content = disease.summary + "\n\n" + disease.details + "\n\n" + disease.risk_factors
            db.add(
                DocumentVersion(
                    document_id=document.id,
                    version=1,
                    title=title,
                    publisher=publisher,
                    source_url=url,
                    usage_note=note,
                    content=content,
                    checksum=hashlib.sha256(content.encode()).hexdigest(),
                    editor_id=None,
                )
            )
            added += 1
        for slug, codes in (extra_links or {}).items():
            disease = find_record(db, Disease, slug)
            if not disease:
                continue
            for code in codes:
                symptom = find_record(db, Symptom, code)
                if not symptom:
                    raise ValueError("Unknown symptom in library release: " + code)
                if not db.get(DiseaseSymptom, (disease.id, symptom.id)):
                    db.add(DiseaseSymptom(disease_id=disease.id, symptom_id=symptom.id))
        db.add(LibraryUpdate(id=release))
        db.commit()
        return added

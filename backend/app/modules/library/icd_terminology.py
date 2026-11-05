"""Source-aware terminology corrections, not clinical validation of the whole catalog."""

TITLE_OVERRIDES = {
    "0 No problem": "Không có vấn đề (mức 0)",
    "1 Mild problem": "Vấn đề mức độ nhẹ (mức 1)",
    "2 Moderate problem": "Vấn đề mức độ vừa (mức 2)",
    "3 Severe problem": "Vấn đề mức độ nặng (mức 3)",
    "4 Complete problem": "Vấn đề ở mức hoàn toàn (mức 4)",
    "9 Not applicable": "Không áp dụng (mã 9)",
    "Upper third of oesophagus": "Một phần ba trên của thực quản",
    "Middle third of oesophagus": "Một phần ba giữa của thực quản",
    "Lower third of oesophagus": "Một phần ba dưới của thực quản",
    "Upper inner quadrant of breast": "Góc phần tư trên trong của vú",
    "Upper outer quadrant of breast": "Góc phần tư trên ngoài của vú",
    "Lower inner quadrant of breast": "Góc phần tư dưới trong của vú",
    "Lower outer quadrant of breast": "Góc phần tư dưới ngoài của vú",
    "Distal third of the scaphoid bone": "Một phần ba đoạn xa của xương thuyền",
    "Middle third of the scaphoid bone": "Một phần ba đoạn giữa của xương thuyền",
    "Proximal third of the scaphoid bone": "Một phần ba đoạn gần của xương thuyền",
    "13C-urea": "Urê đánh dấu carbon-13 (13C)",
    "Methacetin (13C)": "Methacetin đánh dấu carbon-13 (13C)",
    "Developmental speech sound disorder": "Rối loạn phát triển âm lời nói",
    "Developmental speech fluency disorder": "Rối loạn phát triển độ trôi chảy của lời nói",
    "Non-aneurysmal subarachnoid haemorrhage": "Xuất huyết dưới nhện không do phình mạch",
    "Silent cerebral infarct": "Nhồi máu não thầm lặng",
    "Silent cerebral microbleed": "Vi xuất huyết não thầm lặng",
}


def medical_title(source, vietnamese):
    if source in TITLE_OVERRIDES:
        return TITLE_OVERRIDES[source]
    source_lower = source.lower()
    if "other specified" in source_lower:
        vietnamese = vietnamese.replace("khác được chỉ định khác", "khác đã được xác định")
        vietnamese = vietnamese.replace("được chỉ định khác", "khác đã được xác định")
    if "not otherwise specified" in source_lower:
        vietnamese = vietnamese.replace("không được chỉ định khác", "không xác định thêm")
    if "unspecified" in source_lower:
        vietnamese = vietnamese.replace("không được chỉ định", "không xác định")
    if "not elsewhere classified" in source_lower:
        vietnamese = vietnamese.replace(
            "không được phân loại ở nơi khác", "chưa được phân loại ở nơi khác"
        )
    # Match the source concept, never replace legitimate surgical indications or
    # nonspecific findings just because their Vietnamese wording looks similar.
    if "specified" in source_lower and "unspecified" not in source_lower:
        vietnamese = vietnamese.replace("được chỉ định", "đã được xác định")
    if source in {
        "Other disorders of glucose regulation or pancreatic internal secretion",
        "Attention to other artificial openings",
        "Presence of other transplanted organ or tissue",
    }:
        vietnamese = vietnamese.replace(" được chỉ định", "")
    if "not otherwise specified" in source_lower:
        for phrase in (
            "không được phân loại cụ thể khác",
            "không được phân loại ở nơi khác",
            "không được phân loại nơi khác",
            "không được phân loại cụ thể",
            "không có phân loại khác",
            "không phân loại nơi khác",
        ):
            vietnamese = vietnamese.replace(phrase, "không xác định thêm")
    if "complaint" in source_lower:
        vietnamese = vietnamese.replace("khiếu nại về", "cảm giác khó chịu ở")
    if "single episode depressive disorder" in source_lower:
        vietnamese = vietnamese.replace("đơn cực", "một giai đoạn")
    if "pelvic organ prolapse" in source_lower:
        vietnamese = vietnamese.replace("sa sút tạng chậu", "sa tạng chậu")
    if "junction" in source_lower:
        vietnamese = vietnamese.replace("khớp nối", "chỗ nối")
    if "dissociative identity disorder" in source_lower:
        vietnamese = vietnamese.replace("nhân cách", "nhân dạng")
    return vietnamese

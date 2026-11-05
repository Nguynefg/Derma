"""Specialty grouping based on the stored category; no duplicated disease records."""

DERMATOLOGY_CATEGORIES = {
    "Da liễu",
    "Bóng nước & tự miễn",
    "Bệnh bóng nước",
    "Dị ứng & sẩn phù",
    "Ký sinh trùng",
    "Móng",
    "Môi & niêm mạc",
    "Mạch máu da",
    "Nang lông",
    "Nhiễm khuẩn",
    "Nhiễm nấm",
    "Phản ứng thuốc",
    "Rối loạn sừng hóa",
    "Sắc tố da",
    "Sẹo",
    "Tuyến mồ hôi",
    "Tóc & da đầu",
    "Tổn thương da do virus",
    "Tổn thương do môi trường",
    "Tổn thương do ánh nắng",
    "Tổn thương lành tính",
    "Tự miễn",
    "U & tổn thương da",
    "Ung thư da",
    "Viêm da",
    "Vảy nến",
}
GENERAL_SPECIALTIES = {
    "Hô hấp",
    "Tiêu hóa",
    "Tim mạch",
    "Nội tiết",
    "Thần kinh",
    "Cơ xương khớp",
    "Thận & tiết niệu",
    "Tai mũi họng",
}


def specialty_for(category):
    if category in DERMATOLOGY_CATEGORIES:
        return "Da liễu"
    return category if category in GENERAL_SPECIALTIES else "Khác"


def supports_photo(topic):
    return getattr(topic, "category", "") in DERMATOLOGY_CATEGORIES

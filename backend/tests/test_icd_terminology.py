import pytest
from app.modules.library.icd_terminology import medical_title


@pytest.mark.parametrize(
    "source,old,expected",
    [
        ("Lower outer quadrant of breast", "1/4 dưới ngoài vú", "Góc phần tư dưới ngoài của vú"),
        ("Upper inner quadrant of breast", "1/4 trên trong vú", "Góc phần tư trên trong của vú"),
        ("Upper third of oesophagus", "1/3 trên thực quản", "Một phần ba trên của thực quản"),
        ("13C-urea", "13C-urea", "Urê đánh dấu carbon-13 (13C)"),
        (
            "Other specified third nerve palsy",
            "Liệt thần kinh III được chỉ định khác",
            "Liệt thần kinh III khác đã được xác định",
        ),
        ("Other specified disease", "Bệnh khác được chỉ định khác", "Bệnh khác đã được xác định"),
        (
            "Lymphoma, not otherwise specified",
            "U lympho, không được chỉ định khác",
            "U lympho, không xác định thêm",
        ),
        (
            "Disease, not elsewhere classified",
            "Bệnh không được phân loại ở nơi khác",
            "Bệnh chưa được phân loại ở nơi khác",
        ),
        ("Nonspecific reaction", "Phản ứng không đặc hiệu", "Phản ứng không đặc hiệu"),
        ("Specific indication for surgery", "Chỉ định phẫu thuật", "Chỉ định phẫu thuật"),
        ("Drug concentration 1/4", "Nồng độ thuốc 1/4", "Nồng độ thuốc 1/4"),
    ],
)
def test_source_aware_medical_terminology(source, old, expected):
    assert medical_title(source, old) == expected
    assert medical_title(source, expected) == expected

"""Ensure automated title edits cannot silently lose key clinical qualifiers."""

import importlib.util
from pathlib import Path
import pytest

path = Path(__file__).resolve().parents[2] / "scripts/translation/review_icd_titles.py"
spec = importlib.util.spec_from_file_location("review_icd_titles", path)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


@pytest.mark.parametrize(
    "old,new,expected",
    [
        ("Tổn thương bên trái", "Tổn thương bên phải", "laterality_changed"),
        ("Tổn thương bên trái, độ 2", "Tổn thương độ 2", "laterality_changed"),
        ("Nồng độ 5 mg/dL", "Nồng độ 5 g/dL", "measurement_unit_changed"),
        ("Kích thước 2 cm", "Kích thước 2 mm", "measurement_unit_changed"),
        ("Khối u không ác tính", "Khối u ác tính", "negation_removed"),
        ("Tổn thương độ 2", "Tổn thương độ 3", "numeric_qualification_changed"),
        ("Nồng độ 0.5 mg", "Nồng độ 5 mg", "numeric_qualification_changed"),
        ("Viêm da", "Viêm da\nThông tin khác", "unexpected_script_or_linebreak"),
        ("Viêm da", "Viêm da 皮", "unexpected_script_or_linebreak"),
        ("Viêm da", "", "invalid_title"),
        ("Nốt ở phổi bên trái, 2 mm", "Nốt phổi bên trái, kích thước 2 mm", None),
        ("13C-urea", "Urê đánh dấu carbon-13 (13C)", None),
        ("Chưa xác định", "Không xác định", None),
    ],
)
def test_review_protects_qualifiers(old, new, expected):
    assert review.validate_change({"vi": old}, new) == expected

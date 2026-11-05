"""Display groups derived from the imported hierarchy, with safe broad fallbacks."""

from functools import lru_cache
import json
from pathlib import Path

GROUPS_FILE = Path(__file__).resolve().parents[2] / "data/library_groups.json"

GROUP_CORRECTIONS = {
    'Giá trị thang đo vấn đề': 'Mức độ vấn đề',
    'Thang đo Nhẹ Vừa Nặng': 'Thang đánh giá mức độ nhẹ, vừa, nặng',
    'Hệ thống vỏ bọc': 'Hệ da',
    'Hệ thống sinh dục niệu': 'Hệ sinh dục và tiết niệu',
    'Cấu trúc địa hình bề mặt': 'Giải phẫu bề mặt',
    'Tính bên': 'Bên cơ thể',
}

def group_title(label):
    return GROUP_CORRECTIONS.get(label, label)


@lru_cache(maxsize=1)
def groups():
    if not GROUPS_FILE.exists():
        return {"members": {}, "labels": {}}
    return json.loads(GROUPS_FILE.read_text(encoding="utf-8"))


def specific_group(data):
    if data.get("chapter_no") != "X":
        return None
    index = groups()
    key = data.get("linearization_uri", "").rsplit("/", 1)[-1]
    label = index["labels"].get(index["members"].get(key))
    return group_title(label) if label else None

"""Public descriptive labels; these are not trained-model classes or diagnoses."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.data.seed import SYMPTOMS as INITIAL
from app.data.library_expansion import SYMPTOMS as EXPANSION
from app.data.library_extended import SYMPTOMS as EXTENDED
from app.data.library_dermnet import SYMPTOMS as DERMNET

LABELS = {**INITIAL, **EXPANSION, **EXTENDED, **DERMNET}
VISUAL_LABELS = {
    code: name
    for code, name in LABELS.items()
    if code not in {"itch", "pain", "burning", "excessive-sweat", "nonhealing"}
}
SITES = {
    "unspecified": "Chưa chọn vị trí",
    "face": "Mặt",
    "scalp": "Da đầu / tóc",
    "trunk": "Ngực / lưng / bụng",
    "arms": "Cánh tay / bàn tay",
    "legs": "Chân / bàn chân",
    "folds": "Nếp gấp",
    "nails": "Móng",
    "mouth": "Môi / miệng",
    "other": "Vị trí khác",
}
ASSESSMENT_SLUGS = {
    "melanoma",
    "non-melanoma-skin-cancer",
    "basal-cell-carcinoma",
    "cutaneous-squamous-cell-carcinoma",
    "lentigo-maligna",
    "cutaneous-lupus-erythematosus",
    "morphoea",
    "dermatomyositis",
    "dermatitis-herpetiformis",
    "pemphigus-vulgaris",
    "bullous-pemphigoid",
    "epidermolysis-bullosa",
    "cutaneous-small-vessel-vasculitis",
    "urticarial-vasculitis",
    "telogen-effluvium",
    "excessive-sweating-hyperhidrosis",
}
URGENT_SLUGS = {"stevens-johnson-syndrome"}


class ObservationContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label_ids: list[str] = Field(default_factory=list, max_length=8)
    site: Literal[
        "unspecified", "face", "scalp", "trunk", "arms", "legs", "folds", "nails", "mouth", "other"
    ] = "unspecified"


def photo_scope(slug):
    if slug in URGENT_SLUGS:
        return {
            "code": "urgent",
            "name": "Cần đánh giá khẩn cấp",
            "note": "Không chờ kết quả ảnh khi có đau da, bong da, sốt hoặc loét niêm mạc lan rộng.",
        }
    if slug in ASSESSMENT_SLUGS:
        return {
            "code": "needs_assessment",
            "name": "Cần khám / xét nghiệm",
            "note": "Ảnh chỉ mô tả tổn thương; cần hỏi bệnh, khám và có thể xét nghiệm hoặc sinh thiết.",
        }
    return {
        "code": "visual_reference",
        "name": "Tham khảo hình thái qua ảnh",
        "note": "Có thể gợi ý hình thái; không xác nhận bệnh hoặc loại trừ bệnh khác chỉ từ ảnh.",
    }

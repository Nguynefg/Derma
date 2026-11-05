"""Optional local ResNet-18 adapter. Never downloads weights or accepts user checkpoints."""

import hashlib
import importlib.util
import json
import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class Label(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    disease_id: str | None = Field(default=None, min_length=1, max_length=80)
    display_name: str | None = Field(default=None, max_length=200)
    related_disease_ids: list[str] = Field(default_factory=list, max_length=50)


class ModelCard(BaseModel):
    version: str = Field(min_length=1, max_length=80)
    architecture: Literal["resnet18"]
    image_type: Literal["clinical", "dermoscopy"]
    input_size: Literal[224]
    classification_unit: Literal["disease", "group"] = "disease"
    data_limitations: list[str] = Field(default_factory=list, max_length=20)
    checkpoint: str
    checkpoint_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    dataset_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    labels: list[Label] = Field(min_length=2, max_length=50)
    minimum_score: float = Field(gt=0, lt=1)
    minimum_margin: float = Field(ge=0, lt=1)
    temperature: float = Field(gt=0, le=100)
    evaluation_report: str
    evaluation_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewed_for_research: bool
    reviewed_by: str = Field(min_length=1, max_length=150)
    usage_note: str = Field(min_length=10, max_length=1000)

    @model_validator(mode="after")
    def verified(self):
        if not self.reviewed_for_research:
            raise ValueError("Research review required")
        if len({x.label for x in self.labels}) != len(self.labels):
            raise ValueError("Duplicate labels")
        direct_ids = [x.disease_id for x in self.labels if x.disease_id]
        if len(set(direct_ids)) != len(direct_ids):
            raise ValueError("Ambiguous mapping")
        if self.classification_unit == "disease" and len(direct_ids) != len(self.labels):
            raise ValueError("Disease labels require explicit disease mapping")
        return self


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_configuration(card_path=None):
    if card_path is None and os.getenv("DERMA_IMAGE_MODEL_CARD") == "off":
        return None
    default = Path(__file__).resolve().parents[3] / "models" / "active" / "model-card.json"
    name = card_path or os.getenv("DERMA_IMAGE_MODEL_CARD") or default
    if not card_path and not os.getenv("DERMA_IMAGE_MODEL_CARD") and not default.is_file():
        return None
    path = Path(name).resolve()
    if path.stat().st_size > 64 * 1024:
        raise ValueError("Model card too large")
    card = ModelCard.model_validate_json(path.read_text(encoding="utf-8"))

    def asset(name):
        result = (path.parent / name).resolve()
        if not result.is_relative_to(path.parent):
            raise ValueError("Assets must remain in the model directory")
        return result

    checkpoint = asset(card.checkpoint)
    report_path = asset(card.evaluation_report)
    if checkpoint.stat().st_size > 100 * 1024 * 1024:
        raise ValueError("Checkpoint too large")
    if report_path.stat().st_size > 1024 * 1024:
        raise ValueError("Evaluation report too large")
    if (
        digest(checkpoint) != card.checkpoint_sha256
        or digest(report_path) != card.evaluation_sha256
    ):
        raise ValueError("Evidence checksum mismatch")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if (
        report.get("checkpoint_sha256") != card.checkpoint_sha256
        or report.get("dataset_manifest_sha256") != card.dataset_manifest_sha256
    ):
        raise ValueError("Evaluation and checkpoint mismatch")
    if (
        report.get("labels") != [x.label for x in card.labels]
        or report.get("image_type") != card.image_type
        or report.get("classification_unit", "disease") != card.classification_unit
    ):
        raise ValueError("Evaluation label/domain mismatch")
    if report.get("held_out_groups", 0) < 1 or type(report.get("held_out_groups")) is not int:
        raise ValueError("Held-out evaluation required")
    for metric in ["macro_f1", "balanced_accuracy"]:
        value = report.get(metric)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Invalid evaluation metric")
    expected = {
        "minimum_score": card.minimum_score,
        "minimum_margin": card.minimum_margin,
        "temperature": card.temperature,
    }
    if (
        report.get("validation_policy") != expected
        or report.get("policy_selected_on") != "validation"
    ):
        raise ValueError("Policy must come from validation")
    return card, checkpoint


def public_status():
    try:
        config = read_configuration()
        if not config:
            return {
                "status": "not_configured",
                "version": None,
                "message": "Chưa có mô hình ảnh đã kiểm thử; kiểm tra chất lượng ảnh vẫn hoạt động.",
            }
        card, _ = config
        available = (
            importlib.util.find_spec("torch") is not None
            and importlib.util.find_spec("torchvision") is not None
        )
        return {
            "status": "ready" if available else "runtime_unavailable",
            "version": card.version,
            "image_type": card.image_type,
            "label_count": len(card.labels),
            "classification_unit": card.classification_unit,
            "data_limitations": card.data_limitations,
            "message": (
                "Mô hình nghiên cứu đã cấu hình."
                if available
                else "Đã có cấu hình nhưng thiếu thư viện chạy mô hình."
            ),
        }
    except Exception:
        return {
            "status": "invalid_configuration",
            "version": None,
            "message": "Cấu hình hoặc bằng chứng kiểm thử chưa hợp lệ. Nhận diện ảnh chưa được bật.",
        }


@lru_cache(maxsize=1)
def load_runtime(path, sha, labels, manifest):
    import torch
    from torchvision import models, transforms

    version = tuple(int(part) for part in torch.__version__.split("+")[0].split(".")[:2])
    if version < (2, 6):
        raise ValueError("torch 2.6 or newer is required")
    if digest(Path(path)) != sha:
        raise ValueError("Checkpoint changed")
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if (
        checkpoint.get("architecture") != "resnet18"
        or checkpoint.get("labels") != list(labels)
        or checkpoint.get("manifest_sha256") != manifest
    ):
        raise ValueError("Checkpoint metadata mismatch")
    model = models.resnet18(weights=None)
    model.fc = torch.nn.Linear(model.fc.in_features, len(labels))
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    model.eval()
    transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )
    return model, transform


def score_image(image, card, checkpoint):
    import torch

    model, transform = load_runtime(
        str(checkpoint),
        card.checkpoint_sha256,
        tuple(x.label for x in card.labels),
        card.dataset_manifest_sha256,
    )
    with torch.inference_mode():
        logits = model(transform(image).unsqueeze(0))[0]
        if not torch.isfinite(logits).all():
            raise ValueError("Nonfinite output")
        return torch.softmax(logits / card.temperature, dim=0).tolist()


def analyze_with_model(image, image_type, quality, db):
    from app.modules.library.identifiers import find_record
    from app.database.connection import Disease

    def response(status, message, **extra):
        return {"status": status, "message": message, **extra}

    try:
        config = read_configuration()
        if not config:
            return response(
                "model_unavailable",
                "Đã kiểm tra chất lượng ảnh. Chưa có mô hình đã kiểm thử để nhận diện bệnh.",
            )
        card, checkpoint = config
        if image_type != card.image_type:
            return response(
                "out_of_scope",
                "Loại ảnh bạn chọn nằm ngoài phạm vi của mô hình.",
                model_version=card.version,
            )
        if any(issue.get("code") != "low_resolution" for issue in quality["issues"]):
            return response(
                "quality_review_required",
                "Hãy xem các lưu ý chất lượng và thử ảnh khác trước khi dùng mô hình.",
                model_version=card.version,
            )
        group_model = getattr(card, "classification_unit", "disease") == "group"
        mapped = [
            find_record(db, Disease, label.disease_id) if label.disease_id else None
            for label in card.labels
        ]
        if not group_model and any(item is None or not item.published for item in mapped):
            return response(
                "model_unavailable", "Ánh xạ chủ đề của mô hình chưa hợp lệ hoặc có bài đã ẩn."
            )
        scores = score_image(image, card, checkpoint)
        if (
            len(scores) != len(card.labels)
            or any(not math.isfinite(v) or not 0 <= v <= 1 for v in scores)
            or abs(sum(scores) - 1) > 0.001
        ):
            raise ValueError("Invalid scores")
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        if (
            scores[ranked[0]] < card.minimum_score
            or scores[ranked[0]] - scores[ranked[1]] < card.minimum_margin
        ):
            return response(
                "insufficient_confidence",
                "Mô hình chưa đủ chắc chắn để gợi ý chủ đề. Bạn có thể tra cứu bằng dấu hiệu.",
                model_version=card.version,
            )
        if group_model:
            label = card.labels[ranked[0]]
            related = []
            for disease_id in getattr(label, "related_disease_ids", []):
                topic = find_record(db, Disease, disease_id)
                if topic and topic.published:
                    related.append({"disease_id": topic.id, "name": topic.name})
            return response(
                "group_result",
                "Mô hình gợi ý một nhóm nhãn gộp từ tập huấn luyện, không xác định riêng bệnh và không phải chẩn đoán.",
                model_version=card.version,
                usage_note=card.usage_note,
                group={
                    "label": label.label,
                    "name": getattr(label, "display_name", None) or label.label,
                    "score": round(scores[ranked[0]], 4),
                },
                related_articles=related,
                score_notice="Điểm phân loại nhóm không phải xác suất mắc từng bệnh trong nhóm.",
            )
        return response(
            "research_result",
            "Gợi ý từ mô hình nghiên cứu, không phải kết luận chẩn đoán.",
            model_version=card.version,
            usage_note=card.usage_note,
            candidates=[
                {
                    "label": card.labels[i].label,
                    "disease_id": mapped[i].id,
                    "name": mapped[i].name,
                    "score": round(scores[i], 4),
                }
                for i in ranked[:3]
            ],
            score_notice="Điểm mô hình không phải xác suất bạn mắc bệnh. Điểm cao cũng không chứng minh ảnh thuộc phạm vi dữ liệu đã kiểm thử.",
        )
    except Exception:
        return response(
            "model_unavailable",
            "Chưa thể chạy mô hình với cấu hình hiện tại. Kết quả kiểm tra chất lượng ảnh vẫn được giữ.",
        )

import io
from types import SimpleNamespace
import pytest
from PIL import Image, ImageDraw, ImageFilter
from fastapi import HTTPException
from app.modules.images.image_analysis import Crop, decode_image, inspect_quality
import app.modules.images.image_model as image_model


def pattern(size=(512, 512)):
    image = Image.new("RGB", size, (100, 130, 155))
    draw = ImageDraw.Draw(image)
    for x in range(0, size[0], 12):
        draw.line((x, 0, x, size[1]), fill=(160, 175, 185), width=3)
    for y in range(0, size[1], 15):
        draw.line((0, y, size[0], y), fill=(70, 85, 110), width=2)
    return image


def encoded(image, fmt="PNG", **kwargs):
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, **kwargs)
    return buffer.getvalue()


@pytest.mark.parametrize("colour,expected", [(0, "too_dark"), (255, "too_bright")])
def test_exposure_warnings_are_technical_only(colour, expected):
    quality = inspect_quality(Image.new("RGB", (512, 512), (colour, colour, colour)))
    assert expected in {issue["code"] for issue in quality["issues"]}
    assert quality["status"] == "needs_review"
    assert "disease" not in quality and "predictions" not in quality


def test_detail_check_detects_loss_without_claiming_diagnosis():
    sharp = inspect_quality(pattern())
    blurred = inspect_quality(pattern().filter(ImageFilter.GaussianBlur(8)))
    assert sharp["metrics"]["detail_variance"] > blurred["metrics"]["detail_variance"]
    assert sharp["detail"] == "visible" and blurred["detail"] == "limited"


def test_exif_orientation_precedes_crop_and_metadata_is_removed():
    source = Image.new("RGB", (600, 400), "red")
    exif = Image.Exif()
    exif[274] = 6
    exif[270] = "private test metadata"
    image, meta, _ = decode_image(
        encoded(source, "JPEG", exif=exif), Crop(x=0, y=0, width=1, height=0.5)
    )
    assert (meta["original_width"], meta["original_height"]) == (400, 600)
    assert image.size == (400, 300)
    assert image.getexif() == {} and not image.info


def test_region_cannot_escape_image_or_be_too_small():
    with pytest.raises(ValueError):
        Crop(x=0.8, y=0, width=0.4, height=1)
    with pytest.raises(ValueError):
        Crop(x=float("nan"), y=0, width=1, height=1)
    with pytest.raises(HTTPException) as caught:
        decode_image(encoded(pattern()), Crop(x=0, y=0, width=0.2, height=0.2))
    assert caught.value.status_code == 422


def test_transparency_is_reported_not_treated_as_clear_photo():
    image, meta, alpha = decode_image(encoded(Image.new("RGBA", (512, 512), (20, 20, 20, 0))))
    assert alpha == 1
    assert "transparency" in {i["code"] for i in inspect_quality(image, alpha)["issues"]}
    assert image.mode == "RGB"


def test_disabled_model_never_returns_candidates(monkeypatch):
    monkeypatch.setenv("DERMA_IMAGE_MODEL_CARD", "off")
    result = image_model.analyze_with_model(pattern(), "clinical", {"issues": []}, None)
    assert result["status"] == "model_unavailable"
    assert "candidates" not in result


def test_config_failure_is_closed_and_does_not_expose_paths(monkeypatch, tmp_path):
    monkeypatch.setenv("DERMA_IMAGE_MODEL_CARD", str(tmp_path / "private-file.json"))
    status = image_model.public_status()
    assert status["status"] == "invalid_configuration"
    assert str(tmp_path) not in str(status)


def test_adapter_abstains_before_inference_and_links_only_published_topics(monkeypatch):
    monkeypatch.setattr(
        "app.modules.library.identifiers.find_record", lambda db, model, key: db.get(model, key)
    )
    labels = [
        SimpleNamespace(label="a", disease_id="acne"),
        SimpleNamespace(label="b", disease_id="psoriasis"),
    ]
    card = SimpleNamespace(
        version="test-only",
        image_type="dermoscopy",
        labels=labels,
        minimum_score=0.8,
        minimum_margin=0.2,
        usage_note="Synthetic unit test configuration",
    )
    monkeypatch.setattr(image_model, "read_configuration", lambda: (card, None))
    db = SimpleNamespace(get=lambda model, key: SimpleNamespace(id=key, name=key, published=True))
    calls = []

    def scores(*args):
        calls.append(True)
        return [0.9, 0.1]

    monkeypatch.setattr(image_model, "score_image", scores)
    assert (
        image_model.analyze_with_model(pattern(), "clinical", {"issues": []}, db)["status"]
        == "out_of_scope"
    )
    assert (
        image_model.analyze_with_model(pattern(), "dermoscopy", {"issues": [{}]}, db)["status"]
        == "quality_review_required"
    )
    assert not calls
    result = image_model.analyze_with_model(pattern(), "dermoscopy", {"issues": []}, db)
    assert result["status"] == "research_result" and result["candidates"][0]["disease_id"] == "acne"
    monkeypatch.setattr(image_model, "score_image", lambda *args: [0.55, 0.45])
    result = image_model.analyze_with_model(pattern(), "dermoscopy", {"issues": []}, db)
    assert result["status"] == "insufficient_confidence" and "candidates" not in result
    db.get = lambda model, key: SimpleNamespace(id=key, name=key, published=False)
    assert (
        image_model.analyze_with_model(pattern(), "dermoscopy", {"issues": []}, db)["status"]
        == "model_unavailable"
    )


def configuration_fixture(tmp_path):
    import json, hashlib

    # Deliberately non-model bytes. This tests evidence validation, never inference.
    checkpoint = tmp_path / "test-only.pt"
    checkpoint.write_bytes(b"non-model test fixture")
    checkpoint_hash = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    policy = {"minimum_score": 0.8, "minimum_margin": 0.2, "temperature": 1.0}
    report = {
        "checkpoint_sha256": checkpoint_hash,
        "dataset_manifest_sha256": "a" * 64,
        "labels": ["a", "b"],
        "image_type": "clinical",
        "held_out_groups": 5,
        "macro_f1": 0.6,
        "balanced_accuracy": 0.6,
        "validation_policy": policy,
        "policy_selected_on": "validation",
    }
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    card = {
        "version": "test-only",
        "architecture": "resnet18",
        "image_type": "clinical",
        "input_size": 224,
        "checkpoint": "test-only.pt",
        "checkpoint_sha256": checkpoint_hash,
        "dataset_manifest_sha256": "a" * 64,
        "labels": [{"label": "a", "disease_id": "acne"}, {"label": "b", "disease_id": "psoriasis"}],
        **policy,
        "evaluation_report": "report.json",
        "evaluation_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        "reviewed_for_research": True,
        "reviewed_by": "unit test fixture",
        "usage_note": "Only a synthetic test; not a tested medical model.",
    }
    return card, report_path


def test_group_classifier_does_not_turn_combined_labels_into_a_diagnosis(monkeypatch):
    monkeypatch.setattr(
        "app.modules.library.identifiers.find_record", lambda db, model, key: db.get(model, key)
    )
    labels = [
        SimpleNamespace(
            label="Acne and Rosacea",
            display_name="Mụn và trứng cá đỏ",
            disease_id=None,
            related_disease_ids=["acne", "rosacea"],
        ),
        SimpleNamespace(
            label="Other group", display_name="Nhóm khác", disease_id=None, related_disease_ids=[]
        ),
    ]
    card = SimpleNamespace(
        version="synthetic-group-test",
        classification_unit="group",
        image_type="clinical",
        labels=labels,
        minimum_score=0.8,
        minimum_margin=0.2,
        usage_note="Synthetic test only",
    )
    monkeypatch.setattr(image_model, "read_configuration", lambda: (card, None))
    monkeypatch.setattr(image_model, "score_image", lambda *args: [0.9, 0.1])
    db = SimpleNamespace(get=lambda model, key: SimpleNamespace(id=key, name=key, published=True))
    result = image_model.analyze_with_model(pattern(), "clinical", {"issues": []}, db)
    assert result["status"] == "group_result"
    assert result["group"]["label"] == "Acne and Rosacea"
    assert "candidates" not in result
    assert [r["disease_id"] for r in result["related_articles"]] == ["acne", "rosacea"]


def test_model_configuration_requires_matching_evidence(monkeypatch, tmp_path):
    import json

    card, _ = configuration_fixture(tmp_path)
    card_path = tmp_path / "card.json"
    card_path.write_text(json.dumps(card), encoding="utf-8")
    monkeypatch.setenv("DERMA_IMAGE_MODEL_CARD", str(card_path))
    parsed, checkpoint = image_model.read_configuration()
    assert parsed.version == "test-only" and checkpoint.name == "test-only.pt"
    checkpoint.write_bytes(b"changed")
    with pytest.raises(ValueError):
        image_model.read_configuration()


@pytest.mark.parametrize(
    "change",
    [
        {"reviewed_for_research": False},
        {"minimum_score": 1.2},
        {"checkpoint": "../outside.pt"},
        {"evaluation_sha256": "b" * 64},
        {
            "labels": [
                {"label": "same", "disease_id": "acne"},
                {"label": "same", "disease_id": "psoriasis"},
            ]
        },
    ],
)
def test_invalid_model_configuration_stays_disabled(change, monkeypatch, tmp_path):
    import json

    card, _ = configuration_fixture(tmp_path)
    card.update(change)
    path = tmp_path / "card.json"
    path.write_text(json.dumps(card), encoding="utf-8")
    monkeypatch.setenv("DERMA_IMAGE_MODEL_CARD", str(path))
    assert image_model.public_status()["status"] == "invalid_configuration"

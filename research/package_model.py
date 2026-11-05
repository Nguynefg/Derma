"""Evaluate real weights, choose policy on validation, and package an optional research model."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def main(args):
    import pandas as pd
    import torch
    from torch.utils.data import DataLoader
    from torchvision import models, transforms
    from train import Images
    from sklearn.metrics import (
        f1_score,
        balanced_accuracy_score,
        classification_report,
        confusion_matrix,
    )
    from model_policy import choose_policy, policy_statistics

    torch.set_num_threads(4)

    if args.reviewed_for_research and not args.reviewed_by.strip():
        raise ValueError("A real reviewer name is required for research review")
    manifest = Path(args.manifest).resolve()
    frame = pd.read_csv(manifest)
    required = {"path", "dx", "split", "group_by", "sha256"}
    if not required <= set(frame.columns) or frame[list(required)].isna().any().any():
        raise ValueError("Use prepare_split.py with complete labelled data")
    groups = frame.group_by.unique().tolist()
    if len(groups) != 1 or groups[0] not in frame.columns or frame[groups[0]].isna().any():
        raise ValueError("Missing consistent patient/lesion groups")
    if set(frame.split) != {"train", "validation", "test"}:
        raise ValueError("Train, validation and test partitions required")
    if (
        frame.groupby(groups[0]).split.nunique().max() > 1
        or frame.groupby("sha256").split.nunique().max() > 1
    ):
        raise ValueError("Data leakage detected")
    labels = sorted(frame.dx.unique().tolist())
    if any(
        set(frame[frame.split == part].dx) != set(labels)
        for part in ["train", "validation", "test"]
    ):
        raise ValueError("Every partition must contain every label")
    if "image_type" in frame and (
        frame.image_type.isna().any() or set(frame.image_type) != {args.image_type}
    ):
        raise ValueError("Image domain does not match package")
    for row in frame.itertuples():
        if hashlib.sha256(Path(row.path).read_bytes()).hexdigest() != row.sha256:
            raise ValueError("Dataset changed after split was locked")
    manifest_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()
    checkpoint_path = Path(args.checkpoint).resolve()
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if (
        checkpoint.get("labels") != labels
        or checkpoint.get("manifest_sha256") != manifest_hash
        or checkpoint.get("architecture") != "resnet18"
    ):
        raise ValueError("Checkpoint and dataset do not match")
    mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
    if set(mapping) != set(labels):
        raise ValueError("Mapping must contain every original label, with no extra labels")
    grouped = any(isinstance(value, dict) for value in mapping.values())
    if grouped and not all(
        isinstance(value, dict)
        and isinstance(value.get("display_name"), str)
        and isinstance(value.get("related_disease_ids"), list)
        for value in mapping.values()
    ):
        raise ValueError("Every group must have display_name and related_disease_ids")
    if not grouped and (
        len(set(mapping.values())) != len(labels)
        or any(not isinstance(value, str) or not value for value in mapping.values())
    ):
        raise ValueError("Disease labels require distinct disease IDs")
    output = Path(args.output).resolve()
    if output.exists():
        raise FileExistsError("Preserve evaluation; choose a new package directory")
    # Reserve before reading test predictions. Do not overwrite or tune on repeated test runs.
    output.mkdir(parents=True)
    (output / "evaluation-started.txt").write_text(
        "Evaluation of this package has started. Preserve this directory.\n", encoding="utf-8"
    )
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

    def loader(part):
        return DataLoader(
            Images(frame[frame.split == part], labels, transform),
            batch_size=32,
            shuffle=False,
            num_workers=0,
        )

    def predictions(part):
        logits, targets = [], []
        with torch.inference_mode():
            for images, y in loader(part):
                logits.extend(model(images).tolist())
                targets.extend(y.tolist())
        return logits, targets

    validation_logits, validation_targets = predictions("validation")
    policy, validation = choose_policy(validation_logits, validation_targets)
    # The policy is frozen before any test evaluation.
    test_logits, test_targets = predictions("test")
    predicted = [max(range(len(row)), key=lambda i: row[i]) for row in test_logits]
    metrics = {
        "macro_f1": float(f1_score(test_targets, predicted, average="macro", zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(test_targets, predicted)),
        "classification_report": classification_report(
            test_targets,
            predicted,
            labels=list(range(len(labels))),
            target_names=labels,
            output_dict=True,
            zero_division=0,
        ),
        "confusion_matrix": confusion_matrix(
            test_targets, predicted, labels=list(range(len(labels)))
        ).tolist(),
        "n": len(test_targets),
    }
    checkpoint_hash = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    report = {
        **metrics,
        "checkpoint_sha256": checkpoint_hash,
        "dataset_manifest_sha256": manifest_hash,
        "labels": labels,
        "image_type": args.image_type,
        "classification_unit": "group" if grouped else "disease",
        "group_unit": groups[0],
        "patient_grouping_available": groups[0] == "patient_id",
        "held_out_groups": int(frame[frame.split == "test"][groups[0]].nunique()),
        "preprocessing": "resize224-imagenet-v1",
        "validation_policy": policy,
        "policy_selected_on": "validation",
        "validation_selective_metrics": validation,
        "test_selective_metrics": policy_statistics(test_logits, test_targets, policy),
        "notice": "Research evaluation only; not clinical validation or a reliable out-of-distribution detector.",
    }
    report_path = output / "evaluation.json"
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    shutil.copyfile(checkpoint_path, output / "best.pt")
    card = {
        "version": args.version,
        "architecture": "resnet18",
        "image_type": args.image_type,
        "input_size": 224,
        "checkpoint": "best.pt",
        "checkpoint_sha256": checkpoint_hash,
        "dataset_manifest_sha256": manifest_hash,
        "classification_unit": "group" if grouped else "disease",
        "labels": [
            (
                {"label": label, "disease_id": None, **mapping[label]}
                if grouped
                else {"label": label, "disease_id": mapping[label]}
            )
            for label in labels
        ],
        **policy,
        "evaluation_report": "evaluation.json",
        "evaluation_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        "reviewed_for_research": args.reviewed_for_research,
        "reviewed_by": args.reviewed_by or "Not reviewed",
        "data_limitations": (["Nhãn gộp nhiều bệnh; không xác định bệnh riêng."] if grouped else [])
        + (
            []
            if groups[0] == "patient_id"
            else ["Chưa có chia theo người bệnh; không biết mức trùng người giữa các tập."]
        )
        + ["Chưa thẩm định lâm sàng."],
        "usage_note": "Research model; suggestions are not confirmed diagnoses. Review population, image domain and limitations before use.",
    }
    (output / "model-card.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
    print("Packaged real checkpoint and evaluation. Research review:", args.reviewed_for_research)
    print("No web configuration or database records were changed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--image-type", choices=["clinical", "dermoscopy"], required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--reviewed-for-research", action="store_true")
    parser.add_argument("--reviewed-by", default="")
    main(parser.parse_args())

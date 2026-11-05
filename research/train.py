"""Offline ResNet-18 baseline. No deployment or clinical performance claim.
Train: python train.py --manifest artifacts/split.csv --out artifacts/run-01 --epochs 10
Test (after model selection): python train.py --manifest artifacts/split.csv --out artifacts/run-01 --evaluate-test
"""

import argparse
import hashlib
import json
import random
import time
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from PIL import Image, ImageOps
from sklearn.metrics import (
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms


class Images(Dataset):
    def __init__(self, frame, labels, transform):
        self.frame, self.labels, self.transform = frame.reset_index(drop=True), labels, transform

    def __len__(self):
        return len(self.frame)

    def __getitem__(self, index):
        row = self.frame.iloc[index]
        with Image.open(row.path) as image:
            image = ImageOps.exif_transpose(image)
            if "A" in image.getbands() or "transparency" in image.info:
                rgba = image.convert("RGBA")
                image = Image.alpha_composite(
                    Image.new("RGBA", rgba.size, (127, 127, 127, 255)), rgba
                )
            image = self.transform(image.convert("RGB"))
        return image, self.labels.index(row.dx)


def evaluate(model, loader, device, labels):
    model.eval()
    targets, predictions = [], []
    with torch.inference_mode():
        for x, y in loader:
            predictions.extend(model(x.to(device)).argmax(1).cpu().tolist())
            targets.extend(y.tolist())
    return {
        "macro_f1": f1_score(targets, predictions, average="macro", zero_division=0),
        "balanced_accuracy": balanced_accuracy_score(targets, predictions),
        "classification_report": classification_report(
            targets,
            predictions,
            labels=list(range(len(labels))),
            target_names=labels,
            output_dict=True,
            zero_division=0,
        ),
        "confusion_matrix": confusion_matrix(
            targets, predictions, labels=list(range(len(labels)))
        ).tolist(),
        "n": len(targets),
    }


def main(args):
    torch.set_num_threads(args.threads)
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(42)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    manifest = Path(args.manifest)
    frame = pd.read_csv(manifest)
    required = {"path", "dx", "split", "group_by", "sha256"}
    if not required <= set(frame.columns):
        raise ValueError("Use prepare_split.py to create the manifest.")
    if not set(frame.split) == {"train", "validation", "test"}:
        raise ValueError("Invalid splits.")
    group_column = frame.group_by.iloc[0]
    if frame.groupby(group_column).split.nunique().max() > 1:
        raise ValueError("Group leakage detected.")
    if frame.groupby("sha256").split.nunique().max() > 1:
        raise ValueError("Image leakage detected.")
    labels = sorted(frame.dx.unique().tolist())
    manifest_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # Same deterministic preprocessing as the serving adapter.
    eval_transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )
    train_transform = transforms.Compose(
        [
            transforms.Resize((256, 256)),
            transforms.RandomResizedCrop(224, scale=(0.85, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )
    model = models.resnet18(weights=None if args.evaluate_test else models.ResNet18_Weights.DEFAULT)
    model.fc = nn.Linear(model.fc.in_features, len(labels))
    if args.freeze_backbone:
        for parameter in model.parameters():
            parameter.requires_grad = False
        for parameter in model.fc.parameters():
            parameter.requires_grad = True
    model.to(device)

    def loader(split, training=False):
        return DataLoader(
            Images(
                frame[frame.split == split], labels, train_transform if training else eval_transform
            ),
            batch_size=args.batch_size,
            shuffle=training,
            num_workers=0,
        )

    if args.evaluate_test:
        report_path = out / "test_metrics.json"
        if report_path.exists():
            raise FileExistsError(
                "Test report already exists. Keep the first evaluation; do not tune on test."
            )
        checkpoint = torch.load(out / "best.pt", map_location=device, weights_only=True)
        if checkpoint["manifest_sha256"] != manifest_hash or checkpoint["labels"] != labels:
            raise ValueError("Checkpoint and manifest mismatch.")
        model.load_state_dict(checkpoint["state_dict"])
        metrics = evaluate(model, loader("test"), device, labels)
        report_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        print(json.dumps(metrics, indent=2))
        return
    if (out / "best.pt").exists():
        raise FileExistsError("Use a new run directory; existing checkpoint is preserved.")
    if args.epochs < 1:
        raise ValueError("epochs must be positive")
    train_frame = frame[frame.split == "train"]
    counts = train_frame.dx.value_counts()
    weights = torch.tensor(
        [len(train_frame) / (len(labels) * counts[label]) for label in labels],
        dtype=torch.float32,
        device=device,
    )
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(
        (p for p in model.parameters() if p.requires_grad), lr=args.learning_rate, weight_decay=1e-4
    )
    best = -1.0
    logs = []
    train_loader, validation_loader = loader("train", True), loader("validation")
    for epoch in range(args.epochs):
        model.train()
        if args.freeze_backbone:
            model.eval()
            model.fc.train()
        total_loss = 0.0
        started = time.monotonic()
        for batch, (x, y) in enumerate(train_loader, 1):
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(y)
            if batch % 25 == 0:
                print(
                    f"Epoch {epoch+1}/{args.epochs}, batch {batch}/{len(train_loader)}, elapsed {time.monotonic()-started:.0f}s",
                    flush=True,
                )
        metrics = evaluate(model, validation_loader, device, labels)
        logs.append(
            {"epoch": epoch + 1, "train_loss": total_loss / len(train_frame), "validation": metrics}
        )
        if metrics["macro_f1"] > best:
            best = metrics["macro_f1"]
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "labels": labels,
                    "manifest_sha256": manifest_hash,
                    "architecture": "resnet18",
                    "epoch": epoch + 1,
                },
                out / "best.pt",
            )
        print(f'Epoch {epoch+1}: validation macro-F1={metrics["macro_f1"]:.4f}', flush=True)
    (out / "training.json").write_text(
        json.dumps(
            {
                "seed": 42,
                "device": str(device),
                "torch_version": torch.__version__,
                "manifest_sha256": manifest_hash,
                "epochs": logs,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("Training complete. Evaluate held-out test only after freezing all model choices.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--evaluate-test", action="store_true")
    parser.add_argument("--freeze-backbone", action="store_true")
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--threads", type=int, default=4)
    main(parser.parse_args())

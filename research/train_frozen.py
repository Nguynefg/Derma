"""Train a frozen ImageNet ResNet-18 plus a learned classification head.

Extracts train/validation features once; never reads test images or labels for
model selection. This is a research baseline, not clinical validation.
"""

import argparse
import hashlib
import json
import random
import time
from pathlib import Path


def main(args):
    import numpy as np
    import pandas as pd
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset
    from torchvision import models, transforms
    from sklearn.metrics import f1_score, balanced_accuracy_score
    from train import Images

    torch.set_num_threads(4)
    torch.manual_seed(42)
    random.seed(42)
    np.random.seed(42)
    manifest = Path(args.manifest).resolve()
    frame = pd.read_csv(manifest)
    group = frame.group_by.iloc[0]
    if (
        frame.groupby(group).split.nunique().max() > 1
        or frame.groupby("sha256").split.nunique().max() > 1
    ):
        raise ValueError("Split leakage")
    labels = sorted(frame.dx.unique().tolist())
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:", device, "Labels:", len(labels), flush=True)
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT).to(device)
    model.fc = nn.Identity()
    model.eval()
    transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )
    features = {}
    for part in ["train", "validation"]:
        loader = DataLoader(
            Images(frame[frame.split == part], labels, transform),
            batch_size=args.batch_size,
            shuffle=False,
            num_workers=0,
        )
        values = []
        targets = []
        started = time.monotonic()
        with torch.inference_mode():
            for index, (images, y) in enumerate(loader, 1):
                values.append(model(images.to(device)).cpu())
                targets.append(y)
                if index % 10 == 0 or index == len(loader):
                    print(
                        f"{part}: batch {index}/{len(loader)}, {time.monotonic()-started:.0f}s",
                        flush=True,
                    )
        features[part] = (torch.cat(values), torch.cat(targets))
        torch.save(
            {"features": features[part][0], "targets": features[part][1]},
            out / (part + "-features.pt"),
        )
    head = nn.Linear(512, len(labels)).to(device)
    x, y = features["train"]
    vx, vy = features["validation"]
    vx = vx.to(device)
    counts = torch.bincount(y, minlength=len(labels)).float()
    if (counts == 0).any():
        raise ValueError("Missing training class")
    loss_fn = nn.CrossEntropyLoss(weight=(len(y) / (len(labels) * counts)).to(device))
    optimizer = torch.optim.AdamW(head.parameters(), lr=0.003, weight_decay=0.01)
    loader = DataLoader(TensorDataset(x, y), batch_size=256, shuffle=True)
    best = -1
    logs = []
    for epoch in range(args.epochs):
        head.train()
        total = 0.0
        for fx, fy in loader:
            optimizer.zero_grad()
            loss = loss_fn(head(fx.to(device)), fy.to(device))
            loss.backward()
            optimizer.step()
            total += loss.item() * len(fy)
        head.eval()
        with torch.inference_mode():
            pred = head(vx).argmax(1).cpu().numpy()
        metrics = {
            "macro_f1": float(f1_score(vy.numpy(), pred, average="macro", zero_division=0)),
            "balanced_accuracy": float(balanced_accuracy_score(vy.numpy(), pred)),
        }
        logs.append({"epoch": epoch + 1, "loss": total / len(y), "validation": metrics})
        print(
            f'Epoch {epoch+1}/{args.epochs}: validation macro-F1={metrics["macro_f1"]:.4f}',
            flush=True,
        )
        if metrics["macro_f1"] > best:
            best = metrics["macro_f1"]
            state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            state.update(
                {
                    "fc.weight": head.weight.detach().cpu().clone(),
                    "fc.bias": head.bias.detach().cpu().clone(),
                }
            )
            torch.save(
                {
                    "architecture": "resnet18",
                    "state_dict": state,
                    "labels": labels,
                    "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                    "epoch": epoch + 1,
                },
                out / "best.pt",
            )
    (out / "training.json").write_text(
        json.dumps(
            {
                "device": str(device),
                "architecture": "resnet18",
                "frozen_backbone": True,
                "seed": 42,
                "best_validation_macro_f1": best,
                "group_unit": group,
                "patient_grouping_available": group == "patient_id",
                "epochs": logs,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("Saved best.pt. Test set remains untouched.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--batch-size", type=int, default=32)
    main(parser.parse_args())

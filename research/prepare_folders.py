"""Audit supplied train/test class folders, preserve original labels, exclude hash leakage.

No patient IDs are available: splits are by file hash, not by patient. Do not
report patient-independent validation from this manifest.
"""

import argparse
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image


def prepare(root, output):
    root = Path(root).resolve()
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError("Use a new audit directory")
    rows = []
    bad = []
    labels = {}
    for part in ["train", "test"]:
        folders = sorted(p for p in (root / part).iterdir() if p.is_dir())
        labels[part] = [p.name for p in folders]
        for folder in folders:
            for path in sorted(folder.rglob("*")):
                if not path.is_file():
                    continue
                try:
                    content = path.read_bytes()
                    with Image.open(path) as image:
                        width, height = image.size
                        image.verify()
                    if min(width, height) < 32:
                        raise ValueError("Too small")
                    rows.append(
                        dict(
                            path=str(path),
                            dx=folder.name,
                            split=part,
                            sha256=hashlib.sha256(content).hexdigest(),
                            width=width,
                            height=height,
                            group_by="sha256",
                            image_type="clinical",
                        )
                    )
                except Exception:
                    bad.append(str(path))
            print(part, folder.name, len(rows), flush=True)
    if labels["train"] != labels["test"]:
        raise ValueError("Class folders differ between train and test")
    buckets = defaultdict(list)
    for row in rows:
        buckets[row["sha256"]].append(row)
    kept = []
    conflicts = duplicates = cross_split = 0
    for records in buckets.values():
        if len({r["dx"] for r in records}) > 1:
            conflicts += len(records)
            continue
        cross_split += int(len({r["split"] for r in records}) > 1)
        duplicates += len(records) - 1
        kept.append(next((r for r in records if r["split"] == "test"), records[0]))
    randomizer = random.Random(42)
    for label in labels["train"]:
        training = sorted(
            (r for r in kept if r["dx"] == label and r["split"] == "train"),
            key=lambda r: r["sha256"],
        )
        testing = [r for r in kept if r["dx"] == label and r["split"] == "test"]
        if len(training) < 10 or not testing:
            raise ValueError("Insufficient remaining files for class " + label)
        randomizer.shuffle(training)
        for row in training[: max(1, round(len(training) * 0.2))]:
            row["split"] = "validation"
    output.mkdir(parents=True)
    with (output / "manifest.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(kept[0]))
        writer.writeheader()
        writer.writerows(kept)
    summary = {
        "source": str(root),
        "classes": len(labels["train"]),
        "raw_images": len(rows),
        "invalid_files": bad,
        "excluded_conflicting_label_files": conflicts,
        "excluded_duplicates": duplicates,
        "cross_split_duplicate_hashes": cross_split,
        "split_counts": dict(Counter(r["split"] for r in kept)),
        "class_counts": {
            label: dict(Counter(r["split"] for r in kept if r["dx"] == label))
            for label in labels["train"]
        },
        "group_unit": "file_sha256",
        "patient_grouping_available": False,
        "limitations": [
            "No patient/lesion metadata: patient overlap is unknown.",
            "Near-duplicates are not detected.",
            "Original folder labels combine multiple diseases; cannot assign a single diagnosis.",
            "Source and usage terms have not been independently verified.",
        ],
    }
    (output / "audit.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {k: v for k, v in summary.items() if k not in {"class_counts", "invalid_files"}},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    prepare(args.root, args.output)

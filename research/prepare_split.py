"""Create a grouped HAM10000 split; never download restricted data automatically.
python prepare_split.py --metadata data/HAM10000_metadata.csv --images data/images --output artifacts/split.csv
"""

import argparse
import hashlib
from pathlib import Path
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold


def prepare(metadata, images, output):
    df = pd.read_csv(metadata)
    required = {"image_id", "lesion_id", "dx"}
    if not required <= set(df.columns) or df[list(required)].isna().any().any():
        raise ValueError("Missing image_id, lesion_id or dx.")
    if df.image_id.duplicated().any():
        raise ValueError("Duplicate image IDs; resolve provenance before splitting.")
    files = {}
    for path in Path(images).rglob("*"):
        if path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            if path.stem in files:
                raise ValueError(f"Duplicate file stem: {path.stem}")
            files[path.stem] = path.resolve()
    if not set(df.image_id) <= files.keys():
        raise ValueError("Some image files are missing.")
    df["path"] = df.image_id.map(lambda x: str(files[x]))
    df["sha256"] = df.path.map(lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest())
    # Exact duplicates with conflicting labels are unsafe to silently collapse.
    if (df.groupby("sha256").dx.nunique() > 1).any():
        raise ValueError("Identical image content has conflicting labels.")
    if df.sha256.duplicated().any():
        raise ValueError("Duplicate image content found. Resolve lesion grouping first.")
    # 60/20/20 split: group by patient if available, otherwise lesion.
    group_column = (
        "patient_id"
        if "patient_id" in df.columns and not df.patient_id.isna().any()
        else "lesion_id"
    )
    groups = df[group_column]
    if group_column == "patient_id" and (df.groupby("lesion_id").patient_id.nunique() > 1).any():
        raise ValueError("Lesion has conflicting patient IDs.")
    counts = df.groupby("dx")[group_column].nunique()
    if (counts < 5).any():
        raise ValueError(
            "Each label needs at least five independent groups for this split strategy."
        )
    folds = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    df["split"] = "train"
    for fold, (_, indices) in enumerate(folds.split(df, df.dx, groups)):
        if fold < 2:
            df.loc[indices, "split"] = "test" if fold == 0 else "validation"
    for a, b in [("train", "test"), ("train", "validation"), ("test", "validation")]:
        assert not (
            set(df.loc[df.split == a, group_column]) & set(df.loc[df.split == b, group_column])
        )
    labels = set(df.dx)
    if any(set(df.loc[df.split == s, "dx"]) != labels for s in ["train", "validation", "test"]):
        raise ValueError("A split is missing labels. Review grouping and dataset size.")
    df["group_by"] = group_column
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError("Split manifest exists; use a new versioned output path.")
    df.to_csv(target, index=False)
    print(pd.crosstab(df.dx, df.split).to_string())
    print(f"Grouping: {group_column}; inspect near-duplicates separately.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--images", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    prepare(args.metadata, args.images, args.output)

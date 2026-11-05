import csv
import importlib.util
import json
from pathlib import Path
from PIL import Image

spec = importlib.util.spec_from_file_location(
    "derma_prepare_folders", Path(__file__).resolve().parents[2] / "research/prepare_folders.py"
)
folders = importlib.util.module_from_spec(spec)
spec.loader.exec_module(folders)


def test_folder_audit_preserves_groups_and_removes_hash_leakage(tmp_path):
    root = tmp_path / "source"
    index = 0
    for split, count in [("train", 12), ("test", 3)]:
        for label in ["Mixed diseases A", "Disease B"]:
            directory = root / split / label
            directory.mkdir(parents=True)
            for i in range(count):
                index += 1
                Image.new("RGB", (32, 32), (index, 0, 0)).save(directory / f"{i}.png")
    original = root / "train/Mixed diseases A/0.png"
    (root / "test/Mixed diseases A/duplicate.png").write_bytes(original.read_bytes())
    conflict = root / "train/Mixed diseases A/1.png"
    (root / "train/Disease B/conflict.png").write_bytes(conflict.read_bytes())
    output = tmp_path / "prepared"
    folders.prepare(root, output)
    audit = json.loads((output / "audit.json").read_text())
    assert audit["classes"] == 2 and audit["excluded_conflicting_label_files"] == 2
    assert audit["cross_split_duplicate_hashes"] == 1
    assert not audit["patient_grouping_available"]
    with (output / "manifest.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert {r["dx"] for r in rows} == {"Mixed diseases A", "Disease B"}
    for digest in {r["sha256"] for r in rows}:
        assert len({r["split"] for r in rows if r["sha256"] == digest}) == 1
    assert original.exists() and conflict.exists()

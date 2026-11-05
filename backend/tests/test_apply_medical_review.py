import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

path = Path(__file__).resolve().parents[2] / "scripts/translation/apply_medical_review.py"
spec = importlib.util.spec_from_file_location("apply_review_job", path)
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)


@pytest.fixture
def review_files(tmp_path, monkeypatch):
    monkeypatch.setattr(job, "FOLDER", tmp_path)
    package = tmp_path / "package.json"
    cache = tmp_path / "cache.json"
    monkeypatch.setattr(job, "PACKAGED_TRANSLATIONS", package)
    monkeypatch.setattr(job, "TRANSLATION_FILE", cache)
    rows = [
        {"id": 0, "source": "Left-sided condition", "vi": "Bệnh bên trái"},
        {"id": 1, "source": "Other condition", "vi": "Tên cũ"},
    ]
    frozen = tmp_path / "input.json"
    frozen.write_text(json.dumps(rows), encoding="utf-8")
    state = {
        "status": "complete",
        "reviewed_ids": [0, 1],
        "input_sha256": hashlib.sha256(frozen.read_bytes()).hexdigest(),
        "changes": {
            rows[0]["source"]: {
                "before": rows[0]["vi"],
                "after": "Bệnh bên phải",
                "reason": "test",
            },
            rows[1]["source"]: {"before": rows[1]["vi"], "after": "Tên mới", "reason": "test"},
        },
        "rejected_changes": {},
    }
    (tmp_path / "progress.json").write_text(json.dumps(state), encoding="utf-8")
    verification = {
        "status": "complete",
        "verified": {
            source: hashlib.sha256(proposal["after"].encode("utf-8")).hexdigest()
            for source, proposal in state["changes"].items()
        },
        "corrections": {},
        "flagged": {},
    }
    (tmp_path / "verification.json").write_text(json.dumps(verification), encoding="utf-8")
    data = {"translations": {r["source"]: r["vi"] for r in rows}}
    for p in [package, cache]:
        p.write_text(json.dumps(data), encoding="utf-8")
    return tmp_path, package, cache, state


def test_apply_rechecks_proposals_and_preserves_originals(review_files):
    folder, package, cache, state = review_files
    result = job.apply_review()
    assert result["changed_titles"] == 1 and result["unresolved_proposals"] == 1
    data = json.loads(package.read_text(encoding="utf-8"))
    assert data["translations"]["Left-sided condition"] == "Bệnh bên trái"
    assert data["translations"]["Other condition"] == "Tên mới"
    assert package.read_bytes() == cache.read_bytes()
    assert (folder / "before-apply.json").exists()


def test_incomplete_review_cannot_overwrite_dictionary(review_files):
    folder, package, cache, state = review_files
    state["reviewed_ids"] = [0]
    (folder / "progress.json").write_text(json.dumps(state), encoding="utf-8")
    before = package.read_bytes()
    with pytest.raises(ValueError, match="not complete"):
        job.apply_review()
    assert package.read_bytes() == cache.read_bytes() == before


def test_apply_cannot_overwrite_intervening_edits(review_files):
    folder, package, cache, state = review_files
    package.write_text(
        json.dumps({"translations": {"Left-sided condition": "Tên người dùng sửa"}}),
        encoding="utf-8",
    )
    before = package.read_bytes()
    with pytest.raises(ValueError, match="differs"):
        job.apply_review()
    assert package.read_bytes() == before


@pytest.mark.parametrize("problem", ["missing", "incomplete", "stale"])
def test_unverified_proposals_cannot_overwrite_dictionary(review_files, problem):
    folder, package, cache, state = review_files
    path = folder / "verification.json"
    verification = json.loads(path.read_text(encoding="utf-8"))
    if problem == "missing":
        path.unlink()
    else:
        if problem == "incomplete":
            verification["status"] = "running"
        else:
            verification["verified"]["Other condition"] = "stale-fingerprint"
        path.write_text(json.dumps(verification), encoding="utf-8")
    before = package.read_bytes()
    with pytest.raises(ValueError, match="Independent verification"):
        job.apply_review()
    assert package.read_bytes() == cache.read_bytes() == before

"""Apply a complete, validated review to packaged titles; preserve an audit trail."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.modules.library.icd_terminology import medical_title
from app.modules.library.icd_translation import PACKAGED_TRANSLATIONS, TRANSLATION_FILE

spec = importlib.util.spec_from_file_location(
    "medical_review_job", ROOT / "scripts/translation/review_icd_titles.py"
)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
FOLDER = ROOT / "storage/imports/icd-import/medical-review"


def atomic_json(path, data):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def apply_review():
    input_path = FOLDER / "input.json"
    state = json.loads((FOLDER / "progress.json").read_text(encoding="utf-8"))
    rows = json.loads(input_path.read_text(encoding="utf-8"))
    if state["status"] != "complete" or set(state["reviewed_ids"]) != {r["id"] for r in rows}:
        raise ValueError("Review is not complete; dictionary was not modified")
    if hashlib.sha256(input_path.read_bytes()).hexdigest() != state["input_sha256"]:
        raise ValueError("Review snapshot has changed")
    package = json.loads(PACKAGED_TRANSLATIONS.read_text(encoding="utf-8"))
    for row in rows:
        if package["translations"].get(row["source"]) != row["vi"]:
            raise ValueError("Current dictionary differs from review snapshot")
    decisions_path = FOLDER / "decisions.json"
    decisions = (
        json.loads(decisions_path.read_text(encoding="utf-8")) if decisions_path.exists() else {}
    )
    verification_path = FOLDER / "verification.json"
    if not verification_path.exists():
        raise ValueError("Independent verification is missing")
    verification = (
        json.loads(verification_path.read_text(encoding="utf-8"))
        if verification_path.exists()
        else None
    )
    if verification:
        if verification["status"] != "complete":
            raise ValueError("Independent verification is not complete")
        for source, proposal in state["changes"].items():
            expected = hashlib.sha256(proposal["after"].encode("utf-8")).hexdigest()
            if verification["verified"].get(source) != expected:
                raise ValueError("Independent verification does not match proposals")
    accepted, unresolved = {}, dict(state["rejected_changes"])
    if verification:
        unresolved.update(verification["flagged"])
    for row in rows:
        source = row["source"]
        if verification and source in verification["flagged"] and source not in decisions:
            continue
        proposal = (
            decisions.get(source)
            or (verification["corrections"].get(source) if verification else None)
            or state["changes"].get(source)
        )
        if not proposal:
            continue
        title = medical_title(source, proposal["after"].strip())
        issue = review.validate_change(row, title)
        source_checked_exception = (
            source in decisions
            and issue in proposal.get("allow_validation", [])
            and bool(proposal.get("sources"))
        )
        if issue and not source_checked_exception:
            unresolved[source] = {**proposal, "before": row["vi"], "validation": issue}
            continue
        if title != row["vi"]:
            accepted[source] = {**proposal, "before": row["vi"], "after": title}
            package["translations"][source] = title
        if source in decisions:
            unresolved.pop(source, None)
    for source, title in package["translations"].items():
        if not isinstance(title, str) or not title.strip() or len(title) > 1000:
            raise ValueError("Invalid final title")
        if medical_title(source, title) != title:
            raise ValueError("Final title conflicts with terminology glossary")
    summary = {
        "reviewed_titles": len(rows),
        "changed_titles": len(accepted),
        "unresolved_proposals": len(unresolved),
        "method": "AI-assisted full-catalog review, automated qualifier checks and source-based terminology decisions",
        "clinician_validated": False,
        "independently_verified_edits": len(verification["verified"]) if verification else 0,
    }
    backup = FOLDER / "before-apply.json"
    if not backup.exists():
        backup.write_bytes(PACKAGED_TRANSLATIONS.read_bytes())
    package["medical_review"] = summary
    atomic_json(FOLDER / "accepted-changes.json", accepted)
    atomic_json(FOLDER / "unresolved-proposals.json", unresolved)
    atomic_json(PACKAGED_TRANSLATIONS, package)
    atomic_json(TRANSLATION_FILE, package)
    atomic_json(FOLDER / "result.json", summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(apply_review()))

"""Independently verify proposed edits while the full-catalog review runs."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("review_job", ROOT / "scripts/translation/review_icd_titles.py")
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)
FOLDER = job.FOLDER
PATH = FOLDER / "verification.json"


def digest(title):
    return hashlib.sha256(title.encode("utf-8")).hexdigest()


def save(state):
    temp = PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(PATH)


def main():
    os.environ["GEMINI_CHAT_MODEL"] = os.getenv("DERMA_VERIFICATION_MODEL", "gemini-3.5-flash")
    job.PROMPT += """ This is an independent verification of proposed edits.
    Focus on fidelity to English and correct established Vietnamese medical terminology.
    Do not blindly accept the candidate or make unnecessary synonym/style changes.
    The previous_translation field is provided for comparison, not as an authoritative glossary."""
    rows = json.loads((FOLDER / "input.json").read_text(encoding="utf-8"))
    by_source = {r["source"]: r for r in rows}
    state = (
        json.loads(PATH.read_text(encoding="utf-8"))
        if PATH.exists()
        else {
            "verified": {},
            "corrections": {},
            "flagged": {},
            "model": "gemini-3.5-flash",
        }
    )
    state.update(status="running", error=None)
    state["model"] = os.environ["GEMINI_CHAT_MODEL"]
    state.setdefault("models_used", ["gemini-3.5-flash"])
    if state["model"] not in state["models_used"]:
        state["models_used"].append(state["model"])
    save(state)
    failure = None
    with ThreadPoolExecutor(max_workers=2) as pool:
        active = {}
        while True:
            review_state = json.loads((FOLDER / "progress.json").read_text(encoding="utf-8"))
            busy = {source for selection in active.values() for source, _ in selection}
            pending = [
                (source, proposal)
                for source, proposal in review_state["changes"].items()
                if source not in busy and state["verified"].get(source) != digest(proposal["after"])
            ]
            while not failure and pending and len(active) < 2:
                selected, pending = pending[:120], pending[120:]
                batch = [
                    {
                        **by_source[source],
                        "vi": proposal["after"],
                        "previous_translation": proposal["before"],
                    }
                    for source, proposal in selected
                ]
                active[pool.submit(job.review_batch, batch)] = selected
            if not active:
                if failure or review_state["status"] != "running":
                    state["status"] = (
                        "paused_error"
                        if failure
                        else (
                            "complete"
                            if review_state["status"] == "complete"
                            else "waiting_for_review"
                        )
                    )
                    state["error"] = failure
                    save(state)
                    print(
                        json.dumps(
                            {
                                "status": state["status"],
                                "verified": len(state["verified"]),
                                "corrections": len(state["corrections"]),
                                "error": failure,
                            }
                        ),
                        flush=True,
                    )
                    return
                time.sleep(10)
                continue
            future = next(as_completed(active))
            selected = active.pop(future)
            try:
                result = future.result()
                corrections = {r["id"]: r for r in result["changes"]}
                for source, proposal in selected:
                    row = by_source[source]
                    change = corrections.get(row["id"])
                    state["corrections"].pop(source, None)
                    state["flagged"].pop(source, None)
                    if change:
                        title = job.medical_title(source, change["vi"].strip())
                        issue = job.validate_change(row, title)
                        entry = {
                            "before": proposal["after"],
                            "after": title,
                            "reason": change["reason"],
                        }
                        if issue:
                            state["flagged"][source] = {**entry, "validation": issue}
                        elif title != proposal["after"]:
                            state["corrections"][source] = entry
                    state["verified"][source] = digest(proposal["after"])
                save(state)
                print(
                    json.dumps(
                        {
                            "verified": len(state["verified"]),
                            "corrections": len(state["corrections"]),
                            "flagged": len(state["flagged"]),
                        }
                    ),
                    flush=True,
                )
            except Exception as exc:
                failure = getattr(exc, "detail", None) or type(exc).__name__


if __name__ == "__main__":
    main()

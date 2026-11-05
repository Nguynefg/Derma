"""Build display groups from existing source ancestry; never infer groups from names."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[2]


def build():
    snapshot = ROOT / "storage/imports/icd-import/validation-only.sqlite"
    with sqlite3.connect(snapshot.resolve().as_uri() + "?mode=ro", uri=True) as db:
        rows = {
            data["linearization_uri"]: data
            for (raw,) in db.execute(
                "select details from tbldiseases where review_status='icd_classification'"
            )
            for data in [json.loads(raw)]
        }
    translations = json.loads(
        (ROOT / "backend/app/data/icd_titles_vi.json").read_text(encoding="utf-8")
    )["translations"]
    members, labels = {}, {}
    for uri, data in rows.items():
        if data["chapter_no"] != "X":
            continue
        parent = rows.get(data.get("parent_uri"))
        visited = {uri}
        while parent and parent["linearization_uri"] not in visited:
            visited.add(parent["linearization_uri"])
            if parent["class_kind"] == "block":
                label = translations.get(parent["title"])
                if label:
                    group = parent["linearization_uri"].rsplit("/", 1)[-1]
                    members[uri.rsplit("/", 1)[-1]] = group
                    labels[group] = label
                break
            parent = rows.get(parent.get("parent_uri"))
    result = {"method": "nearest source ancestor block", "members": members, "labels": labels}
    target = ROOT / "backend/app/data/library_groups.json"
    target.write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(json.dumps({"grouped_entries": len(members), "groups": len(labels)}))


if __name__ == "__main__":
    build()

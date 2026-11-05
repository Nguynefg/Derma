"""Validate actual weights, evidence and database label mapping before activating a model."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def install(card_path):
    from app.modules.library.identifiers import find_record
    from app.modules.images.image_model import read_configuration, load_runtime
    from app.database.connection import SessionLocal, engine
    from app.database.models import Disease

    if os.getenv("DERMA_IMAGE_MODEL_CARD"):
        raise ValueError(
            "DERMA_IMAGE_MODEL_CARD overrides the default package; review that setting first"
        )
    active = ROOT / "backend/models/active"
    if active.exists():
        raise ValueError(
            "Active model already exists. Preserve it before installing another version"
        )
    card_path = Path(card_path).resolve()
    card, checkpoint = read_configuration(card_path)
    # Loading is CPU-only, strict and weights_only; this verifies tensor shapes and runtime.
    load_runtime(
        str(checkpoint),
        card.checkpoint_sha256,
        tuple(label.label for label in card.labels),
        card.dataset_manifest_sha256,
    )
    if card.classification_unit == "disease":
        try:
            with SessionLocal() as db:
                for label in card.labels:
                    topic = find_record(db, Disease, label.disease_id)
                    if topic is None or not topic.published:
                        raise ValueError(
                            "A disease label is not published in the configured database"
                        )
        finally:
            engine.dispose()
    else:
        # Broad group labels are NOT mapped to a diagnosis. Optional reading links
        # are filtered against live published records on each inference request.
        print("Group classifier: related reading links are checked at request time.")
        engine.dispose()
    active.parent.mkdir(parents=True, exist_ok=True)
    staging = active.parent / ("staging-" + uuid4().hex)
    staging.mkdir()
    shutil.copyfile(checkpoint, staging / "best.pt")
    shutil.copyfile(
        (card_path.parent / card.evaluation_report).resolve(), staging / "evaluation.json"
    )
    prepared = card.model_dump()
    prepared.update(checkpoint="best.pt", evaluation_report="evaluation.json")
    (staging / "model-card.json").write_text(json.dumps(prepared, indent=2), encoding="utf-8")
    read_configuration(staging / "model-card.json")
    staging.rename(active)
    print("Installed verified package under backend/models/active. Restart the web server.")
    print("This is a research model, not a clinically validated diagnosis service.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--card", required=True)
    args = parser.parse_args()
    try:
        install(args.card)
    except Exception as error:
        # Do not print DB connection details, private rows or arbitrary checkpoint content.
        if isinstance(error, ValueError):
            print(
                "Model not activated: validation failed; check review, hashes, mapping and existing configuration.",
                file=sys.stderr,
            )
        elif isinstance(error, ModuleNotFoundError):
            print(
                "Model not activated: install backend/requirements/image.txt first.",
                file=sys.stderr,
            )
        else:
            print(
                "Model not activated: runtime/database/file check failed ("
                + type(error).__name__
                + ").",
                file=sys.stderr,
            )
        raise SystemExit(1)

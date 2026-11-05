"""Resolve numeric IDs and retained legacy slugs without unsafe SQL coercions."""

from sqlalchemy import select, cast
from app.database.models import Disease, Text


def find_record(db, model, value):
    if value is None:
        return None
    text = str(value)
    if text.isascii() and text.isdecimal():
        record = db.get(model, int(text))
        if record is not None or model is not Disease:
            return record
        return db.scalar(select(Disease).where(cast(Disease.aliases,Text).contains('"merged-id:'+text+'"',autoescape=True)))
    field = getattr(model, "slug", None)
    if field is None:
        field = getattr(model, "legacy_id", None)
    if field is None:
        field = getattr(model, "file_uuid", None)
    record = db.scalar(select(model).where(field == text)) if field is not None else None
    if record is None and model is Disease:
        return db.scalar(select(Disease).where(cast(Disease.aliases,Text).contains('"merged-slug:'+text+'"',autoescape=True)))
    return record


def display_code(prefix, value):
    return f"{prefix}{value:06d}"

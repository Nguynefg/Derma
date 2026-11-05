"""Transactional v2 upgrade: tbl names, identity keys, preserved legacy identifiers."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from sqlalchemy import inspect, select, func, text
from app.database.models import Base
from app.database.migrations.legacy_schema import Base as LegacyBase
from app.database.transfer import fingerprint


ENTITIES = {
    "users": ("user_id", "legacy_id"),
    "diseases": ("disease_id", "slug"),
    "symptoms": ("symptom_id", "slug"),
    "medical_references": ("reference_id", "slug"),
    "search_history": ("history_id", "legacy_id"),
    "admin_audit_logs": ("audit_id", "legacy_id"),
    "medical_documents": ("document_id", "slug"),
    "document_versions": ("document_version_id", "legacy_id"),
    "image_records": ("image_id", "file_uuid"),
}
FK_TARGETS = {
    "user_id": "users",
    "actor_id": "users",
    "editor_id": "users",
    "disease_id": "diseases",
    "symptom_id": "symptoms",
    "document_id": "medical_documents",
}


def convert_rows(original):
    mappings = {
        table: {
            row["id"]: i + 1
            for i, row in enumerate(sorted(original.get(table, []), key=lambda r: r["id"]))
        }
        for table in ENTITIES
    }
    converted = {}
    for old_name, records in original.items():
        prepared = []
        for source in records:
            row = source.copy()
            if old_name in ENTITIES:
                pk, legacy = ENTITIES[old_name]
                old_id = row.pop("id")
                row[pk] = mappings[old_name][old_id]
                row[legacy] = old_id
            elif old_name == "library_updates":
                row["update_id"] = row.pop("id")
            for column, target in FK_TARGETS.items():
                if column not in row or row[column] is None:
                    continue
                # The renamed primary key is not a foreign key to itself.
                if old_name in ENTITIES and column == ENTITIES[old_name][0]:
                    continue
                value = row[column]
                if value not in mappings[target]:
                    raise ValueError(
                        f"Orphan foreign key in {old_name}.{column}; migration stopped"
                    )
                row[column] = mappings[target][value]
            if old_name == "search_history":
                row["results"] = [
                    (
                        {**item, "id": str(mappings["diseases"][item["id"]])}
                        if isinstance(item, dict) and item.get("id") in mappings["diseases"]
                        else item
                    )
                    for item in row["results"]
                ]
            if old_name == "admin_audit_logs":
                target = (
                    "medical_documents" if row["action"].startswith("document_") else "diseases"
                )
                row["entity_id"] = str(mappings[target].get(row["entity_id"], row["entity_id"]))
                # Historical snapshots deliberately retain their original IDs and content.
            prepared.append(row)
        converted["tbl" + old_name] = prepared
    return converted, mappings


def _backup(folder, original, mappings):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (
        "schema-v1-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        + "-"
        + uuid4().hex[:8]
        + ".json"
    )
    payload = json.dumps(
        {"schema_version": 1, "tables": original, "id_mapping": mappings},
        ensure_ascii=False,
        default=lambda v: v.isoformat() if isinstance(v, datetime) else str(v),
    ).encode("utf-8")
    with path.open("xb") as output:
        output.write(payload)
        output.flush()
        os.fsync(output.fileno())
    path.with_suffix(".sha256").write_text(hashlib.sha256(payload).hexdigest(), encoding="ascii")
    return path


def verify_schema(connection, allow_pending_bookmarks=False):
    inspector = inspect(connection)
    expected = set(Base.metadata.tables)
    present = set(inspector.get_table_names())
    missing = expected - present
    if allow_pending_bookmarks:
        missing.discard("tblbookmarks")
    if missing:
        raise ValueError("Missing application tables: " + ", ".join(sorted(missing)))
    counts = {}
    for table in Base.metadata.sorted_tables:
        if allow_pending_bookmarks and table.name == "tblbookmarks" and table.name not in present:
            continue
        columns = {c["name"]: c for c in inspector.get_columns(table.name)}
        if set(table.columns.keys()) - set(columns):
            raise ValueError("Missing columns in " + table.name)
        expected_pk = [c.name for c in table.primary_key]
        if inspector.get_pk_constraint(table.name)["constrained_columns"] != expected_pk:
            raise ValueError("Incorrect primary key in " + table.name)
        if table.name[3:] in ENTITIES:
            pk = ENTITIES[table.name[3:]][0]
            if "INT" not in str(columns[pk]["type"]).upper():
                raise ValueError("Primary key is not integer: " + table.name)
            if connection.dialect.name == "mssql" and not columns[pk].get("identity"):
                raise ValueError("Missing IDENTITY in " + table.name)
        actual_fks = {
            (tuple(f["constrained_columns"]), f["referred_table"], tuple(f["referred_columns"]))
            for f in inspector.get_foreign_keys(table.name)
        }
        for column in table.columns:
            for fk in column.foreign_keys:
                if ((column.name,), fk.column.table.name, (fk.column.name,)) not in actual_fks:
                    raise ValueError("Missing foreign key in " + table.name)
                parent = fk.column.table
                orphan = connection.scalar(
                    select(func.count())
                    .select_from(table.outerjoin(parent, column == fk.column))
                    .where(column.is_not(None), fk.column.is_(None))
                )
                if orphan:
                    raise ValueError("Orphan foreign keys in " + table.name)
        counts[table.name] = connection.scalar(select(func.count()).select_from(table))
    return counts


def upgrade(engine, backup_dir, apply=False):
    with engine.connect() as connection:
        names = set(inspect(connection).get_table_names())
        legacy_names = names & set(LegacyBase.metadata.tables)
        current_names = names & set(Base.metadata.tables)
        if not legacy_names:
            if not current_names:
                if apply:
                    Base.metadata.create_all(engine)
                return {"status": "new_database"}
            counts = verify_schema(connection, allow_pending_bookmarks=True)
            if "tblbookmarks" not in names:
                if not apply:
                    return {
                        "status": "upgrade_required",
                        "tables": counts,
                        "target_tables": ["tblbookmarks"],
                    }
                # Additive change only; existing account and library rows are untouched.
                connection.rollback()
                with connection.begin():
                    Base.metadata.tables["tblbookmarks"].create(connection, checkfirst=True)
                counts = verify_schema(connection)
            return {"status": "current", "tables": counts}
        if current_names:
            raise ValueError("Both old and tbl tables exist; refusing to merge or overwrite data")
        missing = set(LegacyBase.metadata.tables) - legacy_names - {"image_records"}
        if missing:
            raise ValueError("Legacy schema incomplete: " + ", ".join(sorted(missing)))
        inspector = inspect(connection)
        for name in legacy_names:
            actual = {c["name"] for c in inspector.get_columns(name)}
            expected = set(LegacyBase.metadata.tables[name].columns.keys())
            if actual != expected:
                raise ValueError(
                    "Legacy table has unexpected columns; preserve/review before upgrading: " + name
                )
        if not apply:
            return {
                "status": "upgrade_required",
                "tables": sorted(legacy_names),
                "target_tables": sorted(Base.metadata.tables),
            }
    with engine.begin() as connection:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        if engine.dialect.name == "mssql":
            connection.execute(
                text(
                    "DECLARE @r int; EXEC @r = sp_getapplock @Resource='derma-schema-v2', @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=5000; IF @r < 0 THROW 50001, 'Schema upgrade is busy', 1;"
                )
            )
        original = {}
        for table in LegacyBase.metadata.sorted_tables:
            query = select(table)
            if engine.dialect.name == "mssql":
                query = query.with_hint(table, "WITH (TABLOCKX, HOLDLOCK)", dialect_name="mssql")
            original[table.name] = (
                [dict(r) for r in connection.execute(query).mappings()]
                if table.name in legacy_names
                else []
            )
        prepared, mappings = convert_rows(original)
        backup = _backup(backup_dir, original, mappings)
        Base.metadata.create_all(connection)
        for table in Base.metadata.sorted_tables:
            records = prepared.get(table.name, [])
            for offset in range(0, len(records), 100):
                connection.execute(table.insert(), records[offset : offset + 100])
            if engine.dialect.name == "postgresql" and table.name[3:] in ENTITIES and records:
                pk = ENTITIES[table.name[3:]][0]
                connection.execute(
                    text("SELECT setval(pg_get_serial_sequence(:t, :c), :n, true)"),
                    {"t": table.name, "c": pk, "n": max(row[pk] for row in records)},
                )
            copied = [dict(r) for r in connection.execute(select(table)).mappings()]
            if len(copied) != len(records) or fingerprint(copied, table) != fingerprint(
                records, table
            ):
                raise ValueError("Content verification failed in " + table.name)
        counts = verify_schema(connection)
        for table in reversed(LegacyBase.metadata.sorted_tables):
            if table.name in legacy_names:
                table.drop(connection)
    return {"status": "upgraded", "backup": str(backup), "tables": counts}

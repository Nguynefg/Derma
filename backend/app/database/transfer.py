"""Offline transfer helpers. No deletes, no logging of row values or credentials."""

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select, func, DateTime, inspect
from app.database.models import Base


def sqlite_backup(source, destination):
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if not source.is_file():
        raise ValueError("Source SQLite file does not exist")
    if source == destination:
        raise ValueError("Backup must be a separate file")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive reservation: do not overwrite a previous backup.
    with destination.open("xb"):
        pass
    try:
        with (
            sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as src,
            sqlite3.connect(str(destination)) as dst,
        ):
            src.backup(dst)
            if dst.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Backup integrity check failed")
    except Exception:
        # Keep failed backup for inspection. Never alter the source.
        raise
    return destination


def rows(connection, table):
    return [dict(row) for row in connection.execute(select(table)).mappings()]


def canonical_value(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds")
    return value


def fingerprint(data, table):
    keys = [col.name for col in table.primary_key]
    normalized = [{key: canonical_value(value) for key, value in row.items()} for row in data]
    normalized.sort(key=lambda row: tuple(str(row[key]) for key in keys))
    return hashlib.sha256(
        json.dumps(
            normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def source_counts(connection):
    present = set(inspect(connection).get_table_names())
    missing = {table.name for table in Base.metadata.sorted_tables} - present
    if missing:
        raise ValueError("Source schema is incomplete; run the current SQLite app before migration")
    return {
        table.name: connection.scalar(select(func.count()).select_from(table))
        for table in Base.metadata.sorted_tables
    }


def assert_empty_target(connection):
    present = set(inspect(connection).get_table_names())
    expected = set(Base.metadata.tables)
    if present - expected:
        raise ValueError("Target contains unrelated tables; use a dedicated empty database")
    for table in Base.metadata.sorted_tables:
        if table.name in present and connection.scalar(select(func.count()).select_from(table)):
            raise ValueError("Target already contains application data; nothing was overwritten")


def transfer(source_engine, target_engine):
    if source_engine.url == target_engine.url:
        raise ValueError("Source and target must differ")
    with source_engine.connect() as source:
        source_counts(source)
        with target_engine.connect() as target:
            assert_empty_target(target)
        Base.metadata.create_all(target_engine)
        report = {}
        # Includes verification: an insert/hash/FK error rolls back all transferred rows.
        with target_engine.begin() as target:
            assert_empty_target(target)
            for table in Base.metadata.sorted_tables:
                original = rows(source, table)
                prepared = []
                for record in original:
                    record = record.copy()
                    for column in table.columns:
                        value = record.get(column.name)
                        if (
                            isinstance(column.type, DateTime)
                            and value is not None
                            and value.tzinfo is None
                        ):
                            record[column.name] = value.replace(tzinfo=timezone.utc)
                    prepared.append(record)
                for offset in range(0, len(prepared), 100):
                    target.execute(table.insert(), prepared[offset : offset + 100])
                copied = rows(target, table)
                if len(original) != len(copied) or fingerprint(original, table) != fingerprint(
                    copied, table
                ):
                    raise ValueError(
                        "Destination verification failed; transferred rows rolled back"
                    )
                report[table.name] = len(copied)
        return report

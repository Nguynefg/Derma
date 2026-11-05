"""Run from project root. Defaults to a read-only plan; --apply explicitly copies data."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from sqlalchemy import create_engine, text, URL
from app.database.config import SQLServerSettings, CONFIG_PATH
from app.database.transfer import sqlite_backup, source_counts, assert_empty_target, transfer


def parse_args():
    parser = argparse.ArgumentParser(
        description="Copy SQLite into a dedicated SQL Server database; keep SQLite intact."
    )
    parser.add_argument(
        "--server", required=True, help=r"SSMS Server name, e.g. localhost or localhost\SQLEXPRESS"
    )
    parser.add_argument("--database", default="BenhLy")
    parser.add_argument("--authentication", choices=["windows", "sql"], default="windows")
    parser.add_argument(
        "--username", help="SQL authentication only; password comes from DERMA_SQL_PASSWORD"
    )
    parser.add_argument(
        "--driver", choices=["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"]
    )
    parser.add_argument("--source", type=Path, default=ROOT / "backend/data/derma.db")
    parser.add_argument(
        "--apply", action="store_true", help="Copy rows and verify in a transaction"
    )
    parser.add_argument(
        "--create-database",
        action="store_true",
        help="Create destination if missing; requires --apply",
    )
    parser.add_argument(
        "--activate",
        action="store_true",
        help="After verification, write backend/database.local.json; requires --apply",
    )
    parser.add_argument(
        "--trust-server-certificate",
        action="store_true",
        help="Explicit local development certificate opt-in; encryption remains enabled",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if (args.activate or args.create_database) and not args.apply:
        raise ValueError("--activate/--create-database require --apply")
    if args.activate and (CONFIG_PATH.exists() or os.getenv("DATABASE_URL")):
        raise ValueError(
            "Existing connection configuration found; preserve/review it before activating"
        )
    import pyodbc

    drivers = pyodbc.drivers()
    driver = args.driver or next(
        (
            name
            for name in ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"]
            if name in drivers
        ),
        None,
    )
    if not driver or driver not in drivers:
        raise ValueError("Microsoft ODBC Driver 17/18 is not installed")
    settings = SQLServerSettings(
        server=args.server,
        database=args.database,
        driver=driver,
        authentication=args.authentication,
        username=args.username,
        trust_server_certificate=args.trust_server_certificate,
    )
    source_path = args.source.resolve()
    if not source_path.is_file():
        raise ValueError("Source SQLite file does not exist")
    if args.apply:
        backup = (
            ROOT
            / "storage/backups"
            / (
                "before-sqlserver-"
                + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                + "-"
                + uuid4().hex[:6]
                + ".db"
            )
        )
        source_path = sqlite_backup(source_path, backup)
        print("Created a consistent SQLite backup under storage/backups.")
    source_engine = create_engine(
        URL.create("sqlite", database=str(source_path)), hide_parameters=True
    )
    master = None
    target = None
    try:
        with source_engine.connect() as source:
            counts = source_counts(source)
        print("Source plan (counts only):")
        for name, count in counts.items():
            print(f"  {name}: {count}")
        master = create_engine(settings.url("master"), hide_parameters=True, pool_pre_ping=True)
        with master.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            exists = (
                connection.scalar(text("SELECT DB_ID(:name)"), {"name": settings.database})
                is not None
            )
            if not exists:
                if not (args.apply and args.create_database):
                    raise ValueError(
                        "Destination database does not exist; create it or explicitly use --apply --create-database"
                    )
                # Database name was restricted to a safe identifier in SQLServerSettings.
                connection.exec_driver_sql("CREATE DATABASE [" + settings.database + "]")
                print("Created destination database: " + settings.database)
        target = create_engine(
            settings.url(), hide_parameters=True, pool_pre_ping=True, isolation_level="SERIALIZABLE"
        )
        with target.connect() as connection:
            assert_empty_target(connection)
        if not args.apply:
            print(
                "Read-only checks passed. No data or connection settings changed. Use --apply to migrate."
            )
            return
        report = transfer(source_engine, target)
        print(
            "Migration committed. Row counts and normalized content hashes match for every table."
        )
        for name, count in report.items():
            print(f"  {name}: {count}")
        if args.activate:
            settings.save()
            print(
                "Saved backend/database.local.json without a password. Restart the app to use SQL Server."
            )
        else:
            print(
                "App connection is unchanged; --activate is required to switch it after a successful migration."
            )
    finally:
        source_engine.dispose()
        if master:
            master.dispose()
        if target:
            target.dispose()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, ModuleNotFoundError) as error:
        print("Migration not completed: " + str(error), file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        # DBAPI exceptions can include credentials or private row values: never print them.
        original = getattr(error, "orig", None)
        code = original.args[0] if original and original.args else ""
        state = (
            code if isinstance(code, str) and re.fullmatch(r"[A-Z0-9]{5}", code) else "unavailable"
        )
        print(
            "Migration not completed: database/file operation failed ("
            + type(error).__name__
            + ", SQLSTATE "
            + state
            + "). Check server, authentication, permissions and certificate. App connection has not been switched unless success was printed.",
            file=sys.stderr,
        )
        sys.exit(1)

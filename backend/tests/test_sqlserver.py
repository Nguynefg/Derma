"""Portable migration checks; live SQL Server is verified separately."""

import json
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, select, text, event
from sqlalchemy.dialects import mssql
from sqlalchemy.schema import CreateTable
from app.database.models import Base, User, History
from app.database.config import SQLServerSettings, configured_url, read_settings
from app.database.transfer import transfer, sqlite_backup, fingerprint


def database(path):
    engine = create_engine("sqlite:///" + str(path))

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return engine


def sample(engine):
    with engine.begin() as connection:
        connection.execute(
            User.__table__.insert(),
            dict(
                user_id=1,
                legacy_id="u1",
                email="test@example.test",
                name="Nguyễn Ánh",
                password_hash="test-only",
                role="user",
                created_at=datetime(2026, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc),
            ),
        )
        connection.execute(
            History.__table__.insert(),
            dict(
                history_id=1,
                legacy_id="h1",
                user_id=1,
                mode="question",
                query="Ngứa, nổi mẩn đỏ?",
                results=[{"tên": "Viêm da", "nested": [True, None, 2]}],
                consent_version="history-v1",
            ),
        )


def test_mssql_unicode_json_dates_and_all_ddl():
    ddl = "\n".join(
        str(CreateTable(table).compile(dialect=mssql.dialect()))
        for table in Base.metadata.sorted_tables
    )
    assert "name NVARCHAR(80)" in ddl
    assert "summary NVARCHAR(max)" in ddl
    assert "DATETIMEOFFSET" in ddl
    assert "results NVARCHAR(max)" in ddl
    assert "NTEXT" not in ddl
    assert "VARCHAR(" not in ddl.replace("NVARCHAR(", "")


def test_settings_password_never_saved(tmp_path, monkeypatch):
    monkeypatch.setenv("DERMA_SQL_PASSWORD", "example-only-secret")
    settings = SQLServerSettings(
        server=r"localhost\SQLEXPRESS", authentication="sql", username="derma"
    )
    path = tmp_path / "database.json"
    settings.save(path)
    assert "secret" not in path.read_text()
    assert read_settings(path) == settings
    assert settings.url().password == "example-only-secret"
    assert "example-only-secret" not in str(settings.url())
    with pytest.raises(ValueError):
        settings.save(path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///explicit.db")
    monkeypatch.setenv("DERMA_DATABASE_CONFIG", str(path))
    assert configured_url(tmp_path) == "sqlite:///explicit.db"


def test_windows_auth_encryption_and_identifier_validation():
    settings = SQLServerSettings(server="localhost")
    args = mssql.pyodbc.dialect().create_connect_args(settings.url())[0][0]
    assert "Trusted_Connection=Yes" in args
    assert "Encrypt=yes" in args and "TrustServerCertificate=no" in args
    with pytest.raises(ValueError):
        SQLServerSettings(server="localhost", database="x]; DROP DATABASE x")
    with pytest.raises(ValueError):
        SQLServerSettings(server="localhost;UID=other")
    with pytest.raises(ValueError):
        SQLServerSettings(server="localhost", encrypt=False)


def test_transfer_preserves_unicode_json_dates_and_rejects_overwrite(tmp_path):
    source = database(tmp_path / "source.db")
    target = database(tmp_path / "target.db")
    try:
        sample(source)
        report = transfer(source, target)
        assert report["tblusers"] == 1 and report["tblsearch_history"] == 1
        for table in Base.metadata.sorted_tables:
            with source.connect() as src, target.connect() as dst:
                assert fingerprint(
                    [dict(r) for r in src.execute(select(table)).mappings()], table
                ) == fingerprint([dict(r) for r in dst.execute(select(table)).mappings()], table)
        with pytest.raises(ValueError, match="already contains"):
            transfer(source, target)
        with target.connect() as connection:
            assert connection.scalar(select(User.name)) == "Nguyễn Ánh"
    finally:
        source.dispose()
        target.dispose()


def test_failure_rolls_back_all_copied_rows(tmp_path, monkeypatch):
    import app.database.transfer as database_transfer

    source = database(tmp_path / "source.db")
    target = database(tmp_path / "target.db")
    try:
        sample(source)
        original = database_transfer.rows

        def corrupted(connection, table):
            data = original(connection, table)
            if connection.engine is target and table.name == "tblsearch_history":
                data[0]["query"] = "changed"
            return data

        monkeypatch.setattr(database_transfer, "rows", corrupted)
        with pytest.raises(ValueError, match="verification failed"):
            transfer(source, target)
        with target.connect() as connection:
            assert connection.execute(select(User.id)).first() is None
            assert connection.execute(select(History.id)).first() is None
    finally:
        source.dispose()
        target.dispose()


def test_backup_and_unrelated_target_are_preserved(tmp_path):
    source = database(tmp_path / "source.db")
    target = database(tmp_path / "target.db")
    try:
        sample(source)
        backup = sqlite_backup(tmp_path / "source.db", tmp_path / "backup.db")
        with pytest.raises(FileExistsError):
            sqlite_backup(tmp_path / "source.db", backup)
        with target.begin() as connection:
            connection.execute(text("CREATE TABLE unrelated (id INTEGER)"))
        with pytest.raises(ValueError, match="unrelated"):
            transfer(source, target)
        saved = create_engine("sqlite:///" + str(backup))
        try:
            with saved.connect() as connection:
                assert connection.scalar(select(User.name)) == "Nguyễn Ánh"
        finally:
            saved.dispose()
    finally:
        source.dispose()
        target.dispose()

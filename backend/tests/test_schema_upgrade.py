"""Upgrade actual legacy rows, preserve references/files, and verify atomic failure."""

from uuid import uuid4
from sqlalchemy import create_engine, event, select, inspect
from sqlalchemy.orm import Session
import pytest
from app.database.migrations import legacy_schema as old
from app.database.migrations import numeric_ids as migration
from app.database.models import Base, User, Disease, ImageRecord, History, DocumentVersion


def legacy_database(tmp_path):
    engine = create_engine("sqlite:///" + (tmp_path / "legacy.db").as_posix())

    @event.listens_for(engine, "connect")
    def foreign_keys(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    old.Base.metadata.create_all(engine)
    file_uuid = str(uuid4())
    with Session(engine) as db:
        db.add(
            old.User(
                id="user-old",
                name="Người dùng",
                email="test@example.test",
                password_hash="hash-preserved",
                role="admin",
            )
        )
        db.add(
            old.Disease(
                id="eczema",
                name="Chàm",
                english_name="Eczema",
                category="Da",
                summary="Nội dung giữ nguyên",
                details="Chi tiết",
                risk_factors="Yếu tố",
                prevention="Chăm sóc",
                published=True,
            )
        )
        db.add(old.Symptom(id="itch", name="Ngứa"))
        db.flush()
        db.add(old.DiseaseSymptom(disease_id="eczema", symptom_id="itch"))
        db.add(
            old.Reference(
                id="ref-old",
                disease_id="eczema",
                title="Nguồn",
                publisher="Test",
                url="https://example.test",
                accessed_at="2026-10-16",
                usage_note="Tham khảo",
            )
        )
        db.add(
            old.MedicalDocument(
                id="doc-old",
                disease_id="eczema",
                title="Tài liệu",
                publisher="Test",
                source_url="https://example.test",
                usage_note="Tham khảo",
                published=True,
            )
        )
        db.add(
            old.ImageRecord(
                id=file_uuid,
                user_id="user-old",
                disease_id="eczema",
                pixel_sha256="a" * 64,
                image_type="clinical",
                width=512,
                height=512,
                is_reference=True,
            )
        )
        db.add(
            old.History(
                id="history-old",
                user_id="user-old",
                mode="keyword",
                query="Chàm",
                results=[{"id": "eczema", "name": "Chàm", "version": 1}],
            )
        )
        db.add(
            old.LoginSession(
                token_hash="b" * 64, user_id="user-old", csrf="c" * 64, expires_at=old.now()
            )
        )
        db.add(
            old.AuditLog(
                id="audit-old",
                actor_id="user-old",
                action="update",
                entity_id="eczema",
                snapshot={"before": {"id": "eczema", "name": "Chàm"}},
            )
        )
        db.add(old.LibraryUpdate(id="release-old"))
        db.flush()
        db.add(
            old.DocumentVersion(
                id="version-old",
                document_id="doc-old",
                version=1,
                title="Tài liệu",
                publisher="Test",
                source_url="https://example.test",
                usage_note="Tham khảo",
                content="Nội dung cũ tiếng Việt",
                checksum="d" * 64,
                editor_id="user-old",
            )
        )
        db.commit()
    return engine, file_uuid


def test_full_upgrade_and_idempotence(tmp_path):
    engine, file_uuid = legacy_database(tmp_path)
    try:
        assert migration.upgrade(engine, tmp_path / "backup")["status"] == "upgrade_required"
        result = migration.upgrade(engine, tmp_path / "backup", apply=True)
        assert result["status"] == "upgraded"
        assert set(result["tables"]) == set(Base.metadata.tables)
        assert set(inspect(engine).get_table_names()) == set(Base.metadata.tables)
        assert len(list((tmp_path / "backup").glob("*.json"))) == 1
        with Session(engine) as db:
            user = db.scalar(select(User))
            disease = db.scalar(select(Disease))
            image = db.scalar(select(ImageRecord))
            assert user.id == 1 and user.role == "admin" and user.password_hash == "hash-preserved"
            assert disease.id == 1 and disease.slug == "eczema"
            assert image.id == 1 and image.file_uuid == file_uuid and image.disease_id == disease.id
            assert db.scalar(select(History)).results[0]["id"] == str(disease.id)
            assert db.scalar(select(DocumentVersion)).content == "Nội dung cũ tiếng Việt"
            another = User(email="second@example.test", name="Second", password_hash="hash")
            db.add(another)
            db.commit()
            assert another.id > user.id
        assert migration.upgrade(engine, tmp_path / "backup", apply=True)["status"] == "current"
    finally:
        engine.dispose()


def test_verification_failure_preserves_old_tables(tmp_path, monkeypatch):
    engine, _ = legacy_database(tmp_path)
    try:

        def fail(*args):
            raise ValueError("Verification failed")

        monkeypatch.setattr(migration, "verify_schema", fail)
        with pytest.raises(ValueError, match="Verification"):
            migration.upgrade(engine, tmp_path / "backup", apply=True)
        assert set(inspect(engine).get_table_names()) == set(old.Base.metadata.tables)
        with Session(engine) as db:
            assert db.get(old.User, "user-old").password_hash == "hash-preserved"
    finally:
        engine.dispose()


def test_refuses_mixed_schema(tmp_path):
    engine, _ = legacy_database(tmp_path)
    try:
        User.__table__.create(engine)
        with pytest.raises(ValueError, match="Both old"):
            migration.upgrade(engine, tmp_path / "backup", apply=True)
    finally:
        engine.dispose()


def test_add_bookmarks_to_existing_v2_without_modifying_accounts(tmp_path):
    engine = create_engine("sqlite:///" + (tmp_path / "v2.db").as_posix())
    try:
        Base.metadata.create_all(engine)
        Base.metadata.tables["tblbookmarks"].drop(engine)
        with Session(engine) as db:
            user = User(email="preserve@test.example", name="Existing", password_hash="keep")
            db.add(user)
            db.commit()
            user_id = user.id
        assert migration.upgrade(engine, tmp_path)["status"] == "upgrade_required"
        assert "tblbookmarks" not in inspect(engine).get_table_names()
        result = migration.upgrade(engine, tmp_path, apply=True)
        assert result["tables"]["tblbookmarks"] == 0
        with Session(engine) as db:
            assert db.get(User, user_id).password_hash == "keep"
        assert migration.upgrade(engine, tmp_path, apply=True)["status"] == "current"
    finally:
        engine.dispose()

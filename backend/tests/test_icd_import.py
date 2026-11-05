import copy
import io
from zipfile import ZipFile
from pathlib import Path
import pytest
from sqlalchemy import create_engine, select, func, event
from app.database.legacy_icd_models import ICDBase, ICDRelease, ICDEntity
from app.modules.library.icd_import import (
    parse_sources,
    import_legacy_payload as import_payload,
    sha,
    canonical,
    process_pending_import,
)


@pytest.fixture(autouse=True)
def isolate_archived_sources(tmp_path, monkeypatch):
    import app.modules.library.icd_merge as icd_merge

    monkeypatch.setattr(icd_merge, "SOURCE_ARCHIVE", tmp_path / "originals")


@pytest.fixture
def payload():
    return dict(
        version="test",
        fingerprint="a" * 64,
        sources=[
            dict(filename=n, content=b"original", sha256=sha(b"original"))
            for n in ["test.zip", "test.docx"]
        ],
        entities=[
            dict(
                foundation_uri="http://id.who.int/icd/entity/1",
                linearization_uri="http://id.who.int/icd/release/11/mms/1",
                parent_uri=None,
                code=None,
                raw_code="",
                block_id=None,
                title="Test",
                class_kind="chapter",
                chapter_no="01",
                depth=0,
                source_order=0,
                browser_url="https://icd.who.int/dev11/",
                raw_row=canonical({"Title": "Test"}),
            )
        ],
        documents=[
            dict(
                chapter_no="01",
                embedded_filename="word/afchunk2.docx",
                paragraph_count=1,
                content="Chapter content",
                paragraphs_json='["Chapter content"]',
                sha256=sha(b"Chapter content"),
            )
        ],
    )


def test_import_is_atomic_and_idempotent(tmp_path, payload):
    engine = create_engine("sqlite:///" + (tmp_path / "test.db").as_posix())
    try:
        result = import_payload(engine, payload)
        assert result["status"] == "imported"
        assert result["entities"] == 1 and result["chapters"] == 1 and result["source_files"] == 2
        assert import_payload(engine, payload)["status"] == "already_imported"
        with engine.connect() as c:
            assert c.scalar(select(func.count()).select_from(ICDEntity)) == 1
        corrupted = copy.deepcopy(payload)
        corrupted["entities"][0]["raw_row"] = "changed"
        with pytest.raises(ValueError, match="verification"):
            import_payload(engine, corrupted)
    finally:
        engine.dispose()


def test_failure_rolls_back_release_and_entities(tmp_path, payload):
    engine = create_engine("sqlite:///" + (tmp_path / "rollback.db").as_posix())
    ICDBase.metadata.create_all(engine)
    broken = copy.deepcopy(payload)
    broken["documents"][0]["sha256"] = "bad"
    try:
        with pytest.raises(ValueError, match="verification"):
            import_payload(engine, broken)
        with engine.connect() as c:
            assert c.scalar(select(func.count()).select_from(ICDRelease)) == 0
            assert c.scalar(select(func.count()).select_from(ICDEntity)) == 0
    finally:
        engine.dispose()


def test_source_formula_is_never_executed(tmp_path):
    tab = "Foundation URI\tLinearization URI\tCode\tBlockId\tTitle\tClassKind\tDepthInKind\tIsResidual\tChapterNo\tBrowserLink\tisLeaf\n"
    tab += "http://id.who.int/icd/entity/1\thttp://id.who.int/icd/release/11/mms/1\t\t\tTest\tchapter\t1\tFalse\t01\t=cmd()\tTrue\n"
    path = tmp_path / "test.zip"
    with ZipFile(path, "w") as z:
        z.writestr("SimpleTabulation-test.txt", tab)
    doc = tmp_path / "test.docx"
    doc.write_bytes(b"not-read")
    with pytest.raises(ValueError, match="formula"):
        parse_sources(path, doc)


def test_no_request_does_not_touch_database(tmp_path):
    assert process_pending_import(None, tmp_path) is None


def test_pending_request_completes_once(tmp_path, payload, monkeypatch):
    import json
    import app.modules.library.icd_import as icd_import

    engine = create_engine("sqlite:///" + (tmp_path / "queued.db").as_posix())
    manifest = tmp_path / "request.json"
    manifest.write_text(json.dumps({"status": "pending", "fingerprint": payload["fingerprint"]}))
    monkeypatch.setattr(icd_import, "parse_sources", lambda *args: payload)
    try:
        assert process_pending_import(engine, tmp_path)["entities"] == 1
        assert json.loads(manifest.read_text())["status"] == "complete"
        assert json.loads((tmp_path / "import-result.json").read_text())["status"] == "imported"
        assert process_pending_import(engine, tmp_path) is None
    finally:
        engine.dispose()


def test_changed_staged_source_stays_pending(tmp_path, payload, monkeypatch):
    import json
    import app.modules.library.icd_import as icd_import

    manifest = tmp_path / "request.json"
    manifest.write_text(json.dumps({"status": "pending", "fingerprint": "different"}))
    monkeypatch.setattr(icd_import, "parse_sources", lambda *args: payload)
    with pytest.raises(ValueError, match="changed"):
        process_pending_import(None, tmp_path)
    assert json.loads(manifest.read_text())["status"] == "pending"


def test_merge_preserves_original_articles_and_long_titles(tmp_path, payload):
    import json
    from sqlalchemy import inspect
    from app.database.models import Base, Disease, LibraryUpdate, DocumentVersion, User
    from app.database.legacy_source_models import SourceFile
    from app.modules.library.icd_merge import merge_icd_tables, key_for

    engine = create_engine("sqlite:///" + (tmp_path / "merge.db").as_posix())
    Base.metadata.create_all(engine)
    try:
        with engine.begin() as c:
            c.execute(
                Disease.__table__.insert(),
                dict(
                    slug="existing",
                    name="Existing",
                    english_name="Existing",
                    category="Viêm da",
                    summary="Keep summary",
                    details="Keep details",
                    risk_factors="",
                    prevention="",
                    aliases=[],
                    published=True,
                ),
            )
            c.execute(
                User.__table__.insert(),
                dict(email="keep@test.example", name="Keep", password_hash="unchanged"),
            )
        payload["entities"][0]["title"] = "Full title " * 30
        import_payload(engine, payload)
        result = merge_icd_tables(engine, tmp_path / "backups")
        assert result["status"] == "merged"
        assert not set(ICDBase.metadata.tables) & set(inspect(engine).get_table_names())
        with engine.connect() as c:
            assert (
                c.scalar(select(Disease.summary).where(Disease.slug == "existing"))
                == "Keep summary"
            )
            assert c.scalar(select(User.password_hash)) == "unchanged"
            assert c.scalar(select(func.count()).select_from(Disease)) == 2
            entity = c.execute(
                select(Disease.summary, Disease.details, Disease.published).where(
                    Disease.review_status == "icd_classification"
                )
            ).one()
            assert entity.summary == payload["entities"][0]["title"]
            assert json.loads(entity.details)["title"] == entity.summary
            assert not entity.published
            assert "tblsource_files" not in inspect(engine).get_table_names()
            assert c.scalar(select(func.count()).select_from(DocumentVersion)) == 3
            assert c.scalar(select(DocumentVersion.content)) == "Chapter content"
            assert c.scalar(select(LibraryUpdate.id)) == key_for(payload["fingerprint"])
        assert merge_icd_tables(engine, tmp_path / "backups")["status"] == "no_legacy_tables"
        from app.modules.library.icd_import import import_payload as unified_import

        assert unified_import(engine, payload)["status"] == "already_imported"
        assert not set(ICDBase.metadata.tables) & set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_failed_merge_rolls_back_without_dropping_old_tables(tmp_path, payload, monkeypatch):
    from sqlalchemy import inspect
    from app.database.models import Base, Disease, LibraryUpdate
    import app.modules.library.icd_merge as icd_merge

    engine = create_engine("sqlite:///" + (tmp_path / "rollback-merge.db").as_posix())
    Base.metadata.create_all(engine)
    import_payload(engine, payload)

    def fail(*args):
        raise ValueError("verification deliberately failed")

    monkeypatch.setattr(icd_merge, "verify_release", fail)
    try:
        with pytest.raises(ValueError, match="verification"):
            icd_merge.merge_icd_tables(engine, tmp_path / "backups")
        assert set(ICDBase.metadata.tables) <= set(inspect(engine).get_table_names())
        with engine.connect() as c:
            assert c.scalar(select(func.count()).select_from(ICDEntity)) == 1
            assert c.scalar(select(func.count()).select_from(Disease)) == 0
            assert c.scalar(select(func.count()).select_from(LibraryUpdate)) == 0
        assert list((tmp_path / "backups").glob("*.zip"))
    finally:
        engine.dispose()


def test_existing_source_table_migrates_and_failure_keeps_bytes(tmp_path, payload, monkeypatch):
    import json
    from sqlalchemy import inspect, delete
    from app.database.models import Base, MedicalDocument, DocumentVersion
    from app.database.legacy_source_models import SourceBase, SourceFile
    import app.modules.library.icd_merge as icd_merge
    from app.modules.library.icd_import import import_payload as unified_import

    engine = create_engine("sqlite:///" + (tmp_path / "existing-source.db").as_posix())
    try:
        Base.metadata.create_all(engine)
        unified_import(engine, payload)
        SourceBase.metadata.create_all(engine)
        with engine.begin() as c:
            manifests = icd_merge.read_source_manifests(c, payload["fingerprint"])
            for manifest in manifests:
                source = manifest["source"]
                c.execute(
                    SourceFile.__table__.insert(),
                    dict(
                        update_id=icd_merge.key_for(payload["fingerprint"]),
                        filename=source["filename"],
                        sha256=source["sha256"],
                        content=b"original",
                        metadata_json=icd_merge.encode(
                            {"release": manifest["release"], "source": source}
                        ),
                    ),
                )
            ids = c.scalars(
                select(MedicalDocument.id).where(
                    MedicalDocument.usage_note == "icd_source_manifest"
                )
            ).all()
            c.execute(delete(DocumentVersion).where(DocumentVersion.document_id.in_(ids)))
            c.execute(delete(MedicalDocument).where(MedicalDocument.id.in_(ids)))
        original = icd_merge.verify_source_documents

        def fail(*args):
            raise ValueError("verification failed")

        monkeypatch.setattr(icd_merge, "verify_source_documents", fail)
        with pytest.raises(ValueError, match="verification"):
            icd_merge.merge_icd_tables(engine, tmp_path / "backups")
        assert "tblsource_files" in inspect(engine).get_table_names()
        with engine.connect() as c:
            assert c.scalars(select(SourceFile.content)).all() == [b"original", b"original"]
        monkeypatch.setattr(icd_merge, "verify_source_documents", original)
        assert (
            icd_merge.merge_icd_tables(engine, tmp_path / "backups")["status"]
            == "source_table_removed"
        )
        assert "tblsource_files" not in inspect(engine).get_table_names()
        assert unified_import(engine, payload)["status"] == "already_imported"
    finally:
        engine.dispose()

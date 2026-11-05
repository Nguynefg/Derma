from app.modules.library.identifiers import find_record
import hashlib
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from app.database.connection import (
    Base,
    Disease,
    Symptom,
    Reference,
    MedicalDocument,
    DocumentVersion,
    LibraryUpdate,
)
from app.data import seed as initial
from app.data import library_expansion as expansion
from app.modules.assistant.knowledge import extract_symptoms


def test_upgrade_preserves_edits_and_does_not_republish(tmp_path, monkeypatch):
    engine = create_engine("sqlite:///" + (tmp_path / "upgrade.db").as_posix())
    factory = sessionmaker(engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(initial, "SessionLocal", factory)
    monkeypatch.setattr(expansion, "SessionLocal", factory)
    try:
        initial.seed()
        with factory() as db:
            original = find_record(db, Disease, "acne")
            original.summary = "Nội dung biên tập được giữ nguyên"
            original.published = False
            db.commit()
        assert expansion.seed_expansion() == 10
        with factory() as db:
            assert db.scalar(select(func.count(Disease.id))) == 16
            assert find_record(db, Disease, "acne").summary == "Nội dung biên tập được giữ nguyên"
            assert not find_record(db, Disease, "acne").published
            assert db.get(LibraryUpdate, expansion.RELEASE)
            for row in expansion.DATA:
                disease = find_record(db, Disease, row["id"])
                ref = find_record(db, Reference, "nhs-" + row["id"])
                doc = find_record(db, MedicalDocument, ref.slug)
                version = db.scalar(
                    select(DocumentVersion).where(DocumentVersion.document_id == doc.id)
                )
                assert disease.published and doc.published
                assert ref.url == doc.source_url and ref.url.startswith(
                    "https://www.nhs.uk/conditions/"
                )
                assert version.checksum == hashlib.sha256(version.content.encode()).hexdigest()
            find_record(db, Disease, "hives").published = False
            find_record(db, MedicalDocument, "nhs-hives").published = False
            db.commit()
        assert expansion.seed_expansion() == 0
        with factory() as db:
            assert db.scalar(select(func.count(Disease.id))) == 16
            assert not find_record(db, Disease, "hives").published
            assert not find_record(db, MedicalDocument, "nhs-hives").published
    finally:
        engine.dispose()


def test_new_symptom_terms_keep_negation():
    result = extract_symptoms("Tôi có mụn nước nhưng không đau da")
    states = {s["id"]: s["presence"] for s in result["symptoms"]}
    assert states["blisters"] == "present"
    assert states["pain"] == "absent"


def test_second_release_adds_34_distinct_topics_and_is_idempotent(tmp_path, monkeypatch):
    from app.data import library_extended as extended

    engine = create_engine("sqlite:///" + (tmp_path / "expanded.db").as_posix())
    factory = sessionmaker(engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(initial, "SessionLocal", factory)
    monkeypatch.setattr(expansion, "SessionLocal", factory)
    try:
        initial.seed()
        expansion.seed_expansion()
        assert extended.seed_extended() == 34
        assert len({d["id"] for d in extended.DATA}) == 34
        assert extended.seed_extended() == 0
        with factory() as db:
            assert db.scalar(select(func.count(Disease.id))) == 50
            assert db.scalar(select(func.count(MedicalDocument.id))) == 44
            for row in extended.DATA:
                disease = find_record(db, Disease, row["id"])
                doc = find_record(db, MedicalDocument, "nhs-" + row["id"])
                version = db.scalar(
                    select(DocumentVersion).where(DocumentVersion.document_id == doc.id)
                )
                assert disease.published and doc.published
                assert version.checksum == hashlib.sha256(version.content.encode()).hexdigest()
                assert doc.source_url.startswith("https://www.nhs.uk/conditions/")
            find_record(db, Disease, "melanoma").summary = "Nội dung được biên tập riêng"
            find_record(db, Disease, "melanoma").published = False
            find_record(db, MedicalDocument, "nhs-melanoma").published = False
            db.commit()
        assert extended.seed_extended() == 0
        with factory() as db:
            assert find_record(db, Disease, "melanoma").summary == "Nội dung được biên tập riêng"
            assert not find_record(db, Disease, "melanoma").published
            assert not find_record(db, MedicalDocument, "nhs-melanoma").published
    finally:
        engine.dispose()


def test_extended_symptom_terms_keep_negation_and_uncertainty():
    states = {
        s["id"]: s["presence"]
        for s in extract_symptoms("Móng dày nhưng không chảy mủ, chưa rõ nốt ruồi thay đổi")[
            "symptoms"
        ]
    }
    assert states["nail-change"] == "present"
    assert states["pus"] == "absent"
    assert states["mole-change"] == "unknown"


def test_dermnet_release_preserves_edits_and_adds_sourced_topics(tmp_path, monkeypatch):
    from app.data import library_extended as extended, library_dermnet as dermnet

    engine = create_engine("sqlite:///" + (tmp_path / "dermnet.db").as_posix())
    factory = sessionmaker(engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(initial, "SessionLocal", factory)
    monkeypatch.setattr(expansion, "SessionLocal", factory)
    try:
        initial.seed()
        expansion.seed_expansion()
        extended.seed_extended()
        with factory() as db:
            find_record(db, Disease, "acne").summary = "Keep editorial text"
            find_record(db, Disease, "acne").published = False
            db.commit()
        assert dermnet.seed_dermnet() == 50
        assert dermnet.seed_dermnet() == 0
        with factory() as db:
            assert db.scalar(select(func.count(Disease.id))) == 100
            assert db.scalar(select(func.count(Symptom.id))) == 40
            assert find_record(db, Disease, "acne").summary == "Keep editorial text"
            assert not find_record(db, Disease, "acne").published
            for row in dermnet.DATA:
                doc = find_record(db, MedicalDocument, "dermnet-" + row["id"])
                ref = find_record(db, Reference, doc.slug)
                version = db.scalar(
                    select(DocumentVersion).where(DocumentVersion.document_id == doc.id)
                )
                assert doc.publisher == ref.publisher == "DermNet"
                assert doc.source_url == ref.url == row["source_url"]
                assert version.checksum == hashlib.sha256(version.content.encode()).hexdigest()
    finally:
        engine.dispose()


def test_new_observation_terms_keep_negation():
    states = {
        s["id"]: s["presence"]
        for s in extract_symptoms("Tôi có mụn mủ nhưng không loét miệng, chưa rõ móng tách")[
            "symptoms"
        ]
    }
    assert states["pustules"] == "present"
    assert states["mouth-ulcers"] == "absent"
    assert states["nail-separation"] == "unknown"


def test_general_release_is_additive_and_has_verified_sources(tmp_path, monkeypatch):
    from app.data import (
        library_extended as extended,
        library_dermnet as dermnet,
        library_general as general,
    )
    from app.modules.library.specialties import specialty_for, supports_photo

    engine = create_engine("sqlite:///" + (tmp_path / "general.db").as_posix())
    factory = sessionmaker(engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(initial, "SessionLocal", factory)
    monkeypatch.setattr(expansion, "SessionLocal", factory)
    try:
        initial.seed()
        expansion.seed_expansion()
        extended.seed_extended()
        dermnet.seed_dermnet()
        with factory() as db:
            find_record(db, Disease, "acne").summary = "Preserve editorial content"
            db.commit()
        assert general.seed_general() == 40
        assert general.seed_general() == 0
        with factory() as db:
            topics = db.scalars(select(Disease)).all()
            assert len(topics) == 140
            assert len({specialty_for(t.category) for t in topics}) == 9
            assert db.scalar(select(func.count(Symptom.id))) == 80
            assert find_record(db, Disease, "acne").summary == "Preserve editorial content"
            for row in general.DATA:
                topic = find_record(db, Disease, row["id"])
                assert not supports_photo(topic)
                document = find_record(db, MedicalDocument, "nhs-" + row["id"])
                reference = find_record(db, Reference, document.slug)
                assert document.source_url == reference.url == row["source_url"]
                assert document.published
                version = db.scalar(
                    select(DocumentVersion).where(DocumentVersion.document_id == document.id)
                )
                assert version.checksum == hashlib.sha256(version.content.encode()).hexdigest()
    finally:
        engine.dispose()


def test_general_symptom_negation():
    states = {
        s["id"]: s["presence"]
        for s in extract_symptoms("Tôi ho nhưng không khó thở, chưa rõ sốt")["symptoms"]
    }
    assert states["cough"] == "present"
    assert states["breathlessness"] == "absent"
    assert states["fever"] == "unknown"

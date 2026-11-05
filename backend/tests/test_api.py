import io
import os
import tempfile
from pathlib import Path
import pytest
from PIL import Image

TEST_PARENT = Path(
    os.environ.get("DERMA_TEST_TMP", str(Path(__file__).resolve().parents[2] / "storage/temporary/api-test-data"))
)
TEST_PARENT.mkdir(parents=True, exist_ok=True)
TEST_DIR = tempfile.TemporaryDirectory(prefix="derma-tests-", dir=TEST_PARENT)
os.environ["DATABASE_URL"] = "sqlite:///" + (Path(TEST_DIR.name) / "test.db").as_posix()
os.environ["DATA_DIR"] = TEST_DIR.name
from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import SessionLocal, User, History, AuditLog, LoginSession, engine
from app.core.security import _buckets
from sqlalchemy import select, func


@pytest.fixture(scope="session", autouse=True)
def close_test_database():
    yield
    engine.dispose()
    TEST_DIR.cleanup()


@pytest.fixture
def client():
    _buckets.clear()
    with TestClient(app) as c:
        yield c


def register(client, email="alice@example.test"):
    from uuid import uuid4

    email = uuid4().hex[:8] + email
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test-password-123", "name": "Test"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    return data, {"X-CSRF-Token": data["csrf"]}


def test_profile_edit_and_mass_assignment_protection(client):
    assert client.patch("/api/v1/auth/profile", json={"name": "Other"}).status_code == 401
    data, headers = register(client)
    assert client.patch("/api/v1/auth/profile", json={"name": "Name"}).status_code == 403
    for body in [
        {"name": "   "},
        {"name": "Name", "role": "admin"},
        {"name": "Name", "email": "other@test.com"},
    ]:
        assert client.patch("/api/v1/auth/profile", headers=headers, json=body).status_code == 422
    r = client.patch("/api/v1/auth/profile", headers=headers, json={"name": "  Nguyễn An  "})
    assert r.status_code == 200
    assert r.json()["user"]["name"] == "Nguyễn An"
    assert r.json()["user"]["role"] == "user"
    assert r.json()["user"]["email"] == data["user"]["email"]
    assert "password_hash" not in r.text


def test_image_label_catalog_tracks_published_database(client):
    result = client.get("/api/v1/images/labels")
    assert result.status_code == 200
    data = result.json()
    assert len(data["topics"]) >= 100
    assert len(data["labels"]) == 40
    assert any(label["id"] == "nail-separation" for label in data["labels"])
    cancer_id = client.get("/api/v1/diseases/basal-cell-carcinoma").json()["id"]
    cancer = next(t for t in data["topics"] if t["id"] == cancer_id)
    assert cancer["scope"]["code"] == "needs_assessment"
    assert any(t["scope"]["code"] == "urgent" for t in data["topics"])
    from app.database.models import Disease

    with SessionLocal() as db:
        db.get(Disease, int(cancer_id)).published = False
        db.commit()
    try:
        assert cancer_id not in {
            t["id"] for t in client.get("/api/v1/images/labels").json()["topics"]
        }
    finally:
        with SessionLocal() as db:
            db.get(Disease, int(cancer_id)).published = True
            db.commit()


def test_general_library_and_specialty_symptom_filter(client):
    result = client.get("/api/v1/diseases", params={"specialty": "Hô hấp"}).json()
    assert len(result["items"]) == 5
    assert all(d["specialty"] == "Hô hấp" and not d["photo_supported"] for d in result["items"])
    assert (
        client.get("/api/v1/diseases", params={"q": "tiểu đường típ 2"}).json()["items"][0]["slug"]
        == "type-2-diabetes"
    )
    topics = client.get("/api/v1/images/labels").json()["topics"]
    assert len(topics) == 100
    assert not {d["id"] for d in result["items"]} & {d["id"] for d in topics}
    symptoms = client.get("/api/v1/symptoms").json()
    cough = next(s for s in symptoms if s["slug"] == "cough")
    assert "Hô hấp" in cough["specialties"]
    response = client.post(
        "/api/v1/search/symptoms", json={"specialty": "Hô hấp", "symptoms": [{"id": cough["id"]}]}
    )
    assert response.status_code == 200
    assert response.json()["items"]
    assert all(d["specialty"] == "Hô hấp" for d in response.json()["items"])
    answer = client.post("/api/v1/answers", json={"question": "Hen phế quản là gì?"}).json()
    assert answer["status"] == "supported"
    assert any(p["disease_name"] == "Hen phế quản" for p in answer["passages"])


def test_public_icd_lookup_paginates_and_does_not_expose_other_drafts(client):
    import json
    from app.database.models import Disease, MedicalDocument, DocumentVersion
    from sqlalchemy import delete

    ids = []
    with SessionLocal() as db:
        for number, kind, title, code in [
            (1, "chapter", "Endocrine chapter", None),
            (2, "block", "Diabetes group", None),
            (3, "category", "Type 2 diabetes mellitus", "5A11"),
        ]:
            metadata = {
                "title": title,
                "code": code,
                "class_kind": kind,
                "chapter_no": "05",
                "linearization_uri": "http://id.who.int/icd/entity/" + str(number),
                "browser_url": "https://icd.who.int/dev11/",
                "parent_uri": None,
            }
            row = Disease(
                slug="icd-test-" + str(number),
                name=title,
                english_name=title,
                category="ICD-11 05",
                summary=title,
                details=json.dumps(metadata, separators=(",", ":")),
                risk_factors="",
                prevention="",
                published=False,
                review_status="icd_classification",
                aliases=[code] if code else [],
            )
            db.add(row)
            db.flush()
            ids.append(row.id)
        draft = Disease(
            slug="private-icd-test",
            name="Private draft",
            english_name="Private",
            category="Khác",
            summary="Private",
            details="secret",
            risk_factors="",
            prevention="",
            published=False,
            aliases=[],
        )
        db.add(draft)
        db.flush()
        ids.append(draft.id)
        db.commit()
    try:
        assert client.get("/api/v1/icd/summary").json()["total"] == 3
        first = client.get("/api/v1/icd", params={"page_size": 2}).json()
        second = client.get("/api/v1/icd", params={"page_size": 2, "page": 2}).json()
        assert first["total"] == 3 and len(first["items"]) == 2 and len(second["items"]) == 1
        assert not {r["id"] for r in first["items"]} & {r["id"] for r in second["items"]}
        found = client.get(
            "/api/v1/icd", params={"q": "5a11", "kind": "category", "chapter": "05"}
        ).json()
        assert found["total"] == 1 and found["items"][0]["code"] == "5A11"
        assert client.get("/api/v1/icd", params={"q": "%"}).json()["total"] == 0
        assert client.get("/api/v1/icd", params={"page_size": 101}).status_code == 422
        assert client.get("/api/v1/icd/" + str(ids[-1])).status_code == 404
        assert (
            client.get("/api/v1/icd/" + str(ids[2])).json()["title"] == "Type 2 diabetes mellitus"
        )
        assert client.get("/api/v1/diseases/" + str(ids[2])).status_code == 404
        combined = client.get(
            "/api/v1/library/search", params={"q": "diabetes", "page_size": 100}
        ).json()
        assert {d["type"] for d in combined["items"]} == {"article", "icd"}
        assert str(ids[-1]) not in {d["id"] for d in combined["items"]}
        icd_only = client.get(
            "/api/v1/library/search", params={"content_type": "icd", "chapter": "05"}
        ).json()
        assert icd_only["total"] == 3 and icd_only["article_count"] == 0
        assert all(d["type"] == "icd" for d in icd_only["items"])
        for entry in icd_only["items"]:
            assert entry["category"] == entry["icd"]["group_name"]
            for text in [entry["category"], entry["summary"]]:
                assert "ICD-11" not in text
                assert "Chương" not in text
                assert "Mục phân loại" not in text
        assert client.get("/api/v1/library/search", params={"q": "%"}).json()["total"] == 0
        first = client.get(
            "/api/v1/library/search", params={"content_type": "icd", "page_size": 2}
        ).json()
        second = client.get(
            "/api/v1/library/search", params={"content_type": "icd", "page_size": 2, "page": 2}
        ).json()
        assert len(first["items"]) == 2 and len(second["items"]) == 1
        assert not {d["id"] for d in first["items"]} & {d["id"] for d in second["items"]}
        assert client.get("/api/v1/library/search", params={"page_size": 101}).status_code == 422
    finally:
        with SessionLocal() as db:
            db.execute(delete(Disease).where(Disease.id.in_(ids)))
            db.commit()


def test_library_merges_exact_icd_match_and_preserves_ambiguous_records(client):
    import json
    from app.database.models import Disease
    from sqlalchemy import delete

    ids = []
    with SessionLocal() as db:
        for slug, title, clinical, kind in [
            ("merge-article", "Unique merger test disease", True, ""),
            ("merge-icd", "Unique merger test disease", False, "category"),
            ("merge-block", "Unique merger test disease", False, "block"),
            ("merge-near", "Unique merger test disease, unspecified", False, "category"),
        ]:
            row = Disease(
                slug=slug,
                name="Bệnh kiểm thử" if clinical else title,
                english_name=title,
                category="Nội tiết" if clinical else "ICD-11 05",
                summary="Nội dung bài gốc" if clinical else title,
                details=(
                    "Nội dung giữ nguyên"
                    if clinical
                    else json.dumps(
                        {
                            "title": title,
                            "code": "TEST-MERGE",
                            "class_kind": kind,
                            "chapter_no": "05",
                            "linearization_uri": "https://id.who.int/test",
                            "browser_url": "https://icd.who.int/dev11/",
                        }
                    )
                ),
                risk_factors="",
                prevention="",
                published=clinical,
                review_status="source_summary" if clinical else "icd_classification",
                aliases=[] if clinical else ["TEST-MERGE"],
            )
            db.add(row)
            db.flush()
            ids.append(row.id)
        db.commit()
    try:
        result = client.get("/api/v1/library/search", params={"q": "TEST-MERGE"}).json()
        assert result["total"] == 3
        merged = next(r for r in result["items"] if int(r["id"]) == ids[0])
        assert merged["code"] == "TEST-MERGE"
        assert merged["article"]["details"] == "Nội dung giữ nguyên"
        assert int(merged["article"]["icd"]["id"]) == ids[1]
        assert ids[1] not in {int(r["id"]) for r in result["items"]}
        assert {ids[2], ids[3]} <= {int(r["id"]) for r in result["items"]}
        filtered = client.get(
            "/api/v1/library/search",
            params={
                "q": "TEST-MERGE",
                "content_type": "icd",
                "chapter": "05",
                "page_size": 1,
            },
        ).json()
        assert filtered["total"] == 3 and len(filtered["items"]) == 1
        detail = client.get("/api/v1/diseases/" + str(ids[0])).json()
        assert detail["icd"]["code"] == "TEST-MERGE"
        # Two exact category candidates must disable automatic merging.
        with SessionLocal() as db:
            row = db.get(Disease, ids[3])
            row.summary = "Unique merger test disease"
            metadata = json.loads(row.details)
            metadata["title"] = row.summary
            row.details = json.dumps(metadata)
            db.commit()
        assert client.get("/api/v1/diseases/" + str(ids[0])).json()["icd"] is None
        assert client.get("/api/v1/library/search", params={"q": "TEST-MERGE"}).json()["total"] == 3
    finally:
        with SessionLocal() as db:
            db.execute(delete(Disease).where(Disease.id.in_(ids)))
            db.commit()


def test_vietnamese_icd_chapter_titles_are_persisted_and_source_is_preserved(client):
    import json
    from app.database.models import Disease
    from app.modules.library.icd_chapters import translate_chapter_titles, CHAPTER_TITLES_VI
    from sqlalchemy import delete

    original = json.dumps(
        {
            "title": "Diseases of the skin",
            "code": "14",
            "class_kind": "chapter",
            "chapter_no": "14",
            "linearization_uri": "https://id.who.int/test",
            "browser_url": "https://icd.who.int/dev11/",
        },
        separators=(",", ":"),
    )
    with SessionLocal() as db:
        row = Disease(
            slug="chapter-translation-test",
            name="Diseases of the skin",
            english_name="Diseases of the skin",
            category="ICD-11 14",
            summary="Diseases of the skin",
            details=original,
            aliases=["14"],
            risk_factors="",
            prevention="",
            published=False,
            review_status="icd_classification",
        )
        db.add(row)
        db.commit()
        row_id = row.id
    try:
        assert len(CHAPTER_TITLES_VI) == 28
        assert max(map(len, CHAPTER_TITLES_VI.values())) <= 120
        assert translate_chapter_titles(engine)["updated_chapters"] == 1
        assert translate_chapter_titles(engine)["updated_chapters"] == 0
        with SessionLocal() as db:
            row = db.get(Disease, row_id)
            assert row.name == "Bệnh da"
            assert row.details == original
            assert row.summary == row.english_name == "Diseases of the skin"
            assert not row.published
            assert "14" in row.aliases
        summary = client.get("/api/v1/icd/summary").json()
        assert summary["chapters"] == [{"code": "14", "title": "Bệnh da"}]
        detail = client.get("/api/v1/icd/" + str(row_id)).json()
        assert detail["title"] == "Bệnh da"
        assert detail["original_title"] == "Diseases of the skin"
        for term in ["Bệnh da", "benh da", "Diseases of the skin"]:
            for endpoint in ["/api/v1/icd", "/api/v1/library/search"]:
                result = client.get(endpoint, params={"q": term}).json()
                assert str(row_id) in {str(r["id"]) for r in result["items"]}
    finally:
        with SessionLocal() as db:
            db.execute(delete(Disease).where(Disease.id == row_id))
            db.commit()


def test_bulk_icd_translation_keeps_source_full_titles_and_search(client, tmp_path):
    import json
    from app.database.models import Disease
    from app.modules.library.icd_translation import apply_translated_titles
    from sqlalchemy import delete

    title = "Synthetic source disease for translation test"
    vietnamese = "Bệnh kiểm thử " + "tổn thương liên quan " * 8 + "đặc hiệu"
    original = json.dumps(
        {
            "title": title,
            "code": "VI-TEST",
            "class_kind": "category",
            "chapter_no": "14",
            "linearization_uri": "https://id.who.int/test",
            "browser_url": "https://icd.who.int/dev11/",
        }
    )
    with SessionLocal() as db:
        row = Disease(
            slug="bulk-translation-test",
            name=title,
            english_name=title,
            category="ICD-11 14",
            summary=title,
            details=original,
            aliases=["VI-TEST"],
            risk_factors="",
            prevention="",
            published=False,
            review_status="icd_classification",
        )
        db.add(row)
        db.commit()
        row_id = row.id
    translations = tmp_path / "titles-vi.json"
    translations.write_text(json.dumps({"translations": {title: vietnamese}}), encoding="utf-8")
    try:
        assert apply_translated_titles(engine, translations)["updated_titles"] == 1
        assert apply_translated_titles(engine, translations)["updated_titles"] == 0
        with SessionLocal() as db:
            row = db.get(Disease, row_id)
            assert len(row.name) == 120
            assert row.english_name == row.summary == title
            assert row.details == original and not row.published
            assert "VI-TEST" in row.aliases
        response = client.get("/api/v1/icd/" + str(row_id)).json()
        assert response["title"] == vietnamese
        assert response["original_title"] == title
        for query in ["đặc hiệu", "dac hieu", "VI-TEST", title]:
            for endpoint in ["/api/v1/icd", "/api/v1/library/search"]:
                data = client.get(endpoint, params={"q": query}).json()
                assert str(row_id) in {str(r["id"]) for r in data["items"]}
        # An invalid cache entry never erases an existing valid translation.
        translations.write_text(json.dumps({"translations": {title: ""}}), encoding="utf-8")
        assert apply_translated_titles(engine, translations)["updated_titles"] == 0
    finally:
        with SessionLocal() as db:
            db.execute(delete(Disease).where(Disease.id == row_id))
            db.commit()


def test_translation_preserves_custom_article_titles(client, tmp_path):
    import json
    from app.database.models import Disease
    from app.modules.library.icd_translation import apply_translated_titles
    from sqlalchemy import delete

    ids = []
    with SessionLocal() as db:
        for slug, name in [
            ("english-title-test", "Synthetic untranslated condition"),
            ("custom-title-test", "Tên do quản trị viên biên tập"),
        ]:
            row = Disease(
                slug=slug,
                name=name,
                english_name="Synthetic untranslated condition",
                category="Khác",
                summary="Tóm tắt tiếng Việt",
                details="Nội dung giữ nguyên",
                risk_factors="",
                prevention="",
                aliases=[],
                published=True,
            )
            db.add(row)
            db.flush()
            ids.append(row.id)
        db.commit()
    path = tmp_path / "translations.json"
    path.write_text(
        json.dumps({"translations": {"Synthetic untranslated condition": "Bệnh kiểm thử"}}),
        encoding="utf-8",
    )
    try:
        assert apply_translated_titles(engine, path)["updated_titles"] == 1
        assert apply_translated_titles(engine, path)["updated_titles"] == 0
        with SessionLocal() as db:
            assert db.get(Disease, ids[0]).name == "Bệnh kiểm thử"
            assert db.get(Disease, ids[0]).details == "Nội dung giữ nguyên"
            assert db.get(Disease, ids[1]).name == "Tên do quản trị viên biên tập"
    finally:
        with SessionLocal() as db:
            db.execute(delete(Disease).where(Disease.id.in_(ids)))
            db.commit()


def test_internal_disease_cannot_be_reference_image_label(client):
    from app.database.models import Disease

    data, headers = register(client)
    with SessionLocal() as db:
        db.get(User, int(data["user"]["id"])).role = "admin"
        db.commit()
    content = io.BytesIO()
    Image.new("RGB", (300, 300)).save(content, format="PNG")
    uploaded = client.post(
        "/api/v1/images/analyze",
        headers=headers,
        files={"file": ("test.png", content.getvalue(), "image/png")},
        data={"analysis_mode": "reference", "save_image": "true"},
    )
    assert uploaded.status_code == 200
    topic = client.get("/api/v1/diseases/asthma").json()
    response = client.put(
        "/api/v1/admin/image-records/" + uploaded.json()["image_record_id"],
        headers=headers,
        json={"disease_id": topic["id"], "is_reference": True},
    )
    assert response.status_code == 422


def test_image_context_validation_and_forwarding(client, monkeypatch):
    import app.modules.images.routes as images
    from app.modules.images.vision_labels import ObservationContext

    content = io.BytesIO()
    Image.new("RGB", (300, 300)).save(content, format="PNG")
    for raw in [
        "bad-json",
        '{"label_ids":["unknown"]}',
        '{"label_ids":["itch","itch"]}',
        '{"site":"invalid"}',
        '{"label_ids": ["itch"] , "role":"admin"}',
    ]:
        response = client.post(
            "/api/v1/images/analyze",
            files={"file": ("test.png", content.getvalue(), "image/png")},
            data={"analysis_mode": "gemini", "observations": raw},
        )
        assert response.status_code == 422
    received = []

    def fake(image, db, context):
        assert isinstance(context, ObservationContext)
        received.append(context)
        return {"status": "unknown", "message": "Chưa rõ"}

    monkeypatch.setattr(images, "analyze_with_gemini", fake)
    response = client.post(
        "/api/v1/images/analyze",
        files={"file": ("test.png", content.getvalue(), "image/png")},
        data={
            "analysis_mode": "gemini",
            "observations": '{"site":"nails","label_ids":["nail-separation"]}',
        },
    )
    assert response.status_code == 200
    assert received[0].site == "nails"
    assert received[0].label_ids == ["nail-separation"]


def test_password_change_rotates_sessions_and_validates(client):
    data, headers = register(client)
    original_cookie = client.cookies.get("derma_session")
    # Keep a second independently authenticated session to check revocation.
    from app.core.config import COOKIE

    original_cookie = client.cookies.get(COOKIE)
    with TestClient(app) as other:
        login = other.post(
            "/api/v1/auth/login",
            json={"email": data["user"]["email"], "password": "Test-password-123"},
        )
        assert login.status_code == 200
        path = "/api/v1/auth/password"
        for current, new, status in [
            ("wrong", "Newpass1@", 400),
            ("Test-password-123", "abcdef", 422),
            ("Test-password-123", "Test-password-123", 422),
        ]:
            assert (
                client.post(
                    path, headers=headers, json={"current_password": current, "new_password": new}
                ).status_code
                == status
            )
        r = client.post(
            path,
            headers=headers,
            json={"current_password": "Test-password-123", "new_password": "Newpass1@"},
        )
        assert r.status_code == 200
        assert r.json()["csrf"] != data["csrf"]
        assert client.cookies.get(COOKIE) != original_cookie
        assert client.get("/api/v1/auth/me").status_code == 200
        assert other.get("/api/v1/auth/me").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": data["user"]["email"], "password": "Test-password-123"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": data["user"]["email"], "password": "Newpass1@"}
        ).status_code
        == 200
    )


def test_bookmarks_private_idempotent_and_published_only(client):
    assert client.get("/api/v1/bookmarks").status_code == 401
    _, headers = register(client)
    disease = client.get("/api/v1/diseases").json()["items"][0]
    path = "/api/v1/bookmarks/" + disease["id"]
    assert client.put(path).status_code == 403
    assert client.put(path, headers=headers).status_code == 204
    assert client.put(path, headers=headers).status_code == 204
    assert [d["id"] for d in client.get("/api/v1/bookmarks").json()] == [disease["id"]]
    with TestClient(app) as other:
        _, other_headers = register(other)
        assert other.get("/api/v1/bookmarks").json() == []
        assert other.delete(path, headers=other_headers).status_code == 204
    assert len(client.get("/api/v1/bookmarks").json()) == 1
    assert client.put("/api/v1/bookmarks/99999999", headers=headers).status_code == 404
    from app.database.models import Disease

    with SessionLocal() as db:
        row = db.get(Disease, int(disease["id"]))
        row.published = False
        db.commit()
    try:
        assert client.get("/api/v1/bookmarks").json() == []
        assert client.put(path, headers=headers).status_code == 404
        assert client.delete(path, headers=headers).status_code == 204
    finally:
        with SessionLocal() as db:
            db.get(Disease, int(disease["id"])).published = True
            db.commit()


def test_keyword_normalization_and_unknown(client):
    r = client.get("/api/v1/diseases", params={"q": "VIEM DA CO DIA"})
    assert [d["slug"] for d in r.json()["items"]] == ["atopic-dermatitis"]
    assert r.json()["items"][0]["references"][0]["url"].startswith("https://www.niams.nih.gov/")
    assert client.get("/api/v1/diseases", params={"q": "no-such-disease"}).json()["items"] == []


def test_public_queries_compile_for_sqlserver(client):
    from sqlalchemy import event
    from sqlalchemy.dialects import mssql

    statements = []

    def capture(connection, clause, multiparams, params, execution_options):
        sql = str(clause.compile(dialect=mssql.dialect()))
        statements.append(sql)
        assert " IS 1" not in sql and " IS 0" not in sql

    event.listen(engine, "before_execute", capture)
    try:
        assert client.get("/api/v1/diseases").status_code == 200
        assert client.get("/api/v1/documents").status_code == 200
        assert (
            client.post(
                "/api/v1/search/symptoms",
                json={"symptoms": [{"id": "itch", "presence": "present"}]},
            ).status_code
            == 200
        )
        assert (
            client.post("/api/v1/answers", json={"question": "Viêm da cơ địa là gì?"}).status_code
            == 200
        )
    finally:
        event.remove(engine, "before_execute", capture)
    assert any("diseases.published = 1" in sql for sql in statements)
    assert any("medical_documents.published = 1" in sql for sql in statements)


def test_symptom_match_and_unknown_presence(client):
    r = client.post(
        "/api/v1/search/symptoms",
        json={
            "symptoms": [
                {"id": "itch", "presence": "present"},
                {"id": "redness", "presence": "unknown"},
            ]
        },
    )
    assert r.status_code == 200
    assert r.json()["items"][0]["matched_symptoms"] == ["Ngứa"]
    assert (
        client.post(
            "/api/v1/search/symptoms", json={"symptoms": [{"id": "itch", "presence": "unknown"}]}
        ).status_code
        == 422
    )
    assert (
        client.post("/api/v1/search/symptoms", json={"symptoms": [{"id": "made-up"}]}).status_code
        == 422
    )


def test_no_implicit_history_and_consent(client):
    data, headers = register(client)
    client.get("/api/v1/diseases?q=acne")
    assert client.get("/api/v1/history").json() == []
    body = {"consent": False, "mode": "keyword", "query": "acne", "result_ids": ["acne"]}
    assert client.post("/api/v1/history", json=body, headers=headers).status_code == 422
    body["consent"] = True
    assert client.post("/api/v1/history", json=body).status_code == 403
    assert client.post("/api/v1/history", json=body, headers=headers).status_code == 201
    assert len(client.get("/api/v1/history").json()) == 1
    assert client.delete("/api/v1/history", headers=headers).status_code == 204
    assert client.get("/api/v1/history").json() == []


def test_user_cannot_read_or_delete_others_history(client):
    _, headers = register(client)
    r = client.post(
        "/api/v1/history",
        headers=headers,
        json={"consent": True, "mode": "keyword", "query": "acne", "result_ids": ["acne"]},
    )
    history_id = r.json()["id"]
    client.post("/api/v1/auth/logout", headers=headers)
    _, other_headers = register(client, "bob@example.test")
    assert client.get("/api/v1/history").json() == []
    assert client.delete("/api/v1/history/" + history_id, headers=other_headers).status_code == 404


def test_auth_and_admin_enforced(client):
    assert client.get("/api/v1/history").status_code == 401
    assert client.get("/api/v1/admin/diseases").status_code == 401
    _, headers = register(client)
    assert client.get("/api/v1/admin/diseases").status_code == 403
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_origin_rejection(client):
    r = client.post(
        "/api/v1/auth/login",
        headers={"Origin": "https://evil.example"},
        json={"email": "x@example.test", "password": "Test-password-123"},
    )
    assert r.status_code == 403


def test_images_are_checked_without_fabricated_prediction(client):
    image = io.BytesIO()
    Image.new("RGB", (256, 256), "white").save(image, format="PNG")
    r = client.post(
        "/api/v1/images/check", files={"file": ("image.png", image.getvalue(), "image/png")}
    )
    assert r.status_code == 200, r.text
    result = r.json()
    assert result["status"] == "model_unavailable" and result["stored"] is False
    assert "predictions" not in result
    assert (
        client.post(
            "/api/v1/images/check",
            files={"file": ("bad.jpg", b"<script>alert(1)</script>", "image/jpeg")},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/images/check",
            files={"file": ("big.png", b"x" * (5 * 1024 * 1024 + 1), "image/png")},
        ).status_code
        == 413
    )


def test_small_image_rejected(client):
    image = io.BytesIO()
    Image.new("RGB", (50, 50)).save(image, format="PNG")
    assert (
        client.post(
            "/api/v1/images/check", files={"file": ("tiny.png", image.getvalue(), "image/png")}
        ).status_code
        == 422
    )


def test_chunked_request_limit(client):
    def chunks():
        for _ in range(7):
            yield b"x" * (1024 * 1024)

    response = client.post(
        "/api/v1/images/check",
        content=chunks(),
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 413


def test_security_headers_and_session_cookie(client):
    response = client.get("/api/v1/health")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    from uuid import uuid4

    response = client.post(
        "/api/v1/auth/register",
        json={"email": uuid4().hex + "@example.test", "password": "Test-password-123"},
    )
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie


def test_admin_edit_and_audit(client):
    data, headers = register(client)
    with SessionLocal() as db:
        user = db.get(User, data["user"]["id"])
        user.role = "admin"
        db.commit()
    body = {
        "name": "Chủ đề kiểm thử",
        "english_name": "Test topic",
        "category": "Test",
        "summary": "Nội dung thử nghiệm chức năng.",
        "details": "Chỉ dùng để kiểm tra luồng biên tập.",
        "risk_factors": "Chưa cung cấp",
        "prevention": "Chưa cung cấp",
        "published": False,
        "symptom_ids": ["itch"],
        "source_title": "Test source",
        "source_url": "https://www.niams.nih.gov/health-topics/atopic-dermatitis",
    }
    r = client.post("/api/v1/admin/diseases", headers=headers, json=body)
    assert r.status_code == 201, r.text
    disease_id = r.json()["id"]
    assert client.get("/api/v1/diseases/" + disease_id).status_code == 404
    body["published"] = True
    r = client.put("/api/v1/admin/diseases/" + disease_id, headers=headers, json=body)
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 2
    assert client.get("/api/v1/diseases/" + disease_id).status_code == 200
    assert any(
        row["entity_id"] == disease_id for row in client.get("/api/v1/admin/audit-logs").json()
    )
    body["source_url"] = "javascript:alert(1)"
    assert (
        client.put("/api/v1/admin/diseases/" + disease_id, headers=headers, json=body).status_code
        == 422
    )


def test_passwords_and_sessions_not_stored_in_clear(client):
    data, _ = register(client)
    with SessionLocal() as db:
        user = db.get(User, data["user"]["id"])
        assert "Test-password-123" not in user.password_hash
        session = db.scalar(select(LoginSession).where(LoginSession.user_id == user.id))
        assert client.cookies.get("derma_session") != session.token_hash


def test_answers_are_grounded_and_do_not_save_history(client):
    register(client)
    response = client.post("/api/v1/answers", json={"question": "Viêm da cơ địa có lây không?"})
    assert response.status_code == 200, response.text
    answer = response.json()
    assert answer["status"] == "supported"
    passage = answer["passages"][0]
    assert passage["disease_id"] == client.get("/api/v1/diseases/atopic-dermatitis").json()["id"]
    assert passage["source_url"].startswith("https://www.niams.nih.gov/")
    assert "không lây" in passage["content"]
    assert passage["document_version"] == 1 and len(passage["checksum"]) == 64
    assert client.get("/api/v1/history").json() == []
    assert (
        client.post("/api/v1/answers", json={"question": "Du lịch sao Hỏa"}).json()["status"]
        == "insufficient_evidence"
    )
    assert (
        client.post("/api/v1/answers", json={"question": "Tôi bị bệnh gì?"}).json()["status"]
        == "out_of_scope"
    )
    assert (
        client.post(
            "/api/v1/answers", json={"question": "Tôi bị ngứa có phải vảy nến không?"}
        ).json()["status"]
        == "out_of_scope"
    )


def test_documents_admin_versioning_visibility_and_concurrency(client):
    assert client.get("/api/v1/admin/documents").status_code == 401
    data, headers = register(client)
    assert client.get("/api/v1/admin/documents").status_code == 403
    with SessionLocal() as db:
        user = db.get(User, data["user"]["id"])
        user.role = "admin"
        db.commit()
    body = {
        "disease_id": "acne",
        "title": "Nguồn kiểm thử retrieval",
        "publisher": "Test only",
        "source_url": "https://example.test/reference",
        "usage_note": "Dữ liệu kiểm thử kỹ thuật, không phải dữ liệu y khoa.",
        "content": "Mã kiểm thử zebravalidation xuất hiện trong tài liệu mụn trứng cá.",
        "published": False,
    }
    response = client.post("/api/v1/admin/documents", headers=headers, json=body)
    assert response.status_code == 201, response.text
    doc = response.json()
    assert not any(d["id"] == doc["id"] for d in client.get("/api/v1/documents").json())
    body["published"] = True
    body["expected_version"] = 1
    response = client.put("/api/v1/admin/documents/" + doc["id"], headers=headers, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["version"] == 2
    assert (
        client.put("/api/v1/admin/documents/" + doc["id"], headers=headers, json=body).status_code
        == 409
    )
    versions = client.get("/api/v1/admin/documents/" + doc["id"] + "/versions").json()
    assert [v["version"] for v in versions] == [2, 1]
    assert versions[1]["content"] == body["content"]
    assert any(d["id"] == doc["id"] for d in client.get("/api/v1/documents").json())
    body["expected_version"] = 2
    body["published"] = False
    assert (
        client.put("/api/v1/admin/documents/" + doc["id"], headers=headers, json=body).status_code
        == 200
    )
    answer = client.post(
        "/api/v1/answers", json={"question": "mụn trứng cá zebravalidation"}
    ).json()
    assert not any(p["document_id"] == doc["id"] for p in answer["passages"])


def test_expanded_library_search_and_grounded_answer(client):
    matches = client.get("/api/v1/diseases", params={"q": "HAC LAO"}).json()["items"]
    assert [d["slug"] for d in matches] == ["ringworm"]
    assert matches[0]["references"][0]["url"] == "https://www.nhs.uk/conditions/ringworm/"
    signs = client.get("/api/v1/symptoms").json()
    assert {"blisters", "pain", "crust", "rough", "wheals"} <= {s["slug"] for s in signs}
    result = client.post(
        "/api/v1/search/symptoms", json={"symptoms": [{"id": "blisters", "presence": "present"}]}
    )
    assert result.status_code == 200
    assert "shingles" in {d["slug"] for d in result.json()["items"]}
    answer = client.post(
        "/api/v1/answers", json={"question": "Ghẻ gây ngứa về đêm như thế nào?"}
    ).json()
    assert any(
        p["disease_id"] == client.get("/api/v1/diseases/scabies").json()["id"]
        and p["source_url"] == "https://www.nhs.uk/conditions/scabies/"
        for p in answer["passages"]
    )


def test_fifty_topic_library_has_sources_and_new_aliases(client):
    from app.data.library_extended import DATA

    items = client.get("/api/v1/diseases").json()["items"]
    by_id = {d["slug"]: d for d in items}
    assert len(by_id) >= 50
    for topic in DATA:
        assert topic["id"] in by_id
        assert by_id[topic["id"]]["references"]
    assert [
        d["slug"] for d in client.get("/api/v1/diseases", params={"q": "LANG BEN"}).json()["items"]
    ] == ["pityriasis-versicolor"]
    assert [
        d["slug"] for d in client.get("/api/v1/diseases", params={"q": "TO DIA"}).json()["items"]
    ] == ["pompholyx"]
    answer = client.post(
        "/api/v1/answers", json={"question": "Nấm móng làm móng đổi màu như thế nào?"}
    ).json()
    assert any(
        p["disease_id"] == client.get("/api/v1/diseases/fungal-nail-infection").json()["id"]
        for p in answer["passages"]
    )


def test_image_analyze_crop_quality_and_no_storage(client):
    import json

    content = io.BytesIO()
    Image.new("RGB", (600, 500), (15, 15, 15)).save(content, format="PNG")
    response = client.post(
        "/api/v1/images/analyze",
        files={"file": ("test.png", content.getvalue(), "image/png")},
        data={
            "image_type": "clinical",
            "crop": json.dumps({"x": 0.1, "y": 0.1, "width": 0.6, "height": 0.6}),
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "unknown" and not result["stored"]
    assert result["metadata_removed"] and (result["width"], result["height"]) == (360, 300)
    assert result["quality"]["lighting"] == "low"
    assert "candidates" not in result and "predictions" not in result
    response = client.post(
        "/api/v1/images/analyze",
        files={"file": ("test.png", content.getvalue(), "image/png")},
        data={"crop": '{"x":0.9,"y":0,"width":1,"height":1}'},
    )
    assert response.status_code == 422
    assert (
        client.post(
            "/api/v1/images/analyze", files={"file": ("bad.jpg", b"not an image", "image/jpeg")}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/images/analyze",
            files={"file": ("test.png", content.getvalue(), "image/png")},
            data={"image_type": "unknown"},
        ).status_code
        == 422
    )
    status = client.get("/api/v1/models/status").json()
    assert status["image_quality"]["status"] == "available"
    assert status["image_model"]["status"] == "not_configured"


def test_image_catalog_reports_database_scope_without_claiming_recognition(client, monkeypatch):
    monkeypatch.setenv("DERMA_IMAGE_MODEL_CARD", "off")
    response = client.get("/api/v1/images/catalog")
    assert response.status_code == 200
    data = response.json()
    assert data["catalog"]["published_topics"] >= 50
    assert data["catalog"]["mapped_topics"] == 0
    assert not data["catalog"]["mapping_valid"]
    assert data["model"]["status"] == "not_configured"


def test_private_image_storage_labelling_lookup_and_deletion(client, monkeypatch, tmp_path):
    from app.database.models import ImageRecord
    from app.modules.images.image_store import image_path

    monkeypatch.setenv("DERMA_IMAGE_STORAGE", str(tmp_path / "images"))
    content = io.BytesIO()
    Image.new("RGB", (512, 512), "gray").save(content, format="PNG")

    def upload(save=False, headers=None, mode="ai"):
        return client.post(
            "/api/v1/images/analyze",
            headers=headers or {},
            data={"save_image": str(save).lower(), "analysis_mode": mode},
            files={"file": ("private.png", content.getvalue(), "image/png")},
        )

    assert upload(True).status_code == 401
    owner, headers = register(client)
    assert upload(True).status_code == 403
    response = upload(True, headers)
    assert response.status_code == 200, response.text
    data = response.json()
    record_id = data["image_record_id"]
    assert data["stored"] and data["status"] == "unknown"
    assert data["database_match"]["status"] == "inconclusive"
    with SessionLocal() as db:
        record = db.get(ImageRecord, record_id)
        assert str(record.user_id) == owner["user"]["id"] and not record.is_reference
        assert record.disease_id is None
    path = image_path(record.file_uuid)
    assert path.is_file()
    assert client.get("/api/v1/images/records/" + record_id + "/file").status_code == 200
    assert (
        client.put(
            "/api/v1/admin/image-records/" + record_id,
            headers=headers,
            json={"disease_id": "acne", "is_reference": True},
        ).status_code
        == 403
    )
    client.post("/api/v1/auth/logout", headers=headers)
    other, other_headers = register(client)
    assert client.get("/api/v1/images/records/" + record_id + "/file").status_code == 404
    assert (
        client.delete("/api/v1/images/records/" + record_id, headers=other_headers).status_code
        == 404
    )
    with SessionLocal() as db:
        db.get(User, other["user"]["id"]).role = "admin"
        db.commit()
    labelled = client.put(
        "/api/v1/admin/image-records/" + record_id,
        headers=other_headers,
        json={"disease_id": "acne", "is_reference": True},
    )
    assert labelled.status_code == 200, labelled.text
    assert upload().json()["status"] == "unknown"  # AI never substitutes an exact-image lookup.
    data = upload(mode="reference").json()
    assert data["status"] == "research_result" and data["method"] == "exact-reference-v1"
    assert data["database_match"]["status"] == "matched"
    assert data["candidates"][0]["name"] == "Mụn trứng cá"
    assert not data["stored"]
    assert (
        client.delete("/api/v1/images/records/" + record_id, headers=other_headers).status_code
        == 204
    )
    assert not path.exists()
    assert upload().json()["status"] == "unknown"


def test_image_result_links_real_catalog_and_rejects_unknown_labels(client, monkeypatch):
    import app.modules.images.routes as images

    # Synthetic model output only; this is not a clinical model evaluation.
    def response(disease_id):
        return {
            "status": "research_result",
            "message": "Synthetic test",
            "candidates": [
                {"disease_id": disease_id, "name": "untrusted model name", "score": 0.9}
            ],
        }

    monkeypatch.setattr(images, "analyze_with_model", lambda *args: response("acne"))
    image = io.BytesIO()
    Image.new("RGB", (512, 512), "gray").save(image, format="PNG")

    def analyze():
        return client.post(
            "/api/v1/images/analyze", files={"file": ("fixture.png", image.getvalue(), "image/png")}
        )

    data = analyze().json()
    assert data["database_match"]["status"] == "matched"
    assert data["candidates"][0]["name"] == "Mụn trứng cá"
    assert data["candidates"][0]["summary"]
    assert data["candidates"][0]["content_version"] >= 1
    monkeypatch.setattr(images, "analyze_with_model", lambda *args: response("does-not-exist"))
    data = analyze().json()
    assert data["status"] == "catalog_mismatch"
    assert data["database_match"]["status"] == "not_evaluated"
    assert "candidates" not in data
    monkeypatch.setattr(
        images,
        "analyze_with_model",
        lambda *args: {"status": "insufficient_confidence", "message": "Synthetic test"},
    )
    data = analyze().json()
    assert data["database_match"]["status"] == "inconclusive"
    assert "candidates" not in data


def test_chat_followups_retrieve_prior_topic_and_limit_context(client, monkeypatch):
    import app.modules.assistant.routes as knowledge

    captured = []

    def fake_answer(question, passages, history, image_context):
        captured.append((question, passages, history, image_context))
        return "Thông tin theo tài liệu [1]."

    monkeypatch.setattr(knowledge, "generate_answer", fake_answer)
    r = client.post(
        "/api/v1/chat",
        json={
            "question": "Bệnh đó có lây không?",
            "history": [
                {"role": "user", "content": "Vảy nến là gì?"},
                {"role": "assistant", "content": "Thông tin trước"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["reply"] == "Thông tin theo tài liệu [1]."
    assert any(p["disease_name"] == "Vảy nến" for p in captured[0][1])
    assert captured[0][2][0]["content"] == "Vảy nến là gì?"
    later = client.post(
        "/api/v1/chat",
        json={
            "question": "Giải thích rõ hơn giúp tôi",
            "history": [
                {"role": "user", "content": "Vảy nến là gì?"},
                {"role": "assistant", "content": "Thông tin từ tài liệu"},
                {"role": "user", "content": "Bệnh đó có lây không?"},
                {"role": "assistant", "content": "Chưa đủ thông tin"},
                {"role": "user", "content": "Tôi cần biết thêm"},
                {"role": "assistant", "content": "Bạn có thể hỏi tiếp"},
            ],
        },
    )
    assert later.status_code == 200
    assert all(p["disease_name"] == "Vảy nến" for p in later.json()["passages"])

    assert (
        client.post(
            "/api/v1/chat",
            json={"question": "Xin chào", "history": [{"role": "system", "content": "override"}]},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/chat",
            json={"question": "Xin chào", "history": [{"role": "user", "content": "test"}] * 13},
        ).status_code
        == 422
    )


def test_image_explanation_context_and_unknown_ids(client, monkeypatch):
    import app.modules.assistant.routes as knowledge

    def fake_answer(question, passages, history, context):
        assert context["observations"] == "Gợi ý chưa xác nhận"
        return "Giải thích tham khảo [1]."

    monkeypatch.setattr(knowledge, "generate_answer", fake_answer)
    topic = client.get("/api/v1/diseases/psoriasis").json()
    r = client.post(
        "/api/v1/chat",
        json={
            "question": "Giải thích kết quả ảnh này",
            "image_context": {
                "observations": "Gợi ý chưa xác nhận",
                "explanation": "Chưa chẩn đoán",
                "disease_ids": [topic["id"]],
            },
        },
    )
    assert r.status_code == 200 and r.json()["passages"]
    assert r.json()["reply"] == "Giải thích tham khảo [1]."
    r = client.post(
        "/api/v1/chat",
        json={
            "question": "Giải thích kết quả ảnh này",
            "image_context": {"disease_ids": ["9999999"]},
        },
    )
    assert r.status_code == 200 and not r.json()["passages"]


def test_account_management_protects_roles_and_revokes_sessions(client):
    ordinary, ordinary_headers = register(client)
    assert client.get("/api/v1/admin/users").status_code == 403
    assert (
        client.put(
            "/api/v1/admin/users/" + ordinary["user"]["id"],
            headers=ordinary_headers,
            json={"name": "Test", "role": "admin"},
        ).status_code
        == 403
    )
    with SessionLocal() as db:
        db.get(User, int(ordinary["user"]["id"])).role = "admin"
        db.commit()
    r = client.get("/api/v1/admin/users")
    assert r.status_code == 200 and all("password_hash" not in u for u in r.json())
    assert (
        client.put(
            "/api/v1/admin/users/" + ordinary["user"]["id"],
            headers=ordinary_headers,
            json={"name": "Test", "role": "user"},
        ).status_code
        == 422
    )
    from app.core.security import hash_password

    with SessionLocal() as db:
        target = User(
            name="Target",
            email="target-" + __import__("uuid").uuid4().hex + "@example.test",
            password_hash=hash_password("Test-password-123"),
        )
        db.add(target)
        db.flush()
        target_id = target.id
        from datetime import timedelta
        from app.database.connection import now

        db.add(
            LoginSession(
                token_hash=__import__("uuid").uuid4().hex * 2,
                user_id=target.id,
                csrf="test",
                expires_at=now() + timedelta(hours=1),
            )
        )
        db.commit()
    r = client.put(
        "/api/v1/admin/users/" + str(target_id),
        headers=ordinary_headers,
        json={"name": "Edited", "role": "admin"},
    )
    assert r.status_code == 200 and r.json()["role"] == "admin"
    with SessionLocal() as db:
        assert not db.scalar(select(LoginSession).where(LoginSession.user_id == target_id))
        assert db.get(User, target_id).name == "Edited"
    assert (
        client.put(
            "/api/v1/admin/users/" + str(target_id), json={"name": "Edited", "role": "user"}
        ).status_code
        == 403
    )


def test_admin_unified_library_pagination_and_versioned_import_edit(client):
    import json
    from sqlalchemy import delete
    from app.database.models import Disease, MedicalDocument, DocumentVersion
    from app.modules.library.library_editorial import PREFIX

    assert client.get("/api/v1/admin/library").status_code == 401
    data, headers = register(client)
    assert client.get("/api/v1/admin/library").status_code == 403
    ids = []
    with SessionLocal() as db:
        db.get(User, int(data["user"]["id"])).role = "admin"
        for number in range(3):
            source = dict(
                title=f"ADMIN-LIB SOURCE {number}",
                chapter_no="05",
                class_kind="category",
                linearization_uri=f"https://example.test/entity/{number}",
                parent_uri=None,
                browser_url="https://example.test/source",
                code=None,
            )
            row = Disease(
                slug=f"admin-unified-test-{number}",
                name=source["title"],
                english_name=source["title"],
                category="ICD-11 05",
                summary=source["title"],
                details=json.dumps(source),
                risk_factors="",
                prevention="",
                aliases=[],
                review_status="icd_classification",
                published=False,
                version=1,
            )
            db.add(row)
            db.flush()
            ids.append(row.id)
        db.commit()
    try:
        params = dict(q="ADMIN-LIB", status="pending", page_size=1)
        first = client.get("/api/v1/admin/library", params=params).json()
        second = client.get("/api/v1/admin/library", params={**params, "page": 2}).json()
        assert first["total"] == second["total"] == 3
        assert len(first["items"]) == len(second["items"]) == 1
        assert first["items"][0]["id"] != second["items"][0]["id"]
        assert first["items"][0]["review_status"] == "pending"
        assert all("ICD-11" not in c["label"] for c in first["categories"])
        target = ids[0]
        assert (
            client.get("/api/v1/admin/library", params={"q": f"BL{target:06d}"}).json()["total"]
            == 1
        )
        form = client.get(f"/api/v1/admin/library/{target}").json()
        assert form["details"] == form["summary"] == ""
        body = dict(
            name="ADMIN-PUBLISHED edited title",
            english_name="Edited English title",
            category="Nội tiết",
            summary="This is an editorial summary.",
            details="This is the editorial overview.",
            risk_factors="Editorial risk factors",
            prevention="Editorial prevention",
            published=False,
            symptom_ids=[],
            source_title="Editorial reference",
            source_url="https://example.test/editorial",
        )
        assert client.put(f"/api/v1/admin/diseases/{target}", json=body).status_code == 403
        response = client.put(f"/api/v1/admin/diseases/{target}", json=body, headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["version"] == 1
        assert "article_content" not in client.get(f"/api/v1/icd/{target}").json()
        assert (
            client.get(
                "/api/v1/admin/library", params={"q": "ADMIN-LIB", "status": "draft"}
            ).json()["total"]
            == 1
        )
        body["published"] = True
        response = client.put(f"/api/v1/admin/diseases/{target}", json=body, headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["version"] == 2
        public = client.get(f"/api/v1/icd/{target}").json()
        assert public["title"] == body["name"]
        assert public["article_content"]["details"] == body["details"]
        assert public["editorial_source"]["url"] == body["source_url"]
        result = client.get("/api/v1/library/search", params={"q": "ADMIN-PUBLISHED"}).json()
        assert result["total"] == 1 and result["items"][0]["summary"] == body["summary"]
        assert (
            client.get(
                "/api/v1/admin/library", params={"q": "ADMIN-LIB", "status": "pending"}
            ).json()["total"]
            == 2
        )
        assert (
            client.get(
                "/api/v1/admin/library", params={"q": "ADMIN-PUBLISHED", "status": "published"}
            ).json()["total"]
            == 1
        )
        with SessionLocal() as db:
            row = db.get(Disease, target)
            assert row.review_status == "icd_classification" and not row.published
            assert json.loads(row.details)["title"] == "ADMIN-LIB SOURCE 0"
            assert row.summary == "ADMIN-LIB SOURCE 0"
            doc = db.scalar(
                select(MedicalDocument).where(MedicalDocument.slug == PREFIX + str(target))
            )
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(DocumentVersion)
                    .where(DocumentVersion.document_id == doc.id)
                )
                == 2
            )
        assert str(doc.id) not in {d["id"] for d in client.get("/api/v1/admin/documents").json()}
        assert client.get("/api/v1/admin/library", params={"page_size": 101}).status_code == 422
    finally:
        with SessionLocal() as db:
            db.execute(delete(MedicalDocument).where(MedicalDocument.disease_id.in_(ids)))
            db.execute(delete(Disease).where(Disease.id.in_(ids)))
            db.commit()

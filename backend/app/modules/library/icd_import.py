"""Read-only parsing and transactional WHO ICD snapshot import. Never execute source formulas."""

import csv
import hashlib
import io
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from sqlalchemy import select, func, text
from app.database.legacy_icd_models import ICDBase, ICDRelease, ICDSource, ICDEntity, ICDChapterDocument
from app.database.models import now


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def parse_sources(zip_path, docx_path):
    source_files = []
    for path in [Path(zip_path), Path(docx_path)]:
        if path.stat().st_size > 64 * 1024 * 1024:
            raise ValueError("Source file exceeds import limit")
        content = path.read_bytes()
        source_files.append(dict(filename=path.name, content=content, sha256=sha(content)))
    with ZipFile(io.BytesIO(source_files[0]["content"])) as archive:
        files = [
            i
            for i in archive.infolist()
            if i.filename.endswith(".txt") and "SimpleTabulation" in i.filename
        ]
        if len(files) != 1 or files[0].file_size > 64 * 1024 * 1024:
            raise ValueError("Expected one SimpleTabulation TXT file")
        tabulation = (
            archive.read(files[0]).decode("utf-8-sig").replace("\r\r\n", "\n").replace("\r\n", "\n")
        )
    reader = csv.DictReader(io.StringIO(tabulation), delimiter="\t")
    required = {
        "Foundation URI",
        "Linearization URI",
        "Code",
        "BlockId",
        "Title",
        "ClassKind",
        "DepthInKind",
        "IsResidual",
        "ChapterNo",
        "BrowserLink",
        "isLeaf",
    }
    if not required <= set(reader.fieldnames or []):
        raise ValueError("Unrecognized tabulation columns")
    version = next(
        (v.partition(":")[2] for v in reader.fieldnames if v.startswith("Version:")), "unknown"
    )
    entities, seen, stack = [], set(), []
    for pos, row in enumerate(reader):
        uri = row["Linearization URI"]
        if not uri or uri in seen or not uri.startswith("http://id.who.int/icd/"):
            raise ValueError("Missing, duplicate or invalid WHO linearization URI")
        seen.add(uri)
        if row["ClassKind"] not in {"chapter", "block", "category"}:
            raise ValueError("Unknown classification kind")
        match = re.fullmatch(r"((?:-\s+)*)(.*)", row["Title"])
        depth = match[1].count("-")
        if row["ClassKind"] == "chapter":
            if depth != 0:
                raise ValueError("Invalid chapter indentation")
            stack = []
        if depth > len(stack):
            raise ValueError("Invalid hierarchy indentation at row " + str(pos + 2))
        stack = stack[:depth]
        parent = stack[-1] if stack else None
        stack.append(uri)
        browser = re.fullmatch(
            r'=hyperlink\("(https://icd\.who\.int/[^"\r\n]+)","browser"\)', row["BrowserLink"], re.I
        )
        if not browser:
            raise ValueError("Unexpected browser link formula")
        entities.append(
            dict(
                foundation_uri=row["Foundation URI"] or None,
                linearization_uri=uri,
                parent_uri=parent,
                code=row["Code"] if row["Code"] not in {"", "_NOCODEASSIGNED"} else None,
                raw_code=row["Code"],
                block_id=row["BlockId"] or None,
                title=match[2],
                class_kind=row["ClassKind"],
                chapter_no=row["ChapterNo"],
                depth=depth,
                source_order=pos,
                browser_url=browser[1],
                raw_row=canonical(row),
            )
        )
    if not entities:
        raise ValueError("Empty classification")
    chapters = {r["chapter_no"] for r in entities if r["class_kind"] == "chapter"}
    documents = []
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with ZipFile(io.BytesIO(source_files[1]["content"])) as outer:
        names = [n for n in outer.namelist() if re.fullmatch(r"word/afchunk\d+\.docx", n)]
        for name in sorted(names):
            if outer.getinfo(name).file_size > 16 * 1024 * 1024:
                raise ValueError("Embedded Word part exceeds limit")
            with ZipFile(io.BytesIO(outer.read(name))) as inner:
                if inner.getinfo("word/document.xml").file_size > 32 * 1024 * 1024:
                    raise ValueError("Word XML exceeds limit")
                root = ET.fromstring(inner.read("word/document.xml"))
                paragraphs = [
                    "".join(t.text or "" for t in p.findall(".//w:t", ns))
                    for p in root.findall(".//w:p", ns)
                ]
            paragraphs = [p for p in paragraphs if p.strip()]
            match = re.fullmatch(r"CHAPTER\s+(\d+|V|X)", paragraphs[0]) if paragraphs else None
            if not match or match[1] not in chapters:
                raise ValueError("Unmatched Word chapter")
            content = "\n".join(paragraphs)
            documents.append(
                dict(
                    chapter_no=match[1],
                    embedded_filename=name,
                    paragraph_count=len(paragraphs),
                    content=content,
                    paragraphs_json=canonical(paragraphs),
                    sha256=sha(content.encode("utf-8")),
                )
            )
    if len(documents) != len(chapters) or {d["chapter_no"] for d in documents} != chapters:
        raise ValueError("Word and tabulation chapters do not agree")
    return dict(
        version=version,
        fingerprint=sha("".join(f["sha256"] for f in source_files).encode()),
        sources=source_files,
        entities=entities,
        documents=documents,
    )


def verify_import(connection, release_id, payload):
    rows = connection.scalars(
        select(ICDEntity.raw_row)
        .where(ICDEntity.release_id == release_id)
        .order_by(ICDEntity.source_order)
    ).all()
    expected = [r["raw_row"] for r in payload["entities"]]
    if rows != expected:
        raise ValueError("Entity count/content verification failed")
    docs = connection.execute(
        select(
            ICDChapterDocument.chapter_no, ICDChapterDocument.content, ICDChapterDocument.sha256
        ).where(ICDChapterDocument.release_id == release_id)
    ).all()
    expected_docs = {d["chapter_no"]: d["sha256"] for d in payload["documents"]}
    if len(docs) != len(expected_docs) or any(
        sha(content.encode("utf-8")) != digest or expected_docs.get(chapter) != digest
        for chapter, content, digest in docs
    ):
        raise ValueError("Word content verification failed")
    sources = connection.execute(
        select(ICDSource.filename, ICDSource.content, ICDSource.sha256).where(
            ICDSource.release_id == release_id
        )
    ).all()
    expected_sources = {s["filename"]: s["sha256"] for s in payload["sources"]}
    if len(sources) != 2 or any(
        sha(content) != digest or expected_sources.get(name) != digest
        for name, content, digest in sources
    ):
        raise ValueError("Original source verification failed")
    return {"entities": len(rows), "chapters": len(docs), "source_files": len(sources)}


def import_legacy_payload(engine, payload):
    with engine.begin() as connection:
        if connection.dialect.name == "mssql":
            connection.execute(
                text(
                    "DECLARE @r int; EXEC @r=sp_getapplock @Resource='derma-icd-import', @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=10000; IF @r<0 THROW 50001, 'ICD import busy', 1;"
                )
            )
        elif connection.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        ICDBase.metadata.create_all(connection)
        existing = connection.scalar(
            select(ICDRelease.id).where(ICDRelease.fingerprint == payload["fingerprint"])
        )
        if existing is not None:
            return {
                "status": "already_imported",
                "release_id": existing,
                **verify_import(connection, existing, payload),
            }
        result = connection.execute(
            ICDRelease.__table__.insert().values(
                fingerprint=payload["fingerprint"],
                version=payload["version"],
                language="en",
                status="development_snapshot",
                entity_count=len(payload["entities"]),
                imported_at=now(),
            )
        )
        release_id = result.inserted_primary_key[0]
        for model, key in [
            (ICDSource, "sources"),
            (ICDEntity, "entities"),
            (ICDChapterDocument, "documents"),
        ]:
            records = [dict(release_id=release_id, **row) for row in payload[key]]
            for offset in range(0, len(records), 50):
                connection.execute(model.__table__.insert(), records[offset : offset + 50])
        return {
            "status": "imported",
            "release_id": release_id,
            **verify_import(connection, release_id, payload),
        }


def import_payload(engine, payload):
    from app.modules.library.icd_merge import existing_unified_import, merge_icd_tables
    from app.database.models import Base

    existing = existing_unified_import(engine, payload)
    if existing:
        return existing
    Base.metadata.create_all(engine)
    imported = import_legacy_payload(engine, payload)
    merge_icd_tables(engine, Path(__file__).resolve().parents[4] / 'storage/backups')
    result = existing_unified_import(engine, payload)
    if not result:
        raise ValueError("Unified import did not complete")
    result["status"] = imported["status"]
    return result


def import_files(engine, zip_path, docx_path):
    return import_payload(engine, parse_sources(zip_path, docx_path))


def process_pending_import(engine, folder):
    """A locally staged, explicitly requested import runs once on server startup."""
    folder = Path(folder)
    manifest_path = folder / "request.json"
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "pending":
        return None
    payload = parse_sources(
        folder / "SimpleTabulation-ICD-11-MMS-en.zip", folder / "print_Foundation_MMS-en.docx"
    )
    if payload["fingerprint"] != manifest.get("fingerprint"):
        raise ValueError("Staged ICD sources changed; refusing to import")
    report = import_payload(engine, payload)
    report.update(version=payload["version"], fingerprint=payload["fingerprint"])
    (folder / "import-result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # If interrupted before this marker, the next startup verifies the existing release.
    manifest["status"] = "complete"
    temp = manifest_path.with_suffix(".tmp")
    temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(manifest_path)
    return report

"""Lossless merge of the four legacy ICD tables into the editorial schema.

ICD classifications remain unpublished, distinguished by review_status. The
original full entity is stored as JSON in details, including its full title.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED
from sqlalchemy import inspect, select, text
from app.database.models import Base, Disease, LibraryUpdate, MedicalDocument, DocumentVersion, now
from app.database.legacy_icd_models import ICDBase, ICDRelease, ICDSource, ICDEntity, ICDChapterDocument
from app.database.legacy_source_models import SourceFile
from app.core.paths import storage_path

SOURCE_ARCHIVE = Path(__file__).resolve().parents[4] / 'storage/backups' / "icd-originals"


def encode(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda v: v.isoformat() if isinstance(v, datetime) else str(v),
    )


def key_for(fingerprint):
    return "icd11-" + fingerprint


def prefix_for(fingerprint):
    return "icd-" + fingerprint[:20] + "-"


def backup_snapshot(folder, snapshot):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (
        "icd-before-merge-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        + "-"
        + uuid4().hex[:8]
        + ".zip"
    )
    with ZipFile(target, "x", compression=ZIP_DEFLATED) as z:
        for name, records in snapshot.items():
            if name == ICDSource.__tablename__:
                metadata = []
                for row in records:
                    entry = f"source-{row['source_id']}.bin"
                    z.writestr(entry, row["content"])
                    metadata.append(
                        {**{k: v for k, v in row.items() if k != "content"}, "backup_entry": entry}
                    )
                z.writestr(name + ".json", encode(metadata))
            else:
                z.writestr(name + ".json", encode(records))
    target.with_suffix(".sha256").write_text(
        hashlib.sha256(target.read_bytes()).hexdigest(), encoding="ascii"
    )
    return str(target)


def write_release(connection, release, entities, documents, sources):
    key = key_for(release["fingerprint"])
    prefix = prefix_for(release["fingerprint"])
    if connection.scalar(select(LibraryUpdate.id).where(LibraryUpdate.id == key)):
        raise ValueError(
            "Target release already exists while legacy tables remain; refusing to overwrite"
        )
    if connection.scalar(select(Disease.id).where(Disease.slug.startswith(prefix))):
        raise ValueError("Target ICD slug collision")
    connection.execute(
        LibraryUpdate.__table__.insert(), {"update_id": key, "applied_at": release["imported_at"]}
    )
    for offset in range(0, len(entities), 50):
        rows = []
        for e in entities[offset : offset + 50]:
            rows.append(
                dict(
                    slug=prefix + str(e["entity_id"]),
                    name=e["title"][:120],
                    english_name=e["title"][:120],
                    category="ICD-11 " + e["chapter_no"],
                    summary=e["title"],
                    details=encode(e),
                    risk_factors="",
                    prevention="",
                    aliases=[e["code"]] if e["code"] else [],
                    published=False,
                    review_status="icd_classification",
                    version=1,
                    updated_at=now(),
                )
            )
        connection.execute(Disease.__table__.insert(), rows)
    rows = connection.execute(
        select(Disease.id, Disease.slug, Disease.details).where(Disease.slug.startswith(prefix))
    ).all()
    mapping = {json.loads(details)["entity_id"]: i for i, slug, details in rows}
    if len(mapping) != len(entities):
        raise ValueError("Target entity count mismatch")
    chapter_entities = {e["chapter_no"]: e for e in entities if e["class_kind"] == "chapter"}
    for d in documents:
        chapter = chapter_entities[d["chapter_no"]]
        title = "ICD-11 Chapter " + d["chapter_no"] + " — WHO"
        slug = prefix + "chapter-" + d["chapter_no"]
        meta = encode({k: v for k, v in d.items() if k != "content"})
        result = connection.execute(
            MedicalDocument.__table__.insert(),
            dict(
                slug=slug,
                disease_id=mapping[chapter["entity_id"]],
                title=title,
                publisher="World Health Organization",
                source_url=chapter["browser_url"],
                usage_note="Original WHO ICD-11 development snapshot; not clinician-reviewed.",
                published=False,
                version=1,
                updated_at=now(),
            ),
        )
        document_id = result.inserted_primary_key[0]
        connection.execute(
            DocumentVersion.__table__.insert(),
            dict(
                document_id=document_id,
                version=1,
                title=title,
                publisher="World Health Organization",
                source_url=chapter["browser_url"],
                usage_note=meta,
                content=d["content"],
                checksum=d["sha256"],
                editor_id=None,
                created_at=now(),
            ),
        )
    store_source_documents(
        connection,
        release,
        sources,
        mapping[next(iter(chapter_entities.values()))["entity_id"]],
        SOURCE_ARCHIVE,
    )
    verify_release(connection, release, entities, documents, sources)
    return {
        "update_id": key,
        "entities": len(entities),
        "chapters": len(documents),
        "source_files": len(sources),
    }


def verify_release(connection, release, entities, documents, sources):
    prefix = prefix_for(release["fingerprint"])
    actual = connection.execute(
        select(Disease.summary, Disease.details, Disease.published).where(
            Disease.slug.startswith(prefix)
        )
    ).all()
    expected = {e["entity_id"]: e for e in entities}
    if len(actual) != len(expected):
        raise ValueError("Entity count verification failed")
    for title, details, published in actual:
        obj = json.loads(details)
        if obj != expected.get(obj.get("entity_id")) or title != obj["title"] or published:
            raise ValueError("Entity content verification failed")
    actual_docs = connection.execute(
        select(
            MedicalDocument.slug,
            DocumentVersion.content,
            DocumentVersion.usage_note,
            DocumentVersion.checksum,
        )
        .join(DocumentVersion, DocumentVersion.document_id == MedicalDocument.id)
        .where(
            MedicalDocument.slug.startswith(prefix),
            DocumentVersion.usage_note != "icd_source_manifest",
        )
    ).all()
    expected_docs = {d["chapter_no"]: d for d in documents}
    if len(actual_docs) != len(expected_docs):
        raise ValueError("Chapter count verification failed")
    for slug, content, metadata, checksum in actual_docs:
        obj = json.loads(metadata)
        expected_doc = expected_docs.get(obj.get("chapter_no"))
        if (
            not expected_doc
            or {**obj, "content": content} != expected_doc
            or checksum != hashlib.sha256(content.encode()).hexdigest()
        ):
            raise ValueError("Chapter content verification failed")
    verify_source_documents(connection, release, sources)


def read_source_manifests(connection, fingerprint):
    rows = connection.scalars(
        select(DocumentVersion.content)
        .join(MedicalDocument, MedicalDocument.id == DocumentVersion.document_id)
        .where(
            MedicalDocument.slug.startswith(prefix_for(fingerprint)),
            DocumentVersion.usage_note == "icd_source_manifest",
        )
    ).all()
    return [json.loads(row) for row in rows]


def verify_archive(manifest):
    path = storage_path(manifest["archive"]["path"])
    if (
        not path.is_file()
        or hashlib.sha256(path.read_bytes()).hexdigest() != manifest["source"]["sha256"]
    ):
        raise ValueError("Original source archive verification failed")


def store_source_documents(connection, release, sources, disease_id, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for source in sources:
        if hashlib.sha256(source["content"]).hexdigest() != source["sha256"]:
            raise ValueError("Original source checksum mismatch")
        extension = Path(source["filename"]).suffix.lower()
        extension = extension if extension in {".zip", ".docx"} else ".bin"
        path = folder / (source["sha256"] + extension)
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(source["content"])
                stream.flush()
                import os

                os.fsync(stream.fileno())
        manifest = {
            "release": release,
            "source": {k: v for k, v in source.items() if k != "content"},
            "archive": {"path": str(path.resolve()), "bytes": len(source["content"])},
        }
        verify_archive(manifest)
        slug = prefix_for(release["fingerprint"]) + "source-" + str(source["source_id"])
        if connection.scalar(select(MedicalDocument.id).where(MedicalDocument.slug == slug)):
            raise ValueError("Source document slug collision")
        title = ("ICD-11 source: " + source["filename"])[:200]
        result = connection.execute(
            MedicalDocument.__table__.insert(),
            dict(
                slug=slug,
                disease_id=disease_id,
                title=title,
                publisher="World Health Organization",
                source_url="https://icd.who.int/",
                usage_note="icd_source_manifest",
                published=False,
                version=1,
                updated_at=now(),
            ),
        )
        content = encode(manifest)
        connection.execute(
            DocumentVersion.__table__.insert(),
            dict(
                document_id=result.inserted_primary_key[0],
                version=1,
                title=title,
                publisher="World Health Organization",
                source_url="https://icd.who.int/",
                usage_note="icd_source_manifest",
                content=content,
                checksum=hashlib.sha256(content.encode()).hexdigest(),
                editor_id=None,
                created_at=now(),
            ),
        )


def verify_source_documents(connection, release, sources):
    manifests = read_source_manifests(connection, release["fingerprint"])
    expected = {s["source_id"]: {k: v for k, v in s.items() if k != "content"} for s in sources}
    if len(manifests) != len(sources):
        raise ValueError("Source document count mismatch")
    for manifest in manifests:
        if manifest["source"] != expected.get(manifest["source"]["source_id"]) or encode(
            manifest["release"]
        ) != encode(release):
            raise ValueError("Source metadata verification failed")
        verify_archive(manifest)


def migrate_source_table(connection, backup_dir):
    rows = [dict(r) for r in connection.execute(select(SourceFile.__table__)).mappings()]
    groups = {}
    for row in rows:
        meta = json.loads(row["metadata_json"])
        release = meta["release"]
        if (
            row["filename"] != meta["source"]["filename"]
            or row["sha256"] != meta["source"]["sha256"]
        ):
            raise ValueError("Source metadata differs from stored file")
        if row["update_id"] != key_for(release["fingerprint"]):
            raise ValueError("Invalid source release link")
        group = groups.setdefault(row["update_id"], {"release": release, "sources": []})
        group["sources"].append({**meta["source"], "content": row["content"]})
    total = 0
    for group in groups.values():
        release = group["release"]
        prefix = prefix_for(release["fingerprint"])
        chapter = connection.scalar(
            select(MedicalDocument.disease_id).where(
                MedicalDocument.slug.startswith(prefix + "chapter-")
            )
        )
        if chapter is None:
            raise ValueError("Cannot attach source metadata: missing chapter")
        store_source_documents(
            connection, release, group["sources"], chapter, Path(backup_dir) / "icd-originals"
        )
        verify_source_documents(connection, release, group["sources"])
        total += len(group["sources"])
    SourceFile.__table__.drop(connection)
    return total


def merge_icd_tables(engine, backup_dir):
    with engine.begin() as connection:
        if connection.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        if connection.dialect.name == "mssql":
            connection.execute(
                text(
                    "DECLARE @r int; EXEC @r=sp_getapplock @Resource='derma-icd-import', @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=10000; IF @r<0 THROW 50001, 'ICD merge busy', 1;"
                )
            )
        tables = set(inspect(connection).get_table_names())
        legacy = set(ICDBase.metadata.tables)
        removed_sources = (
            migrate_source_table(connection, backup_dir) if "tblsource_files" in tables else 0
        )
        if not tables & legacy:
            return {
                "status": "source_table_removed" if removed_sources else "no_legacy_tables",
                "source_files": removed_sources,
            }
        if not legacy <= tables:
            raise ValueError("Partial legacy ICD schema; refusing to merge")
        Base.metadata.create_all(connection)
        snapshot = {}
        for table in ICDBase.metadata.sorted_tables:
            query = select(table)
            if connection.dialect.name == "mssql":
                query = query.with_hint(table, "WITH (TABLOCKX, HOLDLOCK)", dialect_name="mssql")
            snapshot[table.name] = [dict(r) for r in connection.execute(query).mappings()]
        backup = backup_snapshot(backup_dir, snapshot)
        releases = snapshot[ICDRelease.__tablename__]
        known = {r["release_id"] for r in releases}
        for name, records in snapshot.items():
            if name != ICDRelease.__tablename__ and any(
                r["release_id"] not in known for r in records
            ):
                raise ValueError("Orphan legacy release reference")
        result = []
        for release in releases:
            entities = sorted(
                [
                    e
                    for e in snapshot[ICDEntity.__tablename__]
                    if e["release_id"] == release["release_id"]
                ],
                key=lambda e: e["source_order"],
            )
            docs = [
                d
                for d in snapshot[ICDChapterDocument.__tablename__]
                if d["release_id"] == release["release_id"]
            ]
            sources = [
                s
                for s in snapshot[ICDSource.__tablename__]
                if s["release_id"] == release["release_id"]
            ]
            if len(entities) != release["entity_count"]:
                raise ValueError("Legacy entity count differs from release metadata")
            result.append(write_release(connection, release, entities, docs, sources))
        for table in reversed(ICDBase.metadata.sorted_tables):
            table.drop(connection)
        return {"status": "merged", "releases": result, "backup": backup}


def existing_unified_import(engine, payload):
    if "tblsource_files" in inspect(engine).get_table_names():
        merge_icd_tables(engine, SOURCE_ARCHIVE.parent)
    with engine.connect() as connection:
        if "tbllibrary_updates" not in inspect(connection).get_table_names():
            return None
        key = key_for(payload["fingerprint"])
        if not connection.scalar(select(LibraryUpdate.id).where(LibraryUpdate.id == key)):
            return None
        prefix = prefix_for(payload["fingerprint"])
        actual = connection.execute(
            select(Disease.id, Disease.details).where(Disease.slug.startswith(prefix))
        ).all()
        from app.modules.library.library_source import SOURCE_PREFIX
        preserved = {
            disease_id: json.loads(content)['source']
            for disease_id, content in connection.execute(
                select(MedicalDocument.disease_id, DocumentVersion.content)
                .join(DocumentVersion, DocumentVersion.document_id == MedicalDocument.id)
                .where(MedicalDocument.slug.startswith(SOURCE_PREFIX),
                       DocumentVersion.version == MedicalDocument.version)
            )
        }
        entities = sorted([preserved[row_id] if row_id in preserved else json.loads(details)
                           for row_id, details in actual], key=lambda e: e["source_order"])
        if [e["raw_row"] for e in entities] != [e["raw_row"] for e in payload["entities"]]:
            raise ValueError("Unified ICD entity verification failed")
        sources = read_source_manifests(connection, payload["fingerprint"])
        if len(sources) != len(payload["sources"]):
            raise ValueError("Unified source count mismatch")
        expected = {(s["filename"], s["sha256"]) for s in payload["sources"]}
        if {(s["source"]["filename"], s["source"]["sha256"]) for s in sources} != expected:
            raise ValueError("Unified source content mismatch")
        for manifest in sources:
            verify_archive(manifest)
        doc_rows = connection.execute(
            select(DocumentVersion.content, DocumentVersion.checksum)
            .join(MedicalDocument, MedicalDocument.id == DocumentVersion.document_id)
            .where(
                MedicalDocument.slug.startswith(prefix),
                DocumentVersion.usage_note != "icd_source_manifest",
            )
        ).all()
        if len(doc_rows) != len(payload["documents"]) or sorted(
            hashlib.sha256(c.encode()).hexdigest() for c, h in doc_rows
        ) != sorted(d["sha256"] for d in payload["documents"]):
            raise ValueError("Unified Word verification failed")
        return {
            "status": "already_imported",
            "update_id": key,
            "entities": len(entities),
            "chapters": len(doc_rows),
            "source_files": len(sources),
        }

"""Apply reviewed, source-cited missing fields with backup and conflict checks."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.database.models import Disease, MedicalDocument, DocumentVersion, Reference, now
from sqlalchemy import select, update

FIELDS = ('summary', 'details', 'risk_factors', 'prevention')
EMPTY = {'', 'Thông tin tóm tắt đang được bổ sung.', 'Nội dung tổng quan đang được bổ sung.',
         'Chưa bổ sung thông tin về yếu tố liên quan.', 'Chưa bổ sung thông tin về phòng ngừa và chăm sóc.'}


def validated(entry):
    source = entry['source']
    host = urlparse(source['url']).hostname
    is_nci = source.get('type') == 'nci_thesaurus_definition'
    if is_nci:
        if host != 'ncit.nci.nih.gov' or source.get('license') != 'CC BY 4.0':
            raise ValueError('NCI source must retain its official host and attribution license')
    elif host != 'medlineplus.gov':
        raise ValueError('Unexpected source host')
    if hashlib.sha256(source['text'].encode()).hexdigest() != entry['source_sha256']:
        raise ValueError('Source checksum mismatch')
    changes = {}
    for field in FIELDS:
        item = entry['draft'][field]
        text = item['text'].strip()
        quotes = item['evidence']
        if bool(text) != bool(quotes):
            raise ValueError('Missing evidence')
        if text:
            if entry['baseline'][field].strip() not in EMPTY:
                raise ValueError('Attempt to replace populated baseline')
            for quote in quotes:
                if not quote.strip() or ' '.join(quote.split()) not in ' '.join(source['text'].split()):
                    raise ValueError('Evidence does not match source')
            changes[field] = text
    return changes


def apply_entries(engine, entries, folder, apply=False):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    plans = [(e, validated(e)) for e in entries]
    plans = [(e, changes) for e, changes in plans if changes]
    conflicts = []
    pending = []
    with engine.connect().execution_options(isolation_level='SERIALIZABLE') as conn, conn.begin():
        for entry, changes in plans:
            rid = int(entry['draft']['id'])
            query = select(Disease.__table__).where(Disease.id == rid)
            if conn.dialect.name == 'mssql':
                query = query.with_hint(Disease.__table__, 'WITH (UPDLOCK, HOLDLOCK)', dialect_name='mssql')
            current = conn.execute(query).mappings().one_or_none()
            identity = ('slug', 'name', 'english_name')
            if current is None or any(current[f] != entry['baseline'][f] for f in identity):
                conflicts.append({'id': rid, 'reason': 'Missing record or changed disease identity'})
                continue
            remaining = {}
            for field, text in changes.items():
                live = current[field].strip()
                if live == text:
                    continue
                if live != entry['baseline'][field].strip() or live not in EMPTY:
                    conflicts.append({'id': rid, 'field': field, 'reason': 'Live field changed'})
                else:
                    remaining[field] = text
            if remaining:
                pending.append((entry, remaining, dict(current)))
        if conflicts:
            return {'status': 'conflicts_nothing_applied', 'conflicts': conflicts}
        result = {'status': 'preview', 'records': len(pending), 'fields': sum(len(c) for _, c, _ in pending), 'conflicts': []}
        if not apply or not pending:
            if apply and not pending:
                result['status'] = 'already_applied_or_no_supported_changes'
            return result
        backup = folder / 'before-content-completion.jsonl.gz'
        with backup.open('xb') as raw:
            with gzip.GzipFile(fileobj=raw, mode='wb') as compressed:
                for _, _, row in pending:
                    compressed.write((json.dumps(row, ensure_ascii=False, default=str) + '\n').encode())
            raw.flush()
            os.fsync(raw.fileno())
        with gzip.open(backup, 'rt', encoding='utf-8') as check:
            if sum(1 for _ in check) != len(pending):
                raise ValueError('Backup verification failed')
        for entry, changes, current in pending:
            rid = current['disease_id']
            conn.execute(update(Disease).where(Disease.id == rid).values(**changes, version=current['version'] + 1, updated_at=now()))
            source = entry['source']
            publisher = 'National Library of Medicine'
            note = 'Source: MedlinePlus, National Library of Medicine. Vietnamese source-based draft; not clinically validated.'
            if source.get('type') == 'nci_thesaurus_definition':
                publisher = 'National Cancer Institute'
                note = ('Adapted into Vietnamese from NCI Thesaurus, National Cancer Institute, version '
                        + source['version'] + '. CC BY 4.0: https://creativecommons.org/licenses/by/4.0/. '
                        'This translation is not the original NCI text and is not clinically validated.')
            title = source['title'][:200]
            slug = 'clinical-enrichment-' + str(rid) + '-' + entry['source_sha256'][:12]
            doc = conn.execute(select(MedicalDocument.id).where(MedicalDocument.slug == slug)).scalar_one_or_none()
            if doc is None:
                doc = conn.execute(MedicalDocument.__table__.insert().values(slug=slug, disease_id=rid, title=title, publisher=publisher, source_url=source['url'], usage_note=note, published=False, version=1, updated_at=now()).returning(MedicalDocument.id)).scalar_one()
                content = json.dumps(entry, ensure_ascii=False, default=str)
                conn.execute(DocumentVersion.__table__.insert().values(document_id=doc, version=1, title=title, publisher=publisher, source_url=source['url'], usage_note=note, content=content, checksum=hashlib.sha256(content.encode()).hexdigest(), editor_id=None))
            reference = conn.execute(select(Reference.id).where(Reference.disease_id == rid, Reference.url == source['url'])).first()
            if reference is None:
                conn.execute(Reference.__table__.insert().values(disease_id=rid, title=title, publisher=publisher, url=source['url'], accessed_at=datetime.now(timezone.utc).date().isoformat(), usage_note=note))
        return dict(result, status='applied', backup=str(backup))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--work-dir', type=Path, default=ROOT / 'storage/temporary/content-completion-20261021')
    parser.add_argument('--include-nci', action='store_true')
    args = parser.parse_args()
    from app.database.connection import engine
    state = json.loads((args.work_dir / 'reviewed-drafts.json').read_text('utf-8'))
    if not state.get('final_editorial_review'):
        raise SystemExit('Drafts need a final editorial review before database application.')
    entries = list(state['drafts'].values())
    if args.include_nci:
        nci = json.loads((ROOT / 'storage/temporary/content-completion-nci-20261021/reviewed-drafts.json').read_text('utf-8'))
        if not nci.get('final_editorial_review'):
            raise SystemExit('NCI drafts need a final editorial review before database application.')
        entries.extend(nci['drafts'].values())
    ids = [e['draft']['id'] for e in entries]
    if len(ids) != len(set(ids)):
        raise SystemExit('Overlapping record IDs in source packages; nothing applied.')
    folder = args.work_dir / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True, exist_ok=True)
    try:
        result = apply_entries(engine, entries, folder, args.apply)
    except Exception as exc:
        from sqlalchemy.exc import OperationalError
        if not isinstance(exc, OperationalError):
            raise
        result = {'status': 'connection_failed_nothing_applied', 'conflicts': [],
                  'reason': 'Cannot connect to configured SQL Server from this process. Run scripts\\complete-content.cmd in the local project terminal.'}
    result['database_backend'] = engine.dialect.name
    (folder / 'apply-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf-8')
    print(json.dumps(result, ensure_ascii=True))
    if result['conflicts'] or result['status'] == 'connection_failed_nothing_applied':
        raise SystemExit(1)


if __name__ == '__main__':
    main()

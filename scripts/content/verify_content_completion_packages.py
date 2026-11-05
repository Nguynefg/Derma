"""Verify the whole prepared batch against an isolated in-memory database."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from sqlalchemy import create_engine, select, func

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.database.models import Base, Disease, DocumentVersion, Reference
from scripts.content.apply_content_completion import apply_entries, validated, FIELDS


def main():
    folders = [ROOT / 'storage/temporary/content-completion-20261021', ROOT / 'storage/temporary/content-completion-nci-20261021']
    entries = []
    for folder in folders:
        state = json.loads((folder / 'reviewed-drafts.json').read_text('utf-8'))
        assert state['final_editorial_review']
        entries.extend(e for e in state['drafts'].values() if validated(e))
    assert len({e['draft']['id'] for e in entries}) == len(entries)
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        for entry in entries:
            row = dict(entry['baseline'])
            row['updated_at'] = datetime.fromisoformat(row['updated_at'])
            conn.execute(Disease.__table__.insert().values(**row))
    output = folders[0] / ('package-verification-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    applied = apply_entries(engine, entries, output / 'first', True)
    assert applied['records'] == len(entries)
    assert applied['fields'] == sum(len(validated(e)) for e in entries)
    with engine.connect() as conn:
        for entry in entries:
            row = conn.execute(select(Disease.__table__).where(Disease.id == int(entry['draft']['id']))).mappings().one()
            changes = validated(entry)
            for field in FIELDS:
                assert row[field] == changes.get(field, entry['baseline'][field])
            for field in ['name', 'english_name', 'slug', 'category', 'aliases', 'published', 'review_status']:
                assert row[field] == entry['baseline'][field]
            assert row['version'] == entry['baseline']['version'] + 1
        assert conn.scalar(select(func.count()).select_from(DocumentVersion)) == len(entries)
        assert conn.scalar(select(func.count()).select_from(Reference)) == len(entries)
    repeated = apply_entries(engine, entries, output / 'second', True)
    assert repeated['records'] == repeated['fields'] == 0
    report = {'status': 'passed', 'test_database': 'isolated_in_memory_sqlite', 'live_sql_modified': False,
              'records': applied['records'], 'fields': applied['fields'], 'repeat_changes': repeated['records'],
              'unrelated_fields_preserved': True, 'all_source_versions_and_references_preserved': True}
    (output / 'verification.json').write_text(json.dumps(report, indent=2), 'utf-8')
    combined = []
    for folder in folders:
        combined.extend(json.loads((folder / 'ready-content.json').read_text('utf-8')))
    previous = json.loads((folders[0] / 'ready-content-before-continuation.json').read_text('utf-8'))
    before = {(r['id'], f) for r in previous for f in r['fields']}
    after = {(r['id'], f) for r in combined for f in r['fields']}
    summary = {'prepared_records': len(combined), 'prepared_fields': len(after),
               'additional_field_slots_this_continuation': len(after - before),
               'additional_records_this_continuation': len({r['id'] for r in combined} - {r['id'] for r in previous}),
               'live_sql_modified': False, 'clinical_validation': False,
               'verification_report': str(output / 'verification.json')}
    (folders[0] / 'combined-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), 'utf-8')
    labels = {'summary': 'Tóm tắt', 'details': 'Tổng quan', 'risk_factors': 'Nguyên nhân và yếu tố liên quan', 'prevention': 'Phòng ngừa và chăm sóc'}
    lines = ['# Nội dung bổ sung tổng hợp', '',
             f"{len(combined)} mục, {len(after)} trường đã chuẩn bị. Tăng {len(after - before)} trường so với gói trước. Chưa xác nhận ghi vào SQL Server; chưa thẩm định lâm sàng.", '',
             'Nguồn: MedlinePlus, National Library of Medicine; NCI Thesaurus, National Cancer Institute. Phần NCI được chuyển ngữ theo [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), không phải nguyên văn do NCI công bố.', '']
    for row in sorted(combined, key=lambda r: r['name'].casefold()):
        lines.extend([f"## {row['name']} (ID {row['id']})", ''])
        for field, value in row['fields'].items():
            lines.extend([f'{labels[field]}: {value}', ''])
        lines.extend([f"Nguồn: {row['source_url']}", ''])
    (folders[0] / 'Noi-dung-bo-sung-tong-hop.md').write_text('\n'.join(lines), 'utf-8')
    print(json.dumps({'verification': report, 'batch': summary}))


if __name__ == '__main__':
    main()

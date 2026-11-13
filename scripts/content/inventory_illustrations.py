"""Read the current library and export an illustration replacement queue; never mutate SQL."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sources = parser.add_mutually_exclusive_group()
    sources.add_argument('--base-url', help='Read the running public library API instead of SQL')
    sources.add_argument('--from-inventory', type=Path, help='Recheck assets against an explicit previous inventory; does not read live SQL')
    args = parser.parse_args()
    source_created_at = None
    if args.from_inventory:
        previous = json.loads(args.from_inventory.read_text(encoding='utf-8'))
        rows = previous['items']
        source = 'explicit_inventory_snapshot'
        source_created_at = previous.get('source_created_at') or previous.get('created_at')
    elif args.base_url:
        from read_website_library import read_live_records
        rows = read_live_records(args.base_url)
        source = 'live_website'
    else:
        from dotenv import load_dotenv
        load_dotenv(ROOT / '.env')
        from sqlalchemy import text
        from app.database.connection import engine
        with engine.connect() as connection:
            rows = [dict(row) for row in connection.execute(text(
                'SELECT disease_id, slug, name, english_name FROM dbo.tbldiseases'
            )).mappings()]
        source = 'live_database'
    normalize = lambda value: ' '.join((value or '').lower().strip().split())
    covers = json.loads((ROOT / 'frontend/src/shared/data/diseaseCovers.json').read_text(encoding='utf-8'))
    by_name = {normalize(name): cover for cover in covers for name in cover['names']}
    counts = {}
    for row in rows:
        cover = by_name.get(normalize(row['english_name'])) or by_name.get(normalize(row['name']))
        status = 'pending_new'
        if cover:
            status = 'completed' if cover['src'].startswith('/assets/library/illustrations/') else 'pending_replace'
            if not (ROOT / 'frontend/public' / cover['src'].lstrip('/')).is_file():
                status = 'missing_asset'
        row['illustration_status'] = status
        row['current_asset'] = cover['src'] if cover else None
        counts[status] = counts.get(status, 0) + 1
    output = ROOT / 'storage/exports/generated-illustrations'
    output.mkdir(parents=True, exist_ok=True)
    unique_illustrations = len({row['current_asset'] for row in rows if row['illustration_status'] == 'completed'})
    report = dict(source=source, source_created_at=source_created_at,
                  created_at=datetime.now(timezone.utc).isoformat(),
                  records=len(rows), counts=counts, unique_illustrations=unique_illustrations, items=rows)
    (output / 'replacement-queue.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(status='inventoried', source=source, records=len(rows), counts=counts,
                         unique_illustrations=unique_illustrations, output=str(output)), ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps(dict(status='not_completed', error_type=type(error).__name__,
                             message='Cannot read the current library; no database data changed.')))
        sys.exit(1)

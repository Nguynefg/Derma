"""Normalize verified terminology in both title dictionaries, with exact backups.

Does not invent clinical articles or apply unverified AI proposals. SQL is updated
separately by apply_icd_translations.py using the same normalizer.
"""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.modules.library.icd_terminology import medical_title


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = ROOT / 'storage/backups' / ('vietnamese-normalization-' + stamp)
    output.mkdir(parents=True)
    reports = []
    for relative in ('backend/app/data/icd_titles_vi.json', 'storage/imports/icd-import/titles-vi.json'):
        path = ROOT / relative
        if not path.exists():
            continue
        original = path.read_bytes()
        data = json.loads(original)
        changes = []
        for source, old in data['translations'].items():
            new = medical_title(source, old)
            if old != new:
                changes.append({'source': source, 'before': old, 'after': new})
                data['translations'][source] = new
        if changes:
            (output / (relative.replace('/', '__'))).write_bytes(original)
            temp = path.with_suffix('.normalizing.tmp')
            temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            temp.replace(path)
        reports.append({'file': relative, 'updated': len(changes), 'before_sha256': hashlib.sha256(original).hexdigest(), 'changes': changes})
    (output / 'changes.json').write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'files': [{k:v for k,v in r.items() if k != 'changes'} for r in reports], 'backup': str(output)}, ensure_ascii=False))


if __name__ == '__main__':
    main()

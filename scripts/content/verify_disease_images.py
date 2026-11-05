import re
"""Validate public image provenance, asset integrity and exact-name uniqueness."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
rows=json.loads((ROOT/'frontend/public/assets/library/diseases/credits.json').read_text(encoding='utf-8'))
registry=json.loads((ROOT/'frontend/src/shared/data/diseaseCovers.json').read_text(encoding='utf-8'))
assert len(rows)==len(registry)
names=set();sources=set()
for row,entry in zip(rows,registry):
 assert all(row.get(k)==v for k,v in entry.items())
 path=(ROOT/'frontend/public'/row['src'].lstrip('/')).resolve()
 assert path.parent==(ROOT/'frontend/public/assets/library/diseases').resolve()
 assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
 assert bool(re.fullmatch(r'CC BY(?:-SA)? \d+\.\d+(?: [a-z]{2})?',row['license'])) or row['license'] in ('CC0','Public domain')
 assert row['sourceUrl'].startswith('https://commons.wikimedia.org/wiki/File:')
 assert row['creator'].strip() and row['licenseUrl'].startswith('https://')
 assert row['src'] not in sources;sources.add(row['src'])
 for name in row['names']:
  normalized=' '.join(name.casefold().split());assert normalized not in names;names.add(normalized)
assert 'alpha thalassemia, unspecified' not in names
assert 'female pattern hair loss' not in names
assert 'scalp psoriasis' not in names
print(f'PASS: {len(rows)} licensed assets, {len(names)} unique exact names, matching credits and integrity hashes; unreviewed redirects excluded.')

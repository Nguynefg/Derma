"""Add name-based search aliases to Word exports without changing database data."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from lxml import etree as ET
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'storage/exports/tbldiseases-moi-file-50-ban-ghi'
OUTPUT = ROOT / 'storage/exports/tbldiseases-50-ban-ghi-bo-sung-tu-khoa'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}
ET.register_namespace('w', W)


def clean(value):
    return ' '.join(unicodedata.normalize('NFC', value).split()).strip()


def unaccent(value):
    value = value.replace('đ','d').replace('Đ','D')
    return ''.join(c for c in unicodedata.normalize('NFD', value) if not unicodedata.combining(c))


def text(cell):
    return ''.join(cell.itertext())


def fields(table):
    result = {}
    for row in table.findall('w:tr', NS):
        cells = row.findall('w:tc', NS)
        if len(cells) != 2:
            raise ValueError('Expected two cells per field')
        result[text(cells[0])] = cells[1]
    if len(result) != 14:
        raise ValueError('Expected all 14 fields')
    return result


def expand(values):
    old = json.loads(text(values['aliases']))
    if not isinstance(old, list) or any(not isinstance(a, str) for a in old):
        raise ValueError('Aliases must be a list of strings')
    result = list(old)
    seen = {a.casefold() for a in old}

    def add(value):
        value = clean(value)
        if value and value.casefold() not in seen:
            result.append(value)
            seen.add(value.casefold())

    candidates = [text(values['name']), text(values['english_name'])]
    # The vi alias retains full titles when the display name column is shorter.
    candidates.extend(a[3:] for a in old if a.startswith('vi:'))
    for a in old:
        if not a.startswith(('vi:', 'chapter:', 'kind:', 'article-columns:')):
            candidates.append(a)
    slug = text(values['slug'])
    if not slug.startswith(('icd-', 'library-')) and re.fullmatch(r'[a-z]+(?:-[a-z]+)+', slug):
        candidates.extend([slug, slug.replace('-', ' ')])
    for value in candidates:
        add(value)
        add(unaccent(value).lower())
        punctuation = re.sub(r'[-–—_]', ' ', value)
        if punctuation != value:
            add(punctuation)
            add(unaccent(punctuation).lower())
    if text(values['slug']) == 'acanthosis-nigricans':
        for value in ['bệnh gai đen','da dày sẫm màu','mảng da sẫm màu','da dày như nhung',
                      'sạm da vùng cổ','sạm da vùng nách','sạm da vùng bẹn']:
            add(value)
            add(unaccent(value).lower())
    return old, result


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source_files = sorted(p for p in SOURCE.glob('*.docx') if not p.name.startswith('~$'))
    total, changed, new_terms = 0, 0, 0
    reports = []
    before_hash, after_hash = hashlib.sha256(), hashlib.sha256()
    for index, path in enumerate(source_files, 1):
        with ZipFile(path) as archive:
            root = ET.fromstring(archive.read('word/document.xml'))
            snapshots = []
            file_count = 0
            for table in root.findall('w:body/w:tbl', NS):
                row = fields(table)
                snapshot = [(k, text(c)) for k, c in row.items() if k != 'aliases']
                before_hash.update(json.dumps(snapshot, ensure_ascii=False).encode())
                old, updated = expand(row)
                if updated != old:
                    cell = row['aliases']
                    for child in list(cell):
                        if child.tag != '{' + W + '}tcPr':
                            cell.remove(child)
                    p = ET.SubElement(cell, '{' + W + '}p')
                    ppr = ET.SubElement(p, '{' + W + '}pPr')
                    ET.SubElement(ppr, '{' + W + '}spacing', {'{' + W + '}after':'60'})
                    run = ET.SubElement(p, '{' + W + '}r')
                    rpr = ET.SubElement(run, '{' + W + '}rPr')
                    ET.SubElement(rpr, '{' + W + '}rFonts', {'{' + W + '}ascii':'Arial','{' + W + '}hAnsi':'Arial'})
                    ET.SubElement(rpr, '{' + W + '}sz', {'{' + W + '}val':'20'})
                    ET.SubElement(run, '{' + W + '}t').text = json.dumps(updated, ensure_ascii=False)
                    changed += 1
                    new_terms += len(updated) - len(old)
                snapshots.append((snapshot, updated))
                total += 1
                file_count += 1
            destination = OUTPUT / path.name
            with ZipFile(destination, 'w', ZIP_DEFLATED) as target:
                for item in archive.infolist():
                    target.writestr(item.filename, ET.tostring(root, encoding='utf-8', xml_declaration=True)
                                    if item.filename == 'word/document.xml' else archive.read(item.filename))
        with ZipFile(destination) as verify:
            verified = ET.fromstring(verify.read('word/document.xml')).findall('w:body/w:tbl', NS)
            assert len(verified) == file_count <= 50
            for table, (snapshot, updated) in zip(verified, snapshots):
                row = fields(table)
                actual = [(k, text(c)) for k, c in row.items() if k != 'aliases']
                assert actual == snapshot
                assert json.loads(text(row['aliases'])) == updated
                after_hash.update(json.dumps(actual, ensure_ascii=False).encode())
        reports.append({'file':path.name, 'records':file_count})
        if index % 100 == 0:
            print(json.dumps({'processed_files':index, 'records':total}), flush=True)
    assert before_hash.digest() == after_hash.digest()
    report = {'files':len(reports), 'records':total, 'records_updated':changed,
              'aliases_added':new_terms, 'records_per_file':50,
              'last_file_records':reports[-1]['records'], 'other_13_fields_unchanged':True,
              'database_modified':False,
              'method':'Preserve old aliases; add Vietnamese and English names, full vi aliases, unaccented forms and semantic slugs. No generated clinical synonyms.'}
    (OUTPUT / 'Bao-cao-bo-sung-tu-khoa.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with (OUTPUT / 'Danh-sach-file.csv').open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['file','records'])
        writer.writeheader()
        writer.writerows(reports)
    bundle = OUTPUT.with_suffix('.zip')
    with ZipFile(bundle, 'w', ZIP_DEFLATED) as archive:
        for path in sorted(OUTPUT.iterdir()):
            archive.write(path, path.name)
    print(json.dumps({**report, 'zip':str(bundle)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

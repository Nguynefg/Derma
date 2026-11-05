"""Find missing Word article fields and exact matching definitions in supplied sources."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import sqlite3
import unicodedata
from zipfile import ZipFile
from lxml import etree as ET

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'storage/temporary/word-content-20261019'
INPUT = ROOT / 'storage/exports/tbldiseases-50-ban-ghi-bo-sung-tu-khoa'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w':W}
CLINICAL = ['summary','details','risk_factors','prevention']
PLACEHOLDERS = {'', 'Thông tin tóm tắt đang được bổ sung.', 'Nội dung tổng quan đang được bổ sung.',
                'Chưa bổ sung thông tin về yếu tố liên quan.', 'Chưa bổ sung thông tin về phòng ngừa và chăm sóc.'}


def normalized(value):
    value=unicodedata.normalize('NFKC',value).replace('’',"'")
    value=re.sub('[\u2010\u2011\u2012\u2013\u2014]','-',value)
    return ' '.join(value.split()).casefold()


def definitions():
    found = {}
    with ZipFile(ROOT / 'storage/imports/icd-import/print_Foundation_MMS-en.docx') as outer:
        for name in outer.namelist():
            if not re.fullmatch(r'word/afchunk\d+\.docx', name):
                continue
            with ZipFile(BytesIO(outer.read(name))) as inner:
                root = ET.fromstring(inner.read('word/document.xml'))
            current = None
            for p in root.findall('.//w:p', NS):
                style = p.find('w:pPr/w:pStyle', NS)
                style = style.get('{' + W + '}val', '') if style is not None else ''
                text = ''.join((t.text or '') if t.tag == '{'+W+'}t' else '\t'
                               for t in p.iter() if t.tag in {'{'+W+'}t','{'+W+'}tab'}).strip()
                if style in {'CategoryTitlePara','FirstLevelCategoryTitlePara'}:
                    match = re.match(r'^(\S+)\s+(.+)$', text)
                    current = {'title':match[2], 'code':match[1], 'definitions':[], 'embedded_file':name} if match else None
                    if current:
                        found.setdefault(normalized(current['title']), []).append(current)
                elif style.startswith('BlockTitle') or style == 'ChapterTitle':
                    title = re.sub(r'\s+\([^)]*\)\s*$', '', text)
                    current = {'title':title, 'code':None, 'definitions':[], 'embedded_file':name}
                    found.setdefault(normalized(title), []).append(current)
                elif style in {'CategoryDefinition','ChOrBlockDefinition'} and current and text:
                    if not text.startswith(('This chapter has ', 'Code range starts with ')):
                        current['definitions'].append(text)
    return found


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    source_definitions = definitions()
    with sqlite3.connect((ROOT / 'storage/imports/icd-import/validation-only.sqlite').resolve().as_uri() + '?mode=ro', uri=True) as db:
        sources = {slug:json.loads(raw) for slug,raw in db.execute("SELECT slug,details FROM tbldiseases WHERE review_status='icd_classification'")}
    total = pending = matched = 0
    missing_counts = dict.fromkeys(CLINICAL, 0)
    inputs = []
    with (WORK / 'records.jsonl').open('w', encoding='utf-8') as output:
        files = sorted(p for p in INPUT.glob('*.docx') if not p.name.startswith('~$'))
        for index,path in enumerate(files,1):
            inputs.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
            with ZipFile(path) as archive:
                root = ET.fromstring(archive.read('word/document.xml'))
            for table in root.findall('w:body/w:tbl', NS):
                fields = {}
                for row in table.findall('w:tr', NS):
                    cells = row.findall('w:tc', NS)
                    fields[''.join(cells[0].itertext())] = ''.join(cells[1].itertext())
                total += 1
                missing = [key for key in CLINICAL if fields[key].strip() in PLACEHOLDERS]
                if not missing:
                    continue
                pending += 1
                for key in missing:
                    missing_counts[key] += 1
                metadata = sources.get(fields['slug'])
                source = None
                if metadata:
                    candidates = [c for c in source_definitions.get(normalized(metadata['title']), []) if c['definitions']]
                    exact_code = [c for c in candidates if c['code'] == metadata.get('code')]
                    if exact_code:
                        candidates = exact_code
                    distinct = {tuple(c['definitions']) for c in candidates}
                    if len(distinct) == 1:
                        source = candidates[0]
                        matched += 1
                output.write(json.dumps({'file':path.name, 'fields':fields, 'missing':missing,
                    'source':source, 'source_url':metadata.get('browser_url') if metadata else None,
                    'source_title':metadata.get('title') if metadata else fields['english_name'],
                    'kind':metadata.get('class_kind') if metadata else 'article',
                    'chapter':metadata.get('chapter_no') if metadata else None}, ensure_ascii=False) + '\n')
            if index % 200 == 0:
                print(json.dumps({'scanned_files':index,'pending_records':pending,'matched_definitions':matched}),flush=True)
    report = {'total_records':total,'pending_records':pending,'fields_missing':missing_counts,
              'records_with_exact_source_definition':matched,'records_without_definition':pending-matched,
              'input_folder':str(INPUT),'files':inputs}
    (WORK / 'preparation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='files'},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()

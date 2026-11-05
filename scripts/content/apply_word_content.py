"""Apply source-grounded drafts to the Word copies only, with a full gap report."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from collections import Counter
import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as ET

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'storage/temporary/word-content-20261019'
SOURCE=ROOT/'storage/exports/tbldiseases-50-ban-ghi-bo-sung-tu-khoa'
OUTPUT=ROOT/'storage/exports/tbldiseases-50-ban-ghi-bo-sung-noi-dung'
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS={'w':W}
ET.register_namespace('w',W)
FIELDS=['summary','details','risk_factors','prevention']
PLACEHOLDERS={'','Thông tin tóm tắt đang được bổ sung.','Nội dung tổng quan đang được bổ sung.',
              'Chưa bổ sung thông tin về yếu tố liên quan.','Chưa bổ sung thông tin về phòng ngừa và chăm sóc.'}


def celltext(cell):
    parts=[]
    for index,p in enumerate(cell.findall('w:p',NS)):
        if index:parts.append('\n')
        for node in p.iter():
            if node.tag=='{'+W+'}t':parts.append(node.text or '')
            elif node.tag=='{'+W+'}br':parts.append('\n')
            elif node.tag=='{'+W+'}tab':parts.append('\t')
    return ''.join(parts)


def tablefields(table):
    result={}
    for tr in table.findall('w:tr',NS):
        cells=tr.findall('w:tc',NS)
        if len(cells)!=2:raise ValueError('Expected two cells per field')
        result[celltext(cells[0])]=cells[1]
    if len(result)!=14:raise ValueError('Expected fourteen fields')
    return result


def paragraph(text,size=20):
    p=ET.Element('{'+W+'}p')
    pp=ET.SubElement(p,'{'+W+'}pPr')
    ET.SubElement(pp,'{'+W+'}spacing',{'{'+W+'}after':'60'})
    for i,line in enumerate(text.splitlines() or ['']):
        r=ET.SubElement(p,'{'+W+'}r')
        rp=ET.SubElement(r,'{'+W+'}rPr')
        ET.SubElement(rp,'{'+W+'}rFonts',{'{'+W+'}ascii':'Arial','{'+W+'}hAnsi':'Arial'})
        ET.SubElement(rp,'{'+W+'}sz',{'{'+W+'}val':str(size)})
        if i:ET.SubElement(r,'{'+W+'}br')
        ET.SubElement(r,'{'+W+'}t').text=line
    return p


def source_guard(field,text,source):
    if len(text)>100 and text.isascii():
        return 'Đoạn nội dung dài chưa thể hiện bằng tiếng Việt có dấu'
    if field in {'summary','details'} and len(text)>max(400,3.2*len(source)):
        return 'Bản thảo dài vượt đáng kể đoạn nguồn, cần đối chiếu thêm'
    if re.match(r'^(?:hiện\s+)?(?:chưa có (?:định nghĩa|mô tả|thông tin)|không có (?:mô tả|định nghĩa|thông tin)|nguồn (?:chưa|không)|tài liệu (?:chưa|không))',text,re.I):
        return 'Câu này chỉ thông báo thiếu dữ liệu, chưa phải nội dung biên soạn'
    checks=[
        (r'\bhiếm\b',r'rar(e|ity)|uncommon|infrequent|exceptional','Tính hiếm gặp chưa được nêu trong nguồn'),
        (r'\btự miễn\b',r'autoimmun|autoantibod|self.antigen|autoreact|self.reactiv','Cơ chế tự miễn chưa được nêu trong nguồn'),
        (r'\bdi truyền\b',r'genetic|inherit|heredit|famil|mutation|\bgene\b|genomic|chromosom|autosomal|mendel|x.linked','Đặc điểm di truyền chưa được nêu trong nguồn'),
    ]
    for vietnamese,english,reason in checks:
        if re.search(vietnamese,text,re.I) and not re.search(english,source,re.I):return reason
    if field=='prevention' and text:
        if re.search(r'\d\s*(?:mg|mcg|µg|μg|ml|mL|g/kg|mg/kg)\b',text):
            return 'Nội dung liều dùng cần chuyên gia kiểm tra trước khi đưa vào bài'
        if not re.search(r'prevent|prophy|vaccin|avoidance|avoiding|hygien|sanit|immuniz|immunis|can be managed|treated with|treatment (?:is|with|requires|includes)|respond\w* to|corrected by|care (?:includes|requires)|reduc\w*.*risk',source,re.I):
            return 'Chưa tìm thấy nội dung phòng ngừa hoặc chăm sóc rõ trong dẫn chứng'
    return None


def main():
    OUTPUT.mkdir(parents=True,exist_ok=False)
    preparation=json.loads((WORK/'preparation.json').read_text('utf-8'))
    hashes={r['file']:r['sha256'] for r in preparation['files']}
    drafts=json.loads((WORK/'drafts.json').read_text('utf-8'))['drafts']
    source_rows={r['fields']['disease_id']:r for r in map(json.loads,(WORK/'records.jsonl').open(encoding='utf-8'))}
    changed_fields=Counter(); changed_records=0; total=0; completed=0; gaps=[]; provenance=[]
    excluded=[]
    files=sorted(p for p in SOURCE.glob('*.docx') if not p.name.startswith('~$'))
    # Reuse existing authored content only for an exact, unambiguous English
    # title match to a category. Never propagate an article to a subtype/group.
    def key(value):return ' '.join(unicodedata.normalize('NFKC',value).replace('’',"'").split()).casefold()
    authored={}
    ambiguous=set()
    for path in files[:4]:
        with ZipFile(path) as archive:root=ET.fromstring(archive.read('word/document.xml'))
        for table in root.findall('w:body/w:tbl',NS):
            values={k:celltext(c) for k,c in tablefields(table).items()}
            if values['review_status'] not in {'source_summary','editor_reviewed'}:continue
            if values['published'].casefold() not in {'true','1'}:continue
            if any(values[f].strip() in PLACEHOLDERS for f in FIELDS):continue
            title=key(values['english_name'])
            if title in authored:ambiguous.add(title)
            authored[title]=values
    reused_records=0
    for index,path in enumerate(files,1):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=hashes[path.name]:
            raise ValueError('Input changed during preparation: '+path.name)
        with ZipFile(path) as archive:
            root=ET.fromstring(archive.read('word/document.xml'))
            records=root.findall('w:body/w:tbl',NS)
            snapshots=[];file_changed=False
            for table in records:
                cells=tablefields(table)
                before={k:celltext(c) for k,c in cells.items()}
                disease_id=before['disease_id']
                draft=drafts.get(disease_id)
                meta=source_rows.get(disease_id)
                if draft:
                    source_text=' '.join('\n'.join(meta['source']['definitions']).split()) if meta and meta['source'] else ''
                    if any(not quote.strip() or ' '.join(quote.split()) not in source_text
                           for field in FIELDS for quote in draft[field]['evidence']):
                        draft=None
                reuse=None
                if meta and meta['kind']=='category':
                    title=key(meta['source_title'])
                    if title not in ambiguous:reuse=authored.get(title)
                changes={}
                if draft or reuse:
                    for field in FIELDS:
                        new=reuse[field] if reuse else draft[field]['text'].strip()
                        if new and not reuse:
                            guard_source='\n'.join(draft[field]['evidence']) if field=='prevention' else meta['source_title']+'\n'+'\n'.join(meta['source']['definitions'])
                            reason=source_guard(field,new,guard_source)
                            if reason:
                                excluded.append({'disease_id':disease_id,'field':field,'reason':reason,'draft':new})
                                continue
                        if before[field].strip() in PLACEHOLDERS and new:
                            cell=cells[field]
                            for child in list(cell):
                                if child.tag!='{'+W+'}tcPr':cell.remove(child)
                            cell.append(paragraph(new))
                            changes[field]=new
                            changed_fields[field]+=1
                if changes:
                    changed_records+=1;file_changed=True
                    meta=source_rows[disease_id]
                    if reuse:reused_records+=1
                    note=('Bài cùng tên đã có trong bộ dữ liệu, disease_id '+reuse['disease_id']) if reuse else meta['source_url']
                    source_note=paragraph('Nguồn cho phần bổ sung: '+note,18)
                    table.addnext(source_note)
                    provenance.append({'disease_id':disease_id,'file':path.name,'source_title':meta['source_title'],
                        'source_url':None if reuse else meta['source_url'],
                        'source_definition':meta['source']['definitions'] if meta['source'] and not reuse else [],
                        'source_is_development_draft':any('#DRAFT#' in d for d in meta['source']['definitions']) if meta['source'] and not reuse else False,
                        'fields':{f:{'text':reuse[f],'reused_from_disease_id':reuse['disease_id']} if reuse else draft[f] for f in changes},'clinical_validation':False})
                after={k:celltext(c) for k,c in cells.items()}
                for k in before:
                    assert after[k]==(changes[k] if k in changes else before[k])
                missing=[f for f in FIELDS if after[f].strip() in PLACEHOLDERS]
                if not missing:completed+=1
                else:
                    meta=source_rows.get(disease_id)
                    reason='Có định nghĩa, nhưng nguồn không nêu đủ từng trường' if meta and meta['source'] else 'Chưa có đoạn mô tả riêng khớp trong tài liệu nguồn'
                    if meta and meta['source'] and not draft:reason='Có định nghĩa; bản thảo chưa hoàn tất hoặc chưa qua kiểm tra dẫn chứng'
                    gaps.append({'disease_id':disease_id,'name':after['name'],'file':path.name,'missing_fields':', '.join(missing),'reason':reason})
                total+=1
                snapshots.append(after)
            if file_changed:
                body=root.find('w:body',NS)
                body.insert(4,paragraph('Phần nội dung bổ sung được biên soạn với hỗ trợ của AI và đối chiếu tài liệu nguồn; chưa được thẩm định lâm sàng.',18))
            destination=OUTPUT/path.name
            with ZipFile(destination,'w',ZIP_DEFLATED) as target:
                for item in archive.infolist():
                    target.writestr(item.filename, ET.tostring(root,encoding='utf-8',xml_declaration=True)
                                    if item.filename=='word/document.xml' else archive.read(item.filename))
        with ZipFile(destination) as verify:
            checked=ET.fromstring(verify.read('word/document.xml')).findall('w:body/w:tbl',NS)
            assert len(checked)==len(snapshots)<=50
            for table,expected in zip(checked,snapshots):
                assert {k:celltext(c) for k,c in tablefields(table).items()}==expected
        if index%200==0:print(json.dumps({'files_written':index,'updated_records':changed_records}),flush=True)
    assert total==preparation['total_records']
    with (OUTPUT/'Cac-muc-con-thieu-noi-dung.csv').open('w',encoding='utf-8-sig',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=['disease_id','name','file','missing_fields','reason'])
        writer.writeheader();writer.writerows(gaps)
    (OUTPUT/'Nguon-va-dan-chung.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUTPUT/'Ban-thao-bi-loai-can-doi-chieu.json').write_text(json.dumps(excluded,ensure_ascii=False,indent=2),encoding='utf-8')
    report={'total_records':total,'word_files':len(files),'records_with_new_content':changed_records,
            'fields_filled':dict(changed_fields),'records_with_all_four_content_fields':completed,'reused_exact_title_articles':reused_records,
            'records_still_missing_content':len(gaps),'records_with_matching_definition':preparation['records_with_exact_source_definition'],
            'records_without_source_definition':preparation['records_without_definition'],
            'unmodified_fields':['disease_id','slug','name','english_name','category','aliases','published','review_status','version','updated_at'],
            'fields_excluded_by_conservative_source_checks':len(excluded),
            'database_modified':False,'clinically_validated':False}
    (OUTPUT/'Bao-cao-bo-sung-noi-dung.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    bundle=OUTPUT.with_suffix('.zip')
    with ZipFile(bundle,'w',ZIP_DEFLATED) as archive:
        for path in sorted(OUTPUT.iterdir()):archive.write(path,path.name)
    print(json.dumps({**report,'zip':str(bundle)},ensure_ascii=False,indent=2))


if __name__=='__main__':main()

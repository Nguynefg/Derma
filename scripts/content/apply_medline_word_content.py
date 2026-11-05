"""Apply reviewed, source-matched NLM drafts to a fresh Word-only package."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import shutil
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as ET
from scripts.content.apply_word_content import NS,W,FIELDS,PLACEHOLDERS,celltext,tablefields,paragraph

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'storage/temporary/word-content-20261019/medlineplus'
SOURCE=ROOT/'storage/exports/tbldiseases-50-ban-ghi-ra-soat-lan-2'
OUTPUT=ROOT/'storage/exports/tbldiseases-50-ban-ghi-ra-soat-lan-3'

def normalized(text):return ' '.join(text.split())

def main():
    candidates={r['fields']['disease_id']:r for r in map(json.loads,(WORK/'candidates.jsonl').open(encoding='utf-8'))}
    state=json.loads((WORK/'reviewed-drafts.json').read_text('utf-8'))
    drafts=state['drafts']
    OUTPUT.mkdir(exist_ok=False)
    files=sorted(p for p in SOURCE.glob('*.docx') if not p.name.startswith('~$'))
    assert len(files)==745
    changes=[];gaps=[];total=complete=changedfiles=0;fieldcounts=Counter();protected_before=hashlib.sha256();protected_after=hashlib.sha256()
    for i,path in enumerate(files,1):
        with ZipFile(path) as z:root=ET.fromstring(z.read('word/document.xml'))
        body=root.find('w:body',NS);tables=body.findall('w:tbl',NS)
        assert 0<len(tables)<=50
        expected=[];changed=False
        for table in tables:
            cells=tablefields(table);before={k:celltext(v) for k,v in cells.items()};after=before.copy()
            total+=1;rid=before['disease_id'];entry=candidates.get(rid);updated=[]
            if rid in drafts:
                assert entry and entry['fields']['slug']==before['slug']
                assert entry.get('scope_match_approved',False)
                assert entry['fields']['english_name']==before['english_name']
                source=normalized(entry['source']['text']);sourcehash=hashlib.sha256(source.encode()).hexdigest()
                for field in FIELDS:
                    d=drafts[rid][field];text=d['text'].strip()
                    if not text or before[field].strip() not in PLACEHOLDERS:continue
                    assert field in entry['missing']
                    assert d['evidence']
                    spans=[]
                    for quote in d['evidence']:
                        q=normalized(quote);start=source.find(q);assert q and start>=0
                        spans.append({'start':start,'end':start+len(q)})
                    cell=cells[field]
                    for child in list(cell):
                        if child.tag!='{'+W+'}tcPr':cell.remove(child)
                    cell.append(paragraph(text));after[field]=text;updated.append(field);fieldcounts[field]+=1
                    changes.append({'disease_id':rid,'name':before['name'],'field':field,'previous':before[field],
                      'text':text,'source_title':entry['source']['title'],'source_url':entry['source']['url'],
                      'source_type':entry['source']['type'],'attribution':'Source: MedlinePlus, National Library of Medicine.',
                      'source_normalized_sha256':sourcehash,'evidence_offsets_in_normalized_source':spans,
                      'accessed_at':'2026-10-19','draft_method':'AI translation followed by a second source-based AI editorial check',
                      'clinical_validation':False})
            if updated:
                changed=True
                note='Nguồn bổ sung lần 3: Source: MedlinePlus, National Library of Medicine. '+entry['source']['url']+'. Bản diễn giải tiếng Việt có hỗ trợ AI; chưa được thẩm định lâm sàng.'
                body.insert(body.index(table)+1,paragraph(note,size=17))
            protected={k:v for k,v in before.items() if k not in FIELDS}
            assert protected=={k:v for k,v in after.items() if k not in FIELDS}
            protected_before.update(json.dumps(protected,ensure_ascii=False,sort_keys=True).encode())
            protected_after.update(json.dumps({k:v for k,v in after.items() if k not in FIELDS},ensure_ascii=False,sort_keys=True).encode())
            absent=[f for f in FIELDS if after[f].strip() in PLACEHOLDERS]
            if absent:gaps.append({'disease_id':rid,'name':before['name'],'file':path.name,'missing_fields':'; '.join(absent),
              'reason':'Chưa có nội dung riêng đủ căn cứ cho các trường được liệt kê; không tự điền bằng suy đoán.'})
            else:complete+=1
            expected.append(after)
        target=OUTPUT/path.name
        if changed:
            changedfiles+=1
            with ZipFile(path) as src,ZipFile(target,'w',ZIP_DEFLATED) as dst:
                for info in src.infolist():
                    data=ET.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True) if info.filename=='word/document.xml' else src.read(info.filename)
                    dst.writestr(info,data)
        else:shutil.copy2(path,target)
        with ZipFile(target) as z:
            assert z.testzip() is None
            check=ET.fromstring(z.read('word/document.xml'))
        actual=[{k:celltext(v) for k,v in tablefields(t).items()} for t in check.findall('w:body/w:tbl',NS)]
        assert actual==expected,path.name
        if i%200==0:print(json.dumps({'verified_files':i,'filled_fields':sum(fieldcounts.values())}),flush=True)
    assert total==37236 and protected_before.digest()==protected_after.digest()
    # Preserve previous provenance without carrying over an obsolete gap list.
    for path in SOURCE.glob('*.json'):shutil.copy2(path,OUTPUT/path.name)
    with (OUTPUT/'Cac-muc-con-thieu-noi-dung.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['disease_id','name','file','missing_fields','reason']);writer.writeheader();writer.writerows(gaps)
    report={'word_files':len(files),'total_records':total,'newly_changed_records':len({x['disease_id'] for x in changes}),
      'newly_filled_fields':dict(fieldcounts),'newly_filled_fields_total':sum(fieldcounts.values()),'changed_word_files':changedfiles,
      'records_with_all_four_fields':complete,'records_still_missing_fields':len(gaps),
      'matched_NLM_sources':len(candidates),'drafted_source_rows':len(json.loads((WORK/'drafts.json').read_text('utf-8'))['drafts']),
      'source_rows_approved_after_scope_check':sum(r.get('scope_match_approved',False) for r in candidates.values()),
      'source_rows_with_second_editorial_check':len(drafts),'unresolved_review_rejections':state.get('rejected',{}),
      'protected_fields_sha256':protected_before.hexdigest(),'protected_fields_unchanged':True,
      'all_record_values_verified_after_save':True,'database_modified':False,'clinical_validation':False,'visual_render_verified':False}
    (OUTPUT/'Bao-cao-ra-soat-lan-3.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    (OUTPUT/'Thay-doi-va-nguon-lan-3.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),'utf-8')
    (OUTPUT/'DOC-TRUOC.txt').write_text('BỘ DỮ LIỆU WORD RÀ SOÁT LẦN 3\n\n'
      'Kế thừa bộ lần 2, bổ sung những trường còn thiếu có nguồn MedlinePlus/NLM khớp tên hoặc từ đồng nghĩa bệnh di truyền được nguồn công bố.\n'
      'Source: MedlinePlus, National Library of Medicine. Nguồn và thay đổi được ghi cạnh bảng và trong JSON. Các bản diễn giải tiếng Việt có hỗ trợ AI, không phải bản dịch chính thức của NLM.\n'
      'Nội dung qua hai lượt xử lý có đối chiếu nguồn bằng AI, chưa được thẩm định lâm sàng. Không dùng để tự chẩn đoán hoặc tự điều trị.\n'
      'Mỗi file tối đa 50 bản ghi, đủ 14 trường. Chỉ điền các trường nội dung còn trống hoặc báo đang bổ sung. Mã, tên, từ khóa, trạng thái và các trường quản lý được giữ nguyên.\n'
      'Không phải toàn bộ dữ liệu đã hoàn chỉnh. Xem CSV còn thiếu và báo cáo lần 3. Không cập nhật CSDL hoặc web.\n'
      'Đã kiểm tra cấu trúc và nội dung sau lưu; chưa kiểm tra render vì môi trường thiếu LibreOffice.\n','utf-8')
    archive=OUTPUT.with_suffix('.zip')
    with ZipFile(archive,'w',ZIP_DEFLATED) as z:
        for p in sorted(OUTPUT.iterdir()):z.write(p,OUTPUT.name+'/'+p.name)
    with ZipFile(archive) as z:assert z.testzip() is None
    print(json.dumps({**report,'zip':str(archive)},ensure_ascii=True,indent=2))
if __name__=='__main__':main()

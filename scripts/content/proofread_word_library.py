"""Correct individually checked old translation errors in fresh Word copies."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
import hashlib
import json
from pathlib import Path
import shutil
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as ET
from scripts.content.apply_word_content import NS,W,celltext,tablefields,paragraph

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'storage/exports/tbldiseases-50-ban-ghi-ra-soat-lan-3'
OUTPUT=ROOT/'storage/exports/tbldiseases-50-ban-ghi-ra-soat-lan-4'
MDS_SUMMARY='Nhóm rối loạn tạo máu đơn dòng, đặc trưng bởi tình trạng loạn sản và quá trình tạo máu không hiệu quả ở một hoặc nhiều dòng tế bào tạo máu.'
MDS_DETAILS='Các rối loạn tạo máu đơn dòng có tình trạng loạn sản và tạo máu không hiệu quả ở một hoặc nhiều dòng tế bào. Có thể tăng nguyên bào tủy; trong mô tả của đoạn nguồn, tỉ lệ nguyên bào tủy trong máu và tủy xương dưới 20%.'
GAMMA_SUMMARY='Rối loạn đơn dòng đặc trưng bởi sự tiết ra chuỗi gamma không hoàn chỉnh.'
GAMMA_DETAILS='Bệnh chuỗi nặng gamma là một rối loạn đơn dòng, đặc trưng bởi sự tiết ra chuỗi gamma không hoàn chỉnh. Phần lớn trường hợp có biến đổi hình thái tương tự u lympho lympho bào–tương bào, nhưng diễn biến lâm sàng thường ác tính hơn so với u lympho lympho bào–tương bào hoặc bệnh đại globulin máu Waldenström.'
EDITS={
 '1274':{'summary':'Tình trạng tăng sinh tân sinh đơn dòng của các tế bào mast, tích tụ ở một hoặc nhiều cơ quan.'},
 '1289':{'summary':MDS_SUMMARY,'details':MDS_DETAILS},
 '1301':{'summary':'Nhóm rối loạn tạo máu đơn dòng có đồng thời đặc điểm loạn sản tủy và tăng sinh tủy.',
         'details':'Các rối loạn tạo máu đơn dòng trong nhóm này có đồng thời đặc điểm loạn sản tủy và tăng sinh tủy tại thời điểm biểu hiện ban đầu.'},
 '1317':{'summary':'Bệnh bạch cầu cấp dòng tủy đặc trưng bởi sự tăng sinh đơn dòng của nguyên bào dòng tủy trong máu ngoại vi và tủy xương.',
         'details':'Bệnh đặc trưng bởi sự tăng sinh đơn dòng của nguyên bào dòng tủy trong máu ngoại vi và tủy xương. Biểu hiện lâm sàng gồm sốt, da xanh xao, thiếu máu, xuất huyết và nhiễm trùng tái phát.'},
 '1405':{'summary':GAMMA_SUMMARY,'details':GAMMA_DETAILS},
 '1431':{'summary':'Một tân sinh ở trẻ em với sự tăng sinh đơn dòng của tế bào T nhiễm EBV, mang kiểu hình gây độc tế bào đã hoạt hóa.'},
 '8722':{'summary':'Rối loạn đơn dòng của quá trình sừng hóa, biểu hiện bằng một hoặc nhiều mảng teo có bờ tăng sừng nổi gờ.',
         'details':'Bệnh liên quan đến rối loạn đơn dòng của quá trình sừng hóa, đặc trưng bởi một hoặc nhiều mảng teo được bao quanh bởi bờ tăng sừng có hình ảnh đặc trưng trên lâm sàng và mô học. Nguồn ghi nhận nhiều biến thể lâm sàng.'},
 '9232':{'details':'Sự tăng sinh có thể có hoặc không có tính đơn dòng; tiên lượng của bệnh khó dự đoán.'},
 '9736':{'details':'Nang có thể liên quan đến sự phát triển của vạt da, tắc ống tuyến Bartholin do chất nhầy hoặc nhiễm trùng. Đặc trưng là sự tích tụ chất nhầy hoặc dịch trong suốt bên trong một cấu trúc dạng túi kín, hình thành ở tuyến Bartholin hoặc ống dẫn của tuyến. Nang thường không gây triệu chứng, nhưng có thể đau khi to lên hoặc nhiễm trùng.'},
 '19084':{'summary':'Các cơn co giật kèm sủi bọt miệng và cứng các chi ở trẻ nhũ nhi.',
          'details':'Đây là mục mô tả trong các hệ thống y học truyền thống AYU, SID và UNA. Biểu hiện được nêu trong nguồn gồm các cơn co giật, sủi bọt miệng và cứng các chi ở trẻ nhũ nhi.'},
 '26173':{'summary':MDS_SUMMARY,'details':MDS_DETAILS},
 '26418':{'summary':GAMMA_SUMMARY,'details':GAMMA_DETAILS},
 '26435':{'details':'Bệnh bạch cầu tương bào là một tân sinh tương bào có diễn biến ác tính, đặc trưng bởi sự hiện diện của tương bào tân sinh trong máu ngoại vi.'},
 '28809':{'summary':'Bộ phận dạng thanh gắn ở phía bên, có chức năng đỡ hoặc bảo vệ.',
          'details':'Thanh đỡ hoặc thanh bảo vệ được gắn vào phía bên của một vật hoặc thiết bị.'},
}

def main():
    rows={r['fields']['disease_id']:r for r in map(json.loads,(ROOT/'storage/temporary/word-content-20261019/records.jsonl').open(encoding='utf-8'))}
    OUTPUT.mkdir(exist_ok=False);changes=[];count=0;changedfiles=0
    for path in sorted(SOURCE.iterdir()):
        if path.name.startswith('~$'):continue
        target=OUTPUT/path.name
        if path.suffix!='.docx':shutil.copy2(path,target);continue
        with ZipFile(path) as z:root=ET.fromstring(z.read('word/document.xml'))
        expected=[];changed=False
        for table in root.findall('w:body/w:tbl',NS):
            cells=tablefields(table);before={k:celltext(v) for k,v in cells.items()};after=before.copy();rid=before['disease_id'];count+=1
            for field,value in EDITS.get(rid,{}).items():
                if value==before[field]:continue
                source=rows[rid];assert source['source'] and before['slug']==source['fields']['slug']
                full=' '.join((source['source_title']+'\n'+'\n'.join(source['source']['definitions'])).split())
                cell=cells[field]
                for node in list(cell):
                    if node.tag!='{'+W+'}tcPr':cell.remove(node)
                cell.append(paragraph(value));after[field]=value;changed=True
                changes.append({'disease_id':rid,'name':before['name'],'field':field,'previous':before[field],'text':value,
                  'source_title':source['source_title'],'source_url':source['source_url'],
                  'source_normalized_sha256':hashlib.sha256(full.encode()).hexdigest(),
                  'evidence_offsets_in_normalized_source':[{'start':0,'end':len(full)}],
                  'method':'AI editorial comparison with the supplied English definition','clinical_validation':False})
            assert all(before[k]==after[k] for k in before if k not in EDITS.get(rid,{}))
            expected.append(after)
        if changed:
            changedfiles+=1
            with ZipFile(path) as src,ZipFile(target,'w',ZIP_DEFLATED) as dst:
                for info in src.infolist():dst.writestr(info,ET.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True) if info.filename=='word/document.xml' else src.read(info.filename))
        else:shutil.copy2(path,target)
        with ZipFile(target) as z:check=ET.fromstring(z.read('word/document.xml'))
        actual=[{k:celltext(v) for k,v in tablefields(t).items()} for t in check.findall('w:body/w:tbl',NS)]
        assert actual==expected,path.name
    assert count==37236
    assert {(x['disease_id'],x['field']) for x in changes}=={(rid,k) for rid,d in EDITS.items() for k in d}
    report={'word_files':745,'records':count,'corrected_records':len(EDITS),'corrected_fields':len(changes),'changed_files':changedfiles,
      'all_14_fields_preserved':True,'database_modified':False,'clinical_validation':False,'visual_render_verified':False,
      'notes':['Corrected clonal terminology, malformed text, and infant-age wording.',
               'Traditional-system descriptions are identified as such rather than translated as modern biological causes.',
               'The old source numeric threshold for plasma cell leukaemia was not retained as a general current diagnostic rule.']}
    (OUTPUT/'Bao-cao-hieu-dinh-lan-4.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    (OUTPUT/'Thay-doi-hieu-dinh-lan-4.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),'utf-8')
    with (OUTPUT/'DOC-TRUOC.txt').open('a',encoding='utf-8') as f:
        f.write('\nHIỆU ĐÍNH LẦN 4\nĐã rà lại cấu trúc toàn bộ thư viện và hiệu đính '+str(len(changes))+' trường ở '+str(len(EDITS))+' mục theo đoạn nguồn. Xem báo cáo hiệu đính và thay đổi lần 4. Đây vẫn là bản tham khảo chưa được thẩm định lâm sàng.\n')
    with ZipFile(OUTPUT.with_suffix('.zip'),'w',ZIP_DEFLATED) as z:
        for p in sorted(OUTPUT.iterdir()):z.write(p,OUTPUT.name+'/'+p.name)
    print(json.dumps(report,ensure_ascii=True,indent=2))
if __name__=='__main__':main()

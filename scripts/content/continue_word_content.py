"""Continue the Word-only editorial pass without changing the database.

Uses individually checked corrections and short, attributed WHO summaries.
Never treats a classification label as a complete medical article.
"""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

from lxml import etree as ET
from scripts.content.apply_word_content import NS, W, FIELDS, PLACEHOLDERS, celltext, tablefields, paragraph

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'storage/exports/tbldiseases-50-ban-ghi-bo-sung-noi-dung'
OUTPUT = ROOT/'storage/exports/tbldiseases-50-ban-ghi-ra-soat-lan-2'
WORK = ROOT/'storage/temporary/word-content-20261019'


def patches():
    rows = {r['fields']['disease_id']: r for r in map(json.loads, (WORK/'records.jsonl').open(encoding='utf-8'))}
    rejected = json.loads((SOURCE/'Ban-thao-bi-loai-can-doi-chieu.json').read_text('utf-8'))
    result = {}
    # Individually compared against the supplied English definitions. These
    # are draft translations, not a claim of clinician review.
    accepted = [0,1,3,6,7,8,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,
                26,27,28,29,30,31,32,33,34,35,36,40,41,43,44,45,46,47,48,
                50,51,52,53,54]
    replacements = {
      0:'Tài liệu nguồn nhấn mạnh cần điều trị kịp thời tình trạng viêm dây thần kinh vì chậm điều trị có thể gây tổn thương thần kinh vận động vĩnh viễn.',
      1:'Ổ nhiễm trùng hóa mủ ở nhu mô não hoặc khoang ngoài màng cứng, dưới màng cứng trong sọ hay ống sống; nhu mô tủy sống ít bị ảnh hưởng hơn.',
      3:'U lympho tế bào T trưởng thành biểu hiện ở da bằng dát hoặc mảng; biểu hiện dạng khối u hoặc đỏ da toàn thân ít gặp hơn.',
      6:'Tài liệu nguồn ghi nhận bổ sung sắt trong thai kỳ có lợi và nhấn mạnh phát hiện sớm, điều trị, theo dõi lâm sàng để tránh biến chứng của thiếu máu.',
      8:'Có thể xuất hiện thứ phát sau các rối loạn khác hoặc liên quan đến phản ứng tự miễn hướng vào tủy xương.',
      10:'Viêm cơ thể vùi là bệnh cơ viêm vô căn thường gặp nhất ở người trên 50 tuổi.',
      11:'Viêm cân mạc tăng bạch cầu ái toan lan tỏa, còn gọi là bệnh Shulman, là rối loạn vô căn hiếm gặp với da cứng và dấu hiệu vỏ cam, thường tiến triển nhanh.',
      12:'Nguồn ghi nhận triệu chứng thường cải thiện ngay khi dừng vận động. Nếu tiếp tục vận động, bệnh có thể tiến triển đến phù thanh quản, hạ huyết áp và trụy tim mạch.',
      13:'Hạn chế lượng dịch đưa vào là biện pháp điều trị được nêu trong tài liệu nguồn; việc lựa chọn điều trị còn phụ thuộc bệnh nền và các rối loạn đi kèm.',
      14:'Phẫu thuật tuyến yên qua xoang bướm là phương pháp điều trị chủ đạo được nêu trong nguồn và đòi hỏi chuyên môn, kinh nghiệm phẫu thuật thần kinh.',
      15:'Nguồn ghi nhận quáng gà do thiếu vitamin A đáp ứng nhanh với liệu pháp vitamin A, thường trong vòng 48 giờ.',
      16:'Khi được điều trị, khô kết mạc đang hoạt động và vệt Bitot có thể bắt đầu giảm trong 2–5 ngày. Một số tổn thương vẫn có thể tồn tại nhiều tháng.',
      17:'Nguồn ghi nhận khô giác mạc đáp ứng với liệu pháp vitamin A trong 2–5 ngày, giác mạc có thể trở lại hình thái bình thường sau 1–2 tuần.',
      19:'Chế độ ăn hạn chế phenylalanine là biện pháp điều trị được nêu trong nguồn, giúp người bệnh có cuộc sống gần bình thường.',
      20:'Đây là một rối loạn chuyển hóa axit amin bẩm sinh, thuộc thể nặng của bệnh phenylketon niệu.',
      21:'Đây là một rối loạn chuyển hóa axit amin bẩm sinh, thuộc thể nhẹ của bệnh phenylketon niệu.',
      23:'Nguồn nhấn mạnh phải loại bỏ lactose khỏi chế độ ăn vì bệnh có thể gây tiêu chảy nhiều, suy dinh dưỡng nặng và tử vong nếu tiếp tục dùng lactose.',
      24:'Bệnh đáp ứng nhanh với bổ sung kẽm và tài liệu nguồn nêu cần duy trì bổ sung suốt đời.',
      26:'Loạn trương lực cơ xuất hiện như một phần của bệnh thoái hóa có tính di truyền phức tạp hơn.',
      27:'Loạn trương lực cơ là một phần của bệnh thoái hóa có tính di truyền, không phải biểu hiện đơn thuần. Có thể kèm thất điều, dấu hiệu tổn thương bó tháp và rối loạn nhận thức.',
      29:'Một số thuốc có thể làm nặng tình trạng nhược cơ; tài liệu nguồn nhấn mạnh cần thận trọng khi sử dụng các thuốc có liên quan.',
      31:'Tài liệu nguồn ghi nhận hội chứng Reye ít gặp hơn kể từ khi aspirin không còn được khuyến cáo dùng thường quy ở trẻ em.',
      32:'Theo đoạn nguồn còn được đánh dấu là bản thảo, tình trạng này có thể liên quan đến nhiễm trùng, bệnh tự miễn hoặc bệnh ác tính.',
      33:'Đoạn nguồn còn ở dạng bản thảo nêu các nguyên nhân có thể gồm nhiễm trùng, bệnh tự miễn hoặc bệnh ác tính.',
      34:'Người bệnh có tắc nghẽn đường thở gây triệu chứng có thể cần phẫu thuật tạo hình khí quản, theo tài liệu nguồn.',
      35:'Nguồn ghi nhận tiên lượng cải thiện khi điều trị dài hạn bằng kháng sinh nhóm macrolide; tác dụng được cho là liên quan đến hoạt tính chống viêm và điều hòa miễn dịch.',
      36:'Phần lớn trường hợp cần điều trị nội khoa thích hợp hoặc phẫu thuật cắt ruột thừa viêm. Chậm điều trị làm tăng nguy cơ vỡ ruột thừa, viêm phúc mạc và sốc.',
      40:'Ly thượng bì bọng nước là nhóm bệnh gây bọng nước không đồng nhất, phần lớn do bất thường di truyền của các protein cấu trúc ở biểu bì và vùng nối biểu bì–hạ bì. Cần phân biệt các thể di truyền với ly thượng bì bọng nước mắc phải thuộc nhóm bệnh bọng nước qua cơ chế miễn dịch.',
      43:'Bệnh khớp phản ứng là tình trạng viêm khớp thứ phát được tài liệu nguồn mô tả là có thể liên quan đến nhiễm trùng ở vị trí khác, bệnh tự miễn hoặc sau tiêm chủng.',
      44:'Tài liệu nguồn mô tả viêm khớp xuất hiện thứ phát sau nhiễm trùng, trong bệnh tự miễn hoặc sau tiêm chủng. Các vị trí nhiễm trùng trước đó thường thuộc hệ tiêu hóa hoặc tiết niệu–sinh dục.',
      45:'Các yếu tố được nêu trong tài liệu nguồn gồm nhiễm trùng ở nơi khác, bệnh tự miễn hoặc tình trạng sau tiêm chủng; đây không phải khẳng định nguyên nhân cho từng người bệnh.',
      47:'Bệnh da chủ yếu xuất hiện ở người mang thai lần đầu hoặc đa thai, đặc trưng bởi các sẩn và mảng đỏ dạng mày đay, rất ngứa, ở trong và quanh vết rạn da bụng.',
      50:'Nguồn ghi nhận bệnh xuất huyết do thiếu vitamin K ở trẻ sơ sinh liên quan đến việc trẻ không được bổ sung vitamin K ngay sau sinh.',
      51:'Bất thường phát triển hệ bạch huyết tại vùng nối bạch huyết–tĩnh mạch, thường ở phía sau cổ; có thể liên quan đến bất thường nhiễm sắc thể, hội chứng dị tật hoặc tác nhân gây quái thai.',
      52:'Ngón tay dùi trống bẩm sinh đơn thuần là bệnh da di truyền hiếm gặp, với đầu ngón tay hoặc ngón chân to lên và móng dày, không kèm bất thường khác.',
      53:'Bệnh biểu hiện bằng phì đại phần tận cùng của ngón tay và ngón chân, kèm móng dày. Trong thể bẩm sinh đơn thuần được mô tả ở nguồn, không có bất thường khác đi kèm.',
    }
    for index in accepted:
        item = rejected[index]
        row = rows[item['disease_id']]
        assert row['source'] and row['source']['definitions']
        result.setdefault(item['disease_id'], {})[item['field']] = {
            'text': replacements.get(index, item['draft']),
            'source_url':row['source_url'], 'source_title':row['source_title'],
            'evidence':row['source']['definitions'],
            'method':'individual_comparison_with_supplied_definition',
            'clinical_validation':False,
        }
    # Original short paraphrases: each WHO page contributes under 200 words.
    # Match only the named general disease, never its children or subtypes.
    who = [
      ('185','Cholera','cholera',
       'Bệnh tả là nhiễm khuẩn đường ruột gây tiêu chảy cấp do ăn hoặc uống thực phẩm, nước chứa Vibrio cholerae.',
       'Đa số trường hợp nhẹ hoặc vừa; một số diễn tiến nhanh thành tiêu chảy nhiều và mất nước đe dọa tính mạng.',
       'Thiếu nước sạch, vệ sinh môi trường và vệ sinh cá nhân làm tăng nguy cơ lây truyền.',
       'Dùng nước sạch, rửa tay và bảo đảm an toàn thực phẩm; vắc xin tả uống hỗ trợ phòng bệnh. Khi có tiêu chảy cần bù nước kịp thời và tiếp cận điều trị, đặc biệt khi mất nước nặng.'),
      ('882','Measles','measles',
       'Sởi là bệnh do vi rút, lây rất mạnh qua đường hô hấp.',
       'Bệnh có thể gây sốt cao, ho, chảy mũi, phát ban và biến chứng như viêm phổi hoặc viêm não.',
       'Người chưa có miễn dịch dễ mắc bệnh. Trẻ chưa tiêm đủ, người suy dinh dưỡng hoặc suy giảm miễn dịch có nguy cơ biến chứng cao hơn.',
       'Tiêm đủ hai liều vắc xin sởi theo lịch phù hợp. Chăm sóc tập trung vào giảm triệu chứng, bù dịch và phòng biến chứng; dùng vitamin A cho trẻ theo chỉ định của nhân viên y tế.'),
      ('649','Rabies','rabies',
       'Dại là bệnh do vi rút lây từ động vật, gây tổn thương hệ thần kinh trung ương.',
       'Vi rút truyền qua nước bọt khi bị cắn, cào hoặc khi nước bọt tiếp xúc niêm mạc, vết thương. Khi đã có triệu chứng lâm sàng, bệnh hầu như luôn gây tử vong.',
       'Bị động vật có khả năng mắc dại cắn, cào hoặc để nước bọt tiếp xúc với niêm mạc, da tổn thương là tình huống phơi nhiễm.',
       'Tiêm phòng cho chó và phòng tránh bị cắn. Sau phơi nhiễm, rửa kỹ bằng xà phòng và nước ít nhất 15 phút rồi đến cơ sở y tế ngay để đánh giá tiêm vắc xin và dự phòng bổ sung khi cần.'),
      ('731','Dengue','dengue-and-severe-dengue',
       'Dengue là bệnh nhiễm vi rút truyền qua muỗi, có thể không triệu chứng hoặc tiến triển nặng.',
       'Bệnh có thể gây sốt, đau đầu, đau cơ khớp, buồn nôn và phát ban. Đau bụng nhiều, nôn kéo dài hoặc chảy máu là dấu hiệu cần khám ngay.',
       'Bệnh phổ biến ở vùng nhiệt đới, cận nhiệt đới. Người nhiễm Dengue lần thứ hai có nguy cơ bệnh nặng cao hơn.',
       'Phòng muỗi đốt, nhất là ban ngày, và kiểm soát nơi muỗi sinh sản. Tránh aspirin và ibuprofen vì có thể tăng nguy cơ chảy máu; cần chăm sóc y tế ngay khi có dấu hiệu nặng.'),
      ('199','Typhoid fever','typhoid',
       'Thương hàn là bệnh nhiễm khuẩn Salmonella Typhi, thường lây qua thức ăn hoặc nước nhiễm bẩn.',
       'Bệnh có thể gây sốt kéo dài, mệt, đau đầu, đau bụng, táo bón hoặc tiêu chảy. Người hết triệu chứng vẫn có thể tiếp tục thải vi khuẩn.',
       'Thiếu nước sạch, điều kiện vệ sinh kém và sống hoặc đi đến vùng lưu hành làm tăng nguy cơ.',
       'Bảo đảm nước sạch, an toàn thực phẩm, rửa tay và tiêm chủng theo chỉ định. Người đang điều trị cần dùng kháng sinh đủ thời gian được kê, tránh chế biến thức ăn cho người khác và tái kiểm tra theo hướng dẫn.'),
      ('371','Leprosy','leprosy',
       'Phong là bệnh nhiễm khuẩn mạn tính, chủ yếu ảnh hưởng da và dây thần kinh ngoại biên.',
       'Tổn thương da có thể mất cảm giác; nếu không điều trị, bệnh có thể gây khuyết tật vĩnh viễn. Bệnh có thể chữa bằng đa hóa trị liệu.',
       'Lây truyền liên quan đến tiếp xúc gần và kéo dài với người bệnh chưa điều trị; tiếp xúc thông thường như bắt tay không làm lây bệnh.',
       'Phát hiện và điều trị sớm giúp phòng khuyết tật. Người tiếp xúc cần được sàng lọc; dự phòng sau phơi nhiễm do chương trình y tế đánh giá và triển khai.'),
      ('744','Yellow fever','yellow-fever',
       'Sốt vàng là bệnh do vi rút truyền qua muỗi, có thể phòng bằng vắc xin.',
       'Bệnh có thể khởi đầu bằng sốt, đau đầu, đau người, buồn nôn. Thể nặng gây vàng da, xuất huyết, suy cơ quan hoặc sốc.',
       'Phơi nhiễm muỗi mang vi rút ở vùng có nguy cơ tại châu Phi và châu Mỹ làm tăng nguy cơ mắc bệnh.',
       'Tiêm vắc xin là biện pháp phòng bệnh chủ yếu; cần đánh giá tính phù hợp khi có thai, suy giảm miễn dịch hoặc yếu tố chống chỉ định. Mặc quần áo che phủ, dùng chất xua muỗi và loại bỏ nước đọng.'),
      ('580','Trachoma','trachoma',
       'Mắt hột là bệnh mắt do Chlamydia trachomatis gây ra, có thể dẫn đến mất thị lực.',
       'Nhiễm trùng tái diễn có thể làm mi quặm, khiến lông mi cọ vào giác mạc, gây đau và tổn thương lâu dài.',
       'Vệ sinh kém, nhà ở đông người và thiếu nước sạch, công trình vệ sinh thuận lợi cho lây truyền.',
       'Kiểm soát bệnh dựa vào chiến lược SAFE: phẫu thuật khi có lông quặm do mắt hột, kháng sinh theo chương trình điều trị, giữ sạch mặt và cải thiện nước sạch, vệ sinh môi trường.'),
    ]
    for record_id, title, page, *texts in who:
        assert rows[record_id]['source_title'] == title
        url='https://www.who.int/news-room/fact-sheets/detail/'+page
        if record_id=='580':url='https://www.who.int/en/news-room/fact-sheets/detail/trachoma'
        if record_id=='744':pass
        assert sum(len(t.split()) for t in texts)<200
        for field,text in zip(FIELDS,texts):
            result.setdefault(record_id,{})[field]={'text':text,'source_url':url,
              'source_title':'WHO fact sheet: '+title,'method':'short_attributed_paraphrase_of_official_fact_sheet',
              'accessed_at':'2026-10-19','clinical_validation':False}
    return result


def main():
    edits=patches()
    OUTPUT.mkdir(exist_ok=False)
    changes=[]; missing=[]; complete=0; count=0; applied=set(); byfield=Counter()
    files=sorted(p for p in SOURCE.glob('*.docx') if not p.name.startswith('~$'))
    assert len(files)==745
    for path in files:
        with ZipFile(path) as z:
            root=ET.fromstring(z.read('word/document.xml'))
        body=root.find('w:body',NS)
        tables=body.findall('w:tbl',NS)
        expected=[]; filechanged=False
        assert 0<len(tables)<=50
        for table in tables:
            cells=tablefields(table)
            before={k:celltext(v) for k,v in cells.items()}
            after=before.copy(); rid=before['disease_id']; count+=1
            notes=set()
            for key,patch in edits.get(rid,{}).items():
                if before[key].strip() not in PLACEHOLDERS:continue
                text=patch['text']; assert text and text.strip() not in PLACEHOLDERS
                cell=cells[key]
                for child in list(cell):
                    if child.tag!='{'+W+'}tcPr':cell.remove(child)
                cell.append(paragraph(text))
                after[key]=text; byfield[key]+=1; applied.add((rid,key));filechanged=True
                changes.append({'disease_id':rid,'name':before['name'],'field':key,'previous':before[key],**patch})
                notes.add(patch['source_url'] or patch['source_title'])
            if notes:
                pos=body.index(table)+1
                body.insert(pos,paragraph('Nguồn bổ sung lần 2: '+'; '.join(sorted(notes)),size=17))
            assert all(before[k]==after[k] for k in before if k not in FIELDS)
            expected.append(after)
            absent=[k for k in FIELDS if after[k].strip() in PLACEHOLDERS]
            if absent:
                missing.append({'disease_id':rid,'name':before['name'],'file':path.name,
                  'missing_fields':'; '.join(absent),'reason':'Chưa có nội dung riêng đủ căn cứ cho các trường được liệt kê; không tự điền bằng suy đoán.'})
            else:complete+=1
        target=OUTPUT/path.name
        if filechanged:
            with ZipFile(path) as src, ZipFile(target,'w',ZIP_DEFLATED) as dst:
                for info in src.infolist():
                    data=ET.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True) if info.filename=='word/document.xml' else src.read(info.filename)
                    dst.writestr(info,data)
        else:shutil.copy2(path,target)
        with ZipFile(target) as z:check=ET.fromstring(z.read('word/document.xml'))
        actual=[{k:celltext(v) for k,v in tablefields(t).items()} for t in check.findall('w:body/w:tbl',NS)]
        assert actual==expected, path.name
    assert count==37236
    # Preserve earlier source traceability, and label it as the preceding pass.
    shutil.copy2(SOURCE/'Nguon-va-dan-chung.json',OUTPUT/'Nguon-va-dan-chung-lan-1.json')
    shutil.copy2(SOURCE/'Bao-cao-bo-sung-noi-dung.json',OUTPUT/'Bao-cao-bo-sung-lan-1.json')
    report={'word_files':len(files),'total_records':count,'newly_changed_records':len({x['disease_id'] for x in changes}),
      'newly_filled_fields':dict(byfield),'records_with_all_four_fields':complete,
      'records_still_missing_fields':len(missing),'protected_fields_unchanged':True,
      'all_record_values_verified_after_save':True,'database_modified':False,'clinical_validation':False,
      'visual_render_verified':False,'remaining_rejected_fields':len(json.loads((SOURCE/'Ban-thao-bi-loai-can-doi-chieu.json').read_text('utf-8')))-sum(1 for x in changes if x['method']=='individual_comparison_with_supplied_definition')}
    (OUTPUT/'Bao-cao-ra-soat-lan-2.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    (OUTPUT/'Thay-doi-va-nguon-lan-2.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),'utf-8')
    rejected=json.loads((SOURCE/'Ban-thao-bi-loai-can-doi-chieu.json').read_text('utf-8'))
    unresolved=[x for x in rejected if (x['disease_id'],x['field']) not in applied]
    (OUTPUT/'Ban-thao-van-can-doi-chieu.json').write_text(json.dumps(unresolved,ensure_ascii=False,indent=2),'utf-8')
    with (OUTPUT/'Cac-muc-con-thieu-noi-dung.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['disease_id','name','file','missing_fields','reason']);writer.writeheader();writer.writerows(missing)
    (OUTPUT/'DOC-TRUOC.txt').write_text('BỘ DỮ LIỆU WORD RÀ SOÁT LẦN 2\n\n'
      'Bộ này kế thừa toàn bộ nội dung lần trước và bổ sung các trường có nguồn được đối chiếu riêng. Mỗi file tối đa 50 bản ghi, giữ nguyên 14 trường.\n'
      'Đây là nội dung tham khảo được biên soạn với hỗ trợ AI, chưa được thẩm định lâm sàng. Không có cập nhật CSDL hoặc web.\n'
      'Không phải toàn bộ bản ghi đã hoàn chỉnh. Xem báo cáo và CSV để biết các mục còn thiếu. Mục giải phẫu, hoạt chất, thiết bị và phân loại không được tự coi là bệnh.\n'
      'Nguồn được ghi cạnh bảng và trong JSON thay đổi. Nội dung đã có được giữ nguyên; chỉ điền các trường đang trống hoặc thông báo đang bổ sung.\n'
      'Đã kiểm tra cấu trúc, số lượng và nội dung sau lưu; chưa kiểm tra được bản render vì môi trường thiếu LibreOffice.\n','utf-8')
    archive=OUTPUT.with_suffix('.zip')
    with ZipFile(archive,'w',ZIP_DEFLATED) as z:
        for p in sorted(OUTPUT.iterdir()):z.write(p,OUTPUT.name+'/'+p.name)
    print(json.dumps({**report,'zip':str(archive)},ensure_ascii=False,indent=2))


if __name__=='__main__':main()

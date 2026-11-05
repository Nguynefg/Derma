"""Last editorial/source checks before a Word-only write; no clinical sign-off."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
import json
from pathlib import Path
import re
import unicodedata
FIELDS=['summary','details','risk_factors','prevention']

def save(path,value):
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),'utf-8')
    temp.replace(path)

WORK=Path(__file__).resolve().parents[2]/'storage/temporary/word-content-20261019/medlineplus'
VI=set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ')

def main():
    path=WORK/'reviewed-drafts.json';state=json.loads(path.read_text('utf-8'))
    candidates={r['fields']['disease_id']:r for r in map(json.loads,(WORK/'candidates.jsonl').open(encoding='utf-8'))}
    # Individually checked terminology and scope corrections. These are still
    # AI editorial work, not a clinician's approval.
    corrections={
      ('151','prevention'):('Hiện chưa có vắc xin phòng bệnh tăng bạch cầu đơn nhân nhiễm trùng. Để giảm lây truyền, không dùng chung đồ ăn, thức uống hoặc vật dụng tiếp xúc với miệng; tránh hôn khi một trong hai người mắc bệnh và rửa tay thường xuyên bằng xà phòng, nước.',None),
      ('212','prevention'):('Thực hiện cẩn thận việc đóng hộp thực phẩm tại nhà; không cho trẻ nhũ nhi dùng mật ong. Vết thương nhiễm trùng cần được chăm sóc y tế kịp thời.',None),
      ('231','risk_factors'):('Có thể nhiễm ký sinh trùng khi nuốt phải thức ăn hoặc nước nhiễm bẩn, kể cả nước khi bơi. Tiếp xúc bề mặt nhiễm bẩn rồi đưa tay lên mắt, mũi, miệng hoặc tiếp xúc tình dục cũng có thể làm lây bệnh.',None),
      ('231','prevention'):('Rửa tay bằng xà phòng và nước; chỉ uống nước an toàn, dùng sữa và nước táo đã thanh trùng. Tránh thức ăn sống khi đi đến nơi có nguồn thực phẩm không an toàn; không bơi khi bị tiêu chảy hoặc nuốt nước khi bơi. Dùng bao cao su hoặc màng chắn miệng khi quan hệ tình dục.',None),
      ('257','prevention'):('Dùng bao cao su làm từ cao su tự nhiên đúng cách giúp giảm đáng kể nhưng không loại bỏ hoàn toàn nguy cơ lây giang mai. Người dị ứng cao su có thể dùng loại polyurethane. Không quan hệ tình dục qua đường hậu môn, âm đạo hoặc miệng là cách tránh lây nhiễm đáng tin cậy nhất được nguồn nêu.',None),
      ('321','prevention'):('Dùng bao cao su làm từ cao su tự nhiên đúng cách giúp giảm nhưng không loại bỏ hoàn toàn nguy cơ lây bệnh. Người dị ứng cao su có thể dùng loại polyurethane. Không quan hệ tình dục qua đường hậu môn, âm đạo hoặc miệng là cách tránh lây nhiễm đáng tin cậy nhất được nguồn nêu.',None),
      ('815','prevention'):('Vắc xin JYNNEOS có thể giúp phòng bệnh đậu mùa khỉ (mpox). Tránh tiếp xúc gần với vùng da có ban và tránh chạm vào vật dụng người mắc bệnh đã sử dụng.',None),
      ('1056','risk_factors'):('Có thể nhiễm bệnh từ phân mèo mang ký sinh trùng, thịt nhiễm bẩn còn sống hoặc chưa chín kỹ, dụng cụ đã tiếp xúc với thịt sống nhiễm bẩn, nước nhiễm bẩn, hoặc qua truyền máu hay ghép tạng nhiễm tác nhân gây bệnh.',None),
      ('1463','risk_factors'):('Phần lớn người có bệnh khởi phát ở tuổi trưởng thành đang hút thuốc hoặc có tiền sử hút thuốc.',None),
      ('1194','summary'):('Nhiễm trùng huyết (sepsis) là phản ứng quá mức của cơ thể trước tình trạng nhiễm trùng.',None),
      ('1194','details'):('Đây là tình trạng cấp cứu đe dọa tính mạng. Nếu không được điều trị nhanh chóng, bệnh có thể gây tổn thương mô, suy cơ quan và tử vong.',None),
      ('1194','risk_factors'):('Người từ 65 tuổi, người mắc bệnh mạn tính như đái tháo đường, bệnh phổi, ung thư hoặc bệnh thận, người suy giảm miễn dịch, phụ nữ mang thai và trẻ dưới một tuổi có nguy cơ cao hơn.',None),
      ('1194','prevention'):('Giảm nguy cơ nhiễm trùng bằng cách chăm sóc tốt bệnh mạn tính, tiêm các vắc xin được khuyến nghị, giữ vệ sinh và rửa tay. Vết cắt cần được giữ sạch và che phủ đến khi lành.',None),
      ('2893','risk_factors'):('Bệnh thường gặp ở phụ nữ hơn nam giới và hầu như chỉ gặp ở người trên 50 tuổi.',None),
      ('3050','summary'):('Bệnh nội tiết có thể xuất hiện khi lượng hormone quá cao, quá thấp hoặc cơ thể đáp ứng bất thường với hormone.',[
          'If your hormone levels are too high or too low, you may have a hormone disorder.',
          'Hormone diseases also occur if your body does not respond to hormones the way it is supposed to.']),
      ('3050','prevention'):('Về điều trị và chăm sóc, nguồn nêu việc kiểm soát lượng hormone cơ thể sản xuất. Khi bệnh liên quan đến thiếu hormone, liệu pháp bổ sung hormone có thể có ích.',[
          'They are usually treated by controlling how much hormone your body makes.',
          'Hormone supplements can help if the problem is too little of a hormone.']),
      ('1010','summary'):('Ký sinh trùng sống nhờ sinh vật khác để lấy thức ăn và nơi cư trú. Tác nhân gây bệnh ký sinh trùng có thể là động vật nguyên sinh đơn bào hoặc các loài giun.',[
          'Parasites are living things that use other living things - like your body - for food and a place to live.',
          'Parasites range in size from tiny, one-celled organisms called protozoa to worms that can be seen with the naked eye.']),
      ('5351','risk_factors'):('Bại não có thể liên quan đến biến đổi gen, dị dạng não, nhiễm trùng hoặc sốt ở người mang thai và tổn thương thai đang phát triển. Sinh non và sinh nhẹ cân cũng là các yếu tố nguy cơ được nguồn nêu.',None),
      ('5351','prevention'):('Chăm sóc thai kỳ định kỳ có thể giúp giảm nguy cơ sinh non và sinh nhẹ cân. Dùng ghế an toàn trên ô tô cho trẻ để phòng chấn thương đầu có thể dẫn đến bại não.',[
          'Get regular  prenatal care , which can reduce the risk of preterm birth or having a low birthweight baby.',
          'Use car seats for your baby to prevent head injuries that could cause CP.']),
      ('5853','risk_factors'):('Nguy cơ đục thủy tinh thể tăng theo tuổi. Các yếu tố liên quan gồm đái tháo đường, tiền sử gia đình, chấn thương hoặc phẫu thuật mắt, dùng thuốc steroid, hút thuốc, uống quá nhiều rượu và tiếp xúc nhiều với ánh nắng.',None),
      ('6129','risk_factors'):('Tùy gen liên quan, bệnh có thể có kiểu di truyền theo ty thể, trội trên nhiễm sắc thể thường hoặc lặn trên nhiễm sắc thể thường.',None),
      ('6203','risk_factors'):('Người có họ hàng bậc một mắc cận thị, chẳng hạn anh chị em ruột hoặc con, có nguy cơ cao hơn so với dân số chung.',None),
      ('6204','risk_factors'):('Người có họ hàng bậc một mắc viễn thị, chẳng hạn anh chị em ruột hoặc con, có nguy cơ cao hơn so với dân số chung.',None),
      ('6468','summary'):('Hạ huyết áp tư thế đứng là tình trạng huyết áp giảm khi chuyển từ tư thế nằm sang tư thế đứng.',None),
      ('6748','risk_factors'):('Nguồn gợi ý hội chứng QT ngắn có kiểu di truyền trội trên nhiễm sắc thể thường.',None),
      ('8209','risk_factors'):('Bệnh viêm tụy di truyền có kiểu di truyền trội trên nhiễm sắc thể thường.',[
          'it is inherited in an autosomal dominant pattern']),
      ('12370','details'):('Tổn thương thường có từ lúc sinh hoặc xuất hiện đầu thời thơ ấu. Người bệnh có thể có một hoặc nhiều bớt biểu bì với kích thước khác nhau.',None),
      ('12967','details'):('Biểu hiện thay đổi tùy vùng não bị tổn thương: có thể khó diễn đạt, khó hiểu ngôn ngữ, mất gần hết khả năng ngôn ngữ hoặc khó gọi tên sự vật.',None),
      ('13422','risk_factors'):('Ho mạn tính có thể liên quan đến viêm phế quản mạn, hen, dị ứng, bệnh phổi tắc nghẽn mạn tính, trào ngược dạ dày–thực quản, hút thuốc, bệnh lý ở họng hoặc một số thuốc.',None),
      ('13504','prevention'):('Ăn thêm thực phẩm giàu chất xơ, uống đủ nước, vận động và đi đại tiện khi có nhu cầu có thể giúp phòng táo bón. Chỉ dùng thuốc nhuận tràng khi được nhân viên y tế hướng dẫn; trao đổi về khả năng các thuốc đang dùng gây táo bón.',None),
      ('13557','details'):('Dấu hiệu có thể gồm nôn ra máu đỏ tươi hoặc chất nôn giống bã cà phê; phân đen như hắc ín, phân lẫn máu sẫm màu hoặc máu đỏ tươi.',None),
      ('15960','prevention'):('Trong chăm sóc sau bỏng, nguồn đề cập việc dùng kem kháng sinh để phòng hoặc điều trị nhiễm trùng.',None),
      ('16126','risk_factors'):('Ở ngoài trời lạnh lâu, bị lạnh và ướt hoặc ngâm trong nước lạnh quá lâu có thể gây hạ thân nhiệt. Trẻ nhũ nhi và người cao tuổi đặc biệt dễ bị ảnh hưởng; trẻ có thể bị hạ thân nhiệt khi ngủ trong phòng lạnh.',None),
      ('3439','risk_factors'):('Dữ liệu nguồn gợi ý rằng phần lớn trường hợp có kiểu di truyền lặn trên nhiễm sắc thể thường.',None),
      ('3580','risk_factors'):('Bệnh liên quan đến gen OCRL trên nhiễm sắc thể X. Người nam có thể nhận biến đổi gen từ mẹ mang gen hoặc có biến đổi mới xuất hiện, dù gia đình không có tiền sử bệnh.',None),
      ('5323','risk_factors'):('Bệnh liên quan đến đột biến gen MT-ATP6 trong ADN ty thể. Khi được di truyền, biến đổi ADN ty thể truyền theo dòng mẹ.',None),
      ('8436','risk_factors'):('Có cha hoặc mẹ mắc viêm da cơ địa, hen hoặc viêm mũi dị ứng làm tăng nguy cơ mắc bệnh. Các thể liên quan đến CARD11 hoặc nguy cơ liên quan đến FLG có thể theo kiểu trội trên nhiễm sắc thể thường. Phần lớn trường hợp liên quan đến phối hợp yếu tố di truyền và môi trường.',None),
      ('12448','summary'):('Bất sản sụn (achondrogenesis) là nhóm rối loạn nặng ảnh hưởng đến sự phát triển của sụn và xương. Phần lớn trẻ tử vong trước hoặc ngay sau sinh, thường do suy hô hấp.',None),
      ('12448','details'):('Các thể bệnh đều có đặc điểm tay chân ngắn, lồng ngực hẹp và phổi kém phát triển.',None),
      ('12448','risk_factors'):('Thể 1A và 1B có kiểu di truyền lặn trên nhiễm sắc thể thường. Thể 2 được xem là bệnh có kiểu di truyền trội trên nhiễm sắc thể thường; phần lớn trường hợp liên quan đến biến thể mới ở gen COL2A1.',None),
      ('12568','risk_factors'):('Hội chứng Gorlin có kiểu di truyền trội trên nhiễm sắc thể thường. Phần lớn người bệnh nhận biến đổi gen từ cha hoặc mẹ mắc bệnh; một số trường hợp do biến đổi mới xuất hiện.',None),
      ('12586','risk_factors'):('Bệnh có thể có kiểu di truyền trội trên nhiễm sắc thể thường.',None),
    }
    original=json.loads((WORK/'drafts.json').read_text('utf-8'))['drafts']
    excluded_scope=[rid for rid in state['drafts'] if not candidates[rid].get('scope_match_approved',False)]
    for rid in excluded_scope:del state['drafts'][rid]
    state['excluded_after_context_review']=excluded_scope
    for (rid,field),(text,quotes) in corrections.items():
        if rid not in state['drafts'] or field not in candidates[rid]['missing']:continue
        if quotes is None:
            quotes=state['drafts'][rid][field]['evidence']
            if not quotes:quotes=original[rid][field]['evidence']
        assert quotes and all(' '.join(q.split()) in ' '.join(candidates[rid]['source']['text'].split()) for q in quotes),(rid,field)
        state['drafts'][rid][field]={'text':text,'evidence':quotes}
    state['additional_editorial_corrections']=[{'id':rid,'field':f} for rid,f in corrections if rid in state['drafts'] and f in candidates[rid]['missing']]
    rejected=[]
    for rid,draft in state['drafts'].items():
        source=' '.join(candidates[rid]['source']['text'].split())
        for field in FIELDS:
            data=draft[field];text=data['text'].strip()
            if not text:continue
            text=text.replace('nhà cung cấp dịch vụ y tế','nhân viên y tế').replace('nhà cung cấp','nhân viên y tế')
            data['text']=text
            reason=None
            if not data['evidence'] or any(not q.strip() or ' '.join(q.split()) not in source for q in data['evidence']):
                reason='Final evidence no longer matches the current source'
            if any('LATIN' in unicodedata.name(c,'') and c not in VI and c not in source for c in text):
                reason='Malformed or unexplained Latin characters in Vietnamese draft'
            if field=='risk_factors' and re.fullmatch(r'(?:Kiểu|Mẫu|Mô hình)?\s*di truyền (?:chưa|không) rõ\.?|Pattern unknown\.?|Không di truyền\.?',text,re.I):
                reason='An isolated inheritance label is not a useful cause/risk explanation'
            if field=='risk_factors' and any(q.startswith('Inheritance pattern(s):') for q in data['evidence']):
                reason='Compact inheritance metadata requires the condition-specific explanatory prose'
            if rid=='3832' and field=='risk_factors' and any('Mood disorders can increase' in q for q in data['evidence']):
                reason='Consequence of mood disorders is not a risk factor for developing them'
            if reason:
                rejected.append({'id':rid,'field':field,'text':text,'reason':reason})
                draft[field]={'text':'','evidence':[]}
        assert sum(len(draft[f]['text'].split()) for f in FIELDS)<=200
    state['final_editorial_check']={'clinical_validation':False,'rejected_fields':rejected}
    save(WORK/'reviewed-drafts-before-final-guards.json',json.loads(path.read_text('utf-8')))
    save(path,state)
    print(json.dumps({'reviewed_records':len(state['drafts']),'excluded_fields':len(rejected),'remaining_nonempty_fields':sum(bool(d[f]['text']) for d in state['drafts'].values() for f in FIELDS)},ensure_ascii=True))
if __name__=='__main__':main()

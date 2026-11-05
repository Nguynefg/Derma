"""Resolve source quotation failures against the exact supplied definitions."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'storage/temporary/word-content-20261019'


def main():
    state=json.loads((WORK/'drafts.json').read_text('utf-8'))
    rows={r['fields']['disease_id']:r for r in map(json.loads,(WORK/'records.jsonl').open(encoding='utf-8')) if r['source']}
    translations={
        '537':('Meningococcaemia',{
            'summary':'Tình trạng nhiễm trùng do vi khuẩn gram âm Neisseria meningitidis gây ra, dẫn đến phản ứng viêm toàn thân nghiêm trọng.',
            'details':'Các biểu hiện đặc trưng gồm sốt, phát ban và đau cơ. Bệnh lây truyền qua tiếp xúc trực tiếp hoặc qua giọt bắn. Việc xác nhận chẩn đoán dựa trên xác định Neisseria meningitidis trong mẫu máu.',
            'risk_factors':'Các đường lây được nêu gồm tiếp xúc trực tiếp và lây qua giọt bắn.',
            'prevention':'',
        }),
        '5722':('Acute atopic conjunctivitis',{
            'summary':'Tình trạng viêm kết mạc do dị ứng thuộc kiểu phản ứng tức thì, liên quan các dị nguyên trong không khí.',
            'details':'Kết mạc là niêm mạc phủ mặt sau của mi mắt và bề mặt phía trước nhãn cầu quanh giác mạc. Tình trạng viêm dị ứng này thuộc kiểu phản ứng tức thì, do các dị nguyên trong không khí như phấn hoa, bụi, bào tử và lông động vật.',
            'risk_factors':'Các tác nhân được nêu gồm phấn hoa, bụi, bào tử và lông động vật trong không khí.',
            'prevention':'',
        }),
        '11407':('Necrotising enterocolitis of newborn',{
            'summary':'Bệnh diễn tiến tối cấp ở trẻ sơ sinh, gây loét niêm mạc và hoại tử ruột; có thể tiến triển đến thủng ruột và viêm phúc mạc.',
            'details':'Tổn thương gồm loét niêm mạc diện rộng, hình thành giả mạc, xuất huyết dưới niêm mạc và hoại tử, thường ở đại tràng phải, manh tràng, đoạn cuối hồi tràng và ruột thừa. Toàn bộ đại tràng, ruột non, dạ dày và thực quản cũng có thể bị ảnh hưởng. Các biểu hiện xuất hiện trong vài tuần đầu đời gồm chướng bụng, nôn dịch mật và đi ngoài phân đen; có thể kèm ngừng thở, li bì, thân nhiệt không ổn định, nhịp tim nhanh, thở nhanh và hạ huyết áp. Bệnh có thể tiến triển đến thủng ruột và viêm phúc mạc.',
            'risk_factors':'Bệnh có thể liên quan đến thiếu máu cục bộ ở ruột trong giai đoạn quanh sinh và sự xâm nhập của vi khuẩn. Phần lớn trẻ mắc bệnh sinh non hoặc có hội chứng suy hô hấp, nhiễm khuẩn huyết hay thiếu oxy.',
            'prevention':'',
        }),
        '28167':('Radiation leak',{
            'summary':'Tình trạng bức xạ thoát qua các cấu trúc bao giữ, dẫn đến phơi nhiễm ngoài ý muốn.',
            'details':'Bức xạ là năng lượng ở dạng sóng hoặc các hạt hạ nguyên tử, đặc biệt là các loại gây ion hóa. Rò rỉ xảy ra khi bức xạ thoát qua cấu trúc bao giữ, dẫn đến phơi nhiễm ngoài ý muốn.',
            'risk_factors':'',
            'prevention':'',
        }),
    }
    (WORK/'drafts-before-final-source-check.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    stale={key:value for key,value in state['drafts'].items() if key not in rows}
    for key in stale:state['drafts'].pop(key)
    (WORK/'drafts-without-current-source.json').write_text(json.dumps(stale,ensure_ascii=False,indent=2),encoding='utf-8')
    for key,(expected,values) in translations.items():
        row=rows[key]
        assert row['source_title']==expected
        state['drafts'][key]={'id':key,**{field:{'text':value,'evidence':row['source']['definitions'] if value else []} for field,value in values.items()},'method':'direct_translation_checked_against_supplied_source'}
        state.get('rejected',{}).pop(key,None)
    assert set(state['drafts'])==set(rows)
    for key,draft in state['drafts'].items():
        source=' '.join('\n'.join(rows[key]['source']['definitions']).split())
        for field in ['summary','details','risk_factors','prevention']:
            data=draft[field]
            assert bool(data['text'].strip())==bool(data['evidence'])
            assert all(' '.join(q.split()) in source for q in data['evidence'])
    state.update(status='source_draft_pass_complete',error=None,clinical_validation=False)
    temp=WORK/'drafts.final.tmp'
    temp.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    temp.replace(WORK/'drafts.json')
    print(json.dumps({'drafts_with_current_source':len(state['drafts']),'stale_drafts_excluded':len(stale),'clinical_validation':False}))


if __name__=='__main__':main()
